import argparse
import os
import sys
from collections.abc import Sequence

from . import parser, visie


def _build_arg_parser() -> argparse.ArgumentParser:
    arg_parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description=(
            "Visie is a simple initialism enumerator. It helps you name things with acronyms."
        ),
        epilog="""By default, visie will find initialisms and acronyms
that contain any subset of the provided words, in any order:

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

Wrapping words in angle brackets "<...>"
means that they must all occur, in order:

  $ visie 'pleasing orange home <noise expeller>'
  HONE: home orange noise expeller
  PHONE: pleasing home orange noise expeller
  PONE: pleasing orange noise expeller

Words in square brackets "[...]" must all occur, but can be in any order:

  $ visie '[pleasing orange home <noise expeller>]'
  PHONE: pleasing home orange noise expeller

Parenthesis "(...)" means exactly one of the contained elements will be used:

  $ visie --min-length 3 'pleasing home (orange noise expeller)'
  HEP: home expeller pleasing
  HOP: home orange pleasing
  PHO: pleasing home orange
  POH: pleasing orange home

Elements in curly braces "{...}" can occur in any order and any quantity:

  $ visie 'pleasing home ({orange noise} expeller)'
  PHON: pleasing home orange noise

Elements followed by a question mark are optional:

  $ visie '<diaphone is? a? [pleasing orange home noise expeller]>'
  DIAPHONE: diaphone is a pleasing home orange noise expeller

Finally, you can create recursive acronyms by using a period as a wildcard:

  $ visie '<. is? a? [pleasing orange home noise expeller]>'
  DIAPHONE: d is a pleasing home orange noise expeller
  WANHOPE: w a noise home orange pleasing expeller

The name `visie` was discovered this way:

  $ visie '<<. is? a?>? (efficient simple magical) recursive? """
        """(acronym initialism) (name word)? (generator enumerator)>'

With --backronym, visie works the other way around: it reads
CONSTRAINT as an acronym and expands it into phrases whose
word initials spell it:

  $ visie --backronym HOPE --seed 8 -n 5
  HOPE: hyphenation omission preclassification expeditation
  HOPE: hastatosagittate ontogenetically phantasmically elliptically
  HOPE: hermitical outstart Petrarchistical eremitical
  HOPE: holomorphosis odontoplerosis paradidymis epitasis
  HOPE: Heliolitidae overemptiness powderiness expansiveness

The expansions are far too many to search exhaustively, so visie
samples 100,000 of them and prints the best ranked of the sample.
--rank picks what the ranking prefers: brevity for short words,
rhyme for words that end alike, rhythm for words of equal syllable
counts, and harmony, the default, for a blend of the three:

  $ visie -b HOPE --seed 8 --rank brevity -n 5
  HOPE: Helen ogmic pause epulo
  HOPE: haine Olga phase estufa
  HOPE: hunchy oary perique else
  HOPE: Hugh oristic Pomona exon
  HOPE: hoop ought prendre event

Rhyme, rhythm and harmony read spelling as a stand in for sound, so
they miss rhymes that spelling hides, such as through and blue, and
report rhymes that do not sound alike, such as though and rough.
They also tend to pick phrases that all end the same way, so visie
prints at most one phrase per dominant word ending. Pass
--allow-similar for the ranking as it stands.

Every run draws a new sample; pass --seed to repeat an earlier one.
The quality of the results is bounded by the wordlist.
""",
    )
    arg_parser.add_argument("CONSTRAINT", type=str, nargs="+", help="a constraint (see below)")
    arg_parser.add_argument(
        "--use-variants", "-u", action="store_true", help="use variants of the dictionary entries"
    )
    arg_parser.add_argument(
        "--min-length",
        "-m",
        type=int,
        default=4,
        help=(
            "minimum number of letters in a generated acronym (default=4)\n"
            "this does not apply to --backronym, whose acronym is CONSTRAINT itself"
        ),
    )
    arg_parser.add_argument(
        "--backronym",
        "-b",
        action="store_true",
        help=(
            "read CONSTRAINT as an acronym and expand it into phrases\nwhose word initials spell it"
        ),
    )
    arg_parser.add_argument(
        "--limit",
        "-n",
        type=int,
        default=10,
        help="maximum number of backronyms to print (default=10)",
    )
    arg_parser.add_argument(
        "--rank",
        type=str,
        choices=visie.RANK_MODES,
        default=visie.DEFAULT_RANK,
        help=(
            f"what the backronym ranking prefers (default={visie.DEFAULT_RANK})\n"
            "brevity: short words\n"
            "rhyme:   words that end alike\n"
            "rhythm:  words of equal syllable counts\n"
            "harmony: a blend of the three"
        ),
    )
    arg_parser.add_argument(
        "--allow-similar",
        action="store_true",
        help=(
            "print the best ranked backronyms even when they all end the same way\n"
            "by default, visie prints at most one backronym per dominant word ending"
        ),
    )
    arg_parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="seed the backronym sampler, so that a run repeats an earlier one",
    )
    arg_parser.add_argument(
        "--min-word-length",
        type=int,
        default=4,
        help="minimum number of letters in each word of a backronym (default=4)",
    )

    search_path = "\n".join(f"  {path}" for path in visie.DICT_SEARCH_PATH)
    arg_parser.add_argument(
        "--dict",
        "-d",
        type=str,
        default=None,
        help=(
            f"path to the dictionary file\nby default, visie reads the path from the "
            f"{visie.DICT_ENV_VAR} environment\nvariable, and falls back to the first of these "
            f"that it can read:\n{search_path}"
        ),
    )

    return arg_parser


def _parse_constraints(arguments: Sequence[str]) -> visie.Constraint:
    constraints = [parser.Parser(arg).parse() for arg in arguments]
    if len(constraints) == 1:
        return constraints[0]
    return visie.AnyOfConstraint(constraints)


def _write_backronyms(args: argparse.Namespace) -> None:
    for acronym in visie.backronyms(
        "".join(args.CONSTRAINT),
        min_word_length=args.min_word_length,
        limit=args.limit,
        seed=args.seed,
        rank=args.rank,
        allow_similar=args.allow_similar,
        dict_path=args.dict,
    ):
        sys.stdout.write(f"{acronym.name()}: {' '.join(acronym)}\n")


def _discard_stdout() -> None:
    """Point the stdout file descriptor at the null device.

    Once the process reading our output has closed the pipe, whatever is still buffered can
    never be written. Redirecting the descriptor lets interpreter shutdown flush that buffer
    without reporting a second, confusing error on top of the one already handled.
    """
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, sys.stdout.fileno())


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line interface.

    Args:
        argv: The full argument vector, including the program name. Defaults to `sys.argv`.

    Returns:
        The process exit status.
    """
    if argv is None:
        argv = sys.argv

    args = _build_arg_parser().parse_args(argv[1:])

    try:
        if args.backronym:
            _write_backronyms(args)
        else:
            constraints = _parse_constraints(args.CONSTRAINT)

            for acronym in visie.generate(
                constraints,
                min_length=args.min_length,
                use_variants=args.use_variants,
                dict_path=args.dict,
            ):
                sys.stdout.write(f"{acronym.name()}: {' '.join(acronym)}\n")
    except (
        parser.ParseException,
        visie.DictionaryNotFoundError,
        visie.UnmatchedLetterError,
    ) as e:
        sys.stderr.write(f"{e}\n")
        return 1
    except KeyboardInterrupt:
        return 130  # see: https://tldp.org/LDP/abs/html/exitcodes.html#EXITCODESREF
    except BrokenPipeError:
        _discard_stdout()
        return 141  # 128 + SIGPIPE

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
