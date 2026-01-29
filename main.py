import random
import sys
import signal
import atexit
from datetime import datetime

import config_manager as cfg
import deletion_manager as dm
import commands
import search as search_mod
import filter as filter_mod
import cat as cat_mod
from config_manager import (
    Config, ValidationError, FileOperationError,
    validate_length, validate_charset_choice, validate_batch_count,
    validate_menu_choice, validate_index_choice, validate_confirmation,
    validate_custom_charset, clear_screen, colorize, print_success, print_error,
    print_warning, print_info, print_title, print_menu,
    acquire_app_lock, release_app_lock, check_collision_warning,
    calculate_collision_stats
)

# Try to import keyboard handling for Esc key support (Windows)
try:
    import msvcrt
    HAS_MSVCRT = True
except ImportError:
    HAS_MSVCRT = False

# Global flag for graceful shutdown
_shutdown_requested = False


def save_all_data():
    """Save all data before exiting. Called on shutdown."""
    try:
        # Save config
        cfg.save_config(config)
    except:
        pass
    
    try:
        # Save titles (already saved incrementally, but ensure file is consistent)
        cfg.save_all_titles(generated_titles)
    except:
        pass
    
    try:
        # Save trash
        dm.save_trash(trash)
    except:
        pass
    
    try:
        # Save categories
        cat_mod.save_categories(cat_manager)
    except:
        pass


def graceful_shutdown(signum=None, frame=None):
    """Handle graceful shutdown on Ctrl+C or other signals."""
    global _shutdown_requested
    
    if _shutdown_requested:
        # Second interrupt - force exit
        print("\n\nForce exiting...")
        release_app_lock()
        sys.exit(130)
    
    _shutdown_requested = True
    print_warning("\n\nInterrupt received. Saving data...")
    
    try:
        save_all_data()
        print_success("Data saved successfully.")
    except Exception as e:
        print_error(f"Error saving data: {e}")
    
    release_app_lock()
    print_info("Exiting...")
    sys.exit(130)


def cleanup_on_exit():
    """Cleanup function registered with atexit."""
    release_app_lock()


# Register signal handlers and cleanup
signal.signal(signal.SIGINT, graceful_shutdown)
if hasattr(signal, 'SIGTERM'):
    signal.signal(signal.SIGTERM, graceful_shutdown)
atexit.register(cleanup_on_exit)


# Acquire application lock
if not acquire_app_lock():
    print_error("Error: Another instance of titlegen is already running.")
    print_info("If you believe this is an error, delete the .titlegen.lock file.")
    sys.exit(1)

# Load config on startup
config: Config = cfg.load_config()

# Load existing titles
generated_titles = cfg.load_titles()

# Load trash bin for undo functionality
trash = dm.load_trash()

# Load category manager
cat_manager = cat_mod.load_categories()


def check_escape_key() -> bool:
    """Check if Esc key was pressed (Windows only). Returns True if Esc pressed."""
    if HAS_MSVCRT and msvcrt.kbhit():
        key = msvcrt.getch()
        if key == b'\x1b':  # Esc key
            return True
        # Put the key back if it's not Esc (not possible, so we'll just return)
    return False


def get_input_with_escape(prompt: str) -> tuple[str, bool]:
    """
    Get user input with Esc key support.
    Returns (input_string, escape_pressed) tuple.
    """
    if HAS_MSVCRT:
        import time
        print(prompt, end='', flush=True)
        chars = []
        while True:
            if msvcrt.kbhit():
                char = msvcrt.getwch()
                if char == '\x1b':  # Esc
                    print()  # New line
                    return ('', True)
                elif char == '\r':  # Enter
                    print()  # New line
                    return (''.join(chars), False)
                elif char == '\x08':  # Backspace
                    if chars:
                        chars.pop()
                        print('\b \b', end='', flush=True)
                elif char == '\x00' or char == '\xe0':  # Special keys (arrows, function keys)
                    msvcrt.getwch()  # Consume the second byte
                else:
                    chars.append(char)
                    print(char, end='', flush=True)
            else:
                time.sleep(0.01)  # Small sleep to prevent CPU spinning
    else:
        # Fallback for non-Windows
        try:
            return (input(prompt), False)
        except EOFError:
            return ('', True)


