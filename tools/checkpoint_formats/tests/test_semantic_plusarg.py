"""Strict complete semantic ownership of init-only external storage."""
import copy
import unittest
from pathlib import Path
import tempfile

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.replay import prepare_capture
from tools.checkpoint_formats.semantic import PLUSARG_MODEL_SHA256, manifest_hash, state_id, validate_manifest
from tools.checkpoint_formats.tests.test_replay import fixture


def adapted_fixture():
    manifest, boundary, rtl = fixture()
    model = dict(hierarchy="Harness.dut.reader", module="Reader9", adapter="semantic-plusarg-v1",
                 defname="plusarg_reader", source_sha256=PLUSARG_MODEL_SHA256, width=9, default=7,
                 format="semantic_value=%d")
    manifest.update(manifest_version=2, external_models=[model])
    path = model["hierarchy"] + ".myplus"
    manifest["state"].append(dict(state_id=state_id(path, "register"), hierarchy=path, kind="register",
                                  width=9, depth=1, signed=False, clock_domain="initial", reset="none",
                                  bit_order="lsb0", address_order="ascending_zero_based"))
    manifest["state"].sort(key=lambda e: e["state_id"])
    rtl = rtl.replace("endmodule", 'plusarg_reader #(.WIDTH(9), .FORMAT("semantic_value=%d"), .DEFAULT(7)) reader (.out(result));\nendmodule')
    model_text = (Path(__file__).resolve().parents[3] /
                  "generators/rocket-chip/src/main/resources/vsrc/plusarg_reader.v").read_text()
    return manifest, boundary, rtl + model_text


class SemanticPlusargTests(unittest.TestCase):
    def test_nonobject_manifests_reject_with_an_explicit_format_error(self):
        for value in (None, [], 'manifest', 2, True):
            with self.assertRaisesRegex(FormatError, 'manifest must be an object'):
                validate_manifest(value)

    def test_exact_external_bindings_and_emitted_source_are_required(self):
        manifest, boundary, rtl = adapted_fixture()
        validate_manifest(manifest)
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            prepare_capture(manifest, boundary, rtl, rtl + "DUT dut();", out)
            for altered in (rtl.replace('.DEFAULT(7)', '.DEFAULT(8)'),
                            rtl.replace('semantic_value=%d', 'other_value=%d'),
                            rtl.replace('myplus = DEFAULT', 'myplus = 0'),
                            rtl.replace('reader (.out', 'lost (.out'),
                            '`define SYNTHESIS\n' + rtl,
                            rtl + rtl[rtl.index('// See LICENSE.SiFive'):]):
                with self.assertRaises(FormatError):
                    prepare_capture(manifest, boundary, rtl, altered + "DUT dut();", out)

    def test_init_only_domain_cannot_hide_missing_reshaped_or_unbound_owners(self):
        manifest, _, _ = adapted_fixture()
        initialized = next(i for i, e in enumerate(manifest["state"]) if e["clock_domain"] == "initial")
        cases = [lambda m: m.update(manifest_version=1),
                 lambda m: m.update(external_models=[]),
                 lambda m: m["external_models"].append(copy.deepcopy(m["external_models"][0])),
                 lambda m: m["external_models"][0].update(hierarchy="Harness.other.reader"),
                 lambda m: m["external_models"][0].update(source_sha256="0" * 64),
                 lambda m: m["external_models"][0].update(format="unsafe=%s"),
                 lambda m: m["external_models"][0].update(default=512),
                 lambda m: m["state"].pop(initialized),
                 lambda m: m["state"][initialized].update(width=8),
                 lambda m: m["state"][initialized].update(signed=True),
                 lambda m: m["state"][initialized].update(reset="synchronous"),
                 lambda m: m["state"][initialized].update(clock_domain="Harness.dut.clock"),
                 lambda m: next(e for e in m["state"] if e["clock_domain"] != "initial").update(clock_domain="initial")]
        for mutate in cases:
            altered = copy.deepcopy(manifest)
            mutate(altered)
            with self.assertRaises(FormatError):
                validate_manifest(altered)

    def test_external_default_and_format_change_image_build_identity(self):
        manifest, _, _ = adapted_fixture()
        for changes in (dict(default=8), dict(format="other_value=%h"), dict(module="OtherReader")):
            altered = copy.deepcopy(manifest)
            altered["external_models"][0].update(changes)
            self.assertNotEqual(manifest_hash(manifest), manifest_hash(altered))


if __name__ == "__main__":
    unittest.main()
