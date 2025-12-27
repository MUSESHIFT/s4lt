"""Tests for STBL parsing and editing."""

from s4lt.editor.stbl import parse_stbl, build_stbl, STBLEntry, stbl_to_text, text_to_stbl


def test_parse_stbl():
    """Parse a valid STBL."""
    # Minimal STBL: header + 1 entry
    stbl_data = build_test_stbl([
        STBLEntry(0x12345678, "Hello World"),
    ])

    entries = parse_stbl(stbl_data)

    assert len(entries) == 1
    assert entries[0].string_id == 0x12345678
    assert entries[0].text == "Hello World"


def test_build_stbl():
    """Build a valid STBL from entries."""
    entries = [
        STBLEntry(0x12345678, "Hello World"),
        STBLEntry(0x87654321, "Goodbye"),
    ]

    data = build_stbl(entries)
    parsed = parse_stbl(data)

    assert len(parsed) == 2
    assert parsed[0].text == "Hello World"
    assert parsed[1].text == "Goodbye"


def test_roundtrip():
    """Parse then build should produce equivalent data."""
    original_entries = [
        STBLEntry(0xAABBCCDD, "Test string one"),
        STBLEntry(0x11223344, "Test string two"),
    ]

    data = build_stbl(original_entries)
    parsed = parse_stbl(data)

    assert len(parsed) == len(original_entries)
    for orig, new in zip(original_entries, parsed):
        assert orig.string_id == new.string_id
        assert orig.text == new.text


def test_stbl_to_text():
    """Convert entries to text format."""
    entries = [STBLEntry(0x12345678, "Hello World")]
    text = stbl_to_text(entries)
    assert text == "0x12345678: Hello World"


def test_text_to_stbl():
    """Parse text format to entries."""
    entries = text_to_stbl("0x12345678: Hello World")
    assert len(entries) == 1
    assert entries[0].string_id == 0x12345678
    assert entries[0].text == "Hello World"


def test_text_roundtrip():
    """Text format roundtrip."""
    original = [STBLEntry(0xAABBCCDD, "Test")]
    text = stbl_to_text(original)
    parsed = text_to_stbl(text)
    assert parsed[0].string_id == original[0].string_id
    assert parsed[0].text == original[0].text


def build_test_stbl(entries: list) -> bytes:
    """Build test STBL data."""
    return build_stbl(entries)
