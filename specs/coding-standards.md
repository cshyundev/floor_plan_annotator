# Coding Standards

This document defines the coding standards and conventions for the Floor Plan Annotator project.

## Python Style Guide

All Python code in this project must follow the **Google Python Style Guide**.

Reference: https://google.github.io/styleguide/pyguide.html

## File Organization

### File Length Limit

**Maximum: 500 lines per file**

Files exceeding this limit must be refactored into smaller, more focused modules.

**Line counting includes:**
- Code lines
- Comment lines
- Blank lines
- Docstrings

**Refactoring strategies when approaching the limit:**
1. Extract helper functions into separate utility modules
2. Split large classes into multiple smaller classes
3. Move related functionality into submodules
4. Consider if the module has too many responsibilities (Single Responsibility Principle)

## Documentation

### Docstrings

**Every function must have a docstring.**

#### Single-line Docstrings

For simple, self-explanatory functions:

```python
def get_name() -> str:
    """Returns the user's name."""
    return self._name

def is_valid() -> bool:
    """Checks if the current state is valid."""
    return self._state == State.VALID
```

#### Multi-line Docstrings

For complex functions with parameters, return values, or exceptions:

```python
def process_point_cloud(file_path: str, resolution: float = 0.01) -> np.ndarray:
    """Processes a point cloud file and returns a 2D projection.

    Loads the point cloud from the specified file, applies filtering,
    and projects it onto a 2D plane with the given resolution.

    Args:
        file_path: Path to the point cloud file (PLY, PCD, OBJ, or STL).
        resolution: Size of one pixel in meters. Defaults to 0.01 (1cm).

    Returns:
        A 2D numpy array representing the projected density map.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If the resolution is not positive.
    """
    if resolution <= 0:
        raise ValueError("Resolution must be positive")
    # ... implementation
```

#### Class and Module Docstrings

```python
"""Point cloud slicing and projection module.

This module provides functionality for slicing 3D point clouds at
specified heights and projecting them onto 2D images.
"""

class SliceEngine:
    """Engine for processing and slicing point cloud data.

    The SliceEngine loads point cloud data, performs height-based
    slicing operations, and projects 3D points onto 2D images.

    Attributes:
        _pcd: Open3D PointCloud object.
        _points: Nx3 numpy array of point coordinates.
        _colors: Nx3 numpy array of point colors.
    """
```

## Type Hints

### Requirements

1. **All function parameters must have type hints**
2. **All function return values must have type hints**
3. Use `None` for functions that don't return a value

### Examples

```python
from typing import List, Dict, Optional, Tuple, Union

def simple_function(name: str, count: int) -> str:
    """Simple function with basic types."""
    return name * count

def complex_function(
    items: List[str],
    config: Dict[str, int],
    threshold: Optional[float] = None
) -> Tuple[int, str]:
    """Complex function with advanced types."""
    pass

def no_return_function(data: np.ndarray) -> None:
    """Function that doesn't return a value."""
    print(data.shape)
```

### Type Aliases

For complex types, define type aliases:

```python
from typing import List, Tuple

Point2D = Tuple[float, float]
PointList = List[Point2D]

def transform_points(points: PointList) -> PointList:
    """Transforms a list of 2D points."""
    pass
```

## Code Formatting

### Line Length

**Maximum: 150 characters per line**

This is a balance between PEP 8's strict 79-character limit and modern wide-screen readability.

#### Breaking Long Lines

```python
# Function calls
result = some_long_function_name(
    first_argument,
    second_argument,
    third_argument,
    keyword_arg=value
)

# Lists and dictionaries
my_list = [
    "first_element",
    "second_element",
    "third_element",
]

my_dict = {
    "key1": "value1",
    "key2": "value2",
    "key3": "value3",
}

# Long expressions
total = (
    first_variable
    + second_variable
    + third_variable
    - fourth_variable
)

# Long conditionals
if (
    condition_one
    and condition_two
    and condition_three
):
    do_something()
```

### Imports

```python
# Standard library imports
import os
import sys
from typing import List, Dict

# Third-party imports
import numpy as np
from PyQt6.QtWidgets import QWidget

# Local imports
from src.core.processor import SliceEngine
from src.model.data import Wall, Room
```

### Naming Conventions

Follow Google Style Guide:

```python
# Modules and packages: lowercase_with_underscores
# my_module.py

# Classes: CapitalizedWords
class PointCloudProcessor:
    pass

# Functions and methods: lowercase_with_underscores
def load_point_cloud(file_path: str) -> np.ndarray:
    pass

# Constants: UPPERCASE_WITH_UNDERSCORES
MAX_FILE_SIZE = 500
DEFAULT_RESOLUTION = 0.01

# Private methods/attributes: _leading_underscore
def _internal_helper(self) -> None:
    pass

# Instance variables: lowercase_with_underscores
self.point_cloud = None
```

## Linting with Flake8

### Configuration

The project uses Flake8 for code quality checks with the following configuration (`.flake8`):

```ini
[flake8]
max-line-length = 150
ignore =
    E203,  # Whitespace before ':' (conflicts with Black formatter)
    W503   # Line break before binary operator (modern style)
exclude =
    .git,
    __pycache__,
    .venv,
    build,
    dist
```

### Running Flake8

```bash
# Check all Python files
flake8 src/

# Check specific file
flake8 src/gui/main_window.py

# Auto-fix some issues (if using autopep8)
autopep8 --in-place --max-line-length 150 src/gui/main_window.py
```

### Handling Flake8 Warnings

**Default approach:**
- Fix code to comply with the warning

**For warnings that conflict with modern style:**
1. Discuss with team/reviewer
2. If agreed, add to ignore list in `.flake8`
3. Document the decision

**Common ignores:**
- `E203`: Whitespace before ':' (conflicts with Black)
- `W503`: Line break before binary operator (modern preference)
- `F401` in `__init__.py`: Unused imports (for API re-exports)

## Code Quality Checklist

Before committing code, verify:

- [ ] File length ≤ 500 lines
- [ ] All functions have docstrings
- [ ] All parameters have type hints
- [ ] All return values have type hints
- [ ] Line length ≤ 150 characters
- [ ] Flake8 passes with no errors
- [ ] Code follows Google Python Style Guide
- [ ] Imports are organized correctly
- [ ] Naming conventions are followed

## Using the Coding Rules Skill

The project includes a `/coding-rules` skill to automate verification:

```bash
# Check specific file
/coding-rules src/gui/main_window.py

# Check all files
/coding-rules

# Check and fix issues
/coding-rules --fix

# Generate report
/coding-rules --report
```

## Continuous Integration

Consider adding these checks to CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
- name: Check code quality
  run: |
    flake8 src/
    # Add mypy for type checking
    mypy src/
```

## References

- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [PEP 8 – Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [PEP 484 – Type Hints](https://peps.python.org/pep-0484/)
- [Flake8 Documentation](https://flake8.pycqa.org/)
