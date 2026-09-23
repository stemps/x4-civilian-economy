"""Shared fixtures for shipped MD action tests; native behavior remains mocked."""
import os
import sys
from pathlib import Path
from lxml import etree as E

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from md_test_runtime import Runner, Table, List, NIL, wrap, Component

REF = Path(os.environ.get('CE_REFERENCE', os.environ.get('X4_REFERENCE', str(ROOT.parent.parent / 'reference')))).resolve()
Object = Component

class Ware(str):
    averageprice=1600
    minprice=1000
    maxprice=2200
    iscargo=True
    waretransport="container"
    @property
    def id(self): return str(self)
    @property
    def name(self): return str(self)

def definitions(run):
    recipes=E.parse(str(REF/'libraries/wares.xml'))
    types=Table({w.get('id'):Ware(w.get('id')) for w in recipes.xpath('/wares/ware[price]')})
    for node in recipes.xpath('/wares/ware[price]'):
        types[node.get('id')].group=Table(id=node.get('group',''))
        types[node.get('id')].averageprice=int(node.find('price').get('average')) * 100
    races=List([Table(id=name,workforce=Table(resources=List([
        types[n.get('ware')] for n in recipes.xpath('/wares/ware[@id="workunit_busy"]/production[@method=$method]/primary/ware',method='default' if name == 'argon' else name)
    ]))) for name in ('argon','paranid','teladi')])
    run.env.update(ware=types, lookup=Table(ware=Table(list=List(list(types.values()))),race=Table(list=races)),
                   waretransport=Table(container='container'), Sector=Component(owner=Table(primaryrace=races[1])))
    run.env.update(SectorProfiles=Table(),RaceProfiles=Table())
    def resolve():
        run.env['Construction']=Table(Valid=True,Dock='dock',Storage='storage',Pier='pier',Connectors=List(['connector']))
    run.stubs['md.CE_Construction.Resolve']=resolve
    run.env['ProfileRace']=races[1]
    run.library('md.CE_PopulationProfiles.Build')
    run.env['Definitions']=run.env['CandidateDefinitions']
    run.env.setdefault('R',NIL)
    run.env['md'].CE_OwnerlessHub.Init=Table()

class ProfileFixture:
    def setUp(self):
        self.run = Runner()
        definitions(self.run)
        self.r = Table(GrowthSeconds=0.0, Last=0.0, Level=1, Target=0, Operational=True, Wares=Table(),
                       Transfers=Table(), Hub=NIL, Factor=1, Population=8524100000,
                       PauseOffers=False, PlotReady=False, TestUpgrade=False)
        self.run.env['R'] = self.r

    def ware(self, name, group='food', transport='container'):
        ware = Ware(name)
        ware.group = Table(id=group)
        ware.waretransport = transport
        self.run.env['lookup'].ware.list.append(ware)
        return ware

    def race(self, name, wares):
        race = Table(id=name, workforce=Table(resources=List(wares)))
        self.run.env['lookup'].race.list.append(race)
        return race

    def select(self, race):
        self.run.env['Sector'] = Component(owner=Table(primaryrace=race))

    def apply(self, level=1):
        self.r['Level'] = level
        self.run.library('RefreshProfile')
        self.run.library('ApplyLevel')
        return {w for w, state in self.r.Wares.items() if state.Rate > 0}

    def configure(self, statements):
        actions = self.run.profiles.xpath('//library[@name="Configure"]/actions')[0]
        for statement in statements:
            actions.append(E.fromstring(statement))

