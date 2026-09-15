import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

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
""",
    )
    arg_parser.add_argument("CONSTRAINT", type=str, nargs="+", help="a constraint (see below)")
    arg_parser.add_argument(
        "--use-variants", "-u", action="store_true", help="use variants of the dictionary entries"
    )
    arg_parser.add_argument(
        "--min-length", "-m", type=int, default=4, help="minimum acronym length (default=4)"
    )

    arg_parser.add_argument(
        "--dict",
        "-d",
        type=str,
        default=visie.DICT_PATH,
        help=f"path to the dictionary file (default={visie.DICT_PATH})",
    )

    return arg_parser


def _parse_constraints(arguments: Sequence[str]) -> visie.Constraint:
    constraints = [parser.Parser(arg).parse() for arg in arguments]
    if len(constraints) == 1:
        return constraints[0]
    return visie.AnyOfConstraint(constraints)


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
        constraints = _parse_constraints(args.CONSTRAINT)

        if not Path(args.dict).exists():
            sys.stderr.write(
                f"{args.dict} does not exist!\n\nEnsure that a word list is installed.\nOn most "
                f"Linux distributions, try:\n    `apt-cache search wordlist|grep ^w|sort`\n\n"
            )
            return 1

        for acronym in visie.generate(
            constraints,
            min_length=args.min_length,
            use_variants=args.use_variants,
            dict_path=args.dict,
        ):
            sys.stdout.write(f"{acronym.name()}: {' '.join(acronym)}\n")
    except parser.ParseException as e:
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
