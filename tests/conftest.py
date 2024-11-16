# conftest.py
"""
Pytest auto configuration.

This module is run automatically by pytest to define and enable fixtures.
"""

import warnings

import pytest


@pytest.fixture(autouse=True)
def set_warnings():
    """
    Enable the default warning filter. It enables showing these warnings:
    - DeprecationWarning
    - ImportWarning
    - PendingDeprecationWarning
    - ResourceWarning

    The ResourceWarning helps to catch e.g. unclosed files:
    https://docs.python.org/3/library/devmode.html#resourcewarning-example

    One purpose of this fixture that with it, we can globally enable
    Development Mode (https://docs.python.org/3/library/devmode.html)
    using setenv:PYTHONDEVMODE=yes in tox.ini which enables further
    run-time checking during tests.

    Using setenv:PYTHONWARNINGS=ignore in tox.ini, we disable the Deprecation
    warnings caused by pytest plugins. This fixture still enable the default
    warning filter to have e.g. ResourceWarning checks enabled.

    Another nice effect is that also during interactive pytest use, the
    default warning filter also provides checking of ResourceWarning:
    """
    warnings.simplefilter("default")
