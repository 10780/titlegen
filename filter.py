"""
Filtering functionality for the title generator.
Provides various filter methods for narrowing down titles.
"""

from typing import Set, List, Callable, Optional
from dataclasses import dataclass
import string


@dataclass
class FilterCriteria:
    """Represents a single filter criterion."""
    name: str
    description: str
    filter_func: Callable[[str], bool]


def filter_by_length(titles: Set[str], min_len: int = 0, max_len: int = 999) -> List[str]:
    """
    Filter titles by length range.
    
    Args:
        titles: Set of titles to filter
        min_len: Minimum length (inclusive)
        max_len: Maximum length (inclusive)
        
    Returns:
        Sorted list of matching titles
    """
    return sorted([t for t in titles if min_len <= len(t) <= max_len])


def filter_alpha_only(titles: Set[str]) -> List[str]:
    """
    Filter to titles containing only alphabetic characters.
    
    Args:
        titles: Set of titles to filter
        
    Returns:
        Sorted list of matching titles
    """
    return sorted([t for t in titles if t.isalpha()])


def filter_numeric_only(titles: Set[str]) -> List[str]:
    """
    Filter to titles containing only numeric characters.
    
    Args:
        titles: Set of titles to filter
        
    Returns:
        Sorted list of matching titles
    """
    return sorted([t for t in titles if t.isdigit()])


def filter_alphanumeric_only(titles: Set[str]) -> List[str]:
    """
    Filter to titles containing only alphanumeric characters.
    
    Args:
        titles: Set of titles to filter
        
    Returns:
        Sorted list of matching titles
    """
    return sorted([t for t in titles if t.isalnum()])


def filter_has_digits(titles: Set[str]) -> List[str]:
    """
    Filter to titles that contain at least one digit.
    
    Args:
        titles: Set of titles to filter
        
    Returns:
        Sorted list of matching titles
    """
    return sorted([t for t in titles if any(c.isdigit() for c in t)])


def filter_no_digits(titles: Set[str]) -> List[str]:
    """
    Filter to titles that contain no digits.
    
    Args:
        titles: Set of titles to filter
        
    Returns:
        Sorted list of matching titles
    """
    return sorted([t for t in titles if not any(c.isdigit() for c in t)])


def filter_has_letters(titles: Set[str]) -> List[str]:
    """
    Filter to titles that contain at least one letter.
    
    Args:
        titles: Set of titles to filter
        
    Returns:
        Sorted list of matching titles
    """
    return sorted([t for t in titles if any(c.isalpha() for c in t)])


def filter_uppercase_only(titles: Set[str]) -> List[str]:
    """
    Filter to titles containing only uppercase letters (and possibly numbers).
    
    Args:
        titles: Set of titles to filter
        
    Returns:
        Sorted list of matching titles
    """
    def is_upper_or_digit(s: str) -> bool:
        return all(c.isupper() or c.isdigit() for c in s) and any(c.isupper() for c in s)
    
    return sorted([t for t in titles if is_upper_or_digit(t)])


def filter_lowercase_only(titles: Set[str]) -> List[str]:
    """
    Filter to titles containing only lowercase letters (and possibly numbers).
    
    Args:
        titles: Set of titles to filter
        
    Returns:
        Sorted list of matching titles
    """
    def is_lower_or_digit(s: str) -> bool:
        return all(c.islower() or c.isdigit() for c in s) and any(c.islower() for c in s)
    
    return sorted([t for t in titles if is_lower_or_digit(t)])


def filter_mixed_case(titles: Set[str]) -> List[str]:
    """
    Filter to titles containing both uppercase and lowercase letters.
    
    Args:
        titles: Set of titles to filter
        
    Returns:
        Sorted list of matching titles
    """
    def has_mixed_case(s: str) -> bool:
        has_upper = any(c.isupper() for c in s)
        has_lower = any(c.islower() for c in s)
        return has_upper and has_lower
    
    return sorted([t for t in titles if has_mixed_case(t)])


def filter_has_special(titles: Set[str]) -> List[str]:
    """
    Filter to titles containing special (non-alphanumeric) characters.
    
    Args:
        titles: Set of titles to filter
        
    Returns:
        Sorted list of matching titles
    """
    return sorted([t for t in titles if not t.isalnum()])


