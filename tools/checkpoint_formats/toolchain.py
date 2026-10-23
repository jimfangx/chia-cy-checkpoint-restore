"""Exact toolchain selected for a verification run (also used by its audits).

New runs default to the EDA SP2 installation. To audit historical SP1 receipts,
explicitly select that installation with CHECKPOINT_EDA_VCS; receipts themselves
remain immutable. vcs-env.sh exports the actual native compiler paths.
"""
import os
from pathlib import Path

VCS = os.environ.get('CHECKPOINT_EDA_VCS', '/tools/Synopsys/vcs/Y-2026.03-SP2/bin/vcs')
VCS_HOME = str(Path(VCS).parent.parent)
VCS_RELEASE = Path(VCS_HOME).name
VCS_VERSION = VCS_RELEASE + '_Full64'
CC = os.environ.get('CHECKPOINT_EDA_CC', '/usr/bin/gcc-13')
CXX = os.environ.get('CHECKPOINT_EDA_CXX', '/usr/bin/g++-13')
