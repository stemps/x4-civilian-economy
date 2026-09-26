"""Execute shipped unrest actions. Native ship/combat behavior is not simulated."""
import copy
import unittest
from lxml import etree as E
from support import Ware, ROOT, REF
from support_unrest import UnrestFixture


class UnrestTests(UnrestFixture, unittest.TestCase):
    def test_initial_grace_and_no_retroactive_shortage(self):
        self.add('food')
        self.advance(60)
        self.assertEqual(self.u.Grace,7260)
        self.advance(7200)
        self.assertEqual(self.u.Score,0)
        self.advance(3600)
        self.assertEqual(self.u.Score,25)

    def test_depletion_mid_interval_and_partial_deliveries(self):
        ware=self.add('food',reserve=1800)
        self.ready()
        self.u.Scores[1]=30
        self.advance(3600)
        self.assertEqual(self.u.Score,17.5)  # 30 - 25 supplied + 12.5 missing
        self.r.Wares[ware].Reserve=1
        self.advance(3600)
        self.assertAlmostEqual(self.u.Score,17.5+25-75/3600)

    def test_worst_ware_does_not_sum_multiple_shortages(self):
        self.add('food');self.add('water');self.ready()
        self.advance(3600)
        self.assertEqual(self.u.Score,25)
        self.assertEqual(set(self.u.Causes),{'food','water'})

    def test_supplied_time_at_zero_cannot_prepay_later_deprivation(self):
        self.add('food',reserve=1800);self.ready()
        self.advance(3600)
        self.assertEqual(self.u.Score,12.5)

    def test_disabled_rates_suspend_recovery_as_well(self):
        self.add('food',rate=0);self.ready();self.u.Scores[1]=50;self.u.Score=50
        self.advance(3600)
        self.assertEqual(self.u.Score,50)

    def test_industry_and_luxury_cannot_trigger_raids(self):
        self.add('metal',2);self.add('luxury',3);self.ready()
        self.advance(36000)
        self.assertEqual(self.u.Score,45)
        self.assertEqual(self.u.Stage,1)

    def test_new_ware_grace_survives_reload(self):
        self.add('food',reserve=7200);self.ready()
        self.advance(60)
        self.add('medicine')
        self.advance(60)
        self.assertEqual(self.u.Wares[Ware('medicine')],3720)
        saved=copy.deepcopy(self.r)
        self.run.env['R']=saved
        self.run.library('md.CE_Unrest.Ensure')
        self.assertEqual(saved.Unrest.Wares[Ware('medicine')],3720)
        self.assertEqual(saved.Unrest.Score,0)

    def test_disabled_nonoperational_and_below_level_do_not_accrue(self):
        self.add('food');self.ready()
        for key,value in [('PauseOffers',True),('Operational',False),('Level',4)]:
            old=self.r[key];self.r[key]=value
            self.advance(3600)
            self.assertEqual(self.u.Score,0)
            self.r[key]=old
        self.advance(3600)
        self.assertEqual(self.u.Score,25)

    def test_hysteresis_and_critical_warning_once(self):
        self.run.env['player']['age']=100
        for score,stage in [(60,2),(56,2),(54,1),(95,4),(95,4),(94,4),(89,3)]:
            self.score(score);self.assertEqual(self.u.Stage,stage)
        self.assertEqual(len(self.messages),1)
        self.assertEqual(self.u.CriticalSince,0)
        self.score(95)
        self.assertEqual(len(self.messages),2)

    def test_tax_changes_recovery_and_acquisition_without_payment_toggle(self):
        self.run.env['md'].CE_Settings.State.update(TaxPercent=15,TaxNotifications=False)
        tax=lambda:self.run.library('md.CE_UnrestNotifications.Tax')
        tax();self.assertEqual(self.messages,[])
        self.score(60);tax();tax()
        self.assertEqual(self.messages[0],('ticker',(974201,201,('Sector',50,7.5))))
        self.score(80);tax()
        self.score(95);tax()
        self.assertEqual(sum(m[0]=='ticker' for m in self.messages),2)
        self.sector.isplayerowned=False;tax()
        self.sector.isplayerowned=True;tax()
        self.assertEqual(sum(m[0]=='ticker' for m in self.messages),3)
        self.score(0);tax();tax()
        self.assertEqual(self.messages[-2],('ticker',(974201,202,('Sector',15))))

    def test_debug_exact_dispatch_shared_pipeline_and_cooldowns(self):
        seen=[]
        self.run.stubs['md.CE_Raids.Request']=lambda:seen.append(('raid',self.run.env['IncidentTier'],self.run.env['IncidentDebug']))
        self.run.stubs['md.CE_Sabotage.Request']=lambda:seen.append(('sabotage',self.run.env['IncidentKind'],self.run.env['IncidentDebug']))
        for command in ['raid_1','raid_2','raid_3','production','turrets','cargo','shields','destroy']:
            self.run.env['DebugCommand']=command
            self.run.library('md.CE_DebugUnrest.Dispatch')
        self.assertEqual(seen[:3],[('raid',i,True) for i in (1,2,3)])
        self.assertEqual([x[1] for x in seen[3:]],['production','turrets','cargo','shields','destroy'])
        self.assertEqual(self.u.Score,0)
        self.run.env['DebugCommand']='cooldowns'
        self.u.NextRaid=10000
        self.run.library('md.CE_DebugUnrest.Dispatch')
        self.assertEqual(self.u.NextRaid,0)

    def test_native_patch_selectors_resolve_once(self):
        for name in ['move.generic','move.seekenemies']:
            base=E.parse(str(REF/'aiscripts'/f'{name}.xml'))
            patch=E.parse(str(ROOT/'aiscripts'/f'{name}.xml'))
            for change in patch.getroot():
                if isinstance(change.tag,str):self.assertEqual(len(base.xpath(change.get('sel'))),1,name)

    def test_destruction_and_raid_cleanup_are_scoped(self):
        sabotage=self.run.scripts['CE_Sabotage']
        self.assertEqual(sabotage.xpath('//destroy_object/@object'),['$Module'])
        confirm=sabotage.xpath('//cue[@name="Confirm"]/actions/do_if')[0]
        self.assertIn('$Module.iswreck',confirm.get('value'))
        self.assertTrue(confirm.xpath('.//include_actions[@ref="md.CE_UnrestNotifications.Popup"]'))
        raids=self.run.scripts['CE_Raids']
        cleanup=raids.xpath('//destroy_object')[0]
        guards=' '.join(cleanup.xpath('ancestor::*/@value'))
        self.assertIn('boardingoperations',guards)
        self.assertIn('lastattacktime',guards)
        self.assertIn('attention.visible',guards)


if __name__=='__main__':unittest.main()
