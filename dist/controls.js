// UI controls: local dialogs and searchable listboxes; no browser confirm/prompt.
let activePicker=null;
function closePicker(){if(activePicker){activePicker.panel.remove();activePicker.button.setAttribute('aria-expanded','false');activePicker=null;}}
function ask(message,title='Подтверждение',accept='Продолжить'){
  closePicker();
  return new Promise(resolve=>{
    const previous=document.activeElement,overlay=document.createElement('div');overlay.className='ucc-dialog-backdrop';
    overlay.innerHTML=`<section class="ucc-dialog" role="dialog" aria-modal="true" aria-labelledby="ucc-dialog-title"><h2 id="ucc-dialog-title">${esc(title)}</h2><p class="dialog-message">${esc(message)}</p><div class="dialog-actions"><button data-answer="no">Отмена</button><button class="primary" data-answer="yes">${esc(accept)}</button></div></section>`;
    document.body.append(overlay);
    const finish=value=>{document.removeEventListener('keydown',keys,true);overlay.remove();previous?.focus();resolve(value);};
    const keys=e=>{if(e.key==='Escape'){e.preventDefault();finish(false);}if(e.key==='Tab'){const buttons=[...overlay.querySelectorAll('button')];if(e.shiftKey&&document.activeElement===buttons[0]){e.preventDefault();buttons.at(-1).focus();}else if(!e.shiftKey&&document.activeElement===buttons.at(-1)){e.preventDefault();buttons[0].focus();}}};
    overlay.addEventListener('click',e=>{const b=e.target.closest('[data-answer]');if(b)finish(b.dataset.answer==='yes');else if(e.target===overlay)finish(false);});
    document.addEventListener('keydown',keys,true);overlay.querySelector('button').focus();
  });
}

function upgradeSelect(select){
  if(select.dataset.customized)return;select.dataset.customized='1';select.classList.add('custom-select-source');select.tabIndex=-1;select.setAttribute('aria-hidden','true');
  const button=document.createElement('button');button.type='button';button.className='custom-select';button.setAttribute('role','combobox');button.setAttribute('aria-expanded','false');button.setAttribute('aria-haspopup','listbox');
  select.after(button);
  const sync=()=>{button.textContent=(select.selectedOptions[0]?.textContent||'Выбрать')+' ▾';button.disabled=select.disabled;button.title=select.selectedOptions[0]?.textContent||'';};
  select.addEventListener('change',sync);sync();
  button.addEventListener('click',()=>{
    if(activePicker?.button===button)return closePicker();closePicker();
    const panel=document.createElement('div');panel.className='select-popover';const rect=button.getBoundingClientRect();
    panel.style.left=Math.max(8,Math.min(rect.left,innerWidth-Math.max(280,rect.width)-8))+'px';panel.style.width=Math.min(innerWidth-16,Math.max(280,rect.width))+'px';
    panel.style.top=Math.min(rect.bottom+5,Math.max(8,innerHeight-320))+'px';
    panel.innerHTML='<input class="select-search" aria-label="Поиск варианта" placeholder="Поиск по названию или ID…"><div class="select-options" role="listbox"></div>';
    document.body.append(panel);activePicker={panel,button};button.setAttribute('aria-expanded','true');
    const search=panel.querySelector('input'),list=panel.querySelector('[role=listbox]');let cursor=-1;
    const paint=()=>{const q=search.value.toLocaleLowerCase();const options=[...select.options].filter(o=>o.textContent.toLocaleLowerCase().includes(q));cursor=-1;
      list.innerHTML=options.map(o=>`<button type="button" role="option" aria-selected="${o.selected}" data-value="${esc(o.value)}" ${o.disabled?'disabled':''}>${esc(o.textContent)}</button>`).join('')||'<p>Нет вариантов</p>';};
    const choose=b=>{select.value=b.dataset.value;select.dispatchEvent(new Event('input',{bubbles:true}));const event=new Event('change',{bubbles:true});event.uccUser=true;select.dispatchEvent(event);sync();closePicker();button.focus();};
    list.addEventListener('click',e=>{const option=e.target.closest('[data-value]');if(option&&!option.disabled)choose(option);});
    panel.addEventListener('keydown',e=>{const choices=[...list.querySelectorAll('button:not(:disabled)')];if(e.key==='Escape'){e.preventDefault();closePicker();button.focus();}else if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();cursor=Math.max(0,Math.min(choices.length-1,cursor+(e.key==='ArrowDown'?1:-1)));choices[cursor]?.focus();}else if(e.key==='Enter'&&document.activeElement===search){e.preventDefault();if(choices[0])choose(choices[0]);}});
    search.addEventListener('input',paint);paint();search.focus();
  });
}
document.addEventListener('pointerdown',e=>{if(activePicker&&!activePicker.panel.contains(e.target)&&!activePicker.button.contains(e.target))closePicker();});
window.addEventListener('resize',closePicker);
new MutationObserver(records=>{
  for(const record of records)for(const node of record.addedNodes){if(node.nodeType!==1)continue;if(node.matches('select'))upgradeSelect(node);node.querySelectorAll('select').forEach(upgradeSelect);}
  if(activePicker&&!activePicker.button.isConnected)closePicker();
}).observe(document.body,{childList:true,subtree:true});
document.querySelectorAll('select').forEach(upgradeSelect);

