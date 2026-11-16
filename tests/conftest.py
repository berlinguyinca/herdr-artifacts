"""Session start-up shared by the whole suite.

Its one job today is coverage: this suite measures scripts that run as child
processes, and the config that tells a child to trace has to exist, with absolute
paths, before any child starts. See tests/coverage_bootstrap.py for why the paths have
to be absolute and why a child environment has to be asked, not assumed, to carry the
bootstrap.
"""

import importlib.util
import pathlib

_bootstrap = pathlib.Path(__file__).resolve().parent / "coverage_bootstrap.py"
_spec = importlib.util.spec_from_file_location("coverage_bootstrap", _bootstrap)
coverage_bootstrap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(coverage_bootstrap)


def pytest_configure(config):
    coverage_bootstrap.clear()
    coverage_bootstrap.configure()
