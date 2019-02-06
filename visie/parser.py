from . import visie

class Token(object):
    def __init__(self, token, offset, fulltext):
        self.token = token
        self.offset = offset
        self.fulltext = fulltext
    def __str__(self):
        return f"{self.fulltext}\n{' '*self.offset}{'^'*len(self.token)}"
    def __repr__(self):
        return f"{type(self).__name__}(token={self.token!r}, offset={self.offset!r}, fulltext={self.fulltext!r})"

def tokenize(text):
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
        elif ord(c.lower()) >= ord('a') and ord(c.lower()) <= ord('z'):
            word += c
        else:
            raise Exception(f"{text}\n{' '*(len(text)-i)}^\nIllegal token \"{c}\"")
    if word:
        yield Token(word, len(text) - len(word), text)

class Tokenizer(object):
    def __init__(self, text):
        self._tokens = iter(tokenize(text))
        self._token_buffer = []
    def __iter__(self):
        while True:
            yield self.pop()
    def pop(self):
        if not self._token_buffer:
            return next(self._tokens)
        ret = self._token_buffer[0]
        self._token_buffer = self._token_buffer[1:]
        return ret
    def peek(self):
        if not self._token_buffer:
            try:
                self._token_buffer.append(next(self._tokens))
            except StopIteration:
                return None
        return self._token_buffer[0]
    def push(self, token):
        self._token_buffer = [token] + self._token_buffer
    def expect(self, startswith):
        try:
            next_token = self.pop()
            if not next_token.token.startswith(startswith):
                raise Exception(f"\n{str(next_token)}\nExpected \"{startswith}\"")
            return next_token
        except StopIteration:
            raise Exception(f"Ran out of tokens when looking for {startswith}")

class Parser(object):
    def __init__(self, text):
        self._fulltext = text
        self._tokenizer = Tokenizer(text)

    def _parse(self, ConstraintType):
        start = self._tokenizer.expect(ConstraintType.BEGIN_DELIM)
        children = []
        while True:
            next_token = self._tokenizer.peek()
            if next_token is None or next_token.token.startswith(ConstraintType.END_DELIM):
                break
            children += self._parse_arguments(until=ConstraintType.END_DELIM)
        try:
            self._tokenizer.expect(ConstraintType.END_DELIM)
        except Exception as e:
            raise Exception(f"{str(e)}\nwhen looking for the closing delimiter of\n{str(start)}\n")
        return ConstraintType(children)

    def _parse_arguments(self, until=None):
        children = []
        while True:
            next_token = self._tokenizer.peek()
            if next_token is None or next_token.token == until:
                break
            for ConstraintType in (visie.OrderedConstraint, visie.AllOfConstraint, visie.ExactlyOneConstraint, visie.AnyOfConstraint):
                if next_token.token == ConstraintType.BEGIN_DELIM:
                    children.append(self._parse(ConstraintType))
                    break
            else:
                if next_token.token == '?':
                    if not children:
                        raise Exception(f"{str(next_token)}\nUnexpected '?' token")
                    self._tokenizer.pop()
                    children[-1] = visie.Optional([children[-1]])
                elif next_token.token == '.':
                    self._tokenizer.pop()
                    children.append(visie.Wildcard())
                else:
                    children.append(visie.DictionaryWord(self._tokenizer.pop().token))
        return children

    def parse(self):
        """
        <all must occur in order>
        [all must occur in any order]
        (exactly one must occur)
        {any can occur in any order}
        optional?
        """
        children = self._parse_arguments()
        if not children:
            raise Exception(f"No tokens found while parsing \"{self.fulltext}\"")
        elif len(children) == 1:
            return children[0]
        else:
            return visie.AnyOfConstraint(children)