Object.assign(titles,{files:['Файлы и слоты','Целые состояния прохождения и исходные файлы'],settings:['Настройки','Управление, runtime и поведение менеджера']});
const extraNav=document.createElement('div');extraNav.innerHTML='<button class="nav-item" data-view="files"><span>▤</span>Файлы и слоты</button><button class="nav-item" data-view="settings"><span>⚙</span>Настройки</button>';document.querySelector('.sidebar nav').append(...extraNav.children);
const extraViews=document.createElement('div');extraViews.innerHTML=`
<section class="view" id="view-files">
 <article class="card"><h2>Слоты прохождения</h2><p>Слот — весь набор игровых файлов, а не переименованный file0. При запущенной игре предлагается live-замена с перезагрузкой игрового состояния; нужен новый игровой модуль. Перед заменой сохраняется текущий набор. Steam Cloud может восстановить свои копии при следующем запуске.</p>
 <div class="inline-form"><input id="slotTitle" aria-label="Название слота" placeholder="Название нового слота"><button id="cloneSlot">Сохранить текущий набор в слот</button><button id="blankSlot">Создать чистый слот</button><button id="cleanGame" class="danger-button">Очистить текущую игру</button></div><div id="slotList"></div></article>
 <article class="card"><h2>Пресеты прохождения</h2><p>Чужой пресет заменяет весь сюжетный набор, а не переносит один plot в твоё прохождение. Прежнее состояние сохраняется отдельным слотом. Совместимость с модом отмечена для каждого пресета.</p><div id="presetList"></div></article>
 <article class="card"><h2>Игровые файлы</h2><p>Все основные файлы текущего файлового хранилища, включая отсутствующие. Удаление из редактора — независимая операция. Для чистого старта используй кнопку выше.</p><div id="fileList"></div></article>
 <article class="card" id="rawFilePanel" hidden><h2 id="rawFileTitle"></h2><p id="rawFileHelp"></p><label>Содержимое<textarea id="rawFileText" spellcheck="false" rows="16"></textarea></label><div class="inline-form"><button id="writeRawFile" class="primary">Проверить и записать</button><button id="removeRawFile" class="danger-button">Удалить этот файл</button></div></article>
</section>
<section class="view" id="view-settings"><article class="card"><h2>Режим записи менеджера</h2><p>Связанный режим пишет file0, file9 и сводку INI вместе. Независимый режим намеренно допускает расхождения. Он нужен для исследования, не обещает пригодное прохождение.</p><select id="writeMode"><option value="coupled">Связанный — по умолчанию</option><option value="independent">Независимый — допускаю расхождения</option></select><div id="managerToggles"></div></article><article class="card"><h2>Ввод в игре</h2><p>Журнал ограничен самой Undertale: клавиши, нажатия геймпада и мыши. Не записывает ввод других приложений. Клик содержит координаты; смысл выбранного объекта не выводится достоверно из одних координат.</p><div id="inputEvents"></div></article></section>`;
document.querySelector('main').append(...extraViews.children);
let fileState=null,selectedRawFile=null,rawEditorHash=null;
let lastBonusKey=null,bonusRefreshing=false,bonusPlan=null;
async function refreshBonusContext(){
 if(bonusRefreshing)return;bonusRefreshing=true;
 try{
  const context=await api('/api/context'),key=JSON.stringify(context);
  if(key!==lastBonusKey){
   const catalog=await api('/api/catalog');
   lastBonusKey=key;app.catalog=catalog;
   let badge=$('#bonusContext');if(!badge){badge=document.createElement('p');badge.id='bonusContext';document.querySelector('.profile-bar')?.append(badge);}
   badge.textContent=`Активный бонус: ${catalog.bonus.name} · источник: ${catalog.bonus.source}`;
   const draft=$('#flagEditValue')?.value;
   closePicker();
   if($('#view-flags').classList.contains('active')){renderFlags();if(draft!=null&&$('#flagEditValue'))$('#flagEditValue').value=draft;}
   if($('#view-fun').classList.contains('active'))renderFun();
   $('#bonusCurrent').textContent='Сейчас: '+catalog.bonus.name+' ('+catalog.bonus.source+')';
   $('#bonusTarget').value=String(catalog.bonus.mode);$('#bonusTarget').dispatchEvent(new Event('change'));
   app.lastRuntimeFlags=null;
   bonusPlan=null;$('#bonusPlan').innerHTML='';
  }
 }finally{bonusRefreshing=false;}
}
const bonusPanel=document.createElement('article');bonusPanel.className='card';bonusPanel.innerHTML=`<h2>Бонусный контент и миграция</h2><p id="bonusCurrent"></p><p>Это варианты бонусов одной сборки, а не разные форматы сейва. PS4, Switch, Xbox и 10-летие сохраняют собственные поля прогресса. Смена не превращает пожертвования в победу над боссом.</p><div class="inline-form"><select id="bonusTarget" aria-label="Новый бонус"><option value="0">Без бонуса</option><option value="1">PS4</option><option value="2">Switch</option><option value="3">Xbox</option><option value="4">10-летие</option></select><button id="previewBonus">Показать план смены</button></div><div id="bonusPlan"></div>`;$('#view-settings').prepend(bonusPanel);
document.addEventListener('click',async e=>{
 try{
  if(e.target.id==='previewBonus'){
   bonusPlan=await api('/api/bonus/preview',{method:'POST',body:JSON.stringify({target:Number($('#bonusTarget').value)})});
   $('#bonusPlan').innerHTML=bonusPlan.changes.map(c=>`<div class="file-row"><div><b>${esc(c.file)} · ${esc(c.field)}</b><p>${esc(c.before)} → ${esc(c.after)}</p><small>${esc(c.reason)}</small></div></div>`).join('')+`<p>${esc(bonusPlan.preserved)}</p><p>${esc(bonusPlan.runtime)}</p><div class="inline-form"><button id="applyBonus" class="primary">Применить весь план / live-перезагрузка</button><button id="liveBonus">Сменить бонус без перезагрузки (у Санса)</button></div>`;
  }
  if(e.target.id==='applyBonus'||e.target.id==='liveBonus'){
   if(!bonusPlan)return;
   if(!await ask('Применить показанный план? Будет создан резервный слот. Прогресс остальных бонусов сохраняется.','Смена бонусного контента'))return;
   const live=e.target.id==='liveBonus',result=await api('/api/bonus/'+(live?'live':'apply'),{method:'POST',body:JSON.stringify({target:bonusPlan.target,hash:bonusPlan.hash})});
   if(live)app.awaitingSeq=result.seq;
   if(!result.queued)toast(live?'Команда отправлена; ждём подтверждение игры':'Смена сохранена. Исходный набор — в резервном слоте.');bonusPlan=null;$('#bonusPlan').innerHTML='';await refreshAll();await refreshBonusContext();await refreshExtras();
  }
 }catch(err){toast(err.message,true);}
});
async function refreshExtras(){
  const [settings,files,slots,presets]=await Promise.all([api('/api/settings'),api('/api/files'),api('/api/slots'),api('/api/presets').catch(()=>({presets:[]}))]);app.settings=settings;fileState=files;
  $('#writeMode').value=settings.write_mode;$('#writeMode').dispatchEvent(new Event('change'));
  $('#managerToggles').innerHTML=[['wasd','Движение WASD','При debug отключается, чтобы W не конфликтовала с замедлением.'],['zxc','Действия Z / X / C','Дополняют Enter / Shift / Ctrl.'],['debug','Встроенный debug','Открывает отладочные клавиши игры; часть действий меняет маршрут.'],['input_log','Запись игровых нажатий','Локальный журнал событий в ucc-events.log.'],['remember_view','Запоминать вкладку','Вкладка и раздел редактора восстанавливаются после обновления страницы.']].map(([key,label,help])=>`<label class="setting-row"><div><b>${label}</b><p>${help}</p></div><input class="switch-input" type="checkbox" data-manager-setting="${key}" ${settings[key]?'checked':''}><span class="switch-track"></span></label>`).join('');
  $('#slotList').innerHTML=slots.slots.map(slot=>`<div class="file-row"><div><b>${esc(slot.title)}</b><small>${esc(slot.profile)} · ${fmtTime(slot.created)} · ${esc(slot.source)}</small></div><button data-activate-slot="${slot.id}">Активировать</button></div>`).join('')||'<p>Сохранённых слотов пока нет.</p>';
  $('#fileList').innerHTML=files.files.map(f=>`<div class="file-row"><div><b>${esc(f.name)} — ${esc(f.title)}</b><small>${f.exists?f.size+' байт':'Отсутствует'}</small><p>${esc(f.description)}</p></div><button data-edit-file="${f.name}">${f.exists?'Открыть':'Создать'}</button></div>`).join('');
  $('#presetList').innerHTML=presets.presets.map(p=>`<div class="file-row"><div><b>${esc(p.title)}</b><p>${esc(p.description)}</p><small>${esc(p.status)} · <a href="${esc(p.source)}" target="_blank" rel="noreferrer">Источник</a></small></div><button data-preset="${esc(p.id)}">Создать слот из пресета</button></div>`).join('')||'<p>Каталог пресетов загружается после проверки форматов.</p>';
}
async function updateManager(key,value){
  if(key==='write_mode'&&value==='independent'&&!await ask('Независимые изменения не синхронизируют соседние файлы. Такие комбинации могут не встречаться в обычной игре. Включить этот режим?','Независимая запись'))return refreshExtras();
  if(key==='debug'&&value&&!await ask('Debug позволяет менять скорость, HP, сюжет и перезапускать игру. WASD при включённом debug не действует. Включить?','Встроенный debug'))return refreshExtras();
  app.settings=await api('/api/settings',{method:'POST',body:JSON.stringify({[key]:value})});toast(['wasd','zxc','debug','input_log'].includes(key)?'Настройка записана. Ожидается подтверждение от запущенной игры.':'Настройка сохранена');
}
document.addEventListener('change',e=>{if(e.target.dataset.managerSetting)updateManager(e.target.dataset.managerSetting,e.target.checked).catch(err=>toast(err.message,true));if(e.target.id==='writeMode'&&e.isTrusted)updateManager('write_mode',e.target.value).catch(err=>toast(err.message,true));});
// Synthetic select events are intentional custom-control actions; avoid persisting refresh sync.
$('#writeMode').addEventListener('input',e=>updateManager('write_mode',e.target.value).catch(err=>toast(err.message,true)));
document.addEventListener('click',async e=>{
 try{
  if(e.target.closest('[data-view="files"],[data-view="settings"]'))return await refreshExtras();
  if(e.target.id==='cloneSlot'||e.target.id==='blankSlot'){await api('/api/slots/create',{method:'POST',body:JSON.stringify({title:$('#slotTitle').value,clean:e.target.id==='blankSlot'})});toast('Слот создан; текущая игра не изменена');return await refreshExtras();}
  if(e.target.id==='cleanGame'){
   const target=app.state.paths.save,inactive=target!==app.state.discovery.save_dir;
   if(inactive&&!await ask(`Выбрана АРХИВНАЯ папка ${target}. Рабочая папка игры: ${app.state.discovery.save_dir}. Очистка архива не сбросит текущую игру. Очистить именно архив?`,'Выбрана не рабочая папка'))return;
   if(!await ask(`Папка для очистки: ${target}\nИсточник: ${app.state.discovery.source||'ручной выбор'}\nУбедись, что это нужное прохождение.`,'Проверь полный путь'))return;
   if(!await ask('Будут удалены локальные file0–file9, undertale.ini, config.ini, файлы 962/963 и платформенный контейнер, если они существуют. Сначала весь набор будет сохранён в резервном слоте. Настройки языка тоже сбросятся. Steam Cloud этим действием НЕ очищается.','Чистая игра до первого запуска','Сохранить копию и очистить'))return;
   const r=await api('/api/clean',{method:'POST',body:JSON.stringify({hash:fileState.hash,confirm:'clean-all',inactive_path:inactive?target:null})});if(!r.queued)toast('Локальные файлы очищены. Восстановление — из резервного слота '+r.backup);await refreshAll();return refreshExtras();
  }
  const activate=e.target.closest('[data-activate-slot]');if(activate){const slot=(await api('/api/slots')).slots.find(s=>s.id===activate.dataset.activateSlot);const experimental=slot?.source.startsWith('external-preset:');if(experimental&&!await ask('Этот внешний набор предназначен для отдельной сцены. Его автор намеренно использует комбинации, которые не обязательно достижимы обычным прохождением. Возврат в предыдущие главы может нарушить сюжет. Активировать как эксперимент с резервной копией?','Сценарный пресет','Принимаю ограничения'))return;if(!await ask('Текущий набор будет сохранён в резервный слот, затем заменён выбранным. Для запущенной игры будет отдельное подтверждение live-перезагрузки.','Сменить прохождение'))return;const r=await api('/api/slots/activate',{method:'POST',body:JSON.stringify({id:activate.dataset.activateSlot,hash:fileState.hash,accept_experimental:experimental})});if(!r.queued)toast('Слот активирован');await refreshAll();return refreshExtras();}
  const preset=e.target.closest('[data-preset]');if(preset){await api('/api/presets/create',{method:'POST',body:JSON.stringify({id:preset.dataset.preset})});toast('Пресет добавлен как отдельный слот, текущая игра не изменена');return refreshExtras();}
  const edit=e.target.closest('[data-edit-file]');if(edit){rawEditorHash=fileState.hash;selectedRawFile=fileState.files.find(f=>f.name===edit.dataset.editFile);$('#rawFilePanel').hidden=false;$('#rawFileTitle').textContent=selectedRawFile.name+(selectedRawFile.encoding==='hex'?' — HEX':'');$('#rawFileHelp').textContent=selectedRawFile.description;$('#rawFileText').value=selectedRawFile.content;$('#rawFilePanel').scrollIntoView({behavior:'smooth'});return;}
  if(e.target.id==='writeRawFile'||e.target.id==='removeRawFile'){
   const remove=e.target.id==='removeRawFile';if(!selectedRawFile)return;
   if(!await ask(`${remove?'Удалить':'Записать'} ${selectedRawFile.name}? ${app.settings.write_mode==='coupled'&&['file0','file9'].includes(selectedRawFile.name)&&!remove?'Будут обновлены file0, file9 и INI.':'Это отдельная операция с выбранным файлом.'} Будет сохранён резервный слот.`,remove?'Удаление файла':'Запись файла'))return;
   const r=await api('/api/files/write',{method:'POST',body:JSON.stringify({name:selectedRawFile.name,content:$('#rawFileText').value,hash:rawEditorHash,mode:app.settings.write_mode,remove})});if(!r.queued)toast('Изменение записано, резервный слот сохранён');await refreshAll();return refreshExtras();
  }
 }catch(err){toast(err.message,true);}
});
const debugPanel=document.querySelector('#devGrid').closest('article');const debugButton=document.createElement('button');debugButton.id='runtimeDebugToggle';debugButton.textContent='Включить / выключить debug';debugPanel.querySelector('.card-head').append(debugButton);debugButton.addEventListener('click',()=>updateManager('debug',!app.settings.debug).catch(err=>toast(err.message,true)));
setInterval(()=>{if(app.runtime?.settings){const q=app.runtime.settings;debugButton.textContent=q.debug?'Отключить debug':'Включить debug';debugPanel.querySelector('.pill').textContent='В игре debug = '+Number(q.debug);}if(app.runtime?.inputs){$('#inputEvents').innerHTML=app.runtime.inputs.slice(0,100).map(i=>`<div class="input-row">${esc(i.kind)} · ${esc(i.code)} · ${i.pressed?'нажато':'отпущено'} · комната ${i.room} · IGT ${ticksLabel(i.ticks)}${i.x!=null?' · x='+i.x+' y='+i.y:''}</div>`).join('')||'<p>Игровые нажатия ещё не записаны.</p>';}},1500);
