const $ = (s, root=document) => root.querySelector(s);
const $$ = (s, root=document) => [...root.querySelectorAll(s)];
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmtKb = kb => kb == null ? '—' : kb > 1048576 ? `${(kb/1048576).toFixed(2)} ГБ` : `${(kb/1024).toFixed(1)} МБ`;
const fmtTime = iso => { try { return new Date(iso).toLocaleString('ru-RU'); } catch { return iso; } };
const api = async (path, options={}) => {
  const livePaths=['/api/apply','/api/apply-ini','/api/clean','/api/files/write','/api/slots/activate','/api/rollback','/api/bonus/apply'];
  if(options.method==='POST'&&livePaths.includes(path)&&app.state?.game?.running){
    if(!app.runtime?.live_bundle)throw new Error('Для этой операции нужен новый игровой модуль. Он подготовлен отдельно; текущая сессия v5 поддерживает только отдельные live-команды. Игра не изменена.');
    const detail=path==='/api/apply'?'Будет загружен весь выбранный сейв, не только изменённые поля. Несохранённое состояние заменится; HP восстановится, комната загрузится заново, служебные флаги нормализуются штатным загрузчиком.':'Будет заменён набор файлов и перезагружено игровое состояние внутри того же процесса. Игра вернётся к начальному экрану нового состояния; для слота нажми «Продолжить». Несохранённое состояние потеряется.';
    if(!await ask(detail+' Перед применением сохраняется резервный слот. Команда действует 30 секунд и ждёт выхода из боя/диалога.','Применить live?','Применить live'))throw new Error('Live-применение отменено');
    options={...options,body:JSON.stringify({...JSON.parse(options.body||'{}'),live:true})};
  }
  const response = await fetch(path, {...options,headers:{'Content-Type':'application/json',...(app.state?.paths?.save?{'X-UCC-Save-Dir':app.state.paths.save}:{}),...options.headers}});
  const data = await response.json();
  if (!response.ok || data.error) throw new Error(data.error || `HTTP ${response.status}`);
  if(data.queued){app.liveBundleSeq=String(data.seq);toast('Команда отправлена. Ждём проверку и подтверждение игры.');}
  return data;
};

const app = {catalog:null,state:null,history:[],memory:[],saveSection:'core',pending:new Map(),pendingSave:'file0',selectedFlag:null,modal:null};
const titles = {
  dashboard:['Обзор','Живое состояние игры и сохранения'], fun:['FUN-маршрут','Редкие события в порядке прохождения'],
  save:['Редактор сейва','Поля, справочники и проверяемые изменения'], flags:['Все флаги','Ручной разбор состояний и последствий'],
  story:['Сюжет','Все реальные значения global.plot'], history:['История и откат','Семантические diff и снимки'],
  dev:['Devtools','Hot reload, debug и память процесса'], guide:['Как всё устроено','Файлы, формат и логика изменений']
};

function toast(message, error=false){
  const node=document.createElement('div'); node.className=`toast${error?' error':''}`; node.textContent=message;
  $('#toastStack').append(node); setTimeout(()=>node.remove(),4500);
}

function go(view){
  if(!titles[view])view='dashboard'; if(app.settings?.remember_view!==false){localStorage.setItem('ucc-view',view);history.replaceState(null,'','#'+view);}
  $$('.view').forEach(x=>x.classList.remove('active')); $$('.nav-item').forEach(x=>x.classList.toggle('active',x.dataset.view===view));
  $(`#view-${view}`).classList.add('active'); $('#viewTitle').textContent=titles[view][0]; $('#viewSub').textContent=titles[view][1];
  if(view==='flags') renderFlags(); if(view==='history') renderHistory(); if(view==='story') renderStory(); if(view==='save') renderSaveEditor();
}

function activeSave(name){ return app.state?.saves?.[name]?.model; }
function validation(name){ return app.state?.saves?.[name]?.validation; }
function itemName(id){ return app.catalog.items.find(x=>x.id===Number(id))?.name || `ID ${id}`; }
function phoneName(id){ return app.catalog.phones.find(x=>x.id===Number(id))?.name || `ID ${id}`; }
function roomName(id){ return app.catalog.rooms.find(x=>x.id===Number(id))?.label || `Комната ${id}`; }
function soundName(id){ return Number(id)===-1?'Автовыбор комнаты':(app.catalog.sounds.find(x=>x.id===Number(id))?.name || `Звук ${id}`); }
function plotName(value){ return app.catalog.plots.find(x=>Number(x.value)===Number(value))?.title || `Неизвестный этап ${value}`; }

function renderDashboard(){
  const save=activeSave('file0'), valid=validation('file0'), game=app.state.game;
  $('#gameDot').classList.toggle('on',!!game.running); $('#gameState').textContent=game.running?`Undertale запущен · PID ${game.pid}`:'Undertale не запущен';
  $('#launchBtn').textContent=game.running?'● Undertale уже запущен':'▶ Запустить Undertale';
  renderLocation();
  if(!save){$('#heroTitle').textContent='В выбранной папке нет file0';$('#heroText').textContent='Начни игру и сохранись у звезды либо выбери другую папку. Удалённые файлы не восстанавливаются автоматически.';$('#mainStats').innerHTML='';$('#diagnostics').textContent='Нет файла для проверки';renderMemory();renderRecent();return;}
  $('#heroTitle').textContent=`${save.name} · ${roomName(save.room)}`;
  $('#heroText').textContent=`Сюжет: ${plotName(save.plot)}. FUN ${save.flags[5]}. Последнее сохранённое время — ${save.playtime.label}.`;
  const stats=[['LOVE',save.lv,''],['HP',save.maxhp,'max'],['EXP',save.xp,''],['Золото',save.gold,'G'],['Время',save.playtime.label,'']];
  $('#mainStats').innerHTML=stats.map(x=>`<div class="stat"><small>${esc(x[0])}</small><b>${esc(x[1])}</b><em>${esc(x[2])}</em></div>`).join('');
  $('#validationPill').className=`pill ${valid.errors.length?'bad':valid.warnings.length?'warn':''}`; $('#validationPill').textContent=valid.summary;
  const issues=[...valid.errors.map(x=>({...x,kind:'error'})),...valid.warnings.slice(0,5)];
  $('#diagnostics').innerHTML=issues.length?`<div class="issue-list">${issues.map(x=>`<div class="issue ${x.kind||''}"><b>${esc(x.path)}</b> · ${esc(x.message)}</div>`).join('')}</div>`:`<div class="ok-block">✓ Известные проверки пройдены. Это не гарантия согласованности всех сюжетных зависимостей.</div>`;
  renderMemory(); renderRecent();
}

