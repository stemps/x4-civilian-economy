"""Reserve accounting executes the shipped MD, not a duplicate Python model."""
import copy
import unittest
from test_prototype import Runner, Table, List, Ware, NIL
from test_galaxy import Object


class ReserveTests(unittest.TestCase):
    def setUp(self):
        self.run=Runner()
        self.r=Table(Level=1,Target=0,Operational=True,Hub=Object(exists=True,iswreck=False),
                     Wares=Table(),Transfers=Table(),PauseOffers=False,GrowthSeconds=0.0,Last=0.0)
        self.run.env['R']=self.r
        self.food=self.add('food',3600)
        self.water=self.add('water',1800)
        self.run.library('md.CE_Reserves.SyncAll')
        self.run.stubs.update(UpdateOffers=lambda:None,PublishDiagnostics=lambda:None,PublishAllDiagnostics=lambda:None)
        self.guard=self.run.tree.xpath('//cue[@name="SectorDeliveryFinished"]/conditions/check_value[contains(@value,"$Transfers")]/@value')[0]

    def add(self,name,rate):
        state=Table(Active=True,Rate=rate,Reserve=0,Delivered=0,Paid=0,Offer=NIL,Price=1200)
        self.r.Wares[Ware(name)]=state
        return state

    def advance(self,seconds):
        self.run.env['player']['age']+=seconds
        self.run.library('AccrueAll')

    def deliver(self,ware,amount,deal=None):
        deal=deal or Object(buyer=self.r.Hub,transferredamount=amount,unitprice=1200)
        self.r.Transfers[deal]=Ware(ware)
        self.run.env['event']=Table(param=deal)
        self.assertTrue(self.run.expr(self.guard))
        self.run.library('RecordDelivery')
        self.assertFalse(self.run.expr(self.guard))
        return deal

    def test_fractional_consumption_and_exact_first_exhaustion(self):
        self.food['Reserve']=600.25;self.water['Reserve']=90.125
        self.advance(300)
        self.assertAlmostEqual(self.food.Reserve,300.25)
        self.assertEqual(self.water.Reserve,0)
        self.assertAlmostEqual(self.r.GrowthSeconds,180.25)
        self.assertAlmostEqual(self.food.Demand,6899.75)

    def test_shortage_pauses_and_replenishment_resumes_without_reset(self):
        self.food['Reserve']=100;self.water['Reserve']=10
        self.advance(30);self.assertEqual(self.r.GrowthSeconds,20)
        self.advance(30);self.assertEqual(self.r.GrowthSeconds,20)
        self.deliver('water',100)
        self.advance(30);self.assertEqual(self.r.GrowthSeconds,50)
        self.assertEqual(self.food.Reserve,10)

    def test_late_delivery_cannot_cover_elapsed_shortage(self):
        self.food['Reserve']=1000
        self.run.env['player']['age']=600
        self.deliver('water',500)
        self.assertEqual(self.r.GrowthSeconds,0)
        self.assertEqual(self.food.Reserve,400)
        self.advance(60);self.assertEqual(self.r.GrowthSeconds,60)

    def test_partial_simultaneous_surplus_and_duplicate_callbacks(self):
        a=self.deliver('food',4)
        self.deliver('food',8000)
        self.assertEqual(self.food.Reserve,8004)
        self.assertEqual(self.food.Demand,0)
        self.assertEqual(self.food.Delivered,8004)
        self.assertEqual(self.food.Paid,8004*1200)
        self.run.env['event']=Table(param=a)
        self.assertFalse(self.run.expr(self.guard))
        self.run.env['event']=Table(param=Object(buyer=Object(),transferredamount=100))
        self.assertFalse(self.run.expr(self.guard)) # construction/other buyers excluded

    def test_rounding_and_reservations_with_tiny_rate(self):
        self.r.Wares=Table();self.food=self.add('food',0.001)
        self.run.library('md.CE_Reserves.SyncAll')
        self.assertEqual(self.food.Cap,1)
        self.assertEqual(self.food.Demand,1)
        del self.run.stubs['UpdateOffers']
        self.food.Offer=Table(exists=True,offeramount=1,amount=0)
        calls=[]
        self.run.native['update_trade']=lambda n:calls.append((self.run.expr(n.get('amount')),self.run.expr(n.get('desiredamount'))))
        self.run.library('UpdateOffers');self.assertEqual(calls[-1],(0,1))
        self.food.Reserve=0.1
        self.run.library('UpdateOffers');self.assertEqual(calls[-1],(0,0))
        self.advance(360000);self.assertEqual(self.food.Reserve,0)
        self.run.library('UpdateOffers');self.assertEqual(calls[-1],(0,1))

    def test_all_growth_durations_exact_boundary_and_single_commit(self):
        for level in range(1,10):
            self.r.Level=level;self.r.GrowthSeconds=0
            self.food.Reserve=self.water.Reserve=1000000
            required=(level+1)*3600
            self.advance(required-0.25);self.run.library('EvaluateQualification')
            self.assertFalse(self.r.Qualified)
            self.advance(0.25);self.run.library('EvaluateQualification')
            self.assertTrue(self.r.Qualified)
            self.advance(600);self.assertEqual(self.r.GrowthSeconds,required)
            self.r.Target=level+1;self.run.library('EvaluateQualification')
            self.assertFalse(self.r.Qualified)
            self.r.Target=0

    def test_pending_and_max_level_consume_without_growth(self):
        self.food.Reserve=self.water.Reserve=1000
        self.r.Target=2;self.advance(60)
        self.assertEqual(self.r.GrowthSeconds,0);self.assertEqual(self.food.Reserve,940)
        self.r.Target=0;self.r.Level=10;self.advance(60)
        self.assertEqual(self.r.GrowthSeconds,0);self.assertEqual(self.food.Reserve,880)

    def test_operational_pause_and_zero_requirements(self):
        self.food.Reserve=self.water.Reserve=1000
        self.advance(60);self.r.Operational=False;self.advance(10000)
        self.assertEqual(self.r.GrowthSeconds,60);self.assertEqual(self.food.Reserve,940)
        self.r.Operational=True;self.advance(60);self.assertEqual(self.r.GrowthSeconds,120)
        self.food.Rate=self.water.Rate=0
        self.advance(60);self.assertEqual(self.r.GrowthSeconds,120)
        self.food.Rate=10;self.food.Active=False
        self.advance(60);self.assertEqual(self.r.GrowthSeconds,120)

    def test_saved_balances_progress_clock_and_unloading_reference(self):
        self.food.Reserve=self.water.Reserve=10000
        self.advance(123.5)
        self.r.Target=2;self.r.Build='pending'
        deal=Object(exists=True);self.r.Transfers[deal]=Ware('food')
        saved=copy.deepcopy(self.run.env)
        self.advance(10.25);expected=(self.food.Reserve,self.water.Reserve,self.r.GrowthSeconds)
        self.run.env=saved;self.run.env['player']['age']+=10.25;self.run.library('AccrueAll')
        r=self.run.env['R']
        self.assertEqual((r.Wares['food'].Reserve,r.Wares['water'].Reserve,r.GrowthSeconds),expected)
        self.assertEqual(r.Build,'pending');self.assertEqual(len(r.Transfers),1)
        self.run.library('AccrueAll') # real-world elapsed time is never consulted
        self.assertEqual(r.Wares['food'].Reserve,expected[0])
