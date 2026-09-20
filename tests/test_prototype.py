"""Execute shipped MD calculation actions; native behavior still requires X4."""
import unittest, sys, copy
from pathlib import Path
from lxml import etree as E
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from md_test_runtime import Runner, Table, List, NIL, wrap
from generate_plans import plans
REF=ROOT.parent.parent/'reference'

class Ware(str):
    minprice=1000
    maxprice=2200

def definitions(run):
    types=Table({w.get('id'):Ware(w.get('id')) for w in E.parse(str(REF/'libraries/wares.xml')).xpath('/wares/ware[price]')})
    run.env['ware']=types
    run.env['Definitions']=run.expr(run.tree.xpath('//set_value[@name="$Definitions"]/@exact')[0])

class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.run=Runner(); self.r=Table(Level=1,Target=0,Operational=True,Wares=Table(),Transfers=Table(),Hub='hub')
        self.run.env['R']=self.r
        self.w=Table(Rate=2000.,Cap=4000.,Demand=0.,Delivered=0,Paid=0,Offer=NIL)
        self.r.Wares[Ware('food')]=self.w
        self.run.library('ResetHistory')
    def advance(self, seconds):
        self.run.env['player']['age']+=seconds;self.run.library('AccrueAll')
    def deliver(self, amount):
        self.w['Demand']=max(0,self.w.Demand-amount)
        self.w.Bucket['Delivered']+=amount
    def evaluate(self): self.run.library('EvaluateQualification')
    def test_fractional_and_cap(self):
        self.advance(1); self.assertAlmostEqual(self.w.Demand,2000/3600)
        self.advance(20000);self.assertEqual(self.w.Demand,4000)
        self.assertAlmostEqual(sum(b.Generated for b in self.w.History),4000)
        self.assertEqual(len(self.w.History),120)
    def test_capped_generation_is_not_fulfillment(self):
        self.advance(15000);self.evaluate()
        self.assertEqual(self.w.SupplyScore,0);self.assertFalse(self.r.Qualified)
        self.assertAlmostEqual(sum(b.Generated for b in self.w.History),4000)
    def test_sustained_deliveries_qualify_only_full_window(self):
        for _ in range(120):self.advance(59);self.deliver(2000/60);self.advance(1)
        self.evaluate();self.assertTrue(self.r.Qualified)
        self.assertAlmostEqual(self.w.ServiceScore,1)
        self.assertGreaterEqual(self.w.SupplyScore,0.9)
    def test_partial_window_does_not_qualify(self):
        for _ in range(119):self.advance(59);self.deliver(2000/60);self.advance(1)
        self.evaluate();self.assertFalse(self.r.Qualified)
    def test_late_bulk_delivery_does_not_erase_shortage(self):
        self.advance(7199);self.deliver(4000);self.advance(1);self.evaluate()
        self.assertGreaterEqual(self.w.SupplyScore,.9);self.assertFalse(self.r.Qualified)
        self.assertGreater(self.w.LongestBad,900)
    def test_threshold_crossing_between_ticks(self):
        self.w['Demand']=990;self.advance(60)
        self.assertAlmostEqual(self.w.History[1].Good,18)
        self.assertAlmostEqual(self.w.History[1].Suffix,42)
    def test_delivery_midminute_breaks_shortage(self):
        self.w['Demand']=1100;self.advance(20);self.deliver(500);self.advance(40)
        b=self.w.History[1]
        self.assertEqual(b.Prefix,20);self.assertEqual(b.Suffix,0);self.assertEqual(b.MaxBad,20)
        self.assertEqual(b.Good,40)
    def test_cross_bucket_longest_breach(self):
        self.w['History']=List([Table(Generated=1,Delivered=1,Good=30,Prefix=0,Suffix=30,MaxBad=30),
                               Table(Generated=1,Delivered=1,Good=0,Prefix=60,Suffix=60,MaxBad=60),
                               Table(Generated=1,Delivered=1,Good=30,Prefix=30,Suffix=0,MaxBad=30)])
        self.evaluate();self.assertEqual(self.w.LongestBad,120)
    def test_exact_qualification_boundaries(self):
        # 90% service and a 15 minute breach must pass; any longer must fail.
        self.r['Level']=2
        self.w['History']=List([Table(Generated=1,Delivered=.9,Good=54,Prefix=0,Suffix=0,MaxBad=0) for _ in range(180)])
        self.w.History[1]['MaxBad']=900
        self.evaluate();self.assertTrue(self.r.Qualified)
        self.w.History[1]['MaxBad']=900.01
        self.evaluate();self.assertFalse(self.r.Qualified)
    def test_one_missing_ware_blocks(self):
        for _ in range(120):self.advance(59);self.deliver(2000/60);self.advance(1)
        missing=copy.deepcopy(self.w)
        for b in missing.History:b['Delivered']=0
        self.r.Wares['water']=missing;self.evaluate();self.assertFalse(self.r.Qualified)
    def test_paused_service_has_no_catchup(self):
        self.advance(60);d=self.w.Demand
        self.r['Operational']=False;self.advance(10000);self.run.library('ResetHistory')
        self.r['Operational']=True;self.advance(60)
        self.assertAlmostEqual(self.w.Demand,d+2000/60)
    def test_save_copy_retains_fraction_history_and_pending(self):
        self.advance(99.25);self.r['Target']=2;self.r['Build']='saved_task'
        saved=copy.deepcopy(self.run.env)
        self.advance(123.5);expected=self.w.Demand
        self.run.env=saved;self.run.env['player']['age']+=123.5;self.run.library('AccrueAll')
        self.assertAlmostEqual(self.run.env['R'].Wares['food'].Demand,expected)
        self.assertEqual(self.run.env['R'].Build,'saved_task')
    def test_record_actual_delivery_and_guard_consumed(self):
        self.advance(60)
        deal=Table(transferredamount=10,unitprice=1300)
        # Trade references are hashable identities in the engine.
        class Deal(Table):
            __hash__=object.__hash__
        deal=Deal(deal);self.r.Transfers[deal]='food'
        self.run.env['event']=Table(param=deal)
        self.run.stubs.update(UpdateOffers=lambda:None,PublishDiagnostics=lambda:None)
        self.run.library('RecordDelivery')
        self.assertAlmostEqual(self.w.Demand,2000/60-10)
        self.assertEqual(self.w.Delivered,10);self.assertEqual(self.w.Paid,13000)
        self.assertNotIn(deal,self.r.Transfers)
        checks=self.run.tree.xpath('//cue[@name="DeliveryFinished"]/conditions/check_value/@value')
        self.assertIn('event.param.buyer == $R.$Hub and $R.$Transfers.{event.param}?',checks)
    def test_pending_and_top_level_never_requalify(self):
        self.r['Target']=2;self.evaluate();self.assertFalse(self.r.Qualified)
        self.r['Target']=0;self.r['Level']=10;self.evaluate();self.assertFalse(self.r.Qualified)
    def test_offer_updates_preserve_reservations_and_pause(self):
        self.r['Hub']=Table(exists=True,iswreck=False)
        self.r['PauseOffers']=False
        self.w.update(Demand=1050,Price=1300,Offer=Table(exists=True,amount=150,offeramount=1000))
        calls=[]
        self.run.native['update_trade']=lambda n:calls.append((self.run.expr(n.get('trade')),self.run.expr(n.get('amount')),self.run.expr(n.get('desiredamount'))))
        self.run.library('UpdateOffers')
        self.assertIs(calls[0][0],self.w.Offer);self.assertEqual(calls[0][1:],(200,1050))
        self.r['PauseOffers']=True;self.run.library('UpdateOffers')
        self.assertEqual(calls[-1][1:],(0,1050))
        self.assertEqual(self.w.Demand,1050);self.assertEqual(self.w.Delivered,0)
    def test_active_unloading_defers_offer_rewrite(self):
        self.r['Hub']=Table(exists=True,iswreck=False);self.r['PauseOffers']=True
        self.w.update(Demand=1000,Price=1300,Offer=Table(exists=True,amount=100,offeramount=1000))
        class Deal(Table): __hash__=object.__hash__
        deal=Deal(exists=True);self.r.Transfers[deal]='food'
        calls=[];self.run.native['update_trade']=lambda n:calls.append(n)
        self.run.library('UpdateOffers');self.assertEqual(calls,[])
        deal['exists']=False;self.run.library('UpdateOffers')
        self.assertEqual(len(calls),1);self.assertNotIn(deal,self.r.Transfers)