def generate_title(length=None, charset=None, show_collision_warning=True):
    """
    Generate a random composition title using configurable length and character set.
    Ensures no duplicate titles are generated across all sessions on this machine.
    """
    if length is None:
        length = config.length
    if charset is None:
        charset = config.charset
    
    # Check for collision warning before generating
    if show_collision_warning:
        warning = check_collision_warning(charset, length, len(generated_titles))
        if warning:
            print_warning(warning)
            # Show detailed stats at critical level
            stats = calculate_collision_stats(charset, length, len(generated_titles))
            if stats['warning_level'] == 'critical':
                print_error(f"  Used: {len(generated_titles):,} / {stats['total_possible']:,} possible titles")
                print_error(f"  Remaining: ~{stats['remaining']:,} titles before high collision rate")
    
    while True:
        title = ''.join(random.choice(charset) for _ in range(length))
        if title not in generated_titles:
            generated_titles.add(title)
            try:
                cfg.save_title(title)
            except FileOperationError as e:
                print(f"Warning: {e}")
            return title

def configure_settings():
    """Configure title length and character set."""
    print_title(f"\nCurrent Settings:")
    print_info(f"  Length: {config.length} characters")
    print_info(f"  Character set: {config.charset_name}")
    
    print_title("\nWhat would you like to configure?")
    print_menu("  1: Change length")
    print_menu("  2: Change character set")
    print_menu("  3: Configure colors")
    print_menu("  4: Reset to defaults")
    print_menu("  5: Back to main menu")
    
    choice = input("\nSelect option (1-5): ").strip()
    
    if choice == "1":
        try:
            new_length = input(f"\nEnter title length ({cfg.MIN_LENGTH}-{cfg.MAX_LENGTH}): ").strip()
            config.set_length(new_length)
            cfg.save_config(config)
            print_success(f"Length set to {config.length} characters.")
        except ValidationError as e:
            print_error(f"Error: {e}")
        except FileOperationError as e:
            print_error(f"Error saving config: {e}")
    
    elif choice == "2":
        print_title("\nCharacter set options:")
        for key, (name, _) in cfg.CHARSET_OPTIONS.items():
            if key == "8":
                # Show current custom charset if defined
                if config.custom_charset:
                    print_menu(f"  {key}: {name} - Current: '{config.custom_charset}'")
                else:
                    print_menu(f"  {key}: {name} - Not defined")
            else:
                print_menu(f"  {key}: {name}")
        
        charset_choice = input("\nSelect character set (1-8): ").strip()
        try:
            if charset_choice == "8":
                # Custom charset - prompt for characters
                print_info("\nEnter the characters to use for title generation.")
                print_info("Examples: 'ABCD1234', 'XYZ', 'ABC123!@#'")
                if config.custom_charset:
                    print_info(f"Current custom charset: '{config.custom_charset}'")
                
                custom_input = input("Custom characters: ").strip()
                config.set_custom_charset(custom_input)
                cfg.save_config(config)
                print_success(f"Custom character set saved: '{config.custom_charset}' ({len(config.custom_charset)} unique chars)")
            else:
                config.set_charset(charset_choice)
                cfg.save_config(config)
                print_success(f"Character set changed to: {config.charset_name}")
        except ValidationError as e:
            print_error(f"Error: {e}")
        except FileOperationError as e:
            print_error(f"Error saving config: {e}")
    
    elif choice == "3":
        # Color configuration submenu
        configure_colors()
    
    elif choice == "4":
        config.reset_to_defaults()
        try:
            cfg.save_config(config)
            print_success("Settings reset to defaults.")
        except FileOperationError as e:
            print_error(f"Error saving config: {e}")
    
    elif choice == "5":
        return
    else:
        print_error("Invalid option.")


