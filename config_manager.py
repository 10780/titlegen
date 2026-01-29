"""
Configuration and record file management for the title generator.
Uses a Config class for better encapsulation and pathlib for path handling.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Tuple, Set, Any
from contextlib import contextmanager
import json
import string
import os
import time


# ============================================================================
# Constants
# ============================================================================

BASE_DIR = Path(__file__).parent.resolve()
TITLES_FILE = BASE_DIR / "PREVIOUSLY_GENERATED_TITLES.txt"
EXPORT_DIR = BASE_DIR
CONFIG_FILE = BASE_DIR / "titlegen_config.json"
LOCK_FILE = BASE_DIR / ".titlegen.lock"

DEFAULT_LENGTH = 10
MAX_LENGTH = 16
MIN_LENGTH = 1
MAX_BATCH_SIZE = 1000

# Collision detection thresholds
COLLISION_WARNING_THRESHOLD = 0.5  # Warn when 50% of possible titles are used
COLLISION_CRITICAL_THRESHOLD = 0.9  # Critical warning at 90%

# Default charset: uppercase letters + numbers
DEFAULT_CHARSET = string.ascii_uppercase + string.digits
DEFAULT_CHARSET_NAME = "Uppercase + Numbers (default)"

CHARSET_OPTIONS: dict[str, Tuple[str, str]] = {
    "1": ("Uppercase + Numbers (default)", string.ascii_uppercase + string.digits),
    "2": ("Uppercase only", string.ascii_uppercase),
    "3": ("Lowercase + Numbers", string.ascii_lowercase + string.digits),
    "4": ("Lowercase only", string.ascii_lowercase),
    "5": ("Mixed case + Numbers", string.ascii_letters + string.digits),
    "6": ("Mixed case only", string.ascii_letters),
    "7": ("Numbers only", string.digits),
    "8": ("Custom", ""),  # Placeholder for custom charset
}


# ============================================================================
# Color System
# ============================================================================

# ANSI color codes
class Colors:
    """ANSI escape codes for terminal colors."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    
    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright foreground colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"


# Color options mapping - both words and numbers
COLOR_OPTIONS: dict[str, str] = {
    # By name (lowercase)
    "off": "",
    "none": "",
    "black": Colors.BLACK,
    "red": Colors.RED,
    "green": Colors.GREEN,
    "yellow": Colors.YELLOW,
    "blue": Colors.BLUE,
    "magenta": Colors.MAGENTA,
    "cyan": Colors.CYAN,
    "white": Colors.WHITE,
    "bright_red": Colors.BRIGHT_RED,
    "bright_green": Colors.BRIGHT_GREEN,
    "bright_yellow": Colors.BRIGHT_YELLOW,
    "bright_blue": Colors.BRIGHT_BLUE,
    "bright_magenta": Colors.BRIGHT_MAGENTA,
    "bright_cyan": Colors.BRIGHT_CYAN,
    "bright_white": Colors.BRIGHT_WHITE,
    # By number
    "0": "",  # off
    "1": Colors.RED,
    "2": Colors.GREEN,
    "3": Colors.YELLOW,
    "4": Colors.BLUE,
    "5": Colors.MAGENTA,
    "6": Colors.CYAN,
    "7": Colors.WHITE,
    "8": Colors.BRIGHT_RED,
    "9": Colors.BRIGHT_GREEN,
    "10": Colors.BRIGHT_YELLOW,
    "11": Colors.BRIGHT_BLUE,
    "12": Colors.BRIGHT_MAGENTA,
    "13": Colors.BRIGHT_CYAN,
    "14": Colors.BRIGHT_WHITE,
}