function renderMemory(){
  const m=app.state?.game||{}; $('#memoryPulse').classList.toggle('on',!!m.running);
  const metrics=m.running?[['RSS',fmtKb(m.rss_kb)],['Virtual',fmtKb(m.virtual_kb)],['Потоки',m.threads],['FD',m.fds]]:[['Статус','не запущен'],['RSS','—'],['Потоки','—'],['FD','—']];
  $('#memoryCards').innerHTML=metrics.map(x=>`<div class="mini-metric"><span>${x[0]}</span><b>${x[1]}</b></div>`).join('');
  const canvas=$('#memoryChart'), ctx=canvas.getContext('2d'), dpr=devicePixelRatio||1, w=canvas.clientWidth||500,h=150;
  canvas.width=w*dpr;canvas.height=h*dpr;ctx.scale(dpr,dpr);ctx.clearRect(0,0,w,h);
  const pts=app.memory.slice(-80).map(x=>x.rss_kb||0); if(pts.length<2)return;
  const min=Math.min(...pts)*.98,max=Math.max(...pts)*1.02||1; ctx.strokeStyle='#263244';ctx.beginPath();ctx.moveTo(0,h-1);ctx.lineTo(w,h-1);ctx.stroke();
  ctx.strokeStyle='#46d7ff';ctx.lineWidth=2;ctx.beginPath();pts.forEach((v,i)=>{const x=i/(pts.length-1)*w,y=h-8-(v-min)/(max-min||1)*(h-20);i?ctx.lineTo(x,y):ctx.moveTo(x,y)});ctx.stroke();
}

function causeClass(c){return c==='memory'?'memory':c==='game'?'game':c==='external'?'external':'center'}
function eventCard(e,compact=false){
  const changes=(e.changes||[]),written=e.memory_written||[],source={memory:'Память',game:'Файлы игры','control-center':'Менеджер',external:'Внешнее',rollback:'Откат'}[e.cause]||e.cause;
  return `<article class="timeline-event" data-event-key="${esc(e.id ?? e.snapshot ?? `${e.timestamp}:${e.title}`)}"><i class="dot ${causeClass(e.cause)}"></i><div><h4>${esc(e.title)}</h4><time>${fmtTime(e.timestamp)} · ${esc(source)}</time>${written.length?`<p class="memory-saved">Значения, ранее замеченные в памяти, записаны в ${esc([...new Set(written.flatMap(c=>c.files))].join(', '))}. Повторный diff скрыт (${written.length} полей).</p><details><summary>Какие поля сохранены</summary>${written.map(c=>`<div>${esc(c.label)} · ${esc(c.files.join(', '))}</div>`).join('')}</details>`:''}${changes.length?`<details><summary>${changes.length} подробных изменений</summary>${changes.slice(0,compact?3:200).map(c=>`<div class="change-row"><b>${esc(c.label||c.path)}${c.files?.length?`<small class="file-targets">${esc(c.files.join(' + '))}</small>`:''}</b><code>${esc(c.before)}</code><span>→</span><code>${esc(c.after)}</code><span>${esc(c.explanation||'')}</span></div>`).join('')}${changes.length>(compact?3:200)?'<p>Показана часть этой группы. Полная запись остаётся в журнале.</p>':''}</details>`:''}</div>${e.snapshot?`<button class="rollback-btn" data-snapshot="${esc(e.snapshot)}">↶ Откатить</button>`:''}</article>`;
}
function renderEventList(root,events,compact,emptyHtml){
  const key=JSON.stringify([compact,events]);
  if(root._renderKey===key)return;
  const opened=new Set($$('.timeline-event details[open]',root).map(detail=>{
    const event=detail.closest('.timeline-event');
    const kind=detail.querySelector('summary')?.textContent.startsWith('Какие поля')?'written':'changes';
    return `${event.dataset.eventKey}\u0000${kind}`;
  }));
  root.innerHTML=events.map(event=>eventCard(event,compact)).join('')||emptyHtml;
  $$('.timeline-event details',root).forEach(detail=>{
    const event=detail.closest('.timeline-event');
    const kind=detail.querySelector('summary')?.textContent.startsWith('Какие поля')?'written':'changes';
    detail.open=opened.has(`${event.dataset.eventKey}\u0000${kind}`);
  });
  root._renderKey=key;
}
function renderRecent(){renderEventList($('#recentEvents'),app.history.slice(0,4),true,'<div class="empty">История пока пуста</div>')}