class ContentTests(unittest.TestCase):
    def test_apply_level_rates_prices_and_existing_backlog(self):
        run=Runner();definitions(run)
        r=Table(Level=1,Wares=Table());run.env['R']=r
        run.library('ApplyLevel')
        self.assertEqual(set(r.Wares),{'foodrations','water'})
        r.Wares['foodrations']['Demand']=123.5
        r['Level']=2;run.library('ApplyLevel')
        self.assertEqual(r.Wares['foodrations'].Demand,123.5)
        self.assertEqual(r.Wares['energycells'].Demand,0)
        for level in range(2,11):
            r['Level']=level;run.library('ApplyLevel')
            for d in run.env['Definitions']:
                if d[2]<=level:
                    w=r.Wares[d[1]]
                    self.assertAlmostEqual(w.Rate,d[3]*1.25**(level-d[2]))
                    self.assertAlmostEqual(w.Cap,2*w.Rate)
                    self.assertEqual(w.Price,1200)
    def test_plans_cumulative_and_growth(self):
        expected=plans(); actual=E.parse(str(ROOT/'libraries/constructionplans.xml')).xpath('//plan')
        self.assertEqual(len(actual),10)
        for i,p in enumerate(actual):
            self.assertEqual(len(p),[4,6,8,11,13,16,19,21,23,27][i])
            self.assertEqual([dict(e.attrib) for e in p],[dict(e.attrib) for e in expected[i]])
            if i:
                for a,b in zip(actual[i-1],p): self.assertEqual(E.tostring(a).strip(),E.tostring(b).strip())
    def test_snap_positions_and_plot_bounds(self):
        mi=E.parse(str(REF/'index/macros.xml'));ci=E.parse(str(REF/'index/components.xml'))
        snaps={}
        for e in plans()[-1]:
            name=e.get('macro')
            if name not in snaps:
                m=E.parse(str(REF/(mi.xpath('//entry[@name=$n]/@value',n=name)[0]+'.xml')))
                comp=m.find('macro/component').get('ref')
                c=E.parse(str(REF/(ci.xpath('//entry[@name=$n]/@value',n=comp)[0]+'.xml')))
                snaps[name]={n.get('name').lower():[float(n.find('offset/position').get(k,0)) for k in ('x','y','z')]
                             for n in c.xpath('//component/connections/connection') if 'snap' in n.get('name','').lower()}
                self.assertIn(m.find('macro').get('class'),['dockarea','pier','storage','connectionmodule'])
        entries={int(e.get('index')):e for e in plans()[-1]}; used=set()
        def point(e,snap):
            pos=e.find('offset/position');return [float(pos.get(k))+v for k,v in zip(('x','y','z'),snaps[e.get('macro')][snap])]
        for e in entries.values():
            pos=e.find('offset/position')
            for k,limit in [('x',6000),('y',4000),('z',16000)]: self.assertLess(abs(float(pos.get(k))),limit-1500)
            p=e.find('predecessor')
            if p is None:continue
            key=(p.get('index'),p.get('connection'));self.assertNotIn(key,used);used.add(key)
            for a,b in zip(point(e,e.get('connection')),point(entries[int(p.get('index'))],p.get('connection'))):self.assertAlmostEqual(a,b,places=4)
    def test_all_rates_and_unlocks(self):
        r=Runner()
        wares=E.parse(str(REF/'libraries/wares.xml'))
        types=Table()
        for w in wares.xpath('/wares/ware[price]'):
            types[w.get('id')]=w.get('id')
        r.env['ware']=types
        expr=r.tree.xpath('//set_value[@name="$Definitions"]/@exact')[0]
        defs=r.expr(expr)
        self.assertEqual(len(defs),15)
        self.assertEqual([d[1] for d in defs if d[2]==1],['foodrations','water'])
        expected=[2,3,4,6,7,9,10,12,15,15]
        for level in range(1,11):self.assertEqual(sum(d[2]<=level for d in defs),expected[level-1])
        for d in defs:
            self.assertTrue(wares.xpath('/wares/ware[@id=$id]',id=d[1]))
            self.assertGreater(d[3],0)
    def test_safety_and_native_contracts(self):
        t=Runner().tree
        offers=t.xpath('//create_trade_offer');self.assertEqual(len(offers),1)
        self.assertEqual(offers[0].get('virtualmoney'),'false');self.assertEqual(offers[0].get('virtual'),'true')
        listener=t.xpath('//cue[@name="DeliveryFinished"]/conditions/event_trade_completed')[0]
        self.assertEqual(set(listener.attrib),{'buyer','seller'})
        self.assertTrue(t.xpath('//cue[@name="Init"]//set_value[@name="$Blocked"]'))
        self.assertTrue(t.xpath('//library[@name="QueueExpansion"]//do_if[contains(@value,"builds.queued.count")]'))
        self.assertFalse(t.xpath('//reward_player|//set_faction_relation|//destroy_object|//remove_trade_offer'))
        patch=E.parse(str(ROOT/'aiscripts/build.buildstorage.xml')).find('replace')
        base=E.parse(str(REF/'aiscripts/build.buildstorage.xml'))
        self.assertEqual(len(base.xpath(patch.get('sel'))),1)
        self.assertTrue(patch.text.startswith('this.object.base != @player.entity.$ce_hub and '))

