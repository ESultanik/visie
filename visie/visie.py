import itertools
import os

from . import variants

DICT_PATH = os.path.join(os.path.sep, 'usr', 'share', 'dict', 'words')

class Acronym(object):
    def __init__(self, *matches, remainder=None):
        self._matches = matches
        self._remainder = remainder
    @property
    def remainder(self):
        return self._remainder
    def name(self):
        return ''.join(map(lambda w : w[0].upper(), self))
    def is_partial(self):
        return bool(self._remainder)
    def __add__(self, acronym):
        return Acronym(*(self._matches + acronym._matches), remainder=acronym.remainder)
    def __bool__(self):
        return not self.is_partial()
    def __iter__(self):
        return iter(self._matches)
    def __str__(self):
        words = ' '.join(map(str, self))
        if self.is_partial():
            return f"{words}@{self.remainder}"
        else:
            return words
    def __repr__(self):
        ret = repr(self._matches)
        if self._remainder:
            ret = f"{ret}, remainder={repr(remainder)}"
        return f"{type(self).__name__}({ret})"        

class Constraint(object):
    BEGIN_DELIM=''
    END_DELIM=''
    def __init__(self, children):
        self._children = list(children)
    @property
    def children(self):
        return self._children
    def matches(self, word):
        return filter(lambda m : m, self.match(word))
    def __str__(self):
        return f"{self.BEGIN_DELIM}{' '.join(map(str, self.children))}{self.END_DELIM}"
    def __str__(self):
        return f"{type(self).__name__}({repr(self.children)})"

class DictionaryWord(Constraint):
    def __init__(self, word):
        super(DictionaryWord, self).__init__(())
        self._word = word
    @property
    def word(self):
        return self._word
    def match(self, word):
        if word[0].lower() == self.word[0].lower():
            yield Acronym(self.word, remainder=word[1:])
    def min_length(self):
        return 1
    def max_length(self):
        return 1
    def __str__(self):
        return self.word
    def __repr__(self):
        return repr(self.word)
    
class AnyOfConstraint(Constraint):
    '''{any can occur in any order}'''
    BEGIN_DELIM='{'
    END_DELIM='}'
    def _match(self, remainder, children):
        for i, child in enumerate(children):
            for match in child.match(remainder):
                if match:
                    yield match
                else:
                    for m in self._match(match.remainder, children[:i] + children[i+1:]):
                        yield match + m
    def match(self, word):
        return self._match(word, self.children)
    def min_length(self):
        return 0
    def max_length(self):
        return sum(c.max_length() for c in self.children)

class OrderedConstraint(Constraint):
    '''<all must occur in order>'''
    BEGIN_DELIM='<'
    END_DELIM='>'
    def _match(self, remainder, children):
        if not children:
            return
        for match in children[0].match(remainder):
            if match:
                if len(children) == 1:
                    yield match
            elif len(children) == 1:
                yield match
            else:
                for m in self._match(match.remainder, children[1:]):
                    yield match + m

    def match(self, word):
        return self._match(word, self.children)

    def min_length(self):
        return sum(c.min_length() for c in self.children)
    def max_length(self):
        return sum(c.max_length() for c in self.children)

class AnyOrderedConstraint(Constraint):
    '''any can occur, but must be in order'''
    def _match(self, remainder, children):
        if not children:
            return
        for match in children[0].match(remainder):
            if match:
                if len(children) == 1:
                    yield match
            elif len(children) == 1:
                yield match
            else:
                for m in self._match(match.remainder, children[1:]):
                    yield match + m

    def match(self, word):
        return self._match(word, self.children)

    def min_length(self):
        return 0
    def max_length(self):
        return sum(c.max_length() for c in self.children)

class AllOfConstraint(Constraint):
    '''[all must occur in any order]'''
    BEGIN_DELIM='['
    END_DELIM=']'
    def _match(self, remainder, children):
        for i, child in map(lambda c : (c, self.children[c]), children):
            for match in child.match(remainder):
                if match:
                    if len(children) == 1:
                        yield match
                elif len(children) == 1:
                    yield match
                else:
                    for m in self._match(match.remainder, children - frozenset((i,))):
                        yield match + m

    def match(self, word):
        return self._match(word, frozenset(range(len(self.children))))

    def min_length(self):
        return sum(c.min_length() for c in self.children)
    def max_length(self):
        return sum(c.max_length() for c in self.children)

class ExactlyOneConstraint(Constraint):
    '''(exactly one must occur)'''
    BEGIN_DELIM='('
    END_DELIM=')'
    def match(self, word):
        for child in self.children:
            yield from child.match(word)

    def min_length(self):
        return min(c.min_length() for c in self.children)
    def max_length(self):
        return max(c.max_length() for c in self.children)

class Wildcard(Constraint):
    '''.'''
    def __init__(self):
        super(Wildcard, self).__init__([])
    def match(self, word):
        yield Acronym(word[0], remainder=word[1:])
    def min_length(self):
        return 1
    def max_length(self):
        return 1
    def __str__(self):
        return 'Wildcard<.>'
    __repr__ = __str__

class Optional(OrderedConstraint):
    def match(self, word):
        return itertools.chain((Acronym(remainder=word),), super(Optional, self).match(word))
    def min_length(self):
        return 0
    def __str__(self):
        if len(self.children) == 1:
            return f"{str(self.children[0])}?"
        else:
            return f"{super(Optional, self).__str__()}?"

def generate(constraints, min_length=3, use_variants=False, dict_path=DICT_PATH):
    min_length = max(constraints.min_length(), min_length)
    max_length = constraints.max_length()
    with open(dict_path, 'r') as dictionary:
        yielded = set()
        dict_words = map(lambda w : w.strip(), dictionary.readlines())
        if use_variants:
            dict_words = itertools.chain.from_iterable(map(lambda w : variants.generate_variants(w), dict_words))
        for word in dict_words:
            if word.upper() in yielded:
                continue
            word_len = len(word)
            if word_len < min_length or word_len > max_length:
                continue
            for match in constraints.matches(word):
                yielded.add(match.name())
                yield match
