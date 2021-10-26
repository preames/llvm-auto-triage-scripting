#!/usr/bin/python3
# run-one.py revision build-dir testfile
#   Run a single standalone test on the binaries available in build-dir,
#   and output a single observation log record reflecting that run.
#
#   IMPORTANT: Assumes (but does not check) that binaries in build-dir
#   correspond to a build of the source at revision.

from common import *
    
revision = sys.argv[1]
builddir = sys.argv[2]
test = sys.argv[3]

record = run_and_form_record(revision, builddir, test)
print (", ".join(record))
