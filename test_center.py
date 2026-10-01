import copy
import hashlib
import tempfile
import threading
import unittest
from pathlib import Path
from collections import deque
from unittest.mock import patch
import server as s
from runtime import RuntimeLog
from bundles import GAME_FILES, Vault, read_bundle, digest, coupled_bundle, write_bundle
from bonus import migration_plan, contextual_catalog, mode_from_config


def fixture():
    lines=['0']*551
    for i,v in {0:'QA',1:1,2:20,3:20,4:10,6:10,8:4,28:3,29:4,546:-1,547:7}.items(): lines[i]=str(v)
    return '\n'.join(lines).encode()


class ValidationTests(unittest.TestCase):
    def test_fixture(self):
        self.assertTrue(s.validate_model(s.parse_save_bytes(fixture()))['valid'])

    def test_corrupt_numeric_not_silently_zero(self):
        raw=fixture().split(b'\n');raw[34]=b'not-a-number'
        model=s.parse_save_bytes(b'\n'.join(raw))
        self.assertFalse(s.validate_model(model)['valid'])
        s.set_model_value(model,'flags.4',1)
        self.assertTrue(s.validate_model(model)['valid'])

    def test_indices(self):
        for path in ('flags.-1','flags.512','inventory.8.item','inventory.0.bad','menu.3','wat'):
            with self.assertRaises(ValueError): s.set_model_value(s.parse_save_bytes(fixture()),path,1)

    def test_fractional_item(self):
        m=s.parse_save_bytes(fixture());m['inventory'][0]['item']=7.5
        self.assertTrue(any(x['path']=='inventory.0.item' for x in s.validate_model(m)['warnings']))

    def test_nonfinite_and_newline(self):
        for path,value in [('flags.4',float('nan')),('flags.4',float('inf')),('name','QA\n9')]:
            with self.assertRaises(ValueError): s.set_model_value(s.parse_save_bytes(fixture()),path,value)

    def test_transaction_and_stale_preview(self):
        with tempfile.TemporaryDirectory() as t:
            d=Path(t); snaps=d/'snapshots';snaps.mkdir()
            watched={n:d/n for n in ('file0','file9','undertale.ini','config.ini')}
            watched['file0'].write_bytes(fixture())
            mon=s.Monitor.__new__(s.Monitor);mon.lock=threading.RLock();mon.timeline=deque();mon.last_bytes={};mon.self_write_until=0
            with patch.multiple(s,SAVE_DIR=d,WATCHED=watched,SNAPSHOT_DIR=snaps,HISTORY_FILE=d/'history.jsonl',VAULT=Vault(d/'slots')),patch.object(s,'game_pid',return_value=None):
                changes=[{'path':'flags.5','value':61}]
                digest=hashlib.sha256(fixture()).hexdigest()
                result=mon.apply('file0',changes,[],digest)
                self.assertEqual(result['model']['flags'][5],61)
                self.assertEqual(s.read_ini(watched['undertale.ini'])['General']['fun'],'61')
                self.assertEqual((d/'file0').read_bytes(),(d/'file9').read_bytes())
                self.assertEqual(len(mon.timeline),2)
                with self.assertRaises(ValueError): mon.apply('file0',changes,[],digest)

    def test_rollback_preserves_absent_vs_empty_files(self):
        with tempfile.TemporaryDirectory() as t:
            d=Path(t);snaps=d/'snaps';snaps.mkdir();watched={n:d/n for n in ('file0','file9','config.ini')}
            watched['file0'].write_bytes(fixture());watched['config.ini'].write_bytes(b'')
            mon=s.Monitor.__new__(s.Monitor);mon.timeline=deque();mon.last_bytes={};mon.self_write_until=0
            with patch.multiple(s,SAVE_DIR=d,WATCHED=watched,SNAPSHOT_DIR=snaps,HISTORY_FILE=d/'history'),patch.object(s,'game_pid',return_value=None):
                snap=mon.snapshot('QA','test',[])
                watched['file9'].write_bytes(b'new');watched['file0'].write_bytes(b'changed')
                mon.rollback(snap['id'])
                self.assertFalse(watched['file9'].exists())
                self.assertEqual(watched['file0'].read_bytes(),fixture())
                self.assertTrue(watched['config.ini'].exists())
                self.assertEqual(watched['config.ini'].read_bytes(),b'')


