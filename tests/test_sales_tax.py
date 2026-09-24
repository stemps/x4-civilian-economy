"""Execute shipped delivery accounting; native rewards mutate the mocked account."""
import unittest
from support import Runner, Table, Component, Ware, NIL


class SalesTaxTests(unittest.TestCase):
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

    def fixture(self, seller='argon', owned=True, amount=10, price=1300, actual_paid=None):
        run = Runner()
        hub = Component(sector=Component(isplayerowned=owned))
        state = Table(Active=True, Rate=1, Reserve=0, Delivered=0, Paid=0, Offer=NIL)
        record = Table(Hub=hub, Wares=Table({Ware('food'): state}), Transfers=Table(),
                       Operational=True, Last=0, GrowthSeconds=0, Level=1, Target=0)
        # Reserved amount and current offer price deliberately differ from actual sale.
        state.Price = 9000
        deal = Component(buyer=hub, seller=Component(owner=seller, money=777),
                         amount=100, transferredamount=amount, unitprice=price)
        record.Transfers[deal] = Ware('food')
        run.env.update(R=record, event=Table(param=deal),
                       faction=Table(ownerless='ownerless', player='player'))
        run.stubs.update(UpdateOffers=lambda: None, PublishDiagnostics=lambda: None,
                         PublishAllDiagnostics=lambda: None)
        payments = []
        run.env['player'].money = 100000
        def reward(node):
            self.assertNotIn(deal, record.Transfers)
            money = run.expr(node.get('money'))
            payments.append(money)
            run.env['player'].money += money if actual_paid is None else actual_paid
        run.native['reward_player'] = reward
        run.tax_messages = []
        def message(node):
            self.assertTrue(payments)  # Announce only after native reward changes the account.
            self.assertNotIn(deal, record.Transfers)
            self.assertEqual(node.get('text'),
                             "{974201,127}.[$SalesTaxPaid.formatted.{'%s %Cr'},$R.$Hub.sector.name,$Delivered,$Ware.name]")
            if node.tag == 'write_to_logbook':
                self.assertEqual(node.get('category'), 'general')
                self.assertEqual(node.get('title'), '{974201,126}')
                self.assertEqual(run.expr(node.get('money')), run.env['SalesTaxPaid'])
                self.assertIs(run.expr(node.get('object')), hub)
            # Formatting/display remains native; record the amount supplied to it.
            run.tax_messages.append((node.tag, run.env['SalesTaxPaid']))
        run.native.update(show_notification=message, write_to_logbook=message)
        return run, record, deal, payments

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

    def test_reported_water_delivery_credits_player_and_announces_income(self):
        run, record, deal, payments = self.fixture(amount=1666, price=3700)
        run.library('RecordDelivery')
        self.assertEqual(payments, [924630])
        self.assertEqual(run.env['player'].money, 1024630)
        self.assertEqual(run.tax_messages,
                         [('show_notification', 924630), ('write_to_logbook', 924630)])


if __name__ == '__main__':
    unittest.main()
