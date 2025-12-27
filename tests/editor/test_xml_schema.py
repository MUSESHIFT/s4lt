"""Tests for XML tuning schema validation."""

from s4lt.editor.xml_schema import validate_tuning, TuningError, get_tuning_type


def test_validate_well_formed_xml():
    """Well-formed XML should pass basic validation."""
    xml = '<I n="tuning" c="Buff" i="buff" m="buffs.buff" s="12345"></I>'
    errors = validate_tuning(xml)
    assert not any(e.level == "error" for e in errors)


def test_validate_malformed_xml():
    """Malformed XML should return error."""
    xml = '<I n="tuning"><missing close tag>'
    errors = validate_tuning(xml)
    assert any(e.level == "error" for e in errors)


def test_get_tuning_type():
    """Should extract tuning type from XML."""
    xml = '<I n="tuning" c="Buff" i="buff" m="buffs.buff" s="12345"></I>'
    tuning_type = get_tuning_type(xml)
    assert tuning_type == "Buff"
