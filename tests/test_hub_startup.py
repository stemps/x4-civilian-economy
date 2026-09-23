"""Startup orchestration executes shipped libraries; only native actions are mocked."""
import unittest
from support import Runner, Table, List, NIL, Component, definitions
from test_construction import module, sequence


class StartupHarness(unittest.TestCase):
    def setUp(self):
        self.run = r = Runner(); definitions(r)
        r.stubs.clear()
        self.events = []; self.pending = []; self.hubs = []; self.builders = []
        self.fail_build = False
        self.safe_plot = True; self.plot_calls = []; self.moves = []; self.logs = []
        self.owner = Component(primaryrace=r.env['lookup'].race.list[1])
        self.sector = Component(exists=True, isclass=Table(sector=True), owner=self.owner,
                                coreposition=Table(x=0,z=0), knownname='Test sector')
        self.components = {'storage':module('storage'), 'dockarea':module('dockarea'),
                           'pier':module('pier'), 'connection':module('connectionmodule')}
        r.env.update(Sector=self.sector, Registry=Table(), Hubs=List(), R=NIL,
                     PopulationRequest=NIL, PopulationApplied=NIL,
                     faction=Table(ownerless='ownerless'),
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
                        write_to_logbook=lambda n:None, create_ai_unit=lambda n:None,
                        create_cue_actor=lambda n:r.set(n.get('name'), Component(exists=True)),
                        assign_control_entity=lambda n:setattr(r.expr(n.get('object')),'tradenpc',r.expr(n.get('actor'))),
                        remove_cue_actor=lambda n:None,
                        add_to_group=lambda n:r.env['Hubs'].append(r.expr(n.get('object'))),
                        create_group=lambda n:r.set(n.get('groupname'),List()),
                        find_sector=lambda n:r.set(n.get('name'),List([self.sector])),
                        raise_lua_event=lambda n:None,
                        create_construction_sequence=lambda n:None,
                        signal_objects=lambda n:self.events.append(('operational',r.expr(n.get('param2')))),
                        create_trade_offer=self.offer, update_trade=lambda n:None,
                        cancel_cue=lambda n:self.events.append(('cancel',r.expr(n.get('cue')))))

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
        self.run.set(n.get('macro'), List([self.components[self.run.expr(n.get('tags'))[1]]]))

    def create_station(self, n):
        self.assertIsNone(n.find('construction'))
        hub = Component(exists=True, iswreck=False, isoperational=False, owner='ownerless',
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

    def add_build(self, n):
        r=self.run; hub=r.expr(n.get('buildobject'))
        self.events.append(('queue',hub))
        if self.fail_build:
            r.set(n.get('result'),NIL); return
        task=Component(exists=True,constructionsequence=r.expr(n.get('constructionplan')))
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
        r=self.run; caller=r.env
        self.assertEqual(n.get('cue'),'md.CE_Construction.Generate')
        captured=dict(caller)
        captured.update(event=Table(param=r.expr(n.get('param'))),this='layout-'+str(len(self.pending)))
        try:
            r.env=captured
            r.actions(r.construction.xpath('//cue[@name="Generate"]/actions')[0])
        finally: r.env=caller
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

    def complete(self, index=0, success=True, result=None):
        r=self.run; caller=r.env; context=self.pending[index]
        if result is None: result=sequence(context['RequiredMacros'])
        try:
            r.env=context; context['event']=Table(param=result,param2=success)
            r.actions(r.construction.xpath('//cue[@name="Completed"]/actions')[0])
        finally:r.env=caller


class HubStartupTests(StartupHarness):
    def test_fresh_init_to_operational_with_real_startup_libraries(self):
        r=self.run; builder=self.builder()
        r.actions(r.tree.xpath('//cue[@name="Init"]/actions')[0])
        self.assertIn(self.sector,r.env['SectorProfiles'])
        r.env['player'].entity.ce_population_response=List([r.env['PopulationRequest'],List([List([self.sector,100000000])])])
        r.actions(r.tree.xpath('//cue[@name="PopulationReceived"]/actions')[0])
        record=r.env['Registry'][self.sector]; hub=record.Hub
        self.assertFalse(record.Operational); self.assertIs(hub.constructionsequence,NIL)
        self.complete()
        self.assertIs(hub.buildstorage.buildmodule.constructionvessel,builder)
        stages=[kind for kind,_ in self.events]
        self.assertLess(stages.index('queue'),stages.index('process'))
        storage_fund=next(i for i,(kind,obj) in enumerate(self.events) if kind=='fund' and obj is hub.buildstorage)
        self.assertLess(stages.index('process'),storage_fund)
        self.assertLess(storage_fund,stages.index('assign'))
        self.assertTrue(hub.buildstorage.tradenpc.exists)
        hub.constructionsequence=record.TargetSequence
        hub.planmodule=Table({entry.id:Component(exists=True,isoperational=True) for entry in record.TargetSequence})
        hub.isoperational=True; r.env.update(R=record,Hub=hub)
        r.library('UpdateHub')
        self.assertTrue(record.Operational); self.assertIs(record.TargetSequence,NIL)
        self.assertTrue(all(w.Offer.exists for w in record.Wares.values() if w.Rate>0))

    def test_no_builder_then_later_retry_without_duplicate_build_or_order(self):
        record=self.start(); self.complete()
        self.assertFalse(record.Hub.buildstorage.buildmodule.constructionvessel.exists)
        self.builder(); self.start(); self.start(); self.complete()
        self.assertEqual(sum(k=='queue' for k,_ in self.events),1)
        self.assertEqual(sum(k=='order' for k,_ in self.events),1)

    def test_unsuccessful_and_null_results_retry_without_queueing(self):
        for success,result in [(False,None),(True,NIL)]:
            with self.subTest(success=success):
                self.setUp(); record=self.start(); self.complete(success=success,result=result)
                self.assertFalse(record.LayoutPending); self.assertTrue(record.ConstructionError)
                self.assertFalse(any(k=='queue' for k,_ in self.events))
                self.start(); self.assertEqual(len(self.pending),1)
                self.retry(); self.assertEqual(len(self.pending),2)

    def test_failed_build_creation_can_retry(self):
        record=self.start(); self.fail_build=True; self.complete()
        self.assertTrue(record.ConstructionError); self.assertFalse(record.Build.exists)
        self.assertFalse(record.LayoutPending)
        self.fail_build=False; self.retry(); self.complete(index=1)
        self.assertTrue(record.Build.exists); self.assertFalse(record.ConstructionError)

    def test_recover_lost_task_reuses_layout_and_starts_builder(self):
        record=self.start(); self.complete(); original=record.TargetSequence
        record.Build.exists=False; record.Hub.buildstorage.builds.inprogress.clear()
        self.builder(); self.start(); self.start()
        self.assertIs(record.TargetSequence,original)
        self.assertEqual(len(self.pending),1)
        self.assertEqual(sum(k=='queue' for k,_ in self.events),2)
        self.assertEqual(sum(k=='order' for k,_ in self.events),1)

    def test_two_hubs_complete_out_of_order_and_stale_callback_is_ignored(self):
        self.builder(); self.builder(); first=self.start()
        other=Component(exists=True,isclass=Table(sector=True),owner=self.owner,knownname='Other')
        second=self.start(other)
        self.complete(index=1); self.complete(index=0)
        ordered=[hub for kind,hub in self.events if kind=='order']
        self.assertEqual(ordered,[second.Hub,first.Hub])
        self.complete(index=1)
        self.assertEqual(sum(k=='order' for k,_ in self.events),2)
        # A superseded request must not consume the newer request's pending flag.
        first.LayoutPending=True; first.LayoutToken+=1
        self.complete(index=0)
        self.assertTrue(first.LayoutPending)
        self.assertEqual(sum(k=='queue' for k,_ in self.events),2)

    def test_expansion_uses_completed_base_and_queues_only_added_modules(self):
        record=self.start(); self.complete(); r=self.run; hub=record.Hub
        hub.constructionsequence=record.TargetSequence
        hub.planmodule=Table({entry.id:Component(exists=True,isoperational=True) for entry in record.TargetSequence})
        hub.isoperational=True; hub.buildstorage.builds.inprogress.clear()
        r.env.update(R=record,Hub=hub); r.library('UpdateHub')
        base=record.CompletedSequence
        record.Target=2; r.library('QueueExpansion')
        self.assertIs(self.pending[1]['Base'],base)
        self.assertEqual(list(self.pending[1]['NewMacros']),[self.components['storage']])
        self.complete(index=1)
        self.assertEqual(record.Level,1)
        self.assertIs(record.CompletedSequence,base)
        self.assertEqual(record.TargetSequence.count,4)
        for entry in base:
            self.assertIs(record.TargetSequence[entry.id].macro,entry.macro)
        self.assertEqual(sum(k=='queue' for k,_ in self.events),2)
        r.actions(r.tree.xpath('//cue[@name="Reload"]/actions')[0])
        self.start()
        self.assertEqual(sum(k=='queue' for k,_ in self.events),2)

    def test_completion_ignores_destroyed_reowned_or_replaced_hub(self):
        for changed in ('destroyed','owner','replaced'):
            with self.subTest(changed=changed):
                self.setUp(); record=self.start()
                if changed=='destroyed': record.Hub.exists=False
                elif changed=='owner': record.Hub.owner='argon'
                else: record.Hub=Component(exists=True)
                self.complete()
                self.assertFalse(any(k=='queue' for k,_ in self.events))

    def test_reload_restarts_pending_generation_and_preserves_queued_layout(self):
        record=self.start(); r=self.run
        r.actions(r.tree.xpath('//cue[@name="Reload"]/actions')[0])
        self.assertFalse(record.LayoutPending)
        self.assertTrue(any(k=='cancel' for k,_ in self.events))
        self.start(); self.complete(index=0)
        self.assertFalse(record.Build.exists)
        self.complete(index=1); target=record.TargetSequence
        r.actions(r.tree.xpath('//cue[@name="Reload"]/actions')[0])
        self.start()
        self.assertIs(record.TargetSequence,target)
        self.assertEqual(sum(k=='queue' for k,_ in self.events),1)


if __name__ == '__main__': unittest.main()
