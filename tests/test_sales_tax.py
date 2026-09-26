"""Execute shipped delivery accounting; native rewards mutate the mocked account."""
import unittest
from support import Table, Component, Ware, NIL
from support_sales_tax import SalesTaxFixture


class SalesTaxTests(SalesTaxFixture, unittest.TestCase):
    def test_unrest_reduces_only_extra_sector_income(self):
        for stage, remaining in enumerate((100, 75, 50, 25, 25)):
            with self.subTest(stage=stage):
                run, record, deal, payments = self.fixture(amount=100, price=1000)
                record.Unrest = Table(Stage=stage)
                run.library('RecordDelivery')
                self.assertEqual(payments, [15000 * remaining / 100])
                self.assertEqual(record.Wares[Ware('food')].Paid, 100000)
                self.assertEqual(deal.seller.money, 777)

    def test_completed_sales_pay_current_sector_owner_regardless_of_seller(self):
        for seller in ('player', 'argon', 'teladi'):
            for owned in (True, False):
                with self.subTest(seller=seller, player_sector=owned):
                    run, record, deal, payments = self.fixture(seller, owned)
                    run.library('RecordDelivery')
                    self.assertEqual(payments, [1950] if owned else [])
                    self.assertEqual(run.env['player'].money, 100000 + (1950 if owned else 0))
                    self.assertEqual(len(run.tax_messages), 2 if owned else 0)
                    if owned:
                        self.assertEqual([message[0] for message in run.tax_messages],
                                         ['show_notification', 'write_to_logbook'])
                        self.assertTrue(all(message[1] == 1950 for message in run.tax_messages))
                    state = record.Wares[Ware('food')]
                    self.assertEqual((state.Delivered, state.Paid, state.Reserve), (10, 13000, 10))
                    self.assertEqual(deal.seller.money, 777)
                    self.assertNotIn(deal, record.Transfers)
                    guard = run.tree.xpath('//cue[@name="SectorDeliveryFinished"]/conditions/check_value[contains(@value,"$Transfers")]/@value')[0]
                    self.assertFalse(run.expr(guard))  # Duplicate completion cannot pay again.

    def test_ownership_change_during_delivery_uses_completion_owner(self):
        for initial, final in ((False, True), (True, False)):
            run, record, deal, payments = self.fixture(owned=initial)
            record.Hub.sector.isplayerowned = final
            run.library('RecordDelivery')
            self.assertEqual(len(payments), int(final))

    def test_zero_quantity_or_free_delivery_pays_no_tax(self):
        for amount, price in ((0, 1300), (10, 0)):
            run, record, deal, payments = self.fixture(amount=amount, price=price)
            run.library('RecordDelivery')
            self.assertEqual(payments, [])
            self.assertEqual(run.tax_messages, [])

    def test_message_uses_account_delta_and_suppresses_nonpositive_income(self):
        for paid in (-1000, 0, 1000):
            run, record, deal, payments = self.fixture(actual_paid=paid)
            run.library('RecordDelivery')
            self.assertEqual(run.tax_messages,
                             [('show_notification', paid), ('write_to_logbook', paid)] if paid > 0 else [])
            self.assertEqual(run.env['SalesTaxPaid'], paid)
            self.assertEqual(run.tax_descriptions, [paid] if paid > 0 else [])

    def test_optional_description_never_makes_an_additional_payment(self):
        for listener_present in (False, True):
            for notifications in (False, True):
                run, record, deal, payments = self.fixture()
                run.env['md'].CE_Settings.State.TaxNotifications = notifications
                if not listener_present:
                    run.native['raise_lua_event'] = lambda node: None
                run.library('RecordDelivery')
                self.assertEqual(payments, [1950])
                self.assertEqual(run.env['player'].money, 101950)
                self.assertEqual(run.tax_descriptions, [1950] if listener_present else [])
                self.assertEqual(len(run.tax_messages), 2 if notifications else 0)

    def test_reported_water_delivery_credits_player_and_announces_income(self):
        run, record, deal, payments = self.fixture(amount=1666, price=3700)
        run.library('RecordDelivery')
        self.assertEqual(payments, [924630])
        self.assertEqual(run.env['player'].money, 1024630)
        self.assertEqual(run.tax_messages,
                         [('show_notification', 924630), ('write_to_logbook', 924630)])

    def test_delivery_label_is_independent_of_tax_and_does_not_pay_seller_again(self):
        for owned in (False, True):
            for seller in ('player', 'argon'):
                for tax in (0, 15):
                    run, record, deal, payments = self.fixture(seller=seller, owned=owned,
                                                              amount=1666, price=3700)
                    run.env['md'].CE_Settings.State.update(TaxPercent=tax, TaxNotifications=False)
                    run.library('RecordDelivery')
                    self.assertEqual(run.delivery_descriptions, [])
                    self.assertEqual([p.Amount for p in run.delivery_watches], [6164200] if seller == 'player' else [])
                    self.assertEqual(payments, [924630] if owned and tax else [])
                    self.assertEqual(deal.seller.money, 777)
                    self.assertEqual(record.Wares[Ware('food')].Paid, 6164200)

    def test_unpaid_deliveries_do_not_queue_a_financial_label(self):
        for amount, price, free in ((0,1300,False),(10,0,False),(10,1300,True)):
            run, record, deal, payments = self.fixture(seller='player', amount=amount, price=price)
            deal.sellfree = free
            run.library('RecordDelivery')
            self.assertEqual(run.delivery_descriptions, [])
            self.assertEqual(run.delivery_watches, [])

    def test_delivery_description_waits_for_account_payment_and_keeps_captured_context(self):
        run, record, deal, payments = self.fixture(seller='player', amount=1666, price=3700)
        run.env['player'].age = 240858.740
        run.library('RecordDelivery')
        payment, = run.delivery_watches
        self.assertEqual(run.delivery_descriptions, [])
        self.assertIs(payment.Order, deal.seller.order)
        self.assertIs(payment.Seller, deal.seller)
        self.assertEqual(payment.CompletedAt, 240858.740)
        # Execute the shipped listener's capture actions, then move caller state.
        run.env['event'] = Table(param=payment)
        run.actions(run.trade.xpath('//cue[@name="WatchDeliveryPayment"]/actions')[0])
        deal.seller.order = Component(exists=True)
        record.Hub.sector.knownname = 'Another sector'
        record.Hub = NIL
        listener = run.trade.xpath('//cue[@name="DeliveryAccountPaid"]')[0]
        event = listener.find('conditions/event_object_money_updated')
        run.env['parent'] = Table(Payment=payment)
        self.assertIs(run.expr(event.get('object')), payment.Seller)
        self.assertEqual(run.expr(event.get('oldamount')), 6164200)
        self.assertEqual(run.expr(event.get('newamount')), 0)
        # The captured AI order need not finish: slot 4 still has it in the
        # critical/waitingdrones state after the account payment.
        self.assertIsNone(event.get('order'))
        self.assertIsNot(payment.Order, deal.seller.order)
        self.assertEqual(payment.SectorName, 'Grand Exchange I')
        run.env['player'].age = 240859.741
        cancelled = []
        run.native['cancel_cue'] = lambda n: cancelled.append(n.get('cue'))
        run.actions(listener.find('actions'))
        self.assertEqual(run.delivery_descriptions, [6164200])
        self.assertEqual(run.env['player'].entity.ce_vtl_deliveries,
                         [[payment.Seller, 6164200, 240858.740, 240859.741, 'Grand Exchange I', 'food']])
        # This interpreter stops at MD values (cents). The game's blackboard
        # serializes money to Lua credits; do not pre-divide the MD amount.
        self.assertEqual(payments, [924630])
        self.assertEqual(cancelled, ['parent'])

    def test_payment_filter_rejects_other_ships_balances_and_partial_debits(self):
        run, record, deal, payments = self.fixture(seller='player', amount=1666, price=3700)
        run.library('RecordDelivery')
        payment, = run.delivery_watches
        run.env['parent'] = Table(Payment=payment)
        event = run.trade.xpath('//cue[@name="DeliveryAccountPaid"]/conditions/event_object_money_updated')[0]
        expected = (run.expr(event.get('object')), run.expr(event.get('oldamount')), run.expr(event.get('newamount')))
        for source, old, new, match in (
            (deal.seller, 6164200, 0, True),
            (Component(), 6164200, 0, False),
            (deal.seller, 6164200, 100, False),
            (deal.seller, 7000000, 0, False),
        ):
            self.assertEqual((source, old, new) == expected, match)

    def test_missing_order_does_not_guess_a_payment_timestamp(self):
        run, record, deal, payments = self.fixture(seller='player')
        deal.seller.order = NIL
        run.library('RecordDelivery')
        self.assertEqual(run.delivery_watches, [])

    def test_persistent_trading_order_does_not_accumulate_finish_listeners(self):
        run, record, deal, payments = self.fixture(seller='player')
        deal.seller.order.isinfinite = True
        run.library('RecordDelivery')
        self.assertEqual(run.delivery_watches, [])

    def test_destruction_and_cancellation_discard_labels_without_paying(self):
        run, record, deal, payments = self.fixture(seller='player')
        run.library('RecordDelivery')
        for name in ('DeliveryLabelSellerDestroyed', 'DeliveryLabelOrderCancelled'):
            cancelled = []
            run.native['cancel_cue'] = lambda n: cancelled.append(n.get('cue'))
            actions = run.trade.xpath('//cue[@name=$name]/actions', name=name)[0]
            run.actions(actions)
            self.assertEqual(cancelled, ['parent'])
            self.assertEqual(run.delivery_descriptions, [])
        self.assertEqual(payments, [1950])


if __name__ == '__main__':
    unittest.main()
