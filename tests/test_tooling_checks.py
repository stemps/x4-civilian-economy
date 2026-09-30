"""Check selection, failure propagation and optional timing contracts."""
import argparse
import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

from support import ROOT
import check
from check_timings import Timings


class CheckSelectionTests(unittest.TestCase):
    def invoke(self, *, skip=False, schema=False, test_success=True, validator_code=0, merged_code=0):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / 'reference'
            library = reference / 'ui/core'
            library.mkdir(parents=True)
            (library / 'addon.xsd').write_text(
                '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">'
                '<xs:element name="addon"/></xs:schema>')
            (root / 'ui.xml').write_text('<addon/>')
            fake_cli = types.ModuleType('x4validate._cli')
            fake_cli.main = Mock(return_value=validator_code)
            args = argparse.Namespace(reference=reference, toolkit=root, schema=schema, skip_tests=skip)
            timings = Timings(True, io.StringIO())
            runner = Mock()
            runner.run.return_value.wasSuccessful.return_value = test_success
            output = io.StringIO()
            with patch.object(check, 'ROOT', root), patch.dict(os.environ), \
                 patch.object(sys, 'argv', ['check.py']), patch.object(sys, 'path', sys.path[:]), \
                 patch.dict(sys.modules, {'x4validate._cli': fake_cli}), \
                 patch.object(check.unittest.defaultTestLoader, 'discover') as discover, \
                 patch.object(timings, 'runner', return_value=runner), \
                 patch.object(check, 'validate_merged', return_value=merged_code) as merged, \
                 contextlib.redirect_stdout(output):
                result = check.run_checks(args, timings)
                self.assertEqual(os.environ['CE_REFERENCE'], str(reference.resolve()))
                arguments = sys.argv[:]
            return result, discover, runner, fake_cli.main, merged, output.getvalue(), arguments

    def test_default_and_compatible_schema_each_run_tests_once(self):
        for schema in (False, True):
            result, discover, runner, validator, merged, _, arguments = self.invoke(schema=schema)
            self.assertEqual(result, 0)
            discover.assert_called_once()
            runner.run.assert_called_once()
            validator.assert_called_once()
            self.assertEqual(merged.call_count, int(schema))
            self.assertEqual('--update' in arguments, schema)

    def test_schema_only_omits_tests_explicitly_but_runs_both_validators(self):
        result, discover, runner, validator, merged, output, _ = self.invoke(skip=True, schema=True)
        self.assertEqual(result, 0)
        discover.assert_not_called()
        runner.run.assert_not_called()
        validator.assert_called_once()
        merged.assert_called_once()
        self.assertIn('Controller tests omitted', output)

    def test_failures_stop_dependent_phases_and_preserve_exit_codes(self):
        result, _, _, validator, merged, _, _ = self.invoke(schema=True, test_success=False)
        self.assertEqual(result, 1)
        validator.assert_not_called()
        merged.assert_not_called()
        result, _, _, _, merged, _, _ = self.invoke(schema=True, validator_code=3)
        self.assertEqual(result, 3)
        merged.assert_not_called()
        self.assertEqual(self.invoke(schema=True, merged_code=1)[0], 1)

    def test_just_graph_keeps_complete_coverage_without_duplicate_test_discovery(self):
        def commands(target):
            result = subprocess.run(['just', '--dry-run', target], cwd=ROOT,
                                    text=True, capture_output=True, check=True)
            return (result.stdout + result.stderr).splitlines()

        everyday = commands('check')
        full = commands('check-full')
        self.assertEqual(sum('tools/check.py' in line for line in everyday), 1)
        self.assertEqual(sum('tools/generate_plans.py' in line for line in everyday), 1)
        self.assertFalse(any('unittest discover' in line for line in everyday))
        self.assertFalse(any('test/test_release.py' in line for line in everyday))
        self.assertTrue(any('test/test_translations.py' in line for line in everyday))
        self.assertTrue(any('tools/test_map_status.py' in line for line in everyday))
        checks = [line for line in full if 'tools/check.py' in line]
        self.assertEqual(len(checks), 2)
        self.assertEqual(sum('--skip-tests' not in line for line in checks), 1)
        self.assertEqual(sum('--schema --skip-tests' in line for line in checks), 1)
        for script in ('test_release.py', 'test_manual_bbcode.py', 'test_nexus.py',
                       'test_archive.py', 'test_release_support.py'):
            self.assertEqual(sum('test/' + script in line for line in full), 1)
        focused = commands('plans-check')
        self.assertEqual(sum('unittest discover' in line for line in focused), 2)


class TimingTests(unittest.TestCase):
    def test_failed_tests_and_stage_exceptions_still_have_timings(self):
        output = io.StringIO()
        timings = Timings(True, output)

        class Failing(unittest.TestCase):
            def runTest(self):
                self.fail('expected failure in timing fixture')

        with contextlib.redirect_stderr(io.StringIO()):
            with timings.stage('controller tests'):
                result = timings.runner().run(unittest.TestSuite([Failing()]))
        self.assertFalse(result.wasSuccessful())
        with self.assertRaisesRegex(RuntimeError, 'fixture'):
            with timings.stage('broken stage'):
                raise RuntimeError('fixture')
        timings.report()
        self.assertEqual(len(timings.tests), 1)
        for label in ('controller tests', 'broken stage', 'Modules:', 'Slowest tests:', 'Failing.runTest'):
            self.assertIn(label, output.getvalue())

    def test_main_reports_timings_even_when_a_stage_raises(self):
        output = io.StringIO()
        with patch.object(sys, 'argv', ['check.py', '--timings']), \
             patch.object(check, 'run_checks', side_effect=RuntimeError('fixture')), \
             contextlib.redirect_stderr(output):
            with self.assertRaisesRegex(RuntimeError, 'fixture'):
                check.main()
        self.assertIn('Wall-clock timings', output.getvalue())

    def test_disabled_timing_is_silent(self):
        output = io.StringIO()
        timings = Timings(False, output)
        with timings.stage('hidden'):
            pass
        timings.report()
        self.assertEqual(output.getvalue(), '')


if __name__ == '__main__':
    unittest.main()
