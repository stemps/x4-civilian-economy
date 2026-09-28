"""Prototype contracts only. These mocks cannot establish native layout validity."""
import unittest
import json
from copy import deepcopy
from lxml import etree as E
from support import ROOT, REF, Runner, Table, List, Component, NIL
from support_construction import sequence
from md_test_runtime import Angle, Station
from spine_catalog import Catalog, RACES
from spine_geometry import Layout, validate
from spine_geometry import rotate, add
from spine_bounds import box
import itertools


class LayoutGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=Catalog(REF)
        cls.layouts={}
        manifest=json.loads((ROOT/'tests/fixtures/spine_manifest.json').read_text(encoding='utf-8'))
        for race in RACES:
            selected=cls.catalog.select(race)
            plans=manifest['races'][race]['levels']
            for stage in plans:
                for entry in stage: entry['position']=tuple(entry['position'])
            cls.layouts[race]=(selected,plans)

    def test_all_sixty_levels_and_serialized_geometry(self):
        xml=E.parse(str(ROOT/'libraries/constructionplans.xml'))
        self.assertEqual(len(xml.xpath('//plan[starts-with(@id,"ce_hub_")]')),6)
        for race,(selected,plans) in self.layouts.items():
            with self.subTest(race=race):
                validate(plans,self.catalog,selected)
                self.assertEqual(len(plans),10)
                self.assertEqual(sum(e['role']!='connector' for e in plans[-1]),17)
                staged=xml.xpath('//plan[@id=$id]',id=f'ce_hub_{race}')[0]
                self.assertEqual([int(n.get('index')) for n in staged.findall('entry') if n.get('bookmark')=='1'],
                                 [len(stage) for stage in plans[:-1]])
                self.assertEqual(len(staged.findall('entry')),len(plans[-1]))
                for level,entries in enumerate(plans,1):
                    nodes=staged.findall('entry')[:len(entries)]
                    self.assertEqual(len(nodes),len(entries))
                    for node,entry in zip(nodes,entries):
                        self.assertEqual(node.get('macro'),entry['macro'])
                        self.assertEqual(tuple(float(node.find('offset/position').get(k)) for k in ('x','y','z')),entry['position'])
                        self.assertAlmostEqual(float(node.find('offset/rotation').get('yaw')),entry['yaw'])

    def test_capacity_selection_is_monotonic_and_ties_are_deterministic(self):
        for race,(selected,_) in self.layouts.items():
            for role in ('storage','dock','pier'):
                scores=[self.catalog.capacity(m)[role] for m in selected[role]]
                candidates=selected[role+'_candidates']
                self.assertEqual(scores,sorted(scores))
                self.assertEqual(scores[0],min(c['capacity'] for c in candidates))
                self.assertEqual(scores[-1],max(c['capacity'] for c in candidates))
                for name,score in zip(selected[role],scores):
                    self.assertEqual(name,min(c['macro'] for c in candidates if c['capacity']==score))

    def test_measured_boxes_fit_every_level_and_functional_boxes_are_separated(self):
        bounds=json.loads((ROOT/'tests/fixtures/spine_native_bounds.json').read_text(encoding='utf-8'))['macros']
        for race,(_,stages) in self.layouts.items():
            for level,entries in enumerate(stages,1):
                boxes=[box(e,bounds) for e in entries]
                with self.subTest(race=race,level=level):
                    self.assertTrue(all(all(v>=-4950.001 for v in lo) and all(v<=4950.001 for v in hi) for lo,hi in boxes))
                    functional=[b for e,b in zip(entries,boxes) if e['role']!='connector']
                    for a,b in itertools.combinations(functional,2):
                        self.assertTrue(any(a[1][i]+49.999<=b[0][i] or b[1][i]+49.999<=a[0][i] for i in range(3)))

    def test_geometry_rejects_shifted_snap_changed_prefix_missing_basket_and_bounds(self):
        selected,source=self.layouts['argon']
        for mutation in ('snap','prefix','basket','bounds','cycle','port'):
            with self.subTest(mutation=mutation):
                plans=deepcopy(source)
                if mutation=='snap': plans[0][-1]['position']=(0,0,0)
                elif mutation=='prefix': plans[1][0]['yaw']=90
                elif mutation=='basket': plans[0][-1]['role']='storage'
                elif mutation=='bounds': plans[0][-1]['position']=(5001,0,0)
                elif mutation=='cycle': plans[0][1]['predecessor']=2
                else: plans[0][-1]['parent_connection']='invalid_port'
                with self.assertRaises((ValueError,KeyError)):validate(plans,self.catalog,selected)

    def test_native_catalogue_has_each_expected_level(self):
        run=Runner()
        for race,(_,plans) in self.layouts.items():
            run.env['LayoutRace']=race
            run.library('md.CE_ConstructionData.Load')
            self.assertEqual(len(run.env['LayoutMacros']),10)
            for actual,entries in zip(run.env['LayoutMacros'],plans):
                self.assertEqual(list(actual),[e['macro'] for e in entries])
            self.assertEqual(len(run.env['LayoutGeometry']),10)

