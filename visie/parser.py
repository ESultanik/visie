from typing import Iterable, Iterator, List, Optional, Type, TypeVar, Union

from . import visie


class ParseException(Exception):
    pass


class Token:
    def __init__(self, token: str, offset: int, fulltext: str):
        self.token: str = token
        self.offset: int = offset
        self.fulltext: str = fulltext

    def __str__(self):
        num_newlines = self.fulltext
        return f"{self.fulltext}\n{' '*self.offset}{'^'*len(self.token)}"

    def __repr__(self):
        return f"{type(self).__name__}(token={self.token!r}, offset={self.offset!r}, fulltext={self.fulltext!r})"


def tokenize(text: str) -> Iterator[Token]:
    word = ''
    for i, c in enumerate(text):
        if c in ('(', ')', '[', ']', '{', '}', '<', '>', '?', '.'):
            if word:
                yield Token(word, i - len(word), text)
                word = ''
            yield Token(c, i, text)
        elif c == ' ' or c == '\t' or c == '\n' or c == '\r':
            if word:
                yield Token(word, i - len(word), text)
                word = ''
            continue
        elif ord('a') <= ord(c.lower()) <= ord('z'):
            word += c
        else:
            raise ParseException(f"{text}\n{' '*(len(text)-i)}^\nIllegal token \"{c}\"")
    if word:
        yield Token(word, len(text) - len(word), text)


class Tokenizer:
    def __init__(self, text: Union[str, Iterable[Token]]):
        if isinstance(text, str):
            text = tokenize(text)
        self._tokens: Iterator[Token] = iter(text)
        self._token_buffer: List[Token] = []

    def __iter__(self) -> Iterator[Token]:
        while True:
            yield self.pop()

    def pop(self) -> Token:
        if not self._token_buffer:
            return next(self._tokens)
        ret = self._token_buffer[0]
        self._token_buffer = self._token_buffer[1:]
        return ret

    def peek(self) -> Optional[Token]:
        if not self._token_buffer:
            try:
                self._token_buffer.append(next(self._tokens))
            except StopIteration:
                return None
        return self._token_buffer[0]

    def push(self, token: Token):
        self._token_buffer = [token] + self._token_buffer

    def expect(self, startswith: str) -> Token:
        try:
            next_token = self.pop()
            if not next_token.token.startswith(startswith):
                raise ParseException(f"\n{str(next_token)}\nExpected \"{startswith}\"")
            return next_token
        except StopIteration:
            raise ParseException(f"Ran out of tokens when looking for {startswith}")


C = TypeVar("C", bound=visie.Constraint)


class Parser:
    def __init__(self, text: str):
        self._fulltext: str = text
        self._tokenizer: Tokenizer = Tokenizer(text)

    def _parse(self, constraint_type: Type[C]) -> C:
        start = self._tokenizer.expect(constraint_type.BEGIN_DELIM)
        children = []
        while True:
            next_token = self._tokenizer.peek()
            if next_token is None or next_token.token.startswith(constraint_type.END_DELIM):
                break
            children += self._parse_arguments(until=constraint_type.END_DELIM)
        try:
            self._tokenizer.expect(constraint_type.END_DELIM)
        except Exception as e:
            raise Exception(f"{str(e)}\nwhen looking for the closing delimiter of\n{str(start)}\n")
        return constraint_type(children)

    def _parse_arguments(self, until: Optional[str] = None) -> List[visie.Constraint]:
        children: List[visie.Constraint] = []
        while True:
            next_token = self._tokenizer.peek()
            if next_token is None or next_token.token == until:
                break
            for constraint_type in (
                    visie.OrderedConstraint, visie.AllOfConstraint, visie.ExactlyOneConstraint, visie.AnyOfConstraint
            ):
                if next_token.token == constraint_type.BEGIN_DELIM:
                    children.append(self._parse(constraint_type))  # type: ignore
                    break
            else:
                if next_token.token == '?':
                    if not children:
                        raise Exception(f"{str(next_token)}\nUnexpected '?' token")
                    self._tokenizer.pop()
                    children[-1] = visie.OptionalConstraint([children[-1]])
                elif next_token.token == '.':
                    self._tokenizer.pop()
                    children.append(visie.Wildcard())
                else:
                    children.append(visie.DictionaryWord(self._tokenizer.pop().token))
        return children

    def parse(self) -> visie.Constraint:
        """
        <all must occur in order>
        [all must occur in any order]
        (exactly one must occur)
        {any can occur in any order}
        optional?
        """
        children = self._parse_arguments()
        if not children:
            raise Exception(f"No tokens found while parsing \"{self._fulltext}\"")
        elif len(children) == 1:
            return children[0]
        else:
            return visie.AnyOfConstraint(children)
