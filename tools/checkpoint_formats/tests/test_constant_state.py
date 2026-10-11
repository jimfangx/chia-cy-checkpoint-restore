"""Schema/security oracles only; real Jasper/CAD/VCS checks are separate."""

import copy
import json
import unittest

from tools.checkpoint_formats.codec import FormatError
from tools.checkpoint_formats.constant_state import INPUTS, SCRIPT, binding
from tools.checkpoint_formats.formal_state_map import export_state_map, gate_deposits, sha, validate_state_map
from tools.checkpoint_formats.semantic import encode_semantic
from tools.checkpoint_formats.tests import test_formal_state_map as fixture_module


def fixture():
    f = fixture_module.FormalStateMapTests()
    f.setUp()
    artifacts = f.unread_artifacts()
    del artifacts["optimization_report"]
    artifacts["evidence"] = artifacts["evidence"].replace(
        b"FORMAT\tformality-state-v3\nVERIFY\t1\nORIENTATION\trtl-reference\n",
        b"FORMAT\tformality-state-v1\nVERIFY\t1\n").replace(
        b"OPTIMIZED\tunread\tr:/WORK/DUT/saved_reg[1]\n", b"")
    spec = dict(constant_version=1, top="DUT", bits=[dict(signal="saved", width=2, bit=1, value=1)])
    artifacts.update(constant_spec=json.dumps(spec).encode(), constant_bind=binding(spec), constant_script=SCRIPT.encode())
    rows = ["FORMAT\tjasper-constant-v1"] + [f"INPUT\t{r}\t{sha(artifacts[r])}" for r in INPUTS]
    props = {"<embedded>::DUT.checkpoint_constant_proof.constant_0": ("assert", "proven"),
             "<embedded>::DUT.checkpoint_constant_proof.constant_0:precondition1": ("cover", "covered"),
             "<embedded>::DUT.checkpoint_constant_proof.checkpoint_edge": ("cover", "covered")}
    rows += [f"PROPERTY\t{p}\t{k}\t{s}" for p, (k, s) in props.items()]
    artifacts["constant_results"] = ("\n".join(rows + ["END"]) + "\n").encode()
    log = ["CHECKPOINT_CONSTANT_RESET=none", "Exiting the analysis session with status 0."]
    log += [f"CHECKPOINT_CONSTANT_INPUT\t{r}\t{sha(artifacts[r])}" for r in INPUTS]
    for p, (k, s) in props.items():
        log += [f"CHECKPOINT_CONSTANT_PROPERTY\t{p}\t{k}\t{s}",
                f'The {"cover " if k == "cover" else ""}property "{p.split("::", 1)[1]}" was {s} in 0.00 s.']
    artifacts["constant_log"] = ("\n".join(log) + "\n").encode()
    return f, artifacts


