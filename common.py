import hashlib
import os
import sys
import subprocess
import shutil
import contextlib
import stat
import tempfile
import json

def append_file_contents_to_hash(hash, fname):
    assert os.path.exists(fname)
    with open(fname,'rb') as f:
        while chunk := f.read(8192):
            hash.update(chunk)
            pass
        pass
    pass

def sha1_of_files(files):
    hash = hashlib.sha1()
    for f in files:
        append_file_contents_to_hash(hash, f)
        pass
    return hash.hexdigest()


def get_machine_config_hash():
    hash = hashlib.sha1()
    append_file_contents_to_hash(hash, "/proc/version")
    with open("/proc/cpuinfo",'r') as f:
        for line in f.readlines():
            if line.startswith("cpu MHz") or line.startswith("bogomips"):
                continue
            hash.update(line.encode("ASCII"))
            pass
        pass
    return hash.hexdigest()

def find_on_path(binary):
    for path in os.environ['PATH'].split(':'):
        candidate = os.path.join(path, binary)
        if not os.path.exists(candidate):
            continue
        return candidate
    return None

def get_build_config_hash(builddir):
    files = [builddir + "CMakeCache.txt"]
    alive_tv = find_on_path("alive-tv")
    if None != alive_tv:
        files.append(alive_tv)
    return sha1_of_files(files)

def substitute_runline(runline, builddir, testsub):
    assert runline != None
    # Do approximately the same substitution LIT would; if a _very_
    # limited form thereof.
    cmd = runline.split(' ')[0]
    # Try to hardcode the run directory - yes, even though we modify PATH
    # just below - to make commands easier to copy.
    bindir = os.path.abspath(builddir) + "/bin"
    fullcmd = bindir + "/" + cmd
    if not os.path.exists(fullcmd):
        fullcmd = find_on_path(cmd)
        assert fullcmd != None
        pass
    runline = fullcmd + runline[len(cmd):]

    runline = runline.replace("%s", testsub)
    # Disable aslr so that crashes are (closer to) stable
    # It would be better to use a custom crash handler to print the
    # stack trace without addresses, but this works reasonable well
    # for now.
    runline = "setarch `uname -m` -R " + runline

    # Prepend the PATH with our specified build directory.  This is needed
    # as opt-alive.sh picks up the opt from the path.
    runline = ("PATH=%s:$PATH " % bindir) + runline
    return runline

# Get the runline from test, and perform all substitions and additions needed.
# %s is replaced with testsub, not the full path in test
def get_full_runline(builddir, test, testsub):
    runline = get_valid_run_line(test)
    assert runline != None
    return substitute_runline(runline, builddir, testsub)

def run_test(test, builddir):
    runline = get_full_runline(builddir, test, os.path.abspath(test))
    print(runline)
    
    # todo: catch the timeout exception and return a hash of that too
    completed = subprocess.run(runline, capture_output=True,
                               timeout=30, shell=True)
    #print(completed.returncode.to_bytes(4, byteorder='little'))
    #print(completed.stdout)
    #print(completed.stderr)
    return completed
    

def run_and_form_record(revision, builddir, test):
    machinesig = get_machine_config_hash()
    testsig = sha1_of_files([test])
    buildsig = get_build_config_hash(builddir)

    completed = run_test(test, builddir)
    #print (completed)
    hash = hashlib.sha1()
    hash.update(completed.returncode.to_bytes(4, byteorder='little'))
    hash.update(completed.stdout)
    hash.update(completed.stderr)
    outputsig = hash.hexdigest()

    return ["+1", revision, testsig, outputsig, buildsig, machinesig]

def get_comment_prefix(test):
    if test.endswith(".ll"):
        return ";"
    for ext in [".c", ".cc", ".cpp", ".cxx"]:
        if test.endswith(ext):
            return "//"
    if test.endswith(".s"):
        return "#"
    return None

def get_runline_prefix(test):
    comment_prefix = get_comment_prefix(test)
    if None == comment_prefix:
        return None
    return comment_prefix + " RUN:"

