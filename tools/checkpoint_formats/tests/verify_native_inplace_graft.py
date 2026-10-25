"""Native localhost synthesis and EDA SP2 execution of the existing-root graft.

Retains the complete in-place access checks, stalls, negatives and waveforms.
"""
from tools.checkpoint_formats.tests import verify_native_inplace_access as runner
from tools.checkpoint_formats.tests.audit_native_inplace_graft import audit, corruptions

runner.SOURCES = tuple(sorted(set(runner.SOURCES + (
    'sims/firesim/sim/midas/src/main/scala/midas/checkpoint/NativeCheckpointInPlaceGraft.scala',
    'tools/checkpoint_formats/tests/audit_native_inplace_graft.py',
    'tools/checkpoint_formats/tests/verify_native_inplace_graft.py',
    'tools/checkpoint_formats/tests/native_inplace_graft_fixture.sv',
    'tools/checkpoint_formats/tests/native_inplace_graft_tb.sv'))))
runner.FILES = ['generated/grafted.sv',
    'generated/FireSim-generated.native-inplace-graft.sv',
    'generated/FireSim-generated.native-inplace-graft-router.sv',
    'generated/FireSim-generated.native-inplace-graft-ce.sv',
    'sources/CheckpointPhysicalClockCut.sv','sources/native_inplace_graft_fixture.sv']
# Use the same synthesis scope with the original instance path, no /network hop.
start=runner.TCL.index('read_verilog -sv ');end=runner.TCL.index('\nread_xdc',start)
runner.TCL=runner.TCL[:start]+'read_verilog -sv '+' '.join(runner.FILES)+runner.TCL[end:]
runner.TCL=runner.TCL.replace('generated/FireSim-generated.native-state-access.', 'generated/FireSim-generated.native-inplace-graft.')
runner.TCL=runner.TCL.replace('host/network/','host/').replace('*router/', '*checkpoint_readout_adapter/router/').replace('*ce_endpoint/','*checkpoint_readout_adapter/ce_endpoint/')
runner.audit,runner.corruptions=audit,corruptions
runner.ORACLE_BINDING_FILE='original/FireSim-generated.native-functional-binding.json'
runner.REFERENCE_FILE='generated/original/NativeReference.sv'
runner.TESTBENCH_FILE='sources/native_inplace_graft_tb.sv'

if __name__=='__main__':runner.main()