# Reverse mapping for display
COLOR_NAMES: dict[str, str] = {
    "": "off",
    Colors.BLACK: "black",
    Colors.RED: "red",
    Colors.GREEN: "green",
    Colors.YELLOW: "yellow",
    Colors.BLUE: "blue",
    Colors.MAGENTA: "magenta",
    Colors.CYAN: "cyan",
    Colors.WHITE: "white",
    Colors.BRIGHT_RED: "bright_red",
    Colors.BRIGHT_GREEN: "bright_green",
    Colors.BRIGHT_YELLOW: "bright_yellow",
    Colors.BRIGHT_BLUE: "bright_blue",
    Colors.BRIGHT_MAGENTA: "bright_magenta",
    Colors.BRIGHT_CYAN: "bright_cyan",
    Colors.BRIGHT_WHITE: "bright_white",
}

# Default color scheme
DEFAULT_COLOR_ENABLED = True
DEFAULT_COLOR_SUCCESS = Colors.GREEN
DEFAULT_COLOR_ERROR = Colors.RED
DEFAULT_COLOR_WARNING = Colors.YELLOW
DEFAULT_COLOR_INFO = Colors.CYAN
DEFAULT_COLOR_TITLE = Colors.BRIGHT_WHITE
DEFAULT_COLOR_MENU = Colors.BLUE


def validate_color(color: str) -> str:
    """
    Validate a color choice and return the ANSI code.
    
    Args:
        color: Color name or number
        
    Returns:
        ANSI color code or empty string for off
        
    Raises:
        ValidationError: If the color choice is invalid
    """
    color_lower = str(color).strip().lower()
    if color_lower in COLOR_OPTIONS:
        return COLOR_OPTIONS[color_lower]
    
    valid = "off, black, red, green, yellow, blue, magenta, cyan, white, or 0-14"
    raise ValidationError(f"Invalid color '{color}'. Valid options: {valid}")


def get_color_list() -> str:
    """Get a formatted list of available colors."""
    lines = [
        "Available colors:",
        "  Words: off, black, red, green, yellow, blue, magenta, cyan, white",
        "  Bright: bright_red, bright_green, bright_yellow, bright_blue,",
        "          bright_magenta, bright_cyan, bright_white",
        "  Numbers: 0=off, 1=red, 2=green, 3=yellow, 4=blue, 5=magenta,",
        "           6=cyan, 7=white, 8-14=bright variants"
    ]
    return "\n".join(lines)


# Global color state (for quick access without passing config everywhere)
_color_enabled = True
_colors = {
    "success": DEFAULT_COLOR_SUCCESS,
    "error": DEFAULT_COLOR_ERROR,
    "warning": DEFAULT_COLOR_WARNING,
    "info": DEFAULT_COLOR_INFO,
    "title": DEFAULT_COLOR_TITLE,
    "menu": DEFAULT_COLOR_MENU,
}


def init_colors(config: "Config") -> None:
    """Initialize global color state from config."""
    global _color_enabled, _colors
    _color_enabled = config.color_enabled
    _colors = {
        "success": config.color_success,
        "error": config.color_error,
        "warning": config.color_warning,
        "info": config.color_info,
        "title": config.color_title,
        "menu": config.color_menu,
    }


def colorize(text: str, color_type: str = "info") -> str:
    """
    Apply color to text based on the color type.
    
    Args:
        text: The text to colorize
        color_type: One of "success", "error", "warning", "info", "title", "menu"
        
    Returns:
        Colorized string or plain text if colors disabled
    """
    if not _color_enabled:
        return text
    
    color_code = _colors.get(color_type, "")
    if not color_code:
        return text
    
    return f"{color_code}{text}{Colors.RESET}"


def print_success(message: str) -> None:
    """Print a success message in green."""
    print(colorize(message, "success"))


def print_error(message: str) -> None:
    """Print an error message in red."""
    print(colorize(message, "error"))


def print_warning(message: str) -> None:
    """Print a warning message in yellow."""
    print(colorize(message, "warning"))


def print_info(message: str) -> None:
    """Print an info message in cyan."""
    print(colorize(message, "info"))


def print_title(message: str) -> None:
    """Print a title/header message."""
    print(colorize(message, "title"))


def print_menu(message: str) -> None:
    """Print menu text."""
    print(colorize(message, "menu"))


# ============================================================================
# Screen Clearing
# ============================================================================

