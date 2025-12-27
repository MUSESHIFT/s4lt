"""Tests for Resource class."""

import io
import pytest

from s4lt.core.resource import Resource
from s4lt.core.index import IndexEntry, COMPRESSION_NONE, COMPRESSION_ZLIB
from s4lt.core.types import get_type_name


def test_resource_properties():
    """Resource should expose index entry properties."""
    entry = IndexEntry(
        type_id=0x0333406C,
        group_id=0x00000000,
        instance_id=0x123456789ABCDEF0,
        offset=1000,
        compressed_size=500,
        uncompressed_size=1000,
        compression_type=COMPRESSION_ZLIB,
    )

    # Mock file
    file = io.BytesIO(b"\x00" * 2000)

    resource = Resource(entry, file)

    assert resource.type_id == 0x0333406C
    assert resource.type_name == "Tuning"
    assert resource.group_id == 0x00000000
    assert resource.instance_id == 0x123456789ABCDEF0
    assert resource.is_compressed == True
    assert resource.compressed_size == 500
    assert resource.uncompressed_size == 1000


def test_resource_extract_uncompressed():
    """Extracting uncompressed resource returns raw data."""
    raw_data = b"Hello, this is raw tuning data!"

    # Create file with data at offset 100
    file_data = b"\x00" * 100 + raw_data
    file = io.BytesIO(file_data)

    entry = IndexEntry(
        type_id=0x0333406C,
        group_id=0,
        instance_id=0,
        offset=100,
        compressed_size=len(raw_data),
        uncompressed_size=len(raw_data),
        compression_type=COMPRESSION_NONE,
    )

    resource = Resource(entry, file)
    result = resource.extract()

    assert result == raw_data


def test_resource_str():
    """Resource should have readable string representation."""
    entry = IndexEntry(
        type_id=0x0333406C,
        group_id=0x00000001,
        instance_id=0xABCDEF0123456789,
        offset=100,
        compressed_size=50,
        uncompressed_size=100,
        compression_type=COMPRESSION_ZLIB,
    )

    file = io.BytesIO(b"\x00" * 200)
    resource = Resource(entry, file)

    s = str(resource)
    assert "Tuning" in s
    assert "ABCDEF0123456789" in s.upper()
