import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools.checkpoint_formats.codec import FormatError, canonical
from tools.checkpoint_formats.simulator import (check_generated_rtl, generated_capture,
                                                generated_words, validate_generated_manifest,
                                                prepare_generated_stream_probe, validate_generated_stream,
                                                prepare_settled_generated_probe)


def fixture():
    state = []
    for path, width, depth, kind in (("Top.counter", 257, 1, "register"), ("Top.fifo", 9, 2, "memory")):
        identity = hashlib.sha256(canonical(dict(hierarchy=path, kind=kind,
                                                namespace="generated-simulator-state-v1"))).hexdigest()
        state.append(dict(state_id=identity, hierarchy=path, module="Top", kind=kind, width=width,
                          depth=depth, signed=False, clock_expression="clock", reset_expression="none",
                          adapter="firrtl-" + kind + "-v1", bit_order="lsb0", address_order="ascending_zero_based"))
    return dict(manifest_version=1, manifest_type="fsckpt-generated", identity_scheme="generated-simulator-state-v1",
                circuit="Top", root_module="Top", scope="generated_rtl_only", external_runtime_required=True,
                reference_sha256=hashlib.sha256(b"reference").hexdigest(),
                instances=[dict(hierarchy="Top", module="Top", implementation_sha256="a"*64)],
                state=sorted(state, key=lambda e: e["state_id"]))


