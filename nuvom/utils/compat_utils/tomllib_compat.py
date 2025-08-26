"""
Compatibility module for safely importing tomllib for different Python versions.

This module provides unified `tomllib` import that works for Python 3.10 and later.
For Python < 3.11, it will falls back to the `tomli` library, which must be installed.

Usage:
    from nuvom.utils.compat_utils.tomllib_compat import tomllib
"""

try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        raise ModuleNotFoundError(
            "Failed to import tomllib. For Python < 3.11, please install `tomli` "
            "run `pip install tomli.`"
        )
