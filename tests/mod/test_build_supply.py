"""Stalled-build remainder top-up and build funding margin; native actions mocked."""
from types import SimpleNamespace
from support import Table, List, NIL
from support_startup import StartupHarness

class BuildSupplyTests(StartupHarness):
    def building(self, **needs):
        record=self.start();self.complete()
        record.InitialHub=NIL
        storage=record.Hub.buildstorage
        self.need(storage,**needs)
        self.added=[]
        self.run.native['add_cargo']=lambda n:self.added.append(
            (self.run.expr(n.get('object')),self.run.expr(n.get('ware')),self.run.expr(n.get('exact'))))
        self.run.env.update(R=record,Hub=record.Hub,Sector=record.Hub.sector)
        return record,storage

    def need(self, storage, **needs):
        storage.buildprocessor=Table(neededsequenceresources=Table(
            list=List(needs),**{ware:SimpleNamespace(count=count) for ware,count in needs.items()}))

    def tick(self, seconds=0):
        self.run.env['player'].age+=seconds
        self.run.library('md.CE_BuildSupply.Tick')

    def test_small_remainder_is_added_only_after_an_hour_unchanged(self):
        record,storage=self.building(energycells=1)
        self.tick()
        self.tick(3599)
        self.assertEqual(self.added,[])
        self.tick(1)
        self.assertEqual(self.added,[(storage,'energycells',1)])
        self.assertEqual(len(record.SupplyWait),0)

    def test_large_need_stays_with_traders(self):
        record,storage=self.building(claytronics=4)
        self.tick();self.tick(100000)
        self.assertEqual(self.added,[])
        self.assertEqual(len(record.SupplyWait),0)

    def test_changed_remainder_restarts_the_wait(self):
        record,storage=self.building(hullparts=3)
        self.tick()
        self.need(storage,hullparts=2)
        self.tick(3600)
        self.assertEqual(self.added,[])
        self.tick(3600)
        self.assertEqual(self.added,[(storage,'hullparts',2)])

    def test_each_ware_waits_on_its_own(self):
        record,storage=self.building(hullparts=1,claytronics=78)
        self.tick();self.tick(3600)
        self.assertEqual(self.added,[(storage,'hullparts',1)])

    def test_save_without_wait_state_starts_a_fresh_wait(self):
        record,storage=self.building(energycells=1)
        record.pop('SupplyWait',None)
        self.tick()
        self.assertEqual(self.added,[])
        self.assertEqual(record.SupplyWait['energycells'].Amount,1)

    def test_finished_build_and_seed_build_are_never_topped_up(self):
        record,storage=self.building(energycells=1)
        self.tick()
        for prepare in (lambda:record.update(Build=NIL),
                        lambda:record.update(InitialHub=record.Hub,Generation=1,Level=1,Target=0)):
            with self.subTest():
                saved=(record.Build,record.InitialHub,record.Generation,record.Level,record.Target)
                prepare();self.tick(3600)
                self.assertEqual(self.added,[])
                self.assertEqual(len(record.SupplyWait),0)
                record.update(Build=saved[0],InitialHub=saved[1],Generation=saved[2],Level=saved[3],Target=saved[4])

    def test_funding_covers_wanted_money_plus_margin(self):
        for wanted,budget in ((500000,510000),(20000000,20200000)):
            with self.subTest(wanted=wanted):
                record,storage=self.building()
                storage.wantedmoney=wanted;storage.money=0
                self.run.library('md.CE_Accounts.FundAccounts')
                self.assertEqual(storage.money,budget)

    def test_no_margin_is_funded_when_nothing_is_wanted(self):
        record,storage=self.building()
        storage.wantedmoney=0;storage.money=0
        self.run.library('md.CE_Accounts.FundAccounts')
        self.assertEqual(storage.money,0)
