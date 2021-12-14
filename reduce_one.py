#!/usr/bin/python3
# reduce_one.py reducer testfile
#   Reduce a single standalone test via the specified reducer, and add the
#   fully reduced result back to the corpus.  Uses configuration state from
#   config.json
#
#   IMPORTANT: Assumes (but does not check) that binaries in build-dir
#   correspond to a build of the source at revision.

import tempfile
from common import *

import os
import shutil

reducer = sys.argv[1]
test = os.path.abspath(sys.argv[2])

config = load_and_validate_comfig()
revision = config["LLVM_BUILD_REVISION"]
builddir = config["LLVM_BUILD_DIR"]
corpusdir = os.path.abspath(config["CORPUS_DIR"])

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
