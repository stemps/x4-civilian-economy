"""Synthetic fitter tests, never evidence of native clearance."""
import json
import unittest
from copy import deepcopy
from unittest.mock import patch
from support import ROOT
from spine_bounds import box, fit


class BoundsTests(unittest.TestCase):
    def test_envelope_rotates_all_eight_corners_including_asymmetric_bounds(self):
        lo,hi=box({'macro':'m','position':(100,200,300),'yaw':90},{'m':{'min':[-10,-20,-30],'max':[40,50,60]}})
        for actual,expected in zip(lo,(70,180,260)): self.assertAlmostEqual(actual,expected)
        for actual,expected in zip(hi,(160,250,310)): self.assertAlmostEqual(actual,expected)

    def test_corrected_half_extents_reproduce_boron_native_failure(self):
        observed=json.loads((ROOT/'tests/mod/fixtures/spine_span_observation.json').read_text())
        bounds=json.loads((ROOT/'tests/mod/fixtures/spine_native_bounds.json').read_text())['macros']
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
