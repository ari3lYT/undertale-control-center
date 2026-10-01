// Read-only view: never sends commands to the game or writes saves.
const variablesView={offset:0,limit:100,paused:false,busy:false,query:'',request:0};
const monitorSettings=document.createElement('article');monitorSettings.className='card';
monitorSettings.innerHTML='<h2>Частота старого полного обхода</h2><p>Этот параметр действует только до перезапуска игры с новым модулем. Новый модуль не обходит все объекты: он следит за полями сохранения и отмечает IGT при их изменении.</p><label>Полный обход старого модуля <select id="monitorInterval"><option value="1000">Раз в секунду</option><option value="2000">Раз в 2 секунды — меньше нагрузка</option><option value="500">Каждые 500 мс</option><option value="250">Каждые 250 мс</option><option value="100">Каждые 100 мс — выше нагрузка</option></select></label>';
$('#view-settings').append(monitorSettings);
api('/api/settings').then(s=>{const select=$('#monitorInterval');select.value=String(s.monitor_interval_ms||1000);select.dispatchEvent(new Event('change'))}).catch(()=>{});
$('#monitorInterval').addEventListener('change',async e=>{if(!e.isTrusted&&!e.uccUser)return;try{await api('/api/settings',{method:'POST',body:JSON.stringify({monitor_interval_ms:Number(e.target.value)})});toast('Интервал сохранён. Новый модуль подхватит его автоматически.')}catch(err){toast(err.message,true)}});
function updateLiveFlagCells(){
  const r=app.runtime||{}, values=r.live_flags||{}, save=activeSave($('#flagSave').value);
  monitorSettings.style.display=r.monitor?.version>=7?'none':'';
  $$('[data-live-flag]').forEach(cell=>{
    const id=cell.dataset.liveFlag, known=Object.hasOwn(values,id), value=values[id];
    cell.textContent=known?String(value)+(r.connected?'':' · устарело'):'не получено';
    cell.classList.toggle('memory-different',known&&!!save&&Number(save.flags[id])!==Number(value));
    cell.title=known?'Последнее наблюдение в памяти; выделение означает отличие от выбранного сейва':'Модуль ещё не передал значение. Это не ноль.';
  });
  $$('[data-disk-flag]').forEach(cell=>{cell.textContent=save?.flags[cell.dataset.diskFlag]??'—'});
  $('#flagMemoryNote').textContent=`${r.connected?'Связь с игрой есть':'Нет свежих данных'}. Получено значений из памяти: ${Object.keys(values).length}/512. ${r.monitor?.version>=7?'Модуль следит за полями сохранения.':r.monitor?.version>=6?'Старый модуль передаёт начальный снимок и изменения.':'Модуль передаёт только изменившиеся флаги; остальные неизвестны до первого изменения.'} Выделение — отличие от сейва, не обязательно ошибка.`;
}
function variableValue(value,type){return type==='absent'?'отсутствует':type==='undefined'?'undefined':type==='array'?`массив · строк: ${value}`:JSON.stringify(value)}
async function refreshVariables(){
  if(variablesView.paused||variablesView.busy||!$('#view-dev').classList.contains('active'))return;
  variablesView.busy=true;
  const request=++variablesView.request, query=variablesView.query, offset=variablesView.offset;
  try{
    const d=await api(`/api/variables?q=${encodeURIComponent(query)}&offset=${offset}&limit=${variablesView.limit}`);
    if(request!==variablesView.request||variablesView.paused||query!==variablesView.query||offset!==variablesView.offset)return;
    const m=d.monitor||{};
    $('#variableStatus').textContent=m.version>=6?`${d.connected?'● Подключено':'○ Данные устарели'} · ${d.total} значений · самый долгий шаг обхода ${(Number(m.scan_us||0)/1000).toFixed(2)} мс · пропусков в последнем обходе: ${m.skipped??'—'}`:'Сейчас в игре модуль v5: показаны полученные флаги, сюжет, комната и состояние взаимодействия. Расширенный модуль v6 подготовлен отдельно и не установлен в запущенную игру. HP, инвентарь и объекты эта сессия не передаёт.';
    $('#variablePage').textContent=d.matched?`${offset+1}–${Math.min(offset+variablesView.limit,d.matched)} из ${d.matched}`:'0 значений';
    $('#variablePrevious').disabled=offset===0;$('#variableNext').disabled=offset+variablesView.limit>=d.matched;
    $('#variableRows').innerHTML=d.variables.map(v=>`<tr><td><code>${esc(v.path)}</code></td><td>${esc(v.type)}</td><td><code>${esc(variableValue(v.value,v.type))}</code></td><td>${esc(v.ticks)}</td></tr>`).join('')||'<tr><td colspan="4">Нет полученных значений по этому запросу.</td></tr>';
    $('#variableChanges').innerHTML=d.events.filter(e=>e.operation!=='observed').slice(0,100).map(e=>`<article class="live-diff"><b>${esc(e.path)}</b><p><code>${esc(variableValue(e.before,e.previous_type))}</code> → <code>${esc(variableValue(e.after,e.type))}</code></p><small>Тик ${esc(e.ticks)} · ${e.operation==='removed'?'переменная или объект исчезли':'изменилось значение'}</small></article>`).join('')||'<p>Изменений после начального наблюдения пока нет.</p>';
  }catch(e){$('#variableStatus').textContent=`Не удалось прочитать монитор: ${e.message}`}
  finally{variablesView.busy=false}
}
$('#variableSearch').addEventListener('input',e=>{variablesView.query=e.target.value;variablesView.offset=0;refreshVariables()});
$('#variablePause').addEventListener('click',()=>{variablesView.paused=!variablesView.paused;$('#variablePause').textContent=variablesView.paused?'Продолжить таблицу':'Приостановить таблицу';refreshVariables()});
$('#variablePrevious').addEventListener('click',()=>{variablesView.offset=Math.max(0,variablesView.offset-variablesView.limit);refreshVariables()});
$('#variableNext').addEventListener('click',()=>{variablesView.offset+=variablesView.limit;refreshVariables()});
setInterval(refreshVariables,1500);
