"""Independently reconcile composed native-region descriptors and global deficits."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from tools.checkpoint_formats.codec import canonical, require
from tools.checkpoint_formats.tests.audit_physical_clock_plan import arguments, parse_modules, audit_source
from tools.checkpoint_formats.tests.audit_physical_clock_dependencies import audit as audit_dependencies


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def inventory_from_firrtl(text, root):
    """Enumerate original storage, including emitter-owned memory pipelines."""
    modules = parse_modules(text)
    state = []
    def add(path, module, kind, width, depth, signed, clock, reset, adapter):
        state.append(dict(state_id=digest(dict(namespace="generated-simulator-state-v1", hierarchy=path, kind=kind)),
            hierarchy=path, module=module, kind=kind, width=width, depth=depth, signed=signed,
            clock_expression=clock, reset_expression=reset, adapter=adapter,
            bit_order="lsb0", address_order="ascending_zero_based"))
    def walk(module, path, ancestors=frozenset()):
        require(module not in ancestors, "recursive original execution")
        definition = modules[module]
        body = re.sub(r" @\[.*$", "", definition["body"], flags=re.M)
        if definition["kind"] == "extmodule":
            require(body.endswith("defname = BUFGCE"), "opaque original owner")
            add(path + ".O", module, "register", 1, 1, False, "posedge/negedge I", "none", "metasim-bufgce-v1")
            return
        registers = list(re.finditer(r"^  reg (\w+) : (UInt|SInt)<(\d+)>, (.*?) with :\n    reset => \((.*)\)$", body, re.M))
        require(len(registers) == len(re.findall(r"^  reg \w+ :", body, re.M)), "unparsed original register")
        for reg in registers:
            reset = arguments(reg[5])
            require(len(reset) == 2, "unsupported original reset")
            add(path + "." + reg[1], module, "register", int(reg[3]), 1, reg[2] == "SInt", reg[4], reset[0], "firrtl-register-v1")
        memories = list(re.finditer(r"^  mem (\w+) :\n((?:    [^\n]*\n?)*)", body, re.M))
        require(len(memories) == len(re.findall(r"^  mem \w+ :", body, re.M)), "unparsed original memory")
        for memory in memories:
            attrs = re.findall(r"^    ([\w-]+) => (.*)$", memory[2], re.M)
            fields = dict(attrs)
            data = re.fullmatch(r"(UInt|SInt)<(\d+)>", fields["data-type"])
            require(data is not None, "unsupported original memory type")
            width, depth = int(data[2]), int(fields["depth"])
            add(path + "." + memory[1], module, "memory", width, depth, data[1] == "SInt",
                "memory-port-clocks", "none", "firrtl-memory-v1")
            require(int(fields["read-latency"]) in (0, 1), "unsupported hidden memory pipeline")
            if int(fields["read-latency"]) == 1:
                for kind, port in attrs:
                    if kind not in ("reader", "readwriter"):
                        continue
                    field = "rdata" if kind == "readwriter" else "data" if fields["read-under-write"] == "old" else "addr"
                    size = (depth - 1).bit_length() if field == "addr" else width
                    add(path + "." + memory[1] + "_" + port + "_" + field, module, "register", size, 1,
                        field != "addr" and data[1] == "SInt", memory[1] + "." + port + ".clk", "none", "firrtl-emitter-memory-pipeline-v1")
        for instance, child in definition["instances"].items():
            walk(child, path + "." + instance, ancestors | {module})
    walk(root, root)
    require(len({r["state_id"] for r in state}) == len(state), "duplicate original storage")
    return sorted(state, key=lambda r: r["state_id"])


def audit(directory):
    directory = Path(directory)
    read = lambda n: json.loads((directory / n).read_text())
    manifest, binding, routing = map(read, ("manifest.json", "binding.json", "routing.json"))
    global_state, global_plan, dependencies = map(read, ("global-simulator-state.json",
        "global-clock-plan.json", "global-dependencies.json"))
    host_hash = hashlib.sha256((directory / "host.fir").read_bytes()).hexdigest()
    require(sorted(global_state["state"], key=lambda r: r["state_id"]) ==
        inventory_from_firrtl((directory / "host.fir").read_text(), global_state["root_module"]),
        "global inventory differs from complete original storage")
    audit_source(directory / "host.fir", directory / "global-simulator-state.json", directory / "global-clock-plan.json")
    audit_dependencies(directory / "host.fir", directory / "global-simulator-state.json",
        directory / "global-clock-plan.json", directory / "global-dependencies.json")
    source = read("source-input.json")
    require(hashlib.sha256(Path(source["path"]).read_bytes()).hexdigest() == source["sha256"],
        "changed original source input")
    require(binding["scope"] == "same_host_native_region_composition_only" and binding["binding_version"] == 1
        and manifest["scope"] == "selected_native_regions_only" and manifest["descriptor_version"] == 1
        and binding["host_sha256"] == host_hash and binding["manifest_sha256"] == digest(manifest)
        and manifest["routing"] == routing, "changed composition identity")
    flags = dict(complete_fpga_capture=False, deployable_capture_image=False,
        production_freeze_owners_bound=False, metasim_restore_supported=False)
    for doc in (manifest, binding):
        require(all(doc[k] is v for k, v in flags.items()), "changed hardware admission")
    require(routing["routing_version"] == 1 and routing["scope"] == "native_region_selector_routing_only"
        and routing["clock_contract"] == "shared_raw_clock_and_reset_all_endpoints"
        and routing["freeze_contract"] == "external_common_low_phase_all_owner_cut_required"
        and routing["complete_fpga_capture"] is False and routing["deployable_capture_image"] is False,
        "changed router clock/cut contract")
    rtl = Path("sims/firesim/sim/midas/src/main/verilog/CheckpointRegionStateRouter.sv")
    require(routing["router_sha256"] == hashlib.sha256(rtl.read_bytes()).hexdigest(), "changed compiled router")
    functional_global = {r["state_id"]: r for r in global_state["state"] if r["adapter"] != "metasim-bufgce-v1"}
    physical_global = {r["logical_latch_state_id"]: r for r in global_plan["physical_gates"]}
    all_global = functional_global.keys() | physical_global.keys()
    originals, scopes, allocations, physical_order = [], [], [], []
    bank_base = ce_base = 0
    for index, region in enumerate(binding["regions"]):
        doc, pin = region["manifest"], region["binding"]
        require(digest(doc) == region["manifest_sha256"] and digest(pin) == region["binding_sha256"], "changed region digest")
        require(pin["manifest_sha256"] == digest(doc), "region binding differs from its manifest")
        require(doc["scope"] == "selected_inplace_global_identities_only" and pin["host_sha256"] == host_hash,
            "different original host")
        require(pin["global_simulator_manifest_sha256"] == digest(global_state) and
            pin["global_clock_plan_sha256"] == digest(global_plan) and
            pin["global_dependencies_sha256"] == digest(dependencies), "changed global cut/inventory binding")
        require(all(doc[k] is v and pin[k] is v for k, v in flags.items()), "changed region admission")
        scope = doc["selected_scope"]
        require(all(not (scope == s or scope.startswith(s + ".") or s.startswith(scope + ".")) for s in scopes),
            "overlapping concrete regions")
        scopes.append(scope)
        functional = [r for r in doc["state"] if r["domain"] == "functional"]
        physical = [r for r in doc["state"] if r["domain"] == "physical_ce"]
        require(len(functional) + len(physical) == len(doc["state"]) and functional, "unknown/empty region")
        banks = sorted({r["bank"] for r in functional})
        require(banks == list(range(banks[-1] + 1)) and banks[-1] < 255, "sparse/reserved functional banks")
        require([r["slot"] for r in physical] == list(range(len(physical))), "noncanonical CE slots")
        allocations.append(dict(index=index, bank_base=bank_base, bank_count=len(banks), ce_base=ce_base, ce_count=len(physical)))
        physical_order.append(dict(selected_scope=scope, base=ce_base, count=len(physical)))
        for row in doc["state"]:
            is_ce = row["domain"] == "physical_ce"
            require(row["state_id"] in all_global and row["hierarchy"].startswith(scope + "."), "owner outside selected execution")
            if is_ce:
                primitive = physical_global[row["state_id"]]
                require(row["hierarchy"] == primitive["logical_latch_hierarchy"] and row["bank"] == 255
                    and row["ce_bit"] == row["slot"] and row["width"] == row["depth"] == 1,
                    "changed physical owner")
            else:
                require(row["logical_state"] == functional_global[row["state_id"]], "changed functional owner")
            expected = dict(row, region=index, local_bank=row["bank"], local_slot=row["slot"], local_ordinal=row["ordinal"])
            if is_ce:
                expected.update(slot=row["slot"] + ce_base, local_ce_bit=row["ce_bit"], ce_bit=row["ce_bit"] + ce_base)
            else:
                expected["bank"] += bank_base
            originals.append(expected)
        bank_base += len(banks)
        ce_base += len(physical)
    require(bank_base <= 255 and ce_base <= 65535 and len(originals) <= 65535, "ABI overflow")
    require(routing["regions"] == allocations and manifest["physical_ce_order"] == physical_order, "changed routing/CE order")
    ordered = [r for r in originals if r["domain"] == "functional"] + [r for r in originals if r["domain"] == "physical_ce"]
    expected = [dict(r, ordinal=i) for i, r in enumerate(ordered)]
    require(manifest["state"] == expected, "changed global/local ordinal, selectors or sample bits")
    covered = {r["state_id"] for r in expected}
    require(len(covered) == len(expected) and len({(r["bank"], r["slot"]) for r in expected}) == len(expected),
        "overlapping state or selectors")
    require(manifest["uncovered_functional_state"] == [r for k, r in functional_global.items() if k not in covered]
        and manifest["uncovered_physical_gates"] == [r for k, r in physical_global.items() if k not in covered],
        "lost or fabricated global deficits")
    def packed(width, values):
        return str(width * len(values)) + "'h" + "".join(format(v, "0" + str(width // 4) + "x") for v in reversed(values))
    parameters = ".REGIONS(" + str(len(allocations)) + "), " + ", ".join("." + key + "(" + packed(width,
        [a[field] for a in allocations]) + ")" for key, width, field in (
            ("BANK_BASE", 8, "bank_base"), ("BANK_COUNT", 8, "bank_count"),
            ("CE_BASE", 16, "ce_base"), ("CE_COUNT", 16, "ce_count")))
    require((directory / "parameters.svh").read_text() == parameters, "different synthesized routing parameters")
    return dict(status="pass", scope="structural region composition only; no global cut or hardware capture",
        regions=len(allocations), entries=len(expected), physical_ce=ce_base,
        remaining_functional_entries=len(manifest["uncovered_functional_state"]),
        remaining_functional_words=sum(((r["width"] + 63) // 64) * r["depth"] for r in manifest["uncovered_functional_state"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generated", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.generated), indent=2))
