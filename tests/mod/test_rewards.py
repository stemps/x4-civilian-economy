"""Execute shipped reward rules/effects with native calls recorded, not emulated."""
import copy
import unittest
from lxml import etree as E
from support import Runner, Table, List, Object, Ware, REF, NIL, MOD


class RewardsTests(unittest.TestCase):
    def setUp(self):
        self.run=Runner()
        self.sector=Object(knownname='Local')
        self.r=Table(Hub=Object(exists=True,iswreck=False,owner='civilian'),Level=10,
                     Operational=True,Population=1,Last=0,Wares=Table())
        self.food=Table(Active=True,Rate=3600,Reserve=10000)
        self.r.Wares[Ware('food')]=self.food
        self.run.env.update(R=self.r,Sector=self.sector,faction=Table(ownerless='ownerless',civilian='civilian',player='player'))
        self.run.env['md'].CE_CivilianHub.Init['Registry']=Table({self.sector:self.r})
        self.stations=List()
        self.calls=[]
        self.run.native['find_station']=lambda n:self.run.set(n.get('name'),self.stations.clone)
        for tag in ('add_player_discount','add_player_commission','remove_player_discount',
                    'remove_player_commission','add_player_gravidar_access_request',
                    'remove_player_gravidar_access_request','write_to_logbook','set_object_long_range_scanned'):
            self.run.native[tag]=lambda n:self.calls.append((n.tag,self.run.expr(n.get('object','null')),n.get('id')))

    def refresh(self): self.run.library('md.CE_Rewards.Refresh')
    def evaluate(self): self.run.library('md.CE_RewardRules.Evaluate')

    def station(self,**kw):
        s=Object(exists=True,iswreck=False,isplayerowned=False,isclass=Table(station=True),
                 sector=self.sector,owner='argon',hasrelation=Table(dock=Table(player=True)))
        s.update(kw);self.stations.append(s);return s

    def test_all_levels_and_projected_supply_without_mutation(self):
        for level in range(1,11):
            self.r['Level']=level;self.evaluate()
            self.assertEqual(self.run.env['ImmigrationRate'],max(0,10*(level-1)))
            self.assertEqual(self.run.env['PricePoints'],max(0,2*(level-2)))
            self.assertEqual(self.run.env['DiplomacyPoints'],max(0,2*(level-4)))
            self.assertEqual(self.run.env['SensorUnlocked'],level>=7)
            self.assertEqual(self.run.env['SurveyUnlocked'],level>=9)
        self.run.env['player']['age']=10000
        self.evaluate();self.assertFalse(self.run.env['RewardActive'])
        self.assertEqual(self.food.Reserve,10000)
        self.assertEqual(list(self.run.env['RewardMissing']),['food'])

    def test_unavailable_empty_new_ware_and_pending_level(self):
        self.r.update(Level=2,Target=10)
        self.evaluate();self.assertEqual(self.run.env['PricePoints'],0)
        water=Table(Active=True,Rate=1,Reserve=0)
        self.r.Wares[Ware('water')]=water
        self.evaluate();self.assertFalse(self.run.env['RewardActive'])
        water['Active']=False
        self.evaluate();self.assertTrue(self.run.env['RewardActive'])
        for changes in ({'Operational':False},{'Population':0}):
            old=dict(self.r);self.r.update(changes);self.evaluate()
            self.assertFalse(self.run.env['RewardActive']);self.r.update(old)
        self.r.Hub['owner']='player';self.evaluate();self.assertFalse(self.run.env['RewardActive'])

    def test_exactly_one_radar_request_and_owned_price_removal(self):
        station=self.station()
        self.refresh();self.refresh()
        self.assertEqual(sum(c[0]=='add_player_gravidar_access_request' for c in self.calls),1)
        self.assertEqual(sum(c[0]=='add_player_discount' for c in self.calls),1)
        self.food['Reserve']=0;self.refresh();self.refresh()
        self.assertEqual(sum(c[0]=='remove_player_gravidar_access_request' for c in self.calls),1)
        removed=[c[2] for c in self.calls if c[0].startswith('remove_player_') and c[2]]
        self.assertEqual(removed,["'ce_prosperity_buy'","'ce_prosperity_sell'"])
        self.assertFalse(self.r.Rewards.Applied[station].Radar)
        self.food['Reserve']=1000;self.refresh()
        self.assertEqual(sum(c[0]=='add_player_gravidar_access_request' for c in self.calls),2)

    def test_partners_include_unknown_but_not_player_ownerless_civilian_hostile_or_other_sector(self):
        self.station(isknown=False)
        self.station(isplayerowned=True)
        self.station(owner='ownerless')
        self.station(owner='civilian')
        self.station(hasrelation=Table(dock=Table(player=False)))
        self.station(sector=Object())
        self.station(isclass=Table(station=False))
        self.refresh()
        self.assertEqual(self.r.Rewards.Partners,1)
        self.assertEqual(self.r.Rewards.Sensors,1)

    def test_ownership_change_save_reload_ledger_and_reconciliation(self):
        s=self.station();self.refresh()
        # Copy saved ledger while retaining native object identity.
        ledger=Table({s:copy.deepcopy(self.r.Rewards.Applied[s])})
        self.r.Rewards['Applied']=ledger
        self.refresh();self.assertEqual(sum(c[0]=='add_player_gravidar_access_request' for c in self.calls),1)
        s['isplayerowned']=True;self.refresh();self.assertFalse(ledger[s].Radar)
        s['exists']=False;self.refresh();self.assertNotIn(s,ledger)

    def test_survey_filters_and_cadence(self):
        self.refresh()
        boxes=List([Object(exists=True,ismission=False,isradarvisible=True,isknown=False),
                    Object(exists=True,ismission=True,isradarvisible=True,isknown=False),
                    Object(exists=True,ismission=False,isradarvisible=False,isknown=False),
                    Object(exists=True,ismission=False,isradarvisible=True,isknown=True)])
        self.run.native['find_object']=lambda n:self.run.set(n.get('name'),boxes)
        self.run.env['player']['age']=300;self.evaluate()
        self.run.library('md.CE_RewardDiscovery.Survey')
        self.assertEqual(self.r.Rewards.Found,1)
        self.assertEqual(self.r.Rewards.NextSurvey,600)
        self.run.library('md.CE_RewardDiscovery.Survey')
        self.assertEqual(sum(c[0]=='set_object_long_range_scanned' for c in self.calls),1)
        self.food['Reserve']=0;self.run.env['player']['age']=600;self.evaluate()
        self.run.library('md.CE_RewardDiscovery.Survey')
        self.assertEqual(self.r.Rewards.LastSurvey,300)

    def workforce(self):
        race=Object(id='argon')
        station=self.station(isplayerowned=True,workforce=Table({race:Table(capacity=1000,amount=0)}))
        entry=Table(Fractions=Table())
        self.run.env.update(WorkRace=race,WorkStation=station,WorkEntry=entry,
                            WorkRow=List([race,1000,1000,1000,20]),
                            WorkRequest=List([station,List(),self.sector,60,90]),ImmigrationRate=90)
        self.run.native['add_workforce']=lambda n:self.calls.append(('workers',self.run.expr(n.get('exact'))))
        return race,station,entry

    def test_fractional_immigration_and_native_caps(self):
        race,station,entry=self.workforce()
        self.run.library('md.CE_RewardWorkforce.Grant')
        self.assertEqual(self.calls[-1],('workers',1));self.assertEqual(entry.Fractions[race],0.5)
        self.run.library('md.CE_RewardWorkforce.Grant')
        self.assertEqual(self.calls[-1],('workers',2));self.assertEqual(entry.Fractions[race],0)
        station.workforce[race]['amount']=999
        self.run.library('md.CE_RewardWorkforce.Grant')
        self.assertEqual(self.calls[-1],('workers',1));self.assertEqual(entry.Fractions[race],0)
        self.run.env['WorkRow'][5]=-1
        count=len(self.calls);self.run.library('md.CE_RewardWorkforce.Grant');self.assertEqual(len(self.calls),count)

    def test_shortage_discards_immigration_and_no_empty_profile_bonus(self):
        self.refresh();self.r.Rewards['Immigrants']=Table({self.station():Table(Last=1,Fractions=Table())})
        self.food['Reserve']=0;self.refresh();self.assertEqual(len(self.r.Rewards.Immigrants),0)
        self.r['Wares']=Table();self.evaluate()
        self.assertFalse(self.run.env['RewardActive']);self.assertEqual(self.run.env['RewardReason'],'no_demand')

    def test_query_is_read_only_and_sector_local(self):
        before=copy.deepcopy(dict(self.food))
        result=self.run.run_actions('md.CE_RewardRules.Query',{'Sector':self.sector})
        self.assertEqual(list(result)[:4],[True,90,16,12])
        self.assertEqual(dict(self.food),before)
        self.assertIs(self.run.env['R'],self.r)
        other=self.run.run_actions('md.CE_RewardRules.Query',{'Sector':Object()})
        self.assertFalse(other[1]);self.assertEqual(other[4],0)
        self.run.env['player']['age']=10001
        expired=self.run.run_actions('md.CE_RewardRules.Query',{'Sector':self.sector})
        self.assertFalse(expired[1])

    def test_gap_before_delivery_discards_fractional_entitlements(self):
        self.refresh();self.r.Rewards['Immigrants']=Table({self.station():Table(Fractions=Table())})
        self.food['Reserve']=1
        self.r.update(Target=0,GrowthSeconds=0)
        self.run.env['player']['age']=60
        # Only the reserve drain and reward reset are under test here.
        env=self.run.env
        self.run.stubs.update({
            'md.CE_DemandEvents.NextExpiry':lambda:env.update(DEDeadline=-1),
            'md.CE_Settings.RequiredGrowth':lambda:env.update(RequiredGrowthSeconds=7200.0),
            'md.CE_Reserves.SyncAll':lambda:None,'md.CE_Reserves.SyncWare':lambda:None,
            'md.CE_Unrest.AccrueInterval':lambda:None})
        self.run.library('md.CE_Reserves.Accrue')
        self.assertEqual(len(self.r.Rewards.Immigrants),0)
        self.food['Reserve']=1000;self.refresh()
        self.assertEqual(len(self.r.Rewards.Immigrants),0)

    def test_bridge_duplicate_expired_and_failed_responses(self):
        self.refresh()
        race,station,entry=self.workforce()
        station.workforce['races']=List([race])
        self.r.Rewards.Immigrants[station]=entry
        request=self.run.env['WorkRequest']
        row=self.run.env['WorkRow']
        state=self.run.env['md'].CE_RewardWorkforce.State
        state.update(Token=7,Sent=0,Pending=Table({station:request}))
        response=List([7,List([List([station,List([row,row])]),List([station,List([row])])])])
        self.run.env['player']['entity']=Table(ce_workforce_response=response)
        actions=self.run.scripts['CE_RewardWorkforce'].xpath('//cue[@name="Response"]/actions')[0]
        self.run.actions(actions);self.run.actions(actions)
        self.assertEqual([c for c in self.calls if c[0]=='workers'],[('workers',1)])
        state['Pending']=Table({station:request})
        self.run.env['player']['age']=11;self.run.actions(actions)
        self.assertEqual(len([c for c in self.calls if c[0]=='workers']),1)
        self.run.env['Pending']=Table({station:request})
        self.run.env['WorkforceResponse']=List([8,List()])
        self.run.library('md.CE_RewardWorkforce.Accept')
        self.assertEqual(len(entry.Fractions),0)

    def test_diplomacy_injection_only_accepts_station_targets_and_active_supply(self):
        patch=E.parse(str(MOD/'md/diplomacy.xml'))
        setup=patch.xpath('/diff/add[@pos="prepend"]')[0]
        addition=patch.xpath('/diff/add[@pos="after"]')[0]
        for station,stock,base,expected in ((True,1000,50,62),(True,1000,95,99),
                                          (False,1000,50,50),(True,0,50,50)):
            self.food['Reserve']=stock
            self.run.env['CEDestination']=Object(exists=True,isclass=Table(station=station),sector=self.sector)
            self.run.actions(setup)
            self.run.env['AssembledSuccessChance']=base
            self.run.actions(addition)
            self.assertEqual(min(self.run.env['AssembledSuccessChance'],99),expected)

    def test_diplomacy_patch_targets_every_call_once_without_replacing_native_roll(self):
        native=E.parse(str(REF/'md/diplomacy.xml'))
        patch=E.parse(str(MOD/'md/diplomacy.xml'))
        for op in patch.getroot():
            self.assertEqual(op.tag,'add')
            targets=native.xpath(op.get('sel'));self.assertEqual(len(targets),1,op.get('sel'))
            target=targets[0]
            children=[copy.deepcopy(child) for child in op]
            if op.get('pos')=='after':
                for child in reversed(children): target.addnext(child)
            elif op.get('pos')=='prepend':
                for child in reversed(children): target.insert(0,child)
            else:
                target.extend(children)
        calls=native.xpath('//run_actions[@ref="Success_Evaluation"]')
        self.assertEqual(len(calls),20)
        for call in calls:
            self.assertEqual(call.xpath('param[@name="CEDestination"]/@value'),['@$Operation.action.$station'])
        self.assertEqual(native.xpath('//library[@name="Success_Evaluation"]//set_value[@name="$EvaluatedSuccess"]/@seed'),['Start.$Seed']*3)
        self.assertEqual(native.xpath('//library[@name="Success_Evaluation"]//set_value[@name="$CalculatedSuccessChance"]/@exact'),['[$AssembledSuccessChance, 99].min'])


if __name__=='__main__': unittest.main()