def configure_colors():
    """Configure color settings."""
    from config_manager import COLOR_NAMES, get_color_list
    
    print_title("\nColor Settings:")
    print_info(f"  Colors enabled: {'on' if config.color_enabled else 'off'}")
    print_info(f"  Success color:  {COLOR_NAMES.get(config.color_success, 'green')}")
    print_info(f"  Error color:    {COLOR_NAMES.get(config.color_error, 'red')}")
    print_info(f"  Warning color:  {COLOR_NAMES.get(config.color_warning, 'yellow')}")
    print_info(f"  Info color:     {COLOR_NAMES.get(config.color_info, 'cyan')}")
    print_info(f"  Title color:    {COLOR_NAMES.get(config.color_title, 'bright_white')}")
    print_info(f"  Menu color:     {COLOR_NAMES.get(config.color_menu, 'blue')}")
    
    print_title("\nOptions:")
    print_menu("  1: Toggle colors on/off")
    print_menu("  2: Change a color")
    print_menu("  3: Show available colors")
    print_menu("  4: Back")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == "1":
        config.color_enabled = not config.color_enabled
        try:
            cfg.save_config(config)
            cfg.init_colors(config)
            print_success(f"Colors {'enabled' if config.color_enabled else 'disabled'}.")
        except FileOperationError as e:
            print_error(f"Error: {e}")
    
    elif choice == "2":
        print_info("\nColor types: enabled, success, error, warning, info, title, menu")
        color_type = input("Enter color type to change: ").strip()
        print("\n" + get_color_list())
        color_value = input("Enter new color: ").strip()
        try:
            config.set_color(color_type, color_value)
            cfg.save_config(config)
            print_success(f"Color '{color_type}' set to '{color_value}'.")
        except ValidationError as e:
            print_error(f"Error: {e}")
        except FileOperationError as e:
            print_error(f"Error: {e}")
    
    elif choice == "3":
        print("\n" + get_color_list())
    
    elif choice == "4":
        return
    else:
        print_error("Invalid option.")


def view_titles():
    """Display all previously generated titles."""
    if not generated_titles:
        print("\nNo titles have been generated yet.")
    else:
        print("\nPreviously Generated Titles")
        for i, title in enumerate(sorted(generated_titles), 1):
            print(f"  {i}. {title}")
        print(f"Total: {len(generated_titles)} titles")

def delete_title():
    """Delete a specific title from the record."""
    if not generated_titles:
        print_warning("\nNo titles to delete.")
        return
    
    view_titles()
    choice = input("\nEnter the number of the title to delete (or 'c' to cancel): ").strip()
    
    if choice.lower() == 'c':
        print_info("Cancelled.")
        return
    
    try:
        sorted_titles = sorted(generated_titles)
        index = validate_index_choice(choice, len(sorted_titles))
        title_to_delete = sorted_titles[index]
        
        confirm = input(colorize(f"Delete '{title_to_delete}'? (y/n): ", "warning")).strip()
        if validate_confirmation(confirm):
            dm.delete_single_title(title_to_delete, generated_titles, trash)
            print_success(f"Deleted: {title_to_delete}")
            print_info("(Use 'Undo delete' to restore)")
        else:
            print_info("Cancelled.")
    except ValidationError as e:
        print_error(f"Error: {e}")
    except FileOperationError as e:
        print_error(f"Error saving: {e}")


