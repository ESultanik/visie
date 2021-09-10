import itertools
from typing import Callable, Dict, Hashable, Iterable, Iterator, List, Optional, Set, Tuple, TypeVar

VARIATION_MAPPING: Dict[str, Tuple[str, ...]] = {
    'c': ('k',),
    'k': ('c',),
    'i': ('ee', 'ii', 'y'),
    'ee': ('i', 'ii', 'y'),
    'oo': ('u',),
    'a': ('u', 'o'),
    'o': ('u', 'a'),
    'u': ('a', 'o', 'oo'),
    'j': ('g', 'gg'),
    'g': ('gg',),
    'h': ('kh',),
    'kh': ('h', 'ch'),
    'y': ('ee', 'i', 'ii'),
    'sh': ('xi',),
    'xi': ('sh',),
    'w': ('ui',),
    'ui': ('w',),
}

T = TypeVar("T", bound=Hashable)


def unique_everseen(iterable: Iterable[T], key: Optional[Callable[[T], Hashable]] = None) -> Iterator[T]:
    """List unique elements, preserving order. Remember all elements ever seen."""
    # unique_everseen('AAAABBBCCDAABBB') --> A B C D
    # unique_everseen('ABBCcAD', str.lower) --> A B C D
    seen: Set[Hashable] = set()
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


def generate_variants(word: str) -> Iterator[str]:
    word = word.strip().lower()
    if not word:
        return
    variations: List[Tuple[str, ...]] = [(word,)]
    skip = False
    for c, next_c in zip(word, word[1:] + ' '):
        if skip:
            skip = False
            continue
        skip = False
        if c + next_c in VARIATION_MAPPING:
            variations.append(VARIATION_MAPPING[c + next_c])
            skip = True
        elif c in VARIATION_MAPPING:
            variations.append(VARIATION_MAPPING[c])
        else:
            variations.append((c,))

    yield from unique_everseen(("".join(s) for s in itertools.product(*variations)))
