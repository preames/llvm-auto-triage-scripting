#!/usr/bin/python3
# run-many.py revision build-dir N testfile
#   Run a single standalone test multiple times on the binaries available in
#   build-dir, and output a minimal set of observation log records reflecting
#   those run.  Useful for checking whether a particular test is deterministic
#   for a given environment.
#
#   IMPORTANT: Assumes (but does not check) that binaries in build-dir
#   correspond to a build of the source at revision.

from common import *
    
revision = sys.argv[1]
builddir = sys.argv[2]
count = int(sys.argv[3])
test = sys.argv[4]

records = {}
for i in range(0, count):
    record = tuple(run_and_form_record(revision, builddir, test))
    if record not in records:
        records[record] = 0
        pass
    records[record] += 1
    pass

for record in records.keys():
    out = list(record)
    out[0] = "+" + str(records[record])
    print (", ".join(out))
