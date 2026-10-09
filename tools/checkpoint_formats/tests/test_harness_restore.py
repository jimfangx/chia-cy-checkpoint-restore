import copy
from pathlib import Path
import tempfile
import unittest
from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.harness_restore import harness_layout, harness_capture, prepare_harness_restore

ROOT=Path(__file__).resolve().parents[3]
TOP=ROOT/'sims/firesim/sim/midas/src/main/verilog/top.sv'
CONSTANTS='\n'.join('`define '+k+' '+str(v) for k,v in dict(CTRL_ADDR_BITS=32,CTRL_DATA_BITS=32,CTRL_ID_BITS=12,MEM_ADDR_BITS=34,MEM_DATA_BITS=64,MEM_ID_BITS=16,QSFP_DATA_BITS=256).items())

class HarnessRestoreTest(unittest.TestCase):
    def test_audited_layout_and_unsupported_modes(self):
        layout=harness_layout(TOP.read_text(),CONSTANTS,'','a'*64)
        self.assertEqual(len(layout['records']),29)
        self.assertEqual(layout['records'][0]['width'],66)
        self.assertEqual(layout['records'][1]['width'],16)
        self.assertEqual(layout['records'][9]['width'],152)
        narrow=CONSTANTS.replace('CTRL_ADDR_BITS 32','CTRL_ADDR_BITS 1').replace('CTRL_DATA_BITS 32','CTRL_DATA_BITS 8').replace('CTRL_ID_BITS 12','CTRL_ID_BITS 1').replace('QSFP_DATA_BITS 256','QSFP_DATA_BITS 0')
        one=harness_layout(TOP.read_text(),narrow,'','a'*64)
        self.assertEqual(one['records'][0]['width'],20)
        self.assertEqual(one['records'][9]['width'],41)
        self.assertEqual(one['records'][7]['width'],66)
        for source,constant,defines in [(TOP.read_text()+'\n',CONSTANTS,''),(TOP.read_text(),CONSTANTS,'`define DEBUG'),(TOP.read_text(),CONSTANTS,'`define GATE_LEVEL_SIM'),(TOP.read_text(),CONSTANTS.replace('CTRL_DATA_BITS 32','CTRL_DATA_BITS 7'),'')]:
            with self.assertRaises(FormatError): harness_layout(source,constant,defines,'a'*64)

    def test_complete_banks_and_no_publication_on_invalid_cut(self):
        layout=harness_layout(TOP.read_text(),CONSTANTS,'','a'*64)
        capture=harness_capture(layout,['0'*((r['width']+3)//4) for r in layout['records']],123)
        mutations=[lambda c:c['records'].pop(),lambda c:c['records'].reverse(),lambda c:c.update(host_sample=True),lambda c:c.update(schema='other'),lambda c:c.update(layout_sha256='b'*64),lambda c:c.update(sample_phase='settled_host_posedge'),lambda c:c['records'][-1].update(value='1'),lambda c:c['records'][-2].update(value='1'),lambda c:c['records'][0].update(width=True),lambda c:c['records'][0].update(value='x')]
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'load';prepare_harness_restore(layout,capture,path)
            self.assertEqual(len(path.read_text().splitlines()),30)
            for mutate in mutations:
                changed=copy.deepcopy(capture);mutate(changed);path.write_text('preserve')
                with self.assertRaises(FormatError): prepare_harness_restore(layout,changed,path)
                self.assertEqual(path.read_text(),'preserve')

if __name__=='__main__': unittest.main()