function requirementReady(req,save){
  if(req.startsWith('plot >='))return Number(save.plot)>=Number(req.split('>=')[1]);
  if(req.startsWith('plot >'))return Number(save.plot)>Number(req.split('>')[1]);
  const m=req.match(/flag\[(\d+)\]\s*=\s*(\d+)/); if(m)return Number(save.flags[Number(m[1])])===Number(m[2]);
  return false;
}
function renderFun(){
  const saveName=$('#funSave').value,save=activeSave(saveName);
  const q=$('#funSearch').value.toLowerCase(),only=$('#onlyReady').checked;
  const rows=app.catalog.fun_events.filter(e=>JSON.stringify(e).toLowerCase().includes(q)).map(e=>({...e,ready:!!save&&e.conditions.every(c=>conditionReady(c,save))})).filter(e=>!only||e.ready);
  $('#funRoute').innerHTML=rows.map(e=>`<article class="card fun-card"><header><span class="route-order">${e.order}</span><div><h3>${esc(e.event)}</h3><small>${esc(e.region)}</small></div><span class="fun-value">FUN ${e.value}</span></header><p>${esc(e.natural)}</p><p><b>Шанс:</b> ${esc(e.chance)}</p><ul>${e.conditions.map(c=>`<li class="${conditionReady(c,save)?'ready':'not-ready'}">${conditionReady(c,save)?'✓':'△'} ${esc(conditionLabel(c))} · сейчас ${esc(conditionValue(c[0],save))}</li>`).join('')}</ul><div class="inline-form"><button class="prepare-fun" data-value="${e.value}">Проверить и выставить FUN в сейве + INI</button><button class="force-fun primary" data-value="${e.value}">Включить live / убрать случайность</button></div><small>Live обновит текущую комнату. Если ты в другом месте — дойди до указанной комнаты. Сюжет и убийства автоматически не меняются.</small></article>`).join('')||'<div class="card">Ничего не найдено</div>';
  $$('.force-fun').forEach(button=>{const plan=document.createElement('button');plan.className='prepare-conditions';plan.dataset.value=button.dataset.value;plan.textContent='Подготовить условия — показать план';button.parentElement.append(plan);});
}
function murderLevel(s){let n=0;const checks=[s.flags[202]>=20,s.flags[45]===4,s.flags[52]===1,s.flags[53]===1,s.flags[54]===1,s.flags[57]===2,s.flags[203]>=16,s.flags[67]===1,s.flags[81]===1,s.flags[252]===1,s.flags[204]>=18,s.flags[251]===1&&s.flags[350]===1,s.flags[402]===1,s.flags[397]===1,s.flags[205]>=40,s.flags[425]===1&&s.flags[27]===0];for(const ok of checks){if(!ok)break;n++}return s.flags[26]>0?s.flags[26]:n}
function conditionValue(path,save){if(!save)return 'нет сейва';return path==='murderlv'?murderLevel(save):path==='shrine'?Number(app.catalog.bonus?.mode??app.state.config?.General?.ds??0):valueAt(save,path)}
function conditionReady([path,op,v],save){if(!save)return false;const x=conditionValue(path,save);return op==='='?Number(x)===v:op==='<'?x<v:op==='>'?x>v:x>=v}
function conditionLabel([path,op,v]){const label=path.startsWith('flags.')?app.catalog.flags[Number(path.split('.')[1])].title:({plot:'Сюжетный этап',shrine:'Бонус (0:нет, 1:PS4, 2:Switch, 3:Xbox, 4:10-летие)',murderlv:'Прогресс маршрута убийств'}[path]||path);return `${label}: ${op} ${v}`}

async function prepareFunConditions(value){
  const event=app.catalog.fun_events.find(e=>e.value===value),save=activeSave($('#funSave').value);
  if(!save)return toast('Сначала сохранись у звезды: нет файла для плана изменений.',true);
  const changes=[{path:'flags.5',value}],notes=[];
  for(const condition of event.conditions){
    if(conditionReady(condition,save))continue;
    const [path,op,target]=condition;
    if(path==='shrine'){notes.push('Бонус Switch/Xbox/10-летие выбери в настройках самой игры; этот план не меняет бонус.');continue;}
    if(path==='murderlv'){changes.push({path:'flags.26',value:1});notes.push('flag[26]=1 принудительно подменяет весь вычисляемый уровень маршрута, а не только появление NPC. Настоящие убийства остаются. После просмотра верни прежнее значение.');continue;}
    const next=op==='='||op==='>='?target:op==='>'?target+1:target-1;
    changes.push({path,value:next});
    if(path==='plot')notes.push(`plot → ${next} (${plotName(next)}): это перемещение сюжетного счётчика, а не прохождение/отмена сцен. Остальные сюжетные флаги не подгоняются.`);
    if(path==='flags.7')notes.push(`flag[7] → ${next}: меняется эпилог всего мира, а не только это событие. Сохрани прежнее значение.`);
  }
  await reviewChanges(changes,$('#funSave').value);
  if(app.modal){const note=document.createElement('section');note.className='issue warn';note.textContent=['Это искусственная подготовка, не естественное прохождение. Для дискового плана перезагрузи сейв; live-кнопка отдельно убирает случайность. Инвентарь и память о концовках не изменяются.',...notes].join(' ');$('#modalBody').prepend(note);}
}