def filter_no_special(titles: Set[str]) -> List[str]:
    """
    Filter to titles containing no special characters.
    
    Args:
        titles: Set of titles to filter
        
    Returns:
        Sorted list of matching titles
    """
    return sorted([t for t in titles if t.isalnum()])


def filter_unique_chars(titles: Set[str], min_unique: int = 1, max_unique: int = 999) -> List[str]:
    """
    Filter titles by number of unique characters.
    
    Args:
        titles: Set of titles to filter
        min_unique: Minimum unique characters
        max_unique: Maximum unique characters
        
    Returns:
        Sorted list of matching titles
    """
    return sorted([t for t in titles if min_unique <= len(set(t)) <= max_unique])


def filter_no_repeating_chars(titles: Set[str]) -> List[str]:
    """
    Filter to titles with no repeating characters.
    
    Args:
        titles: Set of titles to filter
        
    Returns:
        Sorted list of matching titles
    """
    return sorted([t for t in titles if len(t) == len(set(t))])


def filter_has_repeating_chars(titles: Set[str]) -> List[str]:
    """
    Filter to titles with at least one repeating character.
    
    Args:
        titles: Set of titles to filter
        
    Returns:
        Sorted list of matching titles
    """
    return sorted([t for t in titles if len(t) != len(set(t))])


def filter_by_charset(titles: Set[str], allowed_chars: str) -> List[str]:
    """
    Filter titles to only those using characters from allowed set.
    
    Args:
        titles: Set of titles to filter
        allowed_chars: String of allowed characters
        
    Returns:
        Sorted list of matching titles
    """
    allowed_set = set(allowed_chars)
    return sorted([t for t in titles if set(t).issubset(allowed_set)])


def filter_excludes_chars(titles: Set[str], excluded_chars: str) -> List[str]:
    """
    Filter titles to those not containing any excluded characters.
    
    Args:
        titles: Set of titles to filter
        excluded_chars: String of characters to exclude
        
    Returns:
        Sorted list of matching titles
    """
    excluded_set = set(excluded_chars)
    return sorted([t for t in titles if not excluded_set.intersection(set(t))])


def apply_filters(titles: Set[str], filters: List[FilterCriteria]) -> List[str]:
    """
    Apply multiple filter criteria sequentially.
    
    Args:
        titles: Set of titles to filter
        filters: List of FilterCriteria to apply
        
    Returns:
        Sorted list of titles matching all filters
    """
    result = list(titles)
    
    for criteria in filters:
        result = [t for t in result if criteria.filter_func(t)]
    
    return sorted(result)


# Predefined filter presets
FILTER_PRESETS = {
    "alpha": FilterCriteria("Alphabetic only", "Contains only letters", str.isalpha),
    "numeric": FilterCriteria("Numeric only", "Contains only numbers", str.isdigit),
    "alnum": FilterCriteria("Alphanumeric", "Contains only letters and numbers", str.isalnum),
    "upper": FilterCriteria("Uppercase", "Contains only uppercase letters", lambda s: s.isupper() and s.isalpha()),
    "lower": FilterCriteria("Lowercase", "Contains only lowercase letters", lambda s: s.islower() and s.isalpha()),
    "has_digit": FilterCriteria("Has digits", "Contains at least one digit", lambda s: any(c.isdigit() for c in s)),
    "no_digit": FilterCriteria("No digits", "Contains no digits", lambda s: not any(c.isdigit() for c in s)),
    "unique": FilterCriteria("Unique chars", "All characters are unique", lambda s: len(s) == len(set(s))),
    "repeating": FilterCriteria("Has repeats", "Has repeating characters", lambda s: len(s) != len(set(s))),
}


def get_available_filters() -> dict:
    """Get dictionary of available filter presets."""
    return {name: (f.name, f.description) for name, f in FILTER_PRESETS.items()}


def apply_preset_filter(titles: Set[str], preset_name: str) -> List[str]:
    """
    Apply a predefined filter preset.
    
    Args:
        titles: Set of titles to filter
        preset_name: Name of the preset filter
        
    Returns:
        Sorted list of matching titles
        
    Raises:
        ValueError: If preset name is not recognized
    """
    if preset_name not in FILTER_PRESETS:
        available = ", ".join(FILTER_PRESETS.keys())
        raise ValueError(f"Unknown filter preset: {preset_name}. Available: {available}")
    
    criteria = FILTER_PRESETS[preset_name]
    return sorted([t for t in titles if criteria.filter_func(t)])
