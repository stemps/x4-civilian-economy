"""Execute shipped settings actions; native UI rendering and trades remain mocked."""
import copy
import unittest
from support import Runner, Table, List, Component, Ware, NIL
from support_sales_tax import SalesTaxFixture


class SettingsTests(SalesTaxFixture, unittest.TestCase):
    def setUp(self):
        self.run = Runner()
        self.run.env['player'].entity = Table()
        self.state = self.run.env['md'].CE_Settings.State

    def change(self, key, value):
        self.run.env.update(SettingKey='$' + key, SettingValue=value)
        self.run.library('md.CE_Settings.Change')

    def record(self, sector, factor=1):
        ware = Ware('food')
        definitions = List([List([ware, 1, 3600.0])])
        record = Table(Level=1, Target=0, Operational=True, GrowthSeconds=0.0, Last=0.0,
                       Factor=factor, Hub=NIL, Wares=Table(), Transfers=Table(),
                       Definitions=definitions, PauseOffers=False, PlotReady=True, TestUpgrade=False)
        self.run.env['R'] = record
        self.run.library('md.CE_Demand.ApplyLevel')
        record.Wares[ware].Reserve = 10000.0
        registry = self.run.env['md'].CE_OwnerlessHub.Init
        if 'Registry' not in registry:
            registry.Registry = Table()
        registry.Registry[sector] = record
        return record, record.Wares[ware]

    def test_defaults_save_reload_and_no_cross_save_leak(self):
        self.run.library('md.CE_Settings.Ensure')
        self.assertEqual(dict(self.state), dict(Debug=False, DemandMultiplier=1.0,
                         TimeMultiplier=1.0, TaxNotifications=True, TaxPercent=15))
        for key, value in [('Debug', 1), ('TaxNotifications', 0), ('DemandMultiplier', .3),
                           ('TimeMultiplier', .2), ('TaxPercent', 0)]:
            self.change(key, value)
        saved = copy.deepcopy(self.state)
        self.run.library('md.CE_Settings.Ensure')
        self.assertEqual(self.state, saved)
        # Re-initialization and UI registration are non-destructive.
        self.assertTrue(self.run.env['player'].entity.ce_debug_enabled)
        another = Runner()
        another.library('md.CE_Settings.Read')
        self.assertEqual(another.env['CEDemandMultiplier'], 1)
        self.assertEqual(another.env['CETaxPercent'], 15)

    def test_validation_and_rounding(self):
        for key, value in [('DemandMultiplier', 0), ('DemandMultiplier', 10.1),
                           ('TimeMultiplier', 10.1),
                           ('TimeMultiplier', '0.5'), ('TaxPercent', -1), ('TaxPercent', 51),
                           ('TaxPercent', float('nan')), ('Debug', 2), ('Unknown', 1)]:
            self.change(key, value)
            self.assertFalse(self.run.env['SettingValid'], (key, value))
        self.change('DemandMultiplier', .36)
        self.assertEqual(self.state.DemandMultiplier, .4)
        self.change('TaxPercent', 49.7)
        self.assertEqual(self.state.TaxPercent, 50)
        for key in ('DemandMultiplier', 'TimeMultiplier'):
            for value in (1.1, 5.0, 10.0):
                self.change(key, value)
                self.assertEqual(self.state[key], value)

    def test_live_demand_settles_old_rates_and_preserves_identities(self):
        first, food = self.record(Component(), 1)
        second, other = self.record(Component(), .5)
        definitions = first.Definitions
        deal = Component(exists=True)
        first.Transfers[deal] = Ware('food')
        offer = Component(exists=True)
        food.Offer = offer
        self.run.env['player'].age = 100
        self.change('DemandMultiplier', .5)
        self.assertEqual((food.Reserve, other.Reserve), (9900, 9950))
        self.assertEqual((food.Rate, other.Rate), (1800, 900))
        self.assertEqual((food.Cap, other.Cap), (3600, 1800))
        self.assertEqual((first.GrowthSeconds, second.GrowthSeconds), (100, 100))
        self.assertIs(first.Definitions, definitions)
        self.assertIs(food.Offer, offer)
        self.assertIn(deal, first.Transfers)
        self.run.env['player'].age = 200
        self.change('DemandMultiplier', 1)
        self.assertEqual((food.Reserve, other.Reserve), (9850, 9925))
        self.assertEqual((food.Rate, other.Rate), (3600, 1800))
        self.assertEqual(first.Last, 200)
        # Re-applying the same setting does not repeatedly rescale or accrue.
        self.change('DemandMultiplier', 1)
        self.assertEqual(food.Rate, 3600)

    def test_time_changes_qualification_and_snapshot_without_changing_demand(self):
        record, food = self.record(Component())
        record.GrowthSeconds = 1000
        self.change('TimeMultiplier', .1)
        self.assertEqual(food.Rate, 3600)
        self.assertTrue(record.Qualified)
        self.assertEqual(record.GrowthSeconds, 1000)
        self.run.env['R'] = record
        self.run.library('md.CE_Diagnostics.PublishDiagnostics')
        self.assertEqual(record.Snapshot[6], 720)
        self.run.env['player'].age = 1
        self.run.library('md.CE_Reserves.Accrue')
        self.assertEqual(record.GrowthSeconds, 1000)  # Never truncate earned growth.
        self.change('TimeMultiplier', 1)
        self.assertFalse(record.Qualified)
        self.assertEqual(record.GrowthSeconds, 1000)
        self.assertEqual(record.Target, 0)  # Normal tick owns construction/level changes.

    def test_live_offer_refresh_retains_reservations_and_defers_unloading(self):
        for unloading in (False, True):
            self.setUp()
            record, food = self.record(Component())
            record.Hub = Component(exists=True, iswreck=False)
            food.Reserve = 100
            offer = Component(exists=True, amount=6900, offeramount=7100)
            food.Offer = offer
            if unloading:
                record.Transfers[Component(exists=True)] = Ware('food')
            updates = []
            self.run.native['update_trade'] = lambda n: updates.append(
                (self.run.expr(n.get('amount')), self.run.expr(n.get('desiredamount'))))
            self.change('DemandMultiplier', .1)
            self.assertEqual(updates, [] if unloading else [(420, 620)])
            self.assertIs(food.Offer, offer)
            self.assertEqual(food.Reserve, 100)
            self.assertEqual(record.Snapshot[9][1][9], 360)

    def test_tax_endpoints_and_notification_toggle_do_not_change_seller_accounting(self):
        for percent in (0, 15, 50):
            for notifications in (False, True):
                run, record, deal, payments = self.fixture()
                run.env['md'].CE_Settings.State.update(TaxPercent=percent,
                                                       TaxNotifications=notifications)
                run.library('RecordDelivery')
                self.assertEqual(payments, [13000 * percent / 100] if percent else [])
                self.assertEqual(run.env['player'].money, 100000 + 13000 * percent / 100)
                self.assertEqual(len(run.tax_messages), 2 if percent and notifications else 0)
                self.assertEqual(record.Wares[Ware('food')].Paid, 13000)
                self.assertEqual(deal.seller.money, 777)

    def test_options_builds_selectable_controls_and_callbacks_use_confirmed_values(self):
        calls = []
        self.run.native['signal_cue_instantly'] = lambda n: calls.append((n.get('cue'), self.run.expr(n.get('param'))))
        self.run.library('md.CE_Options.Build')
        selectable = False
        controls = []
        for cue, args in calls:
            if cue.endswith('Add_Row'):
                selectable = args.selectable
            if cue.endswith(('Make_Slider', 'Make_CheckBox')):
                self.assertTrue(selectable)
                controls.append(args)
        self.assertEqual(len(controls), 5)
        debug, demand, time, tax, notifications = controls
        self.assertFalse(debug.checked)
        self.assertTrue(notifications.checked)
        for slider in (demand, time):
            self.assertEqual((slider.min, slider.max, slider.step, slider.start), (.1, 10, .1, 1))
        for checkbox in (debug, notifications):
            self.assertEqual(checkbox.width, 'Helper.standardTextHeight')
            self.assertEqual(checkbox.height, checkbox.width)
        self.assertEqual((tax.min, tax.max, tax.step, tax.start), (0, 50, 1, 15))
        tree = self.run.scripts['CE_Options']
        slider_actions = tree.xpath('//cue[@name="Slider"]/actions')[0]
        self.run.env['event'] = Table(param=Table(echo='$TimeMultiplier', value=.2, valuechanged=False, id='ce_time'))
        self.run.actions(slider_actions)
        self.assertEqual(self.state.TimeMultiplier, 1)
        self.run.env['event'].param.valuechanged = True
        self.run.actions(slider_actions)
        self.assertEqual(self.state.TimeMultiplier, .2)
        self.run.env['event'] = Table(param=Table(echo='$Debug', checked=1))
        self.run.actions(tree.xpath('//cue[@name="Checkbox"]/actions')[0])
        self.assertTrue(self.state.Debug)


if __name__ == '__main__':
    unittest.main()
