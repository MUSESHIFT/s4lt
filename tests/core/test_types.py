"""Tests for resource type registry."""

from s4lt.core.types import get_type_name, RESOURCE_TYPES


def test_known_type_returns_name():
    """Known type IDs should return human-readable names."""
    assert get_type_name(0x0333406C) == "Tuning"
    assert get_type_name(0x034AEECB) == "CASPart"
    assert get_type_name(0x220557DA) == "StringTable"


def test_unknown_type_returns_hex():
    """Unknown type IDs should return formatted hex string."""
    result = get_type_name(0x12345678)
    assert result == "Unknown_12345678"


def test_resource_types_dict_exists():
    """RESOURCE_TYPES should be a non-empty dict."""
    assert isinstance(RESOURCE_TYPES, dict)
    assert len(RESOURCE_TYPES) > 0