def get_valid_run_line(test, verbose=False):
    run_prefix = get_runline_prefix(test)
    if None == run_prefix:
        return None
    with open(test,'r') as f:
        runline = None;
        for line in f.readlines():
            line = line.strip()
            if line.startswith(run_prefix):
                runline = line
                break;
            pass
        if runline == None:
            if verbose:
                print ("No runtime found in test %s" % test)
                pass
            return None
        # For ease, allow a normal filechecked test, and just drop the
        # irrelevant bits
        runline = runline.split("|")[0]
        # drop the RUN prefix
        runline = runline[len(run_prefix):].strip()
        if "%s" not in runline:
            if verbose:
                print ("No %\s found in runline for %s" % test)
                pass
            return None
        return runline
    pass

def add_candidate_to_corpus(corpusdir, cand, verbose = False):
    runline = get_valid_run_line(cand)
    assert runline != None

    hash = sha1_of_files([cand])
    ext = os.path.splitext(cand)[1]
    fname = corpusdir + "/%s%s" % (hash, ext)
    if os.path.exists(fname):
        if verbose:
            print("%s already in corpus" % fname)
            pass
        return None
    if verbose:
        print("Added %s to corpus" % fname)
        pass
    shutil.copy(cand, fname)
    return fname


@contextlib.contextmanager
def scoped_cd(newdir):
    prevdir = os.getcwd()
    os.chdir(newdir)
    try:
        yield
    finally:
        os.chdir(prevdir)
        pass
    return

def make_exec(fname):
    old = os.stat(fname)
    os.chmod(fname, old.st_mode | stat.S_IEXEC)
    return

# Given a .ll candidate test, remove the source_filename and ModuleID lines,
# then prepend the specified comments (which are expected to have e.g. RUN line)
def rewrite_candidate(comments, fname):
    lines = []
    for line in comments:
        lines.append(line)
        pass
    with open(fname, 'r') as original:
        for line in original.readlines():
            if not line.startswith("source_filename") and not line.startswith("; ModuleID"):
                lines.append(line)
                pass
            pass
        pass
    
    with open(fname, 'w') as modified:
        modified.write("".join(lines))
        pass
    pass

def replace_runline(new_runline, fname):
    lines = []
    run_prefix = get_runline_prefix(fname)
    with open(fname, 'r') as original:
        for line in original.readlines():
            if line.startswith(run_prefix):
                lines.append(new_runline)
                continue
            lines.append(line)
            pass
        pass
    
    with open(fname, 'w') as modified:
        modified.write("".join(lines))
        pass
    pass


# Given an .ll test file, read all the user comment lines and return them
def read_comment_lines(fname):
    lines = []
    comment_prefix = get_comment_prefix(fname)
    with open(fname, 'r') as f:
        for line in f.readlines():
            if not line.strip().startswith(comment_prefix):
                continue
            # strip comments introduced by IR printer itself
            if line.strip().startswith("; Function Attrs"):
                continue
            if line.strip().startswith("; ModuleID"):
                continue
            lines.append(line)
            pass
        pass
    return lines

def log_reduction(corpusdir, toolname, test, to):
    logfile = corpusdir + "/reductions.log"
    with open(logfile, 'a') as f:
        entry = [toolname, os.path.relpath(test, corpusdir),
                 os.path.relpath(to, corpusdir)]
        f.write(json.dumps(entry) + "\n")
        pass
    pass