function options(items,value,label=x=>x.name){return items.map(x=>`<option value="${esc(x.id??x.value)}" ${Number(x.id??x.value)===Number(value)?'selected':''}>${esc(x.id??x.value)} — ${esc(label(x))}</option>`).join('')}
function inputField(label,path,value,hint='',type='number',extra=''){return `<div class="field"><label>${esc(label)}</label><input data-path="${path}" type="${type}" value="${esc(value)}" ${extra}><small>${esc(hint)}</small></div>`}
function selectField(label,path,value,opts,hint=''){return `<div class="field"><label>${esc(label)}</label><select data-path="${path}">${opts}</select><small>${esc(hint)}</small></div>`}
function renderSaveEditor(){
  const saveName=$('#saveSelect').value,source=activeSave(saveName);if(!source){$('#saveEditor').innerHTML='<p>Этот файл отсутствует. Начни игру и сохранись у звезды.</p>';return;} const save=structuredClone(source); for(const [path,value] of app.pending){const parts=path.split('.');let target=save;for(const part of parts.slice(0,-1))target=target[part];target[parts.at(-1)]=value;} app.pendingSave=saveName;
  let html='';
  if(app.saveSection==='core')html=`<div class="form-grid">${inputField('Имя','name',save.name,'Строка; отображается в меню','text')}${inputField('LV','lv',save.lv,'1–20; согласуется с EXP', 'number','min="1" max="20"')}${inputField('EXP','xp',save.xp,'scr_levelup вычисляет из него LV')}${inputField('Максимум HP','maxhp',save.maxhp,'Обычно 16 + LV×4')}${inputField('Максимум EN','maxen',save.maxen,'Служебная шкала энергии')}${inputField('Базовая AT','at',save.at,'Обычно 8 + LV×2')}${inputField('Сила оружия','weapon_strength',save.weapon_strength,'Добавка экипированного оружия')}${inputField('Базовая DF','df',save.df,'Обычно 9 + ceil(LV/4)')}${inputField('Защита брони','armor_defense',save.armor_defense,'Добавка экипированной брони')}${inputField('Скорость','sp',save.sp,'Стандарт старта — 4')}${inputField('Золото','gold',save.gold,'Неотрицательное игровое число')}${inputField('Убийства','kills',save.kills,'Влияет на маршрут и NPC')}</div>`;
  if(app.saveSection==='inventory')html=`<div class="inventory-grid">${save.inventory.map((slot,i)=>`<div class="inventory-slot"><span>#${i+1}</span><select data-path="inventory.${i}.item">${options(app.catalog.items,slot.item,x=>`${x.name} · ${x.kind}`)}</select><select data-path="inventory.${i}.phone"><option value="0" ${Number(slot.phone)===0?'selected':''}>0 — Нет контакта</option>${app.catalog.phones.filter(x=>x.id!==0&&!x.variant).map(x=>`<option value="${x.id}" ${Number(slot.phone)===x.id?'selected':''}>${x.id} — ${esc(x.name)}</option>`).join('')}</select></div>`).join('')}</div><div class="form-grid" style="margin-top:16px">${selectField('Экипированное оружие','weapon',save.weapon,options(app.catalog.items.filter(x=>x.kind==='оружие'||x.id===3),save.weapon,x=>x.name),'Только предметы, которые игра описывает как оружие')}${selectField('Экипированная броня','armor',save.armor,options(app.catalog.items.filter(x=>x.kind==='броня'||x.id===4),save.armor,x=>x.name),'Только предметы, которые игра описывает как броню')}</div>`;
  if(app.saveSection==='world')html=`<div class="form-grid">${selectField('Сюжетный этап (plot)','plot',save.plot,options(app.catalog.plots,save.plot,x=>x.title),'Только значения, которые код реально присваивает')}${selectField('Комната','room',save.room,options(app.catalog.rooms,save.room,x=>x.label),'ID из таблицы комнат текущей сборки')}${selectField('Музыка','song',save.song,`<option value="-1" ${Number(save.song)===-1?'selected':''}>-1 — Автовыбор комнаты</option>${options(app.catalog.sounds,save.song,x=>x.name)}`,'ID ресурса звука или -1')}${inputField('Время в тиках','time',save.time,'30 тиков = 1 секунда')}${`<div class="field"><label>Игровое время (IGT)</label><div class="stat"><b id="timeHuman">${esc(save.playtime.label)}</b><small>${(Number(save.time)/30).toFixed(2)} секунд</small></div><small>Пересчитывается сразу при вводе тиков</small></div>`}${selectField('FUN (flag[5])','flags.5',save.flags[5],Array.from({length:101},(_,i)=>`<option ${Number(save.flags[5])===i?'selected':''} value="${i}">${i}</option>`).join(''),'0 — выключено/использовано; 1–100 — номер мира')}</div>`;
  if(app.saveSection==='raw')html=`<div class="form-grid">${inputField('Последнее меню 1','menu.0',save.menu[0],'Позиция курсора')}${inputField('Последнее меню 2','menu.1',save.menu[1],'Позиция курсора')}${inputField('Последнее меню 3','menu.2',save.menu[2],'Позиция курсора')}${inputField('Xbox disconnect','xbox_disconnect',save.xbox_disconnect??0,'Поле новых сборок')}${inputField('Монеты Xbox/Dog Shrine','xbox_coins',save.xbox_coins??save.flags[299],'Должно совпадать с flag[299]')}</div><div class="hint" style="margin-top:16px">Остальные 512 служебных полей доступны во вкладке «Все флаги», где подтверждённые объяснения отделены от ещё не разобранных полей.</div>`;
  if(app.saveSection==='ini'){
    const cfg=app.state.config||{},general=cfg.General||{},joy=cfg.joypad1||{},ini=app.state.ini?.General||{};
    html=`<span class="eyebrow">CONFIG.INI</span><h3>Язык, бонусы и управление</h3><div class="form-grid"><div class="field"><label>Язык</label><select data-ini-file="config.ini" data-ini-section="General" data-ini-key="lang"><option value="ru" ${general.lang==='ru'?'selected':''}>Русский</option><option value="en" ${general.lang==='en'?'selected':''}>English</option><option value="ja" ${general.lang==='ja'?'selected':''}>日本語</option></select><small>Ключ General/lang</small></div><div class="field"><label>Бонусный набор</label><select data-ini-file="config.ini" data-ini-section="General" data-ini-key="ds"><option value="0" ${Number(general.ds||0)===0?'selected':''}>0 — без бонуса</option><option value="1" ${Number(general.ds)===1?'selected':''}>1 — PS4</option><option value="2" ${Number(general.ds)===2?'selected':''}>2 — Switch</option><option value="3" ${Number(general.ds)===3?'selected':''}>3 — Xbox</option><option value="4" ${Number(general.ds)===4?'selected':''}>4 — 10-летие</option></select><small>global.shrine; одновременно выбирается только один</small></div>${['b0','b1','b2','as','jd'].map(k=>inputField(`joypad1/${k}`,`ini-placeholder-${k}`,joy[k]??-1,'Код назначения из config.ini')).join('')}</div><div class="detail-block"><span class="eyebrow">UNDERTALE.INI</span><h3>Сводка стартового экрана</h3><div class="form-grid">${['Room','Kills','Time','Love','Name','fun','BC','Gameover'].map(k=>`<div class="field"><label>${k}</label><input data-ini-file="undertale.ini" data-ini-section="General" data-ini-key="${k}" value="${esc(ini[k]??'')}"><small>General/${k}</small></div>`).join('')}</div></div><button class="primary" id="applyIni">Проверить и записать INI</button>`;
    setTimeout(()=>{$$('[data-path^="ini-placeholder-"]').forEach(el=>{const key=el.dataset.path.replace('ini-placeholder-','');el.removeAttribute('data-path');el.dataset.iniFile='config.ini';el.dataset.iniSection='joypad1';el.dataset.iniKey=key});$$('[data-ini-file]',$('#saveEditor')).forEach(el=>el.dataset.initialValue=el.value)},0);
  }
  $('#saveEditor').innerHTML=html; $('.sticky-actions').style.display=app.saveSection==='ini'?'none':'flex'; updateDirty();
}
function updateDirty(){const n=app.pending.size;$('#dirtyState').textContent=n?`${n} несохранённых изменений`:'Нет изменений';$('#reviewChanges').disabled=!n}
function clearPending(){app.pending.clear();updateDirty();renderSaveEditor()}
function collectChange(path,value){const save=activeSave($('#saveSelect').value);let parsed=value;if(path!=='name'){const n=Number(value);parsed=Number.isFinite(n)?n:value}if(String(valueAt(save,path))===String(parsed))app.pending.delete(path);else app.pending.set(path,parsed);updateDirty();if(path==='time')$('#timeHuman').textContent=ticksLabel(parsed)}
function valueAt(obj,path){return path.split('.').reduce((a,p)=>Array.isArray(a)?a[Number(p)]:a[p],obj)}
function ticksLabel(v){let s=Math.floor(Number(v||0)/30),h=Math.floor(s/3600);s%=3600;return `${String(h).padStart(2,'0')}:${String(Math.floor(s/60)).padStart(2,'0')}:${String(s%60).padStart(2,'0')}`}