def clear_screen() -> None:
    """Clear the terminal screen."""
    # Windows
    if os.name == 'nt':
        os.system('cls')
    # Unix/Linux/Mac
    else:
        os.system('clear')


# ============================================================================
# File Locking
# ============================================================================

class FileLock:
    """
    Simple file-based lock to prevent multiple instances from corrupting data.
    Uses a lock file with PID to detect stale locks.
    """
    
    def __init__(self, lock_path: Path = LOCK_FILE, timeout: float = 5.0):
        self.lock_path = lock_path
        self.timeout = timeout
        self.locked = False
    
    def acquire(self) -> bool:
        """
        Acquire the lock. Returns True if successful.
        Will wait up to timeout seconds for the lock.
        """
        start_time = time.time()
        
        while time.time() - start_time < self.timeout:
            try:
                # Check if lock file exists
                if self.lock_path.exists():
                    # Check if the process that created it is still running
                    try:
                        with open(self.lock_path, 'r') as f:
                            pid = int(f.read().strip())
                        
                        # Check if process is still running
                        if self._process_exists(pid):
                            time.sleep(0.1)
                            continue
                        else:
                            # Stale lock, remove it
                            self.lock_path.unlink()
                    except (ValueError, IOError):
                        # Corrupted lock file, remove it
                        try:
                            self.lock_path.unlink()
                        except:
                            pass
                
                # Try to create lock file
                try:
                    # Use exclusive creation mode
                    fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    os.write(fd, str(os.getpid()).encode())
                    os.close(fd)
                    self.locked = True
                    return True
                except FileExistsError:
                    time.sleep(0.1)
                    continue
                    
            except Exception:
                time.sleep(0.1)
                continue
        
        return False
    
    def release(self) -> None:
        """Release the lock."""
        if self.locked:
            try:
                self.lock_path.unlink()
            except:
                pass
            self.locked = False
    
    def _process_exists(self, pid: int) -> bool:
        """Check if a process with given PID exists."""
        try:
            if os.name == 'nt':
                # Windows
                import ctypes
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.OpenProcess(0x0400, False, pid)  # PROCESS_QUERY_INFORMATION
                if handle:
                    kernel32.CloseHandle(handle)
                    return True
                return False
            else:
                # Unix
                os.kill(pid, 0)
                return True
        except (OSError, PermissionError):
            return False
    
    def __enter__(self):
        if not self.acquire():
            raise FileOperationError("Could not acquire file lock. Another instance may be running.")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False


@contextmanager
def file_lock(timeout: float = 5.0):
    """Context manager for file locking."""
    lock = FileLock(timeout=timeout)
    try:
        if not lock.acquire():
            raise FileOperationError("Could not acquire file lock. Another instance may be running.")
        yield lock
    finally:
        lock.release()


# Global lock instance for the application
_app_lock: Optional[FileLock] = None


def acquire_app_lock() -> bool:
    """Acquire the application lock. Returns True if successful."""
    global _app_lock
    if _app_lock is None:
        _app_lock = FileLock()
    return _app_lock.acquire()


def release_app_lock() -> None:
    """Release the application lock."""
    global _app_lock
    if _app_lock is not None:
        _app_lock.release()
        _app_lock = None


# ============================================================================
# Collision Detection
# ============================================================================

def calculate_collision_stats(charset: str, length: int, existing_count: int) -> dict:
    """
    Calculate collision statistics for the current configuration.
    
    Args:
        charset: The character set being used
        length: The title length
        existing_count: Number of existing titles
        
    Returns:
        Dictionary with collision statistics
    """
    total_possible = len(charset) ** length
    usage_ratio = existing_count / total_possible if total_possible > 0 else 1.0
    remaining = total_possible - existing_count
    
    # Estimate attempts needed for next unique title
    # Using birthday paradox approximation
    if usage_ratio < 0.5:
        avg_attempts = 1 / (1 - usage_ratio) if usage_ratio < 1 else float('inf')
    else:
        avg_attempts = total_possible / remaining if remaining > 0 else float('inf')
    
    return {
        'total_possible': total_possible,
        'existing_count': existing_count,
        'remaining': remaining,
        'usage_ratio': usage_ratio,
        'usage_percent': usage_ratio * 100,
        'avg_attempts': avg_attempts,
        'warning_level': get_collision_warning_level(usage_ratio)
    }


