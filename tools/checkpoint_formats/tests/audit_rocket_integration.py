"""Static recovery audit; grants no CPU checkpoint admission."""
import argparse,json,re,shutil,tempfile
from pathlib import Path
from tools.checkpoint_formats.cpu_recipe import ROOT as root
from tools.checkpoint_formats.evidence import file_sha
from tools.checkpoint_formats.cpu_recipe import RECIPES,recipe_settings
def audit(summary, destination):
    summary=Path(summary).resolve()
    assert json.loads(summary.read_text())['status']=='passed'
    build=summary.parent
    assert (build/'rocket-build-identity.json').is_file()
    destination=Path(destination).resolve()
    assert destination.is_relative_to(root/'automations/checkpoint_loop/runs')
    destination.mkdir(parents=True,exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix='invocation-',dir=destination))
    base=next((build/'build/f2').glob('*/FireSim-generated.const.h'))
    manifest=base.with_name('FireSim-generated.simulator-state.json')
    cc=root/'sims/firesim/sim/midas/src/main/cc'
    paths=[base,manifest,build/'rocket-build-identity.json',root/'sims/firesim-staging/sample_config_build_recipes.yaml',Path(__file__).resolve()]
    paths += [cc/p for p in ('entry.cc','emul/simif_emul.cc','emul/simif_emul.h','emul/mm.h','emul/mm.cc','core/checkpoint.h','core/checkpoint_publication.h','core/configuration_checkpoint.h','bridges/heartbeat.h','bridges/heartbeat.cc','bridges/peek_poke.h','bridges/peek_poke.cc','bridges/cpu_managed_stream.h','bridges/cpu_managed_stream.cc','core/stream_engine.h','core/stream_engine.cc','bridges/master.h','bridges/clock.h','bridges/loadmem.h','bridges/reset_pulse.h','core/systematic_scheduler.h','core/bridge_run_loop.h','core/widget_registry.cc','core/simulation.cc','core/systematic_scheduler.cc','core/bridge_run_loop.cc','rtlsim/Makefrag-checkpoint')]
    paths += [root/p for p in ('tools/checkpoint_formats/metasim_build.py','tools/checkpoint_formats/aggregate_restore.cc','tools/checkpoint_formats/durable_restore_entry.cc','generators/firechip/chip/src/main/cc/firesim/firesim_top.cc','generators/firechip/bridgestubs/src/main/cc/bridges/blockdev.h','generators/firechip/bridgestubs/src/main/cc/bridges/blockdev.cc','generators/firechip/bridgestubs/src/main/cc/bridges/tsibridge.h','generators/firechip/bridgestubs/src/main/cc/bridges/tsibridge.cc','generators/firechip/bridgestubs/src/main/cc/fesvr/tsi_context_group.h')]
    snap=out/'cpu-integration-inputs';snap.mkdir(exist_ok=True);bindings=[]
    for p in paths:
     h=file_sha(p);q=snap/h
     if not q.exists():shutil.copyfile(p,q)
     bindings.append(dict(path=str(p),sha256=h,snapshot=str(q)))
    header=base.read_text();entry=(cc/'entry.cc').read_text()
    phases=('GET_CORE_CONSTRUCTOR','GET_MANAGED_STREAM_CONSTRUCTOR','GET_BRIDGE_CONSTRUCTOR')
    assert [entry.index('#define '+p) for p in phases]==sorted(entry.index('#define '+p) for p in phases)
    blocks=re.findall(r'#ifdef (GET_(?:CORE|MANAGED_STREAM|BRIDGE)_CONSTRUCTOR)\n(.*?)#endif',header,re.S)
    constructors=[]
    for phase in phases:
     for tag,body in blocks:
      if tag!=phase:continue
      classes=re.findall(r'registry\.add_widget\(new (\w+)\(',body)
      assert len(classes)==1
      constructors+=classes
    expected=['master_t','loadmem_t','CPUManagedStreamWidget','peek_poke_t','reset_pulse_t','blockdev_t','uart_t','FASEDMemoryTimingModel',*['tracerv_t']*4,'tsibridge_t','clockmodule_t']
    assert constructors==expected
    ftop=(root/'generators/firechip/chip/src/main/cc/firesim/firesim_top.cc').read_text()
    assert 'new heartbeat_t(' in ftop and 'runtime/simulation/firesim-run-loop' in ftop
    assert 'firesim.simulation.bridge-driver.v1' in ftop and 'simulation_supports_steps() const override { return true; }' in ftop
    assert '.ctrl = AXI4Config{12, 32, 32}' in header and '.cpu_managed = AXI4Config{16, 64, 512}' in header
    assert '.mem_num_channels = 1' in header and '.fpga_managed = std::nullopt' in header and '.qsfp = FPGATopQSFPConfig{256, 0}' in header
    source=(cc/'emul/simif_emul.cc').read_text();guards=[]
    assert 'void publish_sealed_checkpoint_io(io_restore_t &) noexcept;' in (cc/'emul/simif_emul.h').read_text()
    for name in ('seal_checkpoint_io','publish_sealed_checkpoint_io'):
     assert 'void simif_emul_t::'+name in source
    assert 'candidate.generation != io_checkpoint_generation' in source
    
    mm_header=(cc/'emul/mm.h').read_text();mm_source=(cc/'emul/mm.cc').read_text()
    assert 'void publish_sealed_checkpoint(restore_t &) noexcept;' in mm_header
    for method in ('prepare_checkpoint','seal_checkpoint','publish_sealed_checkpoint'):
     assert 'mm_magic_t::'+method in mm_source
    assert 'candidate->expected = save_checkpoint();' in mm_source
    assert 'candidate.generation != checkpoint_generation' in mm_source
    assert 'std::memcpy(data, candidate.incoming.data() + state.memory_offset, size);' in mm_source
    assert 'mm_t(const mm_t &) = delete;' in mm_header
    assert 'memory already initialized' in mm_source
    
    
    base_owner=(cc/'core/checkpoint.h').read_text()
    assert 'unsupported prepared host checkpoint publication' in base_owner
    for cls in ('systematic_scheduler','bridge_run_loop'):
     h=(cc/('core/'+cls+'.h')).read_text();c=(cc/('core/'+cls+'.cc')).read_text()
     assert 'prepare_checkpoint_publication(const std::vector<uint8_t> &) override;' in h
     assert 'void publish() noexcept override' in c and 'guard.publish();' in c
     assert 'publication.changed();' in c
     assert 'guard.require_unsealed();' in c and 'owner.save_checkpoint() != expected' in c
    publication=(cc/'core/checkpoint_publication.h').read_text()
    assert 'std::weak_ptr<state_t> lifetime;' in publication and 'std::this_thread::get_id()' in publication
    assert 'checkpoint_publication_t(const checkpoint_publication_t &) = delete;' in publication
    
    for name in ('master','clock','loadmem','reset_pulse'):
     h=(cc/('bridges/'+name+'.h')).read_text()
     assert 'std::make_unique<configuration_checkpoint_t>(*this, checkpoint_publication, payload)' in h
     assert 'checkpoint_publication.changed();' in h
     assert 'checkpoint_publication_t checkpoint_publication;' in h
    config=(cc/'core/configuration_checkpoint.h').read_text()
    assert 'payload != expected' in config and 'guard.require_unsealed();' in config
    assert 'owner.save_checkpoint() != expected' in config
    assert 'void publish() noexcept override' in config and 'guard.publish();' in config
    
    for name in ('peek_poke','cpu_managed_stream','heartbeat'):
     h=(cc/('bridges/'+name+'.h')).read_text(); c=(cc/('bridges/'+name+'.cc')).read_text()
     assert 'prepare_checkpoint_publication(const std::vector<uint8_t> &) override;' in h
     assert 'void publish() noexcept override' in c and 'guard.publish();' in c
     assert 'publication.changed();' in h+c
     assert 'guard.require_unsealed();' in c and 'owner.save_checkpoint() != expected' in c
     assert 'final : public' in h
    
    for method in ('require_restored_destination','begin_restored_load','require_settled_checkpoint_capture'):
     m=re.search(r'void simif_emul_t::'+method+r'\([^)]*\)(?: const)? \{(.*?)\n\}',source,re.S)
     assert m and 'cpu_managed_stream_io' in m[1] and 'throw std::runtime_error' in m[1]
     guards.append(method)
    profile=(root/'tools/checkpoint_formats/metasim_build.py').read_text()
    assert "PROFILE = 'fcfs-fased-v1'" in profile and 'profile requires exactly four functional-memory channels' in profile
    assert 'unsupported QSFP/managed-stream topology' in profile
    make=(cc/'rtlsim/Makefrag-checkpoint').read_text();assert 'ifneq ($(FS_CHECKPOINT_PROFILE),fcfs-fased-v1)' in make
    loader=(root/'tools/checkpoint_formats/durable_restore_entry.cc').read_text()
    assert 'checkpoint_axi_owners()' in loader and 'checkpoint_stream_io_owners()' not in loader and 'checkpoint_mmio_io_owner()' not in loader
    bridge=(root/'generators/firechip/bridgestubs/src/main/cc/bridges/tsibridge.h').read_text()
    assert 'void seal_publication();' in bridge and 'void publish_sealed() noexcept;' in bridge
    assert 'checkpoint_schema' not in bridge
    assert 'prepare_checkpoint_publication(const std::vector<uint8_t> &payload) override' in ftop
    assert 'expected(owner.destination_stamp())' in ftop
    assert 'owner.destination_stamp() != expected' in ftop
    assert 'owner.driver.started = true;' in ftop
    assert 'publication.changed();' in ftop
    assert 'guard.require_unsealed();' in ftop
    assert 'void publish() noexcept override' in ftop
    base_header=(cc/'core/simulation.h').read_text(); base_source=(cc/'core/simulation.cc').read_text()
    assert 'prepare_checkpoint_publication(const std::vector<uint8_t> &) override;' in base_header
    assert 'checkpoint_publication_t publication;' in base_header
    assert 'expected(owner.destination_stamp())' in base_source
    assert 'owner.destination_stamp() != expected' in base_source
    assert 'guard.require_unsealed();' in base_source and 'guard.publish();' in base_source
    assert 'publication.changed();' in base_source and 'void publish() noexcept override' in base_source
    for field in ('flow_phase','flow_on_stack','flow_poisoned','base_checkpoint_loaded','run_done','start_time','end_time','start_hcycle','end_hcycle','end_tcycle'):
        assert 'stamp.word(' in base_source and 'sim.'+field in base_source
    assert 'owner.sim.base_checkpoint_loaded = true;' in base_source
    
    blockdev=root/'generators/firechip/bridgestubs/src/main/cc/bridges'
    h=(blockdev/'blockdev.h').read_text();c=(blockdev/'blockdev.cc').read_text()
    assert 'class blockdev_t final' in h and 'checkpoint_publication_t publication;' in h
    assert 'prepare_checkpoint_publication(const std::vector<uint8_t> &) override;' in h
    assert 'guard.require_unsealed();' in c and 'owner.save_checkpoint() != expected' in c
    assert 'void publish() noexcept override' in c and 'guard.publish();' in c
    assert 'owner._file = file.release();' in c and 'owner.memory_disk.swap(replacement.disk);' in c
    
    state=json.loads(manifest.read_text());assert (len(state['state']),sum(e['depth'] for e in state['state']))==(11464,445838)
    recipe=recipe_settings(RECIPES['Rocket'])
    for b in bindings:assert file_sha(b['path'])==b['sha256']==file_sha(b['snapshot'])
    result=dict(status='passed',scope='structural CPU coordinator integration recovery; not runtime admission or continuation',recipe=recipe,header=str(base),generated_entries=len(state['state']),generated_words=sum(e['depth'] for e in state['state']),widget_inventory=[dict(owner='widget/'+str(i),concrete=c) for i,c in enumerate(constructors+['heartbeat_t'])],CPU_rejection_guards=guards,FCFS_profile_exclusive=True,IO_split_seal_noexcept_publication=True,functional_memory_prepared_sealed=True,control_prepared_sealed=True,configuration_widgets_prepared_sealed=True,scalar_widgets_prepared_sealed=True,concrete_driver_prepared_sealed=True,base_lifecycle_prepared=True,heartbeat_prepared_sealed=True,blockdev_prepared_sealed=True,CPU_aggregate_enabled=False,CPU_level1_verified=False,CPU_level2_verified=False,source_inputs=bindings,remaining=['CPU-specific manifest/build/owner binding; independent of FCFS whitelist','Full process thread/signal/descriptor/parser exclusion','Join I/O, functional memory, all widgets/driver/generated/harness state and creator-side sealed TSI publication','Replace sequential allocating native loads with a complete prepared commit protocol','Complete fresh-process CPU continuation and independent whole-state audit'])
    path=out/'cpu-integration-audit.json';path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status='passed',widget_owners=len(result['widget_inventory']),CPU_rejection_guards=guards,generated_entries=len(state['state']),generated_words=result['generated_words'],CPU_aggregate_enabled=False,receipt=str(path)),indent=2))
    return path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rocket-summary',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    audit(args.rocket_summary,args.out)


if __name__ == '__main__':
    main()