def undo_delete():
    """Restore the most recently deleted title."""
    if trash.is_empty():
        print_warning("\nNo deleted titles to restore.")
        return
    
    # Show what will be restored
    last_deleted = trash.peek_last()
    print_info(f"\nMost recently deleted: '{last_deleted.title}'")
    print_info(f"  Deleted at: {last_deleted.deleted_at}")
    
    confirm = input("\nRestore this title? (y/n): ").strip()
    if validate_confirmation(confirm):
        try:
            restored = dm.undo_last_delete(generated_titles, trash)
            if restored:
                print_success(f"Restored: {restored}")
            else:
                print_warning("No titles to restore.")
        except ValidationError as e:
            print_error(f"Error: {e}")
        except FileOperationError as e:
            print_error(f"Error: {e}")
    else:
        print_info("Cancelled.")


def delete_all_titles():
    """Delete all titles from the record."""
    if not generated_titles:
        print_warning("\nNo titles to delete.")
        return
    
    count = len(generated_titles)
    print_error(f"\n⚠️  WARNING: This will delete ALL {count} titles!")
    print_warning("Deleted titles will be saved to trash for potential recovery.")
    
    confirm = input(colorize(f"\nType 'DELETE ALL' to confirm: ", "warning")).strip()
    if confirm == "DELETE ALL":
        try:
            deleted_count = dm.delete_all_titles(generated_titles, trash, save_to_trash=True)
            print_success(f"\nDeleted {deleted_count} titles.")
            print_info(f"Trash now contains {len(trash)} items (max {trash.max_size}).")
            print_info("Use 'Undo delete' to restore titles.")
        except FileOperationError as e:
            print_error(f"Error: {e}")
    else:
        print_info("Cancelled. You must type 'DELETE ALL' exactly.")


def view_trash():
    """View contents of the trash bin."""
    if trash.is_empty():
        print("\nTrash is empty.")
        return
    
    items = dm.view_trash(trash)
    print(f"\nTrash ({len(items)} items, max {trash.max_size}):")
    print("  (Oldest first, newest last)")
    for i, item in enumerate(items, 1):
        print(f"  {i}. {item.title} (deleted: {item.deleted_at[:19]})")
    
    print("\nOptions:")
    print("  1: Restore last deleted")
    print("  2: Clear trash permanently")
    print("  3: Back")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == "1":
        undo_delete()
    elif choice == "2":
        confirm = input("Permanently clear all trash? This cannot be undone. (y/n): ").strip()
        if validate_confirmation(confirm):
            try:
                cleared = dm.clear_trash(trash)
                print(f"Cleared {cleared} items from trash.")
            except FileOperationError as e:
                print(f"Error: {e}")
        else:
            print("Cancelled.")
    elif choice == "3":
        return
    else:
        print("Invalid option.")

def search_titles():
    """Advanced search menu for titles."""
    if not generated_titles:
        print("\nNo titles to search.")
        return
    
    print("\n:SEARCH TITLES:")
    print("  1: Contains text")
    print("  2: Starts with")
    print("  3: Ends with")
    print("  4: Regex pattern")
    print("  5: Exact match")
    print("  6: By length")
    print("  7: By length range")
    print("  8: Contains only specific chars")
    print("  0: Back")
    
    choice = input("\nSelect search type (0-8): ").strip()
    
    if choice == "0":
        return
    
    case_sensitive = input("Case sensitive? (y/n, default n): ").strip().lower() == 'y'
    
    results = []
    
    if choice == "1":
        query = input("Enter text to search for: ").strip()
        if query:
            results = search_mod.search_contains(generated_titles, query, case_sensitive)
    elif choice == "2":
        prefix = input("Enter prefix: ").strip()
        if prefix:
            results = search_mod.search_starts_with(generated_titles, prefix, case_sensitive)
    elif choice == "3":
        suffix = input("Enter suffix: ").strip()
        if suffix:
            results = search_mod.search_ends_with(generated_titles, suffix, case_sensitive)
    elif choice == "4":
        pattern = input("Enter regex pattern: ").strip()
        if pattern:
            try:
                results = search_mod.search_regex(generated_titles, pattern, case_sensitive)
            except Exception as e:
                print(f"Invalid regex: {e}")
                return
    elif choice == "5":
        exact = input("Enter exact title: ").strip()
        if exact:
            results = search_mod.search_exact(generated_titles, exact, case_sensitive)
    elif choice == "6":
        try:
            length = int(input("Enter exact length: ").strip())
            results = search_mod.search_length(generated_titles, length)
        except ValueError:
            print("Invalid number.")
            return
    elif choice == "7":
        try:
            min_len = int(input("Enter minimum length: ").strip())
            max_len = int(input("Enter maximum length: ").strip())
            results = search_mod.search_length_range(generated_titles, min_len, max_len)
        except ValueError:
            print("Invalid number.")
            return
    elif choice == "8":
        chars = input("Enter allowed characters: ").strip()
        if chars:
            results = search_mod.search_chars_only(generated_titles, chars, case_sensitive)
    else:
        print("Invalid option.")
        return
    
    if results:
        print(f"\n:SEARCH RESULTS ({len(results)} matches):")
        for i, title in enumerate(sorted(results), 1):
            print(f"  {i}. {title}")
    else:
        print("No matching titles found.")