class SimulatorInventoryTest(unittest.TestCase):
    def test_wide_and_memory_values_are_complete_and_independent(self):
        m = fixture()
        words = list(generated_words(m))
        values = [f"{(1 << w['width']) - 1:0{(w['width']+3)//4}x}" for w in words]
        capture = generated_capture(m, values, 17)
        self.assertEqual(len(capture["records"]), 3)
        self.assertEqual(capture["capture_type"], "generated_rtl_diagnostic")
        self.assertTrue(capture["external_runtime_required"])
        self.assertEqual(capture["manifest_sha256"], hashlib.sha256(canonical(m)).hexdigest())
        self.assertEqual([r["value"] for r in capture["records"]], values)
        for bad in (values[:-1], values + ["0"], ["x"*len(v) for v in values], ["f"*len(v) for v in values]):
            with self.assertRaises(FormatError):
                generated_capture(m, bad, 17)

    def test_manifest_rejects_semantic_inventory_bad_ids_shapes_and_owners(self):
        for mutation in (
            lambda m: m.update(manifest_type="rtlckpt"),
            lambda m: m.update(external_runtime_required=False),
            lambda m: m["state"][0].update(state_id="0"*64),
            lambda m: m["state"][0].update(width=True),
            lambda m: m["state"][0].update(width=0),
            lambda m: m["state"][0].update(adapter="opaque"),
            lambda m: m["state"][0].update(module="Absent"),
            lambda m: m["state"].append(copy.deepcopy(m["state"][0])),
            lambda m: m.update(state=list(reversed(m["state"]))),
        ):
            m = fixture()
            mutation(m)
            with self.assertRaises(FormatError):
                validate_generated_manifest(m)

    def test_emitted_coverage_rejects_missing_extra_reshaped_and_wrong_reference(self):
        m = fixture()
        rtl = "module Top(input clock); reg [256:0] counter; reg [8:0] fifo [0:1]; endmodule"
        check_generated_rtl(m, "reference", rtl, "")
        for bad in (rtl.replace("reg [256:0] counter;", ""),
                    rtl.replace("endmodule", "reg hidden; endmodule"),
                    rtl.replace("endmodule", "reg [5:1] unsupported; endmodule"),
                    rtl.replace("[0:1]", "[0:2]")):
            with self.assertRaises(FormatError):
                check_generated_rtl(m, "reference", bad, "")
        with self.assertRaises(FormatError):
            check_generated_rtl(m, "modified", rtl, "")

    def test_stream_covers_complete_memories_and_rejects_corrupt_membership(self):
        m = fixture()
        header = dict(capture_version=2, capture_type="generated_rtl_diagnostic", scope="generated_rtl_only",
                      external_runtime_required=True, manifest_sha256=hashlib.sha256(canonical(m)).hexdigest(),
                      sample_phase="settled_host_negedge", host_sample=7, stage=0)
        rows = [header] + [dict(state_id=e["state_id"], width=e["width"], depth=e["depth"],
                               values=[f"{(1 << e['width']) - 1:0{(e['width']+3)//4}x}"] * e["depth"])
                           for e in m["state"]]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.jsonl"
            def write(value):
                path.write_text("".join(json.dumps(row) + "\n" for row in value))
            write(rows)
            observed = validate_generated_stream(m, path, 1)
            self.assertEqual(observed[0]["words"], 3)
            self.assertEqual(observed[0]["scalars"]["Top.counter"], (1 << 257) - 1)
            memory = next(i for i, e in enumerate(m["state"], 1) if e["kind"] == "memory")
            mutations = (
                lambda r: r[0].update(external_runtime_required=False),
                lambda r: r[0].update(manifest_sha256="0"*64),
                lambda r: r[0].update(host_sample=True),
                lambda r: r[0].update(stage=1),
                lambda r: r[memory].update(values=r[memory]["values"][:-1]),
                lambda r: r[memory].update(width=8),
                lambda r: r[memory].update(depth=True),
                lambda r: r[memory].update(values=["xxx", "xxx"]),
                lambda r: r[memory].update(values=["fff", "fff"]),
                lambda r: r[memory].update(state_id="0"*64),
                lambda r: r.reverse(),
                lambda r: r.pop(),
                lambda r: r.append(r[-1]),
            )
            for mutate in mutations:
                altered = copy.deepcopy(rows)
                mutate(altered)
                write(altered)
                with self.assertRaises(FormatError):
                    validate_generated_stream(m, path, 1)
            write(rows + [dict(header, host_sample=8, stage=1)] + rows[1:])
            self.assertEqual(len(validate_generated_stream(m, path, 2)), 2)
            write(rows + [dict(header, host_sample=7, stage=1)] + rows[1:])
            with self.assertRaises(FormatError):
                validate_generated_stream(m, path, 2)

    def test_stream_probe_bounds_generation_by_entries_and_requires_manifested_triggers(self):
        m = fixture()
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            prepare_generated_stream_probe(m, out, [{"Top.counter": 1}])
            source = (out / "generated-probe.sv").read_text()
            self.assertIn("emul.Top.fifo[address]", source)
            self.assertIn("address < 2", source)
            self.assertIn("emul.Top.counter >= 257'd1", source)
            for bad in ([], [{}], [{"Top.absent": 1}], [{"Top.fifo": 1}],
                        [{"Top.counter": True}], [{"Top.counter": 1 << 257}]):
                with self.assertRaises(FormatError):
                    prepare_generated_stream_probe(m, out, bad)

    def test_settled_phase_requires_explicit_validator_and_reads_every_memory_word(self):
        m = fixture()
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            prepare_settled_generated_probe(m, out)
            source = (out / "settled-generated-probe.sv").read_text()
            self.assertIn("emul.checkpoint_settled_event", source)
            self.assertIn("emul.Top.fifo[address]", source)
            self.assertIn("settled_host_posedge_parked_driver", source)
            header = dict(capture_version=2, capture_type="generated_rtl_diagnostic", scope="generated_rtl_only",
                          external_runtime_required=True, manifest_sha256=hashlib.sha256(canonical(m)).hexdigest(),
                          sample_phase="settled_host_posedge_parked_driver", host_sample=7, stage=0)
            records = [dict(state_id=e["state_id"], width=e["width"], depth=e["depth"],
                            values=["0" * ((e["width"] + 3) // 4)] * e["depth"]) for e in m["state"]]
            path = out / "capture.jsonl"
            path.write_text("\n".join(json.dumps(r) for r in [header, *records]) + "\n")
            with self.assertRaises(FormatError):
                validate_generated_stream(m, path, 1)
            self.assertEqual(len(validate_generated_stream(m, path, 1, header["sample_phase"])), 1)
            prepare_settled_generated_probe(m, out, lowclock=True)
            self.assertIn("settled_host_negedge_parked_driver", (out / "settled-generated-probe.sv").read_text())
            header["sample_phase"] = "settled_host_negedge_parked_driver"
            path.write_text("\n".join(json.dumps(r) for r in [header, *records]) + "\n")
            self.assertEqual(len(validate_generated_stream(m, path, 1, header["sample_phase"])), 1)
            for phase in ("settled_host_negedge", "settled_host_posedge_parked_driver"):
                with self.assertRaises(FormatError):
                    validate_generated_stream(m, path, 1, phase)
            with self.assertRaises(FormatError):
                validate_generated_stream(m, path, 1, "unknown")


if __name__ == "__main__":
    unittest.main()
