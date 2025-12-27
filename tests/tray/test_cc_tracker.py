"""Tests for CC tracking and TGI extraction."""

import struct
import tempfile
from pathlib import Path

from s4lt.tray.cc_tracker import extract_tgis_from_binary, TGI


def create_mock_binary_with_tgis(tgis: list[tuple[int, int, int]]) -> bytes:
    """Create mock binary data containing TGI references."""
    data = bytearray()
    # Header padding
    data.extend(b"\x00" * 32)

    for type_id, group_id, instance_id in tgis:
        # TGI format: type(4) + group(4) + instance(8) = 16 bytes
        data.extend(struct.pack("<I", type_id))
        data.extend(struct.pack("<I", group_id))
        data.extend(struct.pack("<Q", instance_id))

    # Footer padding
    data.extend(b"\x00" * 32)
    return bytes(data)


def test_extract_tgis_finds_patterns():
    """Should extract TGI patterns from binary data."""
    test_tgis = [
        (0x034AEECB, 0, 12345678901234),  # CAS part
        (0x319E4F1D, 0, 98765432109876),  # Object
    ]

    data = create_mock_binary_with_tgis(test_tgis)

    with tempfile.NamedTemporaryFile(suffix=".householdbinary", delete=False) as f:
        f.write(data)
        path = Path(f.name)

    try:
        extracted = extract_tgis_from_binary(path)

        # Should find our TGIs
        instance_ids = {tgi.instance_id for tgi in extracted}
        assert 12345678901234 in instance_ids
        assert 98765432109876 in instance_ids
    finally:
        path.unlink()


def test_tgi_dataclass():
    """TGI should have expected properties."""
    tgi = TGI(type_id=100, group_id=0, instance_id=12345)

    assert tgi.type_id == 100
    assert tgi.group_id == 0
    assert tgi.instance_id == 12345