def filter_titles():
    """Filter titles with advanced criteria."""
    if not generated_titles:
        print("\nNo titles to filter.")
        return
    
    print("\n:FILTER TITLES:")
    print("  1: Use preset filter")
    print("  2: Filter by length range")
    print("  3: Alphabetic only")
    print("  4: Numeric only")
    print("  5: Alphanumeric only")
    print("  6: Has digits")
    print("  7: No digits")
    print("  8: Uppercase only")
    print("  9: Lowercase only")
    print(" 10: Mixed case")
    print(" 11: Has special characters")
    print(" 12: All unique characters")
    print(" 00: Back")
    
    choice = input("\nSelect filter type (0-12): ").strip()
    
    if choice == "00":
        return
    
    results = []
    
    if choice == "1":
        print("\nAvailable presets:")
        for name, desc in filter_mod.FILTER_PRESETS.items():
            print(f"  {name}: {desc}")
        preset = input("\nEnter preset name: ").strip().lower()
        if preset in filter_mod.FILTER_PRESETS:
            filter_funcs = {
                'alpha': filter_mod.filter_alpha_only,
                'numeric': filter_mod.filter_numeric_only,
                'alnum': filter_mod.filter_alphanumeric_only,
                'upper': filter_mod.filter_uppercase_only,
                'lower': filter_mod.filter_lowercase_only,
                'has_digit': filter_mod.filter_has_digits,
                'no_digit': filter_mod.filter_no_digits,
                'unique': filter_mod.filter_unique_chars,
                'repeating': filter_mod.filter_no_repeating_chars,
            }
            if preset in filter_funcs:
                results = filter_funcs[preset](generated_titles)
        else:
            print("Unknown preset.")
            return
    elif choice == "2":
        try:
            min_len = int(input("Minimum length (0 for no min): ").strip() or "0")
            max_len = int(input("Maximum length (0 for no max): ").strip() or "0")
            results = filter_mod.filter_by_length(generated_titles, min_len if min_len > 0 else None, max_len if max_len > 0 else None)
        except ValueError:
            print("Invalid number.")
            return
    elif choice == "3":
        results = filter_mod.filter_alpha_only(generated_titles)
    elif choice == "4":
        results = filter_mod.filter_numeric_only(generated_titles)
    elif choice == "5":
        results = filter_mod.filter_alphanumeric_only(generated_titles)
    elif choice == "6":
        results = filter_mod.filter_has_digits(generated_titles)
    elif choice == "7":
        results = filter_mod.filter_no_digits(generated_titles)
    elif choice == "8":
        results = filter_mod.filter_uppercase_only(generated_titles)
    elif choice == "9":
        results = filter_mod.filter_lowercase_only(generated_titles)
    elif choice == "10":
        results = filter_mod.filter_mixed_case(generated_titles)
    elif choice == "11":
        results = filter_mod.filter_has_special(generated_titles)
    elif choice == "12":
        results = filter_mod.filter_unique_chars(generated_titles)
    else:
        print("Invalid option.")
        return
    
    if results:
        print(f"\n:FILTERED RESULTS ({len(results)} matches):")
        for i, title in enumerate(sorted(results), 1):
            print(f"  {i}. {title}")
    else:
        print("No titles match the filter criteria.")


