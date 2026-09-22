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
        self.r = Table(GrowthSeconds=0.0, Last=0.0, Level=1, Target=0, Operational=True, Wares=Table(),
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
                        added = self.ware(node.get('id'), node.get('group', ''), node.get('transport'))
                        added.averageprice = int(node.find('price').get('average')) * 100
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
        self.assertEqual(self.r.Wares['algae'].Rate, 9380 * 1.25 ** 7)

    def test_foreign_only_at_eight_shared_staples_are_not_duplicated(self):
        food = self.run.env['ware'].foodrations
        self.race('cousins', [food])
        foreign = self.ware('foreignfood')
        self.race('visitors', [foreign])
        self.assertNotIn('foreignfood', self.apply(7))
        self.assertIn('foreignfood', self.apply(8))
        self.assertEqual(self.r.Wares['foreignfood'].Rate, 4690)
        self.assertEqual(self.r.Wares['foodrations'].Rate, 7140 * 1.25 ** 7)

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
        self.assertEqual((old.Rate,old.Reserve,old.Delivered,old.Paid),(11156.25,50,25,1000))
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


class BudgetBalanceTests(unittest.TestCase):
    setUp = ProfileTests.setUp
    apply = ProfileTests.apply
    select = ProfileTests.select
    configure = ProfileTests.configure
    ware = ProfileTests.ware
    race = ProfileTests.race

    EXPECTED = {
        'foodrations': (1, 7140), 'water': (1, 1420), 'energycells': (2, 9380),
        'medicalsupplies': (3, 2270), 'refinedmetals': (4, 1690),
        'siliconwafers': (4, 840), 'microchips': (5, 260),
        'scanningarrays': (6, 240), 'advancedcomposites': (6, 460),
        'advancedelectronics': (7, 250), 'sojahusk': (8, 2340),
        'nostropoil': (8, 2210), 'cheltmeat': (8, 1470),
        'scruffinfruits': (8, 2680), 'bofu': (8, 740), 'terranmre': (8, 1390),
        'spacefuel': (9, 750), 'spaceweed': (9, 600), 'majadust': (9, 480),
    }

    def load_prices(self, dlcs=False):
        paths = [REF / 'libraries/wares.xml']
        if dlcs:
            paths += [REF / 'extensions' / ('ego_dlc_' + race) / 'libraries/wares.xml'
                      for race in ('split', 'boron', 'terran')]
        by_id = {w.id: w for w in self.run.env['lookup'].ware.list}
        for path in paths:
            tree = E.parse(str(path))
            for node in tree.xpath('//ware[@id][price]'):
                ident = node.get('id')
                if ident not in by_id:
                    by_id[ident] = self.ware(ident, node.get('group', ''), node.get('transport'))
                ware = by_id[ident]
                for prop, attr in (('minprice', 'min'), ('maxprice', 'max'), ('averageprice', 'average')):
                    setattr(ware, prop, int(node.find('price').get(attr)) * 100)
            if path != paths[0]:
                recipe = tree.xpath('//add[@sel=$sel]/production/primary/ware',
                                    sel="/wares/ware[@id='workunit_busy']")
                self.assertTrue(recipe)
                self.race(path.parents[1].name.removeprefix('ego_dlc_'),
                          [by_id[n.get('ware')] for n in recipe])

    def test_argon_prime_quantities_and_all_ten_revenues(self):
        import math
        base = [152500, 303185, 487941, 951977, 1406811, 2179753, 2917442,
                3749112, 4855200, 6069000]
        full = base[:7] + [3958862, 5117388, 6396735]
        optional = {'cheltmeat', 'scruffinfruits', 'bofu', 'terranmre'}
        for dlcs, revenues in ((False, base), (True, full)):
            with self.subTest(dlcs=dlcs):
                self.setUp()
                self.load_prices(dlcs)
                expected = {k: v for k, v in self.EXPECTED.items() if dlcs or k not in optional}
                for level in range(1, 11):
                    active = self.apply(level)
                    self.assertEqual(active, {k for k, (unlock, _) in expected.items() if unlock <= level})
                    revenue = 0
                    for ware, state in self.r.Wares.items():
                        unlock, quantity = expected[ware]
                        if unlock <= level:
                            self.assertAlmostEqual(state.Rate, quantity * 1.25 ** (level - unlock))
                            self.assertEqual(state.Cap, math.ceil(2 * state.Rate))
                            revenue += state.Rate * state.Price / 100
                    self.assertEqual(math.floor(revenue + 0.5), revenues[level - 1])
                self.assertEqual({str(d[1]): (d[2], d[3]) for d in self.r.Definitions}, expected)
                self.assertTrue(all(len(d) == 3 for d in self.r.Definitions))

    def build_one(self, row, price):
        # Isolate default normalization from native local and foreign staples.
        food = self.ware('customfood')
        food.averageprice = price
        self.run.env['lookup'].race.list = List()
        race = self.race('custom', [])
        self.select(race)
        self.configure([f'<set_value name="$ProfileCommon" exact="[{row}]"/>'])
        self.run.library('md.CE_PopulationProfiles.Build')
        return self.run.env['CandidateDefinitions']

    def test_round_half_up_minimum_and_invalid_prices(self):
        for price, expected in ((200000, 80), (200001, 70), (1000000000, 10),
                                (0, None), (-100, None), (NIL, None)):
            with self.subTest(price=price):
                self.setUp()
                rows = self.build_one("['customfood',1,150000.0f,'budget']", price)
                self.assertEqual(self.run.env['CandidateValid'], expected is not None)
                if expected is not None:
                    self.assertEqual(rows[1][3], expected)
                else:
                    self.assertEqual(rows, [])

    def test_explicit_quantity_override_does_not_read_price(self):
        rows = self.build_one("['customfood',4,123.5f]", NIL)
        self.assertTrue(self.run.env['CandidateValid'])
        self.assertEqual(rows[1][1:], [4, 123.5])

    def test_race_quantity_override_and_missing_budget_ware(self):
        self.run.env['ware'].microchips.averageprice = 0
        self.configure(["<set_value name=\"$ProfileRaceDemands.{'$argon'}\" exact=\"[['microchips',4,123.5f],['absent',1,75000.0f,'budget']]\"/>"])
        self.apply(4)
        self.assertFalse(self.r.ProfileError)
        self.assertEqual(self.r.Wares['microchips'].Rate, 123.5)
        self.assertNotIn('energycells', self.r.Wares)

    def test_invalid_budget_cannot_replace_existing_state(self):
        import copy
        self.apply(3)
        self.r['GrowthSeconds'] = 720
        self.r.Wares['water'].update(Reserve=123, Delivered=55, Paid=600)
        before = copy.deepcopy(self.r)
        self.run.env['ware'].foodrations.averageprice = 0
        self.run.library('md.CE_PopulationProfiles.Build')
        self.assertFalse(self.run.env['CandidateValid'])
        self.assertEqual(self.r, before)
        self.run.library('RefreshProfile')
        self.assertEqual(self.r, before)

    def test_interrupted_normalization_cannot_publish_budget_as_quantity(self):
        self.run.stubs['md.CE_PopulationProfiles.NormalizeBudget'] = lambda: None
        self.run.library('RefreshProfile')
        self.assertTrue(self.r.ProfileError)
        self.assertNotIn('Definitions', self.r)
        self.assertEqual(self.r.Wares, {})

    def test_initial_invalid_price_does_not_publish_partial_profile(self):
        self.run.env['ware'].water.averageprice = 0
        self.run.library('RefreshProfile')
        self.assertTrue(self.r.ProfileError)
        self.assertNotIn('Definitions', self.r)
        self.assertEqual(self.r.Wares, {})

    def test_boron_water_and_terran_substitutions(self):
        for race_id in ('boron', 'terran'):
            self.setUp()
            self.load_prices(True)
            self.select(next(r for r in self.run.env['lookup'].race.list if r.id == race_id))
            self.apply(10)
            rows = {str(d[1]): (d[2], d[3]) for d in self.r.Definitions}
            self.assertEqual(rows['water'], (1, 1420))
            if race_id == 'boron':
                self.assertEqual(rows['bofu'], (1, 1490))
            else:
                self.assertEqual(rows['terranmre'], (1, 2780))
                self.assertEqual(rows['metallicmicrolattice'], (4, 5000))
                self.assertEqual(rows['siliconcarbide'], (5, 180))
                self.assertEqual(rows['computronicsubstrate'], (7, 30))
                self.assertEqual(rows['stimulants'], (9, 290))
                self.assertNotIn('refinedmetals', rows)

    def test_adapter_staples_cannot_import_water_or_medicine(self):
        self.configure(["<set_value name=\"$ProfileStaples.{'$paranid'}\" exact=\"['water','medicalsupplies','sojahusk']\"/>"])
        self.apply(8)
        rows = {str(d[1]): (d[2], d[3]) for d in self.r.Definitions}
        self.assertEqual(rows['water'], (1, 1420))
        self.assertEqual(rows['medicalsupplies'], (3, 2270))
        self.assertEqual(rows['sojahusk'], (8, 2340))

    def test_saved_placeholder_preferences_survive_reload_and_price_change(self):
        self.apply(3)
        frozen = self.run.env['SectorProfiles'][self.run.env['Sector']]
        old = List([List([d[1], d[2], 2000.0 if d[2] == 1 else d[3]]) for d in self.r.Definitions])
        frozen['Definitions'] = old
        self.r['Definitions'] = old
        self.run.library('ApplyLevel')
        self.r['GrowthSeconds'] = 1234
        self.r.Wares['foodrations'].update(Reserve=99, Delivered=3, Paid=500)
        self.run.env['ware'].foodrations.averageprice *= 2
        self.run.library('RefreshProfile')
        self.run.library('ApplyLevel')
        self.assertEqual(self.r.Wares['foodrations'].Rate, 3125)
        self.assertEqual((self.r.GrowthSeconds, self.r.Wares['foodrations'].Reserve,
                          self.r.Wares['foodrations'].Delivered, self.r.Wares['foodrations'].Paid),
                         (1234, 99, 3, 500))
        del self.r['Definitions']
        self.run.library('RefreshProfile')
        self.assertEqual(self.r.Wares['foodrations'].Rate, 3125)


if __name__ == '__main__':
    unittest.main()
