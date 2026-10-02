"""One-shot initialization permission, independently of later build recovery."""
from support import Table, List, NIL, Component, REF, MOD
from lxml import etree as E
from support_startup import StartupHarness


class InitialHubTests(StartupHarness):
    def test_native_empty_build_storage_does_not_prevent_instant_initial_completion(self):
        for busy in (False,True):
            with self.subTest(busy=busy):
                self.setUp()
                create=self.create_station
                def native_create(n):
                    create(n)
                    self.hubs[-1].buildstorage=Component(exists=True,money=0,wantedmoney=0,
                        buildmodule=Component(exists=True,constructionvessel=NIL),builds=Table(
                        queued=List([Component(exists=True)]) if busy else List(),inprogress=List()))
                self.run.native['create_station']=native_create
                record=self.initial(reset=True)
                if busy:
                    self.assertFalse(self.pending)
                    self.assertFalse(record.Operational)
                else:
                    self.complete()
                    self.assertTrue(record.Operational)
                    self.assertEqual(sum(k=='materialize' for k,_ in self.events),1)
                    self.assertEqual(sum(k=='queue' for k,_ in self.events),1)

    def test_native_build_completion_preserves_ce_manager_and_other_stations(self):
        base=E.parse(str(REF/'aiscripts/build.buildstorage.xml'))
        patch=E.parse(str(MOD/'aiscripts/build.buildstorage.xml')).findall('replace')[-1]
        original=base.xpath(patch.get('sel'))
        self.assertEqual(len(original),1)
        r=self.run
        r.env['faction'].update(player='player',ownerless='ownerless')
        for registered in (False,True):
            for tracked in (False,True):
                for manager in (NIL,Component(exists=True)):
                    for owner in ('civilian','argon','player','ownerless',NIL):
                        hub=Component(tradenpc=manager)
                        r.env.update(baseowner=owner,this=Table(object=Table(base=hub)))
                        r.env['player'].entity.ce_hubs=List([hub]) if registered else List()
                        protected=registered
                        expected=bool(r.expr(str(original[0]))) and not (protected and bool(manager))
                        self.assertEqual(bool(r.expr(patch.text)),expected)

    def test_cross_script_initialization_helpers_are_explicit(self):
        pending=['md.CE_CivilianHub.UpdateHub'];seen=set()
        while pending:
            ref=pending.pop()
            if ref in seen:continue
            seen.add(ref)
            _,script,name=ref.split('.')
            nodes=self.run.scripts[script].xpath('//library[@name=$name]//include_actions',name=name)
            for node in nodes:
                child=node.get('ref')
                self.assertTrue(child.startswith('md.'),child)
                pending.append(child)

    def initial(self, reset=False):
        r=self.run
        r.env['md'].CE_CivilianHub.Init.Registry=r.env['Registry']
        if reset:
            r.env['md'].CE_DebugReset.State.update(Busy=True,Phase='initializing',Token=1,
                Pending=List(),Total=0,Blocked=False)
            r.actions(r.tree.xpath('//cue[@name="ResetRebuild"]/actions')[0])
        else:
            r.actions(r.tree.xpath('//cue[@name="Init"]/actions')[0])
            r.env['md'].CE_CivilianHub.Init.Registry=r.env['Registry']
        r.env['player'].entity.ce_population_response=List([r.env['PopulationRequest'],List([List([self.sector,100000000])])])
        r.actions(r.tree.xpath('//cue[@name="PopulationReceived"]/actions')[0])
        return r.env['Registry'][self.sector]

    def test_initial_and_reset_hubs_complete_only_stage_one(self):
        for reset in (False,True):
            with self.subTest(reset=reset):
                self.setUp();builder=self.builder();record=self.initial(reset)
                self.assertIs(record.InitialHub,record.Hub)
                self.complete()
                self.assertTrue(record.Operational)
                self.assertIs(record.InitialHub,NIL)
                self.assertEqual(record.FullSequence.stage.count,10)
                self.assertEqual(record.CompletedSequence.count,record.Construction.Levels[1].count)
                self.assertLess(record.CompletedSequence.count,record.FullSequence.count)
                self.assertEqual(self.native_requests[0],(record.Construction.Plan,1))
                self.assertEqual(sum(k=='materialize' for k,_ in self.events),1)
                self.assertIs(builder.constructionmodule,NIL)
                self.assertFalse(any(k in ('assign','order') for k,_ in self.events))
                self.assertTrue(record.Hub.buildstorage.exists)
                self.assertEqual(record.Hub.buildstorage.money,0)
                self.assertGreater(record.Hub.money,0)
                self.assertFalse(any(k=='fund' and obj is record.Hub.buildstorage for k,obj in self.events))

    def test_pending_initial_completion_never_books_builder_during_recovery(self):
        for reset in (False,True):
            with self.subTest(reset=reset):
                self.setUp();builder=self.builder();record=self.initial(reset)
                self.run.native['raise_lua_event']=lambda n:None
                self.complete()
                self.assertTrue(record.Build.exists)
                self.assertIs(record.InitialHub,record.Hub)
                self.retry()
                self.run.env.update(R=record,Hub=record.Hub,Sector=self.sector)
                self.run.library('md.CE_Construction.StartBuild')
                self.assertEqual(record.Hub.buildstorage.money,0)
                self.assertGreater(record.Hub.money,0)
                self.assertIs(builder.constructionmodule,NIL)
                self.assertFalse(any(k in ('assign','order') for k,_ in self.events))
                self.run.native['raise_lua_event']=self.initial_event
                self.run.env['player'].age+=2
                self.run.library('md.CE_Construction.InitialTick')
                self.assertTrue(record.Operational)
                self.assertIs(record.InitialHub,NIL)
                record.Target=2;self.start();self.complete(index=1)
                self.assertIs(record.Hub.buildstorage.buildmodule.constructionvessel,builder)
                self.assertEqual(record.Hub.buildstorage.money,record.Hub.buildstorage.wantedmoney)

    def test_idle_storage_preserves_leftovers_without_topping_up_stale_budget(self):
        record=self.initial();self.complete()
        storage=record.Hub.buildstorage
        storage.money=12345
        storage.cargo=Table(hullparts=100)
        # The harness retains the previous requested budget after completion.
        self.assertGreater(storage.wantedmoney,storage.money)
        self.retry()
        self.assertIs(record.Hub.buildstorage,storage)
        self.assertEqual(storage.money,12345)
        self.assertEqual(storage.cargo.hullparts,100)

    def test_expansion_uses_regular_build_and_preserves_master_sequence(self):
        record=self.initial();self.complete();full=record.FullSequence
        self.builder();record.Target=2;self.start();self.complete(index=1)
        self.assertTrue(record.Build.exists)
        self.assertIs(record.FullSequence,full)
        self.assertEqual(record.Level,1)
        self.assertTrue(record.Hub.buildstorage.buildmodule.constructionvessel.exists)
        self.assertEqual(sum(k=='materialize' for k,_ in self.events),1)

    def test_destruction_before_or_after_materialization_never_grants_replacement_permission(self):
        for completed in (False,True):
            with self.subTest(completed=completed):
                self.setUp();record=self.initial()
                if completed:self.complete()
                original=record.Hub;original.exists=False
                replacement=self.start()
                self.assertIs(replacement,record)
                self.assertEqual(record.Generation,2)
                self.assertIs(record.InitialHub,NIL)
                self.complete(index=1)
                self.assertTrue(record.Build.exists)
                self.assertEqual(sum(k=='materialize' for k,_ in self.events),int(completed))
                self.assertEqual(record.Hub.buildstorage.money,record.Hub.buildstorage.wantedmoney)

    def test_reload_retains_pending_permission_but_does_not_replay_completed_initialization(self):
        record=self.initial();hub=record.Hub
        self.run.actions(self.run.tree.xpath('//cue[@name="Reload"]/actions')[0])
        self.assertIs(record.InitialHub,hub)
        self.start();self.complete(index=0)
        self.assertFalse(hub.constructionsequence)
        self.complete(index=1);self.assertTrue(record.Operational)
        self.run.actions(self.run.tree.xpath('//cue[@name="Reload"]/actions')[0])
        self.start();self.assertEqual(sum(k=='materialize' for k,_ in self.events),1)

    def test_failed_planning_preserves_permission_for_same_hub_retry(self):
        record=self.initial();self.complete(success=False)
        self.assertIs(record.InitialHub,record.Hub)
        self.assertFalse(record.Hub.constructionsequence)
        self.retry();self.complete(index=1)
        self.assertTrue(record.Operational)
        self.assertEqual(sum(k=='materialize' for k,_ in self.events),1)

    def test_later_discovery_uses_regular_construction(self):
        record=self.start();self.complete()
        self.assertFalse(record.Operational)
        self.assertTrue(record.Build.exists)
        self.assertFalse(any(k=='materialize' for k,_ in self.events))
        self.assertEqual(record.Hub.buildstorage.money,record.Hub.buildstorage.wantedmoney)
