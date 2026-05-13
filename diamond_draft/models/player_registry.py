"""Player subclass registry for deserialisation.

Decouples ``Player.from_dict`` from concrete subclass names using the
Registry pattern. Any new ``Player`` subclass is registered once via the
``@register`` decorator; ``Player.from_dict`` resolves the correct class
at runtime without a hard-coded conditional.

Usage example::

    from diamond_draft.models.player_registry import register, resolve

    @register("Batter")
    @dataclass(eq=False)
    class Batter(Player):
        ...

    player_cls = resolve(data["type"])   # returns Batter or Pitcher
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from diamond_draft.models.player import Player

# Internal mapping — module-private; consumers use register() / resolve().
_REGISTRY: dict[str, type[Player]] = {}


def register(type_name: str):
    """Return a class decorator that registers a Player subclass under *type_name*.

    The *type_name* must match the string written to the ``"type"`` field by
    ``Player.to_dict`` (which uses ``cls.__name__``). Using the class name as
    the registry key guarantees backward compatibility with existing save files.

    Args:
        type_name: The serialised type identifier (e.g. ``"Batter"``).
            Must be unique across all registered subclasses.

    Returns:
        A decorator that registers the class and returns it unchanged,
        so the decorator is transparent to the rest of the module.

    Raises:
        KeyError: If *type_name* is already registered to a *different* class.
            Re-registering the same class under the same key is a no-op.
    """
    def _decorator(cls: type[Player]) -> type[Player]:
        existing = _REGISTRY.get(type_name)
        if existing is not None and existing is not cls:
            raise KeyError(
                f"Player type '{type_name}' is already registered to "
                f"'{existing.__name__}'. Each type name must be unique."
            )
        _REGISTRY[type_name] = cls
        return cls

    return _decorator


def resolve(type_name: str) -> type[Player]:
    """Return the concrete Player subclass registered under *type_name*.

    Args:
        type_name: The ``"type"`` string read from a serialised player dict.

    Returns:
        The Player subclass that was decorated with ``@register(type_name)``.

    Raises:
        KeyError: If *type_name* has not been registered. The error message
            includes the sorted list of known type names to aid debugging.
    """
    try:
        return _REGISTRY[type_name]
    except KeyError:
        known = sorted(_REGISTRY.keys())
        raise KeyError(
            f"Unknown player type '{type_name}'. "
            f"Registered types: {known}"
        ) from None
