"""Inventory scope must match the actual runtime, including all API pages."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import f2_inventory


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.invocation = Path(self.temporary.name)
        self.scope = patch.object(f2_inventory, "RUNS", self.invocation)
        self.scope.start()
        self.addCleanup(self.scope.stop)
        self.manifest = dict(run_farm_tag="checkpoint-f2-test", build_execution="localhost",
                             build_dir=str(self.invocation / "build-host"), commands={})
        self.runtime = dict(run_farm=dict(recipe_arg_overrides=dict(run_farm_tag="checkpoint-f2-test")),
                            metasimulation=dict(metasimulation_enabled=False))
        self.write_configs()

    def write_configs(self):
        (self.invocation / "manager-commands.json").write_text(json.dumps(self.manifest))
        (self.invocation / "config_runtime.yaml").write_text(yaml.safe_dump(self.runtime))

    def test_inventory_uses_fsimcluster_and_keeps_all_pages_and_states(self):
        session = MagicMock(region_name="us-west-2")
        ec2, sts = MagicMock(), MagicMock()
        session.client.side_effect = lambda service: {"ec2": ec2, "sts": sts}[service]
        instances = [dict(InstanceId="i-live", State=dict(Name="running")),
                     dict(InstanceId="i-stopped", State=dict(Name="stopped")),
                     dict(InstanceId="i-gone", State=dict(Name="terminated"))]
        paginator = ec2.get_paginator.return_value
        paginator.paginate.return_value = [dict(Reservations=[dict(Instances=instances[:1])]),
                                            dict(Reservations=[dict(Instances=instances[1:])])]
        sts.get_caller_identity.return_value = {"Account": "123"}
        with patch.object(f2_inventory, "build_processes", return_value={"backend": "test", "processes": []}):
            result = f2_inventory.collect(self.invocation, session)
        paginator.paginate.assert_called_once_with(
            Filters=[{"Name": "tag:fsimcluster", "Values": ["checkpoint-f2-test"]}])
        self.assertEqual(result["instances"], instances)
        self.assertEqual(result["aws_identity"], {"Account": "123"})
        self.assertIs(result["metasimulation_enabled"], False)
        self.assertIn("config_runtime.yaml", result["config_sha256"])

    def test_mismatched_manifest_or_metasim_rejects_before_aws(self):
        session = MagicMock()
        self.runtime["run_farm"]["recipe_arg_overrides"]["run_farm_tag"] = "checkpoint-f2-other"
        self.write_configs()
        with self.assertRaisesRegex(ValueError, "agree"):
            f2_inventory.collect(self.invocation, session)
        self.runtime["run_farm"]["recipe_arg_overrides"]["run_farm_tag"] = "checkpoint-f2-test"
        self.runtime["metasimulation"]["metasimulation_enabled"] = True
        self.write_configs()
        with self.assertRaisesRegex(ValueError, "metasimulation_enabled"):
            f2_inventory.collect(self.invocation, session)
        session.client.assert_not_called()

    def test_aws_failure_is_not_an_empty_successful_inventory(self):
        session = MagicMock()
        session.client.return_value.get_paginator.return_value.paginate.side_effect = RuntimeError("AccessDenied")
        with self.assertRaisesRegex(RuntimeError, "AccessDenied"):
            f2_inventory.collect(self.invocation, session)


if __name__ == "__main__":
    unittest.main()
