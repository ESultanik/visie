# Visie is a Simple Initialism Enumerator

[![PyPI version](https://badge.fury.io/py/visie.svg)](https://badge.fury.io/py/visie)
[![Tests](https://github.com/esultanik/visie/workflows/tests/badge.svg)](https://github.com/esultanik/visie/actions)

It helps you name things with acronyms.

## Installation

```
pip3 install visie
```

## Wordlist

Visie builds acronyms from a plain text wordlist that holds one word per line. It reads the first
wordlist it can open, in this order:

1. The path you pass with `--dict`, or `-d`.
2. The path in the `VISIE_DICT` environment variable.
3. `/usr/share/dict/words`, then `/usr/share/dict/web2`, then `/usr/dict/words`.

```
$ visie --dict /usr/share/dict/web2 pleasing orange home noise expeller
$ VISIE_DICT=/usr/share/dict/web2 visie pleasing orange home noise expeller
```

`--dict` and `VISIE_DICT` each name the one wordlist to use, so visie reports an error instead of
falling back to another path when the wordlist you name is missing or unreadable. When visie finds
no readable wordlist at all, it lists every path it tried and exits with status 1.

macOS ships `/usr/share/dict/words`. On Debian and Ubuntu, install a wordlist package such as
`wamerican`. On Windows, and on container images that carry no wordlist, download a wordlist and
set `VISIE_DICT` to its path.

## Examples

By default, visie will find initialisms and acronyms
that contain any subset of the provided words, in any order:

```
$ visie pleasing orange home noise expeller
HONE: home orange noise expeller
HOPE: home orange pleasing expeller
NOPE: noise orange pleasing expeller
OPEN: orange pleasing expeller noise
PEHO: pleasing expeller home orange
PEON: pleasing expeller orange noise
PHEON: pleasing home expeller orange noise
PHON: pleasing home orange noise
PHONE: pleasing home orange noise expeller
PONE: pleasing orange noise expeller
```

Wrapping words in angle brackets `<...>`
means that they must all occur, in order:

```
$ visie 'pleasing orange home <noise expeller>'
HONE: home orange noise expeller
PHONE: pleasing home orange noise expeller
PONE: pleasing orange noise expeller
```

Words in square brackets `[...]` must all occur, but can be in any order:

```
$ visie '[pleasing orange home <noise expeller>]'
PHONE: pleasing home orange noise expeller
```

Parenthesis `(...)` means exactly one of the contained elements will be used:

```
$ visie --min-length 3 'pleasing home (orange noise expeller)'
HEP: home expeller pleasing
HOP: home orange pleasing
PHO: pleasing home orange
POH: pleasing orange home
```

Elements in curly braces `{...}` can occur in any order and any quantity:

```
$ visie 'pleasing home ({orange noise} expeller)'
PHON: pleasing home orange noise
```

Elements followed by a question mark are optional:

```
$ visie '<diaphone is? a? [pleasing orange home noise expeller]>'
DIAPHONE: diaphone is a pleasing home orange noise expeller
```

Finally, you can create recursive acronyms by using a period as a wildcard:

```
$ visie '<. is? a? [pleasing orange home noise expeller]>'
DIAPHONE: d is a pleasing home orange noise expeller
WANHOPE: w a noise home orange pleasing expeller
```

The name `visie` was discovered this way:

```
$ visie '<<. is? a?>? (efficient simple magical) recursive? (acronym initialism) (name word)? (generator enumerator)>'
```

## Variant spellings

Pass `--use-variants`, or `-u`, to match respellings of each wordlist entry as well as the entry
itself, such as `c` for `k`, or `y` for `ee`. Variants turn up acronyms that an exact match misses,
and they make the search slower:

```
$ visie --use-variants pleasing orange home noise expeller
EPHO: expeller pleasing home orange
HEOP: home expeller orange pleasing
HONE: home orange noise expeller
HOPE: home orange pleasing expeller
NOPE: noise orange pleasing expeller
NEOP: noise expeller orange pleasing
NEPO: noise expeller pleasing orange
OPEN: orange pleasing expeller noise
PONE: pleasing orange noise expeller
PEON: pleasing expeller orange noise
PEHO: pleasing expeller home orange
PHEON: pleasing home expeller orange noise
PHON: pleasing home orange noise
PHONE: pleasing home orange noise expeller
```

## Backronyms

Pass `--backronym`, or `-b`, to work the other way around. Give visie an acronym and it finds
phrases whose word initials spell it:

```
$ visie --backronym HOPE --seed 8
HOPE: Helen ogmic pause epulo
HOPE: haine Olga phase estufa
HOPE: hunchy oary perique else
HOPE: Hugh oristic Pomona exon
HOPE: hoop ought prendre event
HOPE: howkit Osage platy emcee
HOPE: hend Owen plan elucidate
HOPE: hulk octuor peres ectype
HOPE: hopper orlo Pygmy enraged
HOPE: hoot ovist Polabian elope
```

The space of expansions is far too large to search exhaustively: four letters over a wordlist of
a quarter of a million words hold about 2.9e16 phrases. Visie therefore samples 100,000 of them
at random and prints the best ranked of the sample. Ranking prefers short words, which stands in
for common words. It is a crude stand in: a plain wordlist carries no frequency data, so visie
cannot tell a familiar word from an obscure one, and the quality of the results is bounded by the
wordlist you point it at. Run the command a few times, and expect to discard most of what it
prints.

Every run draws a new sample. Pass `--seed` with a whole number to repeat an earlier run. Pass
`--limit`, or `-n`, to change how many phrases visie prints, and `--min-word-length` to raise the
length of the shortest word it draws on:

```
$ visie -b HOPE --seed 8 --min-word-length 6 -n 3
HOPE: hexact omnist praiser exsect
HOPE: handful offish patter echoer
HOPE: hander obelism Phoebe epizoa
```

`--min-length`, or `-m`, sets the shortest acronym of the default search, so it has no meaning
here: a backronym is as long as the acronym you pass. When no word in the wordlist begins with one
of the letters, visie names that letter and exits with status 1:

```
$ visie -b HOPE --min-word-length 24
cannot expand 'H': the wordlist holds no word of 24 or more letters that begins with it
```

## License

Visie is licensed and distributed under the [AGPLv3](LICENSE) license. [Contact us](https://www.sultanik.com/) if you’re looking for an exception to the terms.
