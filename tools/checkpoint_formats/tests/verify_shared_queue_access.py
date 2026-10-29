"""Native localhost synthesis and fresh EDA VCS of concrete shared queue banks.

These fixtures prove readout and sibling isolation only. No FPGA checkpoint,
complete owner freeze, restoration or target-cycle authority is established.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile

from tools.checkpoint_formats import toolchain
from tools.checkpoint_formats.codec import FormatError, canonical, require
from tools.checkpoint_formats.tests.audit_checkpoint_regions import inventory_from_firrtl
from tools.checkpoint_formats.tests.audit_physical_clock_plan import arguments, parse_modules

ROOT = Path(__file__).resolve().parents[3]
RUNS = ROOT / "automations/checkpoint_loop/runs"
SOURCES = tuple(sorted({
    str(p.relative_to(ROOT))
    for p in (ROOT / "sims/firesim/sim/midas/src/main/scala/midas/checkpoint").glob("*.scala")
} | {
    "sims/firesim/sim/midas/src/main/scala/midas/widgets/CheckpointCaptureDescriptors.scala",
    "sims/firesim/sim/midas/src/test/scala/midas/checkpoint/NativeCheckpointSharedQueueSpec.scala",
    "sims/firesim/sim/midas/src/test/resources/checkpoint/SharedQueue.firrtl",
    "tools/checkpoint_formats/tests/verify_shared_queue_access.py",
    "tools/checkpoint_formats/tests/shared_queue_access_tb.sv",
    "tools/checkpoint_formats/tests/checkpoint_widget_exit.cc",
    "tools/checkpoint_formats/tests/audit_checkpoint_regions.py",
    "tools/checkpoint_formats/tests/audit_physical_clock_plan.py",
    "tools/checkpoint_formats/codec.py", "tools/checkpoint_formats/toolchain.py",
}))
FLAGS = ("complete_fpga_capture", "deployable_capture_image",
         "production_freeze_owners_bound", "metasim_restore_supported")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(doc):
    return hashlib.sha256(canonical(doc)).hexdigest()


def canonical_json(path):
    data = Path(path).read_bytes()
    doc = json.loads(data)
    require(data == canonical(doc), "noncanonical queue metadata " + Path(path).name)
    return doc


def memory_shape(body):
    # Real Rocket declarations retain FIRRTL source locations. They do not
    # change storage shape; the independent inventory applies the same rule.
    body = re.sub(r" @\[.*$", "", body, flags=re.M)
    memories = {}
    for mem in re.finditer(r"^  mem (\w+) :\n((?:    [^\n]*\n?)*)", body, re.M):
        attrs = re.findall(r"^    ([\w-]+) => (.*)$", mem[2], re.M)
        require(len(attrs) == len(set(k for k, _ in attrs)), "duplicate native memory attribute")
        memories[mem[1]] = dict(attrs)
    return memories


def observation_audit(instrumented, bank):
    """Reconstruct all added state from FIRRTL, including implicit RAM data.

    Use the independent emitter inventory, never an enumerated subset supplied
    by the generator. The packed output itself must read those exact owners.
    """
    text = Path(instrumented).read_text()
    modules = parse_modules(text)
    require(len(modules) == 1, "native observation requires one local module")
    root, module = next(iter(modules.items()))
    original = {r["storage_hierarchy"] for r in bank["state"]}
    inventory = inventory_from_firrtl(text, root)
    require(original <= {r["hierarchy"] for r in inventory}, "original banked state disappeared")
    derived = sorted((r for r in inventory if r["hierarchy"] not in original), key=lambda r: r["hierarchy"])
    memories = memory_shape(module["body"])
    implicit = {f"{name}_{shape['reader']}_data": f"{name}.{shape['reader']}.data"
                for name, shape in memories.items()}
    fields, offset = [], 0
    for row in derived:
        name = row["hierarchy"].removeprefix(root + ".")
        require(row["kind"] == "register" and row["depth"] == 1, "unknown derived state shape")
        if row["adapter"] == "firrtl-emitter-memory-pipeline-v1":
            require(name in implicit, "unknown implicit data pipeline")
            expression = implicit[name]
        else:
            require(name.startswith(("ckpt_", "CheckpointNative")), "unknown derived register")
            expression = name
        fields.append(dict(instrumented_state_id=row["state_id"], hierarchy=row["hierarchy"],
            expression=expression, width=row["width"], offset=offset, signed=row["signed"],
            clock_expression=row["clock_expression"], adapter=row["adapter"]))
        offset += row["width"]
    expected = dict(observation_version=1, scope="derived_native_state_live_vector_only", port="ckpt_native_state",
        bits=offset, words=(offset + 63) // 64, bit_order="lsb0", state=fields, original_banked_entries=len(original),
        includes_implicit_ram_data_pipeline=True,
        sampling_contract="sample_entire_live_vector_at_one_common_raw_clock_cut",
        stable_while_functional_freeze=False, atomic_snapshot_supported=False,
        complete_capture_owner=False, metasim_restore_supported=False)
    require(bank.get("native_state_observation") == expected, "changed complete native observation layout/owner contract")
    expressions = [f"asUInt({r['expression']})" if r["signed"] else r["expression"] for r in reversed(fields)]
    expression = expressions[0]
    for value in expressions[1:]:
        expression = f"cat({expression}, {value})"
    require(module["drivers"].get("ckpt_native_state") == expression,
            "changed native observation equation or bit order")
    require(re.search(r"^  output ckpt_native_state : UInt<" + str(offset) + r">$", module["body"], re.M),
            "changed native observation output width/direction")
    return expected


def emitted_observation(directory, q, bank):
    """Bind the logical FIRRTL owners to this exact emitted storage layout.

    SemanticCleanEmitter runs memory-delay lowering. Its Old read is an
    explicit data_pipe_0 register; the similarly named data net is asynchronous.
    Require the actual declaration, sole sampling equation and clock. Never use
    the data wire or guess a path from a logical inventory entry alone.
    """
    layout = observation_audit(Path(directory) / f"shell-{q}-banked.fir", bank)
    text = (Path(directory) / "generated.sv").read_text()
    name = f"checkpoint_shell_region{q}_selected_SharedQueue"
    match = re.search(r"(?m)^module " + name + r"\([\s\S]*?^endmodule\b", text)
    require(match is not None, "missing actual emitted queue definition")
    body = match[0]
    declarations = re.findall(r"\breg\s+(?:\[(\d+):0\]\s+)?(\w+)\s*;", body)
    registers = {n: int(w) + 1 if w else 1 for w, n in declarations if not n.startswith("_RAND_")}
    require(len(registers) == sum(not n.startswith("_RAND_") for _, n in declarations),
            "duplicate emitted observation register")
    fields = []
    for row in layout["state"]:
        logical = row["hierarchy"].rsplit(".", 1)[1]
        actual = f"checkpoint_shell_region{q}_" + logical if logical.startswith("ckpt_") else logical
        if row["adapter"] == "firrtl-emitter-memory-pipeline-v1":
            actual = logical + "_pipe_0"
            equations = list(re.finditer(r"(?m)^\s+" + re.escape(actual) + r" <= ([^;]+);$", body))
            require(len(equations) == 1 and equations[0][1] == logical,
                    "changed emitted Old data pipeline sampling equation")
            clocks = list(re.finditer(r"always @\(([^)]+)\) begin", body[:equations[0].start()]))
            require(clocks and clocks[-1][1] == "posedge clock", "changed emitted Old data pipeline clock")
        require(registers.get(actual) == row["width"], "missing or reshaped actual emitted observation register")
        fields.append(dict(row, emitted_register=actual))
    original = {r["storage_hierarchy"].rsplit(".", 1)[1] for r in bank["state"] if r["depth"] == 1}
    require(registers.keys() == original | {r["emitted_register"] for r in fields},
            "unowned additional emitted queue register")
    return dict(emission_policy="verilog_memory_delay_lowered_old_data_one_stage",
        module=name, generated_sv_sha256=sha(Path(directory) / "generated.sv"), state=fields)


def bank_audit(directory, q, shell, mapping):
    bank = canonical_json(directory / f"shell-{q}-banks-binding.json")
    reference = directory / f"shell-{q}-reference.fir"
    instrumented = directory / f"shell-{q}-banked.fir"
    require(shell["banks_binding_sha256"] == digest(bank), "unbound underlying queue bank policy")
    require(shell["reference_sha256"] == bank["reference_sha256"] == sha(reference)
            and bank["instrumented_sha256"] == sha(instrumented), "changed underlying bank circuit hash")
    local_manifest = canonical_json(directory / f"shell-{q}-manifest.json")
    require(bank["manifest_sha256"] == digest(local_manifest), "unbound local queue bank manifest")
    expected_policy = dict(adapter_version=2, original_ram_ports_retained=True,
        access_clock_contract="same_running_original_raw_clock", response_latency_edges=3,
        original_reader_reprimed_before_response=True, cancel_reprime_before_ready=True,
        public_reader_shadowed=True, memories=["ram"], native_read_under_write="old",
        original_read_under_write="new", write_first_forwarding="registered_hit_and_data_at_original_ram_edge",
        derived_readout_state_complete_capture_owner=False)
    require(bank.get("synchronous_memory_readout") == expected_policy,
            "changed synchronous queue policy/latency/port contract")
    require(bank["access_clock"] == "ckpt_clock" and bank["functional_clock_domains"] ==
            [dict(clock_hierarchy="SharedQueue.clock", root_clock="clock")],
            "changed native queue access or functional clock contract")
    require(bank["freeze_contract"] == "externally_held_all_functional_owners_before_access_until_drain",
            "changed native queue hold contract")
    modules = parse_modules(instrumented.read_text());refs = parse_modules(reference.read_text())
    require(set(modules) == set(refs) == {"SharedQueue"}, "changed local queue bank topology")
    module = modules["SharedQueue"]
    observation = observation_audit(instrumented, bank)
    emitted_observation(directory, q, bank)
    require(len(observation["state"]) == 14 and observation["bits"] == 518,
            "incomplete derived native queue observation")
    shape = memory_shape(module["body"])
    require(shape == {"ram": {"data-type": "UInt<130>", "depth": "6", "read-latency": "1",
        "write-latency": "1", "reader": "r", "writer": "w", "read-under-write": "old"}},
        "changed actual native queue memory shape or ports")
    reference_shape = memory_shape(refs["SharedQueue"]["body"])
    require(reference_shape == {"ram": dict(shape["ram"], **{"read-under-write": "new"})},
            "native Old RAM must retain the exact original New reference shape")
    final = parse_modules((directory / "generated.fir").read_text())
    selected = final[f"checkpoint_shell_region{q}_selected_SharedQueue"]
    require(shape == memory_shape(selected["body"]), "installed queue RAM differs from exported native bank")
    endpoint = {"ckpt_native_phase", "ckpt_native_bank", "ckpt_native_slot", "ckpt_native_address",
                "ckpt_native_active", "ckpt_native_request"}
    consumers = {name: clock for name, kind, clock in module["consumers"] if kind == "register"}
    require(endpoint <= consumers.keys() and all(consumers[n] == "ckpt_clock" for n in endpoint),
            "changed actual native queue endpoint clocks")
    require(consumers.get("CheckpointNativeHold_ram") == "clock" and
            consumers.get("CheckpointNativeBorrowed") == "clock", "changed native RAM shadow clock")
    forwarding = {"CheckpointNativeForwardHit_ram": "UInt<1>", "CheckpointNativeForwardData_ram": "UInt<130>"}
    for name, width in forwarding.items():
        require(consumers.get(name) == "clock" and re.search(
            r"^  reg " + re.escape(name) + r" : " + re.escape(width) + r", clock(?: with :)?$",
            module["body"], re.M) is not None, "changed native registered write-first forwarding state")
    def unalias(value, seen=frozenset()):
        require(value not in seen, "native queue enable alias cycle")
        if value in module["aliases"]:
            return unalias(module["drivers"][value], seen | {value})
        if value.startswith("mux("):
            args = arguments(value[4:-1])
            if args[1:] == ['UInt<1>("h1")', 'UInt<1>("h0")']:
                return unalias(args[0], seen | {value})
        return value
    def root_clock(value, enable, seen=frozenset()):
        require(value not in seen, "native queue memory clock alias cycle")
        if value == "clock": return value
        if value in module["aliases"]:
            return root_clock(module["drivers"][value], enable, seen | {value})
        if value.startswith("validif("):
            args = arguments(value[8:-1])
            require(len(args) == 2 and unalias(args[0]) == unalias(enable), "native RAM clock guard mismatch")
            return root_clock(args[1], enable, seen | {value})
        require(False, "changed actual native queue memory clock")
    writer_enable = module["drivers"]["ram.w.en"]
    require(writer_enable.startswith("and("), "native writer lacks hold gating")
    writer_args = arguments(writer_enable[4:-1])
    require(len(writer_args) == 2 and writer_args[1] == "not(ckpt_freeze)"
            and writer_args[0] == refs["SharedQueue"]["drivers"]["ram.w.en"],
            "changed exact native queue writer freeze gating")
    require(selected["drivers"]["ram.w.en"] == writer_enable.replace(
        "ckpt_freeze", f"checkpoint_shell_region{q}_ckpt_freeze"), "changed installed writer freeze gating")
    require(module["drivers"]["ram.r.en"] == 'UInt<1>("h1")', "native reader must remain always enabled")
    for port, enable in (("r", module["drivers"]["ram.r.en"]), ("w", writer_args[0])):
        # The writer's exact extra hold gate was checked above. Its original
        # validif guard belongs to its original enable, before that hold gate.
        require(root_clock(module["drivers"][f"ram.{port}.clk"], enable) == "clock",
                "changed native RAM original clock")
    drivers = module["drivers"]
    hit = f"and(and({drivers['ram.w.en']}, {drivers['ram.w.mask']}), eq({drivers['ram.r.addr']}, {drivers['ram.w.addr']}))"
    functional = "mux(CheckpointNativeForwardHit_ram, CheckpointNativeForwardData_ram, ram.r.data)"
    public = f"mux(CheckpointNativeBorrowed, CheckpointNativeHold_ram, {functional})"
    require(drivers["CheckpointNativeForwardHit_ram"] == hit and
            drivers["CheckpointNativeForwardData_ram"] == drivers["ram.w.data"],
            "changed registered same-edge write-first hit or full-width data")
    require(drivers["deq_bits"] == public and drivers["CheckpointNativeHold_ram"] == public,
            "public/held native RAM output omits registered write-first forwarding")
    # The separately reconstructed observation port deliberately contains the
    # forwarding state. Original checkpoint RAM payloads still use raw data.
    bank_data = [value for name, value in drivers.items()
                 if name.startswith("ckpt_") and name != observation["port"] and value is not None]
    require(any("ram.r.data" in value for value in bank_data)
            and all("CheckpointNativeForward" not in value for value in bank_data),
            "checkpoint RAM payload must use raw native read data")
    for name in ("CheckpointNativeForwardHit_ram", "CheckpointNativeForwardData_ram", "CheckpointNativeHold_ram", "deq_bits"):
        installed = re.sub(r"\bckpt_\w+", lambda m: f"checkpoint_shell_region{q}_" + m[0], drivers[name])
        require(selected["drivers"].get(name) == installed,
                "installed queue differs from registered write-first bank equations")
    local_rows = {r["state_id"]: r for r in bank["state"]}
    require(len(local_rows) == len(mapping["state"]) == 5, "changed underlying bank local owners")
    for row in mapping["state"]:
        local = local_rows.get(row["local_state_id"])
        require(local is not None and all(local[k] == row[k] for k in ("bank", "slot", "width", "depth"))
                and local["storage_hierarchy"] == "SharedQueue." + row["storage_hierarchy"].rsplit(".", 1)[1]
                and local.get("transfer_width", local["width"]) == row["transfer_width"]
                and local.get("transfer_depth", local["depth"]) == row["transfer_depth"],
                "changed underlying bank local state mapping")
    return bank


def audit(directory):
    directory = Path(directory)
    read = lambda name: canonical_json(directory / name)
    source = (directory / "source.fir").read_text()
    before = parse_modules(source)
    after = parse_modules((directory / "generated.fir").read_text())
    original = inventory_from_firrtl(source, "SharedQueueHost")
    expected = {row["state_id"]: row for row in original
                if row["hierarchy"].split(".")[1] in ("q0", "q1")}
    require(len(expected) == 10, "different independent shared queue inventory")
    require(before["SharedQueueHost"]["instances"] ==
            dict(gate="Native", q0="SharedQueue", q1="SharedQueue", q2="SharedQueue"), "different original queue topology")
    require(after["SharedQueue"]["body"] == before["SharedQueue"]["body"], "changed unselected original queue")
    require(after["SharedQueueHost"]["instances"] == dict(
        gate="Native", q0="checkpoint_shell_region0_selected_SharedQueue",
        q1="checkpoint_shell_region1_selected_SharedQueue", q2="SharedQueue"), "crossed or lost concrete queue copy")
    require(after["Native"] == before["Native"], "changed uncovered physical clock owner")
    manifest, binding, identities = map(read, ("descriptors.json", "binding.json", "descriptor-binding.json"))
    require(binding["host_sha256"] == sha(directory / "source.fir")
            and binding["instrumented_sha256"] == sha(directory / "generated.fir")
            and binding["descriptor_manifest_sha256"] == digest(manifest)
            and binding["descriptor_binding_sha256"] == digest(identities), "unbound shared queue source/output")
    require(identities["manifest_sha256"] == digest(manifest), "changed descriptor identity")
    for doc in (manifest, binding, identities):
        require(all(doc[k] is False for k in FLAGS), "shared queue readout claims hardware admission")
    rows = manifest["state"]
    require(len(rows) == 10 and {r["state_id"] for r in rows} == set(expected), "omitted/duplicated selected queue owner")
    require(len({(r["bank"], r["slot"]) for r in rows}) == 10, "aliased shared queue selector")
    for row in rows:
        logical = expected[row["state_id"]]
        q = int(logical["hierarchy"].split(".")[1][1:])
        require(row["logical_state"] == logical and row["hierarchy"] == logical["hierarchy"]
                and row["region"] == q, "changed original queue identity or shape")
        require(row["width"] == min(64, logical["width"])
                and row["depth"] == ((logical["width"] + 63) // 64) * logical["depth"], "truncated multiword queue RAM")
    uncovered = [r for r in original if r["hierarchy"].startswith("SharedQueueHost.q2.")]
    require(sorted(manifest["uncovered_functional_state"], key=lambda r: r["state_id"]) == uncovered,
            "lost unselected queue ownership deficit")
    require(len(manifest["uncovered_physical_gates"]) == 1 and sum(r["count"] for r in manifest["physical_ce_order"]) == 0,
            "readout cannot certify physical clock ownership")
    physical = manifest["uncovered_physical_gates"][0]
    physical_path = "SharedQueueHost.gate.CE_latch"
    require(physical["hierarchy"] == "SharedQueueHost.gate"
            and physical["logical_latch_hierarchy"] == physical_path
            and physical["logical_latch_state_id"] == digest(dict(
                namespace="physical-bufgce-ce-latch-v1", hierarchy=physical_path)),
            "changed uncovered physical owner")
    for q in range(2):
        mapping = read(f"shell-{q}-mapping.json")
        shell = read(f"shell-{q}-binding.json")
        bank_audit(directory, q, shell, mapping)
        require(mapping["selected_execution"] == f"SharedQueueHost.q{q}" and len(mapping["state"]) == 5,
                "wrong shell execution")
        require(shell["mapping_sha256"] == digest(mapping) and shell["host_sha256"] == sha(directory / "source.fir"),
                "unbound shell mapping")
        require(shell["annotation_policy"]["translation_results_applied"] is True
                and shell["annotation_policy"]["preservation"] == "concrete_execution_translation", "missing shared owner translation")
        region = identities["regions"][q]
        require(region["manifest_sha256"] == digest(region["manifest"])
                and region["binding_sha256"] == digest(region["binding"])
                and region["binding"]["manifest_sha256"] == digest(region["manifest"]), "changed region identity envelope")
        region_rows = {r["state_id"]: r for r in region["manifest"]["state"]}
        require(len(region_rows) == 5 and region["manifest"]["selected_scope"] == f"SharedQueueHost.q{q}",
                "different region identity execution")
        require(region["binding"]["shell_binding_sha256"] == digest(shell), "unbound shared shell identity")
        expected_ids = {state_id for state_id, row in expected.items()
                        if row["hierarchy"].startswith(f"SharedQueueHost.q{q}.")}
        require({m["state_id"] for m in mapping["state"]} == expected_ids
                and len({m["state_id"] for m in mapping["state"]}) == 5,
                "omitted or duplicate concrete shell mapping")
        require(sum(m["transfer_depth"] for m in mapping["state"]) == 22, "incomplete shell transfer words")
        for m in mapping["state"]:
            logical = expected.get(m["state_id"])
            require(logical is not None and logical["hierarchy"] == m["hierarchy"], "crossed shell owner")
            descriptor = next(row for row in rows if row["state_id"] == m["state_id"])
            local = region_rows.get(m["state_id"])
            require(local is not None and local["logical_state"] == logical
                    and local["bank"] == m["bank"] and local["slot"] == m["slot"]
                    and local["width"] == m["transfer_width"] and local["depth"] == m["transfer_depth"]
                    and local["storage_hierarchy"] == m["storage_hierarchy"], "changed embedded local mapping")
            require(all(m[k] == logical[k] for k in ("width", "depth", "kind"))
                    and m["transfer_width"] == descriptor["width"]
                    and m["transfer_depth"] == descriptor["depth"]
                    and m["bank"] == descriptor["local_bank"]
                    and m["slot"] == descriptor["local_slot"], "changed shell selector or transfer geometry")
            suffix = m["hierarchy"].rsplit(".", 1)[1]
            storage = "CheckpointPipeline_ram_r_addr" if suffix == "ram_r_addr" else suffix
            require(m["storage_hierarchy"] == f"SharedQueueHost.q{q}." + storage, "crossed queue pipeline storage")
    xdc = (directory / "generated.synthesis.xdc").read_text()
    commands = [line for line in xdc.splitlines() if line and not line.startswith("#")]
    require(commands == [f"set_property RAM_STYLE BLOCK [get_cells -hierarchical -regexp .*q{q}/ram_reg.*]"
                         for q in range(3)], "changed concrete original RAM-style policy")
    return rows


def selectors(directory):
    mapping = json.loads((Path(directory) / "shell-0-mapping.json").read_text())
    memory = next(row for row in mapping["state"] if row["hierarchy"].endswith(".ram"))
    lines = [f"localparam integer QUEUE0_RAM_BANK={memory['bank']};",
             f"localparam integer QUEUE0_RAM_SLOT={memory['slot']};", "task allwords;", "begin"]
    for q in range(2):
        mapping = json.loads((Path(directory) / f"shell-{q}-mapping.json").read_text())
        for row in mapping["state"]:
            suffix = row["hierarchy"].rsplit(".", 1)[1]
            if suffix == "ram":
                values = [f"64'(memory[{q}][{i // 3}] >> {64 * (i % 3)})" for i in range(18)]
            else:
                key = {"enq_ptr": "wp", "deq_ptr": "rp", "full": "full", "ram_r_addr": "ra"}[suffix]
                values = [f"64'({key}[{q}])"]
            require(len(values) == row["transfer_depth"], "incomplete independent queue oracle")
            lines.extend(f"readword({q},{row['bank']},{row['slot']},{a},{value},0);" for a, value in enumerate(values))
    lines.extend(["end", "endtask", "task check_native_observation;", "begin"])
    for q in range(2):
        bank = canonical_json(Path(directory) / f"shell-{q}-banks-binding.json")
        layout = emitted_observation(directory, q, bank)
        for row in layout["state"]:
            # The emitted physical data register name differs from its FIRRTL
            # memory port expression. All other names retain their declarations.
            name = row["emitted_register"]
            lines.append(f'check(native_state[{q}][{row["offset"]} +: {row["width"]}] === '
                         f'dut.host.q{q}.{name}, "native observation q{q} {name}");')
        lines.append("native_observation_checks += 14;")
    return "\n".join(lines + ["end", "endtask", ""])


def synthesis_wrapper(generated):
    # The actual region graft consumes only the registered endpoint and ties
    # access clocks to the common raw clock. Raw combinational bank probes are
    # internal wires, not additional externally observed memory read ports.
    text = (Path(generated) / "generated.sv").read_text()
    match = re.search(r"module SharedQueueHost\((.*?)\n\);", text, re.S)
    require(match is not None, "missing queue host interface")
    pins = []
    connections = []
    for line in match[1].splitlines():
        if not line.strip(): continue
        pin = re.fullmatch(r"\s*(input|output)\s*(\[\d+:\d+\])?\s*(\w+),?", line)
        require(pin is not None, "unknown generated queue host port")
        name = pin[3]
        if name.endswith("_ckpt_clock"):
            connections.append(f".{name}(clock)")
        elif name.endswith(("_ckpt_data", "_ckpt_match")):
            require(pin[1] == "output", "raw probe must be output only")
            connections.append(f".{name}()")
        else:
            pins.append(f"  {pin[1]} wire {pin[2] or ''} {name}")
            connections.append(f".{name}({name})")
    require(len(connections) == 53 and len(pins) == 47, "changed queue endpoint boundary")
    return "module SharedQueueSynthesisTop(\n" + ",\n".join(pins) + ");\n" + \
        "  SharedQueueHost host(\n    " + ",\n    ".join(connections) + ");\nendmodule\n"


def negative_audits(generated, out):
    results = []
    for case in ("omitted", "duplicate", "shape", "pipeline", "selector", "duplicate_mapping", "sibling", "false_admission",
                 "bank_policy", "bank_hash", "bank_latency", "bank_port", "noncanonical",
                 "observation_omitted", "observation_pipeline", "observation_offset", "observation_width",
                 "observation_clock", "observation_capture", "observation_restore", "observation_equation",
                 "observation_emitted_register", "observation_emitted_equation", "observation_emitted_clock"):
        directory = out / case
        shutil.copytree(generated, directory)
        manifest = json.loads((directory / "descriptors.json").read_text())
        binding = json.loads((directory / "binding.json").read_text())
        identities = json.loads((directory / "descriptor-binding.json").read_text())
        if case == "omitted": manifest["state"].pop()
        elif case == "duplicate": manifest["state"][-1] = manifest["state"][0]
        elif case == "shape": next(r for r in manifest["state"] if r["logical_state"]["kind"] == "memory")["depth"] = 6
        elif case in ("pipeline", "selector", "duplicate_mapping"):
            p = directory / "shell-0-mapping.json"
            mapping = json.loads(p.read_text())
            if case == "pipeline":
                next(r for r in mapping["state"] if r["hierarchy"].endswith(".ram_r_addr"))["storage_hierarchy"] = "SharedQueueHost.q1.enq_ptr"
            elif case == "selector": mapping["state"][0]["slot"] += 1
            else: mapping["state"][-1] = dict(mapping["state"][0])
            p.write_bytes(canonical(mapping))
            p = directory / "shell-0-binding.json"
            shell = json.loads(p.read_text());shell["mapping_sha256"] = digest(mapping);p.write_bytes(canonical(shell))
            identities["regions"][0]["binding"]["shell_binding_sha256"] = digest(shell)
            identities["regions"][0]["binding_sha256"] = digest(identities["regions"][0]["binding"])
        elif case == "sibling":
            p = directory / "generated.fir"
            text = p.read_text();require(text.count("module SharedQueue :") == 1, "ambiguous sibling fault")
            start = text.index("  module SharedQueue :")
            end = text.index("\n  module ", start + 1)
            body = text[start:end]
            needle = "node enq = and(enq_ready, enq_valid)"
            require(body.count(needle) == 1, "ambiguous original sibling enqueue")
            text = text[:start] + body.replace(needle, 'node enq = UInt<1>("h0")') + text[end:]
            p.write_text(text);binding["instrumented_sha256"] = sha(p)
        elif case == "false_admission": manifest["complete_fpga_capture"] = True
        elif case.startswith("bank_"):
            bp = directory / "shell-0-banks-binding.json"
            bank = json.loads(bp.read_text())
            if case == "bank_policy": bank["synchronous_memory_readout"]["access_clock_contract"] = "foreign_clock"
            elif case == "bank_hash": bank["instrumented_sha256"] = "0" * 64
            elif case == "bank_latency": bank["synchronous_memory_readout"]["response_latency_edges"] = 1
            else:
                fir = directory / "shell-0-banked.fir"
                text = fir.read_text()
                require(text.count("reader => r") == 1, "ambiguous native reader port negative")
                text = text.replace("reader => r", "reader => r\n      reader => extra")
                text += '    ram.extra.clk <= clock\n    ram.extra.en <= UInt<1>("h1")\n    ram.extra.addr <= UInt<3>("h0")\n'
                fir.write_text(text);bank["instrumented_sha256"] = sha(fir)
            bp.write_bytes(canonical(bank))
        elif case.startswith("observation_emitted_"):
            sv = directory / "generated.sv"
            text = sv.read_text()
            module = re.search(r"(?m)^module checkpoint_shell_region0_selected_SharedQueue\([\s\S]*?^endmodule\b", text)
            require(module is not None, "missing emitted mutation owner")
            needle, replacement = {
                "observation_emitted_register": ("reg [129:0] ram_r_data_pipe_0;", "wire [129:0] ram_r_data_pipe_0;"),
                "observation_emitted_equation": ("ram_r_data_pipe_0 <= ram_r_data;", "ram_r_data_pipe_0 <= 130'h0;"),
                "observation_emitted_clock": ("always @(posedge clock) begin", "always @(negedge clock) begin"),
            }[case]
            require(module[0].count(needle) == 1, "ambiguous emitted mutation site")
            sv.write_text(text[:module.start()] + module[0].replace(needle, replacement) + text[module.end():])
        elif case.startswith("observation_"):
            bp = directory / "shell-0-banks-binding.json"
            bank = json.loads(bp.read_text())
            observation = bank["native_state_observation"]
            if case == "observation_omitted": observation["state"].pop()
            elif case == "observation_pipeline":
                next(r for r in observation["state"] if r["expression"] == "ram.r.data")["expression"] = "ram.w.data"
            elif case == "observation_offset": observation["state"][-1]["offset"] = 0
            elif case == "observation_width": observation["state"][-1]["width"] = 1
            elif case == "observation_clock": observation["state"][0]["clock_expression"] = "foreign_clock"
            elif case == "observation_capture": observation["complete_capture_owner"] = True
            elif case == "observation_restore": observation["metasim_restore_supported"] = True
            else:
                fir = directory / "shell-0-banked.fir"
                text = fir.read_text()
                text, count = re.subn(r"^    ckpt_native_state <= .*$", '    ckpt_native_state <= UInt<518>("h0")', text, flags=re.M)
                require(count == 1, "ambiguous native observation equation corruption")
                fir.write_text(text);bank["instrumented_sha256"] = sha(fir)
            bp.write_bytes(canonical(bank))
        # Rebind every enclosing metadata envelope, so policy/hash/port and
        # original semantic negatives cannot pass by tripping a stale checksum.
        for q in range(2):
            sp = directory / f"shell-{q}-binding.json"
            shell = json.loads(sp.read_text())
            shell["banks_binding_sha256"] = sha(directory / f"shell-{q}-banks-binding.json")
            sp.write_bytes(canonical(shell))
            identities["regions"][q]["binding"]["shell_binding_sha256"] = digest(shell)
            identities["regions"][q]["binding_sha256"] = digest(identities["regions"][q]["binding"])
        (directory / "descriptors.json").write_bytes(canonical(manifest))
        identities["manifest_sha256"] = digest(manifest)
        (directory / "descriptor-binding.json").write_bytes(canonical(identities))
        binding["descriptor_manifest_sha256"] = digest(manifest);binding["descriptor_binding_sha256"] = digest(identities)
        (directory / "binding.json").write_bytes(canonical(binding))
        if case == "noncanonical":
            p = directory / "shell-0-banks-binding.json"
            p.write_text(json.dumps(json.loads(p.read_text()), indent=2) + "\n")
        try: audit(directory)
        except FormatError as error: results.append(dict(case=case, rejected=True, reason=str(error)))
        else: raise FormatError("coherently rehashed queue metadata corruption accepted: " + case)
    (out / "summary.json").write_text(json.dumps(results, indent=2) + "\n")
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("vivado", "vcs"), required=True)
    parser.add_argument("--generated", type=Path);parser.add_argument("--native", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args();require(args.out.resolve().is_relative_to(RUNS), "evidence beneath runs required")
    args.out.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=args.mode + "-", dir=args.out.resolve()))
    sources = {n: sha(ROOT / n) for n in SOURCES};commands = []
    doc = dict(status="running", backend="f2" if args.mode == "vivado" else "eda",
               scope="concrete shared queue readout component; no FPGA capture or restore", physical_fpga_capture=False,
               full_image=False, host=socket.gethostname(), source_root=str(ROOT),
               observed_utc=datetime.now(timezone.utc).isoformat(), sources=sources)
    (out / "summary.json").write_text(json.dumps(doc, indent=2) + "\n");print(out, flush=True)
    def run(argv, name, expected=0):
        row = dict(argv=list(map(str, argv)), cwd=str(out), log=str(out / (name + ".log")));commands.append(row)
        with Path(row["log"]).open("w") as f: result = subprocess.run(row["argv"], cwd=out, stdout=f, stderr=subprocess.STDOUT)
        row["returncode"] = result.returncode
        (out / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        if result.returncode != expected:
            # Preserve a source/input-bound failure; no native receipt becomes
            # successful merely because the unsupported policy is diagnosed.
            doc.update(status="fail", commands=commands, failed_command=row,
                       artifacts={str(p.relative_to(out)): sha(p) for p in out.rglob("*")
                                  if p.is_file() and p.suffix in {".log", ".rpt", ".dcp", ".vcd"}})
            (out / "summary.json").write_text(json.dumps(doc, indent=2) + "\n")
        require(result.returncode == expected, "inspect underlying compiler/runtime log " + row["log"])
        return Path(row["log"]).read_text()
    if args.mode == "vivado":
        require(ROOT == Path("/home/ubuntu/chia-cy-checkpoint-restore") and shutil.which("vivado"), "native localhost Vivado required")
        require(args.generated is not None and args.native is None, "explicit generated input required")
        shutil.copytree(args.generated, out / "generated");rows = audit(out / "generated")
        doc["rehashed_negatives"] = negative_audits(out / "generated", out / "audit-negatives")
        (out / "shared-queue-selectors.svh").write_text(selectors(out / "generated"))
        (out / "synthesis-wrapper.sv").write_text(synthesis_wrapper(out / "generated"))
        (out / "sources").mkdir()
        for n in SOURCES: shutil.copyfile(ROOT / n, out / "sources" / Path(n).name)
        vendor = Path(os.environ["XILINX_VIVADO"]) / "data/verilog/src"
        for n, p in [("BUFGCE.v", vendor / "unisims/BUFGCE.v"), ("glbl.v", vendor / "glbl.v")]: shutil.copyfile(p, out / n)
        (out / "synth.tcl").write_text('''set_param general.maxThreads 4
read_verilog -sv generated/generated.sv
read_verilog -sv synthesis-wrapper.sv
read_xdc generated/generated.synthesis.xdc
synth_design -top SharedQueueSynthesisTop -part xcvu47p-fsvh2892-2-e -mode out_of_context -flatten_hierarchy none
create_clock -name raw_clock -period 7.142857 [get_ports clock]
foreach path {host/q0 host/q1 host/q2} {
  if {[llength [get_cells $path]] != 1} {error "original queue execution disappeared"}
}
set all_block [get_cells -hier -filter {REF_NAME =~ RAMB*}]
set all_other_ram [get_cells -hier -filter {REF_NAME =~ RAM* && REF_NAME !~ RAMB*}]
foreach cell $all_other_ram {
  if {[regexp {^host/q[012]/} [get_property NAME $cell]]} {
    error "original BLOCK memory policy fell back to distributed RAM at $cell"
  }
}
set counts {}
foreach path {host/q0 host/q1 host/q2} {
  set count 0
  foreach cell $all_block {
    if {[string match "$path/*" [get_property NAME $cell]]} {incr count}
  }
  if {$count == 0} {error "original BLOCK memory policy has no primitive at $path"}
  lappend counts $count
}
puts "SHARED_QUEUE_MEMORY_PRIMITIVES selected0=[lindex $counts 0] selected1=[lindex $counts 1] sibling=[lindex $counts 2]"
report_utilization -file utilization.rpt
report_timing_summary -file timing.rpt
write_checkpoint -force shared-queue-access.dcp
puts "SHARED_QUEUE_SYNTH_PASS selected=2 untouched=1"
''')
        doc["inputs"] = {str(p.relative_to(out)): sha(p) for p in out.rglob("*") if p.is_file() and p.name != "summary.json"}
        text = run(["vivado", "-mode", "batch", "-source", "synth.tcl"], "synth")
        require("SHARED_QUEUE_SYNTH_PASS selected=2 untouched=1" in text and not re.search(r"ERROR:|CRITICAL WARNING:|Infeasible attribute ram_style", text), "native shared queue synthesis failure")
        resources = re.search(r"SHARED_QUEUE_MEMORY_PRIMITIVES selected0=(\d+) selected1=(\d+) sibling=(\d+)", text)
        require(resources is not None and min(map(int, resources.groups())) > 0, "missing physical BLOCK memory policy audit")
        doc["block_memory_primitives"] = dict(zip(("selected0", "selected1", "sibling"), map(int, resources.groups())))
        doc["entries"] = len(rows)
    else:
        require(str(ROOT).startswith("/scratch/") and toolchain.VCS == "/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs", "fresh EDA SP2 required")
        require(args.native is not None and args.generated is None, "explicit native receipt required")
        native = json.loads((args.native / "summary.json").read_text())
        require(native["status"] == "pass" and native["backend"] == "f2" and native["sources"] == sources, "stale native queue source binding")
        for group in ("inputs", "artifacts"):
            for n, h in native[group].items(): require(sha(args.native / n) == h, "changed native evidence " + n)
        for n in native["inputs"]:
            dest = out / n;dest.parent.mkdir(parents=True, exist_ok=True);shutil.copyfile(args.native / n, dest)
        doc["inputs"] = native["inputs"];audit(out / "generated")
        require((out / "synthesis-wrapper.sv").read_text() == synthesis_wrapper(out / "generated"), "changed production-shaped endpoint wrapper")
        require((out / "shared-queue-selectors.svh").read_text() == selectors(out / "generated"), "changed queue oracle selectors")
        for mode in ("healthy", "corrupt", "corrupt-observation"):
            folder = out / mode;folder.mkdir()
            text = (out / "generated/generated.sv").read_text()
            if mode == "corrupt":
                needle = "assign checkpoint_shell_region0_ckpt_resp_data = checkpoint_shell_region0_ckpt_saved_data;"
                require(text.count(needle) == 1, "ambiguous first response corruption site")
                text = text.replace(needle, needle[:-1] + " ^ 64'h1;")
            elif mode == "corrupt-observation":
                leaf = re.search(r"(?m)^module checkpoint_shell_region0_selected_SharedQueue\([\s\S]*?^endmodule\b", text)
                require(leaf is not None, "missing native observation corruption owner")
                changed, count = re.subn(r"(assign checkpoint_shell_region0_ckpt_native_state = )([^;]+);",
                    r"\1(\2) ^ 518'h1;", leaf[0])
                require(count == 1, "ambiguous native observation corruption site")
                text = text[:leaf.start()] + changed + text[leaf.end():]
            (folder / "compiled.sv").write_text(text)
            run([toolchain.VCS, "-full64", "-sverilog", "-timescale=1ns/1ps", "-Mupdate", "-debug_access+all",
                 "+incdir+" + str(out), "-top", "shared_queue_access_tb", "-top", "glbl", "-Mdir=" + str(folder / "csrc"),
                 "-o", str(folder / "simv"), str(folder / "compiled.sv"), str(out / "synthesis-wrapper.sv"),
                 str(out / "sources/shared_queue_access_tb.sv"), str(out / "sources/checkpoint_widget_exit.cc"),
                 str(out / "BUFGCE.v"), str(out / "glbl.v")], mode + "-compile")
            text = run([folder / "simv", "-no_save"], mode + "-run", 0 if mode == "healthy" else 1)
            wave = out / "shared-queue-access.vcd";require(wave.is_file() and wave.stat().st_size > 0, "missing queue debug waveform")
            shutil.move(wave, folder / wave.name)
            if mode == "healthy":
                match = re.search(r"SHARED_QUEUE_PASS checks=(\d+) reads=364 stalls=(\d+) edges=(\d+) cuts=4 sibling_pushes=(\d+)", text)
                require(match and int(match[1]) > 1000 and int(match[4]) > 100, "incomplete active queue coverage")
                doc["checks"], doc["stalls"], doc["edges"], doc["sibling_pushes"] = map(int, match.groups())
                doc["reads"] = 364;doc["retained_original_reads"] = 361;doc["cuts"] = 4
                observation = re.search(r"NATIVE_OBSERVATION_PASS fields_per_queue=14 bits_per_queue=518 comparisons=(\d+)", text)
                require(observation is not None and int(observation[1]) > 10000,
                        "missing complete live native state observation coverage")
                doc["native_observation_comparisons"] = int(observation[1])
                latency = re.search(r"delayed_reads=(\d+) wait_cycles=(\d+) cancellations=(\d+) held_releases=(\d+) premature_releases=(\d+) running_reset_pulses=(\d+)", text)
                require(latency is not None and int(latency[1]) >= 288 and int(latency[2]) >= int(latency[1])
                        and int(latency[3]) == 3 and int(latency[4]) == 1 and int(latency[5]) == 2 and int(latency[6]) == 1, "missing synchronous latency and reset cancellation coverage")
                doc["delayed_reads"], doc["response_wait_cycles"], doc["cancellations"], doc["held_response_releases"], doc["premature_releases"], doc["running_reset_pulses"] = map(int, latency.groups())
            elif mode == "corrupt":
                require("SHARED_QUEUE_DIVERGENCE signal=complete selected word cuts=0" in text
                        and "frozen=11 response_ack=00 reads=0" in text and "SHARED_QUEUE_PASS" not in text,
                        "corruption acknowledged an edge/word or failed to stop on first read")
                doc["compiled_first_word_corruption_rejected_before_ack"] = True
            else:
                require("SHARED_QUEUE_DIVERGENCE signal=native observation q0 CheckpointNativeBorrowed" in text
                        and "response_ack=00 reads=0" in text and "SHARED_QUEUE_PASS" not in text,
                        "native observation corruption escaped its first divergent sample")
                doc["compiled_native_observation_corruption_rejected_before_ack"] = True
        doc["native_receipt"] = dict(path=str(args.native / "summary.json"), sha256=sha(args.native / "summary.json"))
    emitted = [emitted_observation(out / "generated", q,
        canonical_json(out / "generated" / f"shell-{q}-banks-binding.json")) for q in range(2)]
    if args.mode == "vcs":
        require(emitted == native["emitted_observation"], "changed native-bound emitted observation storage")
    doc["emitted_observation"] = emitted
    require(sources == {n: sha(ROOT / n) for n in SOURCES}, "queue sources changed during verification")
    doc.update(status="pass", commands=commands, artifacts={str(p.relative_to(out)): sha(p) for p in out.rglob("*")
               if p.is_file() and (p.suffix in {".log", ".rpt", ".dcp", ".vcd"} or p.name in {"commands.json", "compiled.sv", "simv"})})
    (out / "summary.json").write_text(json.dumps(doc, indent=2) + "\n");print(out / "summary.json", flush=True)


if __name__ == "__main__": main()
