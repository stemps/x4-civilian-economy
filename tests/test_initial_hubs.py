"""One-shot initialization permission, independently of later build recovery."""
from support import Table, List, NIL, Component
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
                    self.assertFalse(any(k=='queue' for k,_ in self.events))

    def initial(self, reset=False):
        r=self.run
        r.env['md'].CE_OwnerlessHub.Init.Registry=r.env['Registry']
        if reset:
            r.env['md'].CE_DebugReset.State.update(Busy=True,Phase='initializing',Token=1,
                Pending=List(),Total=0,Blocked=False)
            r.actions(r.tree.xpath('//cue[@name="ResetRebuild"]/actions')[0])
        else:
            r.actions(r.tree.xpath('//cue[@name="Init"]/actions')[0])
            r.env['md'].CE_OwnerlessHub.Init.Registry=r.env['Registry']
        r.env['player'].entity.ce_population_response=List([r.env['PopulationRequest'],List([List([self.sector,100000000])])])
        r.actions(r.tree.xpath('//cue[@name="PopulationReceived"]/actions')[0])
        return r.env['Registry'][self.sector]

    def test_initial_and_reset_hubs_materialize_only_after_all_ten_plans_validate(self):
        for reset in (False,True):
            with self.subTest(reset=reset):
                self.setUp();record=self.initial(reset)
                self.assertIs(record.InitialHub,record.Hub)
                self.assertFalse(self.run.env['InitialPopulationPass'])
                for _ in range(9):
                    self.complete(all_stages=False)
                    self.assertFalse(record.Hub.constructionsequence)
                    self.assertFalse(record.Build.exists)
                self.complete()
                self.assertTrue(record.Operational)
                self.assertIs(record.InitialHub,NIL)
                self.assertEqual(record.LayoutPlans.count,10)
                self.assertEqual(record.CompletedSequence.count,3)
                self.assertFalse(record.Hub.buildstorage.exists)

    def test_expansion_uses_regular_build_and_preserves_prepared_plans(self):
        record=self.initial();self.complete();plans=record.LayoutPlans
        self.builder();record.Target=2;self.start()
        self.assertTrue(record.Build.exists)
        self.assertIs(record.TargetSequence,plans[2])
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

    def test_later_discovery_and_legacy_records_use_regular_construction(self):
        record=self.start();self.complete()
        self.assertFalse(record.Operational)
        self.assertTrue(record.Build.exists)
        self.assertFalse(any(k=='materialize' for k,_ in self.events))
