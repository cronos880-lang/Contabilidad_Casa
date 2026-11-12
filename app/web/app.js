(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const state = {year: new Date().getFullYear(), month: new Date().getMonth()+1, tab: 'expenses', data: null, annual: new Map(), dirty: new Map(), details: null, busy: false, detailBusy:false, editDetailId:null, detailCategory:'base-31', profileId:null, profileName:null, folder:null};
  const euro = new Intl.NumberFormat('es-ES', {style:'currency', currency:'EUR', minimumFractionDigits:2, maximumFractionDigits:2});
  const groups = [
    {label:'Recibos e impuestos', start:9, end:15},
    {label:'Seguros y vivienda', start:16, end:21},
    {label:'Servicios y suscripciones', start:22, end:29},
    {label:'Gastos variables', start:30, end:34},
    {label:'Hipoteca', start:35, end:35},
  ];
  const chartColors = ['#4574df','#22a185','#ec9c3b','#a064d1','#db5f82'];
  const $selectYear = $('year'), $selectMonth = $('month');

  function formAmount(value){return value === null || value === undefined || value === '' ? '' : Number(value).toFixed(2).replace('.', ',')}
  function amount(value) {
    if(value === null || String(value).trim() === '') return null;
    let str = String(value).trim().replace(/[€\s\u00a0]/g,'');
    if(str.includes(',') && str.includes('.')) {
      if(str.lastIndexOf(',') > str.lastIndexOf('.')) str = str.replaceAll('.', '').replace(',', '.');
      else str = str.replaceAll(',', '');
    } else str = str.replace(',', '.');
    if(!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(str)) return NaN;
    const num = Number(str);
    return Number.isFinite(num) && Math.abs(num) < 1000000000 ? num : NaN;
  }
  function display(v){return euro.format(v || 0)}
  function displayCompact(v){
    if(v === null || v === undefined) return '—';
    const abs = Math.abs(v);
    if(abs >= 1000) return new Intl.NumberFormat('es-ES', {maximumFractionDigits:0}).format(v) + ' €';
    return display(v);
  }
  function confirmAbandon(){return !state.dirty.size || confirm('Hay cambios sin guardar. ¿Quieres descartarlos?')}
  function notify(msg, fail=false){
    const toast = $('toast');
    toast.textContent = msg;
    toast.className = 'toast show' + (fail ? ' error' : '');
    clearTimeout(notify.timer);
    notify.timer = setTimeout(() => toast.className = 'toast', 4800);
  }
  async function fetchJSON(url, options){
    if(url.startsWith('/api/') && state.profileId && !url.includes('profile=' ) && !url.startsWith('/api/profiles')) {
      const joiner=url.includes('?')?'&':'?';
      if(!options || !options.method || options.method==='GET') url+=joiner+'profile='+encodeURIComponent(state.profileId);
    }
    const response = await fetch(url, options);
    let result;
    try { result = await response.json(); } catch { throw new Error('El servidor no ha respondido correctamente.'); }
    if(!response.ok) throw new Error(result.error || 'Ha ocurrido un error.');
    return result;
  }
  function post(url, body){
    return fetchJSON(url, {
      method:'POST',
      headers:{'Content-Type':'application/json', 'X-CC-Token': window.APP_TOKEN || '', 'X-CC-Profile':state.profileId || ''},
      body: JSON.stringify(body || {})
    });
  }
  function status(text, mode=''){
    $('saveStatus').textContent = text;
    $('statusDot').className = 'status-dot' + (mode ? ' ' + mode : '');
  }
  function refreshStatus(){
    const save = $('save');
    const savebar = document.querySelector('.savebar');
    if(state.tab === 'charts' || state.tab === 'details') {
      savebar.hidden = true;
      return;
    }
    savebar.hidden = false;
    if(state.busy){
      save.disabled = true;
      status('Guardando cambios...', 'changed');
      return;
    }
    if(state.dirty.size){
      save.disabled = false;
      status(`Hay ${state.dirty.size} cambio${state.dirty.size===1?'':'s'} pendiente${state.dirty.size===1?'':'s'}`, 'changed');
    } else {
      save.disabled = true;
      status('Sin cambios pendientes');
    }
  }

  function svgEl(tag, attrs={}){
    const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.entries(attrs).forEach(([k,v]) => el.setAttribute(k, v));
    return el;
  }
  function chartCard(title, hint){
    const card = document.createElement('section');
    card.className = 'chart-card';
    const head = document.createElement('div');
    head.className = 'chart-head';
    head.innerHTML = `<h3>${title}</h3><p>${hint}</p>`;
    const body = document.createElement('div');
    body.className = 'chart-body';
    card.append(head, body);
    return {card, body};
  }
  function emptyChart(message){
    const box = document.createElement('div');
    box.className = 'chart-empty';
    box.textContent = message;
    return box;
  }

  function entry(label, value, key, options={}){
    const row = document.createElement('div');
    row.className = 'entry-row';
    row.dataset.key = key;
    const name = document.createElement('div');
    name.className = 'entry-label';
    name.textContent = label;
    const wrap = document.createElement('div');
    wrap.className = 'input-wrap';
    const input = document.createElement('input');
    input.type = 'text';
    input.inputMode = 'decimal';
    input.className = 'money-input';
    input.value = state.dirty.has(key) ? state.dirty.get(key) : formAmount(value);
    if(options.readonly){
      input.readOnly = true;
      input.disabled = true;
      input.title = 'Este valor es solo informativo en esta versión.';
    }
    if(state.dirty.has(key)) input.classList.add('modified');
    input.addEventListener('input', () => {
      if(options.readonly) return;
      const raw = input.value.trim();
      const parsed = amount(raw);
      const invalid = raw !== '' && Number.isNaN(parsed);
      input.classList.toggle('invalid', invalid);
      if(raw === formAmount(value) || (raw === '' && (value === null || value === undefined || value === ''))) {
        state.dirty.delete(key);
        input.classList.remove('modified');
      } else {
        state.dirty.set(key, raw);
        input.classList.add('modified');
      }
      refreshStatus();
      renderMetrics();
      if(state.tab === 'banks') renderBankSummary();
      if(state.tab === 'incomes') renderIncomeSummary();
    });
    wrap.append(input);
    const euroSign = document.createElement('span');
    euroSign.className = 'euro';
    euroSign.textContent = '€';
    wrap.append(euroSign);
    row.append(name, wrap);
    return row;
  }
  function addNotice(text, variant=''){
    const note = document.createElement('div');
    note.className = 'notice' + (variant ? ' ' + variant : '');
    note.innerHTML = text;
    $('content').appendChild(note);
  }
  function addSummary(label, value, kind){
    const box = document.createElement('div');
    box.className = 'summary-box';
    box.dataset.summary = kind;
    const a = document.createElement('span');
    a.textContent = label;
    const b = document.createElement('strong');
    b.textContent = value === null ? 'Pendiente' : display(value);
    box.append(a,b);
    $('content').appendChild(box);
  }
  function rowValue(area, row, fallback){
    const id = `${area}:${row}`;
    if(state.dirty.has(id)) return amount(state.dirty.get(id));
    return fallback;
  }
  function liveTotals(){
    const d = state.data;
    if(!d) return {expenses:0, incomes:0, extras:0, available:0, count:0};
    const exp = d.categories.map(c => rowValue('expense', c.row, c.value));
    const inc = d.incomes.map(c => rowValue('income', c.row, c.value));
    const custom = (d.customExpenseCategories || []).map(c => rowValue('custom', c.id, c.value));
    const e = [...exp,...custom].reduce((sum,v)=>sum+(Number.isFinite(v)?v:0),0);
    const i = inc.reduce((sum,v)=>sum+(Number.isFinite(v)?v:0),0);
    return {
      expenses:e,
      incomes:i,
      extras: rowValue('income',40,(d.incomes.find(x=>x.row===40)||{}).value) || 0,
      available:i-e,
      count: [...exp,...custom].filter(v=>v!==null && !Number.isNaN(v)).length,
    };
  }
  function renderMetrics(){
    if(!state.data) return;
    const t = liveTotals();
    $('incomeValue').textContent = display(t.incomes);
    $('expenseValue').textContent = display(t.expenses);
    $('availableValue').textContent = display(t.available);
    $('expenseCount').textContent = `${t.count} de ${state.data.categories.length + (state.data.customExpenseCategories||[]).length} conceptos con importe`;
    $('incomeInfo').textContent = t.extras ? `Incluye extras del mes: ${display(t.extras)}` : 'Ingresos menos gastos';
  }
  function renderIncomeSummary(){
    const incomeSummary = document.querySelector('[data-summary="incomes"] strong');
    if(incomeSummary) incomeSummary.textContent = display(liveTotals().incomes);
  }
  function renderBankSummary(){
    const bankSummary = document.querySelector('[data-summary="banks"] strong');
    if(bankSummary){
      const vals = state.data.banks.map(x=>rowValue('bank',x.row,x.value));
      bankSummary.textContent = vals.length===2 && vals.every(x=>x!==null&&x!==0&&Number.isFinite(x)) ? display(vals[0]+vals[1]) : 'Pendiente';
    }
  }

  async function load(){
    try{
      $('content').innerHTML = '<div class="empty-state"><div class="empty-icon">⌛</div><div>Cargando datos...</div></div>';
      state.data = await fetchJSON(`/api/info?year=${state.year}&month=${state.month}`);
      await ensureAnnualIfNeeded();
      await ensureDetailsIfNeeded(true);
      render();
    }catch(error){
      notify(error.message, true);
      $('content').innerHTML = `<div class="empty-state"><div class="empty-icon">⚠</div><div>${error.message}</div></div>`;
    }
  }
  async function ensureAnnualIfNeeded(force=false){
    if(state.tab !== 'charts') return;
    if(!force && state.annual.has(state.year)) return;
    const annual = await fetchJSON(`/api/annual?year=${state.year}`);
    state.annual.set(state.year, annual);
  }

  async function ensureDetailsIfNeeded(force=false){
    if(state.tab !== 'details') return;
    if(!force && state.details?.year === state.year && state.details?.month === state.month) return;
    state.details = await fetchJSON(`/api/details?year=${state.year}&month=${state.month}`);
  }
  const categoryLabels = {31:'Comida',32:'Extras',33:'Vacaciones'};
  function defaultDetailDate(){
    const now=new Date();
    const yr=state.year, mo=state.month;
    const day=(now.getFullYear()===yr && now.getMonth()+1===mo) ? now.getDate() : 1;
    return `${yr}-${String(mo).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
  }
  function makeTag(tag,text,className=''){
    const el=document.createElement(tag);el.textContent=text;if(className)el.className=className;return el;
  }
  function editableDetail(item){
    state.editDetailId=item.id;
    $('detailRow').value=item.categoryId;
    $('detailDate').value=item.date;
    $('detailDescription').value=item.description;
    $('detailAmount').value=formAmount(item.amount);
    $('detailSubmit').textContent='Guardar corrección';
    $('detailCancel').hidden=false;
    $('detailDescription').focus();
  }
  function clearDetailForm(){
    state.editDetailId=null;
    $('detailRow').value=state.detailCategory;
    $('detailDate').value=defaultDetailDate();
    $('detailDescription').value='';
    $('detailAmount').value='';
    $('detailSubmit').textContent='Guardar compra';
    $('detailCancel').hidden=true;
  }
  async function detailAction(payload){
    if(state.detailBusy)return;
    state.detailBusy=true;
    const button=$('detailSubmit');if(button)button.disabled=true;
    try {
      const res=await post('/api/detail', {year:state.year,month:state.month,...payload});
      state.data=res.data;
      state.details=res.details;
      state.annual.delete(state.year);
      render();
      notify('Anotación guardada y totales actualizados.');
    } catch(error) {
      notify(error.message,true);
    } finally {
      state.detailBusy=false;
      if($('detailSubmit'))$('detailSubmit').disabled=false;
    }
  }
  function renderDetails(){
    $('sectionTitle').textContent=`Anotar compras · ${state.data.monthName} ${state.year}`;
    $('sectionHint').textContent='Apunta compras y crea nuevas categorías cuando las necesites.';
    $('panelTools').hidden=true;
    const data=state.details;
    if(!data){ $('content').appendChild(emptyChart('No se pudieron cargar las anotaciones.'));return; }
    // Los totales por categoría ya se muestran en «Gastos del mes».
    // En «Anotar compras» solo se enseña el formulario, la gestión de
    // categorías y el historial. Conservamos los avisos de conflicto reales.
    const warnings=(data.summary || []).filter(cat=>cat.warning);
    if(warnings.length){
      $('content').appendChild(makeTag('div',
        `Revisa estas categorías antes de añadir compras: ${warnings.map(cat=>cat.name).join(', ')}. El Excel se modificó fuera del programa.`,
        'detail-conflict-warning'));
    }
    const form=document.createElement('form');form.id='detailForm';form.className='detail-form';
    const title=makeTag('h3','Añadir un gasto');form.appendChild(title);
    const controls=document.createElement('div');controls.className='detail-fields';
    function labelField(title,control){
      const label=document.createElement('label');label.className='detail-field';
      label.appendChild(makeTag('span',title));label.appendChild(control);return label;
    }
    const row=document.createElement('select');row.id='detailRow';row.required=true;
    data.categories.forEach(c=>{const option=document.createElement('option');option.value=c.id;
      option.textContent=c.builtIn ? c.name : `${c.name} · ${c.group}`;row.appendChild(option)});
    row.value=state.detailCategory;
    if(!row.value || row.selectedIndex<0){row.value='base-31';state.detailCategory='base-31';}
    row.addEventListener('change',()=>{state.detailCategory=row.value});
    const date=document.createElement('input');date.id='detailDate';date.type='date';date.required=true;
    date.min=`${state.year}-${String(state.month).padStart(2,'0')}-01`;
    const last=new Date(state.year,state.month,0).getDate();
    date.max=`${state.year}-${String(state.month).padStart(2,'0')}-${String(last).padStart(2,'0')}`;
    date.value=defaultDetailDate();
    const description=document.createElement('input');description.id='detailDescription';description.type='text';description.maxLength=120;description.placeholder='Ej.: Mercadona';description.required=true;
    const value=document.createElement('input');value.id='detailAmount';value.type='text';value.inputMode='decimal';value.placeholder='0,00';value.required=true;
    controls.append(labelField('Categoría',row),labelField('Fecha',date),labelField('Descripción',description),labelField('Importe (€)',value));
    form.appendChild(controls);
    const actions=document.createElement('div');actions.className='detail-actions';
    const submit=document.createElement('button');submit.type='submit';submit.id='detailSubmit';submit.className='save-button';submit.textContent='Guardar compra';
    const cancel=document.createElement('button');cancel.type='button';cancel.id='detailCancel';cancel.className='detail-secondary';cancel.textContent='Cancelar corrección';cancel.hidden=true;cancel.addEventListener('click',clearDetailForm);
    actions.append(submit,cancel);form.appendChild(actions);
    form.addEventListener('submit',async event=>{
      event.preventDefault();
      if(state.detailBusy)return;
      const num=amount(value.value);
      if(!Number.isFinite(num) || num<=0){notify('Introduce un importe válido mayor que cero.',true);return;}
      if(!description.value.trim()){notify('Escribe dónde hiciste la compra.',true);return;}
      const payload={action:state.editDetailId?'edit':'add',categoryId:row.value,date:date.value,description:description.value.trim(),amount:value.value};
      if(state.editDetailId)payload.id=state.editDetailId;
      await detailAction(payload);
    });
    $('content').appendChild(form);
    const categoryBox=document.createElement('form');categoryBox.className='custom-category-form';
    categoryBox.innerHTML='<h3>Crear una categoría de gastos</h3><p>Ejemplo: Farmacia. Selecciona el grupo en el que aparecerá como gasto independiente, con importe y compras propios.</p>';
    const fields=document.createElement('div');fields.className='custom-category-fields';
    const catInput=document.createElement('input');catInput.type='text';catInput.maxLength=55;catInput.placeholder='Ej.: Farmacia';catInput.required=true;
    catInput.setAttribute('aria-label','Nombre de la nueva categoría');catInput.style.textTransform='uppercase';
    const expenseTarget=document.createElement('select');expenseTarget.setAttribute('aria-label','Grupo de gastos donde aparecerá');
    data.expenseGroups.forEach(name=>{const option=document.createElement('option');option.value=name;option.textContent=name;expenseTarget.appendChild(option)});
    expenseTarget.value='Gastos variables';
    const createButton=makeTag('button','Añadir categoría','detail-secondary');createButton.type='submit';
    fields.append(catInput,expenseTarget,createButton);categoryBox.appendChild(fields);
    categoryBox.addEventListener('submit',async e=>{
      e.preventDefault();
      if(state.detailBusy)return;
      createButton.disabled=true;
      try{
        const result=await post('/api/categories/create',{name:catInput.value.trim().toLocaleUpperCase('es-ES'),group:expenseTarget.value});
        state.detailCategory=result.category.id;
        state.details=await fetchJSON(`/api/details?year=${state.year}&month=${state.month}`);
        state.data=await fetchJSON(`/api/info?year=${state.year}&month=${state.month}`);
        state.annual.delete(state.year);
        render();
        notify(`Categoría «${result.category.name}» creada en «${result.category.group}».`);
      }catch(err){notify(err.message,true)}
      finally{createButton.disabled=false;}
    });
    $('content').appendChild(categoryBox);
    const customCategories=data.categories.filter(c=>!c.builtIn);
    if(customCategories.length){
      const moveBox=document.createElement('form');moveBox.className='custom-category-form category-move-box';
      moveBox.innerHTML='<h3>Cambiar categoría de grupo</h3><p>Mueve una categoría existente a otro apartado de Gastos. Se conservarán sus importes y anotaciones.</p>';
      const fields=document.createElement('div');fields.className='custom-category-fields';
      const catSelect=document.createElement('select');catSelect.setAttribute('aria-label','Categoría existente');
      customCategories.forEach(c=>{const o=document.createElement('option');o.value=c.id;o.textContent=c.name;catSelect.append(o)});
      const groupSelect=document.createElement('select');groupSelect.setAttribute('aria-label','Nuevo grupo de gastos');
      data.expenseGroups.forEach(g=>{const o=document.createElement('option');o.value=g;o.textContent=g;groupSelect.append(o)});
      const syncGroup=()=>{const c=customCategories.find(x=>x.id===catSelect.value);if(c)groupSelect.value=c.group;};
      catSelect.addEventListener('change',syncGroup);syncGroup();
      const moveButton=makeTag('button','Cambiar grupo','detail-secondary');moveButton.type='submit';
      fields.append(catSelect,groupSelect,moveButton);moveBox.append(fields);
      moveBox.addEventListener('submit',async e=>{
        e.preventDefault();if(state.detailBusy)return;
        moveButton.disabled=true;
        try{
          await post('/api/categories/move',{id:catSelect.value,group:groupSelect.value});
          state.details=await fetchJSON(`/api/details?year=${state.year}&month=${state.month}`);
          state.data=await fetchJSON(`/api/info?year=${state.year}&month=${state.month}`);
          state.annual.delete(state.year);render();
          notify('Categoría movida al grupo seleccionado. Sus importes se conservan.');
        }catch(err){notify(err.message,true)}finally{moveButton.disabled=false;}
      });
      $('content').appendChild(moveBox);
      // Solo se pueden borrar las categorías creadas por el usuario.
      const deleteBox=document.createElement('div');deleteBox.className='custom-category-form category-delete-box';
      deleteBox.innerHTML='<h3>Eliminar una categoría</h3><p>Si ya tiene compras o importes, también se quitarán de los gastos y gráficas de todos los años. Antes se guardará una copia completa recuperable de esta contabilidad.</p>';
      const deleteFields=document.createElement('div');deleteFields.className='custom-category-fields';
      const deleteSelect=document.createElement('select');deleteSelect.setAttribute('aria-label','Categoría que quieres eliminar');
      customCategories.forEach(c=>{const option=document.createElement('option');option.value=c.id;option.textContent=c.name;deleteSelect.appendChild(option)});
      const deleteButton=makeTag('button','Eliminar categoría','detail-remove');deleteButton.type='button';
      deleteFields.append(deleteSelect,deleteButton);deleteBox.append(deleteFields);
      deleteButton.addEventListener('click',async ()=>{
        if(state.detailBusy || state.dirty.size){
          notify('Guarda primero los cambios pendientes antes de eliminar una categoría.',true);return;
        }
        const target=customCategories.find(c=>c.id===deleteSelect.value);
        if(!target)return;
        deleteButton.disabled=true;state.detailBusy=true;
        try{
          const impact=await fetchJSON(`/api/categories/impact?profile=${encodeURIComponent(state.profileId)}&id=${encodeURIComponent(target.id)}`);
          const summary=`Categoría: ${impact.name}\nCompras que se eliminarán: ${impact.movements}\nImporte total que desaparecerá de Gastos: ${display(impact.amount)}\n\nSe guardará ANTES una copia completa ZIP para poder recuperarla. Las otras categorías no se tocarán.\n\n¿Quieres continuar?`;
          if(!confirm(summary))return;
          const typed=prompt(`Para confirmar, escribe exactamente el nombre: ${impact.name}`);
          if(typed===null)return;
          if(typed!==impact.name){notify('Nombre incorrecto. No se ha eliminado nada.',true);return;}
          const result=await post('/api/categories/delete',{id:target.id,confirmName:typed});
          if(state.detailCategory===target.id)state.detailCategory='base-31';
          state.editDetailId=null;
          state.details=await fetchJSON(`/api/details?year=${state.year}&month=${state.month}`);
          state.data=await fetchJSON(`/api/info?year=${state.year}&month=${state.month}`);
          state.annual.clear();render();
          notify(`Categoría ${target.name} eliminada. Copia previa conservada en Copias_seguridad.`);
        }catch(err){notify(err.message,true)}finally{
          state.detailBusy=false;
          if(deleteButton.isConnected)deleteButton.disabled=false;
        }
      });
      $('content').appendChild(deleteBox);
    }
    const history=document.createElement('section');history.className='detail-history';
    history.append(makeTag('h3',`Compras anotadas (${data.items.length})`));
    if(!data.items.length)history.append(makeTag('p','Todavía no hay compras individuales apuntadas en este mes.','detail-muted'));
    for(const item of data.items){
      const rowEl=document.createElement('div');rowEl.className='detail-history-row';
      const info=document.createElement('div');info.className='detail-history-info';
      const dateText=item.date.split('-').reverse().join('/');
      info.append(makeTag('strong',item.description),makeTag('span',`${dateText} · ${item.categoryName || categoryLabels[item.row] || 'Gasto'}`,'detail-muted'));
      const value=makeTag('strong',display(Number(item.amount)),'detail-history-amount');
      const edit=document.createElement('button');edit.type='button';edit.className='detail-secondary';edit.textContent='Editar';edit.addEventListener('click',()=>editableDetail(item));
      const del=document.createElement('button');del.type='button';del.className='detail-remove';del.textContent='Eliminar';del.addEventListener('click',()=>{
        if(confirm(`¿Eliminar «${item.description}» de ${display(Number(item.amount))}? El total del mes se corregirá.`))detailAction({action:'delete',id:item.id});
      });
      rowEl.append(info,value,edit,del);history.append(rowEl);
    }
    $('content').appendChild(history);
  }

  function renderExpenses(){
    $('sectionTitle').textContent = `Gastos de ${state.data.monthName.toLowerCase()} de ${state.year}`;
    $('sectionHint').textContent = 'Introduce los importes de ese mes. Deja el campo vacío si todavía no lo has apuntado.';
    $('panelTools').hidden = false;
    $('search').value = '';
    for(const group of groups){
      const items = state.data.categories.filter(c=>c.row>=group.start && c.row<=group.end);
      const section = document.createElement('div');
      section.className = 'group';
      const title = document.createElement('div');
      title.className = 'group-title';
      title.textContent = group.label;
      section.appendChild(title);
      items.forEach(c=>{
        const el=entry(c.name,c.value,'expense:'+c.row,{readonly:c.formula});
        el.dataset.search=(c.name||'').toLocaleLowerCase('es');
        section.appendChild(el);
      });
      const own=(state.data.customExpenseCategories||[]).filter(c=>c.group===group.label);
      own.forEach(c=>{
        const el=entry(c.name,c.value,'custom:'+c.id);
        el.dataset.search=c.name.toLocaleLowerCase('es');
        section.appendChild(el);
      });
      $('content').appendChild(section);
    }
  }
  function renderIncomes(){
    $('sectionTitle').textContent = `Ingresos de ${state.data.monthName.toLowerCase()} de ${state.year}`;
    $('sectionHint').textContent = 'Cada importe corresponde al mes elegido. Corregir un mes no cambia los demás.';
    $('panelTools').hidden = true;
    const regular = document.createElement('div');
    regular.className = 'group';
    regular.innerHTML = `<div class="group-title">Ingresos de ${state.data.monthName.toLowerCase()}</div>`;
    state.data.incomes.filter(x=>x.row===39 || x.row===38).forEach(x=>regular.appendChild(entry(x.name,x.value,'income:'+x.row,{nonnegative:true})));
    $('content').appendChild(regular);
    const variable = document.createElement('div');
    variable.className = 'group';
    variable.innerHTML = `<div class="group-title">Ingreso variable de ${state.data.monthName.toLowerCase()}</div>`;
    state.data.incomes.filter(x=>x.scope==='extra').forEach(x=>variable.appendChild(entry('Ingreso extra',x.value,'income:'+x.row,{nonnegative:true})));
    $('content').appendChild(variable);
    if(state.year===2027) addNotice('La aplicación suma los ingresos habituales y los extras. Algunas fórmulas antiguas del Excel de 2027 no incluyen todavía todos esos importes.', 'warning');
    addSummary('Ingresos de este mes', liveTotals().incomes, 'incomes');
  }
  function renderBanks(){
    $('sectionTitle').textContent = `Cuentas bancarias · ${state.data.monthName} ${state.year}`;
    $('sectionHint').textContent = 'Apunta el saldo de cada banco para ver cómo evolucionan tus ahorros.';
    $('panelTools').hidden = true;
    if(!state.data.bankAvailable){
      addNotice('De momento el seguimiento mensual de bancos solo está preparado en tu Excel para 2026.', 'warning');
      return;
    }
    addNotice('Si un mes está pendiente, déjalo vacío. Un 0 puede dar a entender que el mes ya está cerrado.');
    const group = document.createElement('div');
    group.className = 'group';
    group.innerHTML = '<div class="group-title">Saldos de fin de mes</div>';
    state.data.banks.forEach(x=>group.appendChild(entry(x.name,x.value,'bank:'+x.row,{bank:true,nonnegative:true})));
    $('content').appendChild(group);
    const b = state.data.banks.map(x=>rowValue('bank',x.row,x.value));
    const ready = b.length===2 && b.every(x=>x!==null && x!==0 && Number.isFinite(x));
    addSummary('Saldo total de las dos cuentas', ready ? b[0]+b[1] : null, 'banks');
  }

  function summaryCard(label, value, sub=''){
    const card = document.createElement('div');
    card.className = 'annual-card';
    card.innerHTML = `<div class="annual-label">${label}</div><div class="annual-value">${value}</div>${sub?`<div class="annual-sub">${sub}</div>`:''}`;
    return card;
  }
  function renderAnnualHeader(data){
    const wrap = document.createElement('div');
    wrap.className = 'annual-summary';
    wrap.append(
      summaryCard('Meses registrados', `${data.monthsRecorded} / 12`, 'Solo cuentan los meses realmente apuntados'),
      summaryCard('Ingresos acumulados', display(data.totals.incomes), 'Suma de los meses registrados'),
      summaryCard('Gastos acumulados', display(data.totals.expenses), 'Suma de los meses registrados'),
      summaryCard('Balance acumulado', display(data.totals.available), data.totals.available >= 0 ? 'Lo que ha sobrado hasta ahora' : 'Lo que ha faltado hasta ahora')
    );
    if(data.bankAvailable && data.totals.bankTotal !== null){
      wrap.append(summaryCard('Último saldo en bancos', display(data.totals.bankTotal), 'Suma de La Caixa y Sabadell'));
    }
    $('content').appendChild(wrap);
  }
  // Diferencia respecto al mes inmediatamente anterior, nunca respecto a un mes saltado.
  // No comparamos importes bancarios parciales si falta una de las dos cuentas.
  function previousMonthBalanceDifference(months, index){
    if(index<1) return null; // Enero: sin comparación dentro del año.
    const before=months[index-1], now=months[index];
    const complete=m=>m && Number.isFinite(m.bankTotal)
      && Number.isFinite(m.bankCaixa) && m.bankCaixa>0
      && Number.isFinite(m.bankSabadell) && m.bankSabadell>0;
    if(!complete(before)||!complete(now))return null;
    // Euros en céntimos para evitar valores como 0,009999.
    return (Math.round(now.bankTotal*100)-Math.round(before.bankTotal*100))/100;
  }
  function deltaLabel(delta){
    const val=new Intl.NumberFormat('es-ES', {minimumFractionDigits:0,maximumFractionDigits:2}).format(Math.abs(delta));
    return (delta>0?'+':delta<0?'−':'')+val+' €';
  }

  // Mismo tipo de gráfica que Hoja2 del Excel: tres columnas por mes.
  function renderExcelBankMonths(data){
    const months=data.months;
    const {card,body}=chartCard('1. Evolución de las cuentas bancarias',
      'Tres barras por mes: cada cuenta y su total. Debajo, la diferencia del total frente al mes anterior (verde si sube y rojo si baja).');
    if(!data.bankAvailable){
      body.appendChild(emptyChart('Tu Excel todavía no tiene saldos bancarios mensuales para este año.'));
      return card;
    }
    const valid=months.filter(m=>m.bankTotal!==null);
    if(!valid.length){body.appendChild(emptyChart('Todavía no hay saldos bancarios registrados.'));return card;}
    const max=Math.max(1,...valid.map(m=>m.bankTotal));
    const width=900,height=335,left=58,right=16,top=18,bottom=82;
    const pw=width-left-right,ph=height-top-bottom,slot=pw/12;
    const barW=Math.min(17,slot*.22),gap=2;
    const colors=['#4169bb','#22a185','#e2a347'];
    const labels=[...(data.bankNames||['Cuenta 1','Cuenta 2']),'Total de cuentas'];
    const svg=svgEl('svg',{viewBox:`0 0 ${width} ${height}`,class:'chart-svg',role:'img','aria-label':'Saldos bancarios mensuales por cuenta y total'});
    for(let t=0;t<=4;t++){
      const y=top+ph*t/4;
      svg.append(svgEl('line',{x1:left,y1:y,x2:width-right,y2:y,stroke:'#e5eaf2'}));
      const v=svgEl('text',{x:left-8,y:y+4,'text-anchor':'end',class:'axis-text'});
      v.textContent=new Intl.NumberFormat('es-ES',{maximumFractionDigits:0}).format(max*(4-t)/4);
      svg.append(v);
    }
    months.forEach((m,i)=>{
      const center=left+(i+.5)*slot;
      const label=svgEl('text',{x:center,y:height-54,'text-anchor':'middle',class:'axis-text'});
      label.textContent=m.short;svg.append(label);
      const delta=previousMonthBalanceDifference(months,i);
      const text=m.bankTotal===null?'Pend.':delta===null?'—':deltaLabel(delta);
      const kind=delta===null?'month-delta-neutral':delta>0?'month-delta-positive':delta<0?'month-delta-negative':'month-delta-neutral';
      const change=svgEl('text',{x:center,y:height-26,'text-anchor':'middle',class:kind,
        'font-size':text.length>13?'9':text.length>10?'10':'11'});
      change.textContent=text;
      const tip=svgEl('title');
      tip.textContent=m.bankTotal===null
        ?`${m.name}: pendiente de introducir los saldos`
        :delta===null
          ?`${m.name}: no hay dos meses consecutivos completos para comparar`
          :`${m.name} respecto a ${months[i-1].name}: ${delta>0?'+':''}${display(delta)} de variación en el saldo total`;
      change.append(tip);
      svg.append(change);
      if(m.bankTotal===null)return;
      [m.bankCaixa,m.bankSabadell,m.bankTotal].forEach((v,k)=>{
        const h=Math.max(v>0?2:0,(v||0)/max*ph);
        const rect=svgEl('rect',{x:center-(1.5*barW+gap)+k*(barW+gap),y:top+ph-h,width:barW,height:h,rx:2,fill:colors[k]});
        const tooltip=svgEl('title'); tooltip.textContent=`${m.name} · ${labels[k]}: ${display(v)}`;rect.append(tooltip);
        svg.append(rect);
      });
    });
    body.append(svg);
    const legend=document.createElement('div');legend.className='chart-legend';
    labels.forEach((x,i)=>{
      const span=document.createElement('span');
      const swatch=document.createElement('i');swatch.className='legend-dot';swatch.style.background=colors[i];
      span.append(swatch,document.createTextNode(x));
      legend.append(span);
    });body.append(legend);
    return card;
  }

  // Equivalente a la segunda gráfica del Excel: barras horizontales por año.
  function renderExcelYearComparison(data){
    const {card,body}=chartCard('2. Comparación entre años',
      'Como en el Excel: compara las cuentas y su total al inicio de cada año registrado.');
    const compare=(data.bankComparison||[]).filter(r=>r.caixa>0||r.sabadell>0);
    if(!compare.length){body.appendChild(emptyChart('Aún no hay saldos iniciales por año para comparar.'));return card;}
    const colors=['#4169bb','#22a185','#e2a347','#a064d1'];
    const labels=[...(data.bankNames||['Cuenta 1','Cuenta 2']),'Total'];
    const values=compare.map(x=>[x.caixa,x.sabadell,x.caixa+x.sabadell]);
    const max=Math.max(1,...values.flat());
    const width=850,left=108,right=65,top=20,rowGap=94,height=top+compare.length*rowGap+26,pw=width-left-right;
    const svg=svgEl('svg',{viewBox:`0 0 ${width} ${height}`,class:'chart-svg',role:'img','aria-label':'Comparación horizontal de bancos por año'});
    compare.forEach((row,j)=>{
      const base=top+j*rowGap;
      const yLabel=svgEl('text',{x:10,y:base+30,class:'year-axis-text'});yLabel.textContent=row.year;
      svg.append(yLabel);
      values[j].forEach((v,k)=>{
        const y=base+k*24;
        const label=svgEl('text',{x:left-8,y:y+14,'text-anchor':'end',class:'axis-text'});
        label.textContent=labels[k];svg.append(label);
        const w=(Math.max(0,v)/max)*pw;
        const bar=svgEl('rect',{x:left,y:y+1,width:w,height:17,rx:3,fill:colors[k]});
        const tt=svgEl('title');tt.textContent=`${row.year} · ${labels[k]}: ${display(v)}`;bar.append(tt);svg.append(bar);
        const amount=svgEl('text',{x:Math.min(width-58,left+w+7),y:y+15,class:'axis-text'});
        amount.textContent=new Intl.NumberFormat('es-ES',{maximumFractionDigits:0}).format(v);
        svg.append(amount);
      });
    });
    body.append(svg);
    return card;
  }

  function renderDonutChart(groupsData){
    const clean = groupsData.filter(g=>g.value>0).sort((a,b)=>b.value-a.value);
    const {card, body} = chartCard('3. ¿En qué se va el dinero?', 'Resumen del gasto acumulado por grandes bloques. Sirve para ver de un vistazo qué pesa más en casa.');
    if(!clean.length){ body.appendChild(emptyChart('Todavía no hay gastos acumulados para repartir por bloques.')); return card; }
    const total = clean.reduce((sum,g)=>sum+g.value,0);
    const wrap = document.createElement('div');
    wrap.className = 'donut-layout';
    const svg = svgEl('svg',{viewBox:'0 0 240 240', class:'donut-svg', role:'img', 'aria-label':'Reparto del gasto anual'});
    const cx=120, cy=120, r=78, circ=2*Math.PI*r;
    let offset = 0;
    clean.forEach((g,i)=>{
      const frac = g.value/total;
      const len = frac*circ;
      const circle = svgEl('circle',{cx,cy,r,fill:'none',stroke:chartColors[i%chartColors.length],'stroke-width':'28','stroke-linecap':'butt',transform:'rotate(-90 120 120)','stroke-dasharray':`${len} ${circ-len}`,'stroke-dashoffset':`${-offset}`});
      const title = document.createElementNS('http://www.w3.org/2000/svg','title');
      title.textContent = `${g.name}: ${display(g.value)} (${(frac*100).toFixed(1)}%)`;
      circle.appendChild(title);
      svg.appendChild(circle);
      offset += len;
    });
    svg.appendChild(svgEl('circle',{cx,cy,r:'49',fill:'white'}));
    const centerTop = svgEl('text',{x:120,y:112,'text-anchor':'middle',class:'donut-center-title'}); centerTop.textContent='Total';
    const centerVal = svgEl('text',{x:120,y:134,'text-anchor':'middle',class:'donut-center-value'}); centerVal.textContent=displayCompact(total);
    svg.append(centerTop, centerVal);
    wrap.appendChild(svg);
    const legend = document.createElement('div');
    legend.className = 'donut-legend';
    clean.forEach((g,i)=>{
      const item = document.createElement('div');
      const pct = total ? (g.value/total*100).toFixed(1) : '0.0';
      item.innerHTML = `<span class="legend-name"><i class="legend-dot" style="background:${chartColors[i%chartColors.length]}"></i>${g.name}</span><strong>${display(g.value)}</strong><small>${pct}%</small>`;
      legend.appendChild(item);
    });
    wrap.appendChild(legend);
    body.appendChild(wrap);
    return card;
  }
  function renderCharts(){
    const annual = state.annual.get(state.year);
    $('sectionTitle').textContent = `Gráficas anuales · ${state.year}`;
    $('sectionHint').textContent = 'Comparativas de bancos como en tu Excel y reparto de gastos. Los meses pendientes no cuentan como cero.';
    $('panelTools').hidden = true;
    if(!annual){
      $('content').appendChild(emptyChart('No se han podido cargar las gráficas.')); return;
    }

    renderAnnualHeader(annual);
    const grid = document.createElement('div');
    grid.className = 'charts-grid';
    grid.append(
      renderExcelBankMonths(annual),
      renderExcelYearComparison(annual),
      renderDonutChart(annual.expenseGroups)
    );
    $('content').appendChild(grid);
  }

  function render(){
    $('content').innerHTML = '';
    document.querySelectorAll('.tab').forEach(el=>el.classList.toggle('active', el.dataset.tab===state.tab));
    document.querySelector('.totals').hidden = state.tab === 'charts';
    if(state.tab === 'expenses') renderExpenses();
    if(state.tab === 'incomes') renderIncomes();
    if(state.tab === 'banks') renderBanks();
    if(state.tab === 'charts') renderCharts();
    if(state.tab === 'details') renderDetails();
    $('lastEdited').textContent = state.data ? `Excel actualizado: ${state.data.modified}` : '';
    refreshStatus();
    renderMetrics();
  }

  async function changeTab(newTab){
    if(newTab === state.tab) return;
    if(!confirmAbandon()) return;
    state.tab = newTab;
    state.dirty.clear();
    try{
      if(newTab === 'charts' && !state.annual.has(state.year)) await ensureAnnualIfNeeded(true);
      if(newTab === 'details') {state.editDetailId=null;await ensureDetailsIfNeeded(true);}
      render();
    }catch(error){
      notify(error.message, true);
      render();
    }
  }
  async function updatePeriod(){
    const year = Number($selectYear.value), month = Number($selectMonth.value);
    if(state.year===year && state.month===month) return;
    if(!confirmAbandon()){
      $selectYear.value = String(state.year);
      $selectMonth.value = String(state.month);
      return;
    }
    state.year = year; state.month = month; state.dirty.clear();
    if(state.tab === 'charts') state.annual.delete(year);
    state.editDetailId=null;state.details=null;
    await load();
  }
  async function save(){
    if(state.busy || state.dirty.size===0) return;
    const entries=[...state.dirty.entries()];
    for(const [key,val] of entries){
      const parsed = amount(val);
      if(Number.isNaN(parsed)){ notify('Revisa el importe del campo ' + key.replace(':',' ') + '.', true); return; }
      if((key.startsWith('income:')||key.startsWith('bank:')) && parsed!==null && parsed<0){ notify('Los ingresos y saldos bancarios no pueden ser negativos.', true); return; }
    }
    state.busy = true; refreshStatus();
    try{
      const obj = Object.fromEntries(entries);
      const response = await post('/api/save', {year:state.year, month:state.month, edits:obj});
      state.data = response.data;
      state.annual.delete(state.year);
      state.details=null;
      if(state.tab === 'charts') await ensureAnnualIfNeeded(true);
      state.dirty.clear();
      render();
      status('Guardado y copia de seguridad creada', 'saved');
      notify('Cambios guardados correctamente. Se ha creado una copia de seguridad.');
    }catch(error){ notify(error.message, true); status('No se han podido guardar los cambios', 'changed'); }
    finally{ state.busy = false; refreshStatus(); }
  }


  function showWork(){
    $('homeScreen').hidden=true;
    $('workApp').hidden=false;
    $('currentProfileLabel').textContent='◉  '+state.profileName;
  }
  async function showProfiles(){
    if(!confirmAbandon()) return;
    state.dirty.clear();
    state.data=null;
    state.details=null;
    state.annual.clear();
    state.profileId=null;
    $('homeScreen').hidden=false;
    $('workApp').hidden=true;
    try{
      const result=await fetchJSON('/api/profiles');
      const cards=$('profileCards');cards.innerHTML='';
      if(!result.profiles.length) cards.appendChild(makeTag('div','Todavía no hay contabilidades. Crea una o importa una copia ZIP.','profile-empty'));
      for(const p of result.profiles){
        const card=document.createElement('article');card.className='profile-card';
        const logo=makeTag('div','⌂','profile-card-icon');
        const name=makeTag('h3',p.name);
        const location=makeTag('p',p.location,'profile-location');location.title=p.location;
        const button=makeTag('button','Abrir contabilidad','save-button');
        button.disabled=!p.ready;
        button.addEventListener('click',()=>openProfile(p));
        const tools=document.createElement('div');tools.className='profile-tools';
        const rename=makeTag('button','Cambiar nombre','outline-button');rename.type='button';
        rename.addEventListener('click',async()=>{
          const next=prompt('Nuevo nombre de esta contabilidad:',p.name);
          if(next===null || next.trim()===p.name)return;
          try{await post('/api/profiles/rename',{id:p.id,name:next.trim()});await showProfiles();notify('Nombre actualizado.');}
          catch(e){homeError(e.message);notify(e.message,true);}
        });
        const del=makeTag('button','Eliminar','detail-remove');del.type='button';
        del.addEventListener('click',async()=>{
          const confirmation=prompt(`¿Eliminar «${p.name}»?

Se retirará de la lista, pero se guardará una copia ZIP recuperable y su carpeta de datos completa.

Para confirmar, escribe exactamente el nombre:`, '');
          if(confirmation===null)return;
          if(confirmation!==p.name){notify('No coincide el nombre. No se ha eliminado nada.',true);return;}
          try{const result=await post('/api/profiles/delete',{id:p.id});await showProfiles();notify('Eliminada de la lista. Copia recuperable: '+result.backupPath);}
          catch(e){homeError(e.message);notify(e.message,true);}
        });
        tools.append(rename,del);card.append(logo,name,location,button,tools);
        cards.appendChild(card);
      }
    }catch(e){homeError(e.message)}
  }
  function homeError(text){
    const box=$('homeError');box.hidden=false;box.textContent=text;
  }
  function fechaDeInicio(){
    // Fecha LOCAL de este ordenador en el instante de abrir una contabilidad.
    // Por ahora el Excel dispone de las hojas 2026 y 2027.
    const ahora = new Date();
    const anios = [...$selectYear.options].map(o => Number(o.value)).filter(Number.isFinite);
    const anio = anios.includes(ahora.getFullYear())
      ? ahora.getFullYear() : (anios.filter(y => y <= ahora.getFullYear()).pop() || anios[0]);
    return {year:anio, month:ahora.getMonth()+1};
  }
  async function openProfile(profile){
    try{
      await post('/api/profiles/select',{id:profile.id});
      state.profileId=profile.id;
      state.profileName=profile.name;
      state.dirty.clear();
      state.details=null;
      state.annual.clear();
      state.tab='expenses';
      const periodo = fechaDeInicio();
      state.year=periodo.year;state.month=periodo.month;
      $('year').value=String(periodo.year);$('month').value=String(periodo.month);
      showWork();
      await load();
    }catch(e){homeError(e.message);notify(e.message,true)}
  }
  async function saveBackup(){
    if(!state.profileId)return;
    if(state.dirty.size){notify('Guarda primero los cambios pendientes.',true);return}
    const btn=$('exportBackup');btn.disabled=true;
    try{
      const result=await post('/api/backup/native',{});
      if(result.cancelled) return;
      notify('Copia completa guardada en: '+result.path);
    }catch(e){
      notify('No se pudo abrir el diálogo de Windows: '+e.message+'; probando descarga del navegador.',true);
      try{
        const response=await fetch('/api/backup',{method:'POST',headers:{'X-CC-Token':window.APP_TOKEN,'X-CC-Profile':state.profileId}});
        if(!response.ok){const err=await response.json();throw Error(err.error||'No se pudo exportar.');}
        const blob=await response.blob();
        const url=URL.createObjectURL(blob);
        const link=document.createElement('a');link.href=url;link.download='Copia_Contabilidad_'+new Date().toISOString().slice(0,10)+'.zip';
        document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);
        notify('Descarga iniciada. Comprueba la carpeta de descargas o elige otra ubicación en el navegador.');
      }catch(ex){notify(ex.message,true)}
    }finally{btn.disabled=false}
  }
  async function uploadBackup(url,file,params={}){
    const qs=new URLSearchParams(params);
    const response=await fetch(url+(qs.size?'?'+qs:''),{
      method:'POST',
      headers:{'Content-Type':'application/zip','X-CC-Token':window.APP_TOKEN || '', 'X-CC-Profile':state.profileId||''},
      body:file
    });
    const data=await response.json();
    if(!response.ok)throw Error(data.error||'No se pudo recuperar la copia.');
    return data;
  }
  $('chooseFolder').addEventListener('click',async()=>{
    try{const result=await post('/api/profiles/folder',{});
      if(result.folder){state.folder=result.folder;$('chosenFolder').textContent=result.folder;}
    }catch(e){homeError('No se pudo abrir el selector de carpetas: '+e.message)}
  });
  $('createProfile').addEventListener('click',async()=>{
    const name=$('profileName').value.trim();
    if(!name){homeError('Escribe el nombre de la contabilidad.');return;}
    try{
      const p=await post('/api/profiles/create',{name,parent:state.folder});
      $('profileName').value='';state.folder=null;$('chosenFolder').textContent='Carpeta predeterminada';
      await openProfile(p.profile);
    }catch(e){homeError(e.message)}
  });
  $('importProfile').addEventListener('click',()=>{$('importInput').value='';$('importInput').click();});
  $('importInput').addEventListener('change',async()=>{
    const file=$('importInput').files[0];if(!file)return;
    try{
      const data=await uploadBackup('/api/backup/import',file,{...( $('importName').value.trim() ? {name:$('importName').value.trim()} : {} ),...(state.folder?{parent:state.folder}:{})});
      $('importName').value='';
      await openProfile(data.profile);
      notify('Contabilidad recuperada como perfil independiente.');
    }catch(e){homeError(e.message);notify(e.message,true)}
  });
  $('backProfiles').addEventListener('click',()=>showProfiles());
  $('exportBackup').addEventListener('click',saveBackup);
  $('restoreBackup').addEventListener('click',()=>{
    if(!confirmAbandon())return;
    $('restoreInput').value='';$('restoreInput').click();
  });
  $('restoreInput').addEventListener('change',async()=>{
    const file=$('restoreInput').files[0];if(!file)return;
    if(!confirm('¿RECUPERAR ESTA COPIA sobre la contabilidad «'+state.profileName+'»? Se guardará antes una copia automática del estado actual. Las demás contabilidades no se modificarán.'))return;
    try{
      await uploadBackup('/api/backup/restore',file);
      state.dirty.clear();state.annual.clear();state.details=null;
      await load();
      notify('Copia recuperada correctamente. El estado anterior se ha guardado por seguridad.');
    }catch(e){notify(e.message,true)}
  });

  const periodoInicial = fechaDeInicio();
  state.year = periodoInicial.year;
  state.month = periodoInicial.month;
  $('year').value = String(periodoInicial.year);
  $('month').value = String(periodoInicial.month);
  $selectYear.addEventListener('change', updatePeriod);
  $selectMonth.addEventListener('change', updatePeriod);
  document.querySelectorAll('[data-tab]').forEach(btn=>btn.addEventListener('click',()=>changeTab(btn.dataset.tab)));
  $('search').addEventListener('input', e => {
    const text = e.target.value.toLocaleLowerCase('es').trim();
    document.querySelectorAll('.group').forEach(group => {
      let visible = 0;
      group.querySelectorAll('.entry-row').forEach(row => {
        const found = (row.dataset.search || '').includes(text);
        row.hidden = !found;
        if(found) visible++;
      });
      group.hidden = visible === 0;
    });
  });
  $('save').addEventListener('click', save);
  document.querySelector('a[href="/api/download"]').addEventListener('click', event => {
    if(state.dirty.size && !confirm('Tienes cambios sin guardar. La descarga NO los incluirá. ¿Quieres continuar?')){event.preventDefault();return;}
    event.currentTarget.href='/api/download?profile='+encodeURIComponent(state.profileId);
  });
  $('openExcel').addEventListener('click', async() => {
    if(state.dirty.size){ notify('Guarda primero los cambios pendientes.', true); return; }
    try { await post('/api/open'); notify('Abriendo Cuentas.xlsx. Ciérralo antes de volver a guardar desde aquí.'); }
    catch(e){ notify('No se ha podido abrir automáticamente: ' + e.message, true); }
  });
  $('exit').addEventListener('click', async() => {
    if(!confirmAbandon()) return;
    try { await post('/api/exit'); document.body.innerHTML='<main style="font-family:Segoe UI,Arial,sans-serif;max-width:520px;margin:100px auto;padding:30px"><h1>Contabilidad Casa cerrado</h1><p>Ya puedes cerrar esta pestaña.</p></main>'; }
    catch(e){ notify(e.message, true); }
  });
  window.addEventListener('beforeunload', event => { if(state.dirty.size){ event.preventDefault(); event.returnValue=''; } });
  showProfiles();
})();
