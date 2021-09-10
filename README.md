# Visie is a Simple Initialism Enumerator

[![PyPI version](https://badge.fury.io/py/visie.svg)](https://badge.fury.io/py/visie)
[![Tests](https://github.com/esultanik/visie/workflows/tests/badge.svg)](https://github.com/esultanik/visie/actions)

It helps you name things with acronyms.

## Installation

```
pip3 install visie
```

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

## License

Visie is licensed and distributed under the [AGPLv3](LICENSE) license. [Contact us](https://www.sultanik.com/) if you’re looking for an exception to the terms.
