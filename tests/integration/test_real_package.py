"""Integration tests with real .package files.

These tests are skipped if TEST_PACKAGE_PATH env var is not set.
Set it to a path to a real Sims 4 .package file to run these tests.

Example:
    TEST_PACKAGE_PATH=/path/to/mod.package pytest tests/integration/ -v
"""

import os
import pytest
from pathlib import Path

from s4lt.core import Package


# Skip all tests if no test package available
TEST_PACKAGE_PATH = os.environ.get("TEST_PACKAGE_PATH")

pytestmark = pytest.mark.skipif(
    not TEST_PACKAGE_PATH or not Path(TEST_PACKAGE_PATH).exists(),
    reason="TEST_PACKAGE_PATH not set or file doesn't exist"
)


def test_open_real_package():
    """Should open a real .package file."""
    with Package.open(TEST_PACKAGE_PATH) as pkg:
        assert pkg.version[0] == 2
        assert len(pkg.resources) > 0


def test_list_resources():
    """Should list all resources."""
    with Package.open(TEST_PACKAGE_PATH) as pkg:
        for resource in pkg.resources:
            assert resource.type_id > 0
            assert resource.instance_id >= 0


def test_extract_resources():
    """Should extract all resources without error."""
    with Package.open(TEST_PACKAGE_PATH) as pkg:
        for resource in pkg.resources[:10]:  # Test first 10
            data = resource.extract()
            assert len(data) == resource.uncompressed_size
