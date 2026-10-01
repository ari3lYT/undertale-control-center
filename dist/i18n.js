(() => {
  'use strict';

  const messages = {
    'Обзор':'Dashboard','FUN-маршрут':'FUN route','Редактор сейва':'Save editor','Все флаги':'All flags','Сюжет':'Story',
    'История и откат':'History & rollback','Как всё устроено':'How it works','Файлы и слоты':'Files & slots','Настройки':'Settings',
    'Живое состояние игры и сохранения':'Live game and save state','Редкие события в порядке прохождения':'Rare events in play order',
    'Поля, справочники и проверяемые изменения':'Fields, references, and validated changes','Ручной разбор состояний и последствий':'Reviewed states and consequences',
    'Все реальные значения global.plot':'All known global.plot values','Семантические diff и снимки':'Semantic diffs and snapshots',
    'Hot reload, debug и память процесса':'Hot reload, debug, and process memory','Файлы, формат и логика изменений':'Files, formats, and change logic',
    'Целые состояния прохождения и исходные файлы':'Complete playthrough states and source files','Управление, runtime и поведение менеджера':'Controls, runtime, and manager behavior',
    'Проверка Undertale…':'Checking UNDERTALE…','▶ Запустить Undertale':'▶ Launch UNDERTALE','● Undertale уже запущен':'● UNDERTALE is already running',
    '＋ Снимок':'＋ Snapshot','↻ Обновить':'↻ Refresh','ТЕКУЩЕЕ СОСТОЯНИЕ':'CURRENT STATE','Читаю сохранение…':'Reading save…',
    'Редактировать сейв':'Edit save','Посмотреть историю':'View history','ДИАГНОСТИКА':'DIAGNOSTICS','Целостность сохранения':'Save integrity',
    'Золото':'Gold','Время':'Time','Статус':'Status','не запущен':'not running','Потоки':'Threads','Дескрипторы':'File descriptors',
    '✓ Известные проверки пройдены. Это не гарантия согласованности всех сюжетных зависимостей.':'✓ Known checks passed. This does not guarantee consistency of every story dependency.',
    'Процесс Undertale':'UNDERTALE process','ПОСЛЕДНИЕ СОБЫТИЯ':'RECENT EVENTS','Что менялось':'What changed','Вся история →':'Full history →',
    'Все FUN-события в порядке прохождения':'All FUN events in play order','Сейв':'Save','Только доступные сейчас':'Available now only',
    'Структурированный редактор':'Structured editor','Файл':'File','Основное':'Core','Инвентарь и телефон':'Inventory & phone',
    'Мир и время':'World & time','Служебные поля':'Internal fields','INI и управление':'INI & controls','Нет изменений':'No changes',
    'Сбросить':'Reset','Проверить и применить':'Review & apply','Флаги: действия и последствия':'Flags: actions and consequences',
    'С найденными обращениями':'Referenced in code','Все 512':'All 512','Без прямых обращений (не значит свободные)':'No direct references (not necessarily unused)',
    'Ненулевые':'Non-zero','В сейве':'In save','В памяти':'In memory','Назначение':'Purpose','Проверка смысла':'Meaning review',
    'Выбери флаг слева':'Select a flag on the left','Сплиты прохождения':'Playthrough splits','Проверка связи с игрой…':'Checking game connection…',
    'Карта сюжетных этапов':'Story progress map','Текущий plot: —':'Current plot: —','История памяти и файлов':'Memory and file history',
    'файлы':'files','менеджер':'manager','внешнее':'external','память':'memory','Все источники':'All sources','Файлы игры':'Game files',
    'Память игры':'Game memory','Центр':'Manager','Внешнее':'External','Откаты':'Rollbacks','Devtools меняют правила игры':'Devtools change game rules',
    'ЖИВОЕ УПРАВЛЕНИЕ':'LIVE CONTROL','Hot-подмена флага':'Live flag replacement','Применить live':'Apply live','СЕРВИС':'SERVICE',
    'Быстрые действия':'Quick actions','Открыть папку сохранений':'Open save folder','Сделать защитный снимок':'Create recovery snapshot',
    'Проверить оба сейва':'Validate both saves','ВСТРОЕННЫЙ DEBUG':'BUILT-IN DEBUG','Функции, найденные в коде игры':'Features found in game code',
    'Поля сохранения в памяти игры':'Save fields in game memory','Приостановить таблицу':'Pause table','Продолжить таблицу':'Resume table',
    'Переменная / объект':'Variable / object','Тип':'Type','Последний тик изменения':'Last change tick','Последние изменения полей сохранения':'Recent save-field changes',
    'ПОТРЕБЛЕНИЕ RAM':'RAM USAGE','Размер памяти процесса — не значения переменных':'Process memory size — not variable values',
    'Изменения игровых флагов в памяти':'Game flag changes in memory','Файлы и загрузка состояния':'Files and state loading',
    'ФОРМАТ FILE0/FILE9':'FILE0/FILE9 FORMAT','Разметка строк, как её читает scr_load':'Line layout as read by scr_load',
    'КАК ПРОХОДИТ ИЗМЕНЕНИЕ':'HOW A CHANGE IS APPLIED','Проверяемая транзакция':'Validated transaction','Ты выбираешь значение':'Choose a value',
    'Центр строит diff':'Manager builds a diff','Показывает конфликты':'Conflicts are shown','Ты принимаешь нужные исправления':'Accept selected fixes',
    'Снимок и запись':'Snapshot and write','ПРОВЕРКА ТРАНЗАКЦИИ':'TRANSACTION REVIEW','Что изменится':'What will change','Отмена':'Cancel',
    'Применить выбранное':'Apply selected','Подтверждение':'Confirmation','Продолжить':'Continue','Выбрать':'Select','Текущий':'Current','Источник':'Source',
    'Нет вариантов':'No options','Выбрать значение и последствие':'Choose a value and consequence','Своё число':'Custom number','Проверить запись':'Review write',
    'Как получить в игре':'How to obtain in game','Строки':'Lines','Проверка':'Validation','Разобран вручную':'Manually reviewed','Не расшифрован':'Not decoded',
    'Не используется':'Unused','локальное действие':'local action','может менять ход игры':'may alter the playthrough','Событий не найдено':'No events found',
    'Undertale завершён':'UNDERTALE stopped','↶ Откатить':'↶ Roll back','Память':'Memory',
    'История пока пуста':'History is empty','Какие поля сохранены':'Fields written to disk','Обычная игра — убрать выбор':'Normal game — clear override',
    'Случайный FUN как в оригинале':'Random FUN as in the original','Проверить и выставить FUN в сейве + INI':'Review and set FUN in save + INI',
    'Включить live / убрать случайность':'Enable live / remove randomness','Подготовить условия — показать план':'Prepare requirements — show plan',
    'Слоты прохождения':'Playthrough slots','Название нового слота':'New slot name','Сохранить текущий набор в слот':'Save current bundle to slot',
    'Создать чистый слот':'Create clean slot','Очистить текущую игру':'Reset current game','Пресеты прохождения':'Playthrough presets','Игровые файлы':'Game files',
    'Содержимое':'Contents','Проверить и записать':'Review & write','Удалить этот файл':'Delete this file','Режим записи менеджера':'Manager write mode',
    'Связанный — по умолчанию':'Coupled — default','Независимый — допускаю расхождения':'Independent — allow mismatches','Ввод в игре':'In-game input',
    'Бонусный контент и миграция':'Bonus content & migration','Без бонуса':'No bonus','10-летие':'10th anniversary','Показать план смены':'Show migration plan',
    'Папка сохранений':'Save folder','Автоматически — рабочая папка игры':'Automatic — active game folder','Автопоиск':'Automatic discovery',
    'Это варианты бонусов одной сборки, а не разные форматы сейва. PS4, Switch, Xbox и 10-летие сохраняют собственные поля прогресса. Смена не превращает пожертвования в победу над боссом.':'These are bonus variants of one build, not different save formats. PS4, Switch, Xbox, and the 10th anniversary content retain separate progress fields. Switching does not turn a donation into a boss victory.',
    'Связанный режим пишет file0, file9 и сводку INI вместе. Независимый режим намеренно допускает расхождения. Он нужен для исследования, не обещает пригодное прохождение.':'Coupled mode writes file0, file9, and the INI summary together. Independent mode intentionally permits mismatches. It is intended for research and does not promise a playable state.',
    'Журнал ограничен самой Undertale: клавиши, нажатия геймпада и мыши. Не записывает ввод других приложений. Клик содержит координаты; смысл выбранного объекта не выводится достоверно из одних координат.':'The log is limited to UNDERTALE: keyboard, gamepad, and mouse input. It does not record other applications. Clicks include coordinates; the selected object cannot be identified reliably from coordinates alone.',
    'Движение WASD':'WASD movement','Действия Z / X / C':'Z / X / C actions','Встроенный debug':'Built-in debug','Запись игровых нажатий':'Log game input',
    'Запоминать вкладку':'Remember active tab','Активировать':'Activate','Открыть':'Open','Создать':'Create','Отсутствует':'Missing','Источник':'Source',
    'При debug отключается, чтобы W не конфликтовала с замедлением.':'Disabled while debug is active so W does not conflict with slow motion.',
    'Дополняют Enter / Shift / Ctrl.':'Adds aliases for Enter / Shift / Ctrl.','Открывает отладочные клавиши игры; часть действий меняет маршрут.':'Enables the game’s debug keys; some actions alter the playthrough.',
    'Локальный журнал событий в ucc-events.log.':'Local event log in ucc-events.log.','Вкладка и раздел редактора восстанавливаются после обновления страницы.':'Restores the active tab and editor section after a page reload.',
    'Создать слот из пресета':'Create slot from preset','Включить / выключить debug':'Toggle debug','Отключить debug':'Disable debug','Включить debug':'Enable debug',
    'Частота старого полного обхода':'Legacy full-scan frequency','Полный обход старого модуля':'Legacy module full scan','Раз в секунду':'Once per second',
    'Раз в 2 секунды — меньше нагрузка':'Every 2 seconds — lower load','Каждые 500 мс':'Every 500 ms','Каждые 250 мс':'Every 250 ms',
    'Каждые 100 мс — выше нагрузка':'Every 100 ms — higher load','не получено':'not received','отсутствует':'absent','массив':'array',
    'нажато':'pressed','отпущено':'released','комната':'room','Тик':'Tick','изменилось значение':'value changed','переменная или объект исчезли':'variable or object disappeared',
    'Слот создан; текущая игра не изменена':'Slot created; current game was not changed','Слот активирован':'Slot activated','Настройка сохранена':'Setting saved',
    'Снимок сохранён':'Snapshot saved','Нет изменений':'No changes','Флаг не найден':'Flag not found','Игра подтвердила выполнение live-команды':'Game confirmed the live command',
    'Справочник игры':'Game reference','RU':'RU','EN':'EN','Русский':'Russian','English':'English'
  };

  const placeholders = {
    'Поиск события, региона или комнаты…':'Search event, region, or room…','Номер, персонаж, событие, объект…':'Number, character, event, object…',
    'Ториэль, Андайн, Ядро, 122…':'Toriel, Undyne, CORE, 122…','Искать по полю, флагу или объяснению…':'Search by field, flag, or explanation…',
    'ID флага':'Flag ID','Значение':'Value','gold, currentroom, item, flag[5]…':'gold, currentroom, item, flag[5]…',
    'Название нового слота':'New slot name','Поиск по названию или ID…':'Search by name or ID…'
  };

  const rules = [
    [/^Undertale запущен · PID (.+)$/,'UNDERTALE is running · PID $1'],[/^Undertale не запущен$/,'UNDERTALE is not running'],
    [/^Сюжет: (.+)\. FUN (.+)\. Последнее сохранённое время — (.+)\.$/,'Story: $1. FUN $2. Last saved play time — $3.'],
    [/^(\d+) ошибок · (\d+) предупреждений · (\d+) предложений$/,'$1 errors · $2 warnings · $3 suggestions'],
    [/^(\d+) подробных изменений$/,'$1 detailed changes'],[/^Текущий plot: (.+)$/,'Current plot: $1'],
    [/^PID (\d+) · (\d+) замеров$/,'PID $1 · $2 samples'],[/^(\d+) байт$/,'$1 bytes'],[/^(\d+) значений$/,'$1 values'],
    [/^Сейчас: (.+)$/,'Current: $1'],[/^Активный бонус: (.+) · источник: (.+)$/,'Active bonus: $1 · source: $2'],
    [/^В игре debug = (.+)$/,'In-game debug = $1'],[/^Сессия (.+)$/,'Session $1'],[/^Нет сейва: (.+)$/,'No save: $1'],
    [/^Восстановлено: (.+)$/,'Restored: $1'],[/^Применено: (.+) изменений$/,'Applied: $1 changes'],
    [/^Память · изменений: (\d+)(.*)$/,'Memory · changes: $1$2'],[/^Файлы · изменений: (\d+)(.*)$/,'Files · changes: $1$2'],
    [/^(.*) · Файлы игры$/,'$1 · Game files'],[/^(.*) · Память$/,'$1 · Memory'],[/^(.*) · Менеджер$/,'$1 · Manager'],[/^(.*) · Внешнее$/,'$1 · External'],
    [/^Автопоиск: (.+)$/,'Automatic discovery: $1'],[/^(.+) выбранной папки$/,'$1 selected folder'],
    [/^(Клавиша|Геймпад|Мышь) · (.+) · (нажато|отпущено) · комната (.+)$/,(match,kind,rest,state,room)=>`${{Клавиша:'Keyboard',Геймпад:'Gamepad',Мышь:'Mouse'}[kind]} · ${rest} · ${{нажато:'pressed',отпущено:'released'}[state]} · room ${room}`]
  ];

  let locale = localStorage.getItem('ucc-locale') || (navigator.language.toLowerCase().startsWith('ru') ? 'ru' : 'en');
  if (!['ru','en'].includes(locale)) locale='en';
  const originalText = new WeakMap(), originalAttrs = new WeakMap(), ownWrites = new WeakSet();

  function translated(value){
    if(locale!=='en')return value;
    const suffix=value.endsWith(' ▾')?' ▾':'';
    const source=suffix?value.slice(0,-2):value;
    if(messages[source])return messages[source]+suffix;
    for(const [pattern,replacement] of rules)if(pattern.test(source))return source.replace(pattern,replacement)+suffix;
    return value;
  }
  function writeText(node,value){if(node.nodeValue!==value){ownWrites.add(node);node.nodeValue=value;}}
  function localizeText(node,refreshOriginal=false){
    if(!node.nodeValue.trim())return;
    if(refreshOriginal||!originalText.has(node))originalText.set(node,node.nodeValue);
    const source=originalText.get(node);
    writeText(node,locale==='ru'?source:translated(source));
  }
  function localizeElement(element,refreshOriginal=false){
    if(!(element instanceof Element)||element.matches('script,style,textarea'))return;
    const attrs={};
    for(const name of ['placeholder','aria-label','title'])if(element.hasAttribute(name))attrs[name]=element.getAttribute(name);
    if(refreshOriginal||!originalAttrs.has(element))originalAttrs.set(element,attrs);
    const saved=originalAttrs.get(element)||{};
    for(const [name,value] of Object.entries(saved)){
      const next=locale==='en'?(placeholders[value]||messages[value]||translated(value)):value;
      if(element.getAttribute(name)!==next)element.setAttribute(name,next);
    }
    for(const child of element.childNodes){
      if(child.nodeType===Node.TEXT_NODE)localizeText(child,refreshOriginal);
      else if(child.nodeType===Node.ELEMENT_NODE)localizeElement(child,refreshOriginal);
    }
  }
  function updateSwitch(){
    document.documentElement.lang=locale;
    document.querySelectorAll('[data-locale]').forEach(button=>{
      const active=button.dataset.locale===locale;
      button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active));
    });
  }
  function setLocale(next){
    locale=next;localStorage.setItem('ucc-locale',locale);localizeElement(document.body);updateSwitch();
    document.dispatchEvent(new CustomEvent('ucc:localechange',{detail:{locale}}));
  }

  const observer=new MutationObserver(records=>{
    for(const record of records){
      if(record.type==='characterData'){
        if(ownWrites.has(record.target)){ownWrites.delete(record.target);continue;}
        localizeText(record.target,true);continue;
      }
      for(const node of record.addedNodes){
        if(node.nodeType===Node.TEXT_NODE)localizeText(node,true);
        else if(node.nodeType===Node.ELEMENT_NODE)localizeElement(node,true);
      }
    }
  });

  const switcher=document.createElement('div');switcher.className='locale-switch';switcher.setAttribute('role','group');switcher.setAttribute('aria-label','Language');
  switcher.innerHTML='<button type="button" data-locale="ru">RU</button><button type="button" data-locale="en">EN</button>';
  document.querySelector('.top-actions')?.prepend(switcher);
  switcher.addEventListener('click',event=>{const button=event.target.closest('[data-locale]');if(button)setLocale(button.dataset.locale);});
  observer.observe(document.body,{subtree:true,childList:true,characterData:true});
  localizeElement(document.body,true);updateSwitch();
  window.uccI18n={get locale(){return locale;},setLocale,t:key=>locale==='en'?(messages[key]||translated(key)):key};
})();
