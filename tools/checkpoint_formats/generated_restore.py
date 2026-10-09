"""Manifest-bound staging for the generated RTL component of Level 1.

This is deliberately not a .fsckpt loader. The coordinator must separately own
all software/harness state and stop clocks. Only settled LOW host-clock cuts
are supported; depositing a high BUFGCE output would create a target edge.
"""
import hashlib
import json
from pathlib import Path
import re

from .codec import HASH, bit_value, canonical, keys, natural, require
from .replay import IDENT, modules
from .simulator import check_generated_rtl, generated_words, validate_generated_manifest


def generated_build_identity(manifest, reference, rtl, bufgce_model):
    check_generated_rtl(manifest, reference, rtl + bufgce_model, bufgce_model)
    return hashlib.sha256(canonical(dict(manifest=manifest, rtl=rtl,
                                         bufgce_model=bufgce_model))).hexdigest()


def prepare_generated_loader(manifest, build_hash, out, root="generated_tb.FPGATop", *, rtl=None):
    """Compile a trusted entry table, bounded by entries rather than RAM words.

    The build identity must come from generated_build_identity, after emitted
    coverage validation. The eventual aggregate coordinator must also bind the
    native executable and runtime configuration, which are outside this table.
    """
    validate_generated_manifest(manifest)
    require(type(build_hash) is str and HASH.fullmatch(build_hash), "invalid generated build hash")
    require(type(root) is str and all(re.fullmatch(IDENT, p) for p in root.split('.')),
            "invalid generated loader root")
    digest = hashlib.sha256(canonical(manifest)).hexdigest()
    declarations = []
    clocks = []
    for entry in manifest["state"]:
        path = root + entry["hierarchy"][len(manifest["root_module"]):]
        declarations.append('{%s, %d, %d, %s, %s}' % (
            json.dumps(path), entry["width"], entry["depth"],
            str(entry["kind"] == "memory").lower(),
            str(entry["adapter"] == "metasim-bufgce-v1").lower()))
        if entry["adapter"] in ("metasim-bufgce-v1", "abstract-clock-gate-v1"):
            gate = path.rsplit('.', 1)[0]
            clocks.extend([gate + '.I', gate + '.O'])
        elif rtl is None:
            # Without emitted syntax, only a directly named local clock can
            # be audited. Aggregate memory clock metadata needs the RTL.
            require(re.fullmatch(IDENT, entry['clock_expression']),
                    "emitted RTL required for compound/memory clock inventory")
            clocks.append(path.rsplit('.', 1)[0] + '.' + entry['clock_expression'])
    if rtl is not None:
        # Inventory every actual edge sensitivity, including emitter-created
        # memory pipelines whose clock metadata names a FIRRTL memory port.
        syntax = re.sub(r'//[^\n]*|/\*.*?\*/', '', rtl, flags=re.S)
        definitions = modules(syntax)
        for instance in manifest['instances']:
            if instance['module'] == 'BUFGCE':
                continue  # Its pinned external I/O adapter is handled above.
            require(instance['module'] in definitions, 'missing emitted clock owner')
            body = definitions[instance['module']][1]
            for event in re.findall(r'\balways(?:_ff)?\s*@\s*\(([^)]+)\)', body):
                for edge in re.split(r'\s+or\s+', event.strip()):
                    match = re.fullmatch(r'(?:posedge|negedge)\s+(' + IDENT + ')', edge)
                    require(match is not None, 'unsupported generated clock sensitivity')
                    clocks.append(root + instance['hierarchy'][len(manifest['root_module']):] + '.' + match[1])
    source = ('// Generated from the independently checked Level-1 manifest.\n'
              f'static const char *manifest_hash = {json.dumps(digest)};\n'
              f'static const char *build_hash = {json.dumps(build_hash)};\n'
              f'static const char *clock_path = {json.dumps(root + ".clock")};\n'
              'static const Entry entries[] = {\n' + ',\n'.join(declarations) + '\n};\n'
              'static const char *clock_paths[] = {\n' +
              ',\n'.join(json.dumps(path) for path in sorted({root+'.clock', *clocks})) + '\n};\n')
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "generated-restore-table.h").write_text(source)
    return sum(e["depth"] for e in manifest["state"])


def prepare_generated_restore(manifest, capture, build_hash, destination,
                              root="generated_tb.FPGATop"):
    """Validate every captured owner and value before publishing staging text.

    Staging is a trusted local intermediary, like semantic_restore's input,
    not a durable checkpoint container. No format checksum/aggregate ownership
    is implied. The VPI consumer rechecks identity, membership, shape and bits.
    """
    text = generated_restore_text(manifest, capture, build_hash, root)
    Path(destination).write_text(text)
    return len(capture['records'])


def generated_restore_text(manifest, capture, build_hash, root="generated_tb.FPGATop"):
    """Validate and render a component without publishing any staging file."""
    validate_generated_manifest(manifest)
    require(type(build_hash) is str and HASH.fullmatch(build_hash), "invalid generated build hash")
    require(type(root) is str and all(re.fullmatch(IDENT, p) for p in root.split('.')),
            "invalid generated loader root")
    keys(capture, {"capture_version", "capture_type", "scope", "external_runtime_required",
                   "manifest_sha256", "host_sample", "sample_phase", "records"})
    digest = hashlib.sha256(canonical(manifest)).hexdigest()
    require(type(capture["capture_version"]) is int and capture["capture_version"] == 1
            and capture["capture_type"] == "generated_rtl_diagnostic"
            and capture["scope"] == "generated_rtl_only"
            and capture["external_runtime_required"] is True
            and capture["manifest_sha256"] == digest
            and capture["sample_phase"] == "settled_host_negedge", "incompatible generated restore cut")
    natural(capture["host_sample"])
    words = list(generated_words(manifest))
    require(type(capture["records"]) is list and len(capture["records"]) == len(words),
            "incomplete generated restore")
    clock_outputs = {e["hierarchy"] for e in manifest["state"] if e["adapter"] == "metasim-bufgce-v1"}
    rows = [f'FSGRTL1 {digest} {build_hash} settled_host_negedge {len(words)}']
    for word, record in zip(words, capture["records"]):
        keys(record, {"owner", "width", "value"})
        require(record["owner"] == word["owner"] and type(record["width"]) is int
                and record["width"] == word["width"], "generated restore membership/shape mismatch")
        bit_value(record)
        require(record["owner"] not in clock_outputs or int(record["value"], 16) == 0,
                "high generated clock output would advance target time")
        path = root + record["owner"][len(manifest["root_module"]):]
        rows.append(f'{path} {record["width"]} {record["value"]}')
    # All validation precedes file creation, including bad records at the end.
    return '\n'.join(rows) + '\n'
