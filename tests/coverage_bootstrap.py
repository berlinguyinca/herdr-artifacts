"""Wire coverage.py through the subprocess boundary this suite cannot avoid.

What the repo ships is two extensionless scripts -- a POSIX sh wrapper and a Python
MCP server -- and the tests drive them with ``subprocess.run``. A percentage measured
in the parent process is therefore fiction: on the merged tree ``coverage run -m
pytest`` reported ``No data was collected`` and ``No data to report``.

The pieces, and why each exists:

``ci/coverage/sitecustomize.py``
    imported by ``site`` in every child interpreter; calls ``process_startup()``.
``.coverage-process.ini`` (generated here, gitignored)
    the file ``COVERAGE_PROCESS_START`` names. It is written at run time with absolute
    paths because children run with ``cwd`` inside a ``TemporaryDirectory``: a relative
    ``source`` in a committed config would resolve against that temporary directory and
    match nothing, which is the quiet way this measurement becomes zero data plus a
    green run.
``.coverage-data/`` (gitignored)
    where children drop their parallel data files. ``data_file`` is absolute for the
    same reason as ``source`` -- otherwise each child writes into its own temporary
    directory and ``coverage combine`` finds nothing to combine.

``forward()`` is the only bridge across the deliberately hermetic environments several
tests build (``env = {"HOME": ..., "PATH": ...}``, no inheritance, so a host
``herdr-eng`` cannot leak in). Those dictionaries would otherwise drop ``PYTHONPATH``
and the two coverage variables, and the drop would be invisible: the test passes, the
child is simply not measured.

Not measured, and not pretending to be: the sh wrapper and ``install/install.sh`` are
not Python, so no percentage describes them. The source list is the shipped Python,
and the harness that runs it asserts a row exists for it -- see scripts/run-coverage.sh.
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK_DIR = ROOT / "ci" / "coverage"
CONFIG_PATH = ROOT / ".coverage-process.ini"
DATA_DIR = ROOT / ".coverage-data"
DATA_FILE = DATA_DIR / ".coverage"

#: Where a child records that it could not start coverage. It is a file, not stderr,
#: because a passing test's child stderr never reaches the suite log: pytest prints
#: captured output for failures only. See ci/coverage/sitecustomize.py.
HOOK_REPORT = DATA_DIR / "hook-errors.log"

#: The shipped Python, as a directory: coverage records the absolute path each child
#: executed, and every child here runs a script from this directory.
PYTHON_SOURCE = ROOT / "skill" / "herdr-artifact" / "scripts"

#: The only variables allowed to cross a hermetic child environment. Each is inert
#: without the others: COVERAGE_PROCESS_START names the config, COVERAGE_FILE says
#: where to write, PYTHONPATH carries the hook (and, on a runner whose child PATH is
#: pinned to /usr/bin:/bin, the coverage package itself), COVERAGE_HOOK_REPORT says where
#: a child that could not start coverage says so.
FORWARDED = ("COVERAGE_PROCESS_START", "COVERAGE_FILE", "PYTHONPATH", "COVERAGE_HOOK_REPORT")


def configure():
    """Point the children at a measurement config with absolute paths.

    Called from ``tests/conftest.py`` at session start, so a plain ``pytest tests``
    measures the same thing in CI and on a laptop. Returns the config path.
    """
    DATA_DIR.mkdir(exist_ok=True)
    # Fresh per run: a leftover line from an earlier session would fail the next run for a
    # reason that is no longer true. scripts/run-coverage.sh clears it too, because this
    # function only runs when pytest loaded tests/conftest.py at all.
    HOOK_REPORT.write_text("")
    # The child interpreters that tests exec are not always the one running pytest:
    # Env.run pins PATH to /usr/bin:/bin so the host's herdr-eng cannot leak in, which
    # also pins the interpreter. Importing coverage from a different Python works (it
    # falls back to the pure-Python tracer when its C extension does not load), so the
    # package directory travels with the hook instead of the child going unmeasured.
    import coverage

    # The *parent* of the package directory, never the package directory itself: putting
    # site-packages/coverage on PYTHONPATH makes its modules top-level, and the first
    # `import types` in a child then lands on coverage/types.py instead of the standard
    # library and dies with
    #   ImportError: cannot import name 'GenericAlias' from partially initialized module 'types'
    # which is how this line was measured.
    site_packages = Path(coverage.__file__).resolve().parent.parent
    entries = [str(HOOK_DIR), str(site_packages)]
    inherited = os.environ.get("PYTHONPATH", "")
    python_path = os.pathsep.join(entries + ([inherited] if inherited else []))

    CONFIG_PATH.write_text(
        "[run]\n"
        f"source = {PYTHON_SOURCE}\n"
        f"data_file = {DATA_FILE}\n"
        "parallel = True\n"
    )
    os.environ["COVERAGE_PROCESS_START"] = str(CONFIG_PATH)
    os.environ["COVERAGE_FILE"] = str(DATA_FILE)
    os.environ["COVERAGE_HOOK_REPORT"] = str(HOOK_REPORT)
    os.environ["PYTHONPATH"] = python_path
    return CONFIG_PATH


def forward(env):
    """Return ``env`` with the coverage bootstrap added, if a measurement is running.

    ``env`` is a dict a test built from scratch -- hermetic on purpose. Only the names
    in ``FORWARDED`` cross; a child that must not see the host environment still does
    not see it. With no measurement running this returns the dict unchanged, so the
    hermetic tests are the same tests with or without the gate.
    """
    for name in FORWARDED:
        value = os.environ.get(name)
        if value is not None:
            env[name] = value
    return env


def clear():
    """Remove data from a previous run so a stale file cannot look like new data.

    Only ``.coverage*`` names: the runner's own suite log lives in the same directory,
    and deleting it here would leave the check that reads it looking at nothing (which is
    how the first version of this was caught).
    """
    if DATA_DIR.is_dir():
        for stale in DATA_DIR.iterdir():
            if stale.name.startswith(".coverage"):
                stale.unlink()
