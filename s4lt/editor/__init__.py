"""S4LT Package Editor."""

from s4lt.editor.session import EditSession, get_session, close_session, list_sessions
from s4lt.editor.stbl import STBLEntry, parse_stbl, build_stbl, stbl_to_text, text_to_stbl
from s4lt.editor.xml_schema import validate_tuning, get_tuning_type, format_xml
from s4lt.editor.merge import find_conflicts, merge_packages, MergeConflict
from s4lt.editor.split import split_by_type, split_by_group, extract_all
from s4lt.editor.preview import can_preview, get_preview_png

__all__ = [
    # Session
    "EditSession",
    "get_session",
    "close_session",
    "list_sessions",
    # STBL
    "STBLEntry",
    "parse_stbl",
    "build_stbl",
    "stbl_to_text",
    "text_to_stbl",
    # XML
    "validate_tuning",
    "get_tuning_type",
    "format_xml",
    # Merge
    "find_conflicts",
    "merge_packages",
    "MergeConflict",
    # Split
    "split_by_type",
    "split_by_group",
    "extract_all",
    # Preview
    "can_preview",
    "get_preview_png",
]
