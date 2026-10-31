"""Protect independent endpoint oracles while adapting to the installed widget."""
from contextlib import contextmanager
import copy
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.tests import verify_native_installed_widget as runner


class InstalledNativeBenchTests(unittest.TestCase):
    def setUp(self):
        self.original = (runner.ROOT / runner.base.TB).read_text()

    def test_installed_ports_retain_every_original_oracle_and_poison_descriptor_inputs(self):
        text, receipt = runner.bench(self.original, "a" * 64)
        before = re.findall(r'check\([^;]*?"([^"\n]+)"\)', self.original, re.S)
        after = re.findall(r'check\([^;]*?"([^"\n]+)"\)', text, re.S)
        self.assertTrue(before)
        self.assertEqual([n for n in after if n in before], before)
        self.assertIn("CheckpointCaptureWidget dut(", text)
        self.assertIn(".capture_descriptorValid(1'b0)", text)
        self.assertIn(".capture_descriptorBank(8'd99)", text)
        self.assertIn("dut.nativeEndpoint.originalROM.io_valid", text)
        self.assertIn("dut.nativeEndpoint.endpoint.nativeTransport", text)
        self.assertNotIn(".io_native_", text)
        self.assertNotIn(".io_descriptorValid(", text)
        self.assertIn("#1;expect_fault=1;owner_fault=1;#1;", text)
        self.assertIn("wire [11:0] bid,rid;", text)
        self.assertIn(".io_ctrl_aw_bits_id(12'hfa3)", text)
        self.assertIn(".io_ctrl_ar_bits_id(12'hb07)", text)
        self.assertEqual(text.count("bid==12'hfa3"), 2)
        self.assertEqual(text.count("rid==12'hb07"), 2)
        self.assertEqual(text.count("52'b0"), 4)
        self.assertNotIn("60'b0", text)
        self.assertEqual(receipt["manifest_sha256"], "a" * 64)

    def test_ambiguous_or_missing_native_ports_and_hierarchy_reject(self):
        for token in (".io_native_liveState(", ".io_native_readerIdle(",
                      ".io_endpointState(", "CheckpointNativeWidgetEndpoint dut("):
            for damaged in (self.original.replace(token, "bad_port(", 1), self.original + token):
                with self.subTest(token=token), self.assertRaises(FormatError):
                    runner.bench(damaged, "a" * 64)

    def test_invalid_manifest_cannot_replace_the_compiled_header_identity(self):
        for digest in ("", "g" * 64, "a" * 63, "a" * 64 + "\n#define ACCEPT 1"):
            with self.subTest(digest=digest), self.assertRaises(FormatError):
                runner.bench(self.original, digest)


