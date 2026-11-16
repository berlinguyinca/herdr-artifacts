"""Start coverage.py in a child interpreter.

Every meaningful test in this suite runs a shipped script with ``subprocess``, so a
plain ``coverage run -m pytest`` traces only the parent and collects nothing -- the
merged tree said ``No data was collected`` and ``No data to report``. The documented
fix is this file plus ``COVERAGE_PROCESS_START``: ``site`` imports ``sitecustomize`` at
interpreter start-up, and ``process_startup`` begins tracing only when that variable
names a config file, so an ordinary ``python3`` invocation on a developer machine is
untouched.

This lives in ``ci/coverage`` and is carried into children with ``PYTHONPATH``.
Deliberately NOT inside ``tests/``: pytest puts that directory on ``sys.path`` after
start-up, so ``site`` would never import it, and a file named ``sitecustomize.py``
sitting in the test directory invites someone to import it directly.

Failures are written to ``COVERAGE_HOOK_REPORT`` (one line per problem) instead of
stderr. Two reasons, both measured:

* some tests assert on what a script wrote to stderr, and a hook that talks there can
  break a test that has nothing to do with coverage;
* more importantly, stderr written by a *passing* test never reaches the suite log --
  pytest shows captured output only for failures. A hook complaining on stderr about a
  child interpreter that has no coverage module is a hook complaining to nobody, and the
  run reports 0 data as a percentage. The file is what ``scripts/run-coverage.sh`` reads.
"""

import os
import sys


def _report(problem):
    """Record one hook problem. Never raises: a measurement hook must not break the
    program it is measuring."""
    path = os.environ.get("COVERAGE_HOOK_REPORT")
    line = "pid=%d config=%s %s\n" % (
        os.getpid(),
        os.environ.get("COVERAGE_PROCESS_START", "<unset>"),
        problem,
    )
    if not path:
        sys.stderr.write("coverage-hook (no COVERAGE_HOOK_REPORT set): " + line)
        return
    try:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(line)
    except OSError as exc:  # last resort, so the problem is visible somewhere
        sys.stderr.write("coverage-hook (cannot write %s: %s): %s" % (path, exc, line))


try:
    import coverage
except ImportError as exc:
    _report("this interpreter has no coverage module, so it was not measured: %s" % exc)
else:
    try:
        coverage.process_startup()
    except Exception as exc:  # pylint: disable=broad-except
        # Including the case where the child's interpreter loaded a coverage it cannot
        # run: silent would look like "that script was exercised and measured".
        _report("coverage.process_startup() failed: %r" % exc)
