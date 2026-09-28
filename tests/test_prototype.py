"""Execute shipped MD calculation actions; native behavior still requires X4."""
import unittest, sys, copy, math
from pathlib import Path
from lxml import etree as E
from support import ROOT, REF, Runner, Table, List, NIL, wrap, Component, Ware, definitions

class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.run=Runner(); self.r=Table(GrowthSeconds=0.0,Last=0.0,Level=1,Target=0,Operational=True,Wares=Table(),Transfers=Table(),Hub=Component(sector=Component(isplayerowned=False)))
        self.run.env['R']=self.r
        self.w=Table(Reserve=0.0,Active=True,Rate=2000.,Cap=4000.,Demand=0.,Delivered=0,Paid=0,Offer=NIL)
        self.r.Wares[Ware('food')]=self.w
        self.run.library('RebaseAccrual')
    def advance(self, seconds):
        self.run.env['player']['age']+=seconds;self.run.library('AccrueAll')
    def evaluate(self): self.run.library('EvaluateQualification')
    def test_record_actual_delivery_and_guard_consumed(self):
        self.advance(60)
        deal=Table(transferredamount=10,unitprice=1300)
        # Trade references are hashable identities in the engine.
        class Deal(Table):
            __hash__=object.__hash__
        deal=Deal(deal);self.r.Transfers[deal]='food'
        self.run.env['event']=Table(param=deal)
        self.run.stubs.update(UpdateOffers=lambda:None,PublishDiagnostics=lambda:None,PublishAllDiagnostics=lambda:None)
        self.run.library('RecordDelivery')
        self.assertEqual(self.w.Reserve,10)
        self.assertEqual(self.w.Demand,3990)
        self.assertEqual(self.w.Delivered,10);self.assertEqual(self.w.Paid,13000)
        self.assertNotIn(deal,self.r.Transfers)
        checks=self.run.tree.xpath('//cue[@name="SectorDeliveryFinished"]/conditions/check_value/@value')
        self.assertIn('event.param.buyer == $R.$Hub and $R.$Transfers.{event.param}?',checks)
    def test_pending_and_top_level_never_requalify(self):
        self.r['Target']=2;self.evaluate();self.assertFalse(self.r.Qualified)
        self.r['Target']=0;self.r['Level']=10;self.evaluate();self.assertFalse(self.r.Qualified)
    def test_offer_updates_preserve_reservations_and_pause(self):
        self.r['Hub']=Table(exists=True,iswreck=False)
        self.r['PauseOffers']=False
        self.w.update(Reserve=2950,Price=1300,Offer=Table(exists=True,amount=150,offeramount=1000))
        calls=[]
        self.run.native['update_trade']=lambda n:calls.append((self.run.expr(n.get('trade')),self.run.expr(n.get('amount')),self.run.expr(n.get('desiredamount'))))
        self.run.library('UpdateOffers')
        self.assertIs(calls[0][0],self.w.Offer);self.assertEqual(calls[0][1:],(200,1050))
        self.r['PauseOffers']=True;self.run.library('UpdateOffers')
        self.assertEqual(calls[-1][1:],(0,1050))
        self.assertEqual(self.w.Demand,1050);self.assertEqual(self.w.Delivered,0)
    def test_active_unloading_defers_offer_rewrite(self):
        self.r['Hub']=Table(exists=True,iswreck=False);self.r['PauseOffers']=True
        self.w.update(Reserve=3000,Price=1300,Offer=Table(exists=True,amount=100,offeramount=1000))
        class Deal(Table): __hash__=object.__hash__
        deal=Deal(exists=True);self.r.Transfers[deal]='food'
        calls=[];self.run.native['update_trade']=lambda n:calls.append(n)
        self.run.library('UpdateOffers');self.assertEqual(calls,[])
        deal['exists']=False;self.run.library('UpdateOffers')
        self.assertEqual(len(calls),1);self.assertNotIn(deal,self.r.Transfers)

    def test_unloading_index_keeps_all_live_deals_and_is_rebuilt_per_hub(self):
        self.r.update(Hub=Table(exists=True,iswreck=False),PauseOffers=False)
        self.w.update(Price=1300,Offer=Table(exists=True,amount=0,offeramount=0))
        other=copy.deepcopy(self.w)
        self.r.Wares[Ware('water')]=other
        first,second,expired=(Component(exists=True),Component(exists=True),Component(exists=False))
        self.r.Transfers.update({first:Ware('food'),second:Ware('food'),expired:Ware('water')})
        calls=[]
        self.run.native['update_trade']=lambda n:calls.append(self.run.expr(n.get('trade')))
        self.run.library('UpdateOffers')
        self.assertEqual(len(calls),1);self.assertIs(calls[0],other.Offer)
        self.assertNotIn(expired,self.r.Transfers)
        first.exists=False;calls.clear();self.run.library('UpdateOffers')
        self.assertEqual(len(calls),1);self.assertIs(calls[0],other.Offer)
        self.assertIn(second,self.r.Transfers)
        second.exists=False;calls.clear();self.run.library('UpdateOffers')
        self.assertEqual(len(calls),2)
        self.assertTrue(any(offer is self.w.Offer for offer in calls))
        self.assertEqual(len(self.r.Transfers),0)
        # Reusing the caller namespace for another hub must not retain exclusions.
        second.exists=True;self.r.Transfers[second]=Ware('food')
        self.run.library('UpdateOffers')
        next_ware=copy.deepcopy(self.w)
        self.run.env['R']=Table(Hub=self.r.Hub,Operational=True,PauseOffers=False,
                               Transfers=Table(),Wares=Table({Ware('food'):next_ware}))
        calls.clear();self.run.library('UpdateOffers')
        self.assertEqual(len(calls),1);self.assertIs(calls[0],next_ware.Offer)

