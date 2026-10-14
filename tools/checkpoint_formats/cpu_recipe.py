"""Source-bound native build settings for the initial CPU checkpoint matrix.

This prepares exact-recipe VCS builds; it grants no checkpoint capability. CPU
profiles remain rejected until their complete runtime owners have been audited.
The manager resolves TARGET_PROJECT_MAKEFRAG relative to the FireSim directory,
whereas a direct Make invocation runs in its sim subdirectory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex

import yaml

from .codec import require

ROOT = Path(__file__).resolve().parents[2]
RECIPE_FILE = ROOT / 'sims/firesim-staging/sample_config_build_recipes.yaml'
FIELDS = ('PLATFORM', 'TARGET_PROJECT', 'TARGET_PROJECT_MAKEFRAG', 'DESIGN',
          'TARGET_CONFIG', 'PLATFORM_CONFIG')
RECIPES = {
    'Rocket': 'firesim_rocket_quadcore_no_nic_l2_llc4mb_ddr3',
    'BOOM': 'firesim_boom_singlecore_no_nic_l2_llc4mb_ddr3',
    'Shuttle + Saturn': 'firesim_saturn_GENV256D128_shuttle_singlecore_no_nic_l2_llc4mb_ddr3',
}


def recipe_settings(name, recipe_file=RECIPE_FILE):
    require(name in RECIPES.values(), 'recipe outside initial CPU checkpoint matrix')
    source = Path(recipe_file).read_bytes()
    recipes = yaml.safe_load(source)
    require(type(recipes) is dict and name in recipes, 'missing CPU recipe')
    recipe = recipes[name]
    require(type(recipe) is dict, 'invalid recipe mapping')
    settings = {field: recipe.get(field) for field in FIELDS}
    require(all(type(v) is str and v and '\n' not in v for v in settings.values()),
            'missing/invalid exact recipe build setting')
    makefrag = (ROOT / 'sims/firesim' / settings['TARGET_PROJECT_MAKEFRAG']).resolve()
    require(makefrag.is_relative_to(ROOT) and makefrag.is_dir(), 'missing/out-of-tree recipe makefrag')
    return dict(recipe=name, family=next(k for k, v in RECIPES.items() if v == name),
                recipe_file=str(Path(recipe_file).resolve()), recipe_file_sha256=hashlib.sha256(source).hexdigest(),
                settings=settings, resolved_makefrag=str(makefrag),
                makefrag_resolution_base=str(ROOT / 'sims/firesim'),
                platform_config_args=recipe.get('platform_config_args'),
                fpga_bitstream_required=False, checkpoint_support_verified=False)


def native_build_command(settings, build, goal, *, semantic_root=None):
    require(goal in ('verilog', 'vcs'), 'CPU validation uses RTL generation or VCS metasim only')
    build = Path(build).resolve()
    require(build.is_relative_to(ROOT / 'automations/checkpoint_loop/runs'),
            'CPU build artifacts must be under diagnostic runs')
    args = ['make', '-C', 'sims/firesim/sim']
    args += [field + '=' + (settings['resolved_makefrag'] if field == 'TARGET_PROJECT_MAKEFRAG'
                           else settings['settings'][field]) for field in FIELDS]
    args += [f'BUILD_DIR={build}', 'SIMULATOR_CHECKPOINT_INVENTORY=FPGATop', 'JAVA_HEAP_SIZE=32G']
    if semantic_root is not None:
        require(type(semantic_root) is str and semantic_root, 'explicit pre-FAME root required')
        args += ['SEMANTIC_BRIDGE_CHECKPOINT_ROOT=' + semantic_root]
    if goal == 'vcs':
        args += ['VCS=/ecad/tools/synopsys/vcs/Y-2026.03-SP1/bin/vcs -full64', 'VCS_FLAGS=-Mupdate']
    args += [goal]
    cache = build.parent / 'coursier-cache'
    shell = ('source env.sh && source sims/firesim/env.sh && '
             'export COURSIER_CACHE=' + shlex.quote(str(cache)) + ' && '
             'export CXXFLAGS="${CXXFLAGS} -isystem ${CONDA_PREFIX}/include" && '
             'export LDFLAGS="${LDFLAGS} -L${CONDA_PREFIX}/lib" && '
             'source automations/checkpoint_loop/vcs-env.sh && ' + shlex.join(args))
    return dict(cwd='.', argv=['bash', '-lc', shell])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipe', choices=tuple(RECIPES.values()), required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--semantic-root')
    args = parser.parse_args()
    settings = recipe_settings(args.recipe)
    settings['commands'] = {goal: native_build_command(settings, args.build, goal,
                                                      semantic_root=args.semantic_root)
                            for goal in ('verilog', 'vcs')}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(settings, indent=2) + '\n')
    print(json.dumps(settings, indent=2))


if __name__ == '__main__':
    main()