def get_collision_warning_level(usage_ratio: float) -> str:
    """
    Get the warning level based on usage ratio.
    
    Returns:
        'ok', 'warning', or 'critical'
    """
    if usage_ratio >= COLLISION_CRITICAL_THRESHOLD:
        return 'critical'
    elif usage_ratio >= COLLISION_WARNING_THRESHOLD:
        return 'warning'
    return 'ok'


def check_collision_warning(charset: str, length: int, existing_count: int) -> Optional[str]:
    """
    Check if a collision warning should be displayed.
    
    Returns:
        Warning message string, or None if no warning needed
    """
    stats = calculate_collision_stats(charset, length, existing_count)
    
    if stats['warning_level'] == 'critical':
        return (
            f"⚠️  CRITICAL: Title space is {stats['usage_percent']:.1f}% exhausted! "
            f"Only {stats['remaining']:,} unique titles remaining. "
            f"Consider increasing length or changing charset."
        )
    elif stats['warning_level'] == 'warning':
        return (
            f"⚠️  WARNING: Title space is {stats['usage_percent']:.1f}% used. "
            f"{stats['remaining']:,} unique titles remaining."
        )
    
    return None


# ============================================================================
# Custom Exceptions
# ============================================================================

class ConfigError(Exception):
    """Raised when configuration operations fail."""
    pass


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


class FileOperationError(Exception):
    """Raised when file operations fail."""
    pass


# ============================================================================
# Input Validation
# ============================================================================

def validate_length(length: Any) -> int:
    """
    Validate and return a title length value.
    
    Args:
        length: The length value to validate (can be string or int)
        
    Returns:
        Validated integer length
        
    Raises:
        ValidationError: If the length is invalid
    """
    try:
        length_int = int(length)
    except (ValueError, TypeError):
        raise ValidationError(f"Length must be a number, got: {type(length).__name__}")
    
    if length_int < MIN_LENGTH or length_int > MAX_LENGTH:
        raise ValidationError(f"Length must be between {MIN_LENGTH} and {MAX_LENGTH}, got: {length_int}")
    
    return length_int


def validate_charset_choice(choice: str) -> Tuple[str, str]:
    """
    Validate a charset selection and return the name and charset.
    
    Args:
        choice: The charset option key (e.g., "1", "2", etc.)
        
    Returns:
        Tuple of (charset_name, charset_string)
        
    Raises:
        ValidationError: If the choice is invalid
    """
    choice = str(choice).strip()
    if choice not in CHARSET_OPTIONS:
        valid_options = ", ".join(CHARSET_OPTIONS.keys())
        raise ValidationError(f"Invalid charset choice '{choice}'. Valid options: {valid_options}")
    
    return CHARSET_OPTIONS[choice]


def validate_batch_count(count: Any) -> int:
    """
    Validate a batch generation count.
    
    Args:
        count: The count value to validate
        
    Returns:
        Validated integer count
        
    Raises:
        ValidationError: If the count is invalid
    """
    try:
        count_int = int(count)
    except (ValueError, TypeError):
        raise ValidationError(f"Count must be a number, got: {type(count).__name__}")
    
    if count_int < 1:
        raise ValidationError("Count must be at least 1")
    
    if count_int > MAX_BATCH_SIZE:
        raise ValidationError(f"Count cannot exceed {MAX_BATCH_SIZE}")
    
    return count_int


def validate_menu_choice(choice: str, valid_options: list[str]) -> str:
    """
    Validate a menu choice.
    
    Args:
        choice: The user's input
        valid_options: List of valid option strings
        
    Returns:
        The validated choice string
        
    Raises:
        ValidationError: If the choice is invalid
    """
    choice = choice.strip()
    if choice not in valid_options:
        raise ValidationError(f"Invalid option. Please select from: {', '.join(valid_options)}")
    return choice