class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.run=Runner();definitions(self.run)
        self.run.env['ModuleCounts']=List([4,6,8,11,13,16,19,21,23,27])
        self.run.env['PlanIDs']=List(['p'+str(i) for i in range(1,11)])
        self.run.env['faction']=Table(ownerless='ownerless')
        self.hub=Table(exists=True,iswreck=False,owner='ownerless',
                       constructionsequence=List([Table(id=str(i)) for i in range(6)]),
                       planmodule=Table({str(i):Table(isoperational=i<4) for i in range(6)}),
                       buildstorage=Table(exists=True,builds=Table(queued=List(),inprogress=List()),buildmodule='module'))
        self.r=Table(Level=1,Target=2,Build=NIL,Hub=self.hub,InitializedHub=self.hub,Operational=True,
                     Wares=Table(),Transfers=Table(),PlotReady=True,PauseOffers=False,TestUpgrade=False)
        self.run.env['R']=self.r;self.run.library('ApplyLevel')
        for name in ('FundAccounts','EnsureManager','RenameHub','UpdateOffers','PublishDiagnostics','AssignBuilder'):
            self.run.stubs[name]=lambda:None
        self.run.native['signal_objects']=lambda n:None
        self.created=0
        def add(n):
            self.created+=1
            build=Table(exists=True)
            self.run.set(n.get('result'),build)
            self.run.env['R'].Hub.buildstorage.builds.queued.append(build)
        self.run.native['add_build_to_expand_station']=add
        self.run.native['process_build']=lambda n:None
    def test_expansion_keeps_base_demand_until_all_modules_finish(self):
        self.run.env['player']['age']=60
        self.run.library('UpdateHub')
        self.assertTrue(self.r.Operational);self.assertEqual(self.r.Level,1)
        self.assertEqual(set(self.r.Wares),{'foodrations','water'})
        before=self.r.Wares['foodrations'].Demand
        for m in self.hub.planmodule.values():m['isoperational']=True
        self.run.library('UpdateHub')
        self.assertEqual(self.r.Level,2);self.assertEqual(self.r.Target,0)
        self.assertEqual(self.r.Wares['foodrations'].Demand,before)
        self.assertEqual(self.r.Wares['energycells'].Demand,0)
    def test_damage_pauses_and_resets_without_losing_target(self):
        self.run.env['player']['age']=60;self.run.library('UpdateHub')
        self.hub.planmodule['0']['isoperational']=False
        self.run.env['player']['age']=600;self.run.library('UpdateHub')
        self.assertFalse(self.r.Operational);self.assertEqual(self.r.Target,2)
        self.assertEqual(self.r.HistoryMinutes,0)
    def test_short_construction_sequence_stays_not_ready(self):
        self.hub['constructionsequence']=List([Table(id='0')])
        self.run.library('UpdateHub')
        self.assertFalse(self.r.Operational)
        self.assertEqual(self.r.Level,1)
        self.assertEqual(self.r.Target,2)
    def test_table_keys_require_explicit_list(self):
        with self.assertRaises(ValueError): self.run.expr('$R.$Wares.keys')
        self.assertEqual(set(self.run.expr('$R.$Wares.keys.list')),{'foodrations','water'})
    def test_pending_task_and_native_queue_prevent_duplicates(self):
        self.run.library('QueueExpansion');self.run.library('QueueExpansion')
        self.assertEqual(self.created,1)
        self.run.env=copy.deepcopy(self.run.env)
        self.run.library('QueueExpansion');self.assertEqual(self.created,1)
        # Even if the stored reference is gone, native queue is authoritative.
        self.run.env['R']['Build']=NIL
        self.run.library('QueueExpansion');self.assertEqual(self.created,1)
    def test_destruction_retains_earned_level_backlog_and_counters(self):
        self.r['Level']=3;self.r['Target']=4
        self.r.Wares['foodrations'].update(Demand=432.5,Delivered=77,Paid=100100)
        self.run.env['player']['entity']=Table()
        self.run.library('ForgetHub')
        self.assertEqual(self.r.Level,3);self.assertEqual(self.r.Target,0)
        self.assertEqual(self.r.Wares['foodrations'].Demand,432.5)
        self.assertEqual(self.r.Wares['foodrations'].Delivered,77)
        self.assertFalse(self.r.Operational);self.assertEqual(self.r.HistoryMinutes,0)

