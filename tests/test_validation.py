"""Tests for LCSC part number validation."""

import pytest
from bom_helper.main import validate_lcsc_part_number


def test_valid_part_numbers():
    """Test that valid LCSC part numbers pass validation."""
    valid_parts = [
        "C2040",
        "C124378",
        "C999999999",
        "C1",
        "C12345",
    ]

    for part in valid_parts:
        # Should not raise any exception
        validate_lcsc_part_number(part)


def test_invalid_part_numbers():
    """Test that invalid LCSC part numbers are rejected."""
    invalid_parts = [
        ("C:\\Users\\path", "Windows path"),
        ("C:\\path", "Windows path"),
        ("C123abc", "letters after digits"),
        ("C-123", "hyphen"),
        ("C 123", "space"),
        ("C", "just C without digits"),
        ("", "empty string"),
        ("123", "no C prefix"),
        ("c2040", "lowercase c"),
        ("CC2040", "double C"),
        ("C2040.1", "decimal point"),
        ("C2040-01", "hyphen"),
        ("C2040_01", "underscore"),
    ]

    for part, description in invalid_parts:
        with pytest.raises(ValueError, match="Invalid LCSC part number"):
            validate_lcsc_part_number(part)


def test_validation_error_message():
    """Test that validation error messages are helpful."""
    with pytest.raises(ValueError) as exc_info:
        validate_lcsc_part_number("C\\invalid")

    error_msg = str(exc_info.value)
    assert "Invalid LCSC part number" in error_msg
    assert "C\\invalid" in error_msg
    assert "C2040" in error_msg  # Example in error message
