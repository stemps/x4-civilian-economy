"""Execute the shipped resolver against vanilla recipes and conversion fixtures.

Native race.workforce.resources is mocked with extracted workunit recipes; this
does not assert that the engine bridge or a particular overhaul has been tested.
"""
from test_prototype import Runner, Table, List, Ware, NIL, REF, definitions, E, Component
import unittest


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.run = Runner()
        definitions(self.run)
        self.r = Table(Level=1, Target=0, Operational=True, Wares=Table(),
                       Transfers=Table(), Hub=NIL, Factor=1, Population=8524100000,
                       PauseOffers=False, PlotReady=False, TestUpgrade=False)
        self.run.env['R'] = self.r

    def ware(self, name, group='food', transport='container'):
        ware = Ware(name)
        ware.group = Table(id=group)
        ware.waretransport = transport
        self.run.env['lookup'].ware.list.append(ware)
        return ware

    def race(self, name, wares):
        race = Table(id=name, workforce=Table(resources=List(wares)))
        self.run.env['lookup'].race.list.append(race)
        return race

    def select(self, race):
        self.run.env['Sector'] = Component(owner=Table(primaryrace=race))

    def apply(self, level=1):
        self.r['Level'] = level
        self.run.library('RefreshProfile')
        self.run.library('ApplyLevel')
        return {w for w, state in self.r.Wares.items() if state.Rate > 0}

    def configure(self, statements):
        actions = self.run.profiles.xpath('//library[@name="Configure"]/actions')[0]
        for statement in statements:
            actions.append(E.fromstring(statement))

    def test_mock_rejects_unprefixed_profile_keys_and_preserves_literal_sigil(self):
        self.run.env['ProfileFoods']=Table()
        self.assertEqual(self.run.expr("'$' + 'argon'"),'$argon')
        with self.assertRaisesRegex(ValueError,'string table keys'):
            self.run.set("$ProfileFoods.{'argon'}",List())
        self.run.set("$ProfileFoods.{'$' + 'argon'}",List(['foodrations']))
        self.assertEqual(self.run.expr("$ProfileFoods.{'$argon'}"),['foodrations'])

    def test_empty_saved_definitions_recover_with_existing_demand_and_counters(self):
        self.apply()
        old=self.r.Wares['foodrations']
        old.update(Reserve=50,Delivered=25,Paid=1000)
        self.r['Definitions']=List()
        self.run.library('RefreshProfile')
        self.run.library('PublishDiagnostics')
        self.assertEqual([row[1] for row in self.r.Snapshot[9]],['foodrations','water'])
        self.assertEqual((old.Reserve,old.Delivered,old.Paid),(50,25,1000))

    def test_each_vanilla_race_and_dlc_food(self):
        expected = {'argon': {'foodrations'}, 'paranid': {'sojahusk'},
                    'teladi': {'nostropoil'}, 'split': {'cheltmeat', 'scruffinfruits'},
                    'boron': {'bofu', 'water'}, 'terran': {'terranmre'}}
        for name, staples in expected.items():
            with self.subTest(race=name):
                self.setUp()
                if name in ('split', 'boron', 'terran'):
                    tree = E.parse(str(REF / 'extensions' / ('ego_dlc_' + name) / 'libraries/wares.xml'))
                    for node in tree.xpath('//ware[@id][price]'):
                        self.ware(node.get('id'), node.get('group', ''), node.get('transport'))
                    by_id = {w.id: w for w in self.run.env['lookup'].ware.list}
                    recipe = tree.xpath('//add[@sel=$sel]/production/primary/ware',
                                        sel="/wares/ware[@id='workunit_busy']")
                    self.assertTrue(recipe, name)
                    race = self.race(name, [by_id[n.get('ware')] for n in recipe])
                else:
                    race = next(r for r in self.run.env['lookup'].race.list if r.id == name)
                self.select(race)
                self.assertEqual(self.apply(), staples | {'water'})
                self.assertIn('medicalsupplies', self.apply(3))
                active = self.apply(8)
                self.assertIn('foodrations', active)
                self.assertIn('sojahusk', active)
                self.assertIn('nostropoil', active)
                self.assertEqual(len(self.r.Definitions), len({d[1] for d in self.r.Definitions}))
                if name == 'terran':
                    self.assertIn('computronicsubstrate', active)
                    self.assertNotIn('refinedmetals', active)

    def test_new_race_replaced_and_extended_staples_and_medicine(self):
        a, b = self.ware('algae'), self.ware('grain', 'agricultural')
        med = self.ware('alienmedicine', 'pharmaceutical')
        custom = self.race('custom', [a, b, med])
        self.select(custom)
        self.assertEqual(self.apply(), {'algae', 'grain', 'water'})
        self.assertIn('alienmedicine', self.apply(3))
        self.assertNotIn('medicalsupplies', self.apply(3))
        self.assertNotIn('foodrations', self.apply(7))
        self.assertIn('foodrations', self.apply(8))
        self.assertEqual(self.r.Wares['algae'].Rate, 2000 * 1.25 ** 7)

    def test_foreign_only_at_eight_shared_staples_are_not_duplicated(self):
        food = self.run.env['ware'].foodrations
        self.race('cousins', [food])
        foreign = self.ware('foreignfood')
        self.race('visitors', [foreign])
        self.assertNotIn('foreignfood', self.apply(7))
        self.assertIn('foreignfood', self.apply(8))
        self.assertEqual(self.r.Wares['foreignfood'].Rate, 500)
        self.assertEqual(self.r.Wares['foodrations'].Rate, 2000 * 1.25 ** 7)

    def test_race_overrides_replace_empty_lists(self):
        self.ware('rationreplacement', 'customgroup')
        self.select(self.run.env['lookup'].race.list[2])
        self.configure([
            '<set_value name="$ProfileStaples.{\'$paranid\'}" exact="[\'rationreplacement\',\'missing\']"/>',
            '<set_value name="$ProfileMedicines.{\'$paranid\'}" exact="[]"/>',
            '<set_value name="$ProfileRaceDemands.{\'$paranid\'}" exact="[]"/>',
        ])
        self.assertEqual(self.apply(3), {'rationreplacement'})
        self.assertEqual(self.r.ProfileRace, 'paranid')

    def test_missing_and_noncontainer_wares_are_skipped(self):
        gas = self.ware('aliengas', transport='liquid')
        food = self.ware('onlyfood')
        custom = self.race('custom', [food, gas])
        self.select(custom)
        self.run.env['lookup'].ware.list = List([food, gas])
        self.assertEqual(self.apply(10), {'onlyfood'})

    def test_culture_survives_conquest_and_missing_owner_is_neutral(self):
        self.apply()
        self.select(self.run.env['lookup'].race.list[2])
        self.assertEqual(self.apply(), {'foodrations', 'water'})
        self.setUp()
        self.run.env['Sector'] = Component(owner=NIL)
        self.assertEqual(self.apply(), {'water'})
        self.assertEqual(self.r.ProfileRace, '')

    def test_changed_basket_does_not_change_frozen_preferences(self):
        self.apply(3)
        old = self.r.Wares['foodrations']
        old.update(Reserve=50, Delivered=25, Paid=1000)
        self.r['GrowthSeconds'] = 720
        replacement = self.ware('newrations')
        self.run.env['lookup'].race.list[1].workforce['resources'] = List([replacement])
        self.run.library('RefreshProfile')
        self.assertEqual(self.r.GrowthSeconds,720)
        self.assertEqual((old.Rate,old.Reserve,old.Delivered,old.Paid),(3125,50,25,1000))
        self.assertNotIn('newrations',self.r.Wares)
        self.run.library('ApplyLevel')
        self.assertNotIn('newrations',self.r.Wares)

    def test_lost_record_definitions_recover_from_saved_sector_not_new_owner(self):
        self.apply(4)
        self.r['Target']=5
        self.r.Wares['foodrations']['Delivered']=9
        del self.r['Definitions']
        self.run.env['Sector'].owner.primaryrace=self.run.env['lookup'].race.list[2]
        self.run.library('RefreshProfile')
        self.assertEqual((self.r.Level,self.r.Target),(4,5))
        self.assertEqual(self.r.ProfileRace,'argon')
        self.assertGreater(self.r.Wares['foodrations'].Rate,0)
        self.assertEqual(self.r.Wares['foodrations'].Delivered,9)

    def test_retired_offer_stops_new_reservations_but_finishes_unloading(self):
        self.apply()
        old = self.r.Wares['foodrations']
        old.update(Rate=0, Cap=0, Demand=100, Offer=Table(exists=True, amount=80, offeramount=100))
        self.r['Hub'] = Table(exists=True, iswreck=False)
        self.r.Wares['water']['Reserve'] = self.r.Wares['water'].Cap
        calls = []
        self.run.native['update_trade'] = lambda n: calls.append((self.run.expr(n.get('amount')), self.run.expr(n.get('desiredamount'))))
        self.run.library('UpdateOffers')
        self.assertEqual(calls, [(0, 0)])
        from test_galaxy import Object
        deal = Object(exists=True, transferredamount=20, unitprice=1200, buyer=self.r.Hub)
        self.r.Transfers[deal] = Ware('foodrations')
        calls.clear()
        self.run.library('UpdateOffers')
        self.assertEqual(calls, [])
        self.run.env['event'] = Table(param=deal)
        self.run.stubs['PublishAllDiagnostics'] = lambda: None
        self.run.library('RecordDelivery')
        self.assertEqual((old.Delivered, old.Paid, old.Reserve), (20, 24000, 20))
        self.assertNotIn(deal, self.r.Transfers)

    def test_retired_requirement_does_not_block_and_empty_profile_cannot_qualify(self):
        self.apply()
        self.r.Wares['foodrations']['Rate'] = 0
        self.r['GrowthSeconds'] = 7200
        self.run.library('EvaluateQualification')
        self.assertTrue(self.r.Qualified)
        self.r.Wares['water']['Rate'] = 0
        self.run.library('EvaluateQualification')
        self.assertFalse(self.r.Qualified)


if __name__ == '__main__':
    unittest.main()
