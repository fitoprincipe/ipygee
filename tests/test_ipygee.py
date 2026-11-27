"""Test the ipygee package."""

import ipygee


def test_hello_world():
    """Hello world test."""
    assert ipygee.Hello().hello_world() == "hello world !"
