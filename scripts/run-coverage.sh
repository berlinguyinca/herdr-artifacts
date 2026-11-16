#!/usr/bin/env bash
# run-coverage.sh -- measure the shipped Python, which the suite only ever runs as a
# child process, and gate it on a floor that a real run produced.
#
# Why a script instead of four lines in the workflow: the measurement is only honest if
# four things are all true at once, and a workflow step that checks one of them silently
# reports a percentage that means nothing --
#   1. children started with the hook (tests/conftest.py writes the config it points at),
#   2. at least one parallel data file was actually written,
#   3. the combined data has a row for the shipped script,
#   4. no child said it could not start coverage (they write .coverage-data/hook-errors.log,
#      where nothing else in a passing run would ever look at it).
# Absent any of those, `coverage report` prints 0% or "No data to report", and a
# `--fail-under=0` would call that green. This script fails on each one by name.
#
# What it does NOT measure, stated rather than hidden: skill/herdr-artifact/scripts/herdr-artifact
# is POSIX sh and install/install.sh is shell. coverage.py cannot describe them; the
# gate for those two is `sh -n` plus the subprocess tests that assert their behaviour.
# So the number below is the Python MCP server only, and the workflow says so.
#
# Floor: 90, measured on the merged tree (365 statements, 38 missed) by this script.
# Raise it when the tests get better; lower it only with the reason in the commit.
set -euo pipefail

FLOOR=90
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
DATA_DIR=".coverage-data"
DATA_FILE="$DATA_DIR/.coverage"
SUITE_LOG="${SUITE_LOG:-$DATA_DIR/suite.log}"

say(){ printf '\n=== %s ===\n' "$*"; }

say "toolchain"
if ! "$PYTHON" -m coverage --version >/dev/null 2>&1; then
  echo "FAIL: $PYTHON has no coverage module. Install the pinned test deps:"
  echo "      $PYTHON -m pip install -r requirements-dev.txt"
  exit 1
fi
"$PYTHON" -m coverage --version

say "suite (children are measured; see tests/coverage_bootstrap.py)"
mkdir -p "$DATA_DIR"
# Cleared here, not only in conftest: if tests/conftest.py never loads, the run that
# follows must not inherit the previous run's data or the previous run's hook complaints.
# Measured -- a stale hook-errors.log made a conftest-less run look like 76 children had
# just failed to start coverage.
rm -f "$DATA_DIR"/.coverage "$DATA_DIR"/.coverage.* "$DATA_DIR/hook-errors.log"
set +e
"$PYTHON" -m pytest tests -q -rs 2>&1 | tee "$SUITE_LOG"
suite_rc=${PIPESTATUS[0]}
set -e
if [ "$suite_rc" -ne 0 ]; then
  echo "FAIL: the suite itself failed (exit $suite_rc); a coverage number would be about a partial run."
  exit "$suite_rc"
fi

say "measurement present"
# A child whose interpreter cannot start coverage writes one line here (see
# ci/coverage/sitecustomize.py for why it is a file and not stderr: a passing test's
# child stderr never reaches the suite log, so stderr would be a complaint to nobody).
HOOK_REPORT="$DATA_DIR/hook-errors.log"
if [ ! -f "$HOOK_REPORT" ]; then
  echo "FAIL: $HOOK_REPORT is missing, so no child was able to report a hook problem."
  echo "      tests/conftest.py creates it before any child starts; if pytest did not load"
  echo "      tests/conftest.py, nothing here is being measured."
  exit 1
fi
if [ -s "$HOOK_REPORT" ]; then
  echo "FAIL: $(wc -l < "$HOOK_REPORT") child interpreter(s) could not start coverage:"
  cat "$HOOK_REPORT"
  echo "      Those children ran unmeasured, so the percentage below describes fewer lines"
  echo "      than the suite exercised. Usually the child's interpreter differs from the"
  echo "      one running pytest, or requirements-dev.txt is not installed into it."
  exit 1
fi
echo "ok: no child reported a coverage hook problem"

shopt -s nullglob
partials=("$DATA_DIR"/.coverage.*)
shopt -u nullglob
if [ "${#partials[@]}" -eq 0 ]; then
  echo "FAIL: no parallel data file was written to $DATA_DIR, so nothing was measured."
  echo "      Either no shipped Python ran as a child, or COVERAGE_PROCESS_START never reached it."
  exit 1
fi
echo "ok: ${#partials[@]} child data files written"

say "combine"
"$PYTHON" -m coverage combine --data-file="$DATA_FILE"

say "report (floor: ${FLOOR}%)"
# A report with no row for the shipped script would total 0 statements and pass any
# threshold, which is the second way this measurement could go quietly vacuous.
report=$("$PYTHON" -m coverage report --data-file="$DATA_FILE" --show-missing)
echo "$report"
if ! echo "$report" | grep -q "herdr-artifact-mcp"; then
  echo "FAIL: the report has no row for skill/herdr-artifact/scripts/herdr-artifact-mcp."
  echo "      The measurement measured something other than what this repo ships."
  exit 1
fi
"$PYTHON" -m coverage report --data-file="$DATA_FILE" --fail-under="$FLOOR" >/dev/null

cat <<'NOTE'

Measured: the Python MCP server, exercised through subprocess as users run it.
Not measured: the POSIX sh wrapper and install/install.sh -- coverage.py has no
language for shell. They are gated by `sh -n` and by the subprocess tests instead.
NOTE

echo "PASS: coverage above ${FLOOR}% with the measurement itself checked"
