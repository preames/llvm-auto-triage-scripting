This repository contains a set of fairly messy scripts to auto-reduce LLVM test
cases based on provided LLVM/clang build directory.  This is the code which
backs `preames/llvm-auto-triage-corpus <https://github.com/preames/llvm-auto-triage-corpus>`_.

If you're interested in building a public corpus based on a different build
configuration, please let me know.  Having a public reduction corpus against
old releases would be quite interesting given how often reduced IR cases tend
to still reproduce on ToT while original test programs don't.

Similiarly, this could be used to set up an internal/private reduction flow
if you happen to have a custom build of LLVM w/extensions.

TODO
----

This is an unordered list of ideas for enhancements.

Usability:

* Wrap everything in a docker container.
* Bailout if tool not in PATH (e.g. soft fail for alive2 tests on box
  without alive)
* implement requires handling (e.g. targets)
* Basic reporting for e.g. reduction tree + stack trace.  (Generate and sync)
* factor out a "reduce_one" command to reduce duplication

Ideas for reducers:

* MIR llvm-reduce - blocked by review response and/or some extra plumbing.
* clang->opt conversion
* clang -> assembler input conversion on .s files
* alive-tv -> opt-alive.sh pass guessing
* DD reduction for assembly files, maybe others?
* See if can figure out to speed up creduce and apply it to all input
  languages
  
Automation

* Try integrating with github actions on PRs
* Prioritize new files, then changed binaries
* Consider parallel execution separate from schedule - particularly for
  e.g. corpus ingestion.  Could maybe use something like aws lambda or
  auto-scale kubernetes?  Probablem is the task size problem though.

