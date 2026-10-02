"""Native effects are stand-ins; scheduling, guards and messages execute real MD."""
import unittest
from types import SimpleNamespace
from lxml import etree as E
from support import Table, List, Component, Ware, NIL, MOD
from support_unrest import UnrestFixture


class RaidShip(Component):
    """Ship components cannot store script variables; pilot entities can."""
    def __setitem__(self, key, value):
        if str(key).startswith('ce_unrest_'):
            raise ValueError('Ship components have no entity blackboard')
        super().__setitem__(key, value)


class DroneBay(Table):
    """Native units share a finite bay; adding cargo drones cannot overfill it."""
    @property
    def count(self):return self.transport.count+self.other
    @property
    def free(self):return max(0,self.maxcount-self.count)


class IncidentTests(UnrestFixture, unittest.TestCase):

    def sabotage(self, kind, available=True):
        self.station=Component(exists=True,owner='player',sector=self.sector,knownname='Station',cargo=Table(list=List()))
        self.module=Component(exists=True,iswreck=False,isoperational=True,ishacked=False,ispaused=False,
                              ispausedmanually=False,owner='player',knownname='Module')
        self.station.modules=Table(operational=Table(list=List([self.module])))
        self.run.env.update(IncidentDebug=True,IncidentKind=kind,IncidentTier=3)
        self.run.native['shuffle_list']=lambda n:None
        self.run.native['find_station']=lambda n:self.run.set(n.get('name'),List([self.station]) if available else List())
        self.run.native['find_object_component']=lambda n:self.run.set(n.get('name'),List([self.module]))
        self.run.native['set_production_paused']=lambda n:setattr(self.run.expr(n.get('object')),'ispausedmanually',n.get('paused')!='false')
        def hack(n):
            self.module.ishacked=True
            self.run.set(n.get('result'),List([self.module]))
        self.run.native['set_object_hacked']=hack

    def test_each_hack_reports_station_attack_type_and_affected_module(self):
        for kind in ('production','turrets','shields'):
            with self.subTest(kind=kind):
                self.setUp();self.sabotage(kind)
                self.module.module = self.module if kind == 'production' else Component(exists=True, knownname='Defense module')
                self.run.library('md.CE_Sabotage.Request')
                self.assertTrue(self.run.env['IncidentSuccess'])
                self.assertEqual(self.run.env['BroadcastKey'], 'ce_news_hacking')
                self.assertEqual(len(self.messages),1)
                self.assertEqual(self.messages[0][1][1],204)
                details = self.messages[0][1][2]
                self.assertEqual(details[:2], ('Station','Sector'))
                self.assertEqual(details[2], 'Module' if kind == 'production' else (974201,300,('Module','Defense module')))
                self.assertEqual(details[4], (974201,{'production':297,'turrets':298,'shields':299}[kind],()))
                self.assertEqual(self.u.NextSabotage,5400)
                self.assertEqual(self.run.env['md'].CE_Sabotage.State.Stations[self.station].Next,5400)

    def test_unavailable_or_already_hacked_does_not_report_success(self):
        self.sabotage('turrets',available=False)
        self.run.library('md.CE_Sabotage.Request')
        self.assertFalse(self.run.env['IncidentSuccess'])
        self.assertEqual(self.messages[0][0],'ticker')
        self.assertEqual(self.u.NextSabotage,0)
        self.sabotage('turrets');self.module.ishacked=True
        self.messages.clear();self.run.library('md.CE_Sabotage.Request')
        self.assertFalse(self.run.env['IncidentSuccess'])
        self.assertFalse(any(m[0]=='popup' for m in self.messages))

    def test_cargo_reports_actual_native_quantity(self):
        self.sabotage('cargo')
        ware=Ware('cargo');ware.averageprice=100000
        self.station.cargo=Table({ware:SimpleNamespace(count=10000),'list':List([ware])})
        requested=[]
        def drop(n):
            self.assertIsNotNone(n.get('wares'), 'Native amounts output requires wares output')
            requested.append(self.run.expr(n.get('exact')))
            self.run.set(n.get('amounts'),List([37]))
        self.run.native['drop_cargo']=drop
        self.run.library('md.CE_Sabotage.Request')
        self.assertEqual(requested,[100])
        self.assertEqual(self.run.env['BroadcastKey'], 'ce_news_hacking')
        self.assertEqual(self.messages[0][1][2][-1],37)

    def test_manual_pause_is_not_overwritten(self):
        self.sabotage('production');self.module.ispaused=True;self.module.ispausedmanually=True
        self.run.library('md.CE_Sabotage.Request')
        self.assertFalse(self.run.env['IncidentSuccess'])
        self.assertNotIn(self.module,self.run.env['md'].CE_Sabotage.State.Pauses)

    def test_timed_restore_and_player_intervention(self):
        self.sabotage('production');self.run.library('md.CE_Sabotage.Request')
        state=self.run.env['md'].CE_Sabotage.State
        tree=self.run.scripts['CE_Sabotage']
        self.run.env['player']['age']=301
        self.run.actions(tree.xpath('//cue[@name="RestorePauses"]/actions')[0])
        self.assertFalse(self.module.ispausedmanually)
        self.module.ispausedmanually=True;state.Pauses[self.module]=500
        self.run.env['event']=Table(param3=self.module)
        self.run.actions(tree.xpath('//cue[@name="PlayerPause"]/actions')[0])
        self.run.env['player']['age']=600
        self.run.actions(tree.xpath('//cue[@name="RestorePauses"]/actions')[0])
        self.assertTrue(self.module.ispausedmanually)

    def test_destruction_waits_for_confirmed_wreck_and_keeps_last_module_eligible(self):
        self.sabotage('destroy')
        tree=self.run.scripts['CE_Sabotage']
        captured=[]
        self.run.native['signal_cue_instantly']=lambda n:captured.append(self.run.expr(n.get('param')))
        self.run.library('md.CE_Sabotage.Request')
        self.assertEqual(len(captured),1);self.assertEqual(self.messages,[])
        self.run.env['event']=Table(param=captured[0])
        self.run.native['destroy_object']=lambda n:None
        self.run.actions(tree.xpath('//cue[@name="DestroyModule"]/actions')[0])
        self.module.iswreck=True
        self.run.actions(tree.xpath('//cue[@name="Confirm"]/actions')[0])
        self.assertEqual(self.messages[0][1][1],206)
        self.assertEqual(self.run.env['BroadcastKey'], 'ce_news_sabotage')
        self.assertEqual(self.messages[0][1][2],('Station','Sector','Module'))
        self.assertEqual(self.u.NextDestruction,14400)

    def test_debug_dispatch_rejects_replays_wrong_hub_and_disabled_debug(self):
        self.run.env['md'].CE_CivilianHub.Init.Registry=Table({self.sector:self.r})
        self.run.env['md'].CE_Settings.State.Debug=True
        self.run.env['event']=Table(param2='raid_1:0',param3=self.hub)
        self.run.stubs.update({'md.CE_Reserves.Accrue':lambda:None,
                              'md.CE_Diagnostics.PublishDiagnostics':lambda:None,
                              'md.CE_Diagnostics.PublishAllDiagnostics':lambda:None})
        calls=[]
        self.run.stubs['md.CE_DebugUnrest.Dispatch']=lambda:calls.append(self.run.env['DebugCommand'])
        actions=self.run.scripts['CE_DebugUnrest'].xpath('//cue[@name="Request"]/actions')[0]
        self.run.actions(actions);self.run.actions(actions)
        self.assertEqual(calls,['raid_1']);self.assertEqual(self.u.Token,1)
        self.run.env['event'].param2='raid_1:1';self.run.env['event'].param3=Component()
        self.run.actions(actions);self.assertEqual(len(calls),1)
        self.run.env['event'].param3=self.hub;self.run.env['md'].CE_Settings.State.Debug=False
        self.run.actions(actions);self.assertEqual(len(calls),1)

    def setup_raids(self, tier, failure_at=0):
        self.run.env.update(IncidentTier=tier,IncidentDebug=True,
            macro=Table(ship_arg_m_bomber_01_a_macro='M',ship_arg_s_fighter_01_a_macro='S',ship_arg_l_destroyer_01_a_macro='L'),
            tag=Table(dock_m='M',dock_s='S',dock_l='L'),lookup=Table(ware=Table(list=List())),
            assignment=Table(attack='attack'), unitcategory=Table(transport='transport'),
            attention=Table(visible=1), weaponmode=Table(holdfire='holdfire',defend='defend'))
        self.run.env['player'].entity=Table(hascontext=Table())
        self.run.env['faction'].argon='argon'
        self.created=[];self.orders=[]
        self.docks={size:[Component(exists=True,occupied=False) for _ in range(100)] for size in ('M','S','L')}
        def find_docks(n):
            match=n.find('match_dock')
            self.assertEqual((n.get('multiple'),match.get('free'),match.get('storage')),('true','true','false'))
            self.run.set(n.get('name'),List([dock for dock in self.docks[self.run.expr(match.get('size'))] if not dock.occupied]))
        self.run.native['find_dockingbay']=find_docks
        def create(n):
            dock=self.run.expr(n.get('dock'))
            self.assertFalse(dock.occupied,'Native engine rejects an already assigned external berth')
            ship=RaidShip(exists=True,iswreck=False,owner='civilian',isplayerowned=False,pilot=Component(),dock=dock,
                           macro=self.run.expr(n.get('macro')),orders=List(),boardingoperations=List(),
                           attention=0,lastattacktime=-1,trueowner='civilian',sector=self.sector,size=100,
                           units=DroneBay(transport=SimpleNamespace(count=0),other=0,maxcount=10),cargo=Table(free=Table(all=100)),
                           weapons=Table(operational=Table(list=List())),
                           isclass=Table(ship_l=self.run.expr(n.get('macro'))=='L',ship_m=self.run.expr(n.get('macro'))=='M'))
            self.created.append(ship)
            if len(self.created)!=failure_at:dock.occupied=True
            self.run.set(n.get('name'),NIL if len(self.created)==failure_at else ship)
        self.run.native['create_ship']=create
        def generate(n):
            include_units=not (n.get('invertflags')=='true' and 'units' in n.get('flags','').split())
            self.run.set(n.get('result'),List([Table(include_units=include_units)]))
        def apply(n):
            ship=self.run.expr(n.get('object'))
            if ship.macro=='L' and self.run.expr(n.get('loadout')).include_units:
                ship.units.other=9
        self.run.native['generate_loadout']=generate
        self.run.native['apply_loadout']=apply
        self.run.native['find_object_component']=lambda n:self.run.set(n.get('name'),Component(exists=True))
        def owner(n):
            ship=self.run.expr(n.get('object'));ship.owner=ship.trueowner=self.run.expr(n.get('faction'))
        self.run.native['set_owner']=owner
        def add_units(n):
            bay=self.run.expr(n.get('object')).units
            bay.transport.count+=min(self.run.expr(n.get('exact')),bay.free)
        self.run.native['add_units']=add_units
        self.run.native['create_position']=lambda n:self.run.set(n.get('name'),Table(x=0,y=0,z=15000))
        self.run.native['get_safe_pos']=lambda n:self.run.set(n.get('result'),self.run.expr(n.get('value')))
        self.run.native['cease_fire']=lambda n:None
        self.run.native['set_turrets_armed']=lambda n:setattr(self.run.expr(n.get('object')),'armed',self.run.expr(n.get('armed')))
        self.run.native['set_weapon_mode']=lambda n:None
        self.run.native['remove_object_commander']=lambda n:setattr(self.run.expr(n.get('object')),'commander',NIL)
        self.run.native['cancel_order']=lambda n:setattr(self.run.expr(n.get('order')),'exists',False)
        self.run.native['destroy_object']=lambda n:setattr(self.run.expr(n.get('object')),'exists',False)
        def assign(n):
            ship=self.run.expr(n.get('object'))
            ship.commander=self.run.expr(n.get('commander'))
            self.assertEqual(ship.owner,ship.commander.owner)
            self.assertEqual(ship.owner,'raiders')
            ship.assignment=self.run.expr(n.get('assignment'))
        self.run.native['set_object_commander']=assign
        def order(n):
            ship=self.run.expr(n.get('object'));order_id=self.run.expr(n.get('id'))
            self.orders.append((ship,order_id))
            order=Component(exists=True,id=order_id)
            if n.get('name'):self.run.set(n.get('name'),order)
            if n.get('immediate')=='true':ship.orders.append(order);ship.order=order
        self.run.native['create_order']=order

    def tick(self):
        self.run.actions(self.run.scripts['CE_Raids'].xpath('//cue[@name="Lifecycle"]/actions')[0])

    def depart(self):
        for group in self.run.env['md'].CE_Raids.State.Groups.values():
            for ship in group.Ships:
                ship.dock=NIL
                group.Moves[ship].exists=False
        self.tick()

    def test_every_raid_composition_and_popup_commits_once(self):
        for tier,composition in [(1,['M']),(2,['M','M','S','S']),(3,['M','M','S','S','L','S','S'])]:
            self.setUp();self.setup_raids(tier)
            self.run.library('md.CE_Raids.Request')
            self.assertEqual([s.macro for s in self.created],composition)
            leader=next((ship for ship in self.created if ship.macro=='L'),self.created[0])
            self.assertIs(self.run.env['md'].CE_Raids.State.Groups[1].Leader,leader)
            self.assertFalse(any(order=='Plunder' for _,order in self.orders))
            self.assertEqual(len(self.messages),1)  # Mobilisation is reported before undocking.
            self.assertTrue(self.run.env['md'].CE_Raids.State.Groups[1].Announced)
            self.assertFalse(self.run.env['md'].CE_Raids.State.Groups[1].CombatStarted)
            self.depart()
            self.assertEqual([(s,o) for s,o in self.orders if o=='Plunder'],[(leader,'Plunder')])
            self.assertIs(leader.commander,NIL)
            for ship in self.created:
                if ship is leader:continue
                self.assertIs(ship.commander,leader)
                self.assertEqual(ship.assignment,'attack')
            self.assertTrue(self.run.env['IncidentSuccess'])
            self.assertEqual(len(self.messages),1)
            self.assertEqual(self.messages[0][1][2][3],len(composition))
            self.assertEqual(self.messages[0][1][2][2],(974201,240+tier,()))
            self.assertEqual(self.messages[0][1][2][4],(974201,247,(composition.count('M'),composition.count('S'),composition.count('L'))))
            for ship in self.created:
                self.assertIs(ship.pilot.ce_unrest_sector,self.sector)
                self.assertFalse(ship.pilot.ce_unrest_withdraw)
            self.assertEqual(self.u.NextRaid,3600)

    def test_departure_timeout_rolls_back_cooldowns_despite_early_warning(self):
        self.setup_raids(3);self.u.NextRaid=23;self.u.NextCapital=47
        self.run.library('md.CE_Raids.Request')
        group=self.run.env['md'].CE_Raids.State.Groups[1]
        self.assertEqual(group.Phase,'departing')
        self.assertEqual(group.Leader.units.transport.count,5)
        self.run.env['player'].age=601;self.tick()
        self.assertEqual(group.Phase,'withdrawing')
        self.assertEqual((self.u.NextRaid,self.u.NextCapital),(23,47))
        self.assertEqual(sum(m[0]=='popup' for m in self.messages),1)
        self.assertFalse(group.CombatStarted)
        self.assertEqual(len(self.messages),2)  # Mobilisation plus debug failure feedback.
        self.tick();self.assertEqual(len(self.messages),2)

    def test_capital_loadout_reserves_capacity_instead_of_aborting_after_one_drone(self):
        self.setup_raids(3)
        # Reproduce the old unrestricted loadout: nine other drones leave one slot.
        bay=DroneBay(transport=SimpleNamespace(count=0),other=9,maxcount=10)
        self.run.env['Probe']=Component(units=bay)
        self.run.native['add_units'](E.fromstring('<add_units object="$Probe" exact="5"/>'))
        self.assertEqual(bay.transport.count,1)
        self.run.library('md.CE_Raids.Request')
        group=self.run.env['md'].CE_Raids.State.Groups[1]
        self.assertTrue(self.run.env['IncidentSuccess'])
        self.assertEqual(group.Leader.units.transport.count,5)
        self.assertEqual(group.Leader.units.count,5)
        self.assertEqual(len(group.Ships),7)
        self.assertTrue(all(s.trueowner=='raiders' for s in group.Ships))
        self.depart()
        self.assertEqual(group.Phase,'raiding')
        self.assertTrue(all(s.commander is group.Leader for s in group.Ships if s is not group.Leader))
        self.assertTrue(all(s.pilot.ce_unrest_combat and s.armed for s in group.Ships))
        self.assertEqual(len(self.messages),1)

    def test_missing_cargo_drones_reject_capital_launch(self):
        self.setup_raids(3);self.run.native['add_units']=lambda n:None
        self.run.library('md.CE_Raids.Request')
        self.assertFalse(self.run.env['IncidentSuccess'])
        self.assertEqual(self.run.env['IncidentFailure'],(974201,236,()))
        self.assertTrue(self.run.env['md'].CE_Raids.State.Groups[1].Withdraw)
        self.assertFalse(any(m[0]=='popup' for m in self.messages))
        self.assertEqual(self.u.NextCapital,0)

    def test_departure_needs_every_survivor_and_survives_reload(self):
        from support import Runner
        self.setup_raids(3);self.run.library('md.CE_Raids.Request')
        group=self.run.env['md'].CE_Raids.State.Groups[1]
        for ship in group.Ships:
            if ship is not group.Leader:ship.dock=NIL;group.Moves[ship].exists=False
        self.tick();self.assertEqual(group.Phase,'departing');self.assertEqual(len(self.messages),1)
        # Reparse shipped code with the same persisted MD state/order references.
        self.run.scripts=type(self.run)().scripts
        self.run.env['player'].age=180
        self.depart();self.assertEqual(group.Phase,'raiding');self.assertEqual(len(self.messages),1)
        self.run.scripts=type(self.run)().scripts;self.tick();self.assertEqual(len(self.messages),1)
        self.assertEqual(group.End,self.run.env['player'].age+2700)

    def test_current_raid_resumes_without_replay_or_lifetime_extension(self):
        self.setup_raids(1);self.run.library('md.CE_Raids.Request');self.depart()
        group=self.run.env['md'].CE_Raids.State.Groups[1]
        end=group.End
        self.run.scripts=type(self.run)().scripts
        self.run.env['player'].age=120
        self.tick()
        self.assertTrue(group.CombatStarted)
        self.assertEqual(group.End,end)
        self.assertEqual(len(self.messages),1)
        self.run.env['RaidGroup']=group
        self.run.library('md.CE_RaidBehaviour.Begin')  # Resume following regroup.
        self.assertEqual(group.End,end)
        self.assertEqual(len(self.messages),1)

    def test_current_departing_save_announces_once_and_still_refunds_failure(self):
        self.setup_raids(3);self.u.NextRaid=23;self.u.NextCapital=47
        self.run.library('md.CE_Raids.Request')
        group=self.run.env['md'].CE_Raids.State.Groups[1]
        self.run.scripts=type(self.run)().scripts
        self.tick();self.tick()
        self.assertFalse(group.CombatStarted)
        self.assertTrue(group.Announced)
        self.assertEqual(len(self.messages),1)
        self.run.env['player'].age=601;self.tick()
        self.assertEqual((self.u.NextRaid,self.u.NextCapital),(23,47))
        self.assertEqual(sum(m[0]=='popup' for m in self.messages),1)

    def test_full_hold_or_lost_drones_withdraw_and_preserve_boarding(self):
        for cause in ('hold','drones','lifetime','relief'):
            self.setUp();self.setup_raids(3);self.run.library('md.CE_Raids.Request');self.depart()
            group=self.run.env['md'].CE_Raids.State.Groups[1]
            if cause=='hold':group.Leader.cargo.free.all=0
            elif cause=='drones':group.Leader.units.transport.count=0
            elif cause=='lifetime':self.run.env['player'].age=2701
            else:group.Debug=False;self.u.Stage=1
            group.Leader.boardingoperations=List([Component()])
            self.tick();self.assertEqual(group.Phase,'withdrawing')
            self.assertFalse(group.Leader.pilot.ce_unrest_withdraw)
            self.assertTrue(group.Leader.exists)
            self.assertEqual(len(self.messages),1)

    def test_route_replan_is_local_bounded_and_does_not_reannounce(self):
        self.setup_raids(2);self.run.library('md.CE_Raids.Request');self.depart()
        group=self.run.env['md'].CE_Raids.State.Groups[1];ship=group.Leader
        ship.pilot.ce_unrest_replan=True
        self.tick();count=len(self.orders)
        self.assertFalse(ship.armed);self.assertEqual(group.NextReplan,30)
        ship.pilot.ce_unrest_replan=True
        self.run.env['player'].age=5;self.tick();self.assertEqual(len(self.orders),count)
        ship.pilot.ce_unrest_replan=False
        self.depart();self.assertTrue(ship.armed);self.assertEqual(len(self.messages),1)
        ship.pilot.ce_unrest_replan=True;self.run.env['player'].age=31;self.tick()
        self.run.env['player'].age=212;self.tick();self.tick()
        self.assertEqual(group.Phase,'withdrawing')

    def test_failed_partial_raid_is_tracked_and_never_announced_as_success(self):
        self.setup_raids(3,failure_at=2)
        self.run.library('md.CE_Raids.Request')
        group=self.run.env['md'].CE_Raids.State.Groups[1]
        self.assertTrue(group.Withdraw);self.assertEqual(len(group.Ships),1)
        self.assertFalse(any(m[0]=='popup' for m in self.messages))
        self.assertEqual(self.u.NextRaid,0)

    def test_failed_launch_cleanup_survives_reload_and_respects_safety_guards(self):
        self.setup_raids(3,failure_at=2)
        self.run.library('md.CE_Raids.Request')
        groups=self.run.env['md'].CE_Raids.State.Groups
        group=groups[1];ship=group.Ships[1]
        self.assertEqual(group.Phase,'launching')
        self.run.scripts=type(self.run)().scripts
        ship.boardingoperations=List([Component()]);self.tick()
        self.assertEqual(self.orders,[])
        ship.boardingoperations=List();self.tick()
        self.assertEqual([order for _,order in self.orders],['Wait','MoveWait'])
        self.assertEqual(ship.trueowner,'civilian')
        self.run.env['player'].age=300
        for guard in ('visible','attacked','context','boarding'):
            ship.attention=1 if guard=='visible' else 0
            ship.lastattacktime=299 if guard=='attacked' else -1
            self.run.env['player'].entity.hascontext[ship]=guard=='context'
            ship.boardingoperations=List([Component()]) if guard=='boarding' else List()
            self.tick();self.assertTrue(ship.exists)
        ship.boardingoperations=List();self.tick()
        self.assertFalse(ship.exists)
        self.tick();self.assertEqual(len(groups),0)

    def test_failed_launch_cleanup_releases_captured_ship(self):
        self.setup_raids(3,failure_at=2)
        self.run.library('md.CE_Raids.Request');self.tick()
        ship=self.created[0];ship.isplayerowned=True
        self.tick()
        self.assertTrue(ship.exists)
        self.assertNotIn('ce_unrest_withdraw',ship.pilot)
        self.assertEqual(len(self.run.env['md'].CE_Raids.State.Groups),0)

    def test_capital_launch_uses_seven_distinct_free_berths(self):
        self.setup_raids(3)
        self.docks={size:self.docks[size][:count] for size,count in [('M',2),('S',4),('L',1)]}
        self.run.library('md.CE_Raids.Request')
        self.assertTrue(self.run.env['IncidentSuccess'])
        self.assertEqual(len({ship.dock for ship in self.created}),7)

    def test_insufficient_or_occupied_berths_reject_before_spawning(self):
        for shortage in ('one_m_berth','occupied_l_pier'):
            self.setUp();self.setup_raids(3)
            if shortage=='one_m_berth':self.docks['M']=self.docks['M'][:1]
            else:
                self.docks['L']=self.docks['L'][:1]
                self.docks['L'][0].occupied=True
            self.run.library('md.CE_Raids.Request')
            self.assertFalse(self.run.env['IncidentSuccess'])
            self.assertEqual(self.created,[])
            self.assertEqual(len(self.run.env['md'].CE_Raids.State.Groups),0)
            self.assertEqual(self.run.env['IncidentFailure'],(974201,232,()))
            self.assertEqual(self.run.env['IncidentKind'],'raid_3')
            self.assertEqual(self.u.NextRaid,0)

    def test_harness_rejects_reported_native_failures(self):
        self.setup_raids(1);self.run.library('md.CE_Raids.Request')
        self.run.env['RaidShip']=self.created[0]
        with self.assertRaisesRegex(ValueError,'entity blackboard'):
            self.run.set('$RaidShip.$ce_unrest_sector',self.sector)
        with self.assertRaisesRegex(ValueError,'constant integer'):
            self.run.expr('{974201,240 + $RaidTier}')

    def test_ai_guards_read_pilot_markers_and_keep_player_weighting(self):
        self.setup_raids(1);self.run.library('md.CE_Raids.Request')
        ship=self.created[0]
        other_sector=Component()
        self.run.env.update(this=Table(ship=ship),destination=other_sector)
        other_sector.exists=True
        route=E.parse(str(MOD/'aiscripts/move.generic.xml')).xpath('//add')[0]
        gate=route.find('do_if')
        self.assertTrue(self.run.expr(gate.get('value')))
        self.assertTrue(self.run.expr(gate.find('do_if').get('value')))
        self.run.env['destination']=self.sector
        self.assertFalse(self.run.expr(gate.find('do_if').get('value')))
        def trader(player_owned, sector):
            return Component(sector=sector,primarypurpose='trade',dock=NIL,
                             cargo=SimpleNamespace(count=10),pilot=Component(),isplayerowned=player_owned)
        player_trader=trader(True,self.sector);npc_trader=trader(False,self.sector)
        self.run.env.update(plunder=True,purpose=Table(trade='trade'),
                            detected=List([player_trader,npc_trader,trader(True,other_sector)]))
        self.run.native['shuffle_list']=lambda n:None
        patch=E.parse(str(MOD/'aiscripts/move.seekenemies.xml')).xpath('//add')[0]
        self.run.actions(patch)
        self.assertEqual(list(self.run.env['detected']),[player_trader]*3+[npc_trader])
        ship.pilot.ce_unrest_withdraw=True
        self.run.actions(patch)
        self.assertEqual(list(self.run.env['detected']),[])
        ship.trueowner='player'
        self.assertFalse(self.run.expr(gate.get('value')))

    def test_five_capital_groups_per_hub_and_no_global_limit(self):
        self.setup_raids(3)
        for _ in range(5):
            self.run.library('md.CE_Raids.Request')
            self.assertTrue(self.run.env['IncidentSuccess'])
            self.assertEqual(self.run.env['RaidTier'],3)
        groups=self.run.env['md'].CE_Raids.State.Groups
        groups[1].Withdraw=True  # Withdrawing groups still occupy a slot.
        self.run.library('md.CE_Raids.Request')
        self.assertFalse(self.run.env['IncidentSuccess'])
        self.assertEqual(len(self.created),35)
        self.assertEqual(len(groups),5)
        self.r.Hub=Component(exists=True,iswreck=False,owner='civilian',sector=self.sector,knownname='Other hub')
        for _ in range(5):
            self.run.library('md.CE_Raids.Request')
            self.assertTrue(self.run.env['IncidentSuccess'])
            self.assertEqual(self.run.env['RaidTier'],3)
        self.assertEqual(len(groups),10)
        self.assertEqual(len(self.created),70)

    def test_clear_withdraws_all_current_local_groups(self):
        self.setup_raids(1);self.run.library('md.CE_Raids.Request')
        state=self.run.env['md'].CE_Raids.State
        first=state.Groups[1]
        self.run.library('md.CE_Raids.Ensure')
        self.assertIs(first.Hub,self.hub)
        for _ in range(4):self.run.library('md.CE_Raids.Request')
        self.assertEqual(len(state.Groups),5)
        self.run.library('md.CE_Raids.Request')
        self.assertFalse(self.run.env['IncidentSuccess'])
        other=Table(Hub=Component(),Withdraw=False)
        state.Groups[99]=other
        self.run.env['DebugCommand']='clear'
        self.run.library('md.CE_DebugUnrest.Dispatch')
        self.assertTrue(all(group.Withdraw for group in state.Groups.values() if group is not other))
        self.assertFalse(other.Withdraw)
        self.assertIs(state.Groups[1],first)

    def test_normal_capital_cooldown_still_falls_back_to_strong(self):
        self.setup_raids(3);self.run.env['IncidentDebug']=False
        self.u.NextCapital=10000
        self.run.library('md.CE_Raids.Request')
        self.assertTrue(self.run.env['IncidentSuccess'])
        self.assertEqual(self.run.env['RaidTier'],2)
        self.assertEqual([ship.macro for ship in self.created],['M','M','S','S'])

    def test_raid_cleanup_retains_boarding_and_releases_captured_ships(self):
        self.setup_raids(1);self.run.library('md.CE_Raids.Request')
        ship=self.created[0];group=self.run.env['md'].CE_Raids.State.Groups[1]
        group.Withdraw=True;ship.boardingoperations=List([Component()])
        self.run.env.update(attention=Table(visible=1))
        self.run.env['player'].entity=Table(hascontext=Table())
        removed=[]
        self.run.native['destroy_object']=lambda n:removed.append(self.run.expr(n.get('object')))
        self.run.native['remove_object_commander']=lambda n:None
        self.run.native['cancel_order']=lambda n:None
        actions=self.run.scripts['CE_Raids'].xpath('//cue[@name="Lifecycle"]/actions')[0]
        self.run.actions(actions);self.assertEqual(removed,[]);self.assertEqual(len(group.Ships),1)
        ship.isplayerowned=True;ship.trueowner='player'
        self.run.actions(actions);self.assertEqual(removed,[]);self.assertEqual(len(self.run.env['md'].CE_Raids.State.Groups),0)


if __name__=='__main__':unittest.main()
