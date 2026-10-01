import unittest
from timeline import project,memory_path

class TimelineTests(unittest.TestCase):
    def test_same_diff_in_two_files_shown_once(self):
        e={'id':'x','title':'file update','timestamp':'2026-09-21T01:00:10+00:00','cause':'game','changes':[
            {'path':'flags.5','before':0,'after':66,'file':'file0'},
            {'path':'flags.5','before':0,'after':66,'file':'file9'}]}
        out=project([e],[])[0]
        self.assertEqual(len(out['changes']),1)
        self.assertEqual(out['changes'][0]['files'],['file0','file9'])

    def test_disk_receipt_replaces_previously_observed_diff(self):
        memory={'session':1,'wall_ms':100,'timestamp':'2026-09-21T01:00:01+00:00','path':'global.flag[5]',
                'before':0,'after':66,'operation':'changed'}
        event={'id':'x','title':'save','timestamp':'2026-09-21T01:00:10+00:00','changes':[
            {'path':'flags.5','before':0,'after':66,'file':'file0'}]}
        out=project([event],[memory]);disk=out[0]
        self.assertEqual(disk['changes'],[])
        self.assertEqual(len(disk['memory_written']),1)
        self.assertEqual(out[1]['cause'],'memory')
        memory['timestamp']='2026-09-21T02:00:00+00:00'
        disk=next(e for e in project([event],[memory]) if e['id']=='x')
        self.assertEqual(len(disk['changes']),1)

    def test_different_values_are_not_merged(self):
        event={'id':'x','title':'save','timestamp':'2026-09-21T01:00:10+00:00','changes':[
            {'path':'gold','before':0,'after':3,'file':'file0'},
            {'path':'gold','before':0,'after':4,'file':'file9'}]}
        self.assertEqual(len(project([event],[])[0]['changes']),2)
        self.assertEqual(memory_path('inventory.2.phone'),'global.phone[2]')

    def test_transient_memory_noise_is_not_projected(self):
        base={'session':1,'wall_ms':100,'timestamp':'2026-09-21T01:00:01+00:00',
              'before':0,'after':1,'operation':'changed','ticks':50}
        memory=[{**base,'path':'instance[2:obj_time].spec_rtimer'},
                {**base,'path':'obj_time.time'},
                {**base,'path':'global.currentroom'},
                {**base,'path':'global.flag[5]'}]
        rows=project([],memory)
        self.assertEqual(len(rows),1)
        self.assertEqual({c['path'] for c in rows[0]['changes']},
                         {'global.currentroom','global.flag[5]'})

if __name__=='__main__':unittest.main()
