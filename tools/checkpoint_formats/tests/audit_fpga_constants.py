"""Reconstruct the production FPGA constant transformation from its source.

This establishes exact source/branch selection, never physical capture. Compare
every unchanged definition as well as every replaced module and repeated owner.
"""
import hashlib
import json
from pathlib import Path
import re

from tools.checkpoint_formats.codec import require

MODEL_SHA256 = '482a63c1f24a7ac920909620bd0df108e6954eabf9520de6e72334a2b5450efb'
SCOPE = 'source_checked_fpga_plusarg_constants_only'
PREFIX = '.fpga-constants-'


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def modules(text):
    headers = list(re.finditer(r'^  (extmodule|module) ([A-Za-z_][A-Za-z0-9_$]*) :[^\n]*', text, re.M))
    require(headers and len({h[2] for h in headers}) == len(headers), 'duplicate/missing constant definition')
    root = re.fullmatch(r'(?:FIRRTL version [^\n]+\n)?circuit ([A-Za-z_][A-Za-z0-9_$]*) :[^\n]*\n\s*', text[:headers[0].start()])
    require(root is not None, 'unsupported constant circuit header')
    result = {}
    for index, header in enumerate(headers):
        body = text[header.start():headers[index+1].start() if index+1 < len(headers) else len(text)].rstrip('\n')
        body = '\n'.join(line[2:] if line.startswith('  ') else line for line in body.splitlines())
        result[header[2]] = (header[1], body)
    return root[1], result


def without_info(body):
    return re.sub(r' @\[[^\n]*?\]', '', body)


def audit(original: Path, prepared: Path, sources: Path, report: Path, binding: Path, emitted_body: Path):
    text = original.read_text()
    prepared_text = prepared.read_text()
    doc = json.loads(report.read_text())
    final = json.loads(binding.read_text())
    require(doc['preparation_version'] == 1 and doc['scope'] == final['scope'] == SCOPE and
            doc['complete_fpga_capture'] is False and doc['deployable_capture_image'] is False and
            doc['external_runtime_required'] is True and final['binding_version'] == 1 and
            final['complete_fpga_capture'] is False and final['deployable_capture_image'] is False,
            'constant audit cannot claim physical capture')
    require(doc['original_reference_sha256'] == digest(text) and
            doc['prepared_reference_sha256'] == digest(prepared_text) and
            doc['inline_sources_sha256'] == digest(sources.read_text()) and
            final['emitted_verilog_sha256'] == digest(emitted_body.read_text()), 'unbound constant inputs')
    expected_inputs = {PREFIX+name: digest(path.read_text()) for name, path in [
        ('original.fir', original), ('prepared.fir', prepared), ('sources.json', sources), ('preparation.json', report)]}
    require(final['inputs'] == expected_inputs, 'missing or altered constant emission input')
    root, before = modules(text)
    prepared_root, after = modules(prepared_text)
    require(root == prepared_root == doc['root_module'] and list(before) == list(after),
            'changed constant root or definition inventory')
    replaced = {name for name, (kind, body) in before.items() if kind == 'extmodule' and
                re.search(r'^  defname = plusarg_reader$', body, re.M)}
    require(replaced and [r['module'] for r in doc['constants']] == sorted(replaced),
            'omitted/reordered/duplicate synthesis constant')
    inline = json.loads(sources.read_text())
    require(len(inline) == len(replaced), 'incomplete constant inline sources')
    require([a['target'] for a in inline] == [root+'.'+name for name in sorted(replaced)],
            'foreign/reordered/duplicate constant inline sources')
    for annotation in inline:
        require(annotation['class'] == 'firrtl.transforms.BlackBoxInlineAnno' and
                digest(annotation['text']) == MODEL_SHA256 and isinstance(annotation['name'], str),
                'unknown constant source implementation')
    paths = {name: [] for name in replaced}
    seen = set()

    def walk(name, path, ancestors):
        require(name in before and name not in ancestors and path not in seen, 'missing/recursive/duplicate constant hierarchy')
        seen.add(path)
        if name in replaced:
            paths[name].append(path)
        elif before[name][0] == 'module':
            for instance, child in re.findall(r'^\s+inst (\w+) of (\w+)(?:\s|$)', before[name][1], re.M):
                walk(child, path+'.'+instance, ancestors | {name})
    walk(root, root, set())
    for row in doc['constants']:
        name = row['module']
        body = before[name][1]
        clean = without_info(body)
        width = re.findall(r'^  parameter WIDTH = (\d+)$', clean, re.M)
        default = re.findall(r'^  parameter DEFAULT = (\d+)$', clean, re.M)
        fmt = re.findall(r'^  parameter FORMAT = ("[^\n]*")$', clean, re.M)
        require(len(width) == len(default) == len(fmt) == 1, 'malformed constant parameters')
        width, default, fmt = int(width[0]), int(default[0]), json.loads(fmt[0])
        require(0 < width <= 2147483647 and 0 <= default < (1 << width) and
                re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*=%[dbh]', fmt), 'unsupported constant parameters')
        expected = [f'extmodule {name} :', f'  output out : UInt<{width}>', '  defname = plusarg_reader']
        require(clean.splitlines()[:3] == expected and len(clean.splitlines()) == 6 and
                len(re.findall(r'^  parameter ', clean, re.M)) == 3, 'hidden constant ports or owners')
        require(row['width'] == width and row['default'] == default and row['format'] == fmt and
                row['source_sha256'] == MODEL_SHA256 and row['original_definition_sha256'] == digest(body) and
                row['reachable_instances'] == sorted(paths[name]), 'changed constant values or ownership')
        require(after[name][0] == 'module' and [line for line in without_info(after[name][1]).splitlines() if line.strip()] == [
            f'module {name} :', f'  output out : UInt<{width}>', f'  out <= UInt<{width}>("h{default:x}")'],
            'prepared constant is not the exact combinational FPGA branch')
    require(all(before[name] == after[name] for name in before if name not in replaced),
            'constant preparation changed another state owner')
    return dict(status='pass', scope=SCOPE, physical_fpga_capture=False, root_module=root,
                replaced_definitions=len(replaced), reachable_constant_instances=sum(map(len, paths.values())),
                complete_instance_count=len(seen), original_reference_sha256=digest(text),
                prepared_reference_sha256=digest(prepared_text), report_sha256=digest(report.read_text()))
