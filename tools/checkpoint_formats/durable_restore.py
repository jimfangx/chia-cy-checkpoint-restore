"""Compile the complete durable Level-1 consumer inventory into its executable."""
import json
from pathlib import Path

from .aggregate import digest
from .aggregate_packed import runtime_manifest
from .codec import require


def prepare_durable_loader(runtime, generated, layout, out):
    require('cut_contract' in runtime and runtime == runtime_manifest(
        runtime['profile'], generated, layout, runtime['native_owners'],
        runtime['native_build_hash'], runtime['cut_contract']['target_cycle_owner']),
        'durable restore requires a complete bound v3 runtime')
    text = ''
    for name, value in dict(profile=runtime['profile'], rtl_hash=generated['reference_sha256'],
                            build_hash=layout['generated_build_hash'], runtime_hash=digest(runtime),
                            generated_hash=digest(generated), harness_hash=digest(layout),
                            harness_source_hash=layout['source_hash']).items():
        text += f'static const char *durable_{name} = {json.dumps(value)};\n'
    text += 'static const DurableEntry durable_generated[] = {\n'
    for entry in generated['state']:
        text += '{%s, %s, %d, %d, %s},\n' % (
            json.dumps('generated-entry/'+entry['hierarchy']),
            json.dumps(layout['root']+'.'+entry['hierarchy']), entry['width'], entry['depth'],
            'true' if entry['adapter'] == 'metasim-bufgce-v1' else 'false')
    text += '};\nstatic const DurableEntry durable_harness[] = {\n'
    for row in layout['records']:
        text += '{%s, %s, %d, 1, %s},\n' % (
            json.dumps('harness/'+row['owner']), json.dumps(row['owner']), row['width'],
            'true' if row['owner'].endswith(('.reset', '.fin')) else 'false')
    text += '};\nstatic const DurableNative durable_native[] = {\n'
    for row in runtime['native_owners']:
        text += '{%s, %s},\n' % (json.dumps(row['owner']), json.dumps(row['schema']))
    text += '};\n'
    text += 'static const char *durable_target_cycle_owner = %s;\n' % json.dumps(
        'generated-entry/'+runtime['cut_contract']['target_cycle_owner'])
    (Path(out)/'durable-restore-table.h').write_text(text)
