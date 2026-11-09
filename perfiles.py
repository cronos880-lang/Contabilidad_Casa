"""Gestión de contabilidades independientes para Contabilidad Casa V0.3.4.
Sin librerías de terceros. No borra ni sustituye los archivos originales V0.3.
"""
from __future__ import annotations
import hashlib
import io
import json
import os
import re
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED, BadZipFile
from xml.etree import ElementTree as ET

MAX_BACKUP = 35 * 1024 * 1024
NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
EXPECTED = {'Cuentas.xlsx', 'Gastos_detallados.json', 'manifest.json'}


def _safe_name(s):
    s = str(s).strip()
    if not 1 <= len(s) <= 65 or any(ord(ch) < 32 for ch in s):
        raise ValueError('Escribe un nombre de contabilidad de 1 a 65 caracteres.')
    return s


def _validate_excel_bytes(b):
    if not (100 < len(b) <= MAX_BACKUP):
        raise ValueError('El Excel tiene un tamaño inesperado.')
    try:
        with ZipFile(io.BytesIO(b)) as z:
            required = ['xl/workbook.xml', 'xl/worksheets/sheet1.xml', 'xl/worksheets/sheet2.xml', 'xl/worksheets/sheet3.xml']
            if not all(n in z.namelist() for n in required) or z.testzip() is not None:
                raise ValueError('Cuentas.xlsx está dañado o no es compatible.')
            w = ET.fromstring(z.read('xl/workbook.xml'))
            names = {s.get('name') for s in w.iter(NS+'sheet')}
            if not {'2026', '2027', 'Hoja2'}.issubset(names):
                raise ValueError('El Excel no tiene las hojas necesarias.')
    except (BadZipFile, ET.ParseError) as ex:
        raise ValueError('El Excel es inválido.') from ex


def _validate_ledger_bytes(b):
    if len(b) > 12 * 1024 * 1024:
        raise ValueError('El historial de compras es demasiado grande.')
    try:
        data = json.loads(b.decode('utf-8'))
    except (ValueError, UnicodeError) as ex:
        raise ValueError('El historial de compras no es válido.') from ex
    if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('bases'),dict) or not isinstance(data.get('items'),list):
        raise ValueError('Gastos_detallados.json es incompatible.')
    if any(not isinstance(i,dict) or not all(k in i for k in ('id','year','month','row','amount','date','description')) for i in data['items']):
        raise ValueError('El historial tiene movimientos incompletos.')
    categories = data.get('categories', [])
    if not isinstance(categories, list) or len(categories)>200:
        raise ValueError('Las categorías personalizadas no son válidas.')
    groups = {'Recibos e impuestos', 'Seguros y vivienda', 'Servicios y suscripciones', 'Gastos variables', 'Hipoteca'}
    ids = set()
    for c in categories:
        if (not isinstance(c, dict) or not isinstance(c.get('id'), str)
                or not isinstance(c.get('name'), str) or not 1 <= len(c['name']) <= 55
                or type(c.get('row')) is not int
                or not (c['row'] == 0 and c.get('group') in groups or 9 <= c['row'] <= 35)
                or c['id'] in ids or c['id'] in {f'base-{row}' for row in range(9, 36)}):
            raise ValueError('Categoría personalizada inválida en la copia.')
        ids.add(c['id'])
    deleted = data.get('deletedBaseCategories', [])
    if not isinstance(deleted, list) or len(deleted) != len(set(map(str, deleted))) or any(
            type(row) is not int or row not in range(9,36) for row in deleted):
        raise ValueError('La lista de categorías eliminadas no es válida.')
    if any((item.get('categoryId') or f"base-{item['row']}") == f'base-{row}'
           for row in deleted for item in data['items']):
        raise ValueError('Hay movimientos asociados a una categoría eliminada.')
    if not isinstance(data.get('customBases', {}), dict):
        raise ValueError('Los importes de categorías nuevas están dañados.')
    # Las correcciones mensuales de ingresos forman parte del mismo historial y ZIP.
    monthly = data.get('monthlyIncomes', {})
    if not isinstance(monthly,dict):
        raise ValueError('Los ingresos mensuales no son válidos.')
    for period, incomes in monthly.items():
        if (not isinstance(period,str) or not re.fullmatch(r'20\d\d-(0[1-9]|1[0-2])',period)
                or not isinstance(incomes,dict) or set(incomes)-{'38','39'}):
            raise ValueError('Hay un ingreso asociado a un mes o campo inválido.')
        for value in incomes.values():
            if not isinstance(value,(int,float,str)) or isinstance(value,bool):
                raise ValueError('Los ingresos deben ser cantidades válidas.')
            try:
                from decimal import Decimal
                val = Decimal(str(value))
                if not val.is_finite() or val<0 or val>1000000000:
                    raise ValueError('El ingreso mensual está fuera de rango.')
            except (ValueError, ArithmeticError) as ex:
                raise ValueError('Un ingreso mensual no es un número válido.') from ex

    for item in data['items']:
        if 'categoryId' in item:
            category_id=item['categoryId']
            if category_id not in ids and category_id not in {f'base-{row}' for row in range(9, 36)}:
                raise ValueError('Una compra usa una categoría que no existe.')
    return data


