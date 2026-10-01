"""Version-pinned source presets. Deliberately distinguish scene demos from full runs."""
import json
from pathlib import Path
from bundles import GAME_FILES, ini_bytes

DATA=json.loads((Path(__file__).parent/'data/presets.json').read_text())

def listing():
    return [dict(id=p['id'],title=p['title'],source=p['source'],status='Сценарный пресет; не подтверждён как целое последовательное прохождение',description='Исходный авторский набор Flowey’s Time Machine. Создаётся отдельный слот. Формат адаптирован к 551 строке; исходный сюжетный набор не подменяется догадками. Для активации нужно отдельно принять предупреждение.') for p in DATA]

def build(ident,config,parse,validate):
    preset=next((p for p in DATA if p['id']==ident),None)
    if preset is None: raise ValueError('Нет такого пресета')
    lines=list(preset['original']['lines'])+['0','0']
    # Current Linux build appends disconnect count and donated Xbox coins.
    lines[550]=lines[329]
    # Audio resource indexes are build-specific; let the room initialise its music.
    lines[546]='-1'
    raw='\n'.join(lines).encode();model=parse(raw)
    check=validate(model)
    if check['errors']: raise ValueError('Пресет не проходит формат текущей сборки: '+check['errors'][0]['message'])
    bundle={n:None for n in GAME_FILES};bundle['config.ini']=config
    bundle['file0']=bundle['file9']=raw
    summary={'Name':model['name'],'Love':model['lv'],'Time':model['time'],'Kills':model['kills'],'Room':model['room'],'fun':model['flags'][5]}
    ini={**preset['original']['ini'],'General':{**preset['original']['ini'].get('General',{}),**summary}}
    bundle['undertale.ini']=ini_bytes(None,ini)
    # Flowey's continuation can load file8 after the encounter.
    if ident in ('omega-flowey','asgore-normal','asgore-true'):bundle['file8']=raw
    return preset,bundle,check
