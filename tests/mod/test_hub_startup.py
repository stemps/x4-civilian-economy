"""Startup orchestration executes shipped libraries; only native actions are mocked."""
import unittest
from support import Table, List, NIL, Component
from support_startup import StartupHarness


class HubStartupTests(StartupHarness):
    def test_fresh_init_to_operational_with_real_startup_libraries(self):
        r=self.run; builder=self.builder()
        r.actions(r.tree.xpath('//cue[@name="Init"]/actions')[0])
        r.env['md'].CE_CivilianHub.Init.Registry=r.env['Registry']
        self.assertIn(self.sector,r.env['SectorProfiles'])
        r.env['player'].entity.ce_population_response=List([r.env['PopulationRequest'],List([List([self.sector,100000000])])])
        r.actions(r.tree.xpath('//cue[@name="PopulationReceived"]/actions')[0])
        record=r.env['Registry'][self.sector]; hub=record.Hub
        self.assertFalse(record.Operational); self.assertIs(hub.constructionsequence,NIL)
        self.complete()
        self.assertTrue(hub.buildstorage.exists)
        self.assertEqual(sum(kind=='materialize' for kind,_ in self.events),1)
        self.assertEqual(sum(kind=='queue' for kind,_ in self.events),1)
        self.assertEqual(record.FullSequence.stage.count,10)
        self.assertEqual(hub.constructionsequence.count,record.Construction.Levels[1].count)
        self.assertEqual(hub.owner,'civilian')
        self.assertTrue(record.Operational); self.assertIs(record.TargetSequence,NIL)
        self.assertEqual(hub.tradenpc.owner,'civilian')
        self.assertTrue(all(w.Offer.exists for w in record.Wares.values() if w.Rate>0))

    def test_no_builder_then_later_retry_without_duplicate_build_or_order(self):
        record=self.start(); self.complete()
        self.assertFalse(record.Hub.buildstorage.buildmodule.constructionvessel.exists)
        self.builder(); self.start(); self.start(); self.complete()
        self.assertEqual(sum(k=='queue' for k,_ in self.events),1)
        self.assertEqual(sum(k=='order' for k,_ in self.events),1)

    def test_unsuccessful_and_null_results_retry_without_queueing(self):
        for success,result in [(False,None),(True,NIL)]:
            with self.subTest(success=success):
                self.setUp(); record=self.start(); self.complete(success=success,result=result)
                self.assertFalse(record.LayoutPending); self.assertTrue(record.ConstructionError)
                self.assertFalse(any(k=='process' for k,_ in self.events))
                self.start(); self.assertEqual(len(self.pending),1)
                self.retry(); self.assertEqual(len(self.pending),2)

    def test_failed_build_creation_can_retry(self):
        record=self.start(); self.fail_build=True; self.complete()
        self.assertTrue(record.ConstructionError); self.assertFalse(record.Build.exists)
        self.assertFalse(record.LayoutPending)
        self.fail_build=False; self.retry(); self.complete(index=1)
        self.assertTrue(record.Build.exists); self.assertFalse(record.ConstructionError)

    def test_recover_lost_task_reuses_layout_and_starts_builder(self):
        record=self.start(); self.complete(); original=record.TargetSequence
        record.Build.exists=False; record.Hub.buildstorage.builds.inprogress.clear()
        self.builder(); self.start(); self.start()
        self.assertEqual([e.id for e in record.TargetSequence],[e.id for e in original])
        self.assertEqual(len(self.pending),2)
        self.complete(index=1)
        self.assertEqual(sum(k=='queue' for k,_ in self.events),2)
        self.assertEqual(sum(k=='order' for k,_ in self.events),1)

    def test_two_hubs_complete_out_of_order_and_stale_callback_is_ignored(self):
        self.builder(); self.builder(); first=self.start()
        other=Component(exists=True,isclass=Table(sector=True),owner=self.owner,knownname='Other',macro=Table(id='other_sector_macro'))
        second=self.start(other)
        self.complete(index=1); self.complete(index=0)
        ordered=[hub for kind,hub in self.events if kind=='order']
        self.assertEqual(ordered,[second.Hub,first.Hub])
        self.complete(index=1)
        self.assertEqual(sum(k=='order' for k,_ in self.events),2)
        # A superseded request must not consume the newer request's pending flag.
        first.LayoutPending=True; first.LayoutToken+=1
        self.complete(index=0)
        self.assertTrue(first.LayoutPending)
        self.assertEqual(sum(k=='queue' for k,_ in self.events),2)

    def test_expansion_uses_completed_base_and_queues_only_added_modules(self):
        record=self.start(); self.complete(); r=self.run; hub=record.Hub
        hub.constructionsequence=record.TargetSequence
        hub.planmodule=Table({entry.id:Component(exists=True,isoperational=True) for entry in record.TargetSequence})
        hub.isoperational=True; hub.buildstorage.builds.inprogress.clear()
        r.env.update(R=record,Hub=hub); r.library('UpdateHub')
        base=record.CompletedSequence
        record.Target=2; r.library('QueueExpansion')
        self.complete(index=1)
        self.assertEqual(record.Level,1)
        self.assertIs(record.CompletedSequence,base)
        self.assertEqual(record.TargetSequence.count,record.Construction.Levels[2].count)
        for entry in base:
            self.assertIs(record.TargetSequence[entry.id].macro,entry.macro)
        self.assertEqual(sum(k=='queue' for k,_ in self.events),2)
        r.actions(r.tree.xpath('//cue[@name="Reload"]/actions')[0])
        self.start()
        self.assertEqual(sum(k=='queue' for k,_ in self.events),2)

    def test_completion_ignores_destroyed_reowned_or_replaced_hub(self):
        for changed in ('destroyed','owner','replaced'):
            with self.subTest(changed=changed):
                self.setUp(); record=self.start()
                if changed=='destroyed': record.Hub.exists=False
                elif changed=='owner': record.Hub.owner='argon'
                else: record.Hub=Component(exists=True)
                self.complete()
                self.assertFalse(any(k=='queue' for k,_ in self.events))

    def test_reload_restarts_pending_generation_and_preserves_queued_layout(self):
        record=self.start(); r=self.run
        r.actions(r.tree.xpath('//cue[@name="Reload"]/actions')[0])
        self.assertFalse(record.LayoutPending)
        self.start(); self.complete(index=0)
        self.assertFalse(record.Build.exists)
        self.complete(index=1); target=record.TargetSequence
        r.actions(r.tree.xpath('//cue[@name="Reload"]/actions')[0])
        self.start()
        self.assertIs(record.TargetSequence,target)
        self.assertEqual(sum(k=='queue' for k,_ in self.events),1)


if __name__ == '__main__': unittest.main()