class RuntimeTests(unittest.TestCase):
    def test_runtime_settings_and_inputs(self):
        r=RuntimeLog(Path('/unused'))
        for line in ['Q|100|20|1|0|1|1|3','I|101|21|77|90|1','I|102|22|77|90|0','M|103|23|77|1|1|120|80','G|104|24|77|2|1|0','C|105|25|77|1|1']:r.ingest(line)
        self.assertEqual(r.settings,dict(debug=True,wasd=False,zxc=True,input_log=True,bonus=3))
        self.assertEqual(len(r.inputs),5)
        self.assertEqual(r.inputs[2]['x'],120)

    def test_real_split_rewind_and_manual_mark(self):
        r=RuntimeLog(Path('/unused'))
        for line in ['S|100|300|31|22','P|2100|360|31|23|22','A|2200|363|1234|1|1','P|4100|420|31|24|23','P|5100|330|31|22|24']:
            r.ingest(line)
        self.assertEqual(len(r.splits),3)
        self.assertTrue(r.splits[0]['rewound'])
        self.assertIsNone(r.splits[0]['segment_ticks'])
        self.assertTrue(r.splits[1]['edited'])
        self.assertEqual(r.splits[2]['segment_ticks'],60)
        self.assertTrue(r.splits[2]['initial'])

    def test_partial_line_and_restart(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'events';r=RuntimeLog(p)
            p.write_bytes(b'S|10|30|31|22\nP|20|60')
            r.poll();self.assertEqual(len(r.splits),0)
            with p.open('ab') as f:f.write(b'|31|23|22\n')
            r.poll();self.assertEqual(len(r.splits),1)
            r.ingest('garbage');r.ingest('P|bad')
            self.assertEqual(len(r.splits),1)

    def test_knowledge_not_generated_filler(self):
        flag=s.FLAG_META[4]
        self.assertTrue(flag['reviewed'])
        self.assertIn('kills=1',flag['purpose'])
        self.assertIn('Папирус',s.FLAG_META[67]['title'])
        self.assertTrue(s.FLAG_META[305]['used'])
        self.assertEqual([x['value'] for x in s.CATALOG['fun_events']][:4],[40,46,56,2])
        self.assertEqual(len(s.CATALOG['plots']),120)
        self.assertFalse(any('Промежуточный' in p['title'] or not p.get('description') for p in s.CATALOG['plots']))


class BundleTests(unittest.TestCase):
    def test_bundle_roundtrip_absence_and_stale_guard(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);before=read_bundle(root);after=dict(before);after['file0']=fixture();after['system_information_963']=b''
            write_bundle(root,after,digest(before));self.assertEqual(read_bundle(root),after)
            with self.assertRaises(ValueError):write_bundle(root,before,digest(before))
            vault=Vault(root/'slots');r=vault.capture('QA',after,'QA');_,copy=vault.get(r['id']);self.assertEqual(copy,after)
            write_bundle(root,before,digest(after));self.assertFalse((root/'system_information_963').exists())

    def test_independent_checkpoint_preserved(self):
        before={n:None for n in GAME_FILES};before['file0']=fixture();before['file9']=fixture()+b'\n';m=s.parse_save_bytes(fixture())
        after=coupled_bundle(before,'file9',b'new',m,'independent')
        self.assertEqual(after['file0'],before['file0']);self.assertIsNone(after['undertale.ini'])

    def test_bonus_migration_does_not_convert_progress(self):
        before={n:None for n in GAME_FILES};lines=fixture().splitlines();lines[547]=b'340';lines[322]=b'1';lines[327]=b'3.1';lines[329]=b'50';lines[550]=b'50'
        before['file0']=b'\n'.join(lines);lines[542]=b'104';before['file9']=b'\n'.join(lines);before['config.ini']=b'[General]\nds=3\nlang=ru\n'
        after,plan=migration_plan(before,1,s.parse_save_bytes,s.validate_model)
        self.assertEqual(s.parse_save_bytes(after['file0'])['room'],77)
        self.assertEqual(s.parse_save_bytes(after['file0'])['flags'],s.parse_save_bytes(before['file0'])['flags'])
        self.assertNotEqual(after['file0'],after['file9'])
        self.assertIn(b'lang=ru',after['config.ini']);self.assertEqual(len(plan['changes']),4)

    def test_bonus_text_is_contextual(self):
        a=contextual_catalog(s.CATALOG,3,'QA');b=contextual_catalog(s.CATALOG,1,'QA')
        self.assertTrue(a['flags'][292]['active_in_bonus']);self.assertFalse(b['flags'][292]['active_in_bonus'])
        self.assertIn('Сейчас активен «PS4»',b['flags'][292]['purpose'])
        self.assertNotIn('Сейчас активен',a['flags'][292]['purpose'])

    def test_bonus_roundtrip_preserves_every_save_and_marker(self):
        before={n:None for n in GAME_FILES}
        before.update(file0=fixture(),file9=fixture()+b'\n',file8=fixture())
        before['config.ini']=b'[General]\nds=3\nlang=ru\n'
        before['undertale.ini']=b'[General]\nRoom=7\n[Flowey]\nK=1\n'
        before['system_information_963']=b''
        for target in range(5):
            after,plan=migration_plan(before,target,s.parse_save_bytes,s.validate_model)
            self.assertEqual(mode_from_config(after['config.ini']),target)
            for name in GAME_FILES:
                if name!='config.ini': self.assertEqual(after[name],before[name],name)

    def test_bad_bonus_rejected_and_fun_text_changes(self):
        for value in ('nan','inf','3.5','-1','5','wrong'):
            with self.assertRaises(ValueError):mode_from_config(('[General]\nds='+value).encode())
        ordinary=contextual_catalog(s.CATALOG,1,'QA')['fun_events']
        anniversary=contextual_catalog(s.CATALOG,4,'QA')['fun_events']
        self.assertEqual(next(e for e in ordinary if e['value']==2)['range'],'2–39')
        self.assertEqual(next(e for e in anniversary if e['value']==2)['range'],'2–100')

    def test_catalog_coverage(self):
        self.assertEqual(s.CATALOG['classified_flags'],512)
        self.assertEqual(s.CATALOG['reviewed_flags'],352)
        self.assertTrue(all(f['reviewed'] for f in s.CATALOG['flags']))
        self.assertEqual(len(s.CATALOG['dev_features']),18)

if __name__=='__main__': unittest.main()
