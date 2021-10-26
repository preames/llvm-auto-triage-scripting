#!/usr/bin/python3
# vary-one.py revision build-dir corpus-dir testfile
#
#   IMPORTANT: Assumes (but does not check) that binaries in build-dir
#   correspond to a build of the source at revision.

import tempfile
from common import *

import os

revision = sys.argv[1]
builddir = os.path.abspath(sys.argv[2])
corpusdir = os.path.abspath(sys.argv[3])
test = os.path.abspath(sys.argv[4])

vary_opt_pass(builddir, corpusdir, test)