def manage_categories():
    """Category management menu."""
    global cat_manager
    
    while True:
        print("\n:CATEGORY MANAGEMENT:")
        print("  1: List categories")
        print("  2: Create category")
        print("  3: Delete category")
        print("  4: View category titles")
        print("  5: Add title to category")
        print("  6: Remove title from category")
        print("  7: View uncategorized titles")
        print("  8: Auto-categorize titles")
        print("  9: Rename category")
        print("  0: Back")
        
        choice = input("\nSelect option (0-9): ").strip()
        
        if choice == "0":
            return
        
        if choice == "1":
            categories = cat_manager.list_categories()
            if categories:
                print("\n:CATEGORIES:")
                for name, count in categories:
                    print(f"  {name}: {count} titles")
            else:
                print("No categories created yet.")
        
        elif choice == "2":
            name = input("Enter category name: ").strip()
            desc = input("Enter description (optional): ").strip()
            if name:
                if cat_manager.create_category(name, desc if desc else None):
                    cat_mod.save_categories(cat_manager)
                    print(f"Category '{name}' created.")
                else:
                    print(f"Category '{name}' already exists.")
            else:
                print("Category name required.")
        
        elif choice == "3":
            name = input("Enter category name to delete: ").strip()
            if name:
                if cat_manager.delete_category(name):
                    cat_mod.save_categories(cat_manager)
                    print(f"Category '{name}' deleted.")
                else:
                    print(f"Category '{name}' not found.")
        
        elif choice == "4":
            name = input("Enter category name: ").strip()
            cat = cat_manager.get_category(name)
            if cat:
                if cat.titles:
                    print(f"\n:TITLES IN '{name}':")
                    for i, title in enumerate(sorted(cat.titles), 1):
                        print(f"  {i}. {title}")
                else:
                    print(f"Category '{name}' has no titles.")
            else:
                print(f"Category '{name}' not found.")
        
        elif choice == "5":
            if not generated_titles:
                print("No titles available.")
                continue
            print("\nAvailable titles:")
            sorted_titles = sorted(generated_titles)
            for i, t in enumerate(sorted_titles, 1):
                print(f"  {i}. {t}")
            try:
                idx = int(input("Enter title number: ").strip()) - 1
                if 0 <= idx < len(sorted_titles):
                    title = sorted_titles[idx]
                    cat_name = input("Enter category name: ").strip()
                    if cat_manager.add_title_to_category(title, cat_name):
                        cat_mod.save_categories(cat_manager)
                        print(f"Added '{title}' to '{cat_name}'.")
                    else:
                        print(f"Category '{cat_name}' not found.")
                else:
                    print("Invalid index.")
            except ValueError:
                print("Invalid number.")
        
        elif choice == "6":
            cat_name = input("Enter category name: ").strip()
            cat = cat_manager.get_category(cat_name)
            if cat and cat.titles:
                sorted_titles = sorted(cat.titles)
                for i, t in enumerate(sorted_titles, 1):
                    print(f"  {i}. {t}")
                try:
                    idx = int(input("Enter title number to remove: ").strip()) - 1
                    if 0 <= idx < len(sorted_titles):
                        title = sorted_titles[idx]
                        if cat_manager.remove_title_from_category(title, cat_name):
                            cat_mod.save_categories(cat_manager)
                            print(f"Removed '{title}' from '{cat_name}'.")
                    else:
                        print("Invalid index.")
                except ValueError:
                    print("Invalid number.")
            else:
                print(f"Category '{cat_name}' not found or empty.")
        
        elif choice == "7":
            uncategorized = cat_manager.get_uncategorized_titles(generated_titles)
            if uncategorized:
                print(f"\n:UNCATEGORIZED TITLES ({len(uncategorized)}):")
                for i, title in enumerate(sorted(uncategorized), 1):
                    print(f"  {i}. {title}")
            else:
                print("All titles are categorized.")
        
        elif choice == "8":
            print("\nAuto-categorize by:")
            print("  1: Prefix (first N characters)")
            print("  2: Length")
            print("  3: Character type")
            sub = input("Select method (1-3): ").strip()
            
            if sub == "1":
                try:
                    prefix_len = int(input("Prefix length: ").strip())
                    added = cat_mod.auto_categorize_by_prefix(cat_manager, generated_titles, prefix_len)
                    cat_mod.save_categories(cat_manager)
                    print(f"Auto-categorized {added} titles by prefix.")
                except ValueError:
                    print("Invalid number.")
            elif sub == "2":
                added = cat_mod.auto_categorize_by_length(cat_manager, generated_titles)
                cat_mod.save_categories(cat_manager)
                print(f"Auto-categorized {added} titles by length.")
            elif sub == "3":
                added = cat_mod.auto_categorize_by_charset(cat_manager, generated_titles)
                cat_mod.save_categories(cat_manager)
                print(f"Auto-categorized {added} titles by character type.")
            else:
                print("Invalid option.")
        
        elif choice == "9":
            old_name = input("Enter current category name: ").strip()
            new_name = input("Enter new category name: ").strip()
            if old_name and new_name:
                if cat_manager.rename_category(old_name, new_name):
                    cat_mod.save_categories(cat_manager)
                    print(f"Renamed '{old_name}' to '{new_name}'.")
                else:
                    print(f"Could not rename (category not found or new name exists).")
            else:
                print("Both names required.")
        
        else:
            print("Invalid option.")

