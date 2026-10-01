import tempfile
import unittest
from pathlib import Path
from runtime import RuntimeLog, is_save_memory_key
from compact_log import compact


class VariableTests(unittest.TestCase):
    def test_v5_partial_flags_are_not_fake_snapshot(self):
        r=RuntimeLog(Path('/unused'))
        r.ingest('S|1|2|3|4');r.ingest('F|2|3|30|0|1')
        self.assertEqual(r.state()['live_flags'],{30:1})
        self.assertFalse(r.state()['monitor']['complete_snapshot'])

    def test_snapshot_diff_unicode_escape_delete(self):
        r=RuntimeLog(Path('/unused'))
        for row in ['E|6','V|1|2|global.gold|number|20','V|2|3|global.gold|number|19',
                    'V|2|3|global.charname|string|Привет%7C%25%0Aмир','D|3|4|global.gold']:
            r.ingest(row)
        s=r.variable_state()
        self.assertEqual(s['variables'][0]['value'],'Привет|%\nмир')
        self.assertEqual([e['operation'] for e in s['events']],['removed','observed','changed','observed'])
        self.assertEqual(s['events'][0]['before'],19)

    def test_flag_baseline_and_session_reset(self):
        r=RuntimeLog(Path('/unused'))
        r.ingest('E|6');r.ingest('V|1|1|global.flag[5]|number|66')
        self.assertEqual(r.state()['live_flags'],{5:66})
        r.ingest('E|6');self.assertEqual(r.state()['live_flags'],{})
        self.assertEqual(r.variable_state()['total'],0)

    def test_search_page_and_malformed(self):
        r=RuntimeLog(Path('/unused'))
        for i in range(8):r.ingest(f'V|1|1|global.item[{i}]|number|{i}')
        r.ingest('V|1|1|global.bad|number|nan');r.ingest('V|1|1|global.bad|number|inf')
        s=r.variable_state('item',2,3)
        self.assertEqual(s['total'],8)
        self.assertEqual([v['value'] for v in s['variables']],[2,3,4])

    def test_file_utf8_partial_and_truncated(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'log';r=RuntimeLog(p)
            p.write_bytes('E|6\nV|1|2|global.charname|string|Я'.encode());r.poll()
            self.assertEqual(r.variable_state()['total'],0)
            with p.open('ab') as f:f.write(b'\n')
            r.poll();self.assertEqual(r.variable_state()['variables'][0]['value'],'Я')
            p.write_bytes(b'E|6\n');r.poll();self.assertEqual(r.variable_state()['total'],0)

    def test_only_save_memory_fields_and_clock_context(self):
        r=RuntimeLog(Path('/unused'))
        for row in ('E|7','V|1|1|instance[2:obj_time].spec_rtimer|number|30',
                    'V|2|2|engine.room|number|18','V|3|3|global.currentroom|number|18',
                    'V|4|4|global.currentroom|number|19','V|5|5|obj_time.time|number|5',
                    'T|6|6|540|0|400|30'):
            r.ingest(row)
        self.assertEqual(set(r.variables),{'global.currentroom'})
        self.assertEqual([(e['path'],e['before'],e['after']) for e in r.history()],
                         [('global.currentroom',18,19)])
        self.assertEqual(r.history()[0]['ticks'],4)
        self.assertFalse(is_save_memory_key('global.flag[512]'))
        self.assertTrue(is_save_memory_key('global.flag[511]'))

    def test_flag_bridge_is_not_double_logged(self):
        r=RuntimeLog(Path('/unused'))
        for row in ('E|7','V|1|1|global.flag[5]|number|0',
                    'F|2|2|5|0|66','V|2|2|global.flag[5]|number|66'):
            r.ingest(row)
        self.assertEqual(len(r.history()),1)
        self.assertEqual(r.history()[0]['after'],66)

    def test_compaction_preserves_save_changes_and_recovery_copy(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'ucc-events.log';backup=Path(t)/'before.log'
            original=(b'E|6\nV|1|1|instance[1:obj].buffer|number|9\n'
                      b'V|2|2|global.flag[5]|number|66\n'
                      b'V|3|3|global.currentroom|number|7\n'
                      b'V|4|4|obj_time.time|number|4\n'
                      b'F|5|5|5|0|66\nI|6|6|7|90|1\n')
            path.write_bytes(original)
            report=compact(path,backup)
            self.assertEqual(backup.read_bytes(),original)
            cleaned=path.read_bytes()
            self.assertIn(b'global.flag[5]',cleaned)
            self.assertIn(b'global.currentroom',cleaned)
            self.assertIn(b'F|5|5|5|0|66',cleaned)
            self.assertIn(b'I|6|6|7|90|1',cleaned)
            self.assertNotIn(b'instance[1:obj]',cleaned)
            self.assertNotIn(b'obj_time.time',cleaned)
            self.assertEqual(report['discarded_memory_noise'],2)

if __name__=='__main__':unittest.main()
