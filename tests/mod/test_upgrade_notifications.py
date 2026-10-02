"""Lifecycle notifications through shipped construction and controller actions."""
from support import Table, Component, NIL
from support_startup import StartupHarness


class UpgradeNotificationTests(StartupHarness):
    def setUp(self):
        super().setUp()
        self.messages = []
        def message(node):
            record = self.run.env['R']
            if node.tag == 'write_to_logbook' and node.get('title') == '{974201,1}':
                return  # Existing construction failure warning.
            if node.tag == 'write_to_logbook':
                self.assertIs(self.run.expr(node.get('object')), record.Hub)
                self.assertEqual(node.get('interaction'), 'showonmap')
            started = '129' in node.get('text')
            if started:
                self.assertTrue(record.Build.exists)
                self.assertTrue(record.Hub.buildstorage.builds.inprogress)
            else:
                self.assertEqual(record.Target, 0)
                if not record.PauseOffers:
                    self.assertTrue(all(w.Offer.exists for w in record.Wares.values() if w.Rate > 0))
            self.messages.append((node.tag, 'started' if started else 'completed', record.Hub,
                                  record.Target if started else record.Level,
                                  self.run.env.get('NewGoodsAvailable'), record.PauseOffers))
        self.run.native.update(show_notification=message, write_to_logbook=message)

    def finish(self, record):
        hub = record.Hub
        hub.constructionsequence = record.TargetSequence
        hub.planmodule = Table({e.id: Component(exists=True, isoperational=True) for e in record.TargetSequence})
        hub.isoperational = True
        hub.buildstorage.builds.inprogress.clear()
        self.run.env.update(R=record, Hub=hub)
        self.run.library('UpdateHub')

    def operational(self):
        record = self.start()
        self.complete()
        self.finish(record)
        self.assertEqual(self.messages, [])  # Initial build is not an upgrade.
        return record

    def request(self, record, target):
        record.Target = target
        self.run.env.update(R=record, Hub=record.Hub)
        self.run.library('QueueExpansion')

    def test_announces_start_and_finish_once_and_only_after_native_transitions(self):
        record = self.operational()
        self.request(record, 2)
        self.assertEqual(self.messages, [])  # Layout request alone is not construction.
        self.complete(index=1)
        self.assertEqual([m[1] for m in self.messages], ['started', 'started'])
        self.run.actions(self.run.tree.xpath('//cue[@name="Reload"]/actions')[0])
        record.Build = NIL
        record.Hub.buildstorage.builds.inprogress.clear()
        self.run.library('QueueExpansion')  # Recover a lost native task.
        self.assertEqual(len(self.messages), 2)
        self.run.library('UpdateHub')
        self.assertEqual(len(self.messages), 2)  # Modules have not completed.
        self.finish(record)
        self.assertEqual([m[1] for m in self.messages], ['started', 'started', 'completed', 'completed'])
        self.assertTrue(self.messages[-1][4])  # Energy cells unlock at level 2.
        self.run.library('UpdateHub')
        self.run.actions(self.run.tree.xpath('//cue[@name="Reload"]/actions')[0])
        self.run.library('UpdateHub')
        self.assertEqual(len(self.messages), 4)
        self.assertTrue(all(m[2] is record.Hub for m in self.messages))

    def test_failed_task_does_not_announce_until_retry_succeeds(self):
        record = self.operational()
        self.request(record, 2)
        self.fail_build = True
        self.complete(index=1)
        self.assertEqual(self.messages, [])
        self.fail_build = False
        self.retry()
        self.complete(index=2)
        self.assertEqual(len(self.messages), 2)

    def test_quantity_only_level_and_paused_offers_have_distinct_message_inputs(self):
        record = self.operational()
        self.request(record, 9)
        self.complete(index=1)
        self.finish(record)
        self.assertTrue(self.messages[-1][4])  # A debug jump includes intermediate unlocks.
        self.request(record, 10)
        self.complete(index=2)
        record.PauseOffers = True
        self.finish(record)
        self.assertFalse(self.messages[-1][4])
        self.assertTrue(self.messages[-1][5])

    def test_hub_loss_clears_start_deduplication(self):
        record = self.operational()
        self.request(record, 2)
        self.complete(index=1)
        self.assertEqual(record.UpgradeNotifiedTarget, 2)
        self.run.library('ForgetHub')
        self.assertEqual(record.UpgradeNotifiedTarget, 0)
