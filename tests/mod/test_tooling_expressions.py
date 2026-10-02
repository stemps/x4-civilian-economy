"""Compilation may be shared; mutable values and runner state must not be."""
import unittest
from lxml import etree
from support import Runner, Table, List, NIL
from md_expressions import compile_expression, normalize_path


class ExpressionCacheTests(unittest.TestCase):
    def test_cached_code_reads_current_environment_and_other_runners(self):
        first, second = Runner(), Runner()
        first.env['Value'] = 3
        second.env['Value'] = 11
        self.assertEqual(first.expr('$Value + 1'), 4)
        first.env['Value'] = 8
        self.assertEqual(first.expr('$Value + 1'), 9)
        self.assertEqual(second.expr('$Value + 1'), 12)
        first.env = {'Value': 20}
        self.assertEqual(first.expr('$Value + 1'), 21)

    def test_cached_literals_create_fresh_nested_values(self):
        runner = Runner()
        runner.env['Value'] = 4
        for expression in ('[[$Value]]', 'table[$Items=[$Value]]'):
            first = runner.expr(expression)
            items = first[1] if isinstance(first, List) else first.Items
            items.append(99)
            runner.env['Value'] = 7
            second = runner.expr(expression)
            fresh = second[1] if isinstance(second, List) else second.Items
            self.assertEqual(list(fresh), [7])
            self.assertIsNot(first, second)
            runner.env['Value'] = 4

    def test_special_forms_short_circuit_and_keep_native_list_semantics(self):
        runner = Runner()
        runner.env.update(Value=5, Record=Table())
        for _ in range(2):
            self.assertEqual(runner.expr('if true then $Value else invalid('), 5)
            self.assertFalse(runner.expr('false and invalid()'))
            self.assertEqual(runner.expr('[$Value, 9].{1}'), 5)
            self.assertEqual(runner.expr("'amount %1'.[$Value]"), 'amount 5')
            self.assertEqual(runner.expr('{974201,1}.[$Value]'), (974201, 1, (5,)))
            self.assertFalse(runner.expr('$Record.$Missing?'))
            self.assertIs(runner.expr('@$Record.$Missing'), NIL)
        runner.env['Record'].Missing = 0
        self.assertTrue(runner.expr('$Record.$Missing?'))

    def test_units_angles_and_errors_survive_repeated_evaluation(self):
        runner = Runner()
        for _ in range(2):
            self.assertEqual(runner.expr('2min + 1h'), 3720)
            self.assertEqual(runner.expr('2Cr + 1km'), 1200)
            self.assertEqual(runner.expr('abs(10deg - 30deg)'), 20)
            with self.assertRaisesRegex(TypeError, 'angles'):
                runner.expr('10deg % 3')
            for expression, error in [('@$Value?', ValueError), ('$Record.keys', ValueError),
                                      ('{974201,$Value}', ValueError), ('$Value +', SyntaxError)]:
                with self.assertRaises(error):
                    runner.expr(expression)

    def test_path_cache_preserves_literal_sigils_and_dynamic_keys(self):
        runner = Runner()
        runner.env.update(Record=Table({'$one': 3, '$two': 7}), Key='one')
        expression = "$Record.{'$' + $Key}"
        self.assertEqual(runner.expr(expression), 3)
        runner.env['Key'] = 'two'
        self.assertEqual(runner.expr(expression), 7)
        runner.set(expression, 12)
        self.assertEqual(runner.env['Record']['$two'], 12)
        self.assertEqual(runner.env['Record']['$one'], 3)

    def test_runner_xml_and_state_remain_independent(self):
        first, second = Runner(), Runner()
        first.tree.getroot().append(etree.fromstring(
            '<library name="CacheIsolation"><actions><set_value name="$Value" exact="3"/></actions></library>'))
        first.library('CacheIsolation')
        action = first.tree.xpath('//library[@name="CacheIsolation"]//set_value')[0]
        action.set('exact', '9')
        first.library('CacheIsolation')
        self.assertEqual(first.env['Value'], 9)
        self.assertNotIn('Value', second.env)
        with self.assertRaisesRegex(ValueError, 'CacheIsolation'):
            second.library('CacheIsolation')

    def test_expression_and_path_cache_eviction_preserves_results(self):
        # More unique inputs than either cache can retain, followed by reuse.
        initial = compile_expression('1 + 2')
        for number in range(8193):
            compile_expression(str(number))
            normalize_path(f'$Record.$field{number}')
        self.assertEqual(eval(compile_expression('1 + 2')), 3)
        self.assertIsNot(initial, compile_expression('1 + 2'))
        self.assertEqual(normalize_path("$Record.{'$' + $Key}"), "Record['$' + Key]")
        self.assertLessEqual(compile_expression.cache_info().currsize, 8192)
        self.assertLessEqual(normalize_path.cache_info().currsize, 8192)


if __name__ == '__main__':
    unittest.main()
