"""Synthetic fitter/importer tests, never evidence of native clearance."""
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from support import ROOT
from spine_catalog import RACES
from spine_bounds import import_log, box, fit


class BoundsTests(unittest.TestCase):
    def parse(self, text):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'debug.txt';p.write_text(text,encoding='utf-8')
            return import_log(p)

    def records(self, races=RACES, token=1):
        return '\n'.join(f'[CE Spine] CALIBRATION_BEGIN token={token} race={race} fingerprint=abc\n'
            '[CE Spine] CALIBRATION macro=test_macro max=20,30,40 center=5,0,-5\n'
            f'[CE Spine] CALIBRATION_END race={race}' for race in races)

    def test_import_requires_latest_complete_run_and_keeps_provenance(self):
        result=self.parse(self.records())
        self.assertEqual(result['macros']['test_macro']['min'],[-15,-30,-45])
        self.assertEqual(result['macros']['test_macro']['max'],[25,30,35])
        self.assertEqual(len(result['races']),6)
        self.assertEqual(result['layout_fingerprint'],'abc')
        self.assertEqual(len(result['log_sha256']),64)
        for tail in (self.records(['argon']),self.records(['argon'],2)):
            with self.assertRaisesRegex(ValueError,'Incomplete'):
                self.parse(self.records()+'\n'+tail)
        with self.assertRaisesRegex(ValueError,'No native'):
            self.parse('[CE Spine] BOUNDS outside plot')

    def test_conflicting_missing_and_invalid_measurements_are_rejected(self):
        text=self.records()
        with self.assertRaisesRegex(ValueError,'Conflicting'):
            self.parse(text.replace('max=20,30,40','max=21,30,40',1))
        with self.assertRaisesRegex(ValueError,'Invalid'):
            self.parse(text.replace('max=20,30,40','max=-20,30,40'))
        with self.assertRaisesRegex(ValueError,'Incomplete'):
            self.parse(text.replace('CALIBRATION macro=test_macro max=20,30,40 center=5,0,-5','CALIBRATION_MISSING macro=test_macro'))

    def test_envelope_rotates_all_eight_corners_including_asymmetric_bounds(self):
        lo,hi=box({'macro':'m','position':(100,200,300),'yaw':90},{'m':{'min':[-10,-20,-30],'max':[40,50,60]}})
        for actual,expected in zip(lo,(70,180,260)): self.assertAlmostEqual(actual,expected)
        for actual,expected in zip(hi,(160,250,310)): self.assertAlmostEqual(actual,expected)

    def test_corrected_half_extents_reproduce_boron_native_failure(self):
        observed=json.loads((ROOT/'tests/fixtures/spine_span_observation.json').read_text())
        bounds=json.loads((ROOT/'tests/fixtures/spine_native_bounds.json').read_text())['macros']
        boxes=[box(e,bounds) for e in observed['boron_level6_entries']]
        predicted=[max(b[1][i] for b in boxes)-min(b[0][i] for b in boxes) for i in range(3)]
        native=next(o['span'] for o in observed['observations'] if o['race']=='boron' and o['level']==6)
        for actual,expected in zip(predicted,native):self.assertAlmostEqual(actual,expected,delta=0.002)
        self.assertGreater(predicted[0],10000)

    def test_fitter_centres_full_envelope_once_and_preserves_prefix(self):
        selection={'cross':'a','straight':'a','vertical':'a','storage':['a'],'dock':['b'],'pier':['b']}
        stages=[[dict(index=1,macro='a',position=(1000,0,0),yaw=0,role='storage')],
                [dict(index=1,macro='a',position=(1000,0,0),yaw=0,role='storage'),
                 dict(index=2,macro='b',position=(4000,0,0),yaw=0,role='pier')]]
        bounds={'a':{'min':[-100,-100,-100],'max':[100,100,100]},
                'b':{'min':[-100,-100,-100],'max':[2000,100,100]}}
        with patch('spine_bounds.Layout') as layout,patch('spine_bounds.validate'):
            layout.return_value.generate.side_effect=lambda:deepcopy(stages)
            fitted,report=fit(None,selection,bounds)
            self.assertEqual(fitted[0][0],fitted[1][0])
            self.assertEqual(report['envelope_size'],[5100,200,200])
            self.assertEqual(fitted[0][0]['position'][0],-2450)
            with self.assertRaisesRegex(ValueError,'Missing native'):
                fit(None,selection,{'a':bounds['a']})
            bounds['b']['max'][0]=20000
            with self.assertRaisesRegex(ValueError,'No candidate'):
                fit(None,selection,bounds)


if __name__=='__main__':unittest.main()