def reduce_with_bugpoint(builddir, corpusdir, test):
    assert test.endswith(".ll")
    with tempfile.TemporaryDirectory() as workingdir, scoped_cd(workingdir):
        print("Running bugpoint in %s" % workingdir)
        runline = get_valid_run_line(test)
        assert runline != None
        if not runline.startswith("opt"):
            print("Can't (yet?) reduce with bugpoint")
            return
        runline = builddir + "/bin/bugpoint" + runline[3:]
        runline = runline.replace("< %s", test)
        # message the arguments so that a standard opt runline will cause
        # bugpoint to reduce the opt crash
        runline = runline.replace("-S", "")
        runline += " --safe-run-llc"
        # Disable aslr so that crashes are (closer to) stable
        # It would be better to use a custom crash handler to print the
        # stack trace without addresses, but this works reasonable well
        # for now.
        runline = "setarch `uname -m` -R " + runline
        
        print(runline)
        subprocess.run(runline, capture_output=True,
                       timeout=60*5, shell=True, check=True)

        # Now that we've run bugpoint, convert the simplified output into
        # a standalone test case.
        cmd = builddir + "/bin/opt -S bugpoint-reduced-simplified.bc -o candidate.ll"
        subprocess.run(cmd, timeout=30, shell=True)

        comments = read_comment_lines(test)
        rewrite_candidate(comments, "candidate.ll")

        # Note: We treat reduction as somewhat of a canonicalization step.  That
        # is, we always add the "reduced" output to the corpus even if we don't
        # see any direct evidence of progress.  We don't worry about trying
        # to re-reduce the output as we assume the result being in the corpus
        # will cause this routine to eventually be invoked on the reduced
        # result.

        res = add_candidate_to_corpus(corpusdir, "candidate.ll", True)
        if None != res:
            log_reduction(corpusdir, "bugpoint-crash-unconstrained", test, res)
            pass
        pass
    return


def reduce_with_llvm_reduce(builddir, corpusdir, test):
    assert test.endswith(".ll")
    with tempfile.TemporaryDirectory() as workingdir, scoped_cd(workingdir):
        print("Running llvm-reduce in %s" % workingdir)
        runline = get_valid_run_line(test)
        assert runline != None
    
        # First, write the interestingness script.  It'll look something like:
        # #!/bin/bash
        # ~/llvm-dev/build/bin/opt -early-cse -S $@ && exit -1 || exit 0
        runline = get_full_runline(builddir, test, "$@")
        runline += " && exit -1 || exit 0"
        with open("interestingness.sh", "w") as f:
            # The first line is not optional, llvm-reduce fails with an
            # unhelpful message if left out.
            f.write("#!/bin/bash\n")
            f.write("\n")
            f.write(runline + "\n")
            pass

        make_exec("interestingness.sh")
        
        runline = "%s/bin/llvm-reduce -test=./interestingness.sh %s" % (builddir, test)
        
        print(runline)

        try:
            subprocess.run(runline, capture_output=True,
                           timeout=60*5, shell=True, check=True)
        except subprocess.CalledProcessError:
            # This means either the original test did not crash (i.e. there's
            # nothing to reduce, or that during reduction llvm_reduce itself
            # crashed.  The later is generally because it internally produced
            # invalid IR.  Help with fixing these bugs is appreciated.
            print ("llvm_reduce failed, unable to reduce %s" % test)
            return

        # Now that we've run bugpoint, convert the simplified output into
        # a standalone test case.
        shutil.copy("reduced.ll", "candidate.ll")

        comments = read_comment_lines(test)
        rewrite_candidate(comments, "candidate.ll")

        # Note: We treat reduction as somewhat of a canonicalization step.  That
        # is, we always add the "reduced" output to the corpus even if we don't
        # see any direct evidence of progress.  We don't worry about trying
        # to re-reduce the output as we assume the result being in the corpus
        # will cause this routine to eventually be invoked on the reduced
        # result.

        res = add_candidate_to_corpus(corpusdir, "candidate.ll", True)
        if None != res:
            log_reduction(corpusdir, "llvm-reduce-crash-unconstrained",
                          test, res)
            pass
        pass
    return

all_passes = ["-simplify-cfg",
              "-sroa",
              "-early-cse",
              "-instcombine",
              "-instsimplify",
              "-gvn-hoist",
              "-inline",
              "-loop-vectorize",
              "-memcpyopt",
              "-dse",
              "-gvn",
              "-jump-threading",
              "-consthoist",
              "-indvars"
              ]

simple_passes = ["-instsimplify",
                 "-enable-new-pm=0 -analyze -domtree",
                 "-enable-new-pm=0 -analyze -loops",
                 "-enable-new-pm=0 -analyze -scalar-evolution",
                 "-enable-new-pm=0 -analyze -memoryssa"
                 ]


