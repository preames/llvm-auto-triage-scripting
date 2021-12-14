#!/usr/bin/python3
# validate_test.py build-dir corpus-dir
#   Given a single test, tries to validate it's format.


import sys
import os
from common import *

test = os.path.abspath(sys.argv[1])

runline = get_valid_run_line(test, verbose=True)
#print (runline)
