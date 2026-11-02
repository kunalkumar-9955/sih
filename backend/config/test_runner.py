"""
RouteIQ / SIH26002 — Test Runner bridging Django manage.py test to the pytest suite.
Ensures that running `python manage.py test` discovers and executes all unit and integration tests.
"""
import os
import sys
import pytest


class PytestTestRunner:
    """Runs the project's pytest test suite from manage.py test."""

    def __init__(self, verbosity=1, failfast=False, keepdb=False, **kwargs):
        self.verbosity = verbosity
        self.failfast = failfast
        self.keepdb = keepdb

    @classmethod
    def add_arguments(cls, parser):
        pass

    def run_tests(self, test_labels, extra_tests=None, **kwargs):
        args = ["--reuse-db"]
        if self.verbosity > 1:
            args.append("-v")
        if self.failfast:
            args.append("-x")

        if test_labels:
            for label in test_labels:
                # Convert module path if needed
                if os.path.exists(label):
                    args.append(label)
                else:
                    path_label = label.replace(".", "/")
                    if os.path.exists(path_label):
                        args.append(path_label)
                    elif os.path.exists(f"apps/{path_label}"):
                        args.append(f"apps/{path_label}")
                    else:
                        args.append(label)

        return int(pytest.main(args))
