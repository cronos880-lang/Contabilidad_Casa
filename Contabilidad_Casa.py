#!/usr/bin/env python3
"""Contabilidad Casa V0.3.13 — interfaz local y edición conservadora de Cuentas.xlsx.
No necesita instalar librerías de terceros; conserva las fórmulas y partes del XLSX.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime, date
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import hmac
import json
import os
import re
import secrets
import shutil
import sys
import tempfile
import uuid
import copy
import threading
import webbrowser
from datetime import timezone
from perfiles import Profiles

ROOT = Path(__file__).resolve().parent
XLSX = ROOT / "Cuentas.xlsx"
BACKUPS = ROOT / "Copias_seguridad"
LEDGER = ROOT / "Gastos_detallados.json"
DETAILED = {31: "Comida", 32: "Extras", 33: "Vacaciones"}
STATIC = ROOT / "web"
VERSION = "V0.3.13"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
MONTHS = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
SHEETS = {2026: "xl/worksheets/sheet1.xml", 2027: "xl/worksheets/sheet2.xml"}
BANKS_SHEET = "xl/worksheets/sheet3.xml"
GROUPS = [
    ("Recibos e impuestos", range(9, 16)),
    ("Seguros y vivienda", range(16, 22)),
    ("Servicios y suscripciones", range(22, 30)),
    ("Gastos variables", range(30, 35)),
    ("Hipoteca", range(35, 36)),
]
CELL_TAG = re.compile(r'<(?P<prefix>[A-Za-z_][\w.-]*:)?c\b(?P<attrs>[^>]*?)(?:\s*/>|>(?P<inner>.*?)</(?:[A-Za-z_][\w.-]*:)?c>)', re.DOTALL)
ADDRESS = re.compile(r'\br="([A-Z]+\d+)"')
STYLE = re.compile(r'\bs="(\d+)"')
ROW = re.compile(r'<(?P<prefix>[A-Za-z_][\w.-]*:)?row\b[^>]*\br="(\d+)"[^>]*>.*?</(?:[A-Za-z_][\w.-]*:)?row>', re.DOTALL)
WRITE_LOCK = threading.RLock()
TOKEN = secrets.token_urlsafe(32)
PROFILES = None


def excel_column(n: int) -> str:
    result = ""
    while n:
        n, d = divmod(n - 1, 26)
        result = chr(65 + d) + result
    return result


def column_number(cell: str) -> int:
    letters = re.match(r'[A-Z]+', cell).group()
    n = 0
    for ch in letters:
        n = 26 * n + ord(ch) - 64
    return n


def parse_amount(text):
    if text is None or str(text).strip() == "":
        return None
    if isinstance(text, bool):
        raise ValueError("El importe debe ser un número.")
    s = str(text).strip().replace('€', '').replace(' ', '').replace('\u00a0', '')
    if ',' in s and '.' in s:
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        d = Decimal(s)
        if not d.is_finite() or abs(d) > 1000000000:
            raise ValueError("El importe está fuera del rango permitido.")
        d = d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return format(d, 'f')
    except InvalidOperation:
        raise ValueError(f"Importe no válido: {str(text)[:50]}")


def as_float(value):
    if value in (None, ''):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def read_sheet(z: ZipFile, name: str, strings: list[str]):
    root = ET.fromstring(z.read(name))
    cells = {}
    for cell in root.iter(NS + 'c'):
        addr = cell.get('r')
        if not addr:
            continue
        f = cell.find(NS + 'f')
        v = cell.find(NS + 'v')
        value = v.text if v is not None else None
        if cell.get('t') == 's' and value is not None:
            value = strings[int(value)]
        elif cell.get('t') == 'inlineStr':
            value = ''.join(t.text or '' for t in cell.iter(NS + 't'))
        cells[addr] = {'value': value, 'formula': f is not None}
    return cells


def read_workbook():
    if not XLSX.is_file():
        raise FileNotFoundError("No encuentro Cuentas.xlsx en la contabilidad abierta.")
    with ZipFile(XLSX, 'r') as z:
        if z.testzip() is not None:
            raise ValueError("El archivo Excel está dañado.")
        required = [*SHEETS.values(), BANKS_SHEET, 'xl/workbook.xml']
        if any(x not in z.namelist() for x in required):
            raise ValueError("Este Excel no tiene la estructura esperada de Cuentas.xlsx.")
        wb = ET.fromstring(z.read('xl/workbook.xml'))
        sheetnames = {s.get('name') for s in wb.iter(NS + 'sheet')}
        if not {'2026', '2027', 'Hoja2'}.issubset(sheetnames):
            raise ValueError("Faltan las hojas 2026, 2027 u Hoja2.")
        strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            root = ET.fromstring(z.read('xl/sharedStrings.xml'))
            strings = [''.join(t.text or '' for t in node.iter(NS + 't')) for node in root.iter(NS + 'si')]
        return {2026: read_sheet(z, SHEETS[2026], strings),
                2027: read_sheet(z, SHEETS[2027], strings),
                'banks': read_sheet(z, BANKS_SHEET, strings)}


def value_of(cells, cell):
    return cells.get(cell, {}).get('value')


def income_key(year, month):
    return f'{year}-{month:02d}'


def monthly_income(ledger, sheet, year, month, row):
    """Ingreso habitual 1: valor base del Excel editable por mes. Ingreso habitual 2: SOLO el mes indicado.
    Los valores anteriores a V0.3.6 se congelan al activar cada contabilidad.
    """
    custom = ledger.get('monthlyIncomes', {}).get(income_key(year, month), {})
    if str(row) in custom:
        return as_float(custom[str(row)]) or 0.0
    if row == 39:
        return as_float(value_of(sheet, 'B39')) or 0.0
    return 0.0


def had_legacy_activity(wb, ledger, year, month):
    """Una celda 0 precargada NO constituye un mes registrado."""
    sh = wb[year]
    col = excel_column(month + 4)
    allowed_rows = [r for r in range(9, 36) if r not in deleted_base_rows(ledger)] + [40]
    if any(abs(as_float(value_of(sh, f'{col}{r}')) or 0) > 0.00001
           for r in allowed_rows):
        return True
    if any(abs(c['value']) > 0.00001 for c in custom_expenses(ledger, year, month)):
        return True
    if year == 2026:
        bank = wb['banks']
        bankcol = excel_column(month + 1)
        return any(abs(as_float(value_of(bank, f'{bankcol}{r}')) or 0) > 0.00001 for r in (7,8))
    return False


def snapshot_legacy_incomes():
    """Convierte la referencia anual del ingreso habitual 2 en valores mensuales históricos.
    Conserva el Excel y guarda una copia íntegra antes de editar el historial.
    Es idempotente por contabilidad y respeta las correcciones ya existentes.
    """
    with WRITE_LOCK:
        ledger = load_ledger()
        if ledger.get('incomeSnapshotV036'):
            return
        wb = read_workbook()
        monthly = ledger.setdefault('monthlyIncomes', {})
        for year in SHEETS:
            ref = as_float(value_of(wb[year], 'B38')) or 0.0
            for month in range(1,13):
                if had_legacy_activity(wb, ledger, year, month):
                    monthly.setdefault(income_key(year,month), {}).setdefault('38', format(money(ref),'f'))
        # La copia es recuperable desde "Recuperar copia".
        active = PROFILES.selected() if PROFILES else None
        if active:
            BACKUPS.mkdir(parents=True,exist_ok=True)
            stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            backup_path = BACKUPS / f'Antes_de_ingresos_por_mes_{stamp}.zip'
            backup = PROFILES.make_backup(active['id'])
            fd, temp = tempfile.mkstemp(prefix='._Copia_ingresos_',suffix='.zip',dir=str(BACKUPS))
            try:
                with os.fdopen(fd,'wb') as target:
                    target.write(backup)
                    target.flush();os.fsync(target.fileno())
                PROFILES.check_backup(Path(temp).read_bytes())
                os.replace(temp, backup_path)
            finally:
                if os.path.exists(temp): os.unlink(temp)
        ledger['incomeSnapshotV036'] = True
        write_ledger_atomic(ledger)


def readable_info(year, month):
    if year not in SHEETS or not 1 <= month <= 12:
        raise ValueError('Año o mes incorrecto.')
    wb = read_workbook()
    sheet = wb[year]
    bank = wb['banks']
    month_col = excel_column(month + 4)
    bank_col = excel_column(month + 1)
    ledger = load_ledger()
    deleted = deleted_base_rows(ledger)
    categories = []
    for row in range(9, 36):
        if row in deleted:
            continue
        cell = month_col + str(row)
        content = sheet.get(cell, {})
        categories.append({'row': row, 'name': value_of(sheet, 'A' + str(row)) or 'Concepto ' + str(row),
                           'value': as_float(content.get('value')), 'formula': content.get('formula', False)})
    ledger = load_ledger()
    # B39 continúa como referencia para el ingreso habitual 1. Las variaciones se guardan
    # por año/mes en el historial. El ingreso habitual 2 es completamente mensual.
    incomes = [
        {'row': 39, 'name': value_of(sheet,'A39') or 'Ingreso habitual 1',
         'value': monthly_income(ledger, sheet, year, month, 39), 'scope': 'month', 'habitual': True},
        {'row': 38, 'name': value_of(sheet,'A38') or 'Ingreso habitual 2',
         'value': monthly_income(ledger, sheet, year, month, 38), 'scope': 'month', 'habitual': False},
        {'row': 40, 'name': 'Ingreso extra',
         'value': as_float(value_of(sheet, month_col + '40')), 'scope': 'extra'},
    ]
    banks = [{'row': row, 'name': value_of(bank, 'A' + str(row)),
              'value': as_float(value_of(bank, bank_col + str(row)))} for row in (7, 8)] if year == 2026 else []
    ledger = load_ledger()
    custom_breakdown = custom_expenses(ledger, year, month)
    expense_total = round(sum(x['value'] or 0 for x in categories) +
                          sum(x['value'] for x in custom_breakdown), 2)
    income_total = round(sum(x['value'] or 0 for x in incomes), 2)
    return {'version': VERSION, 'year': year, 'month': month, 'monthName': MONTHS[month - 1],
            'categories': categories, 'customExpenseCategories':custom_breakdown, 'incomes': incomes, 'banks': banks,
            'bankAvailable': year == 2026,
            'monthExpense': expense_total, 'monthlyIncome': income_total,
            'available': round(income_total - expense_total, 2),
            'workbook': XLSX.name,
            'modified': datetime.fromtimestamp(XLSX.stat().st_mtime).strftime('%d/%m/%Y %H:%M')}


def annual_summary(year: int):
    if year not in SHEETS:
        raise ValueError('Año incorrecto.')
    wb = read_workbook()
    sheet = wb[year]
    bank = wb['banks']
    group_totals = {name: 0.0 for name, _ in GROUPS}
    ledger = load_ledger()
    months = []
    months_recorded = 0
    expense_rows = [row for row in range(9, 36) if row not in deleted_base_rows(ledger)]
    for month in range(1, 13):
        month_col = excel_column(month + 4)
        bank_col = excel_column(month + 1)
        expense_total = 0.0
        nonzero_expenses = 0
        for row in expense_rows:
            value = as_float(value_of(sheet, month_col + str(row)))
            if value is None:
                continue
            expense_total += value
            if abs(value) > 1e-9:
                nonzero_expenses += 1
            for group_name, row_range in GROUPS:
                if row in row_range:
                    group_totals[group_name] += value
                    break
        for extra in custom_expenses(ledger, year, month):
            expense_total += extra['value']
            group_totals[extra['group']] += extra['value']
            if abs(extra['value']) > 1e-9:
                nonzero_expenses += 1
        extra_income = as_float(value_of(sheet, month_col + '40')) or 0.0
        ingreso_habitual_1 = monthly_income(ledger, sheet, year, month, 39)
        ingreso_habitual_2 = monthly_income(ledger, sheet, year, month, 38)
        income_total = ingreso_habitual_1 + ingreso_habitual_2 + extra_income
        bank_total = None
        if year == 2026:
            cuenta_1 = as_float(value_of(bank, bank_col + '7'))
            cuenta_2 = as_float(value_of(bank, bank_col + '8'))
            if not ((cuenta_1 in (None, 0)) and (cuenta_2 in (None, 0))):
                bank_total = round((cuenta_1 or 0) + (cuenta_2 or 0), 2)
        recorded = bool(nonzero_expenses or abs(extra_income) > 1e-9 or bank_total is not None
                        or (income_key(year,month) in ledger.get('monthlyIncomes', {}) and
                            (abs(ingreso_habitual_2) > 1e-9 or abs(ingreso_habitual_1 - (as_float(value_of(sheet,'B39')) or 0)) > 1e-9)))
        if recorded:
            months_recorded += 1
        months.append({
            'month': month,
            'name': MONTHS[month - 1],
            'short': MONTHS[month - 1][:3],
            'expenses': round(expense_total, 2),
            'incomes': round(income_total, 2),
            'available': round(income_total - expense_total, 2),
            'pending': not recorded,
            'bankTotal': bank_total,
            'bankCaixa': cuenta_1 if year == 2026 and bank_total is not None else None,
            'bankSabadell': cuenta_2 if year == 2026 and bank_total is not None else None,
        })
    recorded_months = [m for m in months if not m['pending']]
    total_expenses = round(sum(m['expenses'] for m in recorded_months), 2)
    total_incomes = round(sum(m['incomes'] for m in recorded_months), 2)
    total_available = round(sum(m['available'] for m in recorded_months), 2)
    last_bank_total = None
    for item in reversed(months):
        if item['bankTotal'] is not None:
            last_bank_total = item['bankTotal']
            break
    return {
        'version': VERSION,
        'year': year,
        'months': months,
        'monthsRecorded': months_recorded,
        'totals': {
            'expenses': total_expenses,
            'incomes': total_incomes,
            'available': total_available,
            'bankTotal': last_bank_total,
        },
        'expenseGroups': [
            {'name': name, 'value': round(group_totals[name], 2)}
            for name, _ in GROUPS
        ],
        'bankAvailable': year == 2026,
        'bankNames': [value_of(bank, 'A7') or 'Cuenta 1', value_of(bank, 'A8') or 'Cuenta 2'],
        'bankComparison': [
            {'year': str(value_of(bank, f'{column}11') or ''),
             'caixa': as_float(value_of(bank, f'{column}12')) or 0,
             'sabadell': as_float(value_of(bank, f'{column}13')) or 0}
            for column in ('B','C','D')
            if (as_float(value_of(bank, f'{column}12')) or 0) > 0
            or (as_float(value_of(bank, f'{column}13')) or 0) > 0
        ],
        'modified': datetime.fromtimestamp(XLSX.stat().st_mtime).strftime('%d/%m/%Y %H:%M'),
        'workbook': XLSX.name,
    }


def patch_cells(xml: bytes, updates: dict[str, str | None]) -> bytes:
    """Cambia solo valores de las celdas; el resto de XML permanece literal.
    Inserta celdas ausentes en su fila (el Excel de origen omite muchos meses).
    """
    text = xml.decode('utf-8')
    found = set()

    def replace_cell(match):
        attributes = match.group('attrs')
        address = ADDRESS.search(attributes)
        if not address or address.group(1) not in updates:
            return match.group(0)
        addr = address.group(1)
        inner = match.group('inner') or ''
        if re.search(r'<(?:[A-Za-z_][\w.-]*:)?f\b', inner):
            raise ValueError(f"No se permite cambiar una fórmula de Excel ({addr}).")
        found.add(addr)
        attributes = re.sub(r'\s+t="[^"]*"', '', attributes).rstrip()
        value = updates[addr]
        prefix=match.group('prefix') or ''
        return f'<{prefix}c{attributes}/>' if value is None else f'<{prefix}c{attributes}><{prefix}v>{escape(value)}</{prefix}v></{prefix}c>'

    text = CELL_TAG.sub(replace_cell, text)
    missing = {a: v for a, v in updates.items() if a not in found}
    if missing:
        by_row = {}
        for a, v in missing.items():
            row_number = int(re.search(r'\d+$', a).group())
            by_row.setdefault(row_number, []).append((a, v))

        def replace_row(match):
            r = int(match.group(2))
            prefix=match.group('prefix') or ''
            if r not in by_row:
                return match.group(0)
            body = match.group(0)
            items = sorted(by_row[r], key=lambda pair: column_number(pair[0]))
            for address, value in items:
                if value is None:
                    continue
                # Copiar el formato de la celda más cercana de la misma fila.
                neighbors = []
                for c in CELL_TAG.finditer(body):
                    a = ADDRESS.search(c.group('attrs'))
                    st = STYLE.search(c.group('attrs'))
                    if a and st:
                        neighbors.append((abs(column_number(a.group(1)) - column_number(address)), st.group(1)))
                month_neighbors = []
                for c in CELL_TAG.finditer(body):
                    a = ADDRESS.search(c.group('attrs'))
                    st = STYLE.search(c.group('attrs'))
                    if a and st and 5 <= column_number(a.group(1)) <= 16:
                        month_neighbors.append((abs(column_number(a.group(1)) - column_number(address)), st.group(1)))
                candidates = month_neighbors or neighbors
                style = f' s="{min(candidates)[1]}"' if candidates else ''
                newcell = f'<{prefix}c r="{address}"{style}><{prefix}v>{escape(value)}</{prefix}v></{prefix}c>'
                following = None
                for c in CELL_TAG.finditer(body):
                    a = ADDRESS.search(c.group('attrs'))
                    if a and column_number(a.group(1)) > column_number(address):
                        following = c.start()
                        break
                if following is None:
                    following = body.rfind(f'</{prefix}row>')
                body = body[:following] + newcell + body[following:]
            return body

        text = ROW.sub(replace_row, text)
        existing_rows = {int(x) for x in re.findall(r'<(?:[A-Za-z_][\w.-]*:)?row\b[^>]*\br="(\d+)"', text)}
        if any(int(re.search(r'\d+$', a).group()) not in existing_rows for a in missing):
            raise ValueError('No se encuentra una fila necesaria en el Excel.')
    return text.encode('utf-8')


def set_recalculation(xml: bytes) -> bytes:
    text = xml.decode('utf-8')
    if '<calcPr' in text:
        return re.sub(r'<calcPr\b[^>]*/>', '<calcPr calcMode="auto" fullCalcOnLoad="1" forceFullCalc="1"/>', text, count=1).encode('utf-8')
    return xml



def ledger_key(year, month, row):
    return f"{year}-{month:02d}-{row}"


def money(value):
    if value in (None, ''):
        return Decimal('0.00')
    return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def deleted_base_rows(ledger):
    # Filas originales que el usuario ha eliminado de esta contabilidad.
    raw = ledger.get('deletedBaseCategories', [])
    if not isinstance(raw, list) or len(raw) != len(set(map(str, raw))) or any(
            type(row) is not int or row not in range(9, 36) for row in raw):
        raise ValueError('Las categorías eliminadas tienen un formato inválido. Recupera una copia.')
    return set(raw)


def item_matches_category(item, category):
    cid = item.get('categoryId') or f"base-{item['row']}"
    return cid == category['id']


def load_ledger():
    if not LEDGER.is_file():
        return {'version': 1, 'bases': {}, 'items': [], 'categories': [], 'customBases': {}}
    with LEDGER.open('r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('bases'), dict) or not isinstance(data.get('items'), list):
        raise ValueError('Gastos_detallados.json tiene un formato inesperado. Restaura una copia de seguridad.')
    if not isinstance(data.get('customBases',{}),dict):
        raise ValueError('Las cantidades de categorías personalizadas no son válidas.')
    deleted_base_rows(data)
    return data


def categories_for_ledger(ledger, year=2026, wb=None):
    """Todas las categorías de Gastos, con los nombres reales de la hoja anual.

    Los identificadores base-9 ... base-35 son estables para que las compras
    anteriores sigan enlazadas y se contabilicen en la misma celda del Excel.
    """
    if year not in SHEETS:
        raise ValueError('Año incorrecto para la lista de gastos.')
    sheet = (wb if wb is not None else read_workbook())[year]
    entries = []
    deleted = deleted_base_rows(ledger)
    for group, rows in GROUPS:
        for row in rows:
            if row in deleted:
                continue
            name = str(value_of(sheet, f'A{row}') or f'Concepto {row}').strip()
            entries.append({'id': f'base-{row}', 'name': name, 'row': row,
                            'builtIn': True, 'group': group})
        for c in ledger.get('categories', []):
            if (not isinstance(c, dict) or not isinstance(c.get('id'), str)
                    or not isinstance(c.get('name'), str)
                    or c.get('row') != 0 or c.get('group') not in {g for g,_ in GROUPS}):
                raise ValueError('Hay una categoría antigua sin migrar o no válida. Recupera la copia anterior.')
            if c['group'] == group:
                entries.append({'id': c['id'], 'name': c['name'].upper(), 'row': 0,
                                'builtIn': False, 'group': c['group']})
    if len({c['id'] for c in entries}) != len(entries):
        raise ValueError('Hay categorías duplicadas en el historial.')
    return entries


def category_for_item(item, categories):
    category_id = item.get('categoryId') or f"base-{item['row']}"
    match = next((c for c in categories if c['id'] == category_id), None)
    if match is None or item['row'] != match['row']:
        raise ValueError('Una compra hace referencia a una categoría que no existe.')
    return match


def custom_key(year, month, category_id):
    return f'{year}-{month:02d}-{category_id}'


def custom_amounts(ledger, year, month, category_id):
    base_raw = ledger.get('customBases', {}).get(custom_key(year, month, category_id))
    base = money(base_raw)
    movements = sum((money(i['amount']) for i in ledger['items']
                     if i['year'] == year and i['month'] == month
                     and i.get('categoryId') == category_id), Decimal('0.00'))
    return base_raw, base, movements


def custom_expenses(ledger, year, month):
    # Consultar solo categorías personalizadas, sin releer el Excel en cada mes
    # del gráfico anual. Los conceptos originales se leen al crear el desplegable.
    result = []
    for c in ledger.get('categories', []):
        if c.get('row') != 0 or c.get('group') not in {g for g, _ in GROUPS}:
            raise ValueError('Hay una categoría antigua sin migrar o no válida. Recupera la copia anterior.')
        raw, base, movement = custom_amounts(ledger, year, month, c['id'])
        result.append({'id': c['id'], 'name': c['name'].upper(), 'row': 0,
                       'group': c['group'], 'value': float(base + movement),
                       'base': float(base), 'movement': float(movement),
                       'baseExists': raw is not None})
    return result


def create_category(payload):
    name = str(payload.get('name', '')).strip().upper()
    group = str(payload.get('group', '')).strip()
    if not 1 <= len(name) <= 55 or any(ord(ch) < 32 for ch in name):
        raise ValueError('Escribe un nombre de categoría de 1 a 55 caracteres.')
    if group not in {g for g,_ in GROUPS}:
        raise ValueError('Selecciona el grupo en el que aparecerá el gasto.')
    with WRITE_LOCK:
        ledger = load_ledger()
        categories = categories_for_ledger(ledger)
        if any(c['name'].casefold() == name.casefold() for c in categories):
            raise ValueError('Ya existe una categoría con ese nombre.')
        category = {'id': str(uuid.uuid4()), 'name': name, 'row': 0, 'group': group}
        ledger.setdefault('categories', []).append(category)
        BACKUPS.mkdir(exist_ok=True)
        if LEDGER.exists():
            shutil.copy2(LEDGER, BACKUPS / ('Gastos_detallados_antes_categoria_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.json'))
        write_ledger_atomic(ledger)
        return {'ok': True, 'category': category}


def move_category(payload):
    category_id = str(payload.get('id',''))
    group = str(payload.get('group','')).strip()
    if group not in {g for g,_ in GROUPS}:
        raise ValueError('Elige un grupo de gastos válido.')
    with WRITE_LOCK:
        ledger = load_ledger()
        c = next((c for c in ledger.get('categories',[]) if c.get('id') == category_id),None)
        if not c or c.get('row') != 0:
            raise ValueError('No se encuentra esa categoría personalizada.')
        if c.get('group') == group:
            return {'ok':True,'category':c}
        BACKUPS.mkdir(exist_ok=True)
        if LEDGER.is_file():
            shutil.copy2(LEDGER,BACKUPS/('Gastos_detallados_antes_cambiar_grupo_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.json'))
        c['group'] = group
        write_ledger_atomic(ledger)
        return {'ok':True,'category':c}


def category_impact(category_id):
    """Impacto real de borrar cualquier categoría, incluida una fila original."""
    ledger = load_ledger()
    wb = read_workbook()
    categories = categories_for_ledger(ledger, wb=wb)
    category = next((c for c in categories if c['id'] == category_id), None)
    if category is None:
        raise ValueError('No encuentro esta categoría en la contabilidad.')
    # Evitar borrar sobre un historial con referencias rotas.
    for item in ledger['items']:
        category_for_item(item, categories)
    movements = [i for i in ledger['items'] if item_matches_category(i, category)]
    movement_total = sum((money(i['amount']) for i in movements), Decimal('0.00'))
    if category['builtIn']:
        row = category['row']
        raw_months = []
        for year in SHEETS:
            for month in range(1, 13):
                cell = excel_column(month+4)+str(row)
                content = wb[year].get(cell, {})
                # No se borran fórmulas. Mantendremos intacta la estructura Excel.
                if content.get('formula'):
                    raise ValueError(f'La categoría contiene una fórmula en {cell} ({year}); no puede eliminarse automáticamente.')
                key = ledger_key(year, month, row)
                if key in ledger['bases']:
                    check_detail_consistency(ledger, wb, year, month, row)
                val = content.get('value')
                raw_months.append((year, month, money(val)))
        amount = sum((value for _, _, value in raw_months), Decimal('0.00'))
        return {'id':category_id,'name':category['name'],'group':category['group'],
                'builtIn':True, 'movements':len(movements),'amount':float(amount),
                'manualAmount':float(amount-movement_total),'movementAmount':float(movement_total),
                'monthsWithAmount':sum(1 for _,_,value in raw_months if value),
                'note':'La fila del Excel conservará su nombre para no romper fórmulas, pero sus importes se limpiarán.'}
    suffix = '-' + category_id
    bases = {k:v for k,v in ledger.get('customBases', {}).items() if k.endswith(suffix)}
    base_total = sum((money(v) for v in bases.values()), Decimal('0.00'))
    return {'id':category['id'], 'name':category['name'], 'group':category['group'],
            'builtIn':False,'movements':len(movements),'amount':float(base_total+movement_total),
            'manualAmount':float(base_total),'movementAmount':float(movement_total),
            'monthsWithAmount':len({k[:-len(suffix)] for k,v in bases.items() if money(v)})}


def delete_category(payload):
    """Borra cualquier categoría, con ZIP anterior obligatorio y sin eliminar filas Excel."""
    category_id = str(payload.get('id',''))
    confirmation = payload.get('confirmName')
    with WRITE_LOCK:
        impact = category_impact(category_id)
        if not isinstance(confirmation,str) or confirmation != impact['name']:
            raise ValueError('Escribe exactamente el nombre de la categoría para confirmar.')
        active = PROFILES.selected() if PROFILES is not None else None
        if active is None or active['location'] != str(XLSX.parent):
            raise ValueError('La contabilidad activa ha cambiado. Vuelve a abrirla.')
        # Siempre respaldar EXCEL + HISTORIAL juntos antes de alterar nada.
        complete_backup = PROFILES.make_backup(active['id'])
        BACKUPS.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        backup_path = BACKUPS / ('Antes_de_borrar_categoria_' + stamp + '.zip')
        fd, tmp = tempfile.mkstemp(prefix='._Copia_categoria_', suffix='.zip', dir=str(BACKUPS))
        try:
            with os.fdopen(fd,'wb') as dest:
                dest.write(complete_backup)
                dest.flush();os.fsync(dest.fileno())
            PROFILES.check_backup(Path(tmp).read_bytes())
            os.replace(tmp,backup_path)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
        ledger = load_ledger()
        affected = [i for i in ledger['items'] if item_matches_category(i, {'id':category_id})]
        patches = {}
        if impact['builtIn']:
            row = int(category_id.split('-')[1])
            wb = read_workbook()
            for year in SHEETS:
                for month in range(1, 13):
                    cell = excel_column(month+4)+str(row)
                    if wb[year].get(cell, {}).get('formula'):
                        raise ValueError('El Excel tiene fórmulas en esta categoría: no se ha borrado nada.')
                    patches.setdefault(SHEETS[year], {})[cell] = None
                    ledger['bases'].pop(ledger_key(year, month, row), None)
            ledger.setdefault('deletedBaseCategories', []).append(row)
        else:
            ledger['categories'] = [c for c in ledger.get('categories',[])
                                    if c.get('id') != category_id]
            ledger['customBases'] = {k:v for k,v in ledger.get('customBases',{}).items()
                                     if not k.endswith('-'+category_id)}
        removed_ids = {i['id'] for i in affected}
        ledger['items'] = [i for i in ledger['items'] if i['id'] not in removed_ids]
        # save_pair conserva los dos archivos de forma coordinada y recupera
        # el Excel si falla la escritura del historial.
        save_pair(patches,ledger)
        return {'ok':True,'deleted':impact,'backupPath':str(backup_path),
                'message':'Categoría eliminada. Copia ZIP anterior guardada en Copias_seguridad.'}


def details_total(ledger, year, month, row):
    return sum((money(i['amount']) for i in ledger['items']
                if i['year'] == year and i['month'] == month and i['row'] == row), Decimal('0.00'))


def excel_value_for(ledger, year, month, row):
    base = ledger['bases'][ledger_key(year,month,row)]
    total = (money(base) if base is not None else Decimal('0.00')) + details_total(ledger,year,month,row)
    if total == 0 and base is None and details_total(ledger,year,month,row) == 0:
        return None
    return format(total,'f')


def check_detail_consistency(ledger, wb, year, month, row):
    key = ledger_key(year, month, row)
    if key not in ledger['bases']:
        return
    excel_cell = excel_column(month + 4) + str(row)
    existing = value_of(wb[year], excel_cell)
    intended = excel_value_for(ledger, year, month, row)
    if (existing is None) != (intended is None) or (existing is not None and money(existing) != money(intended)):
        concepto = value_of(wb[year], 'A' + str(row)) or 'gasto ' + str(row)
        raise ValueError(f'Los importes detallados y el Excel no coinciden para {concepto} en {MONTHS[month-1]} de {year}. No he guardado nada. Comprueba Gastos_detallados.json y Cuentas.xlsx (por ejemplo, si cambiaste una celda manualmente).')


def get_details(year, month):
    if year not in SHEETS or month not in range(1,13):
        raise ValueError('Mes o año incorrectos.')
    ledger = load_ledger()
    wb = read_workbook()
    summary = []
    all_categories = categories_for_ledger(ledger, year=year, wb=wb)
    for category in all_categories:
        if not category['builtIn']:
            continue
        row, name = category['row'], category['name']
        key = ledger_key(year,month,row)
        current = value_of(wb[year], excel_column(month+4)+str(row))
        base = ledger['bases'].get(key, current)
        movement = details_total(ledger,year,month,row)
        summary.append({'row':row,'name':name,'base': float(money(base)), 'movement':float(movement),
                        'total':float(money(base)+movement), 'baseExists':base is not None,
                        'warning': key in ledger['bases'] and money(current) != money(base)+movement})
    for c in custom_expenses(ledger, year, month):
        summary.append({'row':0,'categoryId':c['id'],'name':c['name'], 'base':c['base'],
                        'movement':c['movement'], 'total':c['value'],
                        'baseExists':c['baseExists'], 'warning':False,
                        'custom':True, 'group':c['group']})
    items = [copy.deepcopy(i) for i in ledger['items'] if i['year']==year and i['month']==month]
    for item in items:
        cat=category_for_item(item, all_categories)
        item['categoryId']=cat['id']
        item['categoryName']=cat['name']
    items.sort(key=lambda x:(x['date'],x['id']), reverse=True)
    return {'year':year,'month':month,'summary':summary,'items':items,
            'categories':all_categories,
            'expenseGroups':[name for name,_ in GROUPS]}


def write_excel_only(patches, original_checksum):
    # Como en V0.2.2, escribir las celdas pertinentes dejando intacto todo el resto del XLSX.
    temp_name = None
    try:
        fd, temp_name = tempfile.mkstemp(prefix='._Cuentas_',suffix='.xlsx',dir=str(XLSX.parent))
        os.close(fd)
        with ZipFile(XLSX,'r') as source, ZipFile(temp_name,'w') as target:
            target.comment = source.comment
            for info in source.infolist():
                blob = source.read(info.filename)
                if info.filename in patches:
                    blob = patch_cells(blob, patches[info.filename])
                elif info.filename == 'xl/workbook.xml':
                    blob = set_recalculation(blob)
                target.writestr(info,blob)
        with ZipFile(temp_name) as check:
            if check.testzip() is not None:
                raise ValueError('No se ha podido verificar el nuevo Excel.')
        if XLSX.stat().st_mtime_ns != original_checksum:
            raise ValueError('Cuentas.xlsx ha cambiado mientras trabajábamos. Vuelve a intentarlo.')
        os.replace(temp_name,XLSX)
    except PermissionError:
        raise PermissionError('No se pudo guardar. Cierra Cuentas.xlsx si está abierto en Excel y vuelve a intentarlo.')
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def write_ledger_atomic(ledger):
    fd, name = tempfile.mkstemp(prefix='._Gastos_', suffix='.json', dir=str(XLSX.parent))
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(ledger,f,ensure_ascii=False,indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, LEDGER)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def save_pair(patches, ledger=None):
    """Crea copia de ambos archivos; si falla un guardado, restaura Excel."""
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    BACKUPS.mkdir(exist_ok=True)
    xlsx_backup = BACKUPS / f'Cuentas_antes_{stamp}.xlsx'
    shutil.copy2(XLSX,xlsx_backup)
    if ledger is not None and LEDGER.exists():
        shutil.copy2(LEDGER,BACKUPS / f'Gastos_detallados_antes_{stamp}.json')
    checksum = XLSX.stat().st_mtime_ns
    try:
        write_excel_only(patches,checksum)
        if ledger is not None:
            write_ledger_atomic(ledger)
    except Exception:
        # Si falla la escritura del registro, devolver también el Excel a su estado original.
        if XLSX.is_file() and XLSX.read_bytes() != xlsx_backup.read_bytes():
            shutil.copy2(xlsx_backup,XLSX)
        raise


def modify_detail(payload):
    year, month = int(payload.get('year',0)), int(payload.get('month',0))
    if year not in SHEETS or not 1 <= month <= 12:
        raise ValueError('Mes o año incorrectos.')
    action = payload.get('action')
    if action not in ('add','edit','delete'):
        raise ValueError('Acción no permitida.')
    with WRITE_LOCK:
        wb = read_workbook()
        ledger = load_ledger()
        old = None
        if action != 'add':
            id_value = payload.get('id')
            old = next((i for i in ledger['items'] if i['id'] == id_value),None)
            if old is None or old['year'] != year or old['month'] != month:
                raise ValueError('No encuentro ese movimiento en el mes seleccionado.')
        categories = categories_for_ledger(ledger, year=year, wb=wb)
        if action == 'delete':
            affected_rows = {old['row']} if old['row'] > 0 else set()
        else:
            category_id = payload.get('categoryId')
            if category_id is None:
                category_id = f"base-{payload.get('row')}"
            category = next((c for c in categories if c['id'] == category_id), None)
            if category is None:
                raise ValueError('La categoría seleccionada no existe.')
            row = category['row']
            description = str(payload.get('description','')).strip()
            if not 1 <= len(description) <= 120:
                raise ValueError('Escribe una descripción de hasta 120 caracteres.')
            date_text = str(payload.get('date',''))
            try:
                parsed_date = date.fromisoformat(date_text)
            except (ValueError,TypeError):
                raise ValueError('La fecha debe ser válida.')
            if parsed_date.year != year or parsed_date.month != month:
                raise ValueError('La fecha debe corresponder al mes y año seleccionados.')
            amount = parse_amount(payload.get('amount'))
            if amount is None or money(amount) <= 0:
                raise ValueError('Introduce un importe mayor que 0.')
            affected_rows = {r for r in (row,old['row'] if old else 0) if r > 0}
        for r in affected_rows:
            check_detail_consistency(ledger, wb, year, month, r)
            key = ledger_key(year,month,r)
            if key not in ledger['bases']:
                address = excel_column(month+4)+str(r)
                existing = value_of(wb[year],address)
                if wb[year].get(address,{}).get('formula'):
                    raise ValueError('Esta celda contiene una fórmula y no se puede modificar.')
                ledger['bases'][key] = format(money(existing),'f') if existing is not None else None
        if action == 'delete':
            ledger['items'] = [i for i in ledger['items'] if i['id'] != old['id']]
        else:
            item = {'id':old['id'] if old else str(uuid.uuid4()), 'year':year, 'month':month,
                    'date':date_text, 'row':row, 'categoryId':category['id'],
                    'description':description, 'amount':amount}
            if old:
                ledger['items'] = [item if i['id'] == old['id'] else i for i in ledger['items']]
            else:
                ledger['items'].append(item)
        col = excel_column(month+4)
        patches={SHEETS[year]:{col+str(r):excel_value_for(ledger,year,month,r) for r in affected_rows}} if affected_rows else {}
        save_pair(patches,ledger)
    return {'ok':True,'data':readable_info(year,month),'details':get_details(year,month)}


def save_data(payload):
    year, month = int(payload.get('year')), int(payload.get('month'))
    if year not in SHEETS or not 1 <= month <= 12:
        raise ValueError("Año o mes incorrecto.")
    edits = payload.get('edits')
    if not isinstance(edits, dict) or not 0 < len(edits) <= 250:
        raise ValueError("No hay datos para guardar.")
    col = excel_column(month + 4)
    bankcol = excel_column(month + 1)
    patches = {}
    custom_edits = {}
    income_edits = {}
    for key, raw in edits.items():
        if not isinstance(key, str) or ':' not in key:
            raise ValueError('Campo inesperado.')
        area, row_text = key.split(':', 1)
        if area == 'custom':
            if not re.fullmatch(r'[0-9a-f-]{36}', row_text):
                raise ValueError('Categoría desconocida.')
            val = parse_amount(raw)
            if val is not None and money(val) < 0:
                raise ValueError('Los gastos de una categoría no pueden ser negativos.')
            custom_edits[row_text] = val
            continue
        if not row_text.isdigit():
            raise ValueError('Fila no válida.')
        row = int(row_text)
        if area == 'income' and row in (38, 39):
            amount = parse_amount(raw)
            if amount is not None and Decimal(amount) < 0:
                raise ValueError('Los ingresos no pueden ser negativos.')
            income_edits[str(row)] = amount or '0.00'
            continue
        if area == 'expense' and 9 <= row <= 35:
            sheet, address = SHEETS[year], f'{col}{row}'
        elif area == 'income' and row == 40:
            sheet, address = SHEETS[year], f'{col}40'
        elif area == 'bank' and year == 2026 and row in (7, 8):
            sheet, address = BANKS_SHEET, f'{bankcol}{row}'
        else:
            raise ValueError(f'Campo no permitido: {key}')
        amount = parse_amount(raw)
        if area in ('income', 'bank') and amount is not None and Decimal(amount) < 0:
            raise ValueError('Ingresos y saldos bancarios no pueden ser negativos.')
        patches.setdefault(sheet, {})[address] = amount
    with WRITE_LOCK:
        contents = read_workbook()
        ledger = load_ledger()
        deleted = deleted_base_rows(ledger)
        for address in patches.get(SHEETS[year], {}):
            number = int(re.search(r'\d+$',address).group())
            if number in deleted:
                raise ValueError('Esta categoría fue eliminada. No se puede modificar.')
        ledger_modified = False
        if income_edits:
            ledger.setdefault('monthlyIncomes', {}).setdefault(income_key(year,month), {}).update(income_edits)
            ledger_modified = True
        known_custom = {c['id'] for c in categories_for_ledger(ledger) if not c['builtIn']}
        if any(cid not in known_custom for cid in custom_edits):
            raise ValueError('Hay una categoría que no existe en esta contabilidad.')
        for cid, total in custom_edits.items():
            key = custom_key(year, month, cid)
            _, _, movements = custom_amounts(ledger,year,month,cid)
            if total is None and movements:
                raise ValueError('No puedes dejar vacío un gasto con compras detalladas. Elimina antes esas compras.')
            base = money(total) - movements
            if base < 0:
                raise ValueError('El total no puede ser inferior a las compras detalladas. Revisa las anotaciones.')
            ledger.setdefault('customBases', {})[key] = format(base,'f') if total is not None else None
            ledger_modified = True
        for sheet_name, edits_sheet in patches.items():
            current = contents[year] if sheet_name == SHEETS[year] else contents['banks']
            for addr in edits_sheet:
                if current.get(addr, {}).get('formula'):
                    raise ValueError(f'La celda {addr} tiene una fórmula. No se ha modificado.')
        for row in range(9, 36):
            address = col + str(row)
            if address not in patches.get(SHEETS[year],{}):
                continue
            key = ledger_key(year,month,row)
            if key in ledger['bases']:
                check_detail_consistency(ledger,contents,year,month,row)
                new_total = patches[SHEETS[year]][address]
                if new_total is None and details_total(ledger,year,month,row):
                    raise ValueError('No se puede borrar un total que tiene compras detalladas. Modifica el importe o elimina los movimientos.')
                base = money(new_total) - details_total(ledger,year,month,row)
                if base < 0:
                    raise ValueError('El total no puede ser inferior a las compras detalladas. Corrige o elimina una anotación antes de ajustar el importe.')
                ledger['bases'][key] = format(base,'f') if new_total is not None else None
                ledger_modified = True
        save_pair(patches,ledger if ledger_modified else None)
    return {'ok': True, 'message': 'Guardado correcto. Se ha creado una copia de seguridad.',
            'data': readable_info(year, month)}



def migrate_linked_categories():
    """V0.3.2: separar categorías vinculadas a una fila sin duplicar euros.

    Conserva un ZIP completo anterior a la conversión; aborta si las cifras de
    Excel no coinciden con su historial, para no alterar una contabilidad dudosa.
    """
    if not LEDGER.is_file():
        return
    with WRITE_LOCK:
        with LEDGER.open('r', encoding='utf8') as f:
            ledger = json.load(f)
        legacy = [c for c in ledger.get('categories', []) if c.get('row') != 0]
        if not legacy:
            return
        category_ids = {c['id']: c for c in legacy}
        affected = set()
        for item in ledger.get('items', []):
            cid = item.get('categoryId')
            if cid in category_ids:
                legacy_row = category_ids[cid]['row']
                if item['row'] != legacy_row:
                    raise ValueError('Una categoría antigua no coincide con su gasto. No se ha migrado.')
                affected.add((item['year'], item['month'], legacy_row))
        wb = read_workbook()
        # Validar el total original ANTES de reasignar movimientos.
        for year, month, row in affected:
            check_detail_consistency(ledger, wb, year, month, row)
        # ZIP legible desde la función habitual Recuperar copia.
        if PROFILES is None or PROFILES.selected() is None:
            raise ValueError('No se ha seleccionado ninguna contabilidad para proteger la migración.')
        BACKUPS.mkdir(exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        saved = PROFILES.make_backup(PROFILES.selected()['id'])
        backup_path = BACKUPS / ('Antes_de_separar_categorias_' + stamp + '.zip')
        with backup_path.open('xb') as f:
            f.write(saved)
            f.flush()
            os.fsync(f.fileno())
        for c in legacy:
            row = c['row']
            group = next((name for name, rng in GROUPS if row in rng), 'Gastos variables')
            c['row'] = 0
            c['group'] = group
            c.pop('target',None)
        for item in ledger.get('items', []):
            if item.get('categoryId') in category_ids:
                item['row'] = 0
        ledger.setdefault('customBases',{})
        patches = {}
        for year,month,row in affected:
            address = excel_column(month+4)+str(row)
            patches.setdefault(SHEETS[year],{})[address] = excel_value_for(ledger,year,month,row)
        save_pair(patches, ledger)
        print('Categorías de la V0.3.2 separadas. Copia anterior:', backup_path)


def _activate_profile(profile):
    """Ejecutar siempre bajo WRITE_LOCK en handlers; no mezclar rutas activas."""
    global XLSX, LEDGER, BACKUPS
    folder = Path(profile['location'])
    XLSX = folder/'Cuentas.xlsx'
    LEDGER = folder/'Gastos_detallados.json'
    BACKUPS = folder/'Copias_seguridad'
    migrate_linked_categories()
    snapshot_legacy_incomes()


def _check_active(expected):
    current = PROFILES.selected()
    if current is None:
        raise ValueError('Selecciona primero una contabilidad.')
    if not expected or current['id'] != expected:
        raise ValueError('La contabilidad abierta ha cambiado. Vuelve a seleccionarla.')
    _activate_profile(current)
    return current


def _choose_directory():
    """Diálogo nativo de carpetas: no guarda ninguna información fuera sin confirmación."""
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes('-topmost', True)
        chosen = filedialog.askdirectory(parent=root, title='Elegir carpeta para contabilidades')
    finally:
        root.destroy()
    return chosen or None


def _choose_backup_file(default):
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes('-topmost', True)
        chosen = filedialog.asksaveasfilename(parent=root, title='Guardar copia de seguridad',
               defaultextension='.zip', initialfile=default,
               filetypes=[('Copia de Contabilidad Casa','*.zip')])
    finally:
        root.destroy()
    return chosen or None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print('HTTP:', fmt % args)

    def response(self, content: bytes, mimetype: str, filename=None, status=200):
        self.send_response(status)
        self.send_header('Content-Type', mimetype)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'")
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        try:
            self.wfile.write(content)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def json_response(self, data, status=200):
        self.response(json.dumps(data, ensure_ascii=False).encode('utf-8'), 'application/json; charset=utf-8', status=status)

    def do_GET(self):
        u=urlparse(self.path)
        try:
            if u.path in ('/','/index.html'):
                page=(STATIC/'index.html').read_text(encoding='utf-8').replace('__APP_TOKEN__',TOKEN)
                self.response(page.encode('utf-8'), 'text/html; charset=utf-8')
                return
            if u.path in ('/app.css','/app.js'):
                kind='text/css; charset=utf-8' if u.path.endswith('.css') else 'application/javascript; charset=utf-8'
                self.response((STATIC/u.path[1:]).read_bytes(),kind)
                return
            if u.path=='/api/profiles':
                with WRITE_LOCK: self.json_response(PROFILES.list())
                return
            if u.path not in ('/api/info','/api/annual','/api/details','/api/download','/api/categories/impact'):
                self.json_response({'error':'No encontrado.'},404)
                return
            q=parse_qs(u.query)
            with WRITE_LOCK:
                _check_active(q.get('profile',[''])[0])
                if u.path=='/api/info':
                    self.json_response(readable_info(int(q.get('year',[2026])[0]),int(q.get('month',[10])[0])))
                elif u.path=='/api/annual':
                    self.json_response(annual_summary(int(q.get('year',[2026])[0])))
                elif u.path=='/api/details':
                    self.json_response(get_details(int(q.get('year',[2026])[0]),int(q.get('month',[10])[0])))
                elif u.path=='/api/categories/impact':
                    self.json_response(category_impact(q.get('id',[''])[0]))
                else:
                    self.response(XLSX.read_bytes(),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',filename='Cuentas.xlsx')
        except (ValueError,FileNotFoundError,PermissionError,OSError,KeyError) as e:
            self.json_response({'error':str(e)},400)
        except Exception as e:
            print('ERROR GET',repr(e))
            self.json_response({'error':'Error inesperado.'},500)

    def do_POST(self):
        if not hmac.compare_digest(self.headers.get('X-CC-Token',''),TOKEN):
            self.json_response({'error':'Acceso no autorizado.'},403)
            return
        u=urlparse(self.path)
        known={'/api/save','/api/detail','/api/open','/api/exit','/api/profiles/select',
               '/api/profiles/create','/api/profiles/rename','/api/profiles/delete','/api/profiles/folder','/api/backup','/api/backup/native',
               '/api/backup/import','/api/backup/restore','/api/categories/create','/api/categories/move','/api/categories/delete'}
        if u.path not in known:
            self.json_response({'error':'No encontrado.'},404)
            return
        try:
            size=int(self.headers.get('Content-Length','0'))
            binary=u.path in ('/api/backup/import','/api/backup/restore')
            limit=35*1024*1024 if binary else 100000
            if not 0<=size<=limit:
                raise ValueError('La solicitud es demasiado grande.')
            raw=self.rfile.read(size)
            obj={} if binary or not size else json.loads(raw)
            with WRITE_LOCK:
                if u.path=='/api/profiles/folder':
                    self.json_response({'folder':_choose_directory()})
                elif u.path=='/api/profiles/create':
                    self.json_response({'ok':True,'profile':PROFILES.create(obj.get('name',''),obj.get('parent'))})
                elif u.path=='/api/profiles/select':
                    p=PROFILES.select(obj.get('id'))
                    _activate_profile(p)
                    self.json_response({'ok':True,'profile':p})
                elif u.path=='/api/profiles/rename':
                    self.json_response({'ok':True,'profile':PROFILES.rename(obj.get('id'),obj.get('name',''))})
                elif u.path=='/api/profiles/delete':
                    self.json_response(PROFILES.delete(obj.get('id')))
                elif u.path=='/api/backup/import':
                    q=parse_qs(u.query)
                    p=PROFILES.import_backup(raw,q.get('name',[None])[0],q.get('parent',[None])[0])
                    self.json_response({'ok':True,'profile':p})
                elif u.path=='/api/exit':
                    self.json_response({'ok':True})
                    threading.Thread(target=self.server.shutdown,daemon=True).start()
                else:
                    expected=self.headers.get('X-CC-Profile','')
                    active=_check_active(expected)
                    if u.path=='/api/save':
                        self.json_response(save_data(obj))
                    elif u.path=='/api/detail':
                        self.json_response(modify_detail(obj))
                    elif u.path=='/api/categories/create':
                        self.json_response(create_category(obj))
                    elif u.path=='/api/categories/move':
                        self.json_response(move_category(obj))
                    elif u.path=='/api/categories/delete':
                        self.json_response(delete_category(obj))
                    elif u.path=='/api/open':
                        if sys.platform=='win32': os.startfile(str(XLSX))
                        elif sys.platform=='darwin':
                            import subprocess
                            subprocess.Popen(['open',str(XLSX)])
                        else:
                            import subprocess
                            subprocess.Popen(['xdg-open',str(XLSX)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                        self.json_response({'ok':True})
                    elif u.path=='/api/backup':
                        blob=PROFILES.make_backup(active['id'])
                        filename=f"Copia_Contabilidad_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                        self.response(blob,'application/zip',filename=filename)
                    elif u.path=='/api/backup/native':
                        filename=f"Copia_Contabilidad_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                        chosen=_choose_backup_file(filename)
                        if not chosen:
                            self.json_response({'cancelled':True})
                        else:
                            blob=PROFILES.make_backup(active['id'])
                            # Permitir elegir nombre y ruta. Sin sobrescritura silenciosa.
                            dest=Path(chosen).expanduser()
                            if dest.exists():
                                raise ValueError('Ya existe una copia con ese nombre. Elige otro nombre para no sobrescribirla.')
                            _atomic_write_for_native(dest,blob)
                            self.json_response({'ok':True,'path':str(dest)})
                    elif u.path=='/api/backup/restore':
                        self.json_response(PROFILES.restore(active['id'],raw))
        except (ValueError,KeyError,PermissionError,OSError,json.JSONDecodeError) as e:
            self.json_response({'error':str(e)},400)
        except Exception as e:
            print('ERROR POST',repr(e))
            self.json_response({'error':'Error inesperado. No se ha aplicado el cambio.'},500)


def _atomic_write_for_native(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        raise ValueError('El archivo ya existe.')
    fd,n=tempfile.mkstemp(dir=str(path.parent),prefix='._Copia_',suffix='.tmp')
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(data);f.flush();os.fsync(f.fileno())
        if path.exists():
            raise ValueError('El archivo ya existe.')
        os.replace(n,path)
    finally:
        if os.path.exists(n): os.unlink(n)


def main():
    global PROFILES
    print('='*55)
    print(' CONTABILIDAD CASA '+VERSION)
    print('='*55)
    try:
        PROFILES=Profiles(ROOT)
        current=PROFILES.selected()
        if current: _activate_profile(current)
    except Exception as e:
        print('\nERROR:',e)
        input('\nPulsa INTRO para cerrar...')
        sys.exit(1)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    url='http://127.0.0.1:'+str(server.server_address[1])
    print('Interfaz:',url)
    print('Contabilidades:', PROFILES.config_dir)
    print('Se abrirá en tu navegador. Para salir, usa "Cerrar" en la barra superior.')
    if '--no-browser' not in sys.argv:
        threading.Timer(.45,lambda:webbrowser.open(url)).start()
    try: server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt: pass
    finally:
        server.server_close()
        print('Programa cerrado.')

if __name__=='__main__':
    main()