async function reviewChanges(changes=null,saveName=null){
  const list=changes||[...app.pending].map(([path,value])=>({path,value}));const save=saveName||$('#saveSelect').value;if(!list.length)return;
  try{const preview=await api('/api/preview',{method:'POST',body:JSON.stringify({save,changes:list,mode:app.settings?.write_mode||'coupled'})});app.modal={save,changes:list,preview};openReview(preview)}catch(e){toast(e.message,true)}
}
function openReview(preview){
  const v=preview.validation; $('#modalBody').innerHTML=`<div class="diff-grid">${preview.changes.map(c=>`<div class="diff-item"><b>${esc(c.label)}</b><code>${esc(c.before)}</code><span>→</span><code>${esc(c.after)}</code></div>`).join('')}</div>${v.errors.length?`<h3>Критические ошибки</h3>${v.errors.map(x=>`<div class="issue error">${esc(x.path)} · ${esc(x.message)}</div>`).join('')}`:''}${v.suggestions.length?`<h3>Предлагаемые согласования</h3>${v.suggestions.map(s=>`<label class="suggestion"><input type="checkbox" data-suggestion="${esc(s.id)}" checked><span><b>${esc(s.path)} → ${esc(s.value)}</b><small>${esc(s.reason)}</small></span></label>`).join('')}`:'<div class="ok-block" style="margin-top:14px">✓ Дополнительных исправлений не требуется</div>'}`;
  const group=document.createElement('p');group.className='issue';group.textContent=`Режим: ${preview.mode==='coupled'?'связанный':'НЕЗАВИСИМЫЙ'}. Будут записаны: ${preview.files?.join(', ')}. При запущенной игре дисковая запись запрещена.`;$('#modalBody').prepend(group);
  if(v.warnings.length){const warning=document.createElement('section');warning.innerHTML='<h3>Предупреждения — можно принять риск или отменить запись</h3>'+v.warnings.map(x=>`<div class="issue warn"><b>${esc(x.path)}</b> · ${esc(x.message)}</div>`).join('');$('#modalBody').append(warning);}
  $('#modalBackdrop').classList.add('open'); $('#confirmApply').disabled=v.errors.some(error=>!v.suggestions.some(s=>s.path===error.path));
}
function closeModal(){app.modal=null;$('#modalBackdrop').classList.remove('open')}
async function confirmApply(){
  if(!app.modal)return;const accepted=$$('[data-suggestion]:checked',$('#modalBody')).map(x=>x.dataset.suggestion);
  try{const result=await api('/api/apply',{method:'POST',body:JSON.stringify({save:app.modal.save,changes:app.modal.changes,accepted,hash:app.modal.preview.hash,bundle_hash:app.modal.preview.bundle_hash,mode:app.modal.preview.mode})});if(!result.queued)toast(`Применено: ${result.changes.length} изменений`);closeModal();app.pending.clear();await refreshAll()}catch(e){toast(e.message,true)}
}

function renderFlags(){
  const save=activeSave($('#flagSave').value)||{flags:Array(512).fill('—')};const q=$('#flagSearch').value.toLowerCase(),filter=$('#flagFilter').value;
  const rows=app.catalog.flags.filter(f=>filter==='all'||filter==='used'&&f.used||filter==='unused'&&!f.used||filter==='changed'&&Number(save.flags[f.id])!==0).filter(f=>`${f.id} ${f.title} ${f.purpose} ${f.references.join(' ')}`.toLowerCase().includes(q));
  $('#flagsTable').innerHTML=rows.map(f=>`<tr data-flag="${f.id}" class="${app.selectedFlag===f.id?'selected':''}"><td class="flag-id">${f.id}</td><td class="flag-value" data-disk-flag="${f.id}"><code>${esc(save.flags[f.id])}</code></td><td data-live-flag="${f.id}">—</td><td><b>${esc(f.title)}</b><br><small>${esc(f.purpose.slice(0,150))}</small></td><td>${f.classification==='reserved'?'Не используется':f.reviewed?'Разобран вручную':'Не расшифрован'}</td></tr>`).join('');
  if(typeof updateLiveFlagCells==='function')updateLiveFlagCells();
  if(app.selectedFlag!=null)renderFlagDetail(app.selectedFlag);
}
function renderFlagDetail(id){
  app.selectedFlag=id;const f=app.catalog.flags[id],save=activeSave($('#flagSave').value),value=save?.flags[id]??0;
  $('#flagDetail').innerHTML=`<span class="eyebrow">GLOBAL.FLAG[${id}] · ${f.reviewed?'РАЗОБРАН':'НЕ РАСШИФРОВАН'}</span><h2>${esc(f.title)}</h2><p>${esc(f.purpose)}</p>${f.natural?`<div class="detail-block"><h4>Как получить в игре</h4><p>${esc(f.natural)}</p></div>`:''}<div class="detail-block"><h4>Выбрать значение и последствие</h4>${f.options?.length?`<label class="field"><select id="flagChoice"><option value="custom">Своё число</option>${f.options.map(o=>`<option value="${o.value}" ${Number(value)===o.value?'selected':''}>${o.value} — ${esc(o.label)}</option>`).join('')}</select></label><ul>${f.options.map(o=>`<li><code>${o.value}</code> — ${esc(o.label)}</li>`).join('')}</ul>`:''}<p>${esc(f.recommended)}</p><div class="inline-form"><input id="flagEditValue" aria-label="Числовое значение флага" type="number" step="any" value="${esc(value)}"><button id="saveFlagBtn">Проверить запись</button><button class="primary" id="hotThisFlag">Применить live</button></div><div class="hint">Live меняет память и обновляет комнату вне боя/диалога. Для записи результата в сейв сохранись у звезды.</div></div><details class="detail-block"><summary>Где и как используется в коде (${f.references.length} обращений)</summary><div class="tag-list">${f.references.map(x=>`<span class="tag">${esc(x)}</span>`).join('')}</div>${f.contexts.map(x=>`<span class="code-line">${esc(x.source)}:${x.line}  ${esc(x.code)}</span>`).join('')}<p>Числа из сравнений сами по себе не задают допустимый диапазон.</p></details>`;
  $$('[data-flag]').forEach(x=>x.classList.toggle('selected',Number(x.dataset.flag)===id));
}

