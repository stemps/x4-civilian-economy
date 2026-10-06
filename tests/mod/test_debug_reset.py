"""Reset lifecycle and authorization contracts. Native destruction is asynchronous."""
import unittest
from support import Runner, Table, List, Component, NIL, definitions


class ResetTests(unittest.TestCase):
    def setUp(self):
        self.r = r = Runner()
        self.sector = Component(exists=True, isclass=Table(sector=True), macro=Table(id='test_sector_macro'))
        self.builder = Component(exists=True, owner='npc')
        self.storage = Component(exists=True, owner='civilian', isclass=Table(ship=False),
            builds=Table(queued=List(['queued']), inprogress=List(['active'])),
            buildmodule=Component(constructionvessel=self.builder))
        self.hub = Component(exists=True, owner='civilian', isclass=Table(ship=False), buildstorage=self.storage)
        self.cue = Component(exists=True)
        self.offer = Component(exists=True)
        self.record = Table(Hub=self.hub, LayoutPending=True, LayoutCue=self.cue,
            Transfers=Table(old='deal'), Wares=Table(food=Table(Offer=self.offer)),
            Level=10, GrowthSeconds=900, PopulationOverride=5000000000, Unrest=Table(Stage=4))
        self.raid = Component(exists=True, trueowner='raid', isclass=Table(ship=True), pilot=NIL, orders=List())
        self.captured = Component(exists=True, trueowner='player', isclass=Table(ship=True), pilot=NIL)
        r.env.update(player=Table(age=100, money=12345, entity=Table(hascontext=Table())),
            faction=Table(civilian='civilian', ownerless='ownerless', ce_unrest='raid'),
            **{'class':Table(ship_s='s',ship_m='m',ship_l='l',ship_xl='xl')})
        self.controller = r.env['md'].CE_CivilianHub.Init
        self.controller.update(Registry=Table({self.sector:self.record}),PopulationRequest=7,
            SectorProfiles=Table(old=True),RaceProfiles=Table(old=True),Hubs=List([self.hub]))
        r.env['md'].CE_Settings.State.update(Debug=True,DemandMultiplier=2,TimeMultiplier=3)
        r.env['md'].CE_Placement.State.Sites=Table({self.hub:Table(Failures=20)})
        r.env['md'].CE_Raids.State.Groups=Table(a=Table(Hub=self.hub, Ships=List([self.raid,self.captured])))
        self.sent=[];self.removed_builds=[];self.detached=[];self.signals=[];self.notifications=[]
        self.visitors=Table()
        r.native.update(destroy_object=self.destroy, find_dockingbay=self.find,
            cancel_cue=self.cancel, clear_group=lambda n:r.expr(n.get('group')).clear(),
            update_trade=lambda n:None, remove_build=lambda n:self.removed_builds.append(r.expr(n.get('build'))),
            disengage_construction_vessel=lambda n:self.detached.append(r.expr(n.get('object'))),
            signal_cue_instantly=lambda n:self.signals.append(n.get('cue')),
            show_notification=lambda n:self.notifications.append(n.get('text')))
        r.native['set_build_plot']=lambda n:None
        self.call('Publish')
        self.state=r.env['md'].CE_DebugReset.State

    def call(self,name): self.r.library('md.CE_DebugReset.'+name)
    def command(self,cmd,context=None):
        self.r.env['event']=Table(param2=cmd,param3=context or self.sector)
        self.call('Request')
    def start(self):
        self.command('arm:1');self.command('confirm:2')
    def find(self,n):
        dock=Table(docked=self.visitors[self.r.expr(n.get('object'))] or List())
        self.r.set(n.get('name'),List([dock]))
    def destroy(self,n): self.sent.append(self.r.expr(n.get('object')))
    def cancel(self,n):
        obj=self.r.expr(n.get('cue'));self.assertTrue(obj.exists);obj.exists=False
    def pump(self): self.call('Pump')

    def test_confirmation_debug_context_expiry_and_replay(self):
        self.command('confirm:1');self.assertFalse(self.state.Busy)
        self.command('arm:1',Component(exists=True,isclass=Table(sector=False)))
        self.assertEqual(self.state.Token,1)
        self.r.env['md'].CE_Settings.State.Debug=False
        self.command('arm:1');self.assertEqual(self.state.Token,1)
        self.r.env['md'].CE_Settings.State.Debug=True
        self.command('arm:1');self.command('arm:1');self.assertEqual(self.state.Token,2)
        self.r.env['player'].age=131
        self.command('confirm:2');self.assertFalse(self.state.Busy)
        self.r.actions(self.r.scripts['CE_DebugReset'].xpath('//cue[@name="Tick"]/actions')[0])
        self.assertEqual(self.state.Phase,'idle')
        self.command('arm:3');self.command('confirm:4');count=len(self.sent)
        self.command('confirm:4');self.assertEqual(len(self.sent),count)

    def test_clears_state_cancels_work_preserves_settings_finances_and_foreign_ships(self):
        self.start()
        self.assertTrue(self.state.Busy);self.assertFalse(self.cue.exists)
        self.assertFalse(self.record.LayoutPending);self.assertIs(self.record.Hub,NIL)
        self.assertEqual(self.record.Transfers.count,0)
        self.assertEqual(self.controller.Registry.count,0)
        self.assertEqual(self.controller.PopulationRequest,8)
        self.assertEqual(self.controller.SectorProfiles.count,0)
        self.assertEqual(self.controller.RaceProfiles.count,0)
        self.assertEqual(self.r.env['md'].CE_Placement.State.Sites.count,0)
        self.assertEqual(self.removed_builds,['queued','active'])
        self.assertEqual(self.detached,[self.storage.buildmodule])
        self.assertEqual(set(self.sent),{self.hub,self.storage,self.raid})
        self.assertTrue(self.captured.exists);self.assertTrue(self.builder.exists)
        self.assertEqual(self.r.env['player'].money,12345)
        self.assertEqual(self.r.env['md'].CE_Settings.State.DemandMultiplier,2)
        self.assertEqual(self.r.env['md'].CE_Raids.State.Groups.count,0)
        self.assertEqual(self.signals,[])

    def test_designated_station_is_detached_not_destroyed_and_loses_old_offers(self):
        removed=[]
        self.r.native['remove_trade_offer']=lambda n:removed.append((self.r.expr(n.get('object')),self.r.expr(n.get('tradeoffer'))))
        self.record.External=True
        self.start()
        self.assertEqual(removed,[(self.hub,self.offer)])
        self.assertEqual(set(self.sent),{self.raid})
        self.assertEqual(self.removed_builds,[])
        self.assertEqual(self.detached,[])
        self.assertTrue(self.hub.exists)
        self.assertIs(self.record.Hub,NIL)
        self.assertEqual(self.controller.Registry.count,0)

    def test_removal_must_be_confirmed_before_reinitializing_and_finishing(self):
        self.start();self.pump();self.assertEqual(len(self.sent),3)
        self.r.env['player'].age=131;self.pump()
        self.assertTrue(self.state.Blocked);self.assertEqual(self.signals,[])
        for obj in self.sent:obj.exists=False
        self.pump();self.assertEqual(self.state.Phase,'initializing')
        self.assertEqual(self.signals,['md.CE_CivilianHub.ResetRebuild'])
        self.assertTrue(self.state.Busy)
        self.call('Finish');self.assertFalse(self.state.Busy)
        self.assertEqual(self.state.Phase,'complete')

    def test_visitors_and_player_block_destruction(self):
        self.visitors[self.hub]=List([self.captured])
        self.r.env['player'].entity.hascontext[self.storage]=True
        self.start();self.assertEqual(self.sent,[self.raid])
        self.visitors[self.hub]=List();self.r.env['player'].entity.hascontext[self.storage]=False
        self.pump();self.assertEqual(set(self.sent),{self.hub,self.storage,self.raid})

    def test_unfinished_docking_bay_without_occupant_list_is_safe_to_inspect(self):
        self.r.native['find_dockingbay']=lambda n:self.r.set(n.get('name'),List([Table(docked=NIL)]))
        self.start()
        self.assertEqual(set(self.sent),{self.hub,self.storage,self.raid})

    def test_ownership_change_before_destruction_preserves_object(self):
        self.visitors[self.hub]=List([self.captured]);self.start()
        self.hub.owner='player';self.visitors[self.hub]=List();self.pump()
        self.assertNotIn(self.hub,self.sent)
        self.assertFalse(any(item.Object is self.hub for item in self.state.Pending))

    def test_missing_hubs_and_expired_workers_are_safe(self):
        self.hub.exists=False;self.cue.exists=False;self.start()
        self.assertEqual(self.sent,[self.raid])

    def test_foreign_hub_and_build_storage_are_not_removed(self):
        self.hub.owner='player';self.start()
        self.assertEqual(self.sent,[self.raid]);self.assertEqual(self.removed_builds,[])
        self.setUp();self.storage.owner='player';self.start()
        self.assertNotIn(self.storage,self.sent);self.assertEqual(self.removed_builds,[])

    def test_reload_preserves_queue_and_reissues_only_population_request(self):
        self.start()
        actions=self.r.scripts['CE_DebugReset'].xpath('//cue[@name="Reload"]/actions')[0]
        self.r.actions(actions);self.assertEqual(len(self.sent),3)
        for obj in self.sent:obj.exists=False
        self.pump();self.r.actions(actions)
        self.assertEqual(self.signals,['md.CE_CivilianHub.ResetRebuild']*2)
        self.assertTrue(self.state.Busy)

    def test_old_population_response_and_debug_cues_cannot_mutate_during_removal(self):
        self.start()
        self.r.env.update(Registry=self.controller.Registry,PopulationRequest=8,
            event=Table(param2='create_hub_5b',param3=self.sector))
        self.r.env['player'].entity.ce_population_response=List([7,List()])
        for cue in ['PopulationReceived','LevelTick','Reload','TestingCommand','SectorTestingCommand']:
            self.r.actions(self.r.tree.xpath('//cue[@name=$name]/actions',name=cue)[0])
        self.assertEqual(self.controller.Registry.count,0)
        self.assertEqual(self.signals,[])

    def test_matching_population_response_rebuilds_fresh_records_with_normal_eligibility(self):
        self.start()
        for obj in self.sent:obj.exists=False
        self.pump()
        r=self.r;definitions(r)
        r.env['md'].CE_CivilianHub.Init=self.controller
        self.sector.owner=Table(primaryrace=r.env['lookup'].race.list[1])
        empty=Component(exists=True,isclass=Table(sector=True),owner=self.sector.owner,macro=Table(id='empty_sector_macro'))
        r.env.update(Registry=self.controller.Registry, SectorProfiles=self.controller.SectorProfiles,
            RaceProfiles=self.controller.RaceProfiles, PopulationRequest=8, PopulationApplied=7)
        r.env['player'].galaxy='galaxy'
        r.native['find_sector']=lambda n:r.set(n.get('name'),List([self.sector,empty]))
        r.native['raise_lua_event']=lambda n:None
        r.native['add_to_group']=lambda n:None
        def create(n):
            r.set(n.get('name'),Component(exists=True,iswreck=False,owner='civilian',
                sector=r.env['Sector'],isclass=Table(container=False),buildstorage=NIL))
        r.native['create_station']=create
        for name in ('FundAccounts','QueueExpansion','AssignBuilder','RenameHub','UpdateHub'):
            r.stubs[name]=lambda:None
        r.actions(r.tree.xpath('//cue[@name="ResetRebuild"]/actions')[0])
        self.assertEqual(r.env['player'].entity.ce_population_request[1],9)
        r.env['player'].entity.ce_population_response=List([8,List([List([self.sector,5000000000])])])
        response=r.tree.xpath('//cue[@name="PopulationReceived"]/actions')[0]
        r.actions(response);self.assertTrue(self.state.Busy)
        self.assertEqual(self.controller.Registry.count,0)
        r.env['player'].entity.ce_population_response=List([9,List([List([self.sector,100000000]),List([empty,0])])])
        r.actions(response)
        fresh=self.controller.Registry[self.sector]
        self.assertIsNot(fresh,self.record)
        self.assertEqual((fresh.Level,fresh.Target,fresh.GrowthSeconds),(1,0,0))
        self.assertIs(fresh.PopulationOverride,NIL);self.assertEqual(fresh.Population,100000000)
        self.assertEqual(fresh.Unrest.Stage,0);self.assertTrue(fresh.Hub.exists)
        self.assertIs(self.controller.Registry[empty],NIL)
        self.assertFalse(self.state.Busy)
        same=fresh.Hub;r.actions(response)
        self.assertIs(self.controller.Registry[self.sector].Hub,same)



if __name__ == '__main__': unittest.main()