# The basic idea of this reducer is to try to isolate failures in particular
# analyzes which are widely used.  A -gvn crash which is actually in e.g.
# domtree construction or -instsimplify can be more easily triaged if only
# the relevant analysis code is involved in the runline. This does not reduce
# a pass list, it simply checks to see if the sole pass used can be replaced.
def vary_opt_pass(builddir, corpusdir, test):
    assert test.endswith(".ll")
    runline = get_valid_run_line(test)
    assert runline != None
    cmd = runline.split(' ')[0]
    if cmd != "opt":
        return None

    origpass = None
    for passoption in all_passes:
        if passoption not in runline:
            continue;
        if None != origpass:
            return None
        origpass = passoption
        pass
    if origpass == None:
        return
    print("vary_opt_pass found %s pass used in %s" % (origpass, test))

    with tempfile.TemporaryDirectory() as workingdir, scoped_cd(workingdir):
        print("Running vary_opt_pass in %s" % workingdir)

        # Make sure that the original test fails unmodified, and passes
        # if we drop the single pass from the command line.
        result = run_test(test, builddir)
        if result.returncode == 0:
            return None
        candidate = "candidate.ll"
        shutil.copy(test, candidate)
        new_runline = "; RUN: " + runline.replace(origpass, "") + "\n"
        replace_runline(new_runline, candidate)
        result = run_test(candidate, builddir)
        if result.returncode != 0:
            return None
        
        for passoption in simple_passes:
            if origpass == passoption:
                continue;
            print("Trying test with pass %s" % passoption)
            shutil.copy(test, candidate)
            new_runline = "; RUN: " + runline.replace(origpass, passoption) + "\n"
            replace_runline(new_runline, candidate)
            #with open(candidate, 'r') as original:
            #    print(original.read())
            #    pass
            result = run_test(candidate, builddir)
            if result.returncode == 0:
                continue
            res = add_candidate_to_corpus(corpusdir, candidate, True)
            if None != res:
                reducertag = "opt-analysis-isolate-crash-unconstrained"
                log_reduction(corpusdir, reducertag, test, res)
                pass
            pass
        pass
    return

# Specifically, reduce a compiler crash.
def reduce_with_creduce(builddir, corpusdir, test):
    with tempfile.TemporaryDirectory() as workingdir, scoped_cd(workingdir):
        print("Running creduce in %s" % workingdir)
        runline = get_valid_run_line(test)
        assert runline != None

        ext = os.path.splitext(test)[1]
        candidate = "candidate" + ext

        # Note: CReduce reduces *in place* by default
        shutil.copy(test, candidate)
    
        # First, write the interestingness script.  To get creduce to reduce
        # assertion failures, we need to make return code 134 interesting, and
        # all others not.  This avoids e.g. reducing any input which doesn't
        # parse as C/C++. Why 134 is the magic crash ret code, I have no idea
        runline = get_full_runline(builddir, test, candidate) + "\n";
        runline += "if [ $? -eq 134 ]; then\n"
        runline += "  exit 0\n"
        runline += "fi;\n"
        runline += "exit 1\n"
        with open("interestingness.sh", "w") as f:
            # The first line is not optional, llvm-reduce fails with an
            # unhelpful message if left out.
            f.write("#!/bin/bash\n")
            f.write("\n")
            f.write(runline + "\n")
            pass

        make_exec("interestingness.sh")
        #with open("interestingness.sh", 'r') as f:
        #    print(f.readlines())

        runline = "creduce ./interestingness.sh %s" % candidate
        if ext not in [".c", ".cc", ".cpp", ".cxx"]:
            runline += " --not-c"
            pass
        print(runline)

        try:
            subprocess.run(runline, capture_output=True,
                           timeout=60*5, shell=True, check=True)
        except subprocess.CalledProcessError:
            # This means either the original test did not crash (i.e. there's
            # nothing to reduce, or that during reduction creduce itself
            # crashed.
            print ("creduce failed, unable to reduce %s" % test)
            return
        except subprocess.TimeoutExpired:
            print ("creduce timed out on %s" % test)
            return

        # Now that we've run creduce, convert the simplified output into
        # a standalone test case.
        if ext in [".ll"]:
            # CReduce doesn't know how to pretty print IR, so run it through
            # opt -S to normalize whitespace.
            cmd = builddir + "/bin/opt -S %s -o temp.ll && cp temp.ll %s" % (candidate, candidate)
            subprocess.run(cmd, capture_output=True,
                           timeout=20, shell=True)
            pass

        comments = read_comment_lines(test)
        rewrite_candidate(comments, candidate)
        res = add_candidate_to_corpus(corpusdir, candidate, True)
        if None != res:
            reducertag = "creduce-crash-unconstrained"
            log_reduction(corpusdir, reducertag, test, res)
            pass
        pass
    return

