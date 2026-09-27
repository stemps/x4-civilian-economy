"""Multi-sector state and scaling checks executing shipped MD libraries."""
import copy, math
from support import Runner, Table, List, NIL, definitions, Ware
import unittest

from support import Object

class GalaxyTests(unittest.TestCase):
    def setUp(self):
        self.run=Runner();definitions(self.run)
        self.registry=Table();self.created=[]
        self.run.env.update(Registry=self.registry,PlanIDs=List(['plan'+str(i) for i in range(10)]),
            faction=Table(ownerless='ownerless',civilian='civilian'))
        self.run.env['player']['entity']=Table()
        for name in ('FundAccounts','QueueExpansion','AssignBuilder','RenameHub','ReserveGrowthPlot'):
            self.run.stubs[name]=lambda:None
        self.run.native['add_to_group']=lambda n:None
        def create(n):
            hub=Object(exists=True,iswreck=False,owner=self.run.expr(n.get('owner')),sector=self.run.env['Sector'],
                       isclass=Table(container=False),buildstorage=NIL)
            self.created.append(hub);self.run.env['NewHub']=hub
        self.run.native['create_station']=create
    def sector(self):return Object(exists=True,isclass=Table(sector=True),owner=Table(primaryrace=self.run.env["lookup"].race.list[1]))
    def reconcile(self,sector,pop):
        self.run.env.update(Sector=sector,Population=pop)
        self.run.library('ReconcileSector')
        return self.registry[sector]
    def test_hostile_sector_blocks_creation_until_liberated(self):
        sector=self.sector()
        sector.owner.hasrelation=Table(enemy=Table(civilian=True))
        record=self.reconcile(sector,100000000)
        self.assertFalse(record.Hub.exists)
        self.reconcile(sector,100000000)
        self.assertEqual(len(self.created),0)
        sector.owner.hasrelation.enemy.civilian=False
        self.reconcile(sector,100000000)
        self.assertEqual(record.Hub.owner,'civilian')
        self.assertEqual(len(self.created),1)

    def test_unowned_sector_can_spawn_with_valid_profile(self):
        sector=self.sector()
        self.run.env['Sector']=sector
        self.run.library('CaptureSectorProfile')
        sector.owner=NIL
        self.assertTrue(self.reconcile(sector,100000000).Hub.exists)

    def test_conquest_keeps_hub_but_blocks_replacement(self):
        sector=self.sector();record=self.reconcile(sector,100000000)
        hub=record.Hub;record.Level=3;record.GrowthSeconds=42
        sector.owner.hasrelation=Table(enemy=Table(civilian=True))
        self.reconcile(sector,100000000)
        self.assertIs(record.Hub,hub)
        hub.iswreck=True
        self.reconcile(sector,100000000)
        self.assertFalse(record.Hub.exists)
        self.assertEqual(len(self.created),1)
        sector.owner.hasrelation.enemy.civilian=False
        self.reconcile(sector,100000000)
        self.assertEqual(len(self.created),2)
        self.assertEqual((record.Level,record.GrowthSeconds),(3,42))

    def test_legacy_migration_preserves_objects_and_state(self):
        sector=self.sector();record=self.reconcile(sector,100000000)
        hub=record.Hub;hub.owner='ownerless'
        hub.tradenpc=Object(exists=True,owner='ownerless')
        manager=Object(exists=True,owner='ownerless')
        build=Object(exists=True)
        storage=Object(exists=True,owner='ownerless',tradenpc=manager,money=123,
                       builds=Table(inprogress=List([build])))
        hub.buildstorage=storage;record.Build=build;record.Target=2
        record.Wares['water'].Reserve=37;record.GrowthSeconds=99
        record.DemandEvent=Table(ID=3);event=record.DemandEvent
        changes=[]
        def change(n):
            obj=self.run.expr(n.get('object'))
            changes.append(obj);obj.owner=self.run.expr(n.get('faction'))
        self.run.native['set_owner']=change
        self.run.env['R']=record
        self.run.library('MigrateHubOwnership')
        self.assertEqual(len(changes),4)
        self.run.library('MigrateHubOwnership')
        self.assertEqual(len(changes),4)
        self.assertIs(record.Hub,hub);self.assertIs(hub.buildstorage,storage)
        self.assertIs(record.Build,build);self.assertIs(record.DemandEvent,event)
        self.assertEqual((record.Target,record.GrowthSeconds,record.Wares['water'].Reserve),(2,99,37))
        self.assertEqual(storage.money,123)
        self.assertTrue(all(obj.owner=='civilian' for obj in changes))

    def test_migration_skips_wrecks_and_other_owners(self):
        record=self.reconcile(self.sector(),100000000)
        self.run.env['R']=record
        self.run.native['set_owner']=lambda n:self.fail('Unexpected ownership transfer')
        for owner,wreck in [('player',False),('argon',False),('ownerless',True)]:
            record.Hub.owner=owner;record.Hub.iswreck=wreck
            self.run.library('MigrateHubOwnership')

    def test_reconcile_migrates_only_registered_hubs_before_population_request(self):
        record=self.reconcile(self.sector(),100000000)
        record.Hub.owner='ownerless'
        unrelated=Object(exists=True,owner='ownerless')
        self.run.native['set_owner']=lambda n:setattr(self.run.expr(n.get('object')),'owner',self.run.expr(n.get('faction')))
        self.run.stubs['md.CE_DebugCreate.ReconcileOverrides']=lambda:None
        self.run.native['find_sector']=lambda n:self.run.set(n.get('name'),List())
        self.run.native['raise_lua_event']=lambda n:self.assertEqual(record.Hub.owner,'civilian')
        self.run.env['PopulationRequest']=NIL
        self.run.library('Reconcile')
        self.assertEqual(unrelated.owner,'ownerless')

    def test_sector_reconciliation_repairs_legacy_hub_in_hostile_sector(self):
        sector=self.sector();record=self.reconcile(sector,100000000)
        hub=record.Hub;hub.owner='ownerless'
        sector.owner.hasrelation=Table(enemy=Table(civilian=True))
        self.run.native['set_owner']=lambda n:setattr(self.run.expr(n.get('object')),'owner',self.run.expr(n.get('faction')))
        self.reconcile(sector,100000000)
        self.assertIs(record.Hub,hub)
        self.assertEqual(hub.owner,'civilian')
        self.assertEqual(len(self.created),1)
    def test_population_threshold_is_inclusive_and_creates_once(self):
        a,b,c=self.sector(),self.sector(),self.sector()
        for population in (0,10000,99999999):
            self.reconcile(a,population)
            self.assertEqual(len(self.created),0)
            self.assertNotIn(a,self.registry)
        first=self.reconcile(b,100000000);second=self.reconcile(c,8524100000)
        self.reconcile(b,100000000);self.assertEqual(len(self.created),2)
        self.assertIsNot(first.Hub,second.Hub)
        self.assertGreater(first.Wares['foodrations'].Rate,0)
        self.assertAlmostEqual(first.Wares['foodrations'].Rate,7140*100000000/8524100000)
        self.assertEqual(second.Wares['foodrations'].Rate,7140)
    def test_population_scaling_above_workforce_bonus_ceiling(self):
        r=self.reconcile(self.sector(),18000000000)
        self.assertAlmostEqual(r.Wares['water'].Rate,1420*18000000000/8524100000)
        self.assertAlmostEqual(r.Wares['water'].Cap,math.ceil(r.Wares['water'].Rate*2))
        self.assertEqual(r.Wares['water'].Price,1200)
    def test_live_change_does_not_unlock_pending_level_or_erase_backlog(self):
        s=self.sector();r=self.reconcile(s,8524100000)
        r['Target']=2;r.Wares['foodrations']['Reserve']=12.75
        self.reconcile(s,4262050000)
        self.assertEqual(r.Level,1);self.assertEqual(r.Target,2)
        self.assertNotIn('energycells',r.Wares)
        self.assertEqual(r.Wares['foodrations'].Reserve,12.75)
        self.assertEqual(r.Wares['foodrations'].Rate,3570)
    def test_zero_then_repopulation_retains_existing_hub(self):
        s=self.sector();r=self.reconcile(s,100000000);hub=r.Hub
        self.reconcile(s,0);self.assertIs(r.Hub,hub)
        self.assertEqual(r.Wares['water'].Rate,0)
        self.reconcile(s,100000000);self.assertEqual(len(self.created),1)
    def test_existing_hub_retained_but_replacement_waits_for_threshold(self):
        s=self.sector();r=self.reconcile(s,100000000);hub=r.Hub
        self.reconcile(s,99999999)
        self.assertIs(r.Hub,hub)
        hub['exists']=False
        self.reconcile(s,99999999)
        self.assertEqual(len(self.created),1)
        self.reconcile(s,100000000)
        self.assertEqual(len(self.created),2)
        self.assertIsNot(r.Hub,hub)
    def test_replacement_retains_only_its_own_level_and_backlog(self):
        a,b=self.sector(),self.sector()
        ra=self.reconcile(a,8524100000);rb=self.reconcile(b,8524100000)
        ra['Level']=4;ra['Target']=5;ra.Wares['water']['Reserve']=123.25
        ra.Hub['exists']=False
        rb.Wares['water']['Reserve']=77;bhub=rb.Hub
        self.reconcile(a,8524100000)
        self.assertEqual(len(self.created),3)
        self.assertEqual(ra.Level,4);self.assertEqual(ra.Target,0)
        self.assertEqual(ra.Wares['water'].Reserve,0)
        self.assertIs(rb.Hub,bhub);self.assertEqual(rb.Wares['water'].Reserve,77)
    def test_registry_survives_copy_without_duplicate_sites(self):
        a,b=self.sector(),self.sector();self.reconcile(a,8524100000);self.reconcile(b,100000000)
        self.run.env=copy.deepcopy(self.run.env);self.registry=self.run.env['Registry']
        for sector in self.registry.keys.list:self.reconcile(sector,self.registry[sector].Population)
        self.assertEqual(len(self.created),2)
    def test_ui_snapshot_contains_both_hubs(self):
        a,b=self.sector(),self.sector();ra=self.reconcile(a,100000000);rb=self.reconcile(b,200000000)
        ra['Snapshot']=List([ra.Hub,1]);rb['Snapshot']=List([rb.Hub,2])
        self.run.library('PublishAllDiagnostics')
        self.assertEqual(len(self.run.env['player'].entity.ce_hubs),2)
        self.assertEqual(len(self.run.env['player'].entity.ce_hub_statuses),2)
    def test_watcher_binds_sector_record_in_own_namespace(self):
        watch=self.run.tree.xpath('//cue[@name="WatchSectorHub"]')[0]
        self.assertEqual(watch.get('namespace'),'this')
        self.assertEqual(watch.xpath('./actions/set_value[@name="$R"]/@exact'),['event.param.{2}'])
        self.assertIn('$Registry.keys.list',self.run.tree.xpath('//cue[@name="TestingCommand"]/actions/do_for_each/@in'))
    def test_deliveries_are_isolated_and_completion_guard_is_consumed(self):
        ra=self.reconcile(self.sector(),8524100000)
        rb=self.reconcile(self.sector(),8524100000)
        for r in (ra,rb):
            r.Wares['water']['Reserve']=100
        deal=Object(buyer=ra.Hub,transferredamount=15,unitprice=1200)
        ra.Transfers[deal]=Ware('water')
        self.run.env['event']=Table(param=deal)
        guard=self.run.tree.xpath('//cue[@name="SectorDeliveryFinished"]/conditions/check_value[contains(@value,"$Transfers")]/@value')[0]
        self.run.env['R']=rb
        self.assertFalse(self.run.expr(guard))
        self.run.env['R']=ra
        self.assertTrue(self.run.expr(guard))
        self.run.stubs.update(UpdateOffers=lambda:None,PublishDiagnostics=lambda:None,PublishAllDiagnostics=lambda:None)
        self.run.library('RecordDelivery')
        self.assertEqual(ra.Wares['water'].Reserve,115)
        self.assertEqual(ra.Wares['water'].Delivered,15)
        self.assertEqual(ra.Wares['water'].Paid,18000)
        self.assertEqual(rb.Wares['water'].Reserve,100)
        self.assertEqual(rb.Wares['water'].Delivered,0)
        self.assertFalse(self.run.expr(guard))
    def test_first_install_in_existing_universe_initializes_complete_records(self):
        self.run.env['player']['age']=987654.0
        a,b=self.sector(),self.sector()
        ra=self.reconcile(a,8524100000);rb=self.reconcile(b,8524100000)
        self.assertEqual(len(self.created),2)
        for record in (ra,rb):
            self.assertEqual((record.Level,record.Target,record.GrowthSeconds,record.Last),
                             (1,0,0.0,987654.0))
            self.assertEqual(list(record.DisplayOrder),['foodrations','water'])
            self.assertTrue(all(w.Active and w.Reserve == 0 and w.Demand == w.Cap
                                for w in record.Wares.values()))
        ra.GrowthSeconds=120;ra.Wares['water'].Reserve=45
        self.assertIs(self.reconcile(a,8524100000),ra)
        self.assertEqual((ra.GrowthSeconds,ra.Wares['water'].Reserve),(120,45))
        self.assertEqual(len(self.created),2)

    def test_delivery_publishes_wares_without_controller_local_definitions(self):
        r=self.reconcile(self.sector(),8524100000)
        other=self.reconcile(self.sector(),100000000)
        self.run.env['R']=other
        self.run.library('PublishDiagnostics')
        other_snapshot=other.Snapshot
        r['Operational']=True
        r.Wares['water']['Reserve']=100
        deal=Object(buyer=r.Hub,transferredamount=15,unitprice=1200)
        r.Transfers[deal]=Ware('water')
        # Match the watcher's namespace: no local Definitions. Only native offer
        # writes are stubbed; execute the entire delivery-to-blackboard path.
        del self.run.env['Definitions']
        self.run.env.update(R=r,Hub=r.Hub,event=Table(param=deal))
        self.run.stubs['UpdateOffers']=lambda:None
        self.run.library('RecordDelivery')
        rows=r.Snapshot[9]
        self.assertEqual([row[1] for row in rows],['foodrations','water'])
        self.assertEqual(rows[2][2],115)
        self.assertEqual(rows[2][6],15)
        self.assertEqual(rows[2][7],180)
        self.assertEqual(len(self.run.env['player'].entity.ce_hub_statuses),2)
        self.assertIs(other.Snapshot,other_snapshot)