function renderStory(){
  const save=activeSave($('#storySave').value)||{plot:null};const q=$('#plotSearch').value.toLowerCase();$('#currentPlot').textContent=save.plot===null?'Нет сейва: справочник доступен, для записи сначала сохранись в игре.':`Текущий plot: ${save.plot} · ${plotName(save.plot)}`;
  const rows=app.catalog.plots.filter(p=>`${p.value} ${p.title} ${p.region} ${p.sources.join(' ')}`.toLowerCase().includes(q));
  $('#plotTimeline').innerHTML=rows.map(p=>`<div class="plot-row ${Number(p.value)===Number(save.plot)?'current':''}"><span class="plot-value">${esc(p.value)}</span><span class="plot-region">${esc(p.region)}</span><div><b>${esc(p.title)}</b><p>${esc(p.description||'')}</p><details><summary>Источник</summary>${esc(p.sources.join(' · '))}</details></div><button class="set-plot" data-plot="${p.value}">${Number(p.value)===Number(save.plot)?'Текущий':'Выбрать'}</button></div>`).join('');
  if(save.plot===null){$$('.plot-row.current').forEach(row=>row.classList.remove('current'));$$('.set-plot').forEach(button=>{button.disabled=true;button.textContent='Нет сейва';});}
}

function renderHistory(){
  const q=$('#historySearch').value.toLowerCase(),cause=$('#historyCause').value;
  const events=app.history.filter(e=>cause==='all'||e.cause===cause).filter(e=>JSON.stringify(e).toLowerCase().includes(q));renderEventList($('#historyTimeline'),events,false,'<div class="card">Событий не найдено</div>');
}
function renderDev(){
  $('#devGrid').innerHTML=app.catalog.dev_features.map(x=>`<div class="dev-card"><b>${esc(x.name)}</b><kbd>${esc(x.key)}</kbd><p>${esc(x.effect)}<br>${esc(x.where)}</p><span class="${x.safe?'safe-mark':'unsafe-mark'}">${x.safe?'● локальное действие':'▲ может менять ход игры'}</span></div>`).join('');
  const m=app.state.game,last=app.memory.at(-1)||{};$('#memoryPid').textContent=m.running?`PID ${m.pid} · ${app.memory.length} замеров`:'игра не запущена';const fields=[['RSS',fmtKb(m.rss_kb)],['Δ RSS',last.delta_rss_kb==null?'—':`${last.delta_rss_kb>=0?'+':''}${fmtKb(last.delta_rss_kb)}`],['Virtual',fmtKb(m.virtual_kb)],['Δ Virtual',last.delta_virtual_kb==null?'—':`${last.delta_virtual_kb>=0?'+':''}${fmtKb(last.delta_virtual_kb)}`],['Data',fmtKb(m.data_kb)],['Swap',fmtKb(m.swap_kb)],['Потоки',m.threads??'—'],['Дескрипторы',m.fds??'—']];
  $('#memoryFull').innerHTML=fields.map(x=>`<div class="mini-metric"><span>${x[0]}</span><b>${x[1]}</b></div>`).join('');
}
function renderGuide(){ $('#saveLayout').innerHTML=`<div class="head">Строки</div><div class="head">Назначение</div><div class="head">Тип</div>${app.catalog.save_layout.map(x=>`<div><code>${x.range}</code></div><div>${esc(x.name)}</div><div>${esc(x.type)}</div>`).join('')}` }

async function hotFlag(index,value){if(!await ask(`Изменить flag[${index}] на ${value} в памяти игры и обновить комнату? Это сбросит позиции объектов комнаты; сейв автоматически не записывается.`))return;try{const r=await api('/api/hot-flag',{method:'POST',body:JSON.stringify({index,value})});app.awaitingSeq=r.seq;toast(r.message)}catch(e){toast(e.message,true)}}
async function launch(){try{const r=await api('/api/launch',{method:'POST',body:'{}'});toast(r.message);setTimeout(refreshState,1800)}catch(e){toast(e.message,true)}}
async function snapshot(title='Ручной защитный снимок'){try{await api('/api/backup',{method:'POST',body:JSON.stringify({title})});toast('Снимок сохранён');await refreshHistory()}catch(e){toast(e.message,true)}}
async function rollback(id){if(!await ask(`Откатить все файлы к снимку ${id}? Перед откатом будет создан ещё один защитный снимок.`))return;try{const r=await api('/api/rollback',{method:'POST',body:JSON.stringify({snapshot:id})});if(!r.queued)toast(`Восстановлено: ${r.restored.join(', ')}`);await refreshAll()}catch(e){toast(e.message,true)}}

