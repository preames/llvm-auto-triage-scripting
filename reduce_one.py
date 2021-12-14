#!/usr/bin/python3
# reduce_one.py reducer revision build-dir corpus-dir testfile
#   Reduce a single standalone test via the specified reducer, and add the
#   fully reduced result back to the corpus.
#
#   IMPORTANT: Assumes (but does not check) that binaries in build-dir
#   correspond to a build of the source at revision.

import tempfile
from common import *

import os
import shutil

reducer = sys.argv[1]
revision = sys.argv[2]
builddir = os.path.abspath(sys.argv[3])
corpusdir = os.path.abspath(sys.argv[4])
test = os.path.abspath(sys.argv[5])

if reducer.endswith("-crash-unconstrained"):
    reducer = reducer[0:len(reducer)-len("-crash-unconstrained")]
    print (reducer)
    pass

if reducer == "llvm-reduce":
    reduce_with_llvm_reduce(builddir, corpusdir, test)
elif reducer == "bugpoint":
    reduce_with_bugpoint(builddir, corpusdir, test)
elif reducer == "creduce":
    reduce_with_creduce(builddir, corpusdir, test)
elif reducer == "opt-analysis-isolate-crash-unconstrained":
    vary_opt_pass(builddir, corpusdir, test)
else:
    print ("Unsupported reducer: %s" % reducer)