def _empty_ledger():
    return b'{"version":1,"bases":{},"items":[],"categories":[],"customBases":{}}'


def _atomic_write(path, blob):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name = tempfile.mkstemp(prefix='._cc_',dir=str(path.parent))
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(blob); f.flush(); os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name): os.unlink(name)


class Profiles:
    def __init__(self, root):
        self.root = Path(root)
        appdata = os.getenv('LOCALAPPDATA') or os.getenv('XDG_DATA_HOME') or str(Path.home()/'.local'/'share')
        self.config_dir = Path(os.getenv('CC_CONFIG_DIR') or (Path(appdata)/'ContabilidadCasaV031'))
        self.config_file = self.config_dir/'perfiles.json'
        self.default_parent = Path(os.getenv('CC_DATA_DIR') or (Path.home()/'Documents'/'Contabilidad Casa'/'Contabilidades'))
        self.template = self.root/'Plantilla_Cuentas.xlsx'
        self.config = self._load()
        self.migrate_legacy()

    def _load(self):
        if not self.config_file.exists():
            return {'version':1,'profiles':[],'active':None,'migrated':False}
        data = json.loads(self.config_file.read_text(encoding='utf-8'))
        if not isinstance(data,dict) or data.get('version')!=1 or not isinstance(data.get('profiles'),list):
            raise ValueError('El índice de contabilidades no es válido.')
        return data

    def _save(self):
        _atomic_write(self.config_file,json.dumps(self.config,ensure_ascii=False,indent=2).encode('utf-8'))

    def list(self):
        return {'profiles':[{'id':p['id'],'name':p['name'],'location':p['location'],
                             'ready':(Path(p['location'])/'Cuentas.xlsx').is_file()}
                            for p in self.config['profiles']], 'active':self.config.get('active')}

    def get(self,id):
        for p in self.config['profiles']:
            if p['id']==id:
                return p
        raise ValueError('No existe esa contabilidad.')

    def selected(self):
        pid=self.config.get('active')
        return self.get(pid) if pid else None

    def rename(self, id, new_name):
        name = _safe_name(new_name)
        if any(p['id'] != id and p['name'].casefold() == name.casefold()
               for p in self.config['profiles']):
            raise ValueError('Ya tienes otra contabilidad con ese nombre.')
        entry = self.get(id)
        entry['name'] = name
        self._save()
        return entry

    def delete(self, id):
        """Quita el perfil activo y traslada la carpeta COMPLETA a un archivo recuperable.
        Nunca se borra definitivamente la información del usuario.
        """
        entry = self.get(id)
        folder = Path(entry['location']).resolve()
        if not folder.is_dir() or not re.fullmatch(r'.+_[0-9a-f]{8}', folder.name):
            raise ValueError('La carpeta no es válida para eliminarla automáticamente.')
        if any(folder == Path(p['location']).resolve() for p in self.config['profiles'] if p['id'] != id):
            raise ValueError('Hay otra contabilidad usando la misma carpeta.')
        # Primero comprobamos la integridad y generamos un ZIP de emergencia.
        backup = self.make_backup(id)
        archive_dir = self.config_dir/'Contabilidades_eliminadas'
        if archive_dir.resolve() == folder or folder in archive_dir.resolve().parents:
            raise ValueError('La carpeta de recuperación está dentro de la contabilidad. No se puede eliminar con seguridad.')
        archive_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        destination = archive_dir / (stamp + '_' + entry['id'])
        zip_path = archive_dir / (stamp + '_' + entry['id'] + '.zip')
        _atomic_write(zip_path, backup)
        # Guardar también el directorio completo, incluidas copias históricas.
        try:
            shutil.move(str(folder), str(destination))
        except Exception:
            raise ValueError('No se ha podido retirar la contabilidad. Sigue en su carpeta original.')
        old_profiles = list(self.config['profiles'])
        old_active = self.config.get('active')
        self.config['profiles'] = [p for p in old_profiles if p['id'] != id]
        if old_active == id:
            self.config['active'] = None
        try:
            self._save()
        except Exception:
            self.config['profiles'] = old_profiles
            self.config['active'] = old_active
            shutil.move(str(destination), str(folder))
            raise
        return {'ok': True, 'message': 'Contabilidad eliminada de la lista. Copia recuperable conservada.',
                'backupPath': str(zip_path), 'archivedFolder': str(destination)}

    def select(self,id):
        p=self.get(id)
        folder=Path(p['location'])
        _validate_excel_bytes((folder/'Cuentas.xlsx').read_bytes())
        if (folder/'Gastos_detallados.json').exists():
            _validate_ledger_bytes((folder/'Gastos_detallados.json').read_bytes())
        self.config['active']=id
        self._save()
        return p

    def _new_folder(self,name,parent=None):
        parent=Path(parent).expanduser().resolve() if parent else self.default_parent.resolve()
        if not parent.exists(): parent.mkdir(parents=True,exist_ok=True)
        if not parent.is_dir(): raise ValueError('La carpeta elegida no existe.')
        base=re.sub(r'[^A-Za-z0-9_-]+','_',name).strip('_')[:35] or 'Contabilidad'
        folder=parent/(base+'_'+uuid.uuid4().hex[:8])
        if folder.exists(): raise ValueError('La carpeta elegida ya existe.')
        return folder

    def create(self,name,parent=None,excel=None,ledger=None,backups=None):
        name=_safe_name(name)
        excel=excel if excel is not None else self.template.read_bytes()
        ledger=ledger if ledger is not None else _empty_ledger()
        _validate_excel_bytes(excel)
        _validate_ledger_bytes(ledger)
        folder=self._new_folder(name,parent)
        pid=str(uuid.uuid4())
        previous_active=self.config.get('active')
        try:
            folder.mkdir(parents=False,exist_ok=False)
            _atomic_write(folder/'Cuentas.xlsx',excel)
            _atomic_write(folder/'Gastos_detallados.json',ledger)
            (folder/'Copias_seguridad').mkdir(exist_ok=True)
            if backups:
                for path in backups:
                    if path.is_file() and path.suffix.lower() in ('.xlsx','.json','.zip'):
                        if path.stat().st_size <= MAX_BACKUP:
                            shutil.copy2(path,folder/'Copias_seguridad'/path.name)
            entry={'id':pid,'name':name,'location':str(folder)}
            self.config['profiles'].append(entry)
            self.config['active']=pid
            self._save()
            return entry
        except Exception:
            self.config['profiles']=[p for p in self.config['profiles'] if p.get('id')!=pid]
            self.config['active']=previous_active
            if folder.exists(): shutil.rmtree(folder)
            raise

    def migrate_legacy(self):
        if self.config.get('migrated'): return
        legacy=self.root/'Cuentas.xlsx'
        if legacy.is_file() and not self.config['profiles']:
            try:
                ledger=(self.root/'Gastos_detallados.json').read_bytes() if (self.root/'Gastos_detallados.json').is_file() else _empty_ledger()
                backdir=self.root/'Copias_seguridad'
                backups=list(backdir.iterdir()) if backdir.is_dir() else []
                self.create('Mi contabilidad (V0.3)',excel=legacy.read_bytes(),ledger=ledger,backups=backups)
            except Exception as e:
                print('ATENCIÓN: No se ha podido importar V0.3:',e)
                # No se marca migrado: volver a intentar la próxima vez.
                return
        self.config['migrated']=True
        self._save()

    def make_backup(self,pid):
        p=self.get(pid)
        folder=Path(p['location'])
        excel=(folder/'Cuentas.xlsx').read_bytes()
        ledger=(folder/'Gastos_detallados.json').read_bytes() if (folder/'Gastos_detallados.json').exists() else _empty_ledger()
        _validate_excel_bytes(excel); _validate_ledger_bytes(ledger)
        manifest={'format':'ContabilidadCasaBackup','schema':1,'name':p['name'],
                  'created':datetime.now().isoformat(timespec='seconds'),
                  'sha256':{'Cuentas.xlsx':hashlib.sha256(excel).hexdigest(),
                            'Gastos_detallados.json':hashlib.sha256(ledger).hexdigest()}}
        mem=io.BytesIO()
        with ZipFile(mem,'w',compression=ZIP_DEFLATED,compresslevel=6) as z:
            z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
            z.writestr('Cuentas.xlsx',excel)
            z.writestr('Gastos_detallados.json',ledger)
        return mem.getvalue()

    def check_backup(self,blob):
        if not isinstance(blob,bytes) or len(blob)>MAX_BACKUP or len(blob)<100:
            raise ValueError('La copia de seguridad tiene un tamaño incorrecto.')
        try:
            with ZipFile(io.BytesIO(blob)) as z:
                entries=z.infolist()
                if len(entries)!=3 or {i.filename for i in entries}!=EXPECTED:
                    raise ValueError('No es una copia creada por Contabilidad Casa.')
                if any(i.file_size>MAX_BACKUP or i.compress_size>MAX_BACKUP for i in entries):
                    raise ValueError('La copia de seguridad es demasiado grande.')
                manifest=json.loads(z.read('manifest.json'))
                if manifest.get('format')!='ContabilidadCasaBackup' or manifest.get('schema')!=1:
                    raise ValueError('La copia no es compatible con esta versión.')
                excel=z.read('Cuentas.xlsx')
                ledger=z.read('Gastos_detallados.json')
        except (BadZipFile, KeyError, UnicodeError, ET.ParseError) as ex:
            raise ValueError('No se ha podido leer la copia de seguridad.') from ex
        for filename, data in [('Cuentas.xlsx',excel),('Gastos_detallados.json',ledger)]:
            if hashlib.sha256(data).hexdigest()!=manifest.get('sha256',{}).get(filename):
                raise ValueError('La copia ha sido modificada o está dañada.')
        _validate_excel_bytes(excel); _validate_ledger_bytes(ledger)
        return manifest,excel,ledger

    def import_backup(self,blob,name=None,parent=None):
        manifest,excel,ledger=self.check_backup(blob)
        return self.create(name or manifest['name'],parent=parent,excel=excel,ledger=ledger)

    def restore(self,pid,blob):
        manifest,excel,ledger=self.check_backup(blob)
        p=self.get(pid)
        folder=Path(p['location'])
        xlsx=folder/'Cuentas.xlsx'; jsonfile=folder/'Gastos_detallados.json'
        old_xlsx=xlsx.read_bytes()
        old_ledger=jsonfile.read_bytes() if jsonfile.exists() else _empty_ledger()
        _validate_excel_bytes(old_xlsx); _validate_ledger_bytes(old_ledger)
        # Primero proteger el estado anterior en un ZIP fechado, no sobrescribirlo nunca.
        backup_dir=folder/'Copias_seguridad'
        backup_dir.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        previous=self.make_backup(pid)
        _atomic_write(backup_dir/f'Antes_de_restaurar_{stamp}.zip',previous)
        try:
            _atomic_write(xlsx,excel)
            _atomic_write(jsonfile,ledger)
        except Exception:
            _atomic_write(xlsx,old_xlsx)
            _atomic_write(jsonfile,old_ledger)
            raise
        return {'ok':True,'message':'Copia recuperada. Guardado anterior protegido en Copias_seguridad.'}
