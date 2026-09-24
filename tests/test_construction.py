"""Exercise racial selection and asynchronous layout contracts, without emulating X4."""
from support import Runner, Table, List, NIL, Component, definitions, REF
from md_test_runtime import PseudoValue
from lxml import etree as E
import unittest


def module(kind, size=1):
    return Component(isclass=Table({kind: True}), numdocks=Table(dock_s=size, dock_m=size),
                     cargo=Table(capacity=Table(container=size)), numpierdocks=size)


class SequenceEntry(Table, PseudoValue):
    pass


class Sequence(List):
    def __getitem__(self, key):
        if isinstance(key, str):
            return next((entry for entry in self if entry.id == key), NIL)
        return super().__getitem__(key)


def sequence(macros):
    return Sequence(SequenceEntry(id=str(i), macro=m, exists=True) for i, m in enumerate(macros))


class ConstructionTests(unittest.TestCase):
    def setUp(self):
        self.run = r = Runner()
        self.components = Table(Dock=module('dockarea'), Storage=module('storage'),
                                Pier=module('pier'), Connectors=List([module('connectionmodule')]), Valid=True)
        self.hub = Component(exists=True, iswreck=False, owner='ownerless',
                             buildstorage=Table(exists=True, builds=Table(queued=List(), inprogress=List())))
        self.record = Table(Hub=self.hub, Construction=self.components, ProfileRace='terran',
                            Level=1, Target=0, Build=NIL, PlotReady=True)
        r.env.update(R=self.record, Hub=self.hub, Station=self.hub, Base=NIL,
                     faction=Table(ownerless='ownerless'),
                     tag=Table({s:s for s in ('dockarea','storage','pier','base','connection','module','dock_s','dock_m')}))
        self.calls = []
        r.stubs.update(FundAccounts=lambda:None, AssignBuilder=lambda:None)
        def build(node):
            self.calls.append(r.expr(node.get('constructionplan')))
            r.set(node.get('result'), Table(exists=True))
        r.native.update(add_build_to_expand_station=build, process_build=lambda n:None,
                        write_to_logbook=lambda n:None, signal_cue_instantly=lambda n:self.calls.append('generate'))

    def test_native_selection_uses_race_and_smallest_functional_modules(self):
        r = self.run
        for race in ('argon','paranid','teladi','split','boron','terran','conversion_race'):
            r.env['ProfileRace'] = Table(id=race)
            groups = {'dockarea':List([module('dockarea',4),self.components.Dock]),
                      'storage':List([module('storage',0),module('storage',100),self.components.Storage]),
                      'pier':List([module('pier',4),self.components.Pier]),
                      'connection':self.components.Connectors}
            def query(n):
                self.assertEqual(r.expr(n.get('race')).id, race)
                self.assertIsNone(n.get('faction'))
                r.set(n.get('macro'), groups[r.expr(n.get('tags'))[1]])
            r.native['get_module_definition'] = query
            r.library('md.CE_Construction.Resolve')
            self.assertTrue(r.env['Construction'].Valid)
            for key in ('Dock','Storage','Pier'):
                self.assertIs(r.env['Construction'][key], self.components[key])

    def test_missing_components_block_without_replacement(self):
        self.components.Pier = NIL
        self.run.library('md.CE_Construction.Queue')
        self.assertTrue(self.record.ConstructionError)
        self.assertEqual(self.calls, [])

    def test_conversion_can_replace_each_native_role(self):
        r=self.run
        r.env['ProfileRace']=Table(id='custom')
        r.native['get_module_definition']=lambda n:r.set(n.get('macro'),List())
        r.stubs['md.CE_Construction.Configure']=lambda:r.env.update(ConstructionOverrides=Table({'$custom':self.components}))
        r.library('md.CE_Construction.Resolve')
        self.assertTrue(r.env['Construction'].Valid)
        self.assertIs(r.env['Construction'].Dock,self.components.Dock)
        self.assertIs(r.env['Construction'].Connectors,self.components.Connectors)

    def test_requirements_all_levels(self):
        for level, total in enumerate((3,4,5,7,8,10,12,13,14,17), 1):
            self.run.env['BuildLevel'] = level
            self.run.library('md.CE_Construction.Requirements')
            required = self.run.env['RequiredMacros']
            self.assertEqual(len(required), total)
            self.assertEqual(sum(m is self.components.Storage for m in required), level)

    def test_pending_layout_does_not_duplicate_request(self):
        self.run.library('md.CE_Construction.Queue')
        self.run.library('md.CE_Construction.Queue')
        self.assertEqual(self.calls, ['generate'])
        self.assertEqual(self.record.LayoutToken, 1)

    def accept(self, macros, base=NIL):
        r = self.run
        r.env['BuildLevel'] = 1
        r.library('md.CE_Construction.Requirements')
        r.env.update(Sequence=sequence(macros) if macros is not None else NIL, Base=base)
        self.record.LayoutPending = True
        r.library('md.CE_Construction.Accept')

    def test_result_requires_exact_functional_basket_and_permitted_connectors(self):
        valid = [self.components.Storage,self.components.Dock,self.components.Pier]
        for invalid in (None, valid[:-1], valid + [module('storage')], valid + [self.components.Dock]):
            self.accept(invalid)
            self.assertFalse(self.run.env['ValidSequence'])
            self.assertEqual(self.calls, [])
        self.accept(valid + list(self.components.Connectors) * 3)
        self.assertTrue(self.run.env['ValidSequence'])
        self.assertEqual(len(self.calls), 1)
        self.assertIs(self.record.TargetSequence, self.calls[0])

    def test_result_must_preserve_base_entry_ids(self):
        base = sequence([self.components.Storage])
        base[1].id = 'existing-storage'
        self.accept([self.components.Storage,self.components.Dock,self.components.Pier], base)
        self.assertFalse(self.run.env['ValidSequence'])
        self.assertEqual(self.calls, [])

    def test_valid_result_preserves_completed_base(self):
        self.accept([self.components.Storage,self.components.Dock,self.components.Pier],
                    sequence([self.components.Storage]))
        self.assertTrue(self.run.env['ValidSequence'])
        self.assertEqual(len(self.calls),1)

    def test_initial_completion_preserves_earned_level(self):
        self.record.Level = 7
        self.record.Growth = 123
        self.record.TargetSequence = sequence([self.components.Dock])
        self.hub.constructionsequence = self.record.TargetSequence
        self.hub.planmodule = Table({'0':Table(exists=True,isoperational=True)})
        self.run.library('md.CE_Construction.Readiness')
        self.assertTrue(self.run.env['Ready'])
        self.assertFalse(self.run.env['TargetReady'])
        self.assertEqual((self.record.Level,self.record.Growth), (7,123))
        self.assertIs(self.record.TargetSequence, NIL)

    def test_generation_is_async_and_completion_checks_identity(self):
        r = self.run
        r.env.update(event=Table(param=List([self.record,self.hub,1,2])),this='cue')
        r.native['create_construction_sequence'] = lambda n:self.calls.append((r.expr(n.get('macros')),n.find('immediate')))
        r.actions(r.construction.xpath('//cue[@name="Generate"]/actions')[0])
        self.assertEqual(len(self.calls[0][0]), 4)
        self.assertIsNone(self.calls[0][1])
        guard = r.construction.xpath('//cue[@name="Completed"]/actions/do_if')[0]
        self.record.update(LayoutToken=2,LayoutPending=True)
        self.assertFalse(r.expr(guard.get('value')))
        self.record.LayoutToken = 1
        self.assertTrue(r.expr(guard.get('value')))
        self.record.Hub = Component(exists=True)
        self.assertFalse(r.expr(guard.get('value')))


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
        record=Table(LayoutPending=True,LayoutCue='old-cue')
        r.env['Registry']=Table({sector:record})
        for name in ('Reconcile','RefreshProfile','RenameHub','PublishDiagnostics','PublishAllDiagnostics'):
            r.stubs[name]=lambda:None
        cancelled=[]
        r.native['cancel_cue']=lambda n:cancelled.append(r.expr(n.get('cue')))
        r.actions(r.tree.xpath('//cue[@name="Reload"]/actions')[0])
        self.assertIn('old-cue',cancelled)
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


class TerranRecipeTests(unittest.TestCase):
    def test_native_terran_categories_use_terran_construction_materials(self):
        root=REF/'extensions/ego_dlc_terran/libraries'
        groups=E.parse(str(root/'modulegroups.xml'))
        wares=E.parse(str(root/'wares.xml'))
        allowed={'energycells','metallicmicrolattice','siliconcarbide','computronicsubstrate'}
        for group in ('dockarea_ter','stor_ter','pier_base_ter','conn_ter'):
            macros=groups.xpath('//group[@name=$name]//select/@macro',name=group)
            self.assertTrue(macros,group)
            for macro in macros:
                recipes=wares.xpath('//ware[component/@ref=$macro]/production[@method="default"]/primary/ware/@ware',macro=macro)
                self.assertTrue(recipes,macro)
                self.assertLessEqual(set(recipes),allowed,macro)


if __name__ == '__main__':
    unittest.main()
