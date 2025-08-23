"""
Tests for utils
"""

def test_tomllib_import():
    from nuvom.utils.compat_utils.tomllib_compat import tomllib
    assert hasattr(tomllib, 'load')
    assert callable(tomllib.load)
