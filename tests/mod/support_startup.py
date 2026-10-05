"""Native-action harness for startup, construction and lifecycle integration tests."""
import unittest
from support import Runner, Table, List, NIL, Component, definitions, MOD
from lxml import etree as E
from support_construction import module, sequence


class StartupHarness(unittest.TestCase):
    def setUp(self):
        self.run = r = Runner(); definitions(r)
        r.stubs.clear()
        self.events = []; self.pending = []; self.hubs = []; self.builders = []
        self.fail_build = False; self.result_override = None; self.native_requests = []
        self.safe_plot = True; self.plot_calls = []; self.moves = []; self.logs = []
        self.owner = Component(primaryrace=r.env['lookup'].race.list[1])
        self.sector = Component(exists=True, isclass=Table(sector=True), owner=self.owner, macro=Table(id='test_sector_macro'),
                                coreposition=Table(x=0,z=0), knownname='Test sector')
        self.components = {'storage':module('storage'), 'dockarea':module('dockarea'),
                           'pier':module('pier'), 'connection':module('connectionmodule')}
        r.env.update(Sector=self.sector, Registry=Table(), Hubs=List(), R=NIL,
                     PopulationRequest=NIL, PopulationApplied=NIL,
                     faction=Table(ownerless='ownerless',civilian='civilian'),
                     tag=Table({s:s for s in ('storage','dockarea','pier','base','connection','module','dock_s','dock_m')}))
        r.env['player'].update(age=100,entity=Table(),galaxy='galaxy')
        r.native.update(can_safely_extend_build_plot=self.check_plot, extend_build_plot=self.extend_plot,
                        warp=self.warp, debug_text=self.log,
                        get_module_definition=self.get_modules, create_station=self.create_station,
                        create_build_storage=self.create_storage, add_build_to_expand_station=self.add_build,
                        process_build=self.process, transfer_money=self.transfer,
                        signal_cue_instantly=self.generate, find_ship=lambda n:r.set(n.get('name'),List(self.builders)),
                        assign_construction_vessel=self.assign, create_order=self.order,
                        set_object_account=lambda n:None, set_object_name=lambda n:None,
                        write_to_logbook=lambda n:None, show_notification=lambda n:None, create_ai_unit=lambda n:None,
                        create_cue_actor=lambda n:r.set(n.get('name'), Component(exists=True,owner=r.expr(n.find('owner').get('exact')))),
                        assign_control_entity=lambda n:setattr(r.expr(n.get('object')),'tradenpc',r.expr(n.get('actor'))),
                        remove_cue_actor=lambda n:None,
                        add_to_group=lambda n:r.env['Hubs'].append(r.expr(n.get('object'))),
                        create_group=lambda n:r.set(n.get('groupname'),List()),
                        find_sector=lambda n:r.set(n.get('name'),List([self.sector])),
                        raise_lua_event=self.initial_event,
                        set_build_plot=lambda n:None, remove_build=self.remove_build,
                        apply_construction_sequence=self.materialize,
                        signal_objects=lambda n:self.events.append(('operational',r.expr(n.get('param2')))),
                        create_trade_offer=self.offer, update_trade=lambda n:None,
                        cancel_cue=lambda n:self.events.append(('cancel',r.env.get('this') if n.get('cue')=='parent' else r.expr(n.get('cue')))))

    def log(self, n):
        # Evaluate retry log arguments as well as checking their labels. Other logs
        # retain the runner's no-op behavior (localized text is not emulated).
        from md_test_runtime import split
        text=n.get('text')
        if text.startswith(("'[CE] Layout attempt:", "'[CE] Layout retry", "'[CE] Plot retry:", "'[CE] Placement retry:")):
            template,args=text.split("'.[",1)
            self.logs.append((template[1:], [self.run.expr(arg) for arg in split(args[:-1])]))

    def check_plot(self,n):
        growth={side+axis:self.run.expr(n.get(side+axis)) for side in ('neg','pos') for axis in 'xyz'}
        self.plot_calls.append(growth)
        self.run.set(n.get('result'),self.safe_plot)

    def extend_plot(self,n):
        plot=self.run.expr(n.get('object')).buildplot
        for axis in 'xyz':
            neg=self.run.expr(n.get('neg'+axis)); pos=self.run.expr(n.get('pos'+axis))
            self.assertEqual(neg,self.plot_calls[-1]['neg'+axis])
            self.assertEqual(pos,self.plot_calls[-1]['pos'+axis])
            plot.max[axis]+=(neg+pos)/2; plot.center[axis]+=(pos-neg)/2

    def warp(self,n):
        hub=self.run.expr(n.get('object')); pos=n.find('safepos')
        self.assertFalse(hub.buildstorage.exists)
        self.assertEqual(hub.constructionsequence.count,0)
        self.assertEqual(pos.get('includeplotbox'),'true')
        self.assertIs(self.run.expr(pos.get('ignored')),hub)
        self.moves.append(hub)
        hub.position=Table({axis:self.run.expr(pos.get(axis)) for axis in 'xyz'})
        self.assertGreaterEqual(self.run.expr(pos.get('radius')),max(hub.buildplot.max.values())*2)

    def retry(self):
        self.run.env['player'].age += 300
        return self.start()

    def get_modules(self, n):
        nodes=E.parse(str(MOD/'libraries/constructionplans.xml')).xpath('//plan/entry/@macro')
        self.run.set(n.get('macro'),List(Component(id=name) for name in sorted(set(nodes))))

    def remove_build(self,n):
        task=self.run.expr(n.get('build'));storage=self.run.expr(n.get('object'))
        for group in (storage.builds.queued,storage.builds.inprogress):
            if task in group:group.remove(task)
        task.exists=False

    def initial_event(self,n):
        if self.run.expr(n.get('name')) != 'CEInitialHubBuildReady':return
        hub=self.run.expr(n.get('param'));record=self.run.env['R']
        self.assertIn(hub,self.run.env['player'].entity.ce_initial_build_hubs)
        plan=record.TargetSequence
        hub.constructionsequence=plan
        hub.planmodule=Table({entry.id:Component(exists=True,isoperational=True) for entry in plan})
        hub.isoperational=True;hub.buildstorage.builds.inprogress.clear()
        record.Build.exists=False
        self.events.append(('materialize',hub))
        self.run.env.update(Hub=hub,Sector=hub.sector)
        self.run.library('UpdateHub')

    def create_station(self, n):
        self.assertIsNone(n.find('construction'))
        hub = Component(exists=True, iswreck=False, isoperational=False, owner=self.run.expr(n.get('owner')),
                        sector=self.run.env['Sector'], isclass=Table(container=True), money=0,
                        buildstorage=NIL, constructionsequence=NIL, planmodule=Table(), position=Table(x=50000,y=0,z=0),
                        hasrelation=Table(dock=Table()),
                        buildplot=Table(max=Table(x=5000,y=5000,z=5000),center=Table(x=0,y=0,z=0)))
        self.hubs.append(hub); self.run.set(n.get('name'),hub)
        for builder in self.builders: self.allow(builder,hub)

    def create_storage(self, n):
        hub = self.run.expr(n.get('station'))
        hub.buildstorage = Component(exists=True,isoperational=True,money=0,wantedmoney=0,
                                     builds=Table(queued=List(),inprogress=List()),
                                     buildmodule=Component(exists=True,constructionvessel=NIL))

    def materialize(self, n):
        hub=self.run.expr(n.get('station')); plan=self.run.expr(n.get('sequence'))
        if hub.buildstorage.exists:
            self.assertEqual(hub.buildstorage.builds.queued.count + hub.buildstorage.builds.inprogress.count,0)
        self.assertFalse(hub.constructionsequence)
        hub.constructionsequence=plan
        hub.planmodule=Table({entry.id:Component(exists=True,isoperational=True) for entry in plan})
        hub.isoperational=True
        self.events.append(('materialize',hub))

    def add_build(self, n):
        from support_construction import Sequence
        r=self.run; hub=r.expr(n.get('buildobject'))
        self.events.append(('queue',hub))
        source=r.expr(n.get('constructionplan'));level=r.expr(n.find('stage').get('exact'))
        self.native_requests.append((source,level))
        if self.fail_build:
            r.set(n.get('result'),NIL); return
        if isinstance(source,str):
            nodes=E.parse(str(MOD/'libraries/constructionplans.xml')).xpath('//plan[@id=$id]/entry',id=source)
            full=sequence([Component(id=e.get('macro')) for e in nodes])
            class Metadata(Table):
                @property
                def count(self):return 10
            full.hasstages=True;full.stage=Metadata()
            first=0
            for i,last in enumerate([j for j,e in enumerate(nodes) if e.get('bookmark')=='1'],1):
                full.stage[i]=Table(first=first,last=last);first=last+1
            full.stage[10]=Table(first=len(nodes),last=len(nodes))
        else:full=source
        count=full.count if level==10 else full.stage[level].last+1
        active=Sequence(list(full)[:count])
        active.hasstages=True;active.stage=Table(current=level);active.finalsequence=full
        if self.result_override is not None:active=self.result_override
        task=Component(exists=True,constructionsequence=active)
        hub.buildstorage.builds.queued.append(task)
        r.set(n.get('result'),task)

    def process(self, n):
        r=self.run; storage=r.expr(n.get('object')); task=r.expr(n.get('build'))
        self.assertIs(r.expr(n.get('buildmodule')),storage.buildmodule)
        if task in storage.builds.queued: storage.builds.queued.remove(task)
        if task not in storage.builds.inprogress: storage.builds.inprogress.append(task)
        storage.wantedmoney=500000
        self.events.append(('process',storage))

    def transfer(self, n):
        r=self.run; recipient=r.expr(n.get('to')); amount=r.expr(n.get('amount'))
        recipient.money += amount; r.set(n.get('result'),amount)
        self.events.append(('fund',recipient))

    def generate(self, n):
        r=self.run
        self.assertEqual(n.get('cue'),'md.CE_Construction.Generate')
        captured=dict(r.env)
        captured.update(event=Table(param=r.expr(n.get('param'))),this=Component(exists=True))
        self.pending.append(captured)

    def allow(self, builder, hub):
        hub.hasrelation.dock[builder]=True
        builder.gatedistance[hub]=0
        builder.owner.hasrelation.enemy[hub.sector.owner]=False

    def builder(self):
        builder=Component(exists=True,isplayerowned=False,pilot=Component(exists=True),
                          constructionmodule=NIL,order=Table(id='FindBuildTasks'),nextorder=NIL,
                          owner=Component(hasrelation=Table(enemy=Table())),gatedistance=Table())
        self.builders.append(builder)
        for hub in self.hubs:self.allow(builder,hub)
        return builder

    def assign(self, n):
        r=self.run; builder=r.expr(n.get('object')); buildmodule=r.expr(n.get('buildmodule'))
        self.assertFalse(buildmodule.constructionvessel.exists)
        buildmodule.constructionvessel=builder; builder.constructionmodule=buildmodule
        self.events.append(('assign',builder))

    def order(self, n):
        r=self.run; station=r.expr(n.find('param[@name="station"]').get('value'))
        builder=r.expr(n.get('object')); builder.order=Table(id='DeployToStation')
        self.assertIs(station.buildstorage.buildmodule.constructionvessel,builder)
        self.assertGreaterEqual(station.buildstorage.money,station.buildstorage.wantedmoney)
        self.events.append(('order',station))

    def offer(self, n):
        r=self.run
        r.set(n.get('name'),Component(exists=True,amount=r.expr(n.get('amount')),
                                    offeramount=r.expr(n.get('amount'))))

    def start(self, sector=None):
        r=self.run; sector=sector or self.sector
        r.env.update(Sector=sector,Population=100000000)
        r.library('ReconcileSector')
        return r.env['Registry'][sector]

    def complete(self, index=0, success=True, result=None, all_stages=True):
        r=self.run;caller=r.env
        old_fail=self.fail_build
        try:
            r.env=self.pending[index]
            self.fail_build=old_fail or not success
            self.result_override=result
            r.actions(r.construction.xpath('//cue[@name="Generate"]/actions')[0])
        finally:
            r.env=caller;self.fail_build=old_fail;self.result_override=None