class ContentTests(unittest.TestCase):
    def test_apply_level_rates_prices_and_existing_backlog(self):
        run=Runner();definitions(run)
        r=Table(GrowthSeconds=0.0,Last=0.0,Level=1,Wares=Table());run.env['R']=r
        run.library('ApplyLevel')
        self.assertEqual(set(r.Wares),{'foodrations','water'})
        r.Wares['foodrations']['Reserve']=123.5
        r['Level']=2;run.library('ApplyLevel')
        self.assertEqual(r.Wares['foodrations'].Reserve,123.5)
        self.assertEqual(r.Wares['energycells'].Reserve,0)
        for level in range(2,11):
            r['Level']=level;run.library('ApplyLevel')
            for d in run.env['Definitions']:
                if d[2]<=level:
                    w=r.Wares[d[1]]
                    self.assertAlmostEqual(w.Rate,d[3]*1.25**(level-d[2]))
                    self.assertAlmostEqual(w.Cap,math.ceil(2*w.Rate))
                    self.assertEqual(w.Price,1200)
    def test_all_rates_and_unlocks(self):
        r=Runner();definitions(r)
        wares=E.parse(str(REF/'libraries/wares.xml'))
        defs=r.env['Definitions']
        self.assertEqual(len(defs),15)
        self.assertEqual([d[1] for d in defs if d[2]==1],['foodrations','water'])
        expected=[2,3,4,6,7,9,10,12,15,15]
        for level in range(1,11):self.assertEqual(sum(d[2]<=level for d in defs),expected[level-1])
        for d in defs:
            self.assertTrue(wares.xpath('/wares/ware[@id=$id]',id=d[1]))
            self.assertGreater(d[3],0)
    def test_safety_and_native_contracts(self):
        t=Runner().tree
        offers=Runner().trade.xpath('//create_trade_offer');self.assertEqual(len(offers),1)
        self.assertEqual(offers[0].get('virtualmoney'),'false');self.assertEqual(offers[0].get('virtual'),'true')
        listener=t.xpath('//cue[@name="SectorDeliveryFinished"]/conditions/event_trade_completed')[0]
        self.assertEqual(set(listener.attrib),{'buyer','seller'})
        self.assertFalse(t.xpath('//cue[@name="Start" or @name="WatchLevelHub"]'))
        self.assertTrue(Runner().construction.xpath('//library[@name="Queue"]//do_if[contains(@value,"builds.queued.count")]'))
        self.assertFalse(any(tree.xpath('//set_faction_relation|//remove_trade_offer') for tree in Runner().scripts.values()))
        # Destruction is confined to explicit sabotage, tracked raid cleanup,
        # and the exact temporary shell created by the opt-in layout test.
        for name, tree in Runner().scripts.items():
            if name == 'CE_DebugReset':
                destroy = tree.xpath('//destroy_object')
                self.assertEqual([n.get('object') for n in destroy], ['$ResetObject'])
                self.assertEqual(destroy[0].xpath('ancestor::library/@name'), ['Pump'])
                continue
            if name not in ('CE_Sabotage', 'CE_Raids', 'CE_RaidBehaviour'):
                self.assertFalse(tree.xpath('//destroy_object'), name)
        # Scripted rewards are restricted to the guarded completed-delivery tax.
        rewards = [node for tree in Runner().scripts.values() for node in tree.xpath('//reward_player')]
        self.assertEqual(len(rewards), 1)
        self.assertEqual(rewards[0].get('money'), '$SalesTax')
        self.assertEqual(rewards[0].getparent().get('value'),
                         '$R.$Hub.sector.isplayerowned and $Delivered gt 0 and event.param.unitprice gt 0Cr and $CETaxPercent gt 0')
        self.assertEqual(rewards[0].xpath('ancestor::library/@name'), ['RecordDelivery'])
        patch=E.parse(str(ROOT/'aiscripts/build.buildstorage.xml')).find('replace')
        base=E.parse(str(REF/'aiscripts/build.buildstorage.xml'))
        self.assertEqual(len(base.xpath(patch.get('sel'))),1)
        self.assertTrue(patch.text.startswith('not @player.entity.$ce_hubs.indexof.{this.object.base} and '))

