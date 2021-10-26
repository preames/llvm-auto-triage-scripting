#!/usr/bin/python3
# Given a file downloaded from oss-fuzz, use the filename to try to
# construct a self describing test, and add it to the corpus.

import sys
import os
import subprocess
import common

bcfile = sys.argv[1]
chunks = bcfile.split('-')
testid = chunks[len(chunks)-1]
passname = chunks[len(chunks)-2].replace('_', '-')

print ([testid, passname])

testfile = "./example-corpus/oss_fuzz/%s.ll" % testid
print (testfile)
if os.path.exists(testfile):
    print ("Test already ingested?")
    #sys.exit(1)
cmd = "~/llvm-dev/build/bin/opt -S %s -o %s" % (bcfile, testfile)
print (cmd)
subprocess.run(cmd, #capture_output=True,
               timeout=30, shell=True)
header = [ "; RUN: opt -%s -S < %s\n" % (passname, "%s"),
           "; XFAIL: *\n",
           "; REQUIRES: asserts\n" ]
common.rewrite_candidate(header, testfile)