class InstalledNativeReceiptTests(unittest.TestCase):
    """Synthetic receipts test admission rules only; no tool or hardware runs."""

    @staticmethod
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n" if isinstance(value, (dict, list)) else value)

    @contextmanager
    def scala_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "runs/scala"
            generated = output / "generated"
            sources = {}
            for name in runner.SOURCES:
                if name.endswith(".scala"):
                    self.write(root / name, "// synthetic Scala input: " + name + "\n")
                    sources[name] = runner.sha(root / name)
            for name in runner.FILES:
                self.write(generated / name, "synthetic emitted input: " + name + "\n")
            self.write(output / "execution.log", "NATIVE_CAPTURE_WIDGET_ELABORATED synthetic fixture only\n")
            self.write(output / "run.sh", "# synthetic receipt, never executed\n")
            phase = dict(passed=True, tests=1, succeeded=1, aborted=0, failed=0,
                         canceled=0, ignored=0, pending=0)
            doc = dict(status="pass", backend="f2", returncode=0,
                       phases=[copy.deepcopy(phase) for _ in range(3)], sources=sources,
                       generated=str(generated), log=str(output / "execution.log"),
                       log_sha256=runner.sha(output / "execution.log"),
                       script_sha256=runner.sha(output / "run.sh"),
                       generated_files={n: runner.sha(generated / n) for n in runner.FILES})
            receipt = output / "summary.json"
            self.write(receipt, doc)
            with patch.object(runner, "ROOT", root):
                yield receipt, generated, doc

    @contextmanager
    def native_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "runs/native"
            for name in runner.FILES:
                self.write(output / "generated" / name, "synthetic generated input: " + name + "\n")
            inputs = {n: runner.sha(output / "generated" / n) for n in runner.FILES}
            payloads = {
                "native.log": "Vivado v2025.2 (64-bit)\n"
                    "INSTALLED_NATIVE_TIMING setup_ns=0.125 hold_ns=0.025 period_ns=7.142857\n"
                    "INSTALLED_NATIVE_SYNTH_PASS bank_bits=67 registers=2500\n",
                "version.log": "Vivado v2025.2 (64-bit)\n",
                "native.tcl": runner.tcl(),
                "installed-native-widget.dcp": "synthetic DCP identity only; never a real checkpoint\n",
                "utilization.rpt": "synthetic utilization report\n",
                "timing.rpt": "synthetic timing report\n",
                "BUFGCE.v": "// synthetic vendor input\n",
                "glbl.v": "// synthetic global input\n",
                "installed-bench.sv": "// synthetic bench\n",
                "bench-adaptation.json": "{\"synthetic\": true}\n",
            }
            for name, value in payloads.items():
                self.write(output / name, value)
            commands = [dict(argv=argv, cwd=str(output), log=str(output / name),
                             log_sha256=runner.sha(output / name), returncode=0)
                        for argv, name in ((["vivado", "-mode", "batch", "-source", "native.tcl"], "native.log"),
                                           (["vivado", "-version"], "version.log"))]
            self.write(output / "commands.json", commands)
            sources = {"synthetic-source": "a" * 64}
            scala_hash = "b" * 64
            doc = dict(status="pass", backend="f2", sources=sources, inputs=inputs,
                       scala=dict(sha256=scala_hash), physical_fpga_capture=False,
                       full_image=False, complete_state_ownership=False, commands=commands,
                       timing=dict(frequency_mhz=140, setup_ns=0.125, hold_ns=0.025),
                       vendor_models={n: runner.sha(output / n) for n in ("BUFGCE.v", "glbl.v")},
                       artifacts={str(p.relative_to(output)): runner.sha(p)
                                  for p in output.rglob("*") if p.is_file()})
            receipt = output / "summary.json"
            self.write(receipt, doc)
            with patch.object(runner, "ROOT", root):
                yield receipt, doc, sources, inputs, scala_hash

    def save_native(self, receipt, doc, rehash=()):
        """Rehash selected changes, keeping a coherent ledger for semantic faults."""
        for name in rehash:
            doc["artifacts"][name] = runner.sha(receipt.parent / name)
            for row in doc.get("commands", []):
                if Path(row["log"]).name == name:
                    row["log_sha256"] = doc["artifacts"][name]
        if "commands" in doc:
            self.write(receipt.parent / "commands.json", doc["commands"])
            if "artifacts" in doc and "commands.json" in doc["artifacts"]:
                doc["artifacts"]["commands.json"] = runner.sha(receipt.parent / "commands.json")
        self.write(receipt, doc)

    def test_positive_synthetic_scala_and_native_receipts(self):
        with self.scala_fixture() as (receipt, generated, doc):
            self.assertEqual(runner.validate_scala(receipt, generated), doc)
        with self.native_fixture() as (receipt, doc, sources, inputs, scala_hash):
            self.assertEqual(runner.validate_native(receipt, sources, inputs, scala_hash), doc)
            self.assertFalse(doc["physical_fpga_capture"])
            self.assertFalse(doc["complete_state_ownership"])

    def test_scala_requires_generated_hashes_and_exact_rtl_and_probe_bytes(self):
        for fault in ("missing", "empty", "wrong_type", "missing_rtl", "renamed_probe", "rtl_bytes", "probe_bytes", "different_directory"):
            with self.subTest(fault=fault), self.scala_fixture() as (receipt, generated, doc):
                if fault == "missing":
                    del doc["generated_files"]
                elif fault == "empty":
                    doc["generated_files"] = {}
                elif fault == "wrong_type":
                    doc["generated_files"] = []
                elif fault == "missing_rtl":
                    del doc["generated_files"][runner.WIDGET + runner.TOP + ".v"]
                elif fault == "renamed_probe":
                    digest = doc["generated_files"].pop(runner.PROBE)
                    doc["generated_files"]["../substitute-probe.v"] = digest
                elif fault in ("rtl_bytes", "probe_bytes"):
                    name = runner.PROBE if fault == "probe_bytes" else runner.WIDGET + runner.TOP + ".v"
                    self.write(generated / name, "changed emitted RTL with unchanged Scala closure\n")
                else:
                    doc["generated"] = str(generated.parent / "other-generated")
                self.write(receipt, doc)
                with self.assertRaises(FormatError):
                    runner.validate_scala(receipt, generated)

    def test_native_requires_artifacts_commands_and_nonempty_bound_dcp(self):
        for fault in ("missing_artifacts", "empty_artifacts", "missing_commands", "empty_commands", "missing_dcp_entry", "empty_dcp", "changed_dcp", "missing_generated_probe"):
            with self.subTest(fault=fault), self.native_fixture() as (receipt, doc, sources, inputs, scala_hash):
                if fault == "missing_artifacts":
                    del doc["artifacts"]
                elif fault == "empty_artifacts":
                    doc["artifacts"] = {}
                elif fault == "missing_commands":
                    del doc["commands"]
                elif fault == "empty_commands":
                    doc["commands"] = []
                elif fault == "missing_dcp_entry":
                    del doc["artifacts"]["installed-native-widget.dcp"]
                elif fault in ("empty_dcp", "changed_dcp"):
                    self.write(receipt.parent / "installed-native-widget.dcp", "" if fault == "empty_dcp" else "different DCP\n")
                    if fault == "empty_dcp":
                        doc["artifacts"]["installed-native-widget.dcp"] = runner.sha(receipt.parent / "installed-native-widget.dcp")
                else:
                    del doc["artifacts"]["generated/" + runner.PROBE]
                self.save_native(receipt, doc)
                with self.assertRaises(FormatError):
                    runner.validate_native(receipt, sources, inputs, scala_hash)

    def test_rehashed_native_command_ledger_still_rejects_failed_or_wrong_execution(self):
        for fault in ("failed", "wrong_tool", "wrong_recipe", "wrong_cwd", "wrong_log", "extra_command"):
            with self.subTest(fault=fault), self.native_fixture() as (receipt, doc, sources, inputs, scala_hash):
                row = doc["commands"][0]
                if fault == "failed":
                    row["returncode"] = 1
                elif fault == "wrong_tool":
                    row["argv"][0] = "verilator"
                elif fault == "wrong_recipe":
                    row["argv"][-1] = "unrelated.tcl"
                elif fault == "wrong_cwd":
                    row["cwd"] = str(receipt.parent.parent)
                elif fault == "wrong_log":
                    row["log"] = str(receipt.parent / "version.log")
                    row["log_sha256"] = doc["artifacts"]["version.log"]
                else:
                    doc["commands"].append(copy.deepcopy(row))
                self.save_native(receipt, doc)
                with self.assertRaises(FormatError):
                    runner.validate_native(receipt, sources, inputs, scala_hash)

    def test_rehashed_native_logs_still_require_success_registers_and_140mhz_timing(self):
        for fault in ("error", "critical", "missing_pass", "wrong_bank_bits", "few_registers", "negative_setup", "negative_hold", "wrong_period", "missing_timing", "mismatched_timing"):
            with self.subTest(fault=fault), self.native_fixture() as (receipt, doc, sources, inputs, scala_hash):
                log = receipt.parent / "native.log"
                text = log.read_text()
                if fault == "error":
                    text += "ERROR: synthesis failed\n"
                elif fault == "critical":
                    text += "CRITICAL WARNING: incomplete design\n"
                elif fault == "missing_pass":
                    text = text.replace("INSTALLED_NATIVE_SYNTH_PASS", "UNVERIFIED_SYNTH")
                elif fault == "wrong_bank_bits":
                    text = text.replace("bank_bits=67", "bank_bits=66")
                elif fault == "few_registers":
                    text = text.replace("registers=2500", "registers=2399")
                elif fault == "negative_setup":
                    text = text.replace("setup_ns=0.125", "setup_ns=-0.125")
                    doc["timing"]["setup_ns"] = -0.125
                elif fault == "negative_hold":
                    text = text.replace("hold_ns=0.025", "hold_ns=-0.025")
                    doc["timing"]["hold_ns"] = -0.025
                elif fault == "wrong_period":
                    text = text.replace("period_ns=7.142857", "period_ns=10.000000")
                elif fault == "missing_timing":
                    text = text.replace("INSTALLED_NATIVE_TIMING", "UNVERIFIED_TIMING")
                else:
                    doc["timing"]["setup_ns"] = 1.0
                self.write(log, text)
                self.save_native(receipt, doc, rehash=("native.log",))
                with self.assertRaises(FormatError):
                    runner.validate_native(receipt, sources, inputs, scala_hash)

    def test_rehashed_version_log_must_identify_native_2025_2_vivado(self):
        for text in ("Icarus Verilog version 12.0\n", "Vivado v2025.1 (64-bit)\n",
                     "Vivado v2025.2 (32-bit)\n", "# expected Vivado v2025.2 (64-bit)\n"):
            with self.subTest(version=text), self.native_fixture() as (receipt, doc, sources, inputs, scala_hash):
                self.write(receipt.parent / "version.log", text)
                self.save_native(receipt, doc, rehash=("version.log",))
                with self.assertRaises(FormatError):
                    runner.validate_native(receipt, sources, inputs, scala_hash)

    def test_rehashed_recipe_and_generated_inputs_cannot_substitute_different_build(self):
        for name in ("native.tcl", "generated/" + runner.WIDGET + runner.TOP + ".v", "generated/" + runner.PROBE):
            with self.subTest(name=name), self.native_fixture() as (receipt, doc, sources, inputs, scala_hash):
                path = receipt.parent / name
                self.write(path, path.read_text() + "// different build input\n")
                self.save_native(receipt, doc, rehash=(name,))
                with self.assertRaises(FormatError):
                    runner.validate_native(receipt, sources, inputs, scala_hash)


if __name__ == "__main__":
    unittest.main()
