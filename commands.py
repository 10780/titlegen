"""
Command line interface commands for the title generator.
Handles all CLI argument parsing and command execution.
"""

import argparse
import sys
from typing import List, Optional, Set

import config_manager as cfg
import deletion_manager as dm
import search as search_mod
import filter as filter_mod
import cat as cat_mod
from config_manager import (
    Config, ValidationError, FileOperationError,
    validate_batch_count, validate_confirmation, CHARSET_OPTIONS,
    clear_screen, colorize, print_success, print_error, print_warning,
    print_info, print_title, get_color_list, COLOR_NAMES
)


# ============================================================================
# Command Functions
# ============================================================================

def cmd_generate(
    config: Config,
    generated_titles: Set[str],
    mode: str = "single",
    batch_count: int = 1
) -> List[str]:
    """
    Generate title(s) based on mode.
    
    Args:
        config: The Config instance
        generated_titles: Set of existing titles
        mode: "single" or "batch"
        batch_count: Number of titles to generate in batch mode
        
    Returns:
        List of generated titles
    """
    import random
    
    titles = []
    count = 1 if mode == "single" else batch_count
    
    for _ in range(count):
        while True:
            title = ''.join(random.choice(config.charset) for _ in range(config.length))
            if title not in generated_titles:
                generated_titles.add(title)
                try:
                    cfg.save_title(title)
                except FileOperationError as e:
                    print(f"Warning: {e}", file=sys.stderr)
                titles.append(title)
                break
    
    return titles


