"""XML tuning schema validation."""

import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass
class ValidationIssue:
    """A validation issue found in tuning XML."""

    level: str  # "error", "warning", "info"
    message: str
    line: int | None = None


class TuningError(Exception):
    """Error in tuning XML."""

    pass


# Known tuning types and their required/optional elements
TUNING_SCHEMAS: dict[str, dict] = {
    "Buff": {
        "required": [],
        "optional": ["buff_type", "visible", "mood_type", "mood_weight"],
    },
    "Trait": {
        "required": [],
        "optional": ["trait_type", "display_name", "display_name_gender_neutral"],
    },
    "Interaction": {
        "required": [],
        "optional": ["display_name", "category", "target_type"],
    },
    "Object": {
        "required": [],
        "optional": ["tuning_id"],
    },
    "Snippet": {
        "required": [],
        "optional": [],
    },
}


def validate_tuning(xml_text: str) -> list[ValidationIssue]:
    """Validate tuning XML.

    Args:
        xml_text: XML string to validate

    Returns:
        List of validation issues found
    """
    issues = []

    # Check well-formedness
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        issues.append(ValidationIssue(
            level="error",
            message=f"Malformed XML: {e}",
            line=getattr(e, "position", (None,))[0],
        ))
        return issues

    # Check for tuning root element
    if root.tag != "I":
        issues.append(ValidationIssue(
            level="warning",
            message=f"Expected root element 'I', got '{root.tag}'",
        ))

    # Check for required attributes
    tuning_type = root.get("c")
    if not tuning_type:
        issues.append(ValidationIssue(
            level="warning",
            message="Missing 'c' (class) attribute on root element",
        ))

    # Schema-specific validation
    if tuning_type and tuning_type in TUNING_SCHEMAS:
        schema = TUNING_SCHEMAS[tuning_type]
        for required in schema["required"]:
            if root.find(f".//*[@n='{required}']") is None:
                issues.append(ValidationIssue(
                    level="warning",
                    message=f"Missing required element: {required}",
                ))

    return issues


def get_tuning_type(xml_text: str) -> str | None:
    """Extract tuning type from XML.

    Args:
        xml_text: XML string

    Returns:
        Tuning type (class name) or None
    """
    try:
        root = ET.fromstring(xml_text)
        return root.get("c")
    except ET.ParseError:
        return None


def get_autocomplete_suggestions(
    xml_text: str,
    cursor_position: int,
) -> list[str]:
    """Get autocomplete suggestions for current position.

    Args:
        xml_text: Current XML text
        cursor_position: Cursor position in text

    Returns:
        List of suggested tag/attribute names
    """
    # Basic implementation - can be enhanced
    suggestions = []

    tuning_type = get_tuning_type(xml_text)
    if tuning_type and tuning_type in TUNING_SCHEMAS:
        schema = TUNING_SCHEMAS[tuning_type]
        suggestions.extend(schema.get("required", []))
        suggestions.extend(schema.get("optional", []))

    # Common tuning elements
    suggestions.extend([
        "T", "V", "L", "U", "E",  # Common value types
    ])

    return sorted(set(suggestions))


def format_xml(xml_text: str, indent: int = 2) -> str:
    """Format/pretty-print XML.

    Args:
        xml_text: XML string
        indent: Indentation spaces

    Returns:
        Formatted XML
    """
    try:
        root = ET.fromstring(xml_text)
        _indent_element(root, level=0, indent=indent)
        return ET.tostring(root, encoding="unicode")
    except ET.ParseError:
        return xml_text  # Return original if can't parse


def _indent_element(elem: ET.Element, level: int, indent: int) -> None:
    """Add indentation to element tree."""
    i = "\n" + " " * (level * indent)
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + " " * indent
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for child in elem:
            _indent_element(child, level + 1, indent)
        if not child.tail or not child.tail.strip():
            child.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i
