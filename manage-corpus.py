#!/usr/bin/python3
# manage-corpus.py <list-of-new-files>
#   If given a list of files, will try to maximally reduce all examples. If
#   not given a list of files, will try to maximally reduce all files in the
#   corpus. Will also print errors for any obvious malformed entiries
#   encountered.
#
#   Uses configuration state from config.json
#
#   IMPORTANT: Assumes (but does not check) that binaries in build-dir
#   correspond to a build of the source at revision.



import hashlib
import sys
import os
import glob
from common import *

# We reduce each file with all available reducers, and then iteratively
# reduce newly produce files until a fixed point is reached.  The idea is
# that reducers may implement distinct subsets of possible techniques and
# that reducing may a) find something closer to a global minima, or b)
# expose another bug entirely.  Keep in mind that reducers are basically
# mutation fuzzers with a bias towards selecting smaller outputs as the
# input for the next round.  There's no requirement that the crash eventually
# reduced was the one you started with.

visited = set()
worklist = []

config = load_and_validate_comfig()
revision = config["LLVM_BUILD_REVISION"]
builddir = config["LLVM_BUILD_DIR"]
root = os.path.abspath(config["CORPUS_DIR"])

targets = None
if len(sys.argv) > 1:
    targets = [os.path.abspath(x) for x in sys.argv[1:]]
    for f in glob.iglob(root + "/**", recursive=True):
        if os.path.isdir(f):
            continue
        if f in visited:
            continue
        if f in targets:
            continue
        visited.add(f)

rescan_count = 0
def rescan_corpus():
    print ("Scanning for files...")
    # Guard against infinite looping in the case when one of the reduction
    # tools has a bug where re-reducing the last output always produces a
    # new distinct output.  Note that we don't care about alternating cases
    # (since those stablize to a fixed set), only an infinite series of new
    # output files.
    global rescan_count
    assert rescan_count < 50
    rescan_count += 1
    for f in glob.iglob(root + "/**", recursive=True):
        if os.path.isdir(f):
            continue
        if f in visited:
            continue
        visited.add(f)
        # Validate the test, but do nothing else if we can't find a valid
        # runline.  By doing this after the visited check, we only verify
        # each file once, no matter how many times we rescan.
        if None == get_valid_run_line(f, verbose=True):
            continue
        # Workaround a really annoying 'bug' where reducing a case with a
        # struct type ends up always remangling the type, and thus always
        # producing a new distinct output.  Do to this hack, we loose the
        # ability to cross reduce any test involving struct types.
        if rescan_count > 0 and " type {" in open(f, 'r').read():
            continue;
        
        worklist.append(os.path.abspath(f))
        pass
    pass


rescan_corpus()
while 0 != len(worklist):
    test = worklist.pop()
    print(test)

    # TODO: save a record to the observation log since we had to run it anyway
    completed = run_test(test, builddir)
    if completed.returncode == 0:
        print ("Skipping reduction of test which does not fail")
        continue

    ext = os.path.splitext(test)[1]

    if ext in [".c", ".cc", ".cpp", ".cxx"]:
        # Note: creduce can be applied to other input types, but it is
        # *slow* compared to other reducers.  Given that, if we have a
        # dedicated reducer for the input language, we chose not to.
        reduce_with_creduce(builddir, root, test)
        pass

    if ext == ".ll":
        reduce_with_bugpoint(builddir, root, test)
        reduce_with_llvm_reduce(builddir, root, test)
        vary_opt_pass(builddir, root, test)
        pass

    # TODO
    # for .ll files:
    #   add brute force pass reduction
    #   add crash isolation (e.g. capture IR just before crash)
    # for .c, .cpp extension
    #   use -emit-llvm C-->LL for attempted

    if 0 == len(worklist):
        rescan_corpus()
        pass
    pass
