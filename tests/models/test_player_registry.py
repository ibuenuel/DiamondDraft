"""Unit tests for the player registry (register / resolve)."""
from __future__ import annotations

import pytest

from diamond_draft.models.player import Batter, Pitcher
from diamond_draft.models import player_registry
from diamond_draft.models.player_registry import resolve, register


def test_resolve_batter_returns_batter_class():
    assert resolve("Batter") is Batter


def test_resolve_pitcher_returns_pitcher_class():
    assert resolve("Pitcher") is Pitcher


def test_resolve_unknown_type_raises_key_error():
    with pytest.raises(KeyError):
        resolve("UnknownXYZ")


def test_resolve_error_message_lists_registered_types():
    with pytest.raises(KeyError) as exc_info:
        resolve("GhostPlayer")
    msg = str(exc_info.value)
    assert "Batter" in msg
    assert "Pitcher" in msg


def test_register_same_class_twice_is_noop():
    # Registering Batter under "Batter" again must not raise
    register("Batter")(Batter)  # should silently succeed


def test_register_duplicate_key_different_class_raises_key_error():
    class DummyPlayer(Batter):
        pass

    # Temporarily register a dummy class under a fresh key, then
    # try to overwrite it with a different class.
    register("_TempKey")(DummyPlayer)
    try:
        with pytest.raises(KeyError):
            register("_TempKey")(Batter)  # different class → must raise
    finally:
        # Clean up: remove the test key so it doesn't pollute other tests
        player_registry._REGISTRY.pop("_TempKey", None)
