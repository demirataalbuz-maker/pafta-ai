"""Real Lucene semantics; these tests never contact Elasticsearch or a network."""
from pathlib import Path
import math
import os
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sandbox import elastic_lucene as native


class LuceneNativeTests(unittest.TestCase):
    def check_query(self, query, mapping, documents, expected):
        self.assertEqual(native.evaluate(query, mapping, documents), expected, query)

    def test_real_version_and_unicode_analyzer(self):
        self.assertEqual(native.version(), 'Apache Lucene 9.12.3')
        self.assertEqual(native.analyze('İnceleme ÇÖZÜM, Quick-Brown'), ['inceleme', 'çözüm', 'quick', 'brown'])
        self.assertEqual(native.analyze('Mixed Case', 'keyword'), ['Mixed Case'])

    def test_keyword_case_normalizer_and_source_keys(self):
        docs = [{'id': 'a', 'k': 'ALICE'}, {'id': 'b', 'k': 'alice'}, {'id':'c','k':'alice admin'}]
        self.check_query('k:alice', {'k':{'type':'keyword'}}, docs, [1])
        self.check_query('k:ALICE', {'k':{'type':'keyword','normalizer':'lowercase'}}, docs, [0,1])
        self.check_query('k:"alice admin"', {'k':{'type':'keyword'}}, docs, [2])

    def test_default_or_boolean_and_pure_negative(self):
        m={'a':{'type':'keyword'},'b':{'type':'keyword'}}
        d=[{'a':'x','b':'z'},{'a':'y','b':'z'},{'a':'y','b':'q'},{}]
        self.check_query('a:x b:q',m,d,[0,2])
        self.check_query('a:x AND b:z',m,d,[0])
        self.check_query('NOT a:x',m,d,[1,2,3])
        self.check_query('NOT (a:x OR b:q)',m,d,[1,3])

    def test_native_classic_boolean_order_is_not_sql_precedence(self):
        # Classic QueryParser makes both surrounding clauses required for AND.
        m={'k':{'type':'keyword'}}
        d=[{'k':['a','b']},{'k':'c'},{'k':'a'},{'k':'b'}]
        self.check_query('k:a AND k:b OR k:c',m,d,[0])
        self.check_query('(k:a AND k:b) OR k:c',m,d,[0,1])

    def test_standard_token_not_substring(self):
        m={'t':{'type':'text'}}; d=[{'t':'Quick-Brown fox'},{'t':'quicker'},{'t':'QUICK'},{'t':'brown'}]
        self.check_query('t:quick',m,d,[0,2])
        self.check_query('t:(quick AND brown)',m,d,[0])
        self.check_query('t:"quick brown"',m,d,[0])

    def test_native_phrase_slop_and_transposition(self):
        m={'t':{'type':'text'}}
        d=[{'t':'alpha omega'},{'t':'alpha x omega'},{'t':'omega alpha'},{'t':'alpha x y omega'}]
        self.check_query('t:"alpha omega"',m,d,[0])
        self.check_query('t:"alpha omega"~1',m,d,[0,1])
        self.check_query('t:"alpha omega"~2',m,d,[0,1,2,3])

    def test_text_array_position_gap_native_boundary(self):
        m={'t':{'type':'text'}};d=[{'t':['alpha','omega']},{'t':'alpha omega'}]
        self.check_query('t:"alpha omega"~99',m,d,[1])
        self.check_query('t:"alpha omega"~100',m,d,[0,1])

    def test_native_fuzzy_damerau_and_exact_edit_limit(self):
        m={'k':{'type':'keyword'}};d=[{'k':x} for x in ['report','reprot','reports','repXXt','other']]
        self.check_query('k:report~1',m,d,[0,1,2])
        self.check_query('k:report~2',m,d,[0,1,2,3])

    def test_native_whole_term_regex_not_python_regex(self):
        m={'k':{'type':'keyword'}};d=[{'k':x} for x in ['admin','xadmin','admin1','ADMIN','admine']]
        self.check_query('k:/admin[0-9]?/',m,d,[0,2])
        self.check_query('k:/^admin.*/',m,d,[]) # ^ is literal in Lucene automata syntax.
        self.check_query('k:/ADMIN.*/',{'k':{'type':'keyword','normalizer':'lowercase'}},d,[0,2,3,4])

    def test_wildcard_question_and_literal_escape(self):
        m={'k':{'type':'keyword'}}; d=[{'k':x} for x in ['ab','a?','ax','a*b','za']]
        self.check_query('k:a?',m,d,[0,1,2])
        self.check_query(r'k:a\?',m,d,[1])
        self.check_query(r'k:a\*b',m,d,[3])
        self.check_query('k:*a',m,d,[4])

    def test_long_open_closed_and_precision(self):
        m={'n':{'type':'long'}}; n=9007199254740993
        d=[{'n':n-1},{'n':n},{'n':n+1},{}]
        for q, expected in [(f'n:[{n} TO {n+1}]',[1,2]),(f'n:{{{n} TO {n+1}]',[2]),
                            (f'n:[{n} TO {n+1}}}',[1]),(f'n:>{n}',[2]),(f'n:[* TO {n}]',[0,1])]:
            self.check_query(q,m,d,expected)

    def test_long_extreme_overflow_bounds(self):
        m={'n':{'type':'long'}};d=[{'n':-(2**63)},{'n':2**63-1}]
        self.check_query('n:{9223372036854775807 TO *]',m,d,[])
        self.check_query('n:[* TO -9223372036854775808}',m,d,[])
        self.check_query('n:[* TO *]',m,d,[0,1])

    def test_double_exact_adjacent_boundary(self):
        m={'n':{'type':'double'}}
        d=[{'n':math.nextafter(1.0,0)},{'n':1.0},{'n':math.nextafter(1.0,2)}]
        self.check_query('n:>1',m,d,[2])
        self.check_query('n:[1 TO 1]',m,d,[1])
        self.check_query('n:[* TO 1}',m,d,[0])

    def test_double_signed_zero_exact_and_open_closed_ranges(self):
        m = {'n': {'type': 'double'}}
        d = [{'n': -0.0}, {'n': 0.0}, {'n': -1.0}, {'n': 1.0}]
        for query, expected in [('n:"-0.0"', [0]), ('n:0.0', [1]),
                                ('n:[-0.0 TO -0.0]', [0]), ('n:[0.0 TO 0.0]', [1]),
                                ('n:{-0.0 TO 0.0]', [1]), ('n:[-0.0 TO 0.0}', [0]),
                                ('n:[0.0 TO -0.0]', []), ('n:{-0.0 TO 0.0}', [])]:
            self.check_query(query, m, d, expected)
        self.assertEqual(native.evaluate_ast({'op':'match','field':'n','value':-0.0}, m, d), [0])
        self.assertEqual(native.evaluate_ast({'op':'range','field':'n','cmp':'>','value':-0.0}, m, d), [1,3])

    def test_date_milliseconds_and_timezone(self):
        m={'at':{'type':'date'}}
        d=[{'at':'2026-01-01T00:00:00.000Z'},{'at':'2026-01-01T00:00:00.001Z'},
           {'at':'2026-01-01T03:00:00+03:00'},{'at':1767225599999}]
        self.check_query('at:["2026-01-01T00:00:00Z" TO "2026-01-01T00:00:00.001Z"}',m,d,[0,2])
        self.assertEqual(native.evaluate_ast({'op':'match','field':'at','value':1767225600000},m,d),[0,2])
        with self.assertRaisesRegex(native.ElasticLuceneError,'sayısal tarih metni'):
            native.evaluate('at:1767225600000',m,d)
        with self.assertRaisesRegex(native.ElasticLuceneError,'kısmi tarih'):
            native.evaluate('at:[2026-01-01 TO 2026-01-02]',m,d)

    def test_exists_indexed_value_empty_null_and_ignore_above(self):
        m={'k':{'type':'keyword','ignore_above':3},'t':{'type':'text'}}
        d=[{'k':''},{'k':None},{'k':[]},{'k':'abc'},{'k':'abcd'},{'k':[None,'ok']},{'t':''},{}]
        self.check_query('_exists_:k',m,d,[0,3,5])
        self.check_query('k:*',m,d,[0,3,5])
        self.check_query('k:""',m,d,[0])
        self.check_query('t:*',m,d,[6])
        self.check_query('*:*',m,d,list(range(8)))

    def test_keyword_null_value_and_boolean(self):
        m={'k':{'type':'keyword','null_value':'NULL'},'b':{'type':'boolean'}}
        d=[{'k':None,'b':True},{'k':[],'b':False},{'k':[None,'x']},{}]
        self.check_query('k:NULL',m,d,[0,2])
        self.check_query('b:false',m,d,[1])
        self.check_query('NOT b:true',m,d,[1,2,3])

    def test_ast_native_match_or_and_phrase(self):
        m={'t':{'type':'text'}};d=[{'t':'alpha'},{'t':'omega'},{'t':'alpha omega'},{'t':'omega alpha'},{}]
        self.assertEqual(native.evaluate_ast({'op':'match','field':'t','value':'alpha omega','phrase':False},m,d),[0,1,2,3])
        self.assertEqual(native.evaluate_ast({'op':'match','field':'t','value':'alpha omega','phrase':True},m,d),[2])

    def test_ast_boolean_range_projection_and_literal_question(self):
        m={'k':{'type':'keyword','normalizer':'lowercase'},'n':{'type':'long'}}
        d=[{'k':'A?','n':1},{'k':'AX','n':2},{'k':'A?','n':3},{}]
        ast={'op':'and','args':[{'op':'wildcard','field':'k','pattern':r'A\?'},
                              {'op':'range','field':'n','cmp':'gte','value':2}]}
        self.assertEqual(native.evaluate_ast(ast,m,d),[2])
        self.assertEqual(native.evaluate_ast({'op':'not','arg':{'op':'exists','field':'n'}},m,d),[3])
        self.assertEqual(native.evaluate_ast({'op':'ids','indices':[2,0]},m,d),[0,2])
        self.assertEqual(native.evaluate_ast({'op':'or','args':[]},m,d),[])

    def test_unsupported_syntax_fails_actionably(self):
        m={'k':{'type':'keyword'},'n':{'type':'long'},'hidden':{'type':'keyword','index':False}}
        for q in ['unqualified','unknown:x','k*:x','__pafta_row:0','k:a^2','hidden:x','n:abc','n:/1.*/','k:(']:
            with self.subTest(q=q),self.assertRaises(native.ElasticLuceneError):
                native.evaluate(q,m,[{'k':'x'}])
        with self.assertRaises(native.ElasticLuceneError):
            native.evaluate('k:x',{'k':{'type':'nested'}},[])

    def test_mapping_and_document_type_boundaries(self):
        for m,d in [({'n':{'type':'integer'}},[{'n':2**31}]),
                    ({'n':{'type':'long'}},[{'n':1.5}]),
                    ({'b':{'type':'boolean'}},[{'b':'true'}]),
                    ({'t':{'type':'text'}},[{'t':{'nested':'value'}}])]:
            with self.subTest(m=m),self.assertRaises(native.ElasticLuceneError):
                native.evaluate('*:*',m,d)
        self.check_query('k:x',{'k':{'type':'keyword'}},[],[])

    def test_java_environment_injection_is_not_inherited(self):
        with patch.dict(os.environ,{'JAVA_TOOL_OPTIONS':'-Dnot_a_runtime_option=unused','CLASSPATH':'bogus'}):
            self.check_query('k:x',{'k':{'type':'keyword'}},[{'k':'x'}],[0])
        for key in ('JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS','CLASSPATH'):
            self.assertNotIn(key,native._java_environment())


if __name__ == '__main__':
    unittest.main(verbosity=2)
