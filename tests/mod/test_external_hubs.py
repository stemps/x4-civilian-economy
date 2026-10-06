"""Designated (external) hubs: registration, adoption and lifecycle with native effects mocked."""
from support import Table, List, NIL, Component
from support_construction import sequence
from support_startup import StartupHarness


class ExternalHubTests(StartupHarness):
    def setUp(self):
        super().setUp()
        r = self.run
        r.env['md'].CE_CivilianHub.Init.Registry = r.env['Registry']
        self.listener = Component(exists=True)
        self.received = []; self.changed = 0; self.god = {}
        self.renamed = []
        r.native.update(signal_cue_instantly=self.signal, find_station=self.find_station,
                        cancel_cue=lambda n: None,
                        set_object_name=lambda n: self.renamed.append(r.expr(n.get('object'))))

    # Native stand-ins -----------------------------------------------------
    def signal(self, n):
        cue = n.get('cue')
        if cue.startswith('$'):
            self.received.append((self.run.expr(cue), self.run.expr(n.get('param'))))
        elif cue == 'md.CE_CivilianHub.ExternalHubsChanged':
            self.changed += 1
        else:
            self.generate(n)

    def find_station(self, n):
        self.assertEqual(n.get('space'), 'player.galaxy')
        found = self.god.get(self.run.expr(n.get('godstationentry')))
        self.run.set(n.get('name'), List([found] if found else []))

    def station(self, owner='civilian', modules=3, entry='sample_hub'):
        plan = sequence(['dockarea'] * modules)
        hub = Component(exists=True, iswreck=False, isoperational=True, owner=owner, sector=self.sector,
                        isclass=Table(container=True), money=0, buildstorage=NIL, tradenpc=Component(exists=True),
                        constructionsequence=plan, hasrelation=Table(dock=Table()),
                        planmodule=Table({e.id: Component(exists=True, isoperational=True) for e in plan}))
        if entry: self.god[entry] = hub
        return hub

    # Helpers --------------------------------------------------------------
    def register(self, **fields):
        params = dict(version=1, godentry='sample_hub', population=1_000_000_000, listener=self.listener)
        params.update(fields)
        self.run.env['ExternalInput'] = Table({k: v for k, v in params.items() if v is not None})
        self.run.library('md.CE_ExternalHubs.Store')
        return self.run.env['ExternalValid']

    def reconcile(self):
        self.run.env['player'].age += 300
        self.run.library('Reconcile')

    def tick(self, record):
        self.run.env.update(R=record, Sector=self.sector)
        self.run.library('UpdateHub')

    def notices(self, kind=None):
        return [p for cue, p in self.received if cue is self.listener and (kind is None or p.event == kind)]

    def adopt(self, **fields):
        hub = self.station()
        self.assertTrue(self.register(**fields))
        self.reconcile()
        return hub, self.run.env['Registry'][self.sector]

    def assert_no_construction(self, hub):
        self.assertEqual(self.hubs, [], 'CE must never create a station for a designated sector')
        self.assertFalse(any(kind in ('queue', 'process', 'assign', 'materialize') for kind, _ in self.events))
        self.assertEqual(self.native_requests, [])
        self.assertIs(hub.buildstorage, NIL)
        self.assertEqual(self.pending, [])
        self.assertNotIn(hub, self.renamed)

    # Tests ----------------------------------------------------------------
    def test_registration_before_init_adopts_operational_hub_without_construction(self):
        hub, record = self.adopt()
        self.assertTrue(record.External)
        self.assertIs(record.Hub, hub)
        self.assertEqual((record.Level, record.Population), (1, 1_000_000_000))
        self.assertTrue(record.Operational)
        self.assertEqual(record.PauseReason, 'active')
        self.assertIs(record.InitialHub, NIL)
        self.assert_no_construction(hub)
        self.assertEqual([e.event for e in self.notices()], ['adopted', 'status'])
        adopted = self.notices('adopted')[0]
        self.assertEqual((adopted.godentry, adopted.station, adopted.sector, adopted.level), ('sample_hub', hub, self.sector, 1))
        self.assertTrue(self.notices('status')[0].operational)
        # Native 'init station' is not re-sent to a station its own mod initialized.
        self.assertFalse(any(kind == 'operational' for kind, _ in self.events))
        entity = self.run.env['player'].entity
        self.assertIn(hub, entity.ce_hubs)
        self.assertNotIn(hub, entity.ce_builder_hubs)
        self.assertEqual(record.Snapshot[24], [1, 10])
        self.assertEqual(record.Snapshot[22], '')

    def test_native_zero_population_keeps_registration_population(self):
        hub, record = self.adopt()
        self.run.env.update(Sector=self.sector, Population=0)
        self.run.library('md.CE_PopulationOverrides.RememberNative')
        self.run.library('ReconcileSector')
        self.assertEqual(record.Population, 1_000_000_000)
        self.assert_no_construction(hub)

    def test_repeated_reconcile_and_registration_are_idempotent(self):
        hub, record = self.adopt()
        level, generation = record.Level, record.Generation
        self.reconcile(); self.reconcile()
        self.assertTrue(self.register())
        self.reconcile()
        self.assertEqual(len(self.notices('adopted')), 1)
        self.assertEqual((record.Level, record.Generation), (level, generation))
        self.assertEqual(len(self.run.env['md'].CE_ExternalHubs.State.Registrations), 1)
        self.assert_no_construction(hub)

    def test_invalid_registrations_are_rejected_without_state(self):
        for fields in (dict(version=2), dict(godentry=None), dict(population=-1),
                       dict(maxlevel=11), dict(race='nosuchrace'), dict(station=Component(exists=True))):
            self.assertFalse(self.register(**fields))
        self.assertEqual(len(self.run.env['md'].CE_ExternalHubs.State.Registrations), 0)
        self.assertEqual({e.reason for e in self.notices('rejected')}, {'invalid'})
        self.run.env['ExternalInput'] = 'not a table'
        self.run.library('md.CE_ExternalHubs.Store')
        self.assertFalse(self.run.env['ExternalValid'])

    def test_wrong_owner_and_missing_station_reject_once_and_retry(self):
        self.assertTrue(self.register())
        self.reconcile(); self.reconcile()
        self.assertEqual([e.reason for e in self.notices('rejected')], ['not_found'])
        hub = self.station(owner='argon')
        self.reconcile(); self.reconcile()
        self.assertEqual([e.reason for e in self.notices('rejected')], ['not_found', 'owner'])
        self.assertNotIn(self.sector, self.run.env['Registry'])
        hub.owner = 'civilian'
        self.reconcile()
        self.assertTrue(self.run.env['Registry'][self.sector].External)
        self.assertEqual(len(self.notices('adopted')), 1)
        self.assertEqual(self.hubs, [])

    def test_sector_with_ce_hub_refuses_registration(self):
        built = self.start()
        self.assertEqual(len(self.hubs), 1)
        self.station()
        self.assertTrue(self.register())
        self.reconcile()
        self.assertEqual([e.reason for e in self.notices('rejected')], ['sector_has_hub'])
        self.assertIs(self.run.env['Registry'][self.sector], built)
        self.assertFalse(built.External)

    def test_level_commits_without_construction_and_honours_max_level(self):
        hub, record = self.adopt(maxlevel=2)
        rates = {w: s.Rate for w, s in record.Wares.items()}
        record.GrowthSeconds = 1e9
        self.tick(record)
        self.assertEqual((record.Level, record.Target, record.GrowthSeconds), (2, 0, 0.0))
        self.assertEqual([(e.oldlevel, e.newlevel) for e in self.notices('level')], [(1, 2)])
        self.assertGreater(sum(s.Rate for s in record.Wares.values()), sum(rates.values()))
        record.GrowthSeconds = 1e9
        self.tick(record)
        self.assertEqual(record.Level, 2)
        self.assertFalse(record.Qualified)
        self.assertEqual(len(self.notices('level')), 1)
        self.assert_no_construction(hub)
        self.assertEqual(record.Snapshot[24], [1, 2])

    def test_damage_pauses_and_announces_status_changes_once(self):
        hub, record = self.adopt()
        hub.planmodule['1'].isoperational = False
        hub.planmodule['1'].iswreck = True
        self.tick(record); self.tick(record)
        status = self.notices('status')
        self.assertEqual([(e.operational, e.reason) for e in status], [(True, 'active'), (False, 'damaged_modules')])
        hub.planmodule['1'].isoperational = True
        hub.planmodule['1'].iswreck = False
        self.tick(record)
        self.assertEqual(self.notices('status')[-1].reason, 'active')

    def test_construction_entry_points_refuse_designated_hubs(self):
        # Defense in depth: no CE path may construct on, fund or staff a designated station.
        hub = self.station(); hub.constructionsequence = NIL
        self.assertTrue(self.register())
        self.reconcile()
        record = self.run.env['Registry'][self.sector]
        record.Target = 2
        self.run.env.update(R=record, Sector=self.sector, Hub=hub)
        self.run.library('QueueExpansion')
        self.assertEqual(self.pending, [])
        self.assertIs(hub.buildstorage, NIL)
        # The station's own mod queued a build: CE neither assigns builders nor pays for it.
        hub.buildstorage = Component(exists=True, isoperational=True, money=0, wantedmoney=900,
                                     builds=Table(queued=List([Component(exists=True)]), inprogress=List()),
                                     buildmodule=Component(exists=True, constructionvessel=NIL))
        self.allow(self.builder(), hub)
        self.run.env.update(R=record, Sector=self.sector, Hub=hub)
        for name in ('AssignBuilder', 'FundAccounts', 'RenameHub'):
            self.run.library(name)
        self.assertFalse(any(kind in ('queue', 'assign', 'order') for kind, _ in self.events))
        self.assertEqual(hub.buildstorage.money, 0)
        self.assertNotIn(hub, self.renamed)

    def test_modules_added_later_do_not_affect_readiness(self):
        hub, record = self.adopt()
        extended = sequence(['dockarea'] * 5)
        hub.constructionsequence = extended
        hub.planmodule['3'] = Component(exists=True, isoperational=False, isconstruction=True)
        self.tick(record)
        self.assertTrue(record.Operational)

    def test_station_without_sequence_uses_station_operational_state(self):
        hub = self.station(); hub.constructionsequence = NIL
        self.assertTrue(self.register())
        self.reconcile()
        record = self.run.env['Registry'][self.sector]
        self.assertTrue(record.Operational)
        self.reconcile()
        self.assert_no_construction(hub)
        hub.isoperational = False
        self.tick(record)
        self.assertEqual(record.PauseReason, 'modules_unavailable')

    def test_loss_goes_dormant_then_readopts_respawned_station(self):
        hub, record = self.adopt()
        record.Level = 4; record.GrowthSeconds = 77
        hub.exists = False
        self.run.env['event'] = Table(object=hub)
        self.run.actions(self.run.tree.xpath('//cue[@name="LostHub"]/actions')[0])
        self.assertEqual([e.station for e in self.notices('lost')], [hub])
        self.assertIs(record.Hub, NIL)
        # In game a minute tick followed 'lost' with a redundant hub_unavailable status.
        statuses = len(self.notices('status'))
        self.tick(record)
        self.assertEqual(len(self.notices('status')), statuses)
        self.god.clear()
        self.reconcile()
        self.assertEqual(self.hubs, [])
        self.assertEqual(self.notices('rejected'), [])
        respawned = self.station()
        self.reconcile()
        self.assertIs(record.Hub, respawned)
        self.assertEqual((record.Level, record.GrowthSeconds), (4, 77))
        self.assertEqual(len(self.notices('adopted')), 2)
        self.assertEqual(self.notices('status')[-1].reason, 'active')
        self.assert_no_construction(respawned)

    def test_dead_listener_is_skipped(self):
        self.listener.exists = False
        hub, record = self.adopt()
        self.assertEqual(self.received, [])
        self.assertTrue(record.Operational)

    def test_debug_create_refuses_dormant_designated_sector(self):
        hub, record = self.adopt()
        hub.exists = False
        self.run.env.update(R=record, Sector=self.sector)
        self.run.library('ForgetHub')
        self.run.native['write_to_logbook'] = lambda n: None
        self.run.env['event'] = Table(param3=self.sector)
        self.run.library('md.CE_DebugCreate.Request')
        self.assertEqual(self.run.env['DebugFailure'], 135)
        self.assertEqual(self.hubs, [])

    def test_debug_advance_commits_requested_level_directly(self):
        hub, record = self.adopt(maxlevel=6)
        self.run.env.update(R=record, Sector=self.sector, event=Table(param2='advance_level_7'))
        self.run.library('md.CE_DebugAdvance.Request')
        self.assertEqual(record.Level, 1)
        self.run.env['event'] = Table(param2='advance_level_5')
        self.run.library('md.CE_DebugAdvance.Request')
        self.assertEqual((record.Level, record.Target), (5, 0))
        self.assertEqual([(e.oldlevel, e.newlevel) for e in self.notices('level')], [(1, 5)])
        self.assert_no_construction(hub)

    def test_debug_queue_upgrade_is_ignored(self):
        hub, record = self.adopt()
        self.run.env['event'] = Table(param2='queue_upgrade', param3=hub)
        self.run.actions(self.run.tree.xpath('//cue[@name="TestingCommand"]/actions')[0])
        self.assertEqual((record.Level, record.Target), (1, 0))
        self.assert_no_construction(hub)

    def test_pinned_race_replaces_sector_owner_race_before_first_freeze(self):
        hub, record = self.adopt(race='teladi')
        self.assertEqual(self.sector.owner.primaryrace.id, 'argon')
        self.assertEqual(record.ProfileRace, 'teladi')

    def test_registration_signals_controller_once_initialized(self):
        self.station()
        self.run.env['md'].CE_ExternalHubs.Register.update()
        self.run.env['event'] = Table(param=Table(version=1, godentry='sample_hub'))
        self.run.actions(self.run.scripts['CE_ExternalHubs'].xpath('//cue[@name="Register"]/actions')[0])
        self.assertEqual(self.changed, 1)
        self.run.env['event'] = Table(param=Table(version=3))
        self.run.actions(self.run.scripts['CE_ExternalHubs'].xpath('//cue[@name="Register"]/actions')[0])
        self.assertEqual(self.changed, 1)

    def test_raid_tier_fits_free_external_berths(self):
        hub, record = self.adopt()
        docks = {}
        def find(n):
            size = self.run.expr(n.find('match_dock').get('size'))
            self.run.set(n.get('name'), List([Component(exists=True)] * docks.get(size, 0)))
        self.run.native['find_dockingbay'] = find
        self.run.env['tag'].update(dock_l='dock_l')
        for counts, tier, expected in (({'dock_m': 2, 'dock_s': 4, 'dock_l': 1}, 3, 3),
                                       ({'dock_m': 2, 'dock_s': 4}, 3, 2),
                                       ({'dock_m': 1, 'dock_s': 4}, 3, 1),
                                       ({'dock_s': 8}, 2, 0)):
            docks.clear(); docks.update(counts)
            self.run.env.update(R=record, RaidTier=tier)
            self.run.library('md.CE_Raids.FitDocks')
            self.assertEqual(self.run.env['RaidTier'], expected, counts)
