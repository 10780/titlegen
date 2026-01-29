"""
Categorization functionality for the title generator.
Provides methods for organizing titles into categories.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Set, List, Dict, Optional, Any
import json

import config_manager as cfg
from config_manager import FileOperationError, ValidationError


# ============================================================================
# Constants
# ============================================================================

CATEGORIES_FILE = cfg.BASE_DIR / "title_categories.json"


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class Category:
    """Represents a category for organizing titles."""
    name: str
    description: str = ""
    titles: Set[str] = field(default_factory=set)
    color: str = ""  # Optional color for UI purposes
    
    def add_title(self, title: str) -> bool:
        """Add a title to this category. Returns True if added, False if already present."""
        if title in self.titles:
            return False
        self.titles.add(title)
        return True
    
    def remove_title(self, title: str) -> bool:
        """Remove a title from this category. Returns True if removed, False if not present."""
        if title not in self.titles:
            return False
        self.titles.remove(title)
        return True
    
    def has_title(self, title: str) -> bool:
        """Check if a title is in this category."""
        return title in self.titles
    
    def __len__(self) -> int:
        return len(self.titles)
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "titles": sorted(self.titles),
            "color": self.color
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Category":
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            titles=set(data.get("titles", [])),
            color=data.get("color", "")
        )


@dataclass
class CategoryManager:
    """Manages multiple categories for title organization."""
    categories: Dict[str, Category] = field(default_factory=dict)
    
    def create_category(self, name: str, description: str = "", color: str = "") -> Category:
        """
        Create a new category.
        
        Args:
            name: Category name (must be unique)
            description: Optional description
            color: Optional color code
            
        Returns:
            The created Category
            
        Raises:
            ValidationError: If category already exists
        """
        normalized_name = name.strip().lower()
        if normalized_name in self.categories:
            raise ValidationError(f"Category '{name}' already exists")
        
        category = Category(name=name.strip(), description=description, color=color)
        self.categories[normalized_name] = category
        return category
    
    def delete_category(self, name: str) -> bool:
        """
        Delete a category.
        
        Args:
            name: Category name to delete
            
        Returns:
            True if deleted, False if not found
        """
        normalized_name = name.strip().lower()
        if normalized_name not in self.categories:
            return False
        del self.categories[normalized_name]
        return True
    
    def get_category(self, name: str) -> Optional[Category]:
        """
        Get a category by name.
        
        Args:
            name: Category name
            
        Returns:
            Category if found, None otherwise
        """
        return self.categories.get(name.strip().lower())
    
    def list_categories(self) -> List[Category]:
        """Get all categories sorted by name."""
        return sorted(self.categories.values(), key=lambda c: c.name.lower())
    
    def add_title_to_category(self, title: str, category_name: str) -> bool:
        """
        Add a title to a category.
        
        Args:
            title: Title to add
            category_name: Category name
            
        Returns:
            True if added
            
        Raises:
            ValidationError: If category doesn't exist
        """
        category = self.get_category(category_name)
        if category is None:
            raise ValidationError(f"Category '{category_name}' not found")
        return category.add_title(title)
    
    def remove_title_from_category(self, title: str, category_name: str) -> bool:
        """
        Remove a title from a category.
        
        Args:
            title: Title to remove
            category_name: Category name
            
        Returns:
            True if removed
            
        Raises:
            ValidationError: If category doesn't exist
        """
        category = self.get_category(category_name)
        if category is None:
            raise ValidationError(f"Category '{category_name}' not found")
        return category.remove_title(title)
    
    def get_title_categories(self, title: str) -> List[str]:
        """
        Get all categories a title belongs to.
        
        Args:
            title: Title to look up
            
        Returns:
            List of category names
        """
        return [cat.name for cat in self.categories.values() if title in cat.titles]
    
    def get_uncategorized_titles(self, all_titles: Set[str]) -> List[str]:
        """
        Get titles not in any category.
        
        Args:
            all_titles: Set of all titles
            
        Returns:
            Sorted list of uncategorized titles
        """
        categorized = set()
        for category in self.categories.values():
            categorized.update(category.titles)
        
        uncategorized = all_titles - categorized
        return sorted(uncategorized)
    
    def rename_category(self, old_name: str, new_name: str) -> bool:
        """
        Rename a category.
        
        Args:
            old_name: Current category name
            new_name: New category name
            
        Returns:
            True if renamed
            
        Raises:
            ValidationError: If old category doesn't exist or new name already taken
        """
        old_normalized = old_name.strip().lower()
        new_normalized = new_name.strip().lower()
        
        if old_normalized not in self.categories:
            raise ValidationError(f"Category '{old_name}' not found")
        
        if new_normalized in self.categories and old_normalized != new_normalized:
            raise ValidationError(f"Category '{new_name}' already exists")
        
        category = self.categories.pop(old_normalized)
        category.name = new_name.strip()
        self.categories[new_normalized] = category
        return True
    
    def to_dict(self) -> dict:
        return {
            "categories": {name: cat.to_dict() for name, cat in self.categories.items()}
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "CategoryManager":
        manager = cls()
        for name, cat_data in data.get("categories", {}).items():
            manager.categories[name] = Category.from_dict(cat_data)
        return manager


# ============================================================================
# Persistence
# ============================================================================

def load_categories() -> CategoryManager:
    """
    Load categories from file.
    
    Returns:
        CategoryManager with loaded or empty state
    """
    if not CATEGORIES_FILE.exists():
        return CategoryManager()
    
    try:
        with open(CATEGORIES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return CategoryManager.from_dict(data)
    except (json.JSONDecodeError, IOError, KeyError) as e:
        print(f"Warning: Could not load categories file. Starting fresh. Error: {e}")
        return CategoryManager()


def save_categories(manager: CategoryManager) -> None:
    """
    Save categories to file.
    
    Args:
        manager: CategoryManager to save
        
    Raises:
        FileOperationError: If save fails
    """
    try:
        with open(CATEGORIES_FILE, "w", encoding="utf-8") as f:
            json.dump(manager.to_dict(), f, indent=2)
    except IOError as e:
        raise FileOperationError(f"Could not save categories: {e}")


# ============================================================================
# Auto-categorization
# ============================================================================

def auto_categorize_by_prefix(
    titles: Set[str],
    manager: CategoryManager,
    prefix_length: int = 1
) -> Dict[str, List[str]]:
    """
    Auto-categorize titles by their prefix.
    
    Args:
        titles: Set of titles to categorize
        manager: CategoryManager to update
        prefix_length: Number of characters for prefix
        
    Returns:
        Dictionary of prefix -> list of titles
    """
    result: Dict[str, List[str]] = {}
    
    for title in titles:
        if len(title) >= prefix_length:
            prefix = title[:prefix_length].upper()
            if prefix not in result:
                result[prefix] = []
            result[prefix].append(title)
    
    # Create categories and add titles
    for prefix, prefix_titles in result.items():
        cat_name = f"Prefix-{prefix}"
        try:
            manager.create_category(cat_name, f"Titles starting with '{prefix}'")
        except ValidationError:
            pass  # Category already exists
        
        category = manager.get_category(cat_name)
        if category:
            for title in prefix_titles:
                category.add_title(title)
    
    return result


def auto_categorize_by_length(
    titles: Set[str],
    manager: CategoryManager
) -> Dict[int, List[str]]:
    """
    Auto-categorize titles by their length.
    
    Args:
        titles: Set of titles to categorize
        manager: CategoryManager to update
        
    Returns:
        Dictionary of length -> list of titles
    """
    result: Dict[int, List[str]] = {}
    
    for title in titles:
        length = len(title)
        if length not in result:
            result[length] = []
        result[length].append(title)
    
    # Create categories and add titles
    for length, length_titles in result.items():
        cat_name = f"Length-{length}"
        try:
            manager.create_category(cat_name, f"Titles with {length} characters")
        except ValidationError:
            pass  # Category already exists
        
        category = manager.get_category(cat_name)
        if category:
            for title in length_titles:
                category.add_title(title)
    
    return result


def auto_categorize_by_charset(
    titles: Set[str],
    manager: CategoryManager
) -> Dict[str, List[str]]:
    """
    Auto-categorize titles by character composition.
    
    Args:
        titles: Set of titles to categorize
        manager: CategoryManager to update
        
    Returns:
        Dictionary of charset type -> list of titles
    """
    categories_map = {
        "Alpha-Only": lambda t: t.isalpha(),
        "Numeric-Only": lambda t: t.isdigit(),
        "Alphanumeric": lambda t: t.isalnum() and not t.isalpha() and not t.isdigit(),
        "Has-Special": lambda t: not t.isalnum(),
    }
    
    result: Dict[str, List[str]] = {name: [] for name in categories_map}
    
    for title in titles:
        for cat_name, check_func in categories_map.items():
            if check_func(title):
                result[cat_name].append(title)
                break
    
    # Create categories and add titles
    for cat_name, cat_titles in result.items():
        if cat_titles:
            try:
                manager.create_category(cat_name, f"Titles with {cat_name.lower().replace('-', ' ')} characters")
            except ValidationError:
                pass  # Category already exists
            
            category = manager.get_category(cat_name)
            if category:
                for title in cat_titles:
                    category.add_title(title)
    
    return result
