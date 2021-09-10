import argparse
import os
import sys

from . import visie, parser


def main(argv=None):
    if argv is None:
        argv = sys.argv

    arg_parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description='Visie is a simple initialism enumerator. It helps you name things with acronyms.',
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

  $ visie '<<. is? a?>? (efficient simple magical) recursive? (acronym initialism) (name word)? (generator enumerator)>'
""")
    arg_parser.add_argument('CONSTRAINT', type=str, nargs='+', help='a constraint (see below)')
    arg_parser.add_argument('--use-variants', '-u', action='store_true', help='use variants of the dictionary entries')
    arg_parser.add_argument('--min-length', '-m', type=int, default=4, help='minimum acronym length (default=4)')
    
    arg_parser.add_argument('--dict', '-d', type=str, default=visie.DICT_PATH,
                            help=f"path to the dictionary file (default={visie.DICT_PATH})")
    
    args = arg_parser.parse_args(argv[1:])

    constraints = []
    for arg in args.CONSTRAINT:
        constraints.append(parser.Parser(arg).parse())
    if len(constraints) == 1:
        constraints = constraints[0]
    else:
        constraints = visie.AnyOfConstraint(constraints)

    if not os.path.exists(args.dict):
        sys.stderr.write(f"{args.dict} does not exist!\n\nEnsure that a word list is installed.\nOn most Linux "
                         f"distributions, try:\n    `apt-cache search wordlist|grep ^w|sort`\n\n")
        exit(1)

    try:
        for acronym in visie.generate(
                constraints,
                min_length=args.min_length,
                use_variants=args.use_variants,
                dict_path=args.dict
        ):
            sys.stdout.write(f"{acronym.name()}: {' '.join(acronym)}\n")
    except parser.ParseException as e:
        sys.stderr.write(str(e))
        exit(1)
    except KeyboardInterrupt:
        exit(1)


if __name__ == '__main__':
    main(sys.argv)