function renderLocation(){
  const d=app.state?.discovery,select=$('#profileSelect');if(!d||!select)return;
  const key=JSON.stringify(d.profiles);
  if(select.dataset.profiles!==key){select.dataset.profiles=key;select.innerHTML='<option value="auto">Автоматически — рабочая папка игры</option>'+d.profiles.map(p=>`<option value="${esc(p.path)}">Вручную: ${esc(p.name)}${p.active?' · активная':' · архив'}</option>`).join('');}
  if(select.value!==d.selection){select.value=d.selection;select.dispatchEvent(new Event('change'));}
  $('#profileNote').textContent=`${d.automatic?'Автопоиск':'РУЧНОЙ ВЫБОР'}: ${d.selected}. ${d.error||d.source}${d.pid?' · PID '+d.pid:''}. ${d.selected!==d.save_dir?'ВНИМАНИЕ: это не папка запущенной сборки.':''}`;
}
async function refreshState(){const previous=app.state?.paths?.save;app.state=await api('/api/state');const changed=previous&&previous!==app.state.paths.save;if(changed){app.pending.clear();app.modal=null;closeModal();if(typeof bonusPlan!=='undefined')bonusPlan=null;if(typeof rawEditorHash!=='undefined')rawEditorHash=null;if($('#rawFilePanel'))$('#rawFilePanel').hidden=true;toast('Рабочая папка изменилась. Старые планы записи и правки формы отменены.',true);}renderDashboard();renderDev();if(!previous||changed){renderFun();renderSaveEditor();renderFlags();renderStory();}else{const note=$('#dirtyState');if(note&&app.pending.size===0)note.textContent='Данные на диске обновляются в фоне; форма сохраняется до твоего действия';}}
async function refreshHistory(){const next=(await api('/api/timeline')).events;if(JSON.stringify(next)===JSON.stringify(app.history))return;app.history=next;renderRecent();renderHistory()}
async function refreshMemory(){const d=await api('/api/memory');app.memory=d.samples||[];if(app.state){app.state.game=d.current;renderDashboard();renderDev()}}
async function refreshRuntime(){
  const r=await api('/api/runtime');app.runtime=r;if(typeof refreshBonusContext==='function')await refreshBonusContext();
  if(typeof updateLiveFlagCells==='function')updateLiveFlagCells();
  $('#runtimeStatus').textContent=r.connected?`● Модуль подключён · plot ${r.current?.plot} · IGT ${ticksLabel(r.current?.ticks)}${r.current?.inbattle?' · бой':''}${r.current?.interacting?' · диалог':''}`:'○ Нет свежих данных от игрового модуля. Ранее записанные сплиты сохранены.';
  if(app.awaitingSeq&&r.ack?.seq===app.awaitingSeq){toast(r.ack.kind<0?'Игра отклонила команду: условия сменились':'Игра подтвердила выполнение live-команды',r.ack.kind<0);app.awaitingSeq=null}
  const flagKey=JSON.stringify(r.flags||[]);if(flagKey!==app.lastRuntimeFlags){app.lastRuntimeFlags=flagKey;$('#liveFlagChanges').innerHTML=(r.flags||[]).slice(0,80).map(change=>{const f=app.catalog.flags[change.index];const label=v=>f.options?.find(o=>o.value===v)?.label||String(v);return `<article class="live-diff"><b>flag[${change.index}] · ${esc(f.title)}</b><p>${esc(label(change.before))} → ${esc(label(change.after))}</p><small>IGT ${ticksLabel(change.ticks)} · ${esc(f.purpose)}</small></article>`}).join('')||'<p>Изменения ещё не записаны. Здесь показываются значения из памяти, даже без сохранения у звезды. Объяснение описывает последствие; по одному флагу нельзя доказать точное действие игрока.</p>';}
  const rows=r.splits||[],key=JSON.stringify(rows);if(key===app.lastSplits)return;app.lastSplits=key;
  $('#splitTimes').innerHTML=rows.length?`<table class="split-table"><thead><tr><th>Достигнутый этап</th><th>IGT отрезка</th><th>IGT всего</th><th>RTA отрезка</th><th>Примечание</th></tr></thead><tbody>${rows.slice(0,200).map(s=>`<tr><td>${s.previous} → ${s.plot}<br>${esc(plotName(s.plot))}</td><td>${s.segment_ticks==null?'—':ticksLabel(s.segment_ticks)}</td><td>${ticksLabel(s.ticks)}</td><td>${(s.segment_wall_ms/1000).toFixed(2)} с</td><td>Сессия ${s.session}${s.rewound?' · загрузка/возврат назад':''}${s.edited?' · после вмешательства редактора':''}${s.initial?' · первый неполный отрезок':''}</td></tr>`).join('')}</tbody></table>`:'<p>Переходы пока не записаны. Нужен запуск игры с модулем и изменение сюжетного этапа; сохранение у звезды не требуется.</p>';
}
async function refreshAll(){try{await Promise.all([refreshState(),refreshHistory(),refreshMemory()]);if(!app.pending.size){renderSaveEditor();renderFlags();}renderFun();renderStory();}catch(e){toast(`Не удалось обновить: ${e.message}`,true)}}

