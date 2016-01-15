# -*- coding: utf-8 -*-

import re
import csv
import imp
import sys
import yaml
import argparse

import sys
import types

# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3

# Add !regexp as a known Yaml dialect.
yaml.add_constructor('!regexp', lambda l, n: l.construct_scalar(n))

if PY3: # pragma: no cover
    text_type = str
    binary_type = bytes
    unicode = str

else:
    text_type = unicode
    binary_type = str

class Line(object):
    # Line
    @classmethod
    def parse(cls, classificator, line):
        return cls(classificator)

    # void
    def __init__(self, classificator, *args, **kwargs):
        self._classificator = classificator

    # bool
    def is_type(self):
        raise RuntimeError('Line.is_type() is not implemented yet!')

    # bool
    def is_production(self):
        return True

    # void
    def classify(self):
        return self._classificator.classify(self)

    # list<str>
    def get_row(self):
        raise RuntimeError('Line.get_row() is not implemented yet!')

class IgnoreLine(Exception):
    pass

class Match(object):
    # void
    def __init__(self, **conditions):
        self.conditions = conditions
        for k,v in self.conditions.items():
            if k.startswith('pattern_'):
                self.conditions[k] = re.compile(v)

    # tuple<bool,object>
    def check(self, line):
        groups = None
        for condition, value in self.conditions.items():
            action, field_name = condition.split('_',1)
            field_value = getattr(line, field_name)

            if not field_value:
                return False, None

            if action == 'match' and unicode(field_value) == unicode(value):
                continue

            elif action == 'pattern':
                match = value.match(field_value)
                if match is not None:
                    if match.groups():
                        groups = match.groups()
                    continue

            return False, None

        return True, groups

class Rule(object):
    # void
    def __init__(self, match=None, ignore=None, **actions):
        self._match = match
        self._ignore = ignore
        self._actions = actions

    # bool
    def apply(self, line):
        success, groups = self._match.check(line)
        if not success:
            return False

        self.action(line, groups)
        return True

    # void
    def action(self, line, groups=None):
        if self._ignore:
            raise IgnoreLine()

        for field_name, value in self._actions.items():
            if '{' in unicode(value) and '}' in unicode(value) and groups is not None:
                value = value.format(*groups)
            setattr(line, field_name, value)

class Classificator(object):
    # void
    def __init__(self, rules):
        self.rules = [ Rule( Match(**dict(filter(lambda x: x[0].startswith(('match_','pattern_')), \
                             r.items()))), r.get('ignore'), **dict(filter(lambda x: \
                             not x[0].startswith(('match_','pattern_','ignore')), r.items()))) \
                       for r in rules ]

    # void
    def classify(self, line):
        for rule in self.rules:
            if rule.apply(line):
                return True

        return False

class Dialect(object):
    # void
    def __init__(self, config):
        self._module = imp.load_source(config['dialect'], config['package'])
        self._class = getattr(self._module, config['class'])
        self.classificator = Classificator(config.get('classifications') or [])

    # object
    def parse(self, line):
        return self._class.parse(self.classificator, line)

# object
def get_dialect(dialects, line):
    for dialect in dialects:
        try:
            obj = dialect.parse(line)
            if not obj.is_type(): continue
            if not obj.is_production(): continue
            return obj
        except Exception as e:
            continue

# Dialect
def make_dialect(file_pointer):
    return Dialect(yaml.load(file_pointer))

# Line
def classify_line(dialects, line):
    # Detect the first valid dialect
    obj = get_dialect(dialects, line)
    if not obj:
        return None

    # Classify the record
    try:
        obj.classify()
    except IgnoreLine as e:
        return None

    return obj

def main():
    # Command Line Interface.
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout, help='output file, using stdout as default')
    parser.add_argument('-f', '--file', type=argparse.FileType('r'), default=sys.stdin, help='log file to process, using stdin as default')
    parser.add_argument('-s', '--separator', default='\001', help='CSV file separator. default is a non-printable character: \\001')
    parser.add_argument('config', type=argparse.FileType('r'), nargs="+", help='dialect YAML configurations files.')
    args = parser.parse_args()

    # Load supported dialect's configurations.
    yaml.add_constructor('!regexp', lambda l, n: l.construct_scalar(n))
    dialects = list(map(make_dialect, args.config))

    # Create a CSV writer.
    writer = csv.writer(args.output, delimiter=args.separator)

    # Iterate over the log file ...
    for line in args.file:
        # Detect the first valid dialect
        obj = classify_line(dialects, line)
        if not obj: continue

        # Write out the final record
        writer.writerow(obj.get_row())
