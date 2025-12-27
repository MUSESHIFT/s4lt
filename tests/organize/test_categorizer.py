"""Tests for mod categorizer."""

from s4lt.organize.categorizer import ModCategory, TYPE_TO_CATEGORY, CATEGORY_PRIORITY


def test_mod_category_enum_values():
    """ModCategory should have all expected values."""
    assert ModCategory.CAS.value == "CAS"
    assert ModCategory.BUILD_BUY.value == "BuildBuy"
    assert ModCategory.SCRIPT.value == "Script"
    assert ModCategory.TUNING.value == "Tuning"
    assert ModCategory.OVERRIDE.value == "Override"
    assert ModCategory.GAMEPLAY.value == "Gameplay"
    assert ModCategory.UNKNOWN.value == "Unknown"


def test_type_to_category_cas():
    """CASPart type should map to CAS category."""
    assert TYPE_TO_CATEGORY.get(0x034AEECB) == ModCategory.CAS


def test_type_to_category_buildbuy():
    """ObjectCatalog type should map to BUILD_BUY category."""
    assert TYPE_TO_CATEGORY.get(0x319E4F1D) == ModCategory.BUILD_BUY


def test_type_to_category_script():
    """Python bytecode type should map to SCRIPT category."""
    assert TYPE_TO_CATEGORY.get(0x9C07855E) == ModCategory.SCRIPT


def test_category_priority_script_highest():
    """SCRIPT should have highest priority."""
    assert CATEGORY_PRIORITY[ModCategory.SCRIPT] > CATEGORY_PRIORITY[ModCategory.CAS]
    assert CATEGORY_PRIORITY[ModCategory.SCRIPT] > CATEGORY_PRIORITY[ModCategory.BUILD_BUY]
