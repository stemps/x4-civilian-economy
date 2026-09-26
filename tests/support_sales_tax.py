"""Shared completed-delivery fixture; native money and notifications are mocked."""
from support import Runner, Table, Component, Ware, NIL


class SalesTaxFixture:
    def fixture(self, seller='argon', owned=True, amount=10, price=1300, actual_paid=None):
        run = Runner()
        hub = Component(sector=Component(isplayerowned=owned, knownname='Grand Exchange I'))
        state = Table(Active=True, Rate=1, Reserve=0, Delivered=0, Paid=0, Offer=NIL)
        record = Table(Hub=hub, Wares=Table({Ware('food'): state}), Transfers=Table(),
                       Operational=True, Last=0, GrowthSeconds=0, Level=1, Target=0)
        # Reserved amount and current offer price deliberately differ from actual sale.
        state.Price = 9000
        deal = Component(buyer=hub, seller=Component(owner=seller, money=777, isplayerowned=seller == 'player', order=Component(exists=True)),
                         amount=100, transferredamount=amount, unitprice=price, sellfree=False)
        record.Transfers[deal] = Ware('food')
        run.env.update(R=record, event=Table(param=deal),
                       faction=Table(ownerless='ownerless', player='player'))
        run.stubs.update(UpdateOffers=lambda: None, PublishDiagnostics=lambda: None,
                         PublishAllDiagnostics=lambda: None)
        payments = []
        run.env['player'].money = 100000
        run.env['player'].entity = Component()
        def reward(node):
            self.assertNotIn(deal, record.Transfers)
            money = run.expr(node.get('money'))
            payments.append(money)
            run.env['player'].money += money if actual_paid is None else actual_paid
        run.native['reward_player'] = reward
        run.tax_descriptions = []
        run.delivery_descriptions = []
        run.delivery_watches = []
        def watch(node):
            self.assertEqual(node.get('cue'), 'md.CE_Trade.WatchDeliveryPayment')
            self.assertNotIn(deal, record.Transfers)
            run.delivery_watches.append(run.expr(node.get('param')))
        run.native['signal_cue_instantly'] = watch
        def description(node):
            if node.get('name') == "'CEVTLDelivery'":
                self.assertIsNone(node.get('param'))
                run.delivery_descriptions.append(run.env['Payment'].Amount)
                return
            self.assertEqual(node.get('name'), "'transfer_money'")
            self.assertEqual(node.get('param'),
                             "$SalesTaxPaid + ';' + {974201,155}.[$R.$Hub.sector.knownname]")
            self.assertTrue(payments)
            self.assertNotIn(deal, record.Transfers)
            run.tax_descriptions.append(run.env['SalesTaxPaid'])
        run.native['raise_lua_event'] = description
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

