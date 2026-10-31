"""Offline tamper checks for native bound endpoint evidence; no FPGA/VCS run."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.checkpoint_formats.codec import canonical, FormatError
from tools.checkpoint_formats.tests import verify_native_bound_endpoint as runner


class NativeBoundEndpointTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.generated = self.root / "generated"
        self.path = self.generated / runner.BOUND
        self.path.mkdir(parents=True)
        self.sources = {n: runner.sha(runner.ROOT/n) for n in runner.SOURCES}
        self.reference = "a" * 64
        self.state_id = runner.digest(dict(hierarchy="NativeBindingFixture.state", kind="register", namespace="pre-fame-state-v1"))
        row = dict(state_id=self.state_id, hierarchy="NativeBindingFixture.state", kind="register", width=64, depth=1)
        self.original = dict(reference_sha256=self.reference, state=[row])
        self.original_binding = dict(reference_sha256=self.reference, manifest_sha256=runner.digest(self.original),
            instrumented_sha256="b"*64, scope="all_reachable_firrtl_state_only", access_version=1,
            protocol="latched-banked64-v1", state=[dict(row, bank=1, slot=0, storage_hierarchy="NativeBindingFixture.state")])
        self.abi = dict(bits=130, gates=3, external_owners=["fixture.functional", "fixture.host"], coordinator_owners=3,
            external_clock_network=1, capture_native_control=True, snapshot_bank=252, native_control_bank=251,
            original_entries=1, stream_entries=4, native_owner_bits=283, raw_control_bits=760, separate_bank_bits=67,
            shadow_control_bits=827, shadow_bits=1585, shadow_layout_version=2, shadow_restore_supported=False)
        self.manifest = dict(descriptor_version=1, scope="native_transport_ordered_stream_descriptors_only", abi=self.abi,
            original_manifest_sha256=runner.digest(self.original), original_binding_sha256=runner.digest(self.original_binding),
            sources={n:self.sources[runner.PREFIX+n] for n in runner.RESOURCES}, **runner.FLAGS)
        identity = dict(domain="native_transport_descriptor_v1", original_manifest_sha256=runner.digest(self.original),
            original_binding_sha256=runner.digest(self.original_binding), abi=self.abi, sources=self.manifest["sources"])
        roles = ["original", "native_owner", "staged_payload_full", "staged_payload_tail"]
        ids = [self.state_id] + [hashlib.sha256(canonical(identity)+b"\n"+s.encode()).hexdigest() for s in roles[1:]]
        selectors = [(1,0,64,1), (251,0,64,5), (252,0,64,2), (252,1,2,1)]
        self.manifest["state"] = [dict(ordinal=i, domain=role, state_id=sid, bank=b, slot=s, width=w, depth=d)
            for i, (role, sid, (b,s,w,d)) in enumerate(zip(roles, ids, selectors))]
        self.binding = dict(binding_version=1, scope="validated_original_rom_and_native_appended_stream_binding_only",
            manifest=self.manifest, manifest_sha256=runner.digest(self.manifest), original_manifest=self.original,
            original_binding=self.original_binding, original_rom_entries=1, original_rom_appended_entries_valid=False, **runner.FLAGS)
        self.write_metadata()

    def write_metadata(self):
        self.binding["manifest"] = self.manifest
        self.binding["manifest_sha256"] = runner.digest(self.manifest)
        mh, bh = runner.digest(self.manifest), runner.digest(self.binding)
        (self.path/"manifest.json").write_bytes(canonical(self.manifest))
        (self.path/"binding.json").write_bytes(canonical(self.binding))
        bytes_ = ", ".join("0x"+mh[i:i+2] for i in range(62,-1,-2))
        rows = ", ".join("{%dU, %dU, %dU, %dU}" % tuple(r[k] for k in ("bank","slot","width","depth")) for r in self.manifest["state"])
        (self.path/"manifest.inc").write_text("checkpoint_capture_manifest_t{{{"+bytes_+"}}, {"+rows+"}}")
        values = dict(NATIVE_DESCRIPTOR_LAYOUT_VERSION=1, ORIGINAL_ROM_ENTRIES=1, STREAM_ENTRIES=4,
            EXTERNAL_OWNERS=2, COORDINATOR_OWNERS=3, NATIVE_BITS=130, PHYSICAL_CLOCK_GATES=3,
            EXTERNAL_CLOCK_NETWORK=1, CAPTURE_NATIVE_CONTROL=1, SNAPSHOT_BANK=252, NATIVE_CONTROL_BANK=251,
            NATIVE_OWNER_BITS=283, RAW_CONTROL_BITS=760, SEPARATE_BANK_BITS=67, SHADOW_CONTROL_BITS=827,
            SHADOW_BITS=1585, SHADOW_LAYOUT_VERSION=2, SHADOW_RESTORE_SUPPORTED=0, FRAME_BYTES=64,
            TRANSPORT_VERSION=1, COMPLETE_FPGA_CAPTURE=0, DEPLOYABLE_CAPTURE_IMAGE=0,
            PRODUCTION_FREEZE_OWNERS_BOUND=0, METASIM_RESTORE_SUPPORTED=0)
        definitions = {k:str(v)+"U" for k,v in values.items()}
        definitions.update({k:'"'+v+'"' for k,v in dict(MANIFEST_SHA256=mh, DESCRIPTOR_BINDING_SHA256=bh,
            ORIGINAL_MANIFEST_SHA256=runner.digest(self.original), ORIGINAL_BINDING_SHA256=runner.digest(self.original_binding)).items()})
        (self.path/"constants.h").write_text("".join("#define NATIVE_%s %s\n" % item for item in definitions.items()))

    def audit(self):
        return runner.validate_descriptors(self.generated, self.sources)

    def test_exact_stream_abi_and_provenance_accept(self):
        result = self.audit()
        self.assertEqual((result["original_entries"],result["stream_entries"]),(1,4))
        self.assertEqual(result["manifest_sha256"],runner.digest(self.manifest))

    def test_coherently_rehashed_descriptor_order_width_selector_and_id_reject(self):
        saved = deepcopy(self.manifest)
        for mutation in (lambda m:m["state"].reverse(), lambda m:m["state"][1].update(depth=4),
            lambda m:m["state"][3].update(slot=0), lambda m:m["state"][0].update(bank=2),
            lambda m:m["state"][2].update(state_id="e"*64)):
            self.manifest=deepcopy(saved);mutation(self.manifest);self.write_metadata()
            with self.assertRaisesRegex(FormatError,"order/shape/StateID"):
                self.audit()

    def test_rehashed_source_owner_abi_and_coverage_claims_reject(self):
        saved=deepcopy(self.manifest)
        for mutation in (lambda m:m["sources"].update({runner.RESOURCES[0]:"0"*64}),
            lambda m:m["abi"].update(original_entries=4), lambda m:m["abi"]["external_owners"].reverse(),
            lambda m:m.update(complete_fpga_capture=True),lambda m:m["abi"].update(shadow_restore_supported=True),
            lambda m:m["abi"].update(external_clock_network=True)):
            self.manifest=deepcopy(saved);mutation(self.manifest);self.write_metadata()
            with self.assertRaises(FormatError): self.audit()

    def refresh_appended_ids(self):
        identity=dict(domain="native_transport_descriptor_v1",
            original_manifest_sha256=self.manifest["original_manifest_sha256"],
            original_binding_sha256=self.manifest["original_binding_sha256"],
            abi=self.manifest["abi"],sources=self.manifest["sources"])
        for row in self.manifest["state"][1:]:
            row["state_id"]=hashlib.sha256(canonical(identity)+b"\n"+row["domain"].encode()).hexdigest()
        self.write_metadata()

    def test_fully_rehashed_boolean_integer_abi_and_flag_substitutions_reject(self):
        saved=deepcopy(self.manifest)
        for key,value in (("external_clock_network",True),("original_entries",True),
            ("shadow_restore_supported",0),("capture_native_control",1)):
            self.manifest=deepcopy(saved);self.manifest["abi"][key]=value;self.refresh_appended_ids()
            with self.assertRaisesRegex(FormatError,"ABI/options differ"):self.audit()
        for value in (0,0.0):
            self.manifest=deepcopy(saved);self.manifest["complete_fpga_capture"]=value
            self.binding["complete_fpga_capture"]=value;self.refresh_appended_ids()
            with self.assertRaisesRegex(FormatError,"ownership claim differs"):self.audit()
        self.binding["complete_fpga_capture"]=False
        self.manifest=deepcopy(saved);self.manifest["state"][1]["ordinal"]=True;self.write_metadata()
        with self.assertRaisesRegex(FormatError,"order/shape/StateID"):self.audit()

    def test_fully_rehashed_boolean_versions_and_original_storage_fields_reject(self):
        self.manifest["descriptor_version"]=True;self.write_metadata()
        with self.assertRaisesRegex(FormatError,"descriptor scope"):self.audit()
        self.manifest["descriptor_version"]=1
        self.binding["original_rom_entries"]=True;self.write_metadata()
        with self.assertRaisesRegex(FormatError,"manifest/ROM identity"):self.audit()
        self.binding["original_rom_entries"]=1
        self.original_binding["state"][0]["bank"]=True
        self.manifest["original_binding_sha256"]=runner.digest(self.original_binding);self.refresh_appended_ids()
        with self.assertRaisesRegex(FormatError,"original fixture identity/selector"):self.audit()

    def test_original_provenance_and_selector_rehashes_reject(self):
        self.original_binding["state"][0]["bank"]=251
        self.manifest["original_binding_sha256"]=runner.digest(self.original_binding)
        self.write_metadata()
        with self.assertRaisesRegex(FormatError,"original fixture identity/selector"):self.audit()

    def test_original_omission_and_bad_hash_reject(self):
        for key in ("original_binding","original_manifest"):
            value=self.binding.pop(key);self.write_metadata()
            with self.assertRaisesRegex(FormatError,"original descriptor provenance"):self.audit()
            self.binding[key]=value
        self.original_binding["manifest_sha256"]="0"*64
        self.write_metadata()
        with self.assertRaisesRegex(FormatError,"provenance hash"):self.audit()

    def test_cpp_digest_order_header_count_and_duplicate_definitions_reject(self):
        for name, transform in (("manifest.inc",lambda s:s.replace("}}, {","}, {",1)),
            ("constants.h",lambda s:s.replace("NATIVE_ORIGINAL_ROM_ENTRIES 1U","NATIVE_ORIGINAL_ROM_ENTRIES 4U")),
            ("constants.h",lambda s:s+"#define NATIVE_STREAM_ENTRIES 4U\n")):
            self.write_metadata();p=self.path/name;p.write_text(transform(p.read_text()))
            with self.assertRaises(FormatError):self.audit()

    def test_noncanonical_or_aliased_metadata_reject(self):
        p=self.path/"manifest.json";p.write_text(json.dumps(self.manifest,indent=2))
        with self.assertRaisesRegex(FormatError,"noncanonical"):self.audit()

    def test_recorded_bench_uses_real_wrapper_and_never_drives_original_rom(self):
        text,receipt=runner.bench((runner.ROOT/runner.TB).read_text(),runner.digest(self.manifest))
        self.assertIn(runner.TOP+" dut(",text)
        self.assertNotIn(".io_descriptorValid(",text)
        self.assertIn("dut.endpoint.nativeTransport",text)
        self.assertIn("dut.originalROM.io_valid",text)
        self.assertIn("rom_seen==3'b111",text)
        self.assertIn("if(descriptor_entry>=1&&descriptor_entry<=3)rom_seen[descriptor_entry]=1",text)
        self.assertEqual(receipt["manifest_sha256"],runner.digest(self.manifest))
        self.assertEqual(len(receipt["transformations"]),8)
        with self.assertRaisesRegex(FormatError,"hierarchy observations"):
            runner.bench(text,runner.digest(self.manifest))

    def frozen_inputs(self):
        for name in runner.SOURCES:
            target=self.root/"sources"/name;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes((runner.ROOT/name).read_bytes())
        for name in runner.GENERATED:
            target=self.generated/name;target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists():target.write_text("generated fixture")
        generated={n:runner.sha(self.generated/n) for n in runner.GENERATED}
        scala_sources={n:h for n,h in self.sources.items() if n.endswith(".scala")}
        (self.root/"scala-execution.log").write_text("NATIVE_BOUND_ENDPOINT_ELABORATED original=1 stream=4 bits=130 gates=3 owners=2")
        (self.root/"scala-run.sh").write_text("actual run script fixture")
        scala=dict(status="pass",backend="f2",returncode=0,sources=scala_sources,
            generated=str(runner.RUNS/"offline-bound-fixture"),
            log_sha256=runner.sha(self.root/"scala-execution.log"),script_sha256=runner.sha(self.root/"scala-run.sh"),
            phases=[dict(passed=True,tests=1,succeeded=1,aborted=0,failed=0,canceled=0,ignored=0,pending=0) for _ in range(3)])
        (self.root/"scala-summary.json").write_bytes(canonical(scala))
        elaboration=dict(status="pass",backend="f2",scope="completed Scala native bound endpoint elaboration",
            scala=dict(path=str(runner.RUNS/"offline-bound-fixture/summary.json"),sha256=runner.sha(self.root/"scala-summary.json")),
            sources=scala_sources,generated=generated,generated_directory=scala["generated"])
        (self.root/"elaboration.json").write_bytes(canonical(elaboration))
        (self.root/"native.tcl").write_text(runner.tcl())
        transformed,transform=runner.bench((runner.ROOT/runner.TB).read_text(),runner.digest(self.manifest))
        (self.root/runner.BENCH).write_text(transformed)
        (self.root/"bench-transformation.json").write_bytes(canonical(transform))
        inputs={"sources/"+n:h for n,h in self.sources.items()}
        inputs.update({"generated/"+n:h for n,h in generated.items()})
        inputs.update({n:runner.sha(self.root/n) for n in runner.ELABORATION_INPUTS})
        inputs.update({n:runner.sha(self.root/n) for n in ("native.tcl",runner.BENCH,"bench-transformation.json")})
        return inputs

    def validate_frozen(self, inputs):
        # Generated descriptor auditing is exercised above; use a small stand-in
        # for RTL here to independently test receipt and frozen-input ownership.
        with patch.object(runner,"validate_generated",return_value={"descriptors":{"manifest_sha256":runner.digest(self.manifest)}}):
            return runner.validate_inputs(self.root,inputs,self.sources)

    def test_completed_three_phase_receipt_and_frozen_namespace_accept(self):
        self.validate_frozen(self.frozen_inputs())

    def test_rehashed_changed_recipe_or_bench_reject(self):
        for name in ("native.tcl",runner.BENCH,"bench-transformation.json"):
            inputs=self.frozen_inputs();p=self.root/name;p.write_text(p.read_text()+"\nchanged")
            inputs[name]=runner.sha(p)
            with self.assertRaisesRegex(FormatError,"namespace differs"):self.validate_frozen(inputs)

    def test_generated_tamper_cannot_be_repaired_by_rehashing_inputs(self):
        inputs=self.frozen_inputs();name=runner.TOP_FILE;p=self.generated/name;p.write_text("different generated top")
        inputs["generated/"+name]=runner.sha(p)
        with self.assertRaisesRegex(FormatError,"generated bytes differ"):self.validate_frozen(inputs)

    def test_incomplete_scala_execution_or_source_namespace_reject(self):
        for defect in ("phase","scope","source"):
            inputs=self.frozen_inputs()
            if defect=="phase":
                p=self.root/"scala-summary.json";value=json.loads(p.read_text());value["phases"][1]["failed"]=1
                p.write_bytes(canonical(value))
                e=self.root/"elaboration.json";edoc=json.loads(e.read_text());edoc["scala"]["sha256"]=runner.sha(p);e.write_bytes(canonical(edoc))
            else:
                p=self.root/"elaboration.json";value=json.loads(p.read_text())
                if defect=="scope":value["scope"]="completed Scala native endpoint elaboration"
                else:value["sources"].pop(next(iter(value["sources"])))
                p.write_bytes(canonical(value))
            for n in runner.ELABORATION_INPUTS:inputs[n]=runner.sha(self.root/n)
            with self.assertRaises(FormatError):self.validate_frozen(inputs)

    def fault_fixture(self,kind="coordinator",endpoint="dut.endpoint",extra=None,ack=0,early=False):
        native=endpoint+".nativeTransport."
        names=["clock","target_cycle","native_cut_cycle","frames","words","requests","control_acks","shadow_captures",
            "native_valid","endpoint_view","original_view","original_bank",native+"native_capture.phase"]
        data=[native+n for n in ("control_response_valid","response_ready","control_selected","response_data","control_response_data")]
        if kind=="native_data":names+=data
        values={n:0 for n in names};values.update(target_cycle=35,native_cut_cycle=35,original_bank=4,control_acks=ack)
        values[native+"native_capture.phase"]=3
        if kind=="native_data":values.update(frames=2,words=1,requests=1)
        def mismatch():
            values["native_valid"]=1
            if kind=="coordinator":values["endpoint_view"]=1
            else:
                for n in data[:3]:values[n]=1
                values[data[3]]=5;values[data[4]]=4
        snapshots=[(0,dict(values))]
        if early:
            values["clock"]=1;snapshots.append((500,dict(values)))
            mismatch();values["clock"]=0;snapshots.append((1000,dict(values)));snapshots.append((2000,dict(values)))
        values["clock"]=1;mismatch();snapshots.append((5000,dict(values)))
        values["clock"]=0;snapshots.append((10000,dict(values)));snapshots.append((11000,dict(values)))
        if extra is not None:values["clock"]=1;snapshots.append((extra,dict(values)))
        declarations="".join("$var wire 827 v%d %s $end\n"%(i,n) for i,n in enumerate(names))
        text="$timescale 1 ps $end\n$scope module native_widget_endpoint_tb $end\n"+declarations+"$upscope $end\n$enddefinitions $end\n"
        for time,row in snapshots:
            text+="#%d\n"%time+"".join("b%s v%d\n"%(format(row[n],"b"),i) for i,n in enumerate(names))
        path=self.root/"fault.vcd";path.write_text(text)
        signal="endpoint_coordinator_layout" if kind=="coordinator" else "native_control_saved_data"
        diagnostic="NATIVE_ENDPOINT_DIVERGENCE signal=%s raw_time=11000 raw_phase=3 target_cycle=35 cut=35 frames=%d words=%d requests=%d control_acks=%d shadow_captures=0"%(signal,values["frames"],values["words"],values["requests"],ack)
        return path,diagnostic

    def test_fault_wave_uses_low_phase_monitor_boundary_for_both_endpoint_hierarchies(self):
        for kind in ("coordinator","native_data"):
            for endpoint in ("dut","dut.endpoint"):
                path,line=self.fault_fixture(kind,endpoint)
                result=runner.audit_fault_wave(path,line,endpoint=endpoint)
                self.assertEqual(result["first_mismatch_timestamp"],5000)
                self.assertEqual(result["first_eligible_mismatch_timestamp"],11000)
                self.assertEqual(result["raw_clock_at_diagnosis"],0)
                self.assertEqual(result["raw_posedges_after_diagnosis"],0)

    def test_fault_wave_rejects_later_timestamp_missed_monitor_ack_and_false_log(self):
        path,line=self.fault_fixture(extra=12000)
        with self.assertRaisesRegex(FormatError,"settled low-phase"):runner.audit_fault_wave(path,line,endpoint="dut.endpoint")
        path,line=self.fault_fixture(early=True)
        with self.assertRaisesRegex(FormatError,"first eligible"):runner.audit_fault_wave(path,line,endpoint="dut.endpoint")
        path,line=self.fault_fixture(kind="native_data",ack=1)
        with self.assertRaisesRegex(FormatError,"acknowledged"):runner.audit_fault_wave(path,line,endpoint="dut.endpoint")
        path,line=self.fault_fixture()
        with self.assertRaisesRegex(FormatError,"counters/cut"):
            runner.audit_fault_wave(path,line.replace("cut=35","cut=36"),endpoint="dut.endpoint")

    def test_tcl_preserves_native_recipe_except_exact_bound_paths(self):
        text=runner.tcl()
        self.assertIn("synth_design -top "+runner.TOP,text)
        self.assertIn("read_verilog generated/"+runner.TOP_FILE,text)
        self.assertIn("-period 7.142857",text)
        self.assertNotIn("read_verilog generated/CheckpointNativeWidgetEndpoint.v",text)
        for resource in runner.RESOURCE_FILES:self.assertIn("generated/"+resource,text)


if __name__ == "__main__":
    unittest.main()
