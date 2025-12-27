"""Tests for mod sorter."""

from s4lt.organize.sorter import extract_creator, normalize_creator


def test_extract_creator_underscore():
    """extract_creator should parse underscore prefix."""
    assert extract_creator("SimsyCreator_CASHair.package") == "Simsycreator"


def test_extract_creator_ts4_prefix():
    """extract_creator should parse TS4 prefix."""
    assert extract_creator("TS4-Bobby-Dress.package") == "Bobby"
    assert extract_creator("TS4_Bobby_Dress.package") == "Bobby"


def test_extract_creator_dash():
    """extract_creator should parse dash prefix."""
    assert extract_creator("Creator-ModName.package") == "Creator"


def test_extract_creator_unknown():
    """extract_creator should return _Uncategorized for unknown patterns."""
    assert extract_creator("randomfile.package") == "_Uncategorized"


def test_normalize_creator():
    """normalize_creator should title case."""
    assert normalize_creator("SIMSY") == "Simsy"
    assert normalize_creator("simsy") == "Simsy"
    assert normalize_creator("SimsyCreator") == "Simsycreator"
