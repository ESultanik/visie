import itertools
from collections.abc import Callable, Hashable, Iterable, Iterator
from typing import TypeVar

VARIATION_MAPPING: dict[str, tuple[str, ...]] = {
    "c": ("k",),
    "k": ("c",),
    "i": ("ee", "ii", "y"),
    "ee": ("i", "ii", "y"),
    "oo": ("u",),
    "a": ("u", "o"),
    "o": ("u", "a"),
    "u": ("a", "o", "oo"),
    "j": ("g", "gg"),
    "g": ("gg",),
    "h": ("kh",),
    "kh": ("h", "ch"),
    "y": ("ee", "i", "ii"),
    "sh": ("xi",),
    "xi": ("sh",),
    "w": ("ui",),
    "ui": ("w",),
}

T = TypeVar("T", bound=Hashable)


def unique_everseen(
    iterable: Iterable[T], key: Callable[[T], Hashable] | None = None
) -> Iterator[T]:
    """List unique elements, preserving order. Remember all elements ever seen."""
    # unique_everseen('AAAABBBCCDAABBB') --> A B C D
    # unique_everseen('ABBCcAD', str.lower) --> A B C D
    seen: set[Hashable] = set()
    seen_add: Callable[[Hashable], None] = seen.add
    if key is None:
        for element in itertools.filterfalse(seen.__contains__, iterable):
            seen_add(element)
            yield element
    else:
        for element in iterable:
            k = key(element)
            if k not in seen:
                seen_add(k)
                yield element


def _spellings(word: str) -> list[tuple[str, ...]]:
    """Split a word into positions, each listing its original spelling then its alternatives.

    Digraphs in `VARIATION_MAPPING` are consumed as a single position, so `sh` yields one
    position spelled either `sh` or `xi` rather than two independent positions.

    Args:
        word: A lowercase word.

    Returns:
        One tuple per position, whose first element is always the original spelling.
    """
    positions: list[tuple[str, ...]] = []
    skip = False
    for c, next_c in zip(word, word[1:] + " ", strict=True):
        if skip:
            skip = False
            continue
        digraph = c + next_c
        if digraph in VARIATION_MAPPING:
            positions.append((digraph, *VARIATION_MAPPING[digraph]))
            skip = True
        elif c in VARIATION_MAPPING:
            positions.append((c, *VARIATION_MAPPING[c]))
        else:
            positions.append((c,))
    return positions


def _expand(
    positions: list[tuple[str, ...]],
    min_suffix: list[int],
    index: int,
    prefix: str,
    max_length: int | None,
) -> Iterator[str]:
    """Walk the spellings depth first, pruning prefixes that cannot fit within `max_length`."""
    if index >= len(positions):
        yield prefix
        return
    for spelling in positions[index]:
        candidate = prefix + spelling
        if max_length is not None and len(candidate) + min_suffix[index + 1] > max_length:
            continue
        yield from _expand(positions, min_suffix, index + 1, candidate, max_length)


def generate_variants(word: str, max_length: int | None = None) -> Iterator[str]:
    """Enumerate alternative spellings of `word`, starting with `word` itself.

    Args:
        word: The word to vary. Leading and trailing whitespace is stripped and the
            word is lowercased.
        max_length: If given, only variants of at most this many characters are
            generated. Prefixes that cannot fit are abandoned before they are expanded,
            which keeps long words from producing millions of discarded strings.

    Yields:
        Each distinct variant exactly once, in depth-first order.
    """
    word = word.strip().lower()
    if not word:
        return
    positions = _spellings(word)
    min_suffix = [0] * (len(positions) + 1)
    for i in reversed(range(len(positions))):
        min_suffix[i] = min_suffix[i + 1] + min(len(s) for s in positions[i])
    yield from unique_everseen(_expand(positions, min_suffix, 0, "", max_length))
