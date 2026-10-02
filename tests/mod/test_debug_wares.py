"""Execute shipped debug actions; native offers and diagnostics are intercepted."""
import unittest
from support import Table, Component
from support_unrest import UnrestFixture


class DebugStockTests(UnrestFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.ware = self.add('food', reserve=100, rate=100)
        self.other = self.add('water', reserve=50, rate=100)
        self.run.env['md'].CE_CivilianHub.Init.Registry = Table({self.sector:self.r})
        self.run.env['md'].CE_Settings.State.Debug = True
        self.run.env['event'] = Table(param2='', param3=self.hub)
        self.updates = []
        self.run.stubs.update({
            'md.CE_CivilianHub.UpdateOffers':lambda:self.updates.append('offers'),
            'md.CE_Diagnostics.PublishDiagnostics':lambda:None,
            'md.CE_Diagnostics.PublishAllDiagnostics':lambda:None})

    def request(self, command, script='CE_DebugWares', cue='Request'):
        self.run.env['event'].param2 = command
        self.run.actions(self.run.scripts[script].xpath(f'//cue[@name="{cue}"]/actions')[0])

    def test_random_bounds_and_only_selected_ware(self):
        for fraction in (0, 0.5, 1):
            self.r.Wares[self.ware].Reserve = 100
            self.run.random_fraction = fraction
            self.request(f'random:food:{self.u.Token}')
            self.assertEqual(self.r.Wares[self.ware].Reserve, 100+100*fraction)
            self.assertEqual(self.r.Wares[self.other].Reserve, 50)
        self.assertEqual(self.updates, ['offers']*3)

    def test_zero_replay_disabled_inactive_and_wrong_hub(self):
        self.request('zero:food:0')
        self.assertEqual(self.r.Wares[self.ware].Reserve, 0)
        self.r.Wares[self.ware].Reserve = 75
        self.request('zero:food:0')
        self.run.env['md'].CE_Settings.State.Debug = False
        self.request('zero:food:1')
        self.run.env['md'].CE_Settings.State.Debug = True
        self.run.env['event'].param3 = Component()
        self.request('zero:food:1')
        self.run.env['event'].param3 = self.hub
        self.r.Wares[self.ware].Active = False
        self.request('zero:food:1')
        self.r.Wares[self.ware].Active = True
        self.r.Wares[self.ware].Rate = 0
        self.request('zero:food:1')
        self.assertEqual(self.r.Wares[self.ware].Reserve, 75)
        self.assertEqual(self.updates, ['offers'])

    def test_accrues_before_mutating_and_does_not_credit_deliveries(self):
        self.run.env['player'].age = 1800
        self.r.Wares[self.ware].Delivered = 12
        self.r.Wares[self.ware].Paid = 34
        self.run.random_fraction = 0
        self.request('random:food:0')
        self.assertEqual(self.r.Wares[self.ware].Reserve, 50)
        self.assertEqual(self.r.Last, 1800)
        self.assertEqual(self.r.Wares[self.ware].Delivered, 12)
        self.assertEqual(self.r.Wares[self.ware].Paid, 34)

    def test_full_or_over_capacity_random_does_not_reduce_stock(self):
        for reserve in (200, 250):
            self.r.Wares[self.ware].Reserve = reserve
            self.request(f'random:food:{self.u.Token}')
            self.assertEqual(self.r.Wares[self.ware].Reserve, reserve)

    def test_progress_cap_replay_and_pending_construction(self):
        def progress(command):
            self.request(command, 'CE_DebugAdvance', 'ProgressRequest')
        progress('hour:0')
        self.assertEqual(self.r.GrowthSeconds, 3600)
        progress('hour:0')
        self.assertEqual(self.r.GrowthSeconds, 3600)
        self.run.library('md.CE_Settings.RequiredGrowth')
        cap = self.run.env['RequiredGrowthSeconds']
        self.r.GrowthSeconds = cap-1
        progress('hour:1')
        self.assertEqual(self.r.GrowthSeconds, cap)
        self.r.GrowthSeconds = 0
        self.r.Target = 6
        progress('hour:2')
        self.assertEqual(self.r.GrowthSeconds, 0)
