"""Offline AWS F2 configuration/routing checks; no cloud resources are launched."""

from contextlib import contextmanager
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import f2


class F2Tests(unittest.TestCase):
    @contextmanager
    def invocation(self):
        with tempfile.TemporaryDirectory() as directory:
            runs = Path(directory) / "runs"
            runs.mkdir()
            with patch.object(f2, "RUNS", runs):
                yield runs / "invocation"

    def test_baseline_is_single_actual_f2_and_never_claims_capture(self):
        with self.invocation() as out:
            result = f2.prepare("Rocket", "selfcheck.json", out, phase="baseline")
            runtime = yaml.safe_load((out / "config_runtime.yaml").read_text())
            self.assertIs(runtime["metasimulation"]["metasimulation_enabled"], False)
            farm = runtime["run_farm"]["recipe_arg_overrides"]
            self.assertEqual(farm["run_farm_hosts_to_use"], [{"f2.6xlarge": 1}])
            self.assertFalse(farm["always_expand_run_farm"])
            self.assertTrue(farm["run_farm_tag"].startswith("checkpoint-f2-"))
            self.assertEqual(runtime["target_config"]["no_net_num_nodes"], 1)
            self.assertTrue(result["hwdb_ready"])
            self.assertFalse(result["checkpoint_hardware_verified"])
            self.assertEqual(result["intended_capture_source"], "aws-f2")
            for task, command in result["commands"].items():
                self.assertEqual(command["backend"], "f2")
                self.assertEqual(command["argv"][:2], ["firesim", task])
                for option in ("-c", "-b", "-r", "-a"):
                    self.assertTrue(Path(command["argv"][command["argv"].index(option) + 1]).is_file())
            self.assertIn("--forceterminate", result["commands"]["terminaterunfarm"]["argv"])
            build = yaml.safe_load((out / "config_build.yaml").read_text())
            self.assertEqual(build["share_with_accounts"], {})
            farm = build["build_farm"]
            self.assertEqual(Path(farm["base_recipe"]).name, "externally_provisioned.yaml")
            self.assertEqual(farm["recipe_arg_overrides"],
                             {"default_build_dir": str(out / "build-host"), "build_farm_hosts": ["localhost"]})
            self.assertEqual(result["build_execution"], "localhost")

    def test_checkpoint_build_has_no_invented_agfi_and_keeps_exact_recipe(self):
        with self.invocation() as out:
            result = f2.prepare("Rocket", "selfcheck.json", out)
            self.assertFalse(result["hwdb_ready"])
            self.assertEqual(yaml.safe_load((out / "config_hwdb.yaml").read_text()), {})
            original = yaml.safe_load((f2.ROOT / "sims/firesim-staging/sample_config_build_recipes.yaml").read_text())[f2.RECIPES["Rocket"]]
            generated = yaml.safe_load((out / "config_build_recipes.yaml").read_text())[f2.RECIPES["Rocket"]]
            for key in ("PLATFORM", "TARGET_PROJECT", "DESIGN", "TARGET_CONFIG", "PLATFORM_CONFIG", "platform_config_args"):
                self.assertEqual(generated[key], original[key])
            self.assertTrue(Path(generated["TARGET_PROJECT_MAKEFRAG"]).is_dir())
            self.assertTrue(Path(generated["bit_builder_recipe"]).is_file())

    def test_public_image_cannot_be_selected_as_checkpoint_hardware(self):
        with self.invocation() as out:
            stock = f2.ROOT / "sims/firesim-staging/sample_config_hwdb.yaml"
            with self.assertRaisesRegex(ValueError, "baseline-only"):
                f2.prepare("Rocket", "selfcheck.json", out, hwdb=stock)
            self.assertFalse(out.exists())

    def test_custom_hwdb_is_an_intent_without_hardware_verification(self):
        with self.invocation() as out:
            hwdb = out.parent / "custom.yaml"
            hwdb.write_text(yaml.safe_dump({"custom-rocket": {"agfi": "agfi-abc123"}}))
            result = f2.prepare("Rocket", "selfcheck.json", out, hwdb=hwdb, hwconfig="custom-rocket")
            self.assertTrue(result["hwdb_ready"])
            self.assertFalse(result["checkpoint_hardware_verified"])
            self.assertEqual(yaml.safe_load((out / "config_runtime.yaml").read_text())["target_config"]["default_hw_config"],
                             "custom-rocket")

    def test_existing_invocation_and_unscoped_tags_are_rejected(self):
        with self.invocation() as out:
            with self.assertRaisesRegex(ValueError, "tag"):
                f2.prepare("Rocket", "selfcheck.json", out, tag="mainrunfarm")
            f2.prepare("Rocket", "selfcheck.json", out)
            original = (out / "manager-commands.json").read_bytes()
            with self.assertRaisesRegex(ValueError, "retained invocation"):
                f2.prepare("Rocket", "other.json", out)
            self.assertEqual((out / "manager-commands.json").read_bytes(), original)

    def test_initialized_configs_are_inputs_and_customizations_survive(self):
        with self.invocation() as out:
            deploy = out.parent / "manager/sims/firesim/deploy"
            deploy.mkdir(parents=True)
            runtime, _ = f2.manager_config("runtime")
            runtime["target_config"]["plusarg_passthrough"] = "+user-setting=1"
            runtime["run_farm"]["recipe_arg_overrides"] = {
                "default_simulation_dir": "/custom/runtime", "run_instance_market": "spot"}
            recipe_name = f2.RECIPES["Rocket"]
            recipe = yaml.safe_load((f2.ROOT / "sims/firesim-staging/sample_config_build_recipes.yaml").read_text())[recipe_name]
            recipe["bit_builder_arg_overrides"] = {"s3_bucket_name": "user-configured-bucket"}
            configs = {
                "runtime": runtime,
                "build": {"build_farm": {"base_recipe": "build-farm-recipes/aws_ec2.yaml"},
                          "builds_to_run": ["user-default"], "user_build_option": "keep"},
                "build_recipes": {recipe_name: recipe},
                "hwdb": {recipe_name: {"agfi": "agfi-abc123"}},
            }
            for name, config in configs.items():
                (deploy / f"config_{name}.yaml").write_text(yaml.safe_dump(config))
            originals = {p: p.read_bytes() for p in deploy.glob("config_*.yaml")}
            with patch.object(f2, "FIRE", deploy.parent):
                result = f2.prepare("Rocket", "selfcheck.json", out)
            generated = yaml.safe_load((out / "config_runtime.yaml").read_text())
            self.assertEqual(generated["target_config"]["plusarg_passthrough"], "+user-setting=1")
            overrides = generated["run_farm"]["recipe_arg_overrides"]
            self.assertEqual(overrides["run_instance_market"], "spot")
            self.assertEqual(overrides["default_simulation_dir"], "/custom/runtime")
            self.assertEqual(yaml.safe_load((out / "config_build.yaml").read_text())["user_build_option"], "keep")
            self.assertEqual(yaml.safe_load((out / "config_build_recipes.yaml").read_text())[recipe_name]
                             ["bit_builder_arg_overrides"]["s3_bucket_name"], "user-configured-bucket")
            self.assertTrue(result["hwdb_ready"])
            self.assertEqual(set(result["manager_config_sources"]), set(configs))
            for source in result["manager_config_sources"].values():
                self.assertIn(Path(source["path"]), originals)
            self.assertEqual(originals, {p: p.read_bytes() for p in originals})

    def test_manager_environment_preserves_argv_and_exit_code(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fire = root / "sims/firesim"
            fire.mkdir(parents=True)
            (fire / "sourceme-manager.sh").write_text(
                '[[ "$1" == --skip-ssh-setup ]] || return 91\n'
                'export FIRESIM_SOURCED=1\n')
            (root / "work").mkdir()
            setup = root / "setup.sh"
            setup.write_text('export CHECKPOINT_TEST_SITE_SETUP="native manager"\n')
            output = []
            manager = f2.F2Manager(root, output.append)
            literal = 'literal `id` $HOME ; echo bad'
            with patch.dict(os.environ, {"CHECKPOINT_F2_SETUP": str(setup)}):
                code = manager.run(["bash", "-c", 'printf "%s\\n" "$PWD" "$FIRESIM_SOURCED" '
                                    '"$CHECKPOINT_TEST_SITE_SETUP" "$1"; exit 23', "test", literal], "work")
            self.assertEqual(code, 23)
            text = "".join(output)
            self.assertIn(str(root / "work"), text)
            self.assertIn("native manager", text)
            self.assertIn(literal, text)
            with self.assertRaises(ValueError):
                manager.command(["firesim"], "../outside")

    def test_preflight_is_read_only(self):
        with patch.object(f2.F2Manager, "run", return_value=0) as run:
            self.assertEqual(f2.F2Manager().preflight(), 0)
        argv, cwd = run.call_args.args
        script = argv[-1]
        self.assertIn("get-caller-identity", script)
        self.assertIn("describe-instance-types", script)
        for action in ("launchrunfarm", "buildbitstream", "managerinit", "run-instances"):
            self.assertNotIn(action, script)

    def test_known_vcs_invocations_are_rejected_on_the_manager(self):
        manager = f2.F2Manager()
        for argv in (["vcs", "-full64"], ["/path/to/simv"],
                     ["bash", "-c", "source automations/checkpoint_loop/vcs-env.sh && vcs -ID"],
                     ["python", "-m", "tools.checkpoint_formats.tests.verify_semantic_vcs"]):
            with self.subTest(argv=argv), self.assertRaisesRegex(ValueError, "backend eda"):
                manager.command(argv)

    def test_build_commands_reject_stale_ec2_configs_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            deploy = root / "sims/firesim/deploy"
            deploy.mkdir(parents=True)
            recipe = deploy / "farm.yaml"
            build = deploy / "config_build.yaml"
            build.write_text(yaml.safe_dump({"build_farm": {"base_recipe": "farm.yaml"}}))
            recipe.write_text(yaml.safe_dump({"build_farm_type": "AWSEC2", "args": {}}))
            manager = f2.F2Manager(root)
            with self.assertRaisesRegex(ValueError, "only localhost"):
                manager.command(["firesim", "buildbitstream"], "sims/firesim/deploy")
            recipe.write_text(yaml.safe_dump({"build_farm_type": "ExternallyProvisioned",
                                            "args": {"build_farm_hosts": ["localhost"],
                                                     "default_build_dir": str(root / "build")}}))
            command = manager.command(["firesim", "buildbitstream", "--buildconfigfile=" + str(build)],
                                      "sims/firesim/deploy")
            self.assertEqual(command[:2], ["bash", "-c"])
            # A remote externally-provisioned host is also outside this request.
            recipe.write_text(recipe.read_text().replace("localhost", "eda"))
            with self.assertRaisesRegex(ValueError, "only localhost"):
                manager.command(["firesim", "buildbitstream", "-b", str(build)], "sims/firesim/deploy")


if __name__ == "__main__":
    unittest.main()