def cmd_delete_last(
    generated_titles: Set[str],
    trash: dm.TrashBin
) -> Optional[str]:
    """
    Delete the most recently generated title.
    
    Args:
        generated_titles: Set of existing titles
        trash: TrashBin for undo functionality
        
    Returns:
        The deleted title, or None if no titles exist
    """
    if not generated_titles:
        return None
    
    # Get the last title from the file (maintains order)
    try:
        with open(cfg.TITLES_FILE, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        
        if not lines:
            return None
        
        last_title = lines[-1]
        
        if last_title in generated_titles:
            dm.delete_single_title(last_title, generated_titles, trash)
            return last_title
        
        return None
    except IOError:
        return None


def cmd_delete_record(
    generated_titles: Set[str],
    trash: dm.TrashBin,
    confirm: bool = False
) -> int:
    """
    Delete entire title record.
    
    Args:
        generated_titles: Set of existing titles
        trash: TrashBin for undo functionality
        confirm: Whether deletion is confirmed
        
    Returns:
        Number of deleted titles, or -1 if not confirmed
    """
    if not confirm:
        return -1
    
    count = len(generated_titles)
    dm.delete_all_titles(generated_titles, trash, save_to_trash=True)
    return count


def cmd_undo(
    generated_titles: Set[str],
    trash: dm.TrashBin
) -> Optional[str]:
    """
    Undo the last title deletion.
    
    Args:
        generated_titles: Set of existing titles
        trash: TrashBin to restore from
        
    Returns:
        The restored title, or None if trash is empty
    """
    if trash.is_empty():
        return None
    
    try:
        return dm.undo_last_delete(generated_titles, trash)
    except (ValidationError, FileOperationError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return None


def cmd_config_show(config: Config) -> dict:
    """
    Get current configuration as dictionary.
    
    Args:
        config: The Config instance
        
    Returns:
        Dictionary of current settings
    """
    return {
        "length": config.length,
        "charset_name": config.charset_name,
        "charset": config.charset,
        "charset_key": config.charset_key,
        "custom_charset": config.custom_charset or "(not set)",
        "color_enabled": "on" if config.color_enabled else "off",
        "color_success": COLOR_NAMES.get(config.color_success, "green"),
        "color_error": COLOR_NAMES.get(config.color_error, "red"),
        "color_warning": COLOR_NAMES.get(config.color_warning, "yellow"),
        "color_info": COLOR_NAMES.get(config.color_info, "cyan"),
        "color_title": COLOR_NAMES.get(config.color_title, "bright_white"),
        "color_menu": COLOR_NAMES.get(config.color_menu, "blue"),
    }


def cmd_config_set_length(config: Config, length: int) -> bool:
    """
    Set title length.
    
    Args:
        config: The Config instance
        length: New length value
        
    Returns:
        True if successful
    """
    try:
        config.set_length(length)
        cfg.save_config(config)
        return True
    except (ValidationError, FileOperationError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return False


def cmd_config_set_charset(config: Config, charset_key: str) -> bool:
    """
    Set character set by key.
    
    Args:
        config: The Config instance
        charset_key: The charset option key (1-8)
        
    Returns:
        True if successful
    """
    try:
        config.set_charset(charset_key)
        cfg.save_config(config)
        return True
    except (ValidationError, FileOperationError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return False


def cmd_config_set_custom_charset(config: Config, charset: str) -> bool:
    """
    Set custom character set.
    
    Args:
        config: The Config instance
        charset: The custom characters
        
    Returns:
        True if successful
    """
    try:
        config.set_custom_charset(charset)
        cfg.save_config(config)
        return True
    except (ValidationError, FileOperationError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return False


def cmd_config_reset(config: Config) -> bool:
    """
    Reset configuration to defaults.
    
    Args:
        config: The Config instance
        
    Returns:
        True if successful
    """
    try:
        config.reset_to_defaults()
        cfg.save_config(config)
        return True
    except FileOperationError as e:
        print(f"Error: {e}", file=sys.stderr)
        return False


def cmd_config_set_color(config: Config, color_type: str, color_value: str) -> bool:
    """
    Set a color configuration.
    
    Args:
        config: The Config instance
        color_type: Type of color (enabled, success, error, warning, info, title, menu)
        color_value: Color name or number
        
    Returns:
        True if successful
    """
    try:
        config.set_color(color_type, color_value)
        cfg.save_config(config)
        return True
    except (ValidationError, FileOperationError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return False


def cmd_clear() -> None:
    """Clear the terminal screen."""
    clear_screen()


def cmd_backup(suffix: Optional[str] = None) -> str:
    """
    Create a backup of the titles file.
    
    Args:
        suffix: Optional suffix for the backup filename
        
    Returns:
        Path to the backup file
        
    Raises:
        FileOperationError: If backup fails
    """
    from datetime import datetime
    from shutil import copy2
    
    if not cfg.TITLES_FILE.exists():
        raise FileOperationError("No titles file to backup")
    
    # Create backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if suffix:
        backup_name = f"TITLES_BACKUP_{timestamp}_{suffix}.txt"
    else:
        backup_name = f"TITLES_BACKUP_{timestamp}.txt"
    
    backup_path = cfg.BASE_DIR / backup_name
    
    try:
        copy2(cfg.TITLES_FILE, backup_path)
        return str(backup_path)
    except IOError as e:
        raise FileOperationError(f"Failed to create backup: {e}")


def cmd_ref(generated_titles: Set[str]) -> List[str]:
    """
    Get all previously generated titles.
    
    Args:
        generated_titles: Set of existing titles
        
    Returns:
        Sorted list of titles
    """
    return sorted(generated_titles)


# ============================================================================
# Search Command Functions
# ============================================================================

def cmd_search(
    generated_titles: Set[str],
    query: str,
    search_type: str = "contains",
    case_sensitive: bool = False
) -> search_mod.SearchResult:
    """
    Search titles with specified criteria.
    
    Args:
        generated_titles: Set of titles to search
        query: Search query
        search_type: Type of search (contains, starts, ends, regex, exact)
        case_sensitive: Whether search is case-sensitive
        
    Returns:
        SearchResult with matches
    """
    return search_mod.perform_search(generated_titles, query, search_type, case_sensitive)


# ============================================================================
# Filter Command Functions
# ============================================================================

def cmd_filter(
    generated_titles: Set[str],
    preset: Optional[str] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None
) -> List[str]:
    """
    Filter titles with specified criteria.
    
    Args:
        generated_titles: Set of titles to filter
        preset: Filter preset name
        min_length: Minimum length filter
        max_length: Maximum length filter
        
    Returns:
        Sorted list of matching titles
    """
    result = set(generated_titles)
    
    # Apply length filter
    if min_length is not None or max_length is not None:
        min_l = min_length if min_length is not None else 0
        max_l = max_length if max_length is not None else 999
        result = set(filter_mod.filter_by_length(result, min_l, max_l))
    
    # Apply preset filter
    if preset:
        result = set(filter_mod.apply_preset_filter(result, preset))
    
    return sorted(result)


def cmd_filter_list_presets() -> dict:
    """Get available filter presets."""
    return filter_mod.get_available_filters()


# ============================================================================
# Category Command Functions
# ============================================================================

def cmd_cat_list(cat_manager: cat_mod.CategoryManager) -> List[cat_mod.Category]:
    """List all categories."""
    return cat_manager.list_categories()


def cmd_cat_create(
    cat_manager: cat_mod.CategoryManager,
    name: str,
    description: str = ""
) -> cat_mod.Category:
    """
    Create a new category.
    
    Raises:
        ValidationError: If category already exists
    """
    category = cat_manager.create_category(name, description)
    cat_mod.save_categories(cat_manager)
    return category


def cmd_cat_delete(cat_manager: cat_mod.CategoryManager, name: str) -> bool:
    """Delete a category."""
    result = cat_manager.delete_category(name)
    if result:
        cat_mod.save_categories(cat_manager)
    return result


def cmd_cat_add_title(
    cat_manager: cat_mod.CategoryManager,
    title: str,
    category_name: str,
    generated_titles: Set[str]
) -> bool:
    """
    Add a title to a category.
    
    Raises:
        ValidationError: If category or title doesn't exist
    """
    if title not in generated_titles:
        raise ValidationError(f"Title '{title}' not found in generated titles")
    
    result = cat_manager.add_title_to_category(title, category_name)
    cat_mod.save_categories(cat_manager)
    return result


def cmd_cat_remove_title(
    cat_manager: cat_mod.CategoryManager,
    title: str,
    category_name: str
) -> bool:
    """Remove a title from a category."""
    result = cat_manager.remove_title_from_category(title, category_name)
    cat_mod.save_categories(cat_manager)
    return result


def cmd_cat_view(
    cat_manager: cat_mod.CategoryManager,
    category_name: str
) -> Optional[cat_mod.Category]:
    """Get a category by name."""
    return cat_manager.get_category(category_name)


def cmd_cat_uncategorized(
    cat_manager: cat_mod.CategoryManager,
    generated_titles: Set[str]
) -> List[str]:
    """Get uncategorized titles."""
    return cat_manager.get_uncategorized_titles(generated_titles)


def cmd_cat_auto(
    cat_manager: cat_mod.CategoryManager,
    generated_titles: Set[str],
    method: str = "prefix"
) -> int:
    """
    Auto-categorize titles.
    
    Args:
        cat_manager: Category manager
        generated_titles: Set of titles
        method: Auto-categorization method (prefix, length, charset)
        
    Returns:
        Number of categories created/updated
    """
    if method == "prefix":
        result = cat_mod.auto_categorize_by_prefix(generated_titles, cat_manager)
    elif method == "length":
        result = cat_mod.auto_categorize_by_length(generated_titles, cat_manager)
    elif method == "charset":
        result = cat_mod.auto_categorize_by_charset(generated_titles, cat_manager)
    else:
        raise ValidationError(f"Unknown auto-categorize method: {method}")
    
    cat_mod.save_categories(cat_manager)
    return len(result)


# ============================================================================
# Help Text
# ============================================================================

HELP_TEXT = """
Title Generator - Command Line Interface

USAGE:
  python main.py [command] [options]

COMMANDS:
  generate, gen, g    Generate new title(s)
    -s, --single      Generate a single title (default)
    -b, --batch N     Generate N titles at once

  del                 Delete titles
    last              Delete the last generated title
    record            Delete ALL titles (requires --confirm)
    --confirm         Confirm destructive operation

  undo                Restore the last deleted title

  config              View or modify settings
    --show            Show current configuration (default)
    --length N        Set title length (1-16)
    --charset N       Set character set (1-8)
    --custom CHARS    Set custom character set
    --color TYPE VAL  Set color (type: enabled/success/error/warning/info/title/menu)
    --colors          Show available colors
    --reset           Reset to default settings

  clear               Clear the terminal screen

  bckup               Create a backup of the titles file
    --suffix NAME     Add a custom suffix to backup filename

  ref                 View all previously generated titles
    --count           Show only the count

  search              Search titles
    QUERY             Search term
    --type TYPE       Search type: contains, starts, ends, regex, exact
    --case            Case-sensitive search

  filter              Filter titles
    --preset NAME     Use preset filter (alpha, numeric, alnum, upper, 
                      lower, has_digit, no_digit, unique, repeating)
    --min-length N    Minimum length
    --max-length N    Maximum length
    --list            List available filter presets

  cat                 Manage categories
    list              List all categories
    create NAME       Create a new category
    delete NAME       Delete a category
    view NAME         View titles in a category
    add TITLE CAT     Add title to category
    remove TITLE CAT  Remove title from category
    uncat             Show uncategorized titles
    auto METHOD       Auto-categorize (prefix, length, charset)

  help, -h, --help    Show this help message

EXAMPLES:
  python main.py g                    Generate one title
  python main.py gen -b 10            Generate 10 titles
  python main.py del last             Delete last title
  python main.py del record --confirm Delete all titles
  python main.py undo                 Restore last deleted
  python main.py config --length 12   Set length to 12
  python main.py config --charset 5   Set mixed case + numbers
  python main.py config --color enabled off   Disable colors
  python main.py config --color success green Set success color
  python main.py clear                Clear screen
  python main.py bckup                Create titles backup
  python main.py bckup --suffix v1    Backup with custom suffix
  python main.py ref                  View all titles
  python main.py search ABC           Search for 'ABC'
  python main.py search ^A --type regex   Regex search
  python main.py filter --preset alpha    Filter alphabetic only
  python main.py filter --min-length 8    Filter by length
  python main.py cat list             List categories
  python main.py cat create favorites Create category
  python main.py cat auto prefix      Auto-categorize by prefix

CHARACTER SETS:
  1: Uppercase + Numbers (default)
  2: Uppercase only
  3: Lowercase + Numbers
  4: Lowercase only
  5: Mixed case + Numbers
  6: Mixed case only
  7: Numbers only
  8: Custom

FILTER PRESETS:
  alpha     - Alphabetic characters only
  numeric   - Numeric characters only
  alnum     - Alphanumeric characters only
  upper     - Uppercase letters only
  lower     - Lowercase letters only
  has_digit - Contains at least one digit
  no_digit  - Contains no digits
  unique    - All characters are unique
  repeating - Has repeating characters

COLOR OPTIONS:
  Types: enabled, success, error, warning, info, title, menu
  Colors (by name): off, black, red, green, yellow, blue, magenta, cyan, white
  Bright colors: bright_red, bright_green, bright_yellow, bright_blue,
                 bright_magenta, bright_cyan, bright_white
  Colors (by number): 0=off, 1=red, 2=green, 3=yellow, 4=blue, 5=magenta,
                      6=cyan, 7=white, 8-14=bright variants

Run without arguments for interactive mode.
"""


# ============================================================================
# Argument Parser
# ============================================================================

def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        prog="titlegen",
        description="Generate random composition titles",
        add_help=False  # We'll handle help ourselves
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Generate command
    gen_parser = subparsers.add_parser("generate", aliases=["gen", "g"], help="Generate title(s)")
    gen_group = gen_parser.add_mutually_exclusive_group()
    gen_group.add_argument("-s", "--single", action="store_true", help="Generate single title (default)")
    gen_group.add_argument("-b", "--batch", type=int, metavar="N", help="Generate N titles")
    
    # Delete command
    del_parser = subparsers.add_parser("del", help="Delete titles")
    del_parser.add_argument("target", choices=["last", "record"], help="What to delete")
    del_parser.add_argument("--confirm", action="store_true", help="Confirm destructive operation")
    
    # Undo command
    subparsers.add_parser("undo", help="Undo last deletion")
    
    # Config command
    config_parser = subparsers.add_parser("config", help="View/modify settings")
    config_parser.add_argument("--show", action="store_true", help="Show current config")
    config_parser.add_argument("--length", type=int, metavar="N", help="Set title length")
    config_parser.add_argument("--charset", type=str, metavar="N", help="Set charset (1-8)")
    config_parser.add_argument("--custom", type=str, metavar="CHARS", help="Set custom charset")
    config_parser.add_argument("--color", nargs=2, metavar=("TYPE", "VALUE"), help="Set color (type value)")
    config_parser.add_argument("--colors", action="store_true", help="List available colors")
    config_parser.add_argument("--reset", action="store_true", help="Reset to defaults")
    
    # Clear command
    subparsers.add_parser("clear", aliases=["cls"], help="Clear the terminal screen")
    
    # Backup command
    backup_parser = subparsers.add_parser("bckup", aliases=["backup"], help="Backup titles file")
    backup_parser.add_argument("--suffix", type=str, metavar="NAME", help="Custom suffix for backup filename")
    
    # Ref command
    ref_parser = subparsers.add_parser("ref", help="View generated titles")
    ref_parser.add_argument("--count", action="store_true", help="Show only count")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search titles")
    search_parser.add_argument("query", nargs="?", default="", help="Search term")
    search_parser.add_argument("--type", dest="search_type", choices=["contains", "starts", "ends", "regex", "exact"],
                                default="contains", help="Search type")
    search_parser.add_argument("--case", action="store_true", help="Case-sensitive search")
    
    # Filter command
    filter_parser = subparsers.add_parser("filter", help="Filter titles")
    filter_parser.add_argument("--preset", type=str, metavar="NAME", help="Use preset filter")
    filter_parser.add_argument("--min-length", type=int, metavar="N", help="Minimum length")
    filter_parser.add_argument("--max-length", type=int, metavar="N", help="Maximum length")
    filter_parser.add_argument("--list", action="store_true", help="List available presets")
    
    # Category command
    cat_parser = subparsers.add_parser("cat", help="Manage categories")
    cat_subparsers = cat_parser.add_subparsers(dest="cat_action", help="Category action")
    
    cat_subparsers.add_parser("list", help="List all categories")
    
    cat_create = cat_subparsers.add_parser("create", help="Create a category")
    cat_create.add_argument("name", help="Category name")
    cat_create.add_argument("--desc", default="", help="Category description")
    
    cat_delete = cat_subparsers.add_parser("delete", help="Delete a category")
    cat_delete.add_argument("name", help="Category name")
    
    cat_view = cat_subparsers.add_parser("view", help="View category contents")
    cat_view.add_argument("name", help="Category name")
    
    cat_add = cat_subparsers.add_parser("add", help="Add title to category")
    cat_add.add_argument("title", help="Title to add")
    cat_add.add_argument("category", help="Category name")
    
    cat_remove = cat_subparsers.add_parser("remove", help="Remove title from category")
    cat_remove.add_argument("title", help="Title to remove")
    cat_remove.add_argument("category", help="Category name")
    
    cat_subparsers.add_parser("uncat", help="Show uncategorized titles")
    
    cat_auto = cat_subparsers.add_parser("auto", help="Auto-categorize titles")
    cat_auto.add_argument("method", choices=["prefix", "length", "charset"], help="Categorization method")
    
    # Help command
    subparsers.add_parser("help", help="Show help")
    
    return parser


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = create_parser()
    
    # Check for help flags
    if args is None:
        args = sys.argv[1:]
    
    if not args:
        return argparse.Namespace(command=None)
    
    if args[0] in ["-h", "--help", "help"]:
        return argparse.Namespace(command="help")
    
    return parser.parse_args(args)


# ============================================================================
# Command Execution
# ============================================================================

def execute_command(
    args: argparse.Namespace,
    config: Config,
    generated_titles: Set[str],
    trash: dm.TrashBin,
    cat_manager: Optional[cat_mod.CategoryManager] = None
) -> int:
    """
    Execute a CLI command.
    
    Args:
        args: Parsed arguments
        config: Config instance
        generated_titles: Set of existing titles
        trash: TrashBin instance
        cat_manager: CategoryManager instance (optional, loaded if needed)
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    command = args.command
    
    if command is None:
        # No command - return to indicate interactive mode
        return -1
    
    if command == "help":
        print(HELP_TEXT)
        return 0
    
    if command in ["generate", "gen", "g"]:
        # Determine mode and count
        if hasattr(args, 'batch') and args.batch:
            try:
                count = validate_batch_count(args.batch)
                mode = "batch"
            except ValidationError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1
        else:
            mode = "single"
            count = 1
        
        titles = cmd_generate(config, generated_titles, mode, count)
        
        if mode == "single":
            print(titles[0])
        else:
            print(f"Generated {len(titles)} titles:")
            for i, title in enumerate(titles, 1):
                print(f"  {i}. {title}")
        
        return 0
    
    if command == "del":
        if args.target == "last":
            deleted = cmd_delete_last(generated_titles, trash)
            if deleted:
                print(f"Deleted: {deleted}")
                return 0
            else:
                print("No titles to delete.", file=sys.stderr)
                return 1
        
        elif args.target == "record":
            if not args.confirm:
                print("Error: Deleting all titles requires --confirm flag.", file=sys.stderr)
                print("Usage: python main.py del record --confirm", file=sys.stderr)
                return 1
            
            count = cmd_delete_record(generated_titles, trash, confirm=True)
            print(f"Deleted {count} titles.")
            print(f"Trash contains {len(trash)} items for recovery.")
            return 0
    
    if command == "undo":
        restored = cmd_undo(generated_titles, trash)
        if restored:
            print(f"Restored: {restored}")
            return 0
        else:
            print("No deleted titles to restore.", file=sys.stderr)
            return 1
    
    if command == "config":
        # Check what config operation to perform
        if args.reset:
            if cmd_config_reset(config):
                print("Configuration reset to defaults.")
                return 0
            return 1
        
        if args.colors:
            print(get_color_list())
            return 0
        
        if args.color:
            color_type, color_value = args.color
            if cmd_config_set_color(config, color_type, color_value):
                print(f"Color '{color_type}' set to '{color_value}'.")
                return 0
            return 1
        
        if args.length is not None:
            if cmd_config_set_length(config, args.length):
                print(f"Length set to {config.length}.")
                return 0
            return 1
        
        if args.charset is not None:
            if cmd_config_set_charset(config, args.charset):
                print(f"Character set changed to: {config.charset_name}")
                return 0
            return 1
        
        if args.custom is not None:
            if cmd_config_set_custom_charset(config, args.custom):
                print(f"Custom charset set: '{config.custom_charset}' ({len(config.custom_charset)} chars)")
                return 0
            return 1
        
        # Default: show config
        settings = cmd_config_show(config)
        print("Current Configuration:")
        print(f"  Length:        {settings['length']} characters")
        print(f"  Character set: {settings['charset_name']}")
        print(f"  Charset key:   {settings['charset_key']}")
        if settings['custom_charset'] != "(not set)":
            print(f"  Custom chars:  '{settings['custom_charset']}'")
        print(f"\n  Color enabled: {settings['color_enabled']}")
        print(f"  Color success: {settings['color_success']}")
        print(f"  Color error:   {settings['color_error']}")
        print(f"  Color warning: {settings['color_warning']}")
        print(f"  Color info:    {settings['color_info']}")
        print(f"  Color title:   {settings['color_title']}")
        print(f"  Color menu:    {settings['color_menu']}")
        return 0
    
    if command in ["clear", "cls"]:
        cmd_clear()
        return 0
    
    if command in ["bckup", "backup"]:
        try:
            suffix = args.suffix if hasattr(args, 'suffix') else None
            backup_path = cmd_backup(suffix)
            print(f"Backup created: {backup_path}")
            return 0
        except FileOperationError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    
    if command == "ref":
        titles = cmd_ref(generated_titles)
        
        if args.count:
            print(f"Total titles: {len(titles)}")
            return 0
        
        if not titles:
            print("No titles generated yet.")
            return 0
        
        print(f"Previously Generated Titles ({len(titles)}):")
        for i, title in enumerate(titles, 1):
            print(f"  {i}. {title}")
        return 0
    
    if command == "search":
        if not generated_titles:
            print("No titles to search.")
            return 0
        
        if not args.query:
            print("Error: Search query required.", file=sys.stderr)
            print("Usage: python main.py search QUERY [--type TYPE] [--case]", file=sys.stderr)
            return 1
        
        try:
            result = cmd_search(
                generated_titles,
                args.query,
                args.search_type,
                args.case
            )
            
            print(result.summary())
            if result:
                for i, title in enumerate(result.matches, 1):
                    print(f"  {i}. {title}")
            return 0
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    
    if command == "filter":
        if not generated_titles:
            print("No titles to filter.")
            return 0
        
        # List presets
        if hasattr(args, 'list') and args.list:
            presets = cmd_filter_list_presets()
            print("Available filter presets:")
            for name, (display_name, description) in presets.items():
                print(f"  {name:12} - {display_name}: {description}")
            return 0
        
        try:
            results = cmd_filter(
                generated_titles,
                preset=args.preset if hasattr(args, 'preset') else None,
                min_length=args.min_length if hasattr(args, 'min_length') else None,
                max_length=args.max_length if hasattr(args, 'max_length') else None
            )
            
            print(f"Filtered titles ({len(results)} of {len(generated_titles)}):")
            if results:
                for i, title in enumerate(results, 1):
                    print(f"  {i}. {title}")
            else:
                print("  No titles match the filter criteria.")
            return 0
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    
    if command == "cat":
        # Load category manager if not provided
        if cat_manager is None:
            cat_manager = cat_mod.load_categories()
        
        cat_action = args.cat_action if hasattr(args, 'cat_action') else None
        
        if cat_action is None or cat_action == "list":
            categories = cmd_cat_list(cat_manager)
            if not categories:
                print("No categories defined.")
            else:
                print(f"Categories ({len(categories)}):")
                for cat in categories:
                    print(f"  {cat.name} ({len(cat)} titles)")
                    if cat.description:
                        print(f"    {cat.description}")
            return 0
        
        if cat_action == "create":
            try:
                category = cmd_cat_create(cat_manager, args.name, args.desc if hasattr(args, 'desc') else "")
                print(f"Created category: {category.name}")
                return 0
            except ValidationError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1
        
        if cat_action == "delete":
            if cmd_cat_delete(cat_manager, args.name):
                print(f"Deleted category: {args.name}")
                return 0
            else:
                print(f"Category not found: {args.name}", file=sys.stderr)
                return 1
        
        if cat_action == "view":
            category = cmd_cat_view(cat_manager, args.name)
            if category is None:
                print(f"Category not found: {args.name}", file=sys.stderr)
                return 1
            
            print(f"Category: {category.name}")
            if category.description:
                print(f"Description: {category.description}")
            print(f"Titles ({len(category)}):")
            if category.titles:
                for i, title in enumerate(sorted(category.titles), 1):
                    print(f"  {i}. {title}")
            else:
                print("  (empty)")
            return 0
        
        if cat_action == "add":
            try:
                if cmd_cat_add_title(cat_manager, args.title, args.category, generated_titles):
                    print(f"Added '{args.title}' to category '{args.category}'")
                else:
                    print(f"Title already in category")
                return 0
            except ValidationError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1
        
        if cat_action == "remove":
            try:
                if cmd_cat_remove_title(cat_manager, args.title, args.category):
                    print(f"Removed '{args.title}' from category '{args.category}'")
                else:
                    print(f"Title not in category")
                return 0
            except ValidationError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1
        
        if cat_action == "uncat":
            uncategorized = cmd_cat_uncategorized(cat_manager, generated_titles)
            print(f"Uncategorized titles ({len(uncategorized)} of {len(generated_titles)}):")
            if uncategorized:
                for i, title in enumerate(uncategorized, 1):
                    print(f"  {i}. {title}")
            else:
                print("  All titles are categorized.")
            return 0
        
        if cat_action == "auto":
            try:
                count = cmd_cat_auto(cat_manager, generated_titles, args.method)
                print(f"Auto-categorized titles into {count} categories by {args.method}.")
                return 0
            except ValidationError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1
        
        print("Invalid category action. Use 'cat list' to see options.")
        return 1
    
    # Unknown command
    print(f"Unknown command: {command}", file=sys.stderr)
    print("Use 'python main.py help' for usage information.", file=sys.stderr)
    return 1


def run_cli(
    config: Config,
    generated_titles: Set[str],
    trash: dm.TrashBin,
    args: Optional[List[str]] = None,
    cat_manager: Optional[cat_mod.CategoryManager] = None
) -> int:
    """
    Main entry point for CLI mode.
    
    Args:
        config: Config instance
        generated_titles: Set of existing titles
        trash: TrashBin instance
        args: Command line arguments (defaults to sys.argv[1:])
        cat_manager: CategoryManager instance (optional, loaded if needed)
        
    Returns:
        Exit code, or -1 to indicate interactive mode should run
    """
    parsed = parse_args(args)
    return execute_command(parsed, config, generated_titles, trash, cat_manager)
