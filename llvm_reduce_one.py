#!/usr/bin/python3
# llvm_reduce-one.py revision build-dir corpus-dir testfile
#   Reduce a single standalone test via llvm-reduce, and add the fully
#   reduced result back to the corpus.
#
#   IMPORTANT: Assumes (but does not check) that binaries in build-dir
#   correspond to a build of the source at revision.

import tempfile
from common import *

import os
import shutil

revision = sys.argv[1]
builddir = os.path.abspath(sys.argv[2])
corpusdir = os.path.abspath(sys.argv[3])
test = os.path.abspath(sys.argv[4])

reduce_with_llvm_reduce(builddir, corpusdir, test)
