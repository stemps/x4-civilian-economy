"""Execute CE hook guards, not the native movement/combat engine."""
import unittest
from types import SimpleNamespace
from lxml import etree as E
from support import Runner, Table, List, Component, Ware, NIL, ROOT, REF

class RaidAITests(unittest.TestCase):
    def setUp(self):
        self.run=Runner();self.sector=Component(exists=True)
        self.ship=Component(trueowner='ce',owner='disguise',pilot=Component(
            ce_unrest_version=2,ce_unrest_sector=self.sector,ce_unrest_combat=True,
            ce_unrest_replan=False,ce_unrest_withdraw=False),cargo=Table())
        self.run.env.update(this=Table(ship=self.ship,assignedcontrolled=self.ship),
                            faction=Table(ce_unrest='ce'),waretransport=Table(container='container'))
        self.run.native['cease_fire']=lambda n:None
        self.run.native['set_turrets_armed']=lambda n:setattr(self.ship,'armed',False)

    def patch(self,name):return E.parse(str(ROOT/'aiscripts'/name))
    def target(self,kind='ship',container=NIL):
        return Component(exists=True,sector=self.sector,container=container,
                         isclass=Table(ship=kind=='ship',station=kind=='station',missile=kind=='missile'))

    def test_loaded_player_fighter_exception_empty_exclusion_and_weighting(self):
        fighter=self.target();npc=self.target();empty=self.target();other_fighter=self.target()
        for ship in (fighter,npc,empty,other_fighter):
            ship.primarypurpose='fight';ship.isplayerowned=True;ship.dock=NIL;ship.pilot=Component()
            ship.cargo=SimpleNamespace(count=1)
        npc.primarypurpose='trade';npc.isplayerowned=False;empty.cargo.count=0
        self.run.env['player'].occupiedship=fighter
        self.run.env.update(plunder=True,purpose=Table(trade='trade'),detected=List([fighter,npc,empty,other_fighter]))
        self.run.native['shuffle_list']=lambda n:None
        self.run.actions(self.patch('move.seekenemies.xml').getroot()[0])
        self.assertEqual(list(self.run.env['detected']),[fighter]*3+[npc])

    def test_cheap_container_goods_qualify_only_for_ce(self):
        guard=self.patch('order.plunder.xml').xpath('//replace[contains(@sel,"evalware")]/text()')[0]
        for name in ('water','foodrations','energycells'):
            ware=Ware(name);ware.averageprice=10;ware.hastag=Table(minable=False)
            self.ship.cargo[ware]=SimpleNamespace(free=100)
            self.run.env.update(evalware=ware,pricethreshold=1000)
            self.assertTrue(self.run.expr(guard))
            self.ship.trueowner='other';self.assertFalse(self.run.expr(guard));self.ship.trueowner='ce'
        ware.waretransport='solid';self.assertFalse(self.run.expr(guard))

    def test_added_waits_have_new_script_versions_for_saved_resume_mapping(self):
        for name in ('move.generic.xml','order.fight.attack.object.xml','order.plunder.xml'):
            native=E.parse(str(REF/'aiscripts'/name))
            patch=self.patch(name)
            version=int(patch.xpath('/diff/replace[@sel="/aiscript/@version"]/text()')[0])
            self.assertGreater(version,int(native.getroot().get('version')))
            waits=patch.xpath('//wait')
            self.assertTrue(waits)
            for wait in waits:
                self.assertEqual(int(wait.get('sinceversion')),version)

    def test_station_combat_is_native_but_departure_and_sector_guards_remain(self):
        guard=self.patch('order.fight.attack.object.xml').xpath('/diff/add/do_if')[0].get('value')
        for target in (self.target(),self.target('station'),self.target('module',self.target('station'))):
            self.run.env['primarytarget']=target
            self.assertFalse(self.run.expr(guard))
            self.ship.pilot.ce_unrest_combat=False
            self.assertTrue(self.run.expr(guard))
            self.ship.pilot.ce_unrest_combat=True
            target.sector=Component()
            self.assertTrue(self.run.expr(guard))
        for path in (ROOT/'aiscripts').glob('*.xml'):
            tree=E.parse(str(path))
            self.assertFalse(tree.xpath('//shoot_at | //apply_attackstrength | //set_turret_targets'))
            self.assertFalse(tree.xpath('//*[@ref="CE_RaidStationAttacked" or @ref="CE_RaidFilterTargets"]'))
        self.assertFalse((ROOT/'aiscripts/interrupt.attacked.xml').exists())

    def test_destination_rejection_waits_and_signals_controller_before_gate(self):
        class Returned(Exception):pass
        waits=[]
        self.run.native['wait']=lambda n:waits.append(self.run.expr(n.get('exact')))
        def returned(n):raise Returned()
        self.run.native['return']=returned
        patch=self.patch('move.generic.xml');guards=patch.xpath('/diff/add')
        self.run.env['destination']=Component(exists=True,sector=Component())
        with self.assertRaises(Returned):self.run.actions(guards[0])
        self.assertEqual(waits,[5]);self.assertTrue(self.ship.pilot.ce_unrest_replan)
        self.run.env['destination']=self.sector;self.run.actions(guards[0])
        self.assertEqual(waits,[5])
        self.run.env['gatedestination']=Component(sector=Component())
        with self.assertRaises(Returned):self.run.actions(guards[1])
        self.assertFalse((ROOT/'aiscripts/move.gate.xml').exists())
        self.ship.trueowner='player';self.run.actions(guards[1]);self.assertEqual(waits,[5,5])

    def test_resupply_disguise_and_offload_hooks_use_true_owner(self):
        guard=self.patch('interrupt.restock.xml').xpath('//check_value')[0].get('value')
        self.assertFalse(self.run.expr(guard))
        disguise=self.patch('order.plunder.xml').xpath('//replace[contains(@sel,"policefaction")]/text()')[0]
        self.run.env['targetzone']=Table(policefaction='argon')
        self.assertFalse(self.run.expr(disguise))
        self.ship.trueowner='other'
        self.assertTrue(self.run.expr(guard));self.assertTrue(self.run.expr(disguise))

if __name__=='__main__':unittest.main()
