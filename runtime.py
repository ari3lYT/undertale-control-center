"""Read-only parser for the append-only GML runtime bridge protocol."""
import time
import math
import threading
import re
from datetime import datetime, timezone
from collections import deque
from urllib.parse import unquote


# scr_saveprocess writes these globals to file0/file9. The saved room is an
# event; the continuously ticking clock is kept only as event context,
# never as a separate diff or periodic variable entry.
SAVE_SCALARS = frozenset(('charname','lv','maxhp','maxen','at','wstrength',
    'df','adef','sp','xp','gold','kills','weapon','armor','plot',
    'currentroom','xbox_disconnect_counter','xbox_coins_donated'))
SAVE_ARRAY_LIMITS = {'flag':512, 'item':8, 'phone':8, 'menuchoice':3}
SAVE_ARRAY_KEY = re.compile(r'^global\.(flag|item|phone|menuchoice)\[(\d+)\]$')


def is_save_memory_key(key):
    if key.startswith('global.') and key[7:] in SAVE_SCALARS:
        return True
    match = SAVE_ARRAY_KEY.fullmatch(key)
    return bool(match and int(match[2]) < SAVE_ARRAY_LIMITS[match[1]])


class RuntimeLog:
    def __init__(self, path):
        self.path = path
        self.offset = 0
        self.inode = None
        self.remainder = b''
        self.session = 0
        self.anchor = None
        self.current = None
        self.splits = deque(maxlen=2000)
        self.flags = deque(maxlen=500)
        self.ack = None
        self.last_received = 0
        self.edited = False
        self.inputs = deque(maxlen=1000)
        self.settings = None
        self.lock = threading.RLock()
        self.variables = {}
        self.variable_events = deque(maxlen=2000)
        self.semantic_events = deque(maxlen=2000)
        self.live_flags = {}
        self.monitor = dict(version=5, complete_snapshot=False)
        self.live_token = None
        self.record_wall = 0
        self.backlog = 0

    def variable_record(self, parts):
        kind = parts[0]
        if kind == 'E' and len(parts) == 2:
            self.variables.clear(); self.live_flags.clear()
            self.variable_events.clear()
            self.semantic_events.clear()
            self.current=None; self.anchor=None
            self.monitor = dict(version=int(parts[1]), complete_snapshot=False)
            return
        if kind == 'T' and len(parts) == 7:
            self.record_wall=float(parts[1])
            self.monitor.update(complete_snapshot=True, wall_ms=float(parts[1]), ticks=float(parts[2]),
                observed=len(self.variables), raw_observed=int(parts[3]),
                skipped=int(parts[4]), scan_us=float(parts[5]), frames=int(parts[6]))
            return
        if kind not in ('V','D') or len(parts) != (6 if kind == 'V' else 4): return
        key = unquote(parts[3])
        if not is_save_memory_key(key): return
        wall, ticks = float(parts[1]), float(parts[2])
        if not math.isfinite(wall) or not math.isfinite(ticks): return
        self.record_wall=wall
        self.monitor['wall_ms']=wall
        previous = self.variables.get(key)
        value = None; value_type = 'absent'
        if kind == 'V':
            value_type = parts[4]; raw = unquote(parts[5])
            if value_type == 'number':
                value = float(raw)
                if not math.isfinite(value): return
            else: value = raw
            self.variables[key] = dict(value=value, type=value_type, ticks=ticks)
        else: self.variables.pop(key, None)
        if key.startswith('global.flag[') and key.endswith(']'):
            try:
                index = int(key[12:-1])
                if 0 <= index < 512:
                    if kind == 'V': self.live_flags[index] = value
                    else: self.live_flags.pop(index, None)
            except ValueError: pass
        if previous is None and kind == 'D': return
        if previous is not None and previous['value'] == value and previous['type'] == value_type: return
        event=dict(path=key, before=previous['value'] if previous else None,
            after=value, type=value_type, previous_type=previous['type'] if previous else 'absent',
            operation='removed' if kind=='D' else 'changed' if previous else 'observed',
            wall_ms=wall, ticks=ticks, session=self.session)
        self.variable_events.appendleft(event)
        if event['operation']!='observed':self.semantic_events.appendleft(event)

    def ingest(self, line):
        parts = line.strip().split('|')
        if len(parts)==2 and parts[0]=='K' and parts[1].isdigit():
            self.live_token=parts[1];return
        if parts and parts[0] in ('E','V','D','T'):
            try: self.variable_record(parts)
            except (ValueError, OverflowError, IndexError): pass
            return
        if not parts or parts[0] not in ('S','P','F','H','A','Q','I','M','G','C'):
            return
        try:
            kind = parts[0]
            n = [float(v) for v in parts[1:]]
            if not all(math.isfinite(v) for v in n): return
            if n:self.record_wall=n[0]
            if kind in ('S','H','P') and len(n) >= 4:
                current = dict(wall_ms=n[0], ticks=n[1], room=int(n[2]), plot=n[3], session=self.session)
                if kind == 'S':
                    if self.monitor['version'] < 6:
                        self.live_flags.clear(); self.variables.clear(); self.variable_events.clear(); self.semantic_events.clear()
                    self.session += 1
                    current['session'] = self.session
                    self.anchor = current
                    self.edited = False
                if kind == 'P':
                    previous = self.anchor
                    if previous:
                        rewound = n[1] < previous['ticks'] or n[3] < previous['plot']
                        self.splits.appendleft(dict(**current, previous=previous['plot'],
                            segment_ticks=None if rewound else n[1]-previous['ticks'],
                            segment_wall_ms=n[0]-previous['wall_ms'], rewound=rewound,
                            edited=self.edited, initial=previous.get('initial',False)))
                    self.anchor = current
                if kind == 'H' and len(n) >= 6:
                    current.update(inbattle=bool(n[4]), interacting=bool(n[5]))
                self.current = current
                if self.monitor['version'] < 6:
                    observed={'engine.room':n[2], 'global.plot':n[3], 'obj_time.time':n[1]}
                    if kind == 'H' and len(n) >= 6: observed.update({'global.inbattle':n[4], 'global.interact':n[5]})
                    for key,value in observed.items():
                        self.variable_record(['V',parts[1],parts[2],key,'number',str(value)])
                if kind == 'S': self.anchor['initial'] = True
            elif kind == 'F' and len(n) == 5:
                self.flags.appendleft(dict(wall_ms=n[0], ticks=n[1], index=int(n[2]), before=n[3], after=n[4], session=self.session))
                if 0 <= int(n[2]) < 512: self.live_flags[int(n[2])] = n[4]
                if 0 <= int(n[2]) < 512:
                    key=f'global.flag[{int(n[2])}]'
                    if key not in self.variables:self.variables[key]=dict(value=n[3],type='number',ticks=n[1])
                    self.variable_record(['V',parts[1],parts[2],f'global.flag[{int(n[2])}]','number',parts[5]])
            elif kind == 'A' and len(n) == 5:
                self.ack = dict(seq=int(n[2]), kind=int(n[3]), value=n[4])
                self.edited = True
            elif kind == 'Q' and len(n) in (6,7):
                self.settings=dict(debug=bool(n[2]),wasd=bool(n[3]),zxc=bool(n[4]),input_log=bool(n[5]))
                if len(n)==7: self.settings['bonus']=int(n[6])
            elif kind in ('I','M','G','C') and len(n)>=5:
                event=dict(wall_ms=n[0],ticks=n[1],room=int(n[2]),code=int(n[3]),pressed=bool(n[4]),kind={'I':'Клавиша','M':'Мышь','G':'Геймпад','C':'Ответ в диалоге'}[kind],session=self.session)
                if kind=='M' and len(n)==7: event.update(x=n[5],y=n[6])
                if kind=='G' and len(n)==6: event['device']=int(n[5])
                self.inputs.appendleft(event)
        except (ValueError, OverflowError):
            pass

    def poll(self):
        with self.lock: self._poll()

    def _poll(self):
        if not self.path.exists(): return
        stat = self.path.stat()
        if stat.st_ino != self.inode or stat.st_size < self.offset:
            self.inode = stat.st_ino
            self.offset = 0
            self.remainder = b''
            self.anchor = None
            self.variables.clear(); self.live_flags.clear(); self.variable_events.clear(); self.semantic_events.clear()
            self.monitor = dict(version=5, complete_snapshot=False)
            self.live_token = None
        if stat.st_size == self.offset: return
        with self.path.open('rb') as stream:
            stream.seek(self.offset)
            chunk = stream.read(4_000_000)
            self.offset = stream.tell()
        self.backlog=max(0,stat.st_size-self.offset)
        records = (self.remainder + chunk).split(b'\n')
        self.remainder = records.pop()
        for line in records: self.ingest(line.decode('utf-8',errors='replace'))
        origin=stat.st_mtime-self.record_wall/1000
        for event in list(self.variable_events)+list(self.semantic_events):
            if 'timestamp' not in event and not self.backlog:
                event['timestamp']=datetime.fromtimestamp(origin+event['wall_ms']/1000,timezone.utc).isoformat()
        self.last_received = stat.st_mtime

    def state(self):
        with self.lock: return self._state()

    def _state(self):
        return dict(connected=time.time()-self.last_received < 4 and not self.backlog, current=self.current, backlog_bytes=self.backlog,
                    live_flags=dict(self.live_flags), monitor=dict(self.monitor),
                    live_bundle=bool(self.live_token), live_token=self.live_token,
                    splits=list(self.splits), flags=list(self.flags), ack=self.ack,inputs=list(self.inputs),settings=self.settings,
                    coverage='Запись начинается с подключения модуля. Первое время — неполный отрезок; прошлые этапы не восстанавливаются из сейва.')

    def variable_state(self, query='', offset=0, limit=200):
        with self.lock:
            keys = sorted(k for k in self.variables if query.lower() in k.lower())
            return dict(connected=time.time()-self.last_received < 4 and not self.backlog, monitor=dict(self.monitor),backlog_bytes=self.backlog,
                total=len(self.variables), matched=len(keys), offset=offset,
                variables=[dict(path=k, **self.variables[k]) for k in keys[offset:offset+limit]],
                events=[dict(e) for e in self.variable_events if query.lower() in e['path'].lower()][:200])

    def history(self,technical=False):
        with self.lock:
            events=list(self.semantic_events)
            if technical:
                known={(e['session'],e['wall_ms'],e['path']) for e in events}
                events.extend(e for e in self.variable_events if e['operation']!='observed' and (e['session'],e['wall_ms'],e['path']) not in known)
            return [dict(e) for e in events]