def batch_generate():
    """Generate multiple titles at once."""
    try:
        count_input = input("\nHow many titles to generate? ").strip()
        count = validate_batch_count(count_input)
        
        if count > 100:
            confirm = input(f"Generate {count} titles? This may take a moment. (y/n): ").strip()
            if not validate_confirmation(confirm):
                print("Cancelled.")
                return
    except ValidationError as e:
        print(f"Error: {e}")
        return
    
    print(f"\nGenerating {count} titles...")
    new_titles = []
    for _ in range(count):
        new_titles.append(generate_title())
    
    print("Generated titles:")
    for i, title in enumerate(new_titles, 1):
        print(f"  {i}. {title}")

def export_titles():
    """Export titles to different formats."""
    if not generated_titles:
        print("\nNo titles to export.")
        return
    
    print("\nExport format:")
    print("  1: Text file (.txt)")
    print("  2: CSV file (.csv)")
    print("  3: JSON file (.json)")
    
    choice = input("\nSelect format (1-3): ").strip()
    sorted_titles = sorted(generated_titles)
    
    try:
        if choice == "1":
            filepath = cfg.get_export_filepath("txt")
            content = "\n".join(sorted_titles) + "\n"
            cfg.export_to_file(filepath, content)
            print(f"Exported to: {filepath}")
        
        elif choice == "2":
            filepath = cfg.get_export_filepath("csv")
            rows = [[i, title] for i, title in enumerate(sorted_titles, 1)]
            cfg.export_to_csv(filepath, ["Index", "Title"], rows)
            print(f"Exported to: {filepath}")
        
        elif choice == "3":
            filepath = cfg.get_export_filepath("json")
            data = {
                "export_date": datetime.now().isoformat(),
                "total_count": len(sorted_titles),
                "titles": sorted_titles
            }
            cfg.export_to_json(filepath, data)
            print(f"Exported to: {filepath}")
        
        else:
            print("Invalid selection.")
    
    except FileOperationError as e:
        print(f"Export failed: {e}")


