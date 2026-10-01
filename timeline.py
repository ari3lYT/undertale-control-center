"""Display projection. Original file snapshots/diffs and runtime log stay intact."""
import hashlib
import json
import re
from datetime import datetime
from runtime import is_save_memory_key

FIELDS={'name':'global.charname','weapon_strength':'global.wstrength','armor_defense':'global.adef',
        'song':'global.currentsong','room':'global.currentroom','time':'obj_time.time','xbox_coins':'global.xbox_coins_donated'}
def memory_path(path):
    if path.startswith('flags.'):return 'global.flag['+path.split('.')[1]+']'
    m=re.fullmatch(r'inventory\.(\d+)\.(item|phone)',path)
    if m:return f'global.{m[2]}[{m[1]}]'
    return FIELDS.get(path,'global.'+path)

def seconds(value):
    try:return datetime.fromisoformat(value).timestamp()
    except (TypeError,ValueError):return 0

def igt_label(ticks):
    if ticks is None:return '—'
    total=max(0,int(float(ticks)//30))
    hours,remainder=divmod(total,3600)
    minutes,seconds_part=divmod(remainder,60)
    return f'{hours:02d}:{minutes:02d}:{seconds_part:02d}'

def project(events,memory,label=lambda p:p,explain=lambda p:''):
    mem=[e for e in memory if e.get('timestamp') and is_save_memory_key(e.get('path',''))]
    by_path={}
    batches={}
    for e in mem:
        by_path.setdefault(e['path'],[]).append(e)
        ident=hashlib.sha256(json.dumps([e['session'],e['wall_ms'],e['path'],e['before'],e['after']],ensure_ascii=False).encode()).hexdigest()[:16]
        group=(e['session'],int(e['wall_ms']//1000))
        batch=batches.setdefault(group,{'id':'ram-'+ident,'timestamp':e['timestamp'],'cause':'memory','title':'Изменения в памяти','ticks':e.get('ticks'),'changes':[]})
        batch['changes'].append({'path':e['path'],'label':label(e['path']),'before':e['before'],'after':e['after'],
            'explanation':f"IGT {igt_label(e.get('ticks'))} ({e.get('ticks','?')} тиков). {explain(e['path'])}",
            'source':'memory','memory_id':ident,'operation':e['operation'],
            'ticks':e.get('ticks')})
    result=[]
    for event in events:
        grouped={}
        for c in event.get('changes',[]):
            # file0 and file9 often get the same transition. Show it once.
            key=json.dumps([c.get('path'),c.get('before'),c.get('after')],ensure_ascii=False,sort_keys=True)
            if key not in grouped:grouped[key]={**c,'files':[]}
            if c.get('file') and c['file'] not in grouped[key]['files']:grouped[key]['files'].append(c['file'])
        remaining=[];written=[]
        for c in grouped.values():
            matches=[m for m in by_path.get(memory_path(c.get('path','')),[]) if m['after']==c.get('after') and seconds(m['timestamp'])<=seconds(event['timestamp'])+.6]
            if matches and c['files']:
                written.append({'label':c.get('label',c.get('path')),'files':c['files']})
            else:remaining.append(c)
        title=event['title']
        if title.startswith('Обнаружено изменений:'):
            title=f'Файлы: {len(remaining)} новых изменений, {len(written)} полей записано из наблюдавшейся памяти'
        result.append({**event,'title':title,'changes':remaining,'memory_written':written})
    for event in batches.values():
        event['title']=f"Память · изменений: {len(event['changes'])} · IGT {igt_label(event.get('ticks'))}"
        result.append(event)
    return sorted(result,key=lambda e:seconds(e['timestamp']),reverse=True)[:1000]
