import importlib

import pytest

import saltmarket


@pytest.mark.smoke
def test_version_is_set():
    assert saltmarket.__version__


@pytest.mark.smoke
@pytest.mark.parametrize("name", ["engine", "bots", "sim", "rl", "analysis"])
def test_subpackages_import(name):
    assert importlib.import_module(f"saltmarket.{name}")
