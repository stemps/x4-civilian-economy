"""Run shipped debug creation and lifecycle actions with native construction mocks."""
import copy
from support import Table, List, NIL, Component
from test_hub_startup import StartupHarness


class DebugCreateTests(StartupHarness):
    def setUp(self):
        super().setUp()
        self.run.env['md'].CE_OwnerlessHub.Init.Registry = self.run.env['Registry']
        self.raised = []
        self.feedback = []
        self.run.native['raise_lua_event'] = lambda n: self.raised.append(
            (self.run.expr(n.get('name')), self.run.expr(n.get('param')) if n.get('param') else NIL))
        self.run.native['write_to_logbook'] = lambda n: self.feedback.append(n.get('text'))

    def request(self, sector=None):
        self.run.env['event'] = Table(param3=sector if sector is not None else self.sector)
        self.run.library('md.CE_DebugCreate.Request')
        return self.run.env['Registry'][self.sector]

    def finish(self, record):
        hub = record.Hub
        hub.constructionsequence = record.TargetSequence
        hub.planmodule = Table({e.id:Component(exists=True, isoperational=True) for e in record.TargetSequence})
        hub.isoperational = True
        hub.buildstorage.builds.inprogress.clear()
        self.run.env.update(R=record, Hub=hub, Sector=self.sector)
        self.run.library('UpdateHub')
        self.run.library('md.CE_DebugCreate.Tick')

    def test_create_and_all_native_population_values_keep_five_billion(self):
        record = self.request()
        self.assertEqual((record.Level, record.Target, record.Population), (1, 0, 5_000_000_000))
        self.assertAlmostEqual(record.Factor, 5_000_000_000 / 8_524_100_000)
        rates = {w:state.Rate for w,state in record.Wares.items()}
        self.assertTrue(any(rates.values()))
        for population in (0, 5_000_000, 100_000_000, 18_000_000_000):
            self.run.env.update(Sector=self.sector, Population=population)
            self.run.library('ReconcileSector')
            self.assertEqual(record.Population, 5_000_000_000)
            self.assertEqual(rates, {w:state.Rate for w,state in record.Wares.items()})
        self.assertEqual(len(self.hubs), 1)
        self.assertEqual(self.run.env['player'].entity.ce_hub_sectors, [self.sector])

    def test_invalid_duplicate_and_captured_hub_requests_do_not_mutate(self):
        for target in (NIL, Component(exists=True, isclass=Table(sector=False))):
            self.request(target)
        self.assertEqual(len(self.hubs), 0)
        record = self.start()
        record.Hub.owner = 'player'
        before = (record.Population, record.Definitions, record.Level)
        self.request(); self.request()
        self.assertEqual(len(self.hubs), 1)
        self.assertEqual(before, (record.Population, record.Definitions, record.Level))
        self.assertIs(record.PopulationOverride, NIL)
        self.assertEqual(self.run.env['player'].entity.ce_hub_sectors, [self.sector])

    def test_duplicate_debug_request_does_not_reset_pending_layout(self):
        record = self.request()
        token, hub = record.LayoutToken, record.Hub
        self.request(); self.request()
        self.assertEqual(len(self.hubs), 1)
        self.assertEqual(len(self.pending), 1)
        self.assertEqual(record.LayoutToken, token)
        self.assertIs(record.DebugInitialHub, hub)

    def test_saved_record_preserves_override_and_ordinary_sector_is_independent(self):
        record = self.request()
        saved = copy.deepcopy(record)
        self.run.env['Registry'][self.sector] = saved
        self.run.env.update(R=saved, Sector=self.sector, Population=0)
        self.run.library('ReconcileSector')
        self.assertEqual(saved.Population, 5_000_000_000)
        self.assertIs(saved.DebugInitialHub, saved.Hub)
        other = Component(exists=True, isclass=Table(sector=True), owner=self.owner,
                          coreposition=Table(x=0,z=0), knownname='Ordinary sector')
        normal = self.start(other)
        self.assertEqual(normal.Population, 100_000_000)
        self.assertIs(normal.PopulationOverride, NIL)
        self.assertIs(normal.DebugInitialHub, NIL)
        self.run.env.update(Sector=other, Population=0)
        self.run.library('ReconcileSector')
        self.assertEqual(normal.Population, 0)
        self.assertEqual(saved.Population, 5_000_000_000)

    def test_argon_fallback_is_saved_without_changing_shared_profiles(self):
        self.sector.owner = NIL
        record = self.request()
        frozen = self.run.env['SectorProfiles'][self.sector]
        self.assertFalse(frozen.Construction.Valid)
        self.assertTrue(record.DebugFallback)
        self.assertEqual(record.ProfileRace, 'argon')
        self.assertIsNot(record.DebugProfile, frozen)
        self.assertFalse(self.run.env['RaceProfiles']['$unknown'].Construction.Valid)
        profile = record.DebugProfile
        self.sector.owner = self.owner
        self.run.library('Reconcile')
        self.assertIs(record.DebugProfile, profile)
        self.assertEqual(record.ProfileRace, 'argon')

    def test_invalid_fallback_leaves_no_record_or_partial_override(self):
        self.sector.owner = NIL
        self.run.native['get_module_definition'] = lambda n:self.run.set(n.get('macro'), List())
        self.request()
        self.assertNotIn(self.sector, self.run.env['Registry'])
        self.assertEqual(len(self.hubs), 0)
        self.assertEqual(self.run.env['DebugFailure'], 136)
        self.assertTrue(self.feedback)

    def test_invalid_fallback_preserves_existing_hubless_record(self):
        record = self.start()
        self.run.library('ForgetHub')
        profile = self.run.env['SectorProfiles'][self.sector]
        profile.Valid = False
        before = copy.deepcopy(record)
        self.run.native['get_module_definition'] = lambda n:self.run.set(n.get('macro'), List())
        self.request()
        self.assertIs(record.PopulationOverride, NIL)
        self.assertEqual(record.Population, before.Population)
        self.assertEqual(record.Level, before.Level)
        self.assertEqual(len(self.hubs), 1)

    def test_initial_build_publishes_permission_then_revokes_on_readiness(self):
        record = self.request()
        self.assertEqual(self.raised, [])
        # Native construction callbacks capture the record, not controller locals.
        self.pending[0].pop('Registry', None)
        self.complete()
        self.assertEqual(self.raised, [('CEInitialBuildReady', record.Hub)])
        snapshot = self.run.env['player'].entity.ce_hub_statuses[1]
        self.assertEqual(snapshot[17], 5_000_000_000)
        self.assertTrue(snapshot[19])
        self.assertFalse(record.Operational)
        self.assertFalse(record.TestUpgrade)
        self.finish(record)
        self.assertTrue(record.Operational)
        self.assertIs(record.DebugInitialHub, NIL)
        self.run.library('PublishDiagnostics')
        self.assertFalse(record.Snapshot[19])
        record.Target = 2
        self.run.library('QueueExpansion')
        self.complete(index=1)
        self.assertEqual(len(self.raised), 1)

    def test_layout_failure_and_reload_preserve_exact_permission(self):
        record = self.request(); hub = record.Hub
        self.complete(success=False)
        self.assertIs(record.DebugInitialHub, hub)
        self.run.native['cancel_cue'] = lambda n:None
        self.run.actions(self.run.tree.xpath('//cue[@name="Reload"]/actions')[0])
        self.assertIs(record.DebugInitialHub, hub)
        self.assertEqual(record.Population, 5_000_000_000)
        # Placement cooldown is part of the real retry path.
        self.run.env['player'].age += 3600
        self.run.library('Reconcile')
        self.complete(index=len(self.pending)-1)
        self.assertIn(('CEInitialBuildReady', hub), self.raised)

    def test_permission_cannot_complete_reowned_or_replaced_hub(self):
        record = self.request()
        record.Hub.owner = 'player'
        self.run.library('md.CE_DebugCreate.Tick')
        self.assertIs(record.DebugInitialHub, NIL)
        record.Hub.owner = 'ownerless'
        self.complete()
        self.assertEqual(self.raised, [])
        record.DebugInitialHub = Component(exists=True)
        self.run.library('md.CE_DebugCreate.Tick')
        self.assertIs(record.DebugInitialHub, NIL)

    def test_destroyed_debug_hub_replaced_without_native_response_or_completion_permission(self):
        record = self.request(); profile = record.DebugProfile
        record.Hub.exists = False
        self.run.library('ForgetHub')
        record.Level = 3; record.GrowthSeconds = 42
        self.run.library('Reconcile')
        self.assertEqual(len(self.hubs), 2)
        self.assertEqual((record.Level, record.GrowthSeconds, record.Population), (3, 42, 5_000_000_000))
        self.assertIs(record.DebugProfile, profile)
        self.assertIs(record.DebugInitialHub, NIL)
        self.complete(index=1)
        self.assertFalse(any(event == 'CEInitialBuildReady' for event,_ in self.raised))

    def test_explicit_creation_in_retained_record_preserves_earned_level(self):
        record = self.start()
        record.Hub.exists = False
        self.run.library('ForgetHub')
        record.Level = 4; record.GrowthSeconds = 123
        self.request()
        self.assertEqual((record.Level, record.GrowthSeconds), (4, 123))
        self.assertIs(record.DebugInitialHub, record.Hub)

    def test_stale_diagnostics_cannot_authorize_completion(self):
        record = self.request(); self.complete()
        self.assertTrue(record.Snapshot[19])
        record.DisplayOrder.append(record.DisplayOrder[1])
        self.run.library('PublishDiagnostics')
        self.assertTrue(record.Snapshot[15])
        self.assertEqual(record.Snapshot[17], 5_000_000_000)
        self.assertFalse(record.Snapshot[19])
