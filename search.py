"""
Search functionality for the title generator.
Provides various search methods for finding titles.
"""

from typing import Set, List, Optional
import re


def search_contains(titles: Set[str], query: str, case_sensitive: bool = False) -> List[str]:
    """
    Search for titles containing a substring.
    
    Args:
        titles: Set of titles to search
        query: Substring to search for
        case_sensitive: Whether search is case-sensitive
        
    Returns:
        Sorted list of matching titles
    """
    if not query:
        return sorted(titles)
    
    if case_sensitive:
        matches = [t for t in titles if query in t]
    else:
        query_upper = query.upper()
        matches = [t for t in titles if query_upper in t.upper()]
    
    return sorted(matches)


def search_starts_with(titles: Set[str], prefix: str, case_sensitive: bool = False) -> List[str]:
    """
    Search for titles starting with a prefix.
    
    Args:
        titles: Set of titles to search
        prefix: Prefix to search for
        case_sensitive: Whether search is case-sensitive
        
    Returns:
        Sorted list of matching titles
    """
    if not prefix:
        return sorted(titles)
    
    if case_sensitive:
        matches = [t for t in titles if t.startswith(prefix)]
    else:
        prefix_upper = prefix.upper()
        matches = [t for t in titles if t.upper().startswith(prefix_upper)]
    
    return sorted(matches)


def search_ends_with(titles: Set[str], suffix: str, case_sensitive: bool = False) -> List[str]:
    """
    Search for titles ending with a suffix.
    
    Args:
        titles: Set of titles to search
        suffix: Suffix to search for
        case_sensitive: Whether search is case-sensitive
        
    Returns:
        Sorted list of matching titles
    """
    if not suffix:
        return sorted(titles)
    
    if case_sensitive:
        matches = [t for t in titles if t.endswith(suffix)]
    else:
        suffix_upper = suffix.upper()
        matches = [t for t in titles if t.upper().endswith(suffix_upper)]
    
    return sorted(matches)


def search_regex(titles: Set[str], pattern: str, case_sensitive: bool = False) -> List[str]:
    """
    Search for titles matching a regex pattern.
    
    Args:
        titles: Set of titles to search
        pattern: Regex pattern to match
        case_sensitive: Whether search is case-sensitive
        
    Returns:
        Sorted list of matching titles
        
    Raises:
        ValueError: If the regex pattern is invalid
    """
    if not pattern:
        return sorted(titles)
    
    try:
        flags = 0 if case_sensitive else re.IGNORECASE
        compiled = re.compile(pattern, flags)
        matches = [t for t in titles if compiled.search(t)]
        return sorted(matches)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern: {e}")


def search_exact(titles: Set[str], query: str, case_sensitive: bool = False) -> List[str]:
    """
    Search for exact title matches.
    
    Args:
        titles: Set of titles to search
        query: Exact title to find
        case_sensitive: Whether search is case-sensitive
        
    Returns:
        List containing the match if found, empty otherwise
    """
    if not query:
        return []
    
    if case_sensitive:
        return [query] if query in titles else []
    else:
        query_upper = query.upper()
        matches = [t for t in titles if t.upper() == query_upper]
        return sorted(matches)


def search_length(titles: Set[str], length: int) -> List[str]:
    """
    Search for titles of a specific length.
    
    Args:
        titles: Set of titles to search
        length: Exact length to match
        
    Returns:
        Sorted list of matching titles
    """
    matches = [t for t in titles if len(t) == length]
    return sorted(matches)


def search_length_range(titles: Set[str], min_length: int = 0, max_length: int = 999) -> List[str]:
    """
    Search for titles within a length range.
    
    Args:
        titles: Set of titles to search
        min_length: Minimum length (inclusive)
        max_length: Maximum length (inclusive)
        
    Returns:
        Sorted list of matching titles
    """
    matches = [t for t in titles if min_length <= len(t) <= max_length]
    return sorted(matches)


def search_chars_only(titles: Set[str], allowed_chars: str) -> List[str]:
    """
    Search for titles containing only specific characters.
    
    Args:
        titles: Set of titles to search
        allowed_chars: String of allowed characters
        
    Returns:
        Sorted list of matching titles
    """
    if not allowed_chars:
        return []
    
    allowed_set = set(allowed_chars)
    matches = [t for t in titles if set(t).issubset(allowed_set)]
    return sorted(matches)


def search_chars_any(titles: Set[str], chars: str) -> List[str]:
    """
    Search for titles containing any of the specified characters.
    
    Args:
        titles: Set of titles to search
        chars: String of characters to look for
        
    Returns:
        Sorted list of matching titles
    """
    if not chars:
        return sorted(titles)
    
    char_set = set(chars)
    matches = [t for t in titles if char_set.intersection(set(t))]
    return sorted(matches)


def search_chars_all(titles: Set[str], chars: str) -> List[str]:
    """
    Search for titles containing all of the specified characters.
    
    Args:
        titles: Set of titles to search
        chars: String of characters that must all be present
        
    Returns:
        Sorted list of matching titles
    """
    if not chars:
        return sorted(titles)
    
    char_set = set(chars)
    matches = [t for t in titles if char_set.issubset(set(t))]
    return sorted(matches)


class SearchResult:
    """Container for search results with metadata."""
    
    def __init__(self, matches: List[str], query: str, search_type: str, total_searched: int):
        self.matches = matches
        self.query = query
        self.search_type = search_type
        self.total_searched = total_searched
        self.match_count = len(matches)
    
    def __len__(self) -> int:
        return self.match_count
    
    def __bool__(self) -> bool:
        return self.match_count > 0
    
    def __iter__(self):
        return iter(self.matches)
    
    def summary(self) -> str:
        """Get a summary string of the search results."""
        return f"Found {self.match_count} of {self.total_searched} titles matching '{self.query}' ({self.search_type})"


def perform_search(
    titles: Set[str],
    query: str,
    search_type: str = "contains",
    case_sensitive: bool = False
) -> SearchResult:
    """
    Perform a search with the specified type.
    
    Args:
        titles: Set of titles to search
        query: Search query
        search_type: Type of search (contains, starts, ends, regex, exact)
        case_sensitive: Whether search is case-sensitive
        
    Returns:
        SearchResult object with matches and metadata
    """
    search_functions = {
        "contains": search_contains,
        "starts": search_starts_with,
        "ends": search_ends_with,
        "regex": search_regex,
        "exact": search_exact,
    }
    
    if search_type not in search_functions:
        raise ValueError(f"Unknown search type: {search_type}. Valid types: {', '.join(search_functions.keys())}")
    
    matches = search_functions[search_type](titles, query, case_sensitive)
    
    return SearchResult(
        matches=matches,
        query=query,
        search_type=search_type,
        total_searched=len(titles)
    )