def run_command_mode():
    """Allow user to enter CLI commands from interactive mode."""
    print("\n:COMMAND LINE MODE:")
    print("Enter commands as you would from the terminal.")
    print("Type 'help' for available commands, 'exit' or 'q' to return to menu.\n")
    
    while True:
        try:
            cmd_input = input("cmd> ").strip()
        except EOFError:
            break
        
        if not cmd_input:
            continue
        
        if cmd_input.lower() in ('exit', 'q', 'quit', 'back'):
            print("Returning to main menu.")
            break
        
        # Split the input into arguments
        args = cmd_input.split()
        
        # Execute the command
        exit_code = commands.run_cli(config, generated_titles, trash, args, cat_manager)
        
        # Don't exit on -1 (which would indicate interactive mode)
        if exit_code == -1:
            print("Invalid command. Type 'help' for available commands.")


def main():
    """Main interactive loop."""
    try:
        new_title = generate_title()
        print_success(f"\nGenerated Title: {new_title}")
    except FileOperationError as e:
        print_warning(f"Warning: {e}")
    
    while True:
        print_title("\nOptions:")
        print_menu("  1: Generate another title")
        print_menu("  2: View all previously generated titles")
        print_menu("  3: Delete a title")
        print_menu("  4: Undo delete")
        print_menu("  5: Delete ALL titles")
        print_menu("  6: View trash")
        print_menu("  7: Search titles")
        print_menu("  8: Filter titles")
        print_menu("  9: Manage categories")
        print_menu(" 10: Batch generate titles")
        print_menu(" 11: Export titles")
        print_menu(" 12: Settings (length/character set)")
        print_menu(" 00: Exit")
        print_menu("clr: Clear screen")
        print_menu("cmd: Command line mode")
        if HAS_MSVCRT:
            print_info("(Press Esc to exit at any time)")
        
        # Get input with Esc key support
        choice, escaped = get_input_with_escape(colorize("\nSelect an option: ", "info"))
        
        if escaped:
            print_info("Exiting program (Esc pressed).")
            break
        
        choice = choice.strip()
        
        # Handle special commands
        if choice.lower() == 'cmd':
            run_command_mode()
            continue
        
        if choice.lower() in ('clear', 'clr', 'cls'):
            clear_screen()
            continue
        
        try:
            validated_choice = validate_menu_choice(choice, ["00", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"])
        except ValidationError:
            print_error("Invalid option. Please enter 00-12, 'clr', or 'cmd'.")
            continue
        
        if validated_choice == "1":
            new_title = generate_title()
            print_success(f"\nGenerated Title: {new_title}")
        elif validated_choice == "2":
            view_titles()
        elif validated_choice == "3":
            delete_title()
        elif validated_choice == "4":
            undo_delete()
        elif validated_choice == "5":
            delete_all_titles()
        elif validated_choice == "6":
            view_trash()
        elif validated_choice == "7":
            search_titles()
        elif validated_choice == "8":
            filter_titles()
        elif validated_choice == "9":
            manage_categories()
        elif validated_choice == "10":
            batch_generate()
        elif validated_choice == "11":
            export_titles()
        elif validated_choice == "12":
            configure_settings()
        elif validated_choice == "00":
            print_info("Saving data before exit...")
            save_all_data()
            print_success("Data saved. Exiting program.")
            break


if __name__ == "__main__":
    try:
        # Check if CLI arguments provided
        if len(sys.argv) > 1:
            # Run in CLI mode
            exit_code = commands.run_cli(config, generated_titles, trash, cat_manager=cat_manager)
            release_app_lock()
            if exit_code >= 0:
                sys.exit(exit_code)
            # exit_code == -1 means fall through to interactive mode
        
        # Run in interactive mode
        main()
        release_app_lock()
    except KeyboardInterrupt:
        # This is a fallback - graceful_shutdown should handle most cases
        graceful_shutdown()
    except Exception as e:
        print_error(f"\nUnexpected error: {e}")
        save_all_data()
        release_app_lock()
        raise