# Given a clang crash, see if we can produce a standalone opt/llc test
# case.
def convert_clang_test_to_opt_test(builddir, corpusdir, test):
    runline = get_valid_run_line(test)
    assert runline != None
    cmd = runline.split(' ')[0]
    if cmd != "clang":
        return None

    with tempfile.TemporaryDirectory() as workingdir, scoped_cd(workingdir):
        print("Running clang-to-opt in %s" % workingdir)

        # Make sure that the original test fails unmodified.
        result = run_test(test, builddir)
        if result.returncode == 0:
            return None

        # Extract the IR to be passed to opt
        opt_runline = runline
        opt_runline += " -emit-llvm -disable-llvm-optzns"
        opt_runline += " -o candidate.ll"
        opt_runline = substitute_runline(opt_runline, builddir, test)
        completed = subprocess.run(opt_runline, capture_output=True,
                                   timeout=30, shell=True)
        if completed.returncode != 0:
            print("Unable to extract IR - probably a frontend crash")
            return None;

        # TODO: Need to do better than just blindly assume O2, but need
        # some real examples to play with.

        # Run opt on the captured IR, if that fails, consider that a new test
        # case and add it to the corpus
        opt_runline = "opt -S -O2 < candidate.ll -o llc-candidate.ll \n"
        opt_runline = substitute_runline(opt_runline, builddir, test)
        completed = subprocess.run(opt_runline, capture_output=True,
                                   timeout=30, shell=True)
        if completed.returncode != 0:
            candidate = "candidate.ll"
            new_runline = "; RUN: opt -S -O2 < %s \n"
            rewrite_candidate(new_runline, candidate)
            result = run_test(candidate, builddir)
            assert result.returncode != 0
            res = add_candidate_to_corpus(corpusdir, candidate, True)
            if None != res:
                reducertag = "clang-to-opt-crash-unconstrained"
                log_reduction(corpusdir, reducertag, test, res)
                pass
            return

        # If opt didn't fail, try piping the output of opt to LLC, and
        # see if we can create a backend test case.
        candidate = "llc-candidate.ll"
        new_runline = "; RUN: llc -O2 < %s \n"
        rewrite_candidate(new_runline, candidate)
        result = run_test(candidate, builddir)
        if result.returncode == 0:
            # Can't make progress
            return None;
        res = add_candidate_to_corpus(corpusdir, candidate, True)
        if None != res:
            reducertag = "clang-to-llc-crash-unconstrained"
            log_reduction(corpusdir, reducertag, test, res)
            pass
        return
    return

def validate_and_canoncalize_config_path(config, key):
    assert key in config
    value = config[key]
    value = os.path.expanduser(value)
    value = os.path.abspath(value)
    assert os.path.exists(value)
    config[key] = value
    return

def load_and_validate_comfig():
    with open("config.json", 'r') as f:
        config = json.load(f)
        validate_and_canoncalize_config_path(config, "LLVM_BUILD_DIR")
        assert "LLVM_BUILD_REVISION"  in config
        validate_and_canoncalize_config_path(config, "LLVM_SOURCE_DIR")
        validate_and_canoncalize_config_path(config, "CORPUS_DIR")
        return config