def validate_index_choice(choice: str, max_index: int) -> int:
    """
    Validate an index selection (1-based).
    
    Args:
        choice: The user's input
        max_index: The maximum valid index (inclusive)
        
    Returns:
        The validated 0-based index
        
    Raises:
        ValidationError: If the choice is invalid
    """
    try:
        index = int(choice.strip())
    except ValueError:
        raise ValidationError("Please enter a valid number")
    
    if index < 1 or index > max_index:
        raise ValidationError(f"Please enter a number between 1 and {max_index}")
    
    return index - 1  # Convert to 0-based


def validate_confirmation(response: str) -> bool:
    """
    Validate a yes/no confirmation response.
    
    Args:
        response: The user's input
        
    Returns:
        True if confirmed, False otherwise
    """
    return response.strip().lower() in ('y', 'yes')


def validate_custom_charset(charset: str) -> str:
    """
    Validate a custom character set.
    
    Args:
        charset: The custom character set string
        
    Returns:
        The validated and deduplicated charset
        
    Raises:
        ValidationError: If the charset is invalid
    """
    if not charset:
        raise ValidationError("Custom charset cannot be empty")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_chars = []
    for char in charset:
        if char not in seen:
            seen.add(char)
            unique_chars.append(char)
    
    deduplicated = ''.join(unique_chars)
    
    if len(deduplicated) < 2:
        raise ValidationError("Custom charset must contain at least 2 unique characters")
    
    # Check for printable ASCII characters only
    for char in deduplicated:
        if not (32 <= ord(char) <= 126):
            raise ValidationError(f"Character '{char}' (ord={ord(char)}) is not a printable ASCII character")
    
    return deduplicated


# ============================================================================
# Config Class
# ============================================================================

