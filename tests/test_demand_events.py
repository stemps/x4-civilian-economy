"""Execute shipped event actions with deterministic random draws and native UI mocks."""
import copy
import unittest
from support import Table, List, Component, Ware, NIL
from support_unrest import UnrestFixture


class DemandEventTests(UnrestFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.r.update(Level=1, Definitions=List(), DisplayOrder=List(), Factor=1,
                      Transfers=Table(), PlotReady=True, TestUpgrade=False)
        self.run.env.update(Sector=self.sector, readtext=Table({974201:Table({i:str(i) for i in range(321,332)})}))
        self.run.env['md'].CE_OwnerlessHub.Init.Registry = Table({self.sector:self.r})
        self.run.env['md'].CE_Settings.State.Debug = True
        self.run.env['event'] = Table(param3=self.hub)
        self.offers=[]
        self.run.stubs['md.CE_OwnerlessHub.UpdateOffers']=lambda:self.offers.append(True)
        self.run.stubs['md.CE_Diagnostics.PublishAllDiagnostics']=lambda:None
        self.run.env['player'].entity=Table()
        self.run.library('md.CE_DemandEvents.Ensure')

    def add_good(self, name, category=1, group='food', level=1, reserve=10000, rate=100):
        ware=Ware(name)
        ware.group=Table(id=group)
        self.r.Definitions.append(List([ware,level,float(rate)]))
        self.r.Categories[ware]=category
        self.run.library('md.CE_Demand.ApplyLevel')
        if ware in self.r.Wares:self.r.Wares[ware].Reserve=reserve
        return ware

    def candidates(self):
        self.run.library('md.CE_DemandEvents.Candidates')
        return {i:set(wares) for i,wares in enumerate(self.run.env['DELists'],1)}

    def start(self, event_id):
        self.run.library('md.CE_Reserves.Accrue')
        self.candidates()
        self.run.env['DEChosen']=event_id
        self.run.library('md.CE_DemandEvents.Start')

    def debug(self, event_id, token=None):
        token=self.r.DemandEvent.Token if token is None else token
        self.run.env['event'].param2=f'{event_id}:{token}'
        self.run.actions(self.run.scripts['CE_DebugEvents'].xpath('//cue[@name="Request"]/actions')[0])

    def test_all_eleven_mappings_and_omitted_goods(self):
        self.add_good('foodrations')
        self.add_good('sojahusk',3)
        self.add_good('water',1,'water')
        self.add_good('medicalsupplies',1,'pharmaceutical')
        self.add_good('energycells',1,'energy')
        for name in ('spacefuel','spaceweed','majadust','stimulants'):self.add_good(name,3,'drug')
        for name in ('microchips','advancedelectronics','computronicsubstrate'):self.add_good(name,2,'tech')
        materials={'refinedmetals','siliconwafers','advancedcomposites','metallicmicrolattice','siliconcarbide'}
        for name in materials:self.add_good(name,2,'material')
        self.add_good('scanningarrays',2,'tech')
        self.add_good('lockedfood',3,level=8)
        rows=self.candidates()
        self.assertEqual(rows[1],{'foodrations'})
        self.assertEqual(rows[2],rows[1])
        self.assertEqual(rows[3],{'water'})
        self.assertEqual(rows[4],{'sojahusk','spacefuel','spaceweed','majadust','stimulants'})
        self.assertEqual(rows[5],{'microchips','advancedelectronics','computronicsubstrate'})
        self.assertEqual(rows[6],{'medicalsupplies'})
        self.assertEqual(rows[7],{'energycells'})
        self.assertEqual(rows[8],materials)
        self.assertEqual(rows[9],materials)
        self.assertEqual(rows[10],{'spacefuel','spaceweed','majadust','stimulants'})
        self.assertEqual(rows[11],rows[10])
        self.assertEqual(list(self.run.env['DECandidates']),list(range(1,12)))

    def test_strength_bounds_and_every_event_uses_its_own_basket(self):
        goods=[('food',1,'food'),('water',1,'water'),('exotic',3,'food'),('microchips',2,'tech'),
               ('medicine',1,'pharmaceutical'),('energycells',1,'energy'),('refinedmetals',2,'material'),('spacefuel',3,'drug')]
        for name,cat,group in goods:self.add_good(name,cat,group)
        for fraction in (0,1):
            self.run.random_fraction=fraction
            for event_id in range(1,12):
                selected=self.candidates()[event_id]
                self.start(event_id)
                percent=(-(25+25*fraction) if event_id in (2,9,10) else 25+75*fraction)
                self.assertEqual(self.r.DemandEvent.Percent,percent)
                self.assertEqual(self.r.DemandEvent.End,7200)
                for ware,w in self.r.Wares.items():
                    self.assertAlmostEqual(w.Rate,100+percent if ware in selected else 100)

    def test_initial_delay_save_copy_and_independent_sectors(self):
        self.assertEqual(self.r.DemandEvent.Next,16200)
        saved=copy.copy(self.r.DemandEvent)
        self.run.env['player'].age=500
        self.run.library('md.CE_DemandEvents.Ensure')
        self.assertEqual(self.r.DemandEvent,saved)
        original=self.r.DemandEvent
        other=Table(self.r);other.pop('DemandEvent')
        self.run.env['R']=other
        self.run.random_fraction=1
        self.run.library('md.CE_DemandEvents.Ensure')
        self.assertEqual(other.DemandEvent.Next,22100)
        self.assertIsNot(other.DemandEvent,original)
        self.assertEqual(original.Next,16200)

    def test_scheduler_waits_requires_applicability_and_never_overlaps(self):
        self.r.DemandEvent.Next=0
        self.run.library('md.CE_DemandEvents.Tick')
        self.assertEqual(self.r.DemandEvent.ID,0)
        self.add_good('water',1,'water')
        self.hub.owner='player'
        self.run.library('md.CE_DemandEvents.Tick')
        self.assertEqual(self.r.DemandEvent.ID,0)
        self.hub.owner='civilian'
        self.r.Operational=False
        self.run.library('md.CE_DemandEvents.Tick')
        self.assertEqual(self.r.DemandEvent.ID,0)
        self.r.Operational=True
        self.run.library('md.CE_DemandEvents.Tick')
        self.assertEqual(self.r.DemandEvent.ID,3)
        saved=copy.copy(self.r.DemandEvent)
        self.run.library('md.CE_DemandEvents.Tick')
        self.assertEqual(self.r.DemandEvent,saved)
        self.assertEqual(len(self.messages),2)

    def test_expiry_splits_consumption_and_does_not_drop_surplus(self):
        ware=self.add_good('food',reserve=1000)
        self.run.random_fraction=1
        self.start(1)
        self.advance(9000)
        self.assertEqual(self.r.Wares[ware].Reserve,550)  # 2h*200 + 0.5h*100
        self.assertEqual(self.r.Wares[ware].Rate,100)
        self.assertEqual(self.r.Wares[ware].Cap,200)
        self.assertEqual(self.r.GrowthSeconds,7200)  # level-one growth cap
        self.assertEqual(self.r.Last,9000)
        self.assertEqual(self.r.DemandEvent.ID,0)
        self.assertEqual(len(self.messages),4)
        self.advance(60)
        self.assertEqual(len(self.messages),4)

    def test_unrest_and_growth_split_at_the_same_boundary(self):
        ware=self.add_good('food',reserve=4400,rate=1000)
        self.r.Level=5
        # Keep definition's unlock at the current level so baseline is exactly 1000/h.
        self.r.Definitions[1][2]=5
        self.run.library('md.CE_Demand.ApplyLevel')
        self.ready()
        self.run.random_fraction=1
        self.start(1)
        self.advance(9000)
        self.assertEqual(self.r.Wares[ware].Reserve,0)
        self.assertEqual(self.r.GrowthSeconds,8640)  # 2 supplied hours + 24 minutes
        self.assertAlmostEqual(self.u.Score,2.5)  # only six minutes without staple food

    def test_population_level_and_setting_recalculation_never_compounds(self):
        ware=self.add_good('food')
        locked=self.add_good('newfood',level=2)
        self.run.random_fraction=1
        self.start(1)
        self.r.Factor=2
        self.r.Level=2
        self.run.env['md'].CE_Settings.State.DemandMultiplier=3
        for _ in range(2):self.run.library('md.CE_Demand.ApplyLevel')
        self.assertEqual(self.r.Wares[ware].Rate,1500)
        self.assertEqual(self.r.Wares[locked].Rate,600)  # not in the frozen event basket
        self.run.library('md.CE_DemandEvents.End')
        self.assertEqual(self.r.Wares[ware].Rate,750)

    def test_debug_replacement_end_and_replay_guards(self):
        self.add_good('food')
        self.debug(1)
        first_end=self.r.DemandEvent.End
        token=self.r.DemandEvent.Token
        self.advance(600)
        self.debug(2)
        self.assertEqual(self.r.DemandEvent.ID,2)
        self.assertEqual(self.r.DemandEvent.End,first_end+600)
        self.assertEqual(len(self.messages),6)  # start, replacement end, replacement start
        self.debug(1,token)
        self.assertEqual(self.r.DemandEvent.ID,2)
        self.debug(0)
        self.assertEqual(self.r.DemandEvent.ID,0)
        self.assertEqual(self.r.DemandEvent.Next,600+16200)
        self.assertEqual(len(self.messages),8)

    def test_debug_rejects_unavailable_captured_wrong_disabled_and_stale(self):
        self.add_good('food')
        self.debug(5)
        self.assertEqual(self.r.DemandEvent.ID,0)
        self.hub.owner='player';self.debug(1)
        self.hub.owner='civilian'
        self.run.env['event'].param3=Component();self.debug(1)
        self.run.env['event'].param3=self.hub
        self.run.env['md'].CE_Settings.State.Debug=False;self.debug(1)
        self.run.env['md'].CE_Settings.State.Debug=True
        self.debug(1,999)
        self.r.Operational=False;self.debug(1)
        self.r.Operational=True;self.r.SnapshotError=True;self.debug(1)
        self.assertEqual(self.r.DemandEvent.ID,0)
        self.assertEqual(self.messages,[])

    def test_nonoperational_expiry_and_replacement_keep_sector_state(self):
        self.add_good('food')
        self.start(1)
        self.r.Hub=NIL;self.r.Operational=False
        self.advance(3600)
        self.assertEqual(self.r.DemandEvent.ID,1)
        self.r.Hub=Component(exists=True,iswreck=False,owner='civilian',sector=self.sector)
        self.r.Operational=True
        self.advance(3600)
        self.assertEqual(self.r.DemandEvent.ID,0)
        self.assertEqual(self.messages[-1][1][1],335)

    def test_snapshot_and_save_reload_retain_deadline_without_reannouncement(self):
        self.add_good('food')
        self.start(1)
        self.run.env['R']=self.r=copy.deepcopy(self.r)
        self.run.env['player'].age=1200
        self.run.library('md.CE_DemandEvents.Ensure')
        self.run.library('md.CE_Demand.ApplyLevel')
        self.run.library('md.CE_Diagnostics.PublishDiagnostics')
        event=self.r.Snapshot[21]
        self.assertEqual(event[1],1)
        self.assertEqual(event[3],6000)
        self.assertEqual(list(event[5]),[1,2])
        self.assertEqual(len(self.messages),2)

    def test_delivery_after_expiry_preserves_trade_and_accounts_only_received_stock(self):
        ware=self.add_good('food',reserve=1000)
        self.run.random_fraction=1
        self.start(1)
        w=self.r.Wares[ware]
        offer=Component(exists=True,amount=0,offeramount=0)
        w.Offer=offer
        deal=Component(transferredamount=70,unitprice=1000)
        other=Component(exists=True)
        self.r.Transfers[deal]=ware
        self.r.Transfers[other]=ware
        self.sector.isplayerowned=False
        self.run.stubs['md.CE_TransactionLog.WatchPayment']=lambda:None
        self.run.env['event'].param=deal
        self.run.env['player'].age=9000
        self.run.library('md.CE_Trade.RecordDelivery')
        self.assertIs(self.r.Wares[ware],w)
        self.assertIs(w.Offer,offer)
        self.assertIn(other,self.r.Transfers)
        self.assertNotIn(deal,self.r.Transfers)
        self.assertEqual(w.Reserve,620)
        self.assertEqual(w.Delivered,70)
        self.assertEqual(w.Paid,70000)
        self.assertEqual(self.r.DemandEvent.ID,0)

    def test_stale_snapshot_keeps_event_and_unrest_without_debug_authorization(self):
        self.add_good('food')
        self.start(1)
        self.run.library('md.CE_Diagnostics.PublishDiagnostics')
        before=self.r.Snapshot
        self.r.DisplayOrder=List()
        self.run.library('md.CE_Diagnostics.PublishDiagnostics')
        self.assertTrue(self.r.Snapshot[15])
        self.assertEqual(self.r.Snapshot[20],before[20])
        self.assertEqual(self.r.Snapshot[21],before[21])

    def test_real_reload_does_not_rebase_accrual_or_repeat_start(self):
        self.add_good('food')
        self.start(1)
        deadline=self.r.DemandEvent.End
        self.run.env.update(Registry=Table({self.sector:self.r}))
        self.run.stubs.update(Reconcile=lambda:None,RenameHub=lambda:None)
        self.run.env['player'].age=1200
        self.run.actions(self.run.tree.xpath('//cue[@name="Reload"]/actions')[0])
        self.assertEqual(self.r.Last,0)
        self.assertEqual(self.r.DemandEvent.End,deadline)
        self.assertEqual(len(self.messages),2)

    def test_expiry_while_hub_absent_and_boundary_with_rebased_clock(self):
        self.add_good('food')
        self.start(1)
        self.r.Hub=NIL;self.r.Operational=False
        self.run.env['player'].age=7300
        self.run.library('md.CE_Reserves.Rebase')
        self.run.library('md.CE_DemandEvents.Tick')
        self.assertEqual(self.r.Last,7300)
        self.assertEqual(self.r.DemandEvent.ID,0)
        self.assertEqual(len(self.messages),4)

    def test_old_frozen_profile_categories_are_classified_without_replacing_definitions(self):
        food=self.add_good('food')
        self.add_good('water',1,'water')
        self.r.pop('Categories')
        self.r.ProfileRace='test'
        race=Table(id='test',workforce=Table(resources=List([food])))
        self.run.env['lookup']=Table(race=Table(list=List([race])))
        definitions=self.r.Definitions
        rows=self.candidates()
        self.assertEqual(rows[1],{'food'})
        self.assertEqual(rows[3],{'water'})
        self.assertIs(self.r.Definitions,definitions)


if __name__ == '__main__':
    unittest.main()
