# -*- coding: utf-8 -*-

import os
import unittest
from logsanitizer import (
    Line,
    Match,
    Rule,
    Classificator,
    Dialect,
    IgnoreLine,
    get_dialect,
)

class LineA(Line):
    @classmethod
    def parse(cls, classificator, line):
        return cls(classificator, *line.split(',',3))

    def __init__(self, classificator, timestamp, service_name, user_id):
        self._classificator = classificator
        self.timestamp = timestamp
        self.service_name = service_name
        self.user_id = user_id

    def is_type(self):
        return all([self.timestamp, self.service_name, self.user_id])

    def get_row(self):
        return [self.timestamp, self.user_id]

class TestLine(unittest.TestCase):
    def test_parse(self):
        l1 = LineA.parse(None, '2016-01-01 14:32,noxy_production,22')
        l2 = LineA(None, '2016-01-01 14:32', 'noxy_production', '22')
        self.assertEqual(l1.timestamp, l2.timestamp)
        self.assertEqual(l1.service_name, l2.service_name)
        self.assertEqual(l1.user_id, l2.user_id)

    def test_get_row(self):
        line = LineA(None, '2016-01-01 14:32', 'noxy_production', 22)
        self.assertEqual(line.get_row(), ['2016-01-01 14:32', 22])

class TestMatch(unittest.TestCase):
    def test_success_match_condition(self):
        m = Match(match_user_id=22)
        success, _ = m.check(LineA(None, '2016-01-01 14:32', 'noxy_production', 22))
        self.assertTrue(success)

    def test_not_success_match_condition(self):
        m = Match(match_user_id=22)
        success, _ = m.check(LineA(None, '2016-01-01 14:32', 'noxy_production', 52))
        self.assertFalse(success)

    def test_success_pattern_condition(self):
        m = Match(pattern_service_name='.*production')
        success, groups = m.check(LineA(None, '2016-01-01 14:32', 'noxy_production', 22))
        self.assertTrue(success)

    def test_not_success_pattern_condition(self):
        m = Match(pattern_service_name='production.*')
        success, groups = m.check(LineA(None, '2016-01-01 14:32', 'noxy_production', 22))
        self.assertFalse(success)

    def test_success_multiple_condition(self):
        m = Match(pattern_service_name='.*production', match_user_id=22)
        success, _ = m.check(LineA(None, '2016-01-01 14:32', 'noxy_production', 22))
        self.assertTrue(success)

    def test_not_success_multiple_condition_1(self):
        m = Match(pattern_service_name='.*production', match_user_id=22)
        success, _ = m.check(LineA(None, '2016-01-01 14:32', 'noxy_production', 43))
        self.assertFalse(success)

    def test_not_success_multiple_condition_2(self):
        m = Match(pattern_service_name='production.*', match_user_id=22)
        success, _ = m.check(LineA(None, '2016-01-01 14:32', 'noxy_production', 43))
        self.assertFalse(success)

class TestRule(unittest.TestCase):
    def test_matched_ignore(self):
        rule = Rule(Match(match_user_id=22), ignore=True)
        line = LineA(None, '2016-01-01 14:32', 'noxy_production', 22)
        with self.assertRaises(IgnoreLine):
            rule.apply(line)

    def test_not_matched_ignore(self):
        rule = Rule(Match(match_user_id=22), ignore=True)
        line = LineA(None, '2016-01-01 14:32', 'noxy_production', 43)
        self.assertFalse(rule.apply(line))

    def test_matched_setter(self):
        rule = Rule(Match(match_user_id=22), not_existing=1, service_name=2)
        line = LineA(None, '2016-01-01 14:32', 'noxy_production', 22)
        self.assertTrue(rule.apply(line))
        self.assertEqual(line.not_existing, 1)
        self.assertEqual(line.service_name, 2)

    def test_not_matched_setter(self):
        rule = Rule(Match(match_user_id=22), not_existing=1, service_name=2)
        line = LineA(None, '2016-01-01 14:32', 'noxy_production', 43)
        self.assertFalse(rule.apply(line))
        self.assertFalse(hasattr(line, 'not_existing'))
        self.assertEqual(line.service_name, 'noxy_production')

    def test_matched_group_setter(self):
        rule = Rule(Match(pattern_service_name='(\w+)_production'), event='ComeFrom.{0}')
        line = LineA(None, '2016-01-01 14:32', 'noxy_production', 43)
        self.assertTrue(rule.apply(line))
        self.assertEqual(line.event, 'ComeFrom.noxy')

    def test_matched_multiple_group_setter_not_collide(self):
        rule = Rule(Match(pattern_service_name='(\w+)_production'), pattern_user_id='\d+', event='ComeFrom.{0}')
        line = LineA(None, '2016-01-01 14:32', 'noxy_production', 43)
        self.assertTrue(rule.apply(line))
        self.assertEqual(line.event, 'ComeFrom.noxy')

