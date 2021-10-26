#!/usr/bin/python3
# wrap_one.py build-dir testfile
#   Run a single standalone test on the binaries available in build-dir,
#   and propagate the output to the output pipes and exit with the
#   tests return code.  This is useful for checking that a test behaves
#   as expected when debugging reducer problems.

from common import *

builddir = sys.argv[1]
test = sys.argv[2]

completed = run_test(test, builddir)
sys.stdout.write(completed.stdout.decode())
sys.stderr.write(completed.stderr.decode())
sys.exit(completed.returncode)