class GrowthPlotTests(unittest.TestCase):
    def reserve(self, half, center, safe=True):
        run=Runner()
        plot=Table(max=Table(zip('xyz',half)),center=Table(zip('xyz',center)))
        run.env.update(Hub=Table(buildplot=plot),R=Table(PlotReady=False))
        calls=[]
        def check(node):
            calls.append({side+axis:run.expr(node.get(side+axis)) for side in ('neg','pos') for axis in 'xyz'})
            run.env['SafePlot']=safe
        def extend(node):
            growth={side+axis:run.expr(node.get(side+axis)) for side in ('neg','pos') for axis in 'xyz'}
            self.assertEqual(growth,calls[-1])
            for axis in 'xyz':
                neg,pos=growth['neg'+axis],growth['pos'+axis]
                plot.max[axis]+=(neg+pos)/2
                plot.center[axis]+=(pos-neg)/2
        run.native.update(can_safely_extend_build_plot=check,extend_build_plot=extend)
        run.library('ReserveGrowthPlot')
        return run,plot,calls
    def test_incremental_growth_matches_checked_bounds(self):
        run,plot,calls=self.reserve((1000,1000,1000),(0,0,0))
        self.assertEqual(calls[0],dict(negx=5000,posx=5000,negy=3000,posy=3000,negz=15000,posz=15000))
        self.assertEqual(list(plot.max.values()),[6000,4000,16000])
        self.assertTrue(run.env['R'].PlotReady)
        run.library('ReserveGrowthPlot');self.assertEqual(len(calls),1)
    def test_off_center_existing_plot_is_preserved(self):
        run,plot,calls=self.reserve((8000,5000,17000),(4000,-2000,2000))
        self.assertEqual(calls[0],dict(negx=2000,posx=0,negy=0,posy=1000,negz=1000,posz=0))
        self.assertTrue(run.env['R'].PlotReady)
    def test_rejected_growth_does_not_resize_or_unlock(self):
        run,plot,calls=self.reserve((1000,1000,1000),(0,0,0),safe=False)
        self.assertFalse(run.env['R'].PlotReady)
        self.assertEqual(list(plot.max.values()),[1000,1000,1000])
    def test_existing_large_plot_needs_no_further_clearance(self):
        run,plot,calls=self.reserve((12000,8000,32000),(0,0,0),safe=False)
        self.assertTrue(run.env['R'].PlotReady);self.assertEqual(calls,[])

if __name__=='__main__':unittest.main()