@dataclass
class Config:
    """
    Configuration container for the title generator.
    Encapsulates all settings and provides methods for persistence.
    """
    length: int = DEFAULT_LENGTH
    charset: str = field(default_factory=lambda: DEFAULT_CHARSET)
    charset_name: str = DEFAULT_CHARSET_NAME
    charset_key: str = "1"
    custom_charset: str = ""  # Stores the custom charset if option 8 is selected
    
    # Color settings
    color_enabled: bool = DEFAULT_COLOR_ENABLED
    color_success: str = field(default_factory=lambda: DEFAULT_COLOR_SUCCESS)
    color_error: str = field(default_factory=lambda: DEFAULT_COLOR_ERROR)
    color_warning: str = field(default_factory=lambda: DEFAULT_COLOR_WARNING)
    color_info: str = field(default_factory=lambda: DEFAULT_COLOR_INFO)
    color_title: str = field(default_factory=lambda: DEFAULT_COLOR_TITLE)
    color_menu: str = field(default_factory=lambda: DEFAULT_COLOR_MENU)
    
    def __post_init__(self):
        """Validate initial values and initialize color system."""
        self.length = validate_length(self.length)
        init_colors(self)
    
    def set_length(self, length: Any) -> None:
        """Set the title length with validation."""
        self.length = validate_length(length)
    
    def set_charset(self, choice: str) -> None:
        """
        Set the charset by option key with validation.
        For custom charset (option 8), use set_custom_charset() instead.
        """
        name, charset = validate_charset_choice(choice)
        if choice == "8":
            # For custom, use stored custom_charset or raise error if not set
            if not self.custom_charset:
                raise ValidationError("Custom charset not defined. Use set_custom_charset() first.")
            self.charset = self.custom_charset
            self.charset_name = f"Custom ({len(self.custom_charset)} chars)"
        else:
            self.charset = charset
            self.charset_name = name
        self.charset_key = choice
    
    def set_custom_charset(self, charset: str) -> None:
        """
        Set a custom character set.
        
        Args:
            charset: The custom characters to use for title generation
            
        Raises:
            ValidationError: If the charset is invalid
        """
        validated = validate_custom_charset(charset)
        self.custom_charset = validated
        self.charset = validated
        self.charset_name = f"Custom ({len(validated)} chars)"
        self.charset_key = "8"
    
    def set_color(self, color_type: str, color: str) -> None:
        """
        Set a specific color setting.
        
        Args:
            color_type: One of "enabled", "success", "error", "warning", "info", "title", "menu"
            color: Color name or number (or "on"/"off" for enabled)
            
        Raises:
            ValidationError: If the color type or color is invalid
        """
        color_type = color_type.lower().strip()
        
        if color_type == "enabled":
            if color.lower() in ("on", "true", "1", "yes"):
                self.color_enabled = True
            elif color.lower() in ("off", "false", "0", "no"):
                self.color_enabled = False
            else:
                raise ValidationError("Color enabled must be 'on' or 'off'")
        elif color_type == "success":
            self.color_success = validate_color(color)
        elif color_type == "error":
            self.color_error = validate_color(color)
        elif color_type == "warning":
            self.color_warning = validate_color(color)
        elif color_type == "info":
            self.color_info = validate_color(color)
        elif color_type == "title":
            self.color_title = validate_color(color)
        elif color_type == "menu":
            self.color_menu = validate_color(color)
        else:
            valid_types = "enabled, success, error, warning, info, title, menu"
            raise ValidationError(f"Invalid color type '{color_type}'. Valid types: {valid_types}")
        
        # Update global color state
        init_colors(self)
    
    def reset_to_defaults(self) -> None:
        """Reset all settings to default values."""
        self.length = DEFAULT_LENGTH
        self.charset = DEFAULT_CHARSET
        self.charset_name = DEFAULT_CHARSET_NAME
        self.charset_key = "1"
        self.custom_charset = ""
        self.color_enabled = DEFAULT_COLOR_ENABLED
        self.color_success = DEFAULT_COLOR_SUCCESS
        self.color_error = DEFAULT_COLOR_ERROR
        self.color_warning = DEFAULT_COLOR_WARNING
        self.color_info = DEFAULT_COLOR_INFO
        self.color_title = DEFAULT_COLOR_TITLE
        self.color_menu = DEFAULT_COLOR_MENU
        init_colors(self)
    
    def to_dict(self) -> dict:
        """Convert config to dictionary for serialization."""
        result = {
            "length": self.length,
            "charset_key": self.charset_key,
            "color_enabled": self.color_enabled,
        }
        # Only save custom_charset if it's being used
        if self.charset_key == "8" and self.custom_charset:
            result["custom_charset"] = self.custom_charset
        
        # Save color settings (store names, not ANSI codes)
        result["color_success"] = COLOR_NAMES.get(self.color_success, "green")
        result["color_error"] = COLOR_NAMES.get(self.color_error, "red")
        result["color_warning"] = COLOR_NAMES.get(self.color_warning, "yellow")
        result["color_info"] = COLOR_NAMES.get(self.color_info, "cyan")
        result["color_title"] = COLOR_NAMES.get(self.color_title, "bright_white")
        result["color_menu"] = COLOR_NAMES.get(self.color_menu, "blue")
        
        return result
    
    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        """Create a Config instance from a dictionary."""
        config = cls()
        
        if "length" in data:
            try:
                config.set_length(data["length"])
            except ValidationError:
                pass  # Keep default on invalid value
        
        # Load custom charset first if present
        if "custom_charset" in data:
            try:
                config.custom_charset = validate_custom_charset(data["custom_charset"])
            except ValidationError:
                pass  # Ignore invalid custom charset
        
        if "charset_key" in data:
            try:
                config.set_charset(data["charset_key"])
            except ValidationError:
                pass  # Keep default on invalid value
        
        # Load color settings
        if "color_enabled" in data:
            config.color_enabled = bool(data["color_enabled"])
        
        color_fields = ["color_success", "color_error", "color_warning", "color_info", "color_title", "color_menu"]
        for field_name in color_fields:
            if field_name in data:
                try:
                    color_code = validate_color(data[field_name])
                    setattr(config, field_name, color_code)
                except ValidationError:
                    pass  # Keep default on invalid value
        
        # Initialize global color state
        init_colors(config)
        
        return config