class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.run=Runner();definitions(self.run)
        self.run.env['ModuleCounts']=List([4,6,8,11,13,16,19,21,23,27])
        self.run.env['PlanIDs']=List(['p'+str(i) for i in range(1,11)])
        self.run.env['faction']=Table(ownerless='ownerless',civilian='civilian')
        self.hub=Component(exists=True,iswreck=False,owner='civilian',
                       isoperational=True,isclass=Table(container=True),money=0,
                       constructionsequence=List([Table(id=str(i)) for i in range(6)]),
                       planmodule=Table({str(i):Table(isoperational=i<4) for i in range(6)}),
                       buildstorage=Table(exists=True,isoperational=True,money=0,wantedmoney=50000,
                                          builds=Table(queued=List(),inprogress=List()),buildmodule='module'))
        self.r=Table(GrowthSeconds=0.0,Last=0.0,Level=1,Target=2,Build=NIL,Hub=self.hub,InitializedHub=self.hub,Operational=True,
                     Wares=Table(),Transfers=Table(),PlotReady=True,PauseOffers=False,TestUpgrade=False,
                     CompletedSequence=List(self.hub.constructionsequence[:4]),TargetSequence=self.hub.constructionsequence)
        self.run.env['R']=self.r;self.run.library('ApplyLevel')
        self.r.Construction=Table(Valid=True,Levels=List(List(['m']*n) for n in (4,6,8,11,13,16,19,21,23,27)))
        for name in ('RenameHub','UpdateOffers','PublishDiagnostics','AssignBuilder'):
            self.run.stubs[name]=lambda:None
        # Exercise the real provisioning libraries; mock only native side effects.
        def transfer(node):
            amount=self.run.expr(node.get('amount'))
            self.run.expr(node.get('to')).money += amount
            self.run.set(node.get('result'),amount)
        self.run.native.update(transfer_money=transfer,set_object_account=lambda n:None,
            create_cue_actor=lambda n:self.run.set(n.get('name'),Component(exists=True)),
            assign_control_entity=lambda n:setattr(self.run.expr(n.get('object')),'tradenpc',self.run.expr(n.get('actor'))),
            remove_cue_actor=lambda n:None,create_ai_unit=lambda n:None)
        self.run.native['signal_objects']=lambda n:None
        self.run.native.update(show_notification=lambda n:None, write_to_logbook=lambda n:None)
        self.created=0
        def add(n):
            self.created+=1
            build=Table(exists=True)
            self.run.set(n.get('result'),build)
            self.run.env['R'].Hub.buildstorage.builds.queued.append(build)
        self.run.native['add_build_to_expand_station']=add
        self.run.native['process_build']=lambda n:None
    def test_expansion_keeps_base_demand_until_all_modules_finish(self):
        self.hub.buildstorage.builds.inprogress.append(Component(exists=True))
        self.run.env['player']['age']=60
        self.run.library('UpdateHub')
        self.assertTrue(self.r.Operational);self.assertEqual(self.r.Level,1)
        self.assertTrue(self.hub.tradenpc.exists)
        self.assertTrue(self.hub.buildstorage.tradenpc.exists)
        self.assertEqual(self.hub.money,sum(w.Cap*w.Price*2 for w in self.r.Wares.values()))
        self.assertEqual(self.hub.buildstorage.money,self.hub.buildstorage.wantedmoney)
        self.assertEqual(set(self.r.Wares),{'foodrations','water'})
        before=self.r.Wares['foodrations'].Reserve
        for m in self.hub.planmodule.values():m['isoperational']=True
        self.run.library('UpdateHub')
        self.assertEqual(self.r.Level,2);self.assertEqual(self.r.Target,0)
        self.assertEqual(self.r.Wares['foodrations'].Reserve,before)
        self.assertEqual(self.r.Wares['energycells'].Reserve,0)
    def test_every_completed_expansion_preserves_reserves_and_resets_growth(self):
        for target,count in enumerate([6,8,11,13,16,19,21,23,27],2):
            self.r['Target']=target;self.r['GrowthSeconds']=1234.5
            self.r.Wares['water']['Reserve']=777.25
            self.hub['constructionsequence']=List([Table(id=str(i)) for i in range(count)])
            self.hub['planmodule']=Table({str(i):Table(isoperational=True) for i in range(count)})
            self.r['TargetSequence']=self.hub.constructionsequence
            self.run.library('UpdateHub')
            self.assertEqual((self.r.Level,self.r.Target,self.r.GrowthSeconds),(target,0,0))
            self.assertEqual(self.r.Wares['water'].Reserve,777.25)
            for d in self.run.env['Definitions']:
                if d[2]==target:self.assertEqual(self.r.Wares[d[1]].Reserve,0)

    def test_damage_pauses_without_losing_progress_or_target(self):
        self.run.env['player']['age']=60;self.run.library('UpdateHub')
        self.r['GrowthSeconds']=1234.5
        self.r.Wares['water']['Reserve']=100
        self.hub.planmodule['0']['isoperational']=False
        self.run.env['player']['age']=600;self.run.library('UpdateHub')
        self.assertFalse(self.r.Operational);self.assertEqual(self.r.Target,2)
        self.assertEqual(self.r.GrowthSeconds,1234.5)
        self.assertEqual(self.r.Wares['water'].Reserve,100)
    def test_short_construction_sequence_stays_not_ready(self):
        self.hub['constructionsequence']=List([Table(id='0')])
        self.run.library('UpdateHub')
        self.assertFalse(self.r.Operational)
        self.assertEqual(self.r.Level,1)
        self.assertEqual(self.r.Target,2)
        self.assertEqual(self.r.PauseReason,'constructing')
    def test_pause_reasons_preserve_readiness_and_snapshot_contract(self):
        for module in self.hub.planmodule.values():
            module.update(exists=True,isconstruction=False,iswreck=False)
        self.run.library('UpdateHub')
        self.assertTrue(self.r.Operational)
        self.assertEqual(self.r.PauseReason,'active')  # Pending expansion does not pause level 1.
        module=self.hub.planmodule['0']
        module.update(isoperational=False,isconstruction=True)
        self.run.library('UpdateHub')
        self.assertEqual(self.r.PauseReason,'constructing')
        module.update(isconstruction=False,iswreck=True)
        self.run.library('UpdateHub')
        self.assertEqual(self.r.PauseReason,'damaged_modules')
        module.update(iswreck=False)
        self.run.library('UpdateHub')
        self.assertEqual(self.r.PauseReason,'modules_unavailable')
        module.update(isoperational=True)
        self.r['Population']=0
        self.run.library('UpdateHub')
        self.assertFalse(self.r.Operational)
        self.assertEqual(self.r.PauseReason,'no_population')
        del self.run.stubs['PublishDiagnostics']
        self.run.library('PublishDiagnostics')
        self.assertEqual(self.r.Snapshot[11],0)
        self.assertEqual(self.r.Snapshot[12],'no_population')
        self.r['Population']=1
        self.hub['owner']='player'
        self.run.library('UpdateHub')
        self.assertEqual(self.r.PauseReason,'owner_changed')
        self.hub['exists']=False
        self.run.library('UpdateHub')
        self.assertEqual(self.r.PauseReason,'hub_unavailable')
    def test_table_keys_require_explicit_list(self):
        with self.assertRaises(ValueError): self.run.expr('$R.$Wares.keys')
        self.assertEqual(set(self.run.expr('$R.$Wares.keys.list')),{'foodrations','water'})
    def test_pending_request_and_native_queue_prevent_duplicates(self):
        requested=[]
        self.run.native['signal_cue_instantly']=lambda n:requested.append(n.get('cue'))
        self.run.library('QueueExpansion');self.run.library('QueueExpansion')
        self.assertEqual(requested,['md.CE_Construction.Generate'])
        self.r.LayoutPending=False
        self.hub.buildstorage.builds.queued.append(Table(exists=True))
        self.run.library('QueueExpansion')
        self.assertEqual(len(requested),1)
    def test_destruction_loses_reserves_but_keeps_level_progress_counters(self):
        self.r['Level']=3;self.r['Target']=4;self.r['GrowthSeconds']=987.25
        self.r.Wares['foodrations'].update(Reserve=432.5,Delivered=77,Paid=100100)
        self.run.env['player']['entity']=Table()
        self.run.library('ForgetHub')
        self.assertEqual(self.r.Level,3);self.assertEqual(self.r.Target,0)
        self.assertEqual(self.r.Wares['foodrations'].Reserve,0)
        self.assertEqual(self.r.Wares['foodrations'].Delivered,77)
        self.assertFalse(self.r.Operational);self.assertEqual(self.r.GrowthSeconds,987.25)

if __name__=='__main__':unittest.main()
