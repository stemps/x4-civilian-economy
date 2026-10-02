"""Exercise racial selection and asynchronous layout contracts, without emulating X4."""
from support import Runner, Table, List, NIL, Component, definitions, REF
from support_construction import module, sequence
from lxml import etree as E
import unittest


class ConstructionTests(unittest.TestCase):
    def test_supported_racial_profiles_require_every_native_macro(self):
        for race in ('argon','boron','paranid','split','terran','teladi'):
            r=Runner();r.env.update(ProfileRace=Table(id=race),tag=Table(module='module'))
            names=E.parse(str(__import__('support').MOD/'libraries/constructionplans.xml')).xpath('//plan[@id=$id]/entry/@macro',id='ce_hub_'+race)
            r.native['get_module_definition']=lambda n:r.set(n.get('macro'),List(Component(id=x) for x in sorted(set(names))))
            r.library('md.CE_Construction.Resolve')
            profile=r.env['Construction']
            self.assertTrue(profile.Valid);self.assertEqual(profile.Plan,'ce_hub_'+race)
            self.assertEqual(profile.Levels.count,10)
            r.native['get_module_definition']=lambda n:r.set(n.get('macro'),List())
            r.library('md.CE_Construction.Resolve');self.assertFalse(r.env['Construction'].Valid)

    def test_unsupported_race_has_no_silent_argon_fallback(self):
        r=Runner();r.env['ProfileRace']=Table(id='conversion_race')
        r.library('md.CE_Construction.Resolve')
        self.assertFalse(r.env['Construction'].Valid)

class StartupProfileTests(unittest.TestCase):
    def test_all_sectors_are_captured_before_population_response(self):
        r=Runner(); definitions(r)
        r.env['Registry']=Table()  # Initialized by the controller before Reconcile.
        sectors=List([r.env['Sector'],Component(owner=Table(primaryrace=r.env['lookup'].race.list[2]))])
        r.env['player'].entity=Table()
        r.env['PopulationRequest']=NIL
        r.native['find_sector']=lambda n:r.set(n.get('name'),sectors)
        def request(n):
            self.assertEqual(len(r.env['SectorProfiles']),2)
            self.assertIs(r.env['R'],NIL)
        r.native['raise_lua_event']=request
        r.library('Reconcile')
        self.assertEqual(len(r.env['SectorProfiles']),2)

    def test_reload_cancels_pending_layout_without_changing_snapshot(self):
        r=Runner(); definitions(r)
        sector=r.env['Sector']; r.library('CaptureSectorProfile')
        frozen=r.env['SectorProfiles'][sector]
        record=Table(LayoutPending=True,LayoutCue=Component(exists=True))
        r.env['Registry']=Table({sector:record})
        for name in ('Reconcile','RefreshProfile','RenameHub','PublishDiagnostics','PublishAllDiagnostics'):
            r.stubs[name]=lambda:None
        cancelled=[]
        r.native['cancel_cue']=lambda n:cancelled.append(r.expr(n.get('cue')))
        r.actions(r.tree.xpath('//cue[@name="Reload"]/actions')[0])
        self.assertIn(record.LayoutCue,cancelled)
        self.assertFalse(record.LayoutPending)
        self.assertIs(r.env['SectorProfiles'][sector],frozen)

    def test_sector_snapshot_survives_conquest_before_hub_creation(self):
        r=Runner(); definitions(r)
        sector=r.env['Sector']; original=sector.owner.primaryrace
        r.library('CaptureSectorProfile')
        frozen=r.env['SectorProfiles'][sector]
        sector.owner.primaryrace=r.env['lookup'].race.list[2]
        r.library('CaptureSectorProfile')
        self.assertIs(r.env['SectorProfiles'][sector],frozen)
        self.assertEqual(frozen.Race,original.id)
        self.assertIs(r.env['R'],NIL)

    def test_construction_receives_captured_race_after_food_discovery(self):
        r=Runner(); definitions(r)
        original=r.env['Sector'].owner.primaryrace
        seen=[]
        def resolve():
            seen.append(r.env['ProfileRace'])
            r.env['Construction']=Table(Valid=True)
        r.stubs['md.CE_Construction.Resolve']=resolve
        r.library('CaptureSectorProfile')
        self.assertEqual(seen,[original])


class UnownedSectorRaceTests(unittest.TestCase):
    def setUp(self):
        self.r=Runner(); definitions(self.r)
        self.races=self.r.env['lookup'].race.list  # argon, paranid, teladi
        self.target=Component(owner=NIL,gatedistance=Table())
        self.sectors=List([self.target])
        self.r.native['find_sector']=lambda n:self.r.set(n.get('name'),self.sectors)
        self.seen=[]
        def resolve():
            self.seen.append(self.r.env['ProfileRace'])
            self.r.env['Construction']=Table(Valid=True)
        self.r.stubs['md.CE_Construction.Resolve']=resolve
        self.r.env['Sector']=self.target

    def owned(self,race,distance,hostile=False):
        owner=Table(primaryrace=self.races[race],hasrelation=Table(enemy=Table(civilian=hostile)))
        sector=Component(owner=owner)
        self.target.gatedistance[sector]=distance
        self.sectors.append(sector)
        return sector

    def capture(self):
        self.r.library('CaptureSectorProfile')
        return self.r.env['SectorProfiles'][self.target]

    def test_nearest_owned_sector_supplies_race(self):
        self.owned(3,3);self.owned(1,2);self.owned(2,1)
        self.assertEqual(self.capture().Race,'paranid')
        self.assertEqual(self.seen,[self.races[2]])

    def test_distance_tie_prefers_race_library_order_regardless_of_sector_order(self):
        for order in ((3,2),(2,3)):
            self.setUp()
            for race in order:self.owned(race,1)
            self.owned(1,2)
            self.assertEqual(self.capture().Race,'paranid')

    def test_hostile_unreachable_and_ownerless_sectors_are_ignored(self):
        self.owned(1,1,hostile=True);self.owned(2,-1)
        ownerless=Component(owner=Table(primaryrace=NIL));self.target.gatedistance[ownerless]=1
        self.sectors.append(ownerless)
        self.owned(3,4)
        self.assertEqual(self.capture().Race,'teladi')

    def test_owned_sector_keeps_its_own_race(self):
        self.target.owner=Table(primaryrace=self.races[3]);self.owned(1,1)
        self.assertEqual(self.capture().Race,'teladi')

    def test_no_candidate_keeps_unknown_profile(self):
        self.owned(1,-1)
        self.assertEqual(self.capture().Race,'')


class TerranRecipeTests(unittest.TestCase):
    def test_native_terran_categories_use_terran_construction_materials(self):
        root=REF/'extensions/ego_dlc_terran/libraries'
        groups=E.parse(str(root/'modulegroups.xml'))
        wares=E.parse(str(root/'wares.xml'))
        allowed={'energycells','metallicmicrolattice','siliconcarbide','computronicsubstrate'}
        for group in ('dockarea_ter','stor_ter','pier_base_ter','pier_add_ter','conn_ter'):
            macros=groups.xpath('//group[@name=$name]//select/@macro',name=group)
            self.assertTrue(macros,group)
            for macro in macros:
                recipes=wares.xpath('//ware[component/@ref=$macro]/production[@method="default"]/primary/ware/@ware',macro=macro)
                self.assertTrue(recipes,macro)
                self.assertLessEqual(set(recipes),allowed,macro)


if __name__ == '__main__':
    unittest.main()