# ============================================================================
# File Operations with Error Handling
# ============================================================================

def load_config() -> Config:
    """
    Load configuration from file.
    
    Returns:
        Config instance with loaded or default values
        
    Note:
        Returns default config if file doesn't exist or is corrupted
    """
    if not CONFIG_FILE.exists():
        return Config()
    
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return Config.from_dict(data)
    except json.JSONDecodeError as e:
        print(f"Warning: Config file corrupted, using defaults. Error: {e}")
        return Config()
    except IOError as e:
        print(f"Warning: Could not read config file, using defaults. Error: {e}")
        return Config()


def save_config(config: Config) -> None:
    """
    Save configuration to file.
    
    Args:
        config: The Config instance to save
        
    Raises:
        FileOperationError: If the file cannot be written
    """
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, indent=2)
    except IOError as e:
        raise FileOperationError(f"Could not save configuration: {e}")


def load_titles() -> Set[str]:
    """
    Load previously generated titles from the reference file.
    
    Returns:
        Set of existing titles
    """
    titles: Set[str] = set()
    
    if not TITLES_FILE.exists():
        return titles
    
    try:
        with open(TITLES_FILE, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:  # Skip empty lines
                    titles.add(stripped)
    except IOError as e:
        print(f"Warning: Could not load titles file. Error: {e}")
    
    return titles


def save_title(title: str) -> None:
    """
    Append a new title to the reference file.
    
    Args:
        title: The title to save
        
    Raises:
        FileOperationError: If the file cannot be written
    """
    try:
        with open(TITLES_FILE, "a", encoding="utf-8") as f:
            f.write(title + "\n")
    except IOError as e:
        raise FileOperationError(f"Could not save title: {e}")


def save_all_titles(titles: Set[str]) -> None:
    """
    Rewrite the entire titles file with current set.
    
    Args:
        titles: Set of all titles to save
        
    Raises:
        FileOperationError: If the file cannot be written
    """
    try:
        with open(TITLES_FILE, "w", encoding="utf-8") as f:
            for title in sorted(titles):
                f.write(title + "\n")
    except IOError as e:
        raise FileOperationError(f"Could not save titles: {e}")


def export_to_file(filepath: Path, content: str) -> None:
    """
    Export content to a file with error handling.
    
    Args:
        filepath: Path to the output file
        content: Content to write
        
    Raises:
        FileOperationError: If the file cannot be written
    """
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    except IOError as e:
        raise FileOperationError(f"Could not export to {filepath}: {e}")


def export_to_csv(filepath: Path, headers: list[str], rows: list[list[Any]]) -> None:
    """
    Export data to a CSV file with error handling.
    
    Args:
        filepath: Path to the output file
        headers: List of column headers
        rows: List of row data
        
    Raises:
        FileOperationError: If the file cannot be written
    """
    import csv
    
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
    except IOError as e:
        raise FileOperationError(f"Could not export CSV to {filepath}: {e}")


def export_to_json(filepath: Path, data: dict) -> None:
    """
    Export data to a JSON file with error handling.
    
    Args:
        filepath: Path to the output file
        data: Dictionary to serialize
        
    Raises:
        FileOperationError: If the file cannot be written
    """
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        raise FileOperationError(f"Could not export JSON to {filepath}: {e}")


# ============================================================================
# Utility Functions
# ============================================================================

def get_export_filepath(format_ext: str, prefix: str = "titles_export") -> Path:
    """
    Generate a timestamped export filepath.
    
    Args:
        format_ext: File extension (e.g., "txt", "csv", "json")
        prefix: Filename prefix
        
    Returns:
        Path object for the export file
    """
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.{format_ext}"
    return EXPORT_DIR / filename
