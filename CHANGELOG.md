# Changelog

This project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-09-15

The first release since 2021-09-10. It modernizes the package, fixes every bug found in an audit of
the existing code, and adds backronym generation.

### Added

- `--backronym`/`-b` expands an acronym into phrases whose word initials spell it, for example
  `visie -b HOPE`. Results are sampled and then ranked, because the full search space for a
  four-letter acronym holds about 3 × 10^16 phrases.
- `--rank` chooses how sampled phrases are ranked: `brevity`, `rhyme`, `rhythm`, or `harmony`
  (the default). The rhyme and rhythm metrics are orthographic approximations of pronunciation,
  so they miss rhymes that spelling hides and can report ones that it invents.
- `--allow-similar` turns off the guard that stops the ranked results from sharing a word ending.
  Without the guard, rhyme ranking returns phrases that all end in `-ly`, `-able`, or `-ic`.
- `--seed` makes sampled output reproducible.
- `--limit`/`-n` sets how many results to print.
- `--min-word-length` sets the shortest word a backronym may use. It is separate from
  `--min-length`, which applies only to acronym enumeration.
- `--version` reports the installed version.
- `VISIE_DICT` names the wordlist to read, and visie falls back to a search path of common
  locations. Previously the path `/usr/share/dict/words` was the only one it would try.
- A `py.typed` marker, so type checkers use the package's annotations.

### Changed

- Python 3.11 or later is now required. Versions 3.6 through 3.10 are no longer supported.
- Packaging moved from `setup.py` to `pyproject.toml`, built with hatchling.
- Errors now name every wordlist path that visie tried, and mention `VISIE_DICT`.

### Fixed

- `--use-variants` produced no output at all. Its expansion seeded the product with the whole
  original word, so no variant ever matched. The corrected expansion is bounded by the longest
  acronym that can match, which keeps the run near a second instead of generating 3 × 10^8 strings.
- Malformed constraints raised a traceback instead of reporting an error. Parsing ran outside the
  block that caught parse errors, and the parser raised bare `Exception` in three places.
- `visie '()'` raised `ValueError` from taking the minimum of an empty sequence. Empty groups are
  now rejected while parsing, with the position named.
- The caret in a tokenizer error pointed at the wrong character, and pointed into the wrong line
  when the constraint spanned several lines.
- Iterating a `Tokenizer` raised `RuntimeError`, because it let `StopIteration` escape a generator.
- Piping output to a command that exits early, such as `head`, raised `BrokenPipeError`.
- The command used the `site` builtin `exit()` rather than returning an exit status.
- The wordlist was read with the locale's encoding and loaded into memory in full.
- `import visie` exported `os`, `itertools`, and several typing names alongside the real API.

### Removed

- `AnyOrderedConstraint`, which no syntax could reach and which duplicated `OrderedConstraint`.

[Unreleased]: https://github.com/ESultanik/visie/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/ESultanik/visie/compare/v0.1.1...v0.2.0