class TestClassificator(unittest.TestCase):
    def setUp(self):
        self.c = Classificator([{'match_user_id': 43, 'not_existing': 1}, {'match_user_id': 45, 'not_existing': 2}])
        self.ic = Classificator([{'match_user_id': 43, 'ignore': True}, {'match_user_id': 43, 'not_existing': 2}])

    def test_constructor(self):
        self.assertEqual(len(self.c.rules), 2)
        self.assertTrue(isinstance(self.c.rules, list))
        self.assertTrue(isinstance(self.c.rules[0],Rule))
        self.assertEqual(self.c.rules[0]._match.conditions, {'match_user_id': 43})
        self.assertEqual(self.c.rules[0]._actions, {'not_existing': 1})

    def test_none_apply(self):
        line = LineA(self.c, '2016-01-01 14:32', 'noxy_production', 22)
        self.assertFalse(line.classify())
        self.assertFalse(hasattr(line, 'not_existing'))

    def test_first_apply(self):
        line = LineA(self.c, '2016-01-01 14:32', 'noxy_production', 43)
        self.assertTrue(line.classify())
        self.assertEqual(line.not_existing, 1)

    def test_next_apply(self):
        line = LineA(self.c, '2016-01-01 14:32', 'noxy_production', 45)
        self.assertTrue(line.classify())
        self.assertEqual(line.not_existing, 2)

    def test_ignore_apply(self):
        line = LineA(self.ic, '2016-01-01 14:32', 'noxy_production', 43)
        with self.assertRaises(IgnoreLine):
            line.classify()

class LineB(Line):
    @classmethod
    def parse(cls, classificator, line):
        return cls(classificator, *line.split('|',2))

    def __init__(self, classificator, timestamp, user_id):
        self._classificator = classificator
        self.timestamp = timestamp
        self.user_id = user_id

    def is_type(self):
        return all([self.timestamp, self.user_id])

    def get_row(self):
        return [self.timestamp, self.user_id]

class TestDialect(unittest.TestCase):
    def setUp(self):
        self.A = Dialect({'dialect': 'A', 'package': '{}/tests.py'.format(os.path.abspath(os.path.dirname(__file__))), 'class': 'LineA'})
        self.B = Dialect({'dialect': 'B', 'package': '{}/tests.py'.format(os.path.abspath(os.path.dirname(__file__))), 'class': 'LineB'})
        self.dialects = [self.A, self.B]

    def test_success_parse_line(self):
        str_line = u'2016-01-01 14:32,noxy_production,22'
        line = self.A.parse(str_line)
        self.assertTrue(isinstance(line, self.A._class))

    def test_failure_parse_line(self):
        str_line = u'2016-01-01 14:32 22'
        with self.assertRaises(Exception):
            self.A.parse(str_line)

    def test_not_detect_dialect(self):
        line = get_dialect(self.dialects, u'2016-01-01 14:32,22')
        self.assertIsNone(line)

    def test_detect_first_dialect(self):
        line = get_dialect(self.dialects, u'2016-01-01 14:32,noxy_production,22')
        self.assertTrue(isinstance(line, self.A._class))

    def test_detect_next_dialect(self):
        line = get_dialect(self.dialects, u'2016-01-01 14:32|22')
        self.assertTrue(isinstance(line, self.B._class))