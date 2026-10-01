"""Bonus selection in this build is global.shrine, not a save-format version."""
import copy
import configparser
from bundles import ini_bytes

NAMES={0:'Без бонуса',1:'PS4',2:'Switch',3:'Xbox',4:'10-летие'}
OWNERS={157:2,158:2,159:1,160:1,161:1,162:1,163:4,292:3,293:3,294:3,295:3,297:3,298:3,299:3}
# Source: doorXmusicfade Alarm 2, mewmew room scripts, current room catalog.
ROOM_MODES={336:1,337:2,338:2,340:3,346:4}
SANS_HOUSE=77

def mode_from_config(raw):
    cp=configparser.ConfigParser(interpolation=None,strict=False)
    if raw: cp.read_string(raw.decode('utf-8-sig'))
    value=cp.get('General','ds',fallback='0').strip('" ')
    try:
        number=float(value);mode=int(number)
        if number!=mode: raise ValueError()
    except (ValueError,OverflowError): raise ValueError('config.ini General/ds должен быть целым числом 0–4')
    if mode not in NAMES: raise ValueError('Неизвестный бонус в config.ini')
    return mode

def contextual_catalog(catalog,mode,origin):
    result=copy.deepcopy(catalog)
    result['bonus']={'mode':mode,'name':NAMES[mode],'source':origin}
    for f in result['flags']:
        owner=OWNERS.get(f['id'])
        if owner is None: continue
        f['bonus_owner']=owner;f['active_in_bonus']=owner==mode
        if f['id']==292:
            f.update(title='Xbox: тройка вишен в автомате',purpose='Тройка вишен ставит 1: появляется декорация, доступна проверка dog_cherry. Начисление монет выполняет исход вращения, а не запись флага. В этой сборке текущее PS4-святилище использует 159–162, не 292. Старый обработчик коробки в trashzone1 тоже обращается к 292; это отдельный оставшийся сценарий, не миграция PS4.',options=[{'value':0,'label':'Вишни ещё не выиграны'},{'value':1,'label':'Тройка вишен выиграна'}],natural='Получить три вишни в Xbox-автомате.')
        if owner!=mode:
            f['purpose']=f'Сейчас активен «{NAMES[mode]}». Поле хранит прогресс бонуса «{NAMES[owner]}», а не активного бонуса. При смене он сохраняется. '+f['purpose']
            f['recommended']='Не преобразовывать в значение активного бонуса: это отдельное сохранённое состояние '+NAMES[owner]+'.'
        else:
            f['recommended']='Активный бонус: '+NAMES[owner]+'. Используй варианты с указанными последствиями.'
    for event in result['fun_events']:
        if event['value']==2:
            event['range']='2–100' if mode==4 else '2–39'
            event['natural']=('Активно 10-летие: расширенная песня, подходит любой FUN>1. ' if mode==4 else 'Активен '+NAMES[mode]+': обычная песня, нужен FUN 2–39. ')+'Пройди на северный причал Сноудина до сцены Монстрёнка на мосту (plot<120), вне эпилога (flag[7]=0). flag[277] должен быть 0: уже использованный редкий звонок блокирует событие.'
        if event['value']==81:
            event['natural']=('В выбранном бонусе продолжение доступно. ' if mode>=2 else 'В выбранном бонусе исчезновения нет; для этой сцены выбери Switch, Xbox или 10-летие. ')+event['natural']
    return result

def migration_plan(before,target,parse,validate):
    if isinstance(target,bool) or target not in NAMES: raise ValueError('Допустимы бонусы 0–4')
    source=mode_from_config(before.get('config.ini'))
    after=dict(before);changes=[]
    # Bonus fields are distinct in this build. Never manufacture cross-platform progress.
    for name,raw in before.items():
        if not name.startswith('file') or raw is None: continue
        model=parse(raw)
        if validate(model)['errors']: raise ValueError(name+': сначала исправь повреждённый сейв')
        room=int(model['room'])
        if room in ROOM_MODES and ROOM_MODES[room]!=target:
            lines=raw.decode('utf-8').splitlines();lines[547]=str(SANS_HOUSE);lines[546]='-1'
            after[name]='\n'.join(lines).encode()
            changes.append({'file':name,'field':'room / song','before':str(room)+' / '+str(model['song']),'after':'77 / −1','reason':'Сохранение внутри бонусной комнаты другого набора. Загрузка переносится в дом Санса перед входом; музыку выбирает комната.'})
    summary={}
    if after.get('file0') is not None and after['file0']!=before.get('file0'):
        summary={'General':{'Room':SANS_HOUSE}}
    if summary:
        cp=configparser.ConfigParser(interpolation=None,strict=False)
        if before.get('undertale.ini'):cp.read_string(before['undertale.ini'].decode('utf-8-sig'))
        old_room=cp.get('General','Room',fallback='нет поля').strip('" ')
        after['undertale.ini']=ini_bytes(after.get('undertale.ini'),summary)
        changes.append({'file':'undertale.ini','field':'General/Room','before':old_room,'after':'77','reason':'Сводка стартового экрана согласуется с перенесённым file0; остальные разделы INI сохраняются.'})
    after['config.ini']=ini_bytes(after.get('config.ini'),{'General':{'ds':target}})
    changes.insert(0,{'file':'config.ini','field':'General/ds','before':NAMES[source],'after':NAMES[target],'reason':'Меняется бонусный контент одной сборки. Формат file0/file9 не меняется.'})
    return after,{'source':source,'target':target,'changes':changes,'preserved':'Все сюжетные флаги, предметы, убийства и независимый прогресс бонусов сохраняются без конвертации. file0 и временный file9 сохраняют свои отдельные состояния.','runtime':'Без перезапуска менеджер разрешает смену только при свободном управлении в доме Санса и отсутствии сейвов в несовместимых бонусных комнатах. Иначе закрой игру и примени этот план.'}
