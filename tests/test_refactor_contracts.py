"""Regression checks for configuration and synchronous library boundaries."""
import os
import runpy
import unittest
from unittest.mock import patch

from support import ROOT, Runner, Table, NIL, definitions


class RefactorContracts(unittest.TestCase):
    def test_fixture_reference_uses_checker_configuration(self):
        reference = ROOT / '.validation' / 'alternate-reference'
        with patch.dict(os.environ, {'CE_REFERENCE': str(reference), 'X4_REFERENCE': 'unused'}):
            fixture = runpy.run_path(str(ROOT / 'tests' / 'support.py'))
        self.assertEqual(fixture['REF'], reference.resolve())

    def test_capture_keeps_caller_record_even_if_resolver_stops(self):
        run = Runner()
        definitions(run)
        record = Table(ProfileRace='unrelated-record', sentinel=True)
        run.env['R'] = record
        race = run.env['Sector'].owner.primaryrace

        def interrupted():
            self.assertIs(run.env['R'], record)
            self.assertIs(run.env['ProfileRace'], race)
            raise RuntimeError('interrupted discovery')

        run.stubs['md.CE_PopulationProfiles.Build'] = interrupted
        with self.assertRaisesRegex(RuntimeError, 'interrupted discovery'):
            run.library('CaptureSectorProfile')
        self.assertIs(run.env['R'], record)
        self.assertEqual(len(run.env['SectorProfiles']), 0)

    def test_profile_input_is_independent_of_record_and_sector(self):
        run = Runner()
        definitions(run)
        race = run.env['lookup'].race.list[2]
        record = Table(ProfileRace='argon')
        run.env.update(R=record, ProfileRace=race)
        run.library('md.CE_PopulationProfiles.Build')
        self.assertEqual(run.env['CandidateRace'], race.id)
        self.assertIs(run.env['ProfileRace'], race)
        self.assertIs(run.env['R'], record)
        run.env['ProfileRace'] = NIL
        run.library('md.CE_PopulationProfiles.Build')
        self.assertEqual(run.env['CandidateRace'], '')