document.addEventListener('click',async e=>{
  const nav=e.target.closest('[data-view]');if(nav)return go(nav.dataset.view);
  const goBtn=e.target.closest('[data-go]');if(goBtn)return go(goBtn.dataset.go);
  const sec=e.target.closest('[data-save-section]');if(sec){app.saveSection=sec.dataset.saveSection;localStorage.setItem('ucc-save-section',app.saveSection);$$('[data-save-section]').forEach(x=>x.classList.toggle('active',x===sec));return renderSaveEditor()}
  const flag=e.target.closest('[data-flag]');if(flag)return renderFlagDetail(Number(flag.dataset.flag));
  const prep=e.target.closest('.prepare-fun');if(prep)return reviewChanges([{path:'flags.5',value:Number(prep.dataset.value)}],$('#funSave').value);
  const conditions=e.target.closest('.prepare-conditions');if(conditions)return prepareFunConditions(Number(conditions.dataset.value));
  const force=e.target.closest('.force-fun');if(force){const event=app.catalog.fun_events.find(x=>x.value===Number(force.dataset.value));if(!await ask(`${event.event}\nFUN в памяти и INI будет ${event.value}. Комната обновится, текущие несохранённые позиции объектов сбросятся. Случайный бросок будет принудительным для последователей, Sound Test и двери Mystery Man. Остальные сюжетные условия остаются обязательными.\nПродолжить?`))return;try{const r=await api('/api/force-fun',{method:'POST',body:JSON.stringify({value:event.value})});app.awaitingSeq=r.seq;toast(r.message)}catch(err){toast(err.message,true)}return}
  const plot=e.target.closest('.set-plot');if(plot)return reviewChanges([{path:'plot',value:Number(plot.dataset.plot)}],$('#storySave').value);
  const rb=e.target.closest('.rollback-btn');if(rb)return rollback(rb.dataset.snapshot);
  if(e.target.id==='launchBtn')return launch(); if(e.target.id==='snapshotBtn'||e.target.id==='manualSnapshot')return snapshot();
  if(e.target.id==='refreshBtn')return refreshAll(); if(e.target.id==='discardChanges')return clearPending(); if(e.target.id==='reviewChanges')return reviewChanges();
  if(e.target.id==='closeModal'||e.target.id==='cancelApply')return closeModal();if(e.target.id==='confirmApply')return confirmApply();
  if(e.target.id==='saveFlagBtn')return reviewChanges([{path:`flags.${app.selectedFlag}`,value:Number($('#flagEditValue').value)}],$('#flagSave').value);
  if(e.target.id==='hotThisFlag')return hotFlag(app.selectedFlag,Number($('#flagEditValue').value));
  if(e.target.id==='hotFlagBtn')return hotFlag(Number($('#hotFlagIndex').value),Number($('#hotFlagValue').value));
  if(e.target.id==='applyIni'){
    const groups={};$$('[data-ini-file]',$('#saveEditor')).filter(el=>el.value!==el.dataset.initialValue).forEach(el=>{(groups[el.dataset.iniFile]??=[]).push({section:el.dataset.iniSection,key:el.dataset.iniKey,value:el.value})});
    if(!Object.keys(groups).length)return toast('Нет изменений');
    try{if(app.state.game.running&&Object.keys(groups).length>1)throw new Error('Применяй по одному INI за live-транзакцию. Ничего не записано.');let queued=false;for(const [file,changes] of Object.entries(groups)){const r=await api('/api/apply-ini',{method:'POST',body:JSON.stringify({file,changes,bundle_hash:(await api('/api/files')).hash})});queued=queued||r.queued;}if(!queued)toast('INI проверены и записаны; снимки созданы');await refreshAll()}catch(err){toast(err.message,true)}return;
  }
  if(e.target.id==='openSaveFolder'){try{await api('/api/open-folder',{method:'POST',body:'{}'})}catch(err){toast(err.message,true)}return}
  if(e.target.id==='validateNow'){await refreshState();toast(`file0: ${validation('file0')?.summary||'нет файла'}; file9: ${validation('file9')?.summary||'нет файла'}`)}
});
document.addEventListener('input',e=>{
  if(e.target.matches('#funSearch,#onlyReady'))renderFun();if(e.target.matches('#flagSearch,#flagFilter'))renderFlags();if(e.target.matches('#plotSearch'))renderStory();if(e.target.matches('#historySearch,#historyCause'))renderHistory();
  if(e.target.closest('#saveEditor')&&e.target.dataset.path)collectChange(e.target.dataset.path,e.target.value);
  if(e.target.id==='hotFlagIndex'){const f=app.catalog.flags[Number(e.target.value)];$('#hotFlagHint').textContent=f?`${f.title}: ${f.purpose}`:'Флаг не найден'}
});
document.addEventListener('change',async e=>{
  if(e.target.id==='profileSelect'&&(e.isTrusted||e.uccUser)){if(app.pending.size&&!await ask('Сбросить несохранённые правки формы при смене папки?')){e.target.value=app.state.discovery.selection;e.target.dispatchEvent(new Event('change'));return;}app.pending.clear();api('/api/profile',{method:'POST',body:JSON.stringify({profile:e.target.value})}).then(refreshAll).catch(err=>toast(err.message,true));return;}
  if(e.target.id==='flagChoice'&&e.target.value!=='custom')$('#flagEditValue').value=e.target.value;
  if(e.target.id==='saveSelect'){app.pending.clear();app.pendingSave=e.target.value;renderSaveEditor()}
  if(e.target.id==='funSave')renderFun();if(e.target.id==='flagSave')renderFlags();if(e.target.id==='storySave')renderStory();
  if(e.target.closest('#saveEditor')&&e.target.dataset.path)collectChange(e.target.dataset.path,e.target.value);
});

async function init(){
  try{app.settings=await api('/api/settings');app.saveSection=localStorage.getItem('ucc-save-section')||'core';app.catalog=await api('/api/catalog');const profile=document.createElement('div');profile.className='profile-bar';profile.innerHTML='<label>Папка сохранений <select id="profileSelect"><option value="auto">Автоматически — рабочая папка игры</option></select></label><small id="profileNote"></small>';document.querySelector('#view-settings').prepend(profile);$('#flagCoverage').textContent=`Классифицировано ${app.catalog.classified_flags} из 512 ячеек: ${app.catalog.reviewed_flags} с игровой логикой, ${app.catalog.reserved_flags} не задействованы в этой сборке.`;renderGuide();await refreshAll();renderLocation();$('#profileSelect').dispatchEvent(new Event('change'));await refreshRuntime();go(app.settings.remember_view?(location.hash.slice(1)||localStorage.getItem('ucc-view')||'dashboard'):'dashboard');if(typeof refreshExtras==='function')refreshExtras();setInterval(()=>refreshState().catch(()=>{}),3500);setInterval(()=>refreshHistory().catch(()=>{}),4500);setInterval(()=>refreshMemory().catch(()=>{}),2500);setInterval(()=>refreshRuntime().catch(()=>{}),1500)}catch(e){document.body.innerHTML=`<div class="card" style="margin:40px"><h2>Control Center не запустился</h2><p>${esc(e.message)}</p></div>`}
}
init();