class ConstantStateTests(unittest.TestCase):
    def setUp(self):
        self.f, self.artifacts = fixture()

    def export(self, artifacts=None):
        return export_state_map(self.f.manifest, "DUT", self.f.adapter, artifacts or self.artifacts)

    def deposits(self, mapping, checkpoint):
        return gate_deposits(mapping, self.f.manifest, self.f.adapter, self.artifacts,
                             encode_semantic(checkpoint, self.f.manifest), self.f.build, "tb.gate")

    def test_proven_constant_keeps_identity_and_enforces_value_and_horizon(self):
        mapping = self.export()
        self.assertEqual((mapping["map_version"], mapping["semantic_bits"], mapping["gate_storage_bits"]), (4, 6, 6))
        self.assertEqual(len(self.deposits(mapping, self.f.checkpoint)[1]), 6)
        for cycle in (1, 17, 1000):
            cp = copy.deepcopy(self.f.checkpoint)
            cp["target_cycle"] = cycle
            self.deposits(mapping, cp)
        cp = copy.deepcopy(self.f.checkpoint)
        cp["target_cycle"] = 0
        with self.assertRaisesRegex(FormatError, "constant horizon"):
            self.deposits(mapping, cp)
        cp = copy.deepcopy(self.f.checkpoint)
        next(r for r in cp["records"] if r["depth"] == 1)["values"] = ["1"]
        with self.assertRaisesRegex(FormatError, "conflicts with proven constant"):
            self.deposits(mapping, cp)

    def test_missing_bounded_vacuous_or_constrained_properties_reject(self):
        results = self.artifacts["constant_results"]
        for changed in (results.replace(b"\tassert\tproven", b"\tassert\tbounded_proven"),
                        results.replace(b"\tcover\tcovered", b"\tcover\tunreachable", 1),
                        results.replace(b"END\n", b"PROPERTY\textra\tassume\tproven\nEND\n"),
                        results.replace(b"END\n", b""),
                        b"\n".join(row for row in results.split(b"\n") if b"constant_0\tassert" not in row)):
            with self.subTest(data=changed), self.assertRaises(FormatError):
                self.export(dict(self.artifacts, constant_results=changed))

    def test_predicates_and_runner_must_be_audited_and_bound(self):
        for role in INPUTS:
            with self.subTest(role=role), self.assertRaises(FormatError):
                self.export(dict(self.artifacts, **{role: self.artifacts[role] + b"\n"}))
        spec = json.loads(self.artifacts["constant_spec"])
        for mutate in (lambda s: s["bits"][0].update(signal="ram"),
                       lambda s: s["bits"][0].update(width=3),
                       lambda s: s["bits"][0].update(value=2),
                       lambda s: s["bits"].append(s["bits"][0]),
                       lambda s: s.update(top="OTHER")):
            changed = copy.deepcopy(spec)
            mutate(changed)
            with self.subTest(spec=changed), self.assertRaises(FormatError):
                self.export(dict(self.artifacts, constant_spec=json.dumps(changed).encode()))

    def test_machine_status_alone_cannot_replace_raw_engine_evidence(self):
        log = self.artifacts["constant_log"]
        for changed in (log.replace(b"was proven", b"was bounded_proven"),
                        log.replace(b"\tassert\tproven", b"\tassert\tcex"),
                        log.replace(b"CHECKPOINT_CONSTANT_INPUT\trtl", b"CHECKPOINT_CONSTANT_INPUT\tother"),
                        log.replace(b"RESET=none", b"RESET=reset"), log + b"ERROR: tool failed\n"):
            with self.subTest(log=changed), self.assertRaises(FormatError):
                self.export(dict(self.artifacts, constant_log=changed))

    def test_global_pass_cannot_excuse_missing_constants_or_gate_proof(self):
        for role in self.artifacts:
            if role.startswith("constant_"):
                missing = dict(self.artifacts)
                del missing[role]
                with self.subTest(role=role), self.assertRaises(FormatError):
                    self.export(missing)
        missing = {k: v for k, v in self.artifacts.items() if not k.startswith("constant_")}
        with self.assertRaisesRegex(FormatError, "unproven or unmappable semantic state"):
            self.export(missing)
        row = next(r for r in self.artifacts["evidence"].splitlines() if r.startswith(b"PROVEN\t"))
        with self.assertRaises(FormatError):
            self.export(dict(self.artifacts, evidence=self.artifacts["evidence"].replace(row + b"\n", b"")))

    def test_map_proof_fields_and_build_artifacts_revalidate_before_translation(self):
        mapping = self.export()
        entry = next(e for e in mapping["entries"] if not e["gates"])
        for field, value in (("value", 0), ("min_target_cycle", 0), ("proof_status", "matched")):
            changed = copy.deepcopy(mapping)
            next(e for e in changed["entries"] if e["formal_reference"] == entry["formal_reference"])["optimization"][field] = value
            with self.assertRaises(FormatError):
                self.deposits(changed, self.f.checkpoint)
        for role in self.artifacts:
            with self.subTest(role=role), self.assertRaises(FormatError):
                validate_state_map(mapping, self.f.manifest, self.f.adapter,
                                   dict(self.artifacts, **{role: self.artifacts[role] + b"\n"}))
