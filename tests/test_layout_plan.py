"""Forward-plan contracts. Native geometry remains an in-game acceptance gate."""
from support import Table, NIL, Component
from support_startup import StartupHarness
from support_construction import sequence


class LayoutPlanTests(StartupHarness):
    def finish(self, record):
        hub=record.Hub
        hub.constructionsequence=record.TargetSequence
        hub.planmodule=Table({e.id:Component(exists=True,isoperational=True) for e in record.TargetSequence})
        hub.isoperational=True;hub.buildstorage.builds.inprogress.clear()
        self.run.env.update(R=record,Hub=hub);self.run.library('UpdateHub')

    def test_new_hub_prepares_all_levels_and_builds_only_requested_stage(self):
        record=self.start()
        self.assertEqual(self.pending[0]['BuildLevel'],1)
        for level in range(1,10):
            self.complete(all_stages=False)
            self.assertFalse(record.Build.exists)
            self.assertFalse(record.Hub.buildstorage.exists)
            self.assertIs(record.LayoutPlans,NIL)
            self.assertEqual(self.pending[0]['BuildLevel'],level+1)
        self.complete()
        self.assertEqual(record.LayoutPlans.count,10)
        self.assertEqual(record.TargetSequence.count,3)
        self.assertIs(record.LayoutPlanHub,record.Hub)
        for level,total in enumerate((3,4,5,7,8,10,12,13,14,17),1):
            stage=record.LayoutPlans[level]
            self.assertEqual(stage.count,total)
            self.assertEqual(sum(e.macro is self.components['storage'] for e in stage),level)
            if level<10:
                for entry in stage:
                    self.assertIs(record.LayoutPlans[level+1][entry.id].macro,entry.macro)
        plans=record.LayoutPlans
        self.finish(record)
        native_calls=[]
        self.run.native['create_construction_sequence']=lambda n:native_calls.append(n)
        for level in range(2,11):
            record.Target=level;self.run.library('QueueExpansion')
            self.assertIs(record.TargetSequence,plans[level])
            self.assertEqual(record.Level,level-1)
            self.finish(record)
            self.assertEqual(record.Level,level)
        self.assertEqual(native_calls,[])
        self.assertEqual(self.plot_calls,[])

    def test_missing_modules_reject_whole_candidate_before_building(self):
        record=self.start()
        self.complete(result=sequence([self.components['storage']]))
        self.assertIs(record.LayoutPlans,NIL)
        self.assertFalse(record.Build.exists)
        self.assertFalse(record.Hub.buildstorage.exists)
        self.assertEqual(record.ConstructionFailure,'staged_layout_invalid')

    def test_reassigned_ids_and_generation_failures_are_rejected(self):
        for mode in ('ids','generation'):
            with self.subTest(mode=mode):
                self.setUp();record=self.start()
                self.complete(all_stages=False)
                candidate=sequence(self.pending[0]['RequiredMacros'])
                candidate[1].id='changed'
                self.complete(success=mode!='generation',result=candidate)
                self.assertIs(record.LayoutPlans,NIL)
                self.assertFalse(record.Build.exists)
                self.assertEqual(self.pending[0]['CandidatePlans'].count,0)

    def test_failed_extension_retries_same_base_then_discards_candidate(self):
        record=self.start()
        for _ in range(5): self.complete(all_stages=False)
        context=self.pending[0];base=context['Base']
        self.assertEqual(context['BuildLevel'],6)
        self.complete(success=False,all_stages=False)
        self.assertIs(context['Base'],base)
        self.assertEqual((context['BuildLevel'],context['StageAttempt']),(6,2))
        self.complete(success=False)
        self.assertFalse(record.LayoutPending)
        self.assertIs(record.LayoutPlans,NIL)
        self.assertEqual(record.ConstructionFailure,'generation_failed')
        self.retry()
        self.assertEqual(self.pending[1]['BuildLevel'],1)
        self.assertIs(self.pending[1]['Base'],NIL)

    def test_recovered_extension_preserves_stages_and_requests_only_additions(self):
        record=self.start();self.complete(all_stages=False)
        context=self.pending[0];base=context['Base']
        self.assertEqual(list(context['NewMacros']),[self.components['storage']])
        self.complete(success=False,all_stages=False)
        self.complete()
        self.assertIs(record.LayoutPlans[1],base)
        self.assertEqual(record.TargetSequence.count,3)

    def test_saved_stages_survive_failed_task_and_reload_but_not_hub_loss(self):
        record=self.start();self.fail_build=True;self.complete()
        plans=record.LayoutPlans
        self.assertEqual(plans.count,10)
        self.assertFalse(record.Build.exists)
        self.run.actions(self.run.tree.xpath('//cue[@name="Reload"]/actions')[0])
        self.fail_build=False;self.retry()
        self.assertTrue(record.Build.exists)
        self.assertIs(record.LayoutPlans,plans)
        self.assertIs(record.TargetSequence,plans[1])
        self.run.env.update(R=record,Hub=record.Hub);self.run.library('ForgetHub')
        self.assertIs(record.LayoutPlans,NIL)
        self.assertIs(record.LayoutPlanHub,NIL)

    def test_jump_five_to_ten_uses_saved_plan_and_native_readiness(self):
        record=self.start();self.complete();self.finish(record)
        record.Target=5;self.run.library('QueueExpansion');self.finish(record)
        base=record.CompletedSequence
        self.run.env['event']=Table(param2='advance_level_10',param3=record.Hub)
        self.run.actions(self.run.tree.xpath('//cue[@name="TestingCommand"]/actions')[0])
        self.assertEqual((record.Level,record.Target),(5,10))
        self.assertIs(record.TargetSequence,record.LayoutPlans[10])
        for entry in base:self.assertIs(record.TargetSequence[entry.id].macro,entry.macro)
        self.finish(record)
        self.assertEqual((record.Level,record.Target),(10,0))

    def test_old_hub_still_generates_additions_against_completed_base(self):
        record=self.start();self.complete();self.finish(record)
        record.LayoutPlans=NIL;record.LayoutPlanHub=NIL
        base=record.CompletedSequence
        record.Target=5;self.run.library('QueueExpansion')
        request=self.pending[-1]
        self.assertFalse(request['PlanAhead'])
        self.assertIs(request['Base'],base)
        self.assertEqual(request['RequiredMacros'].count,8)
        self.assertTrue(record.LayoutPending)

    def test_diagnostics_distinguish_layout_retry_from_native_build(self):
        record=self.start()
        def phase():
            self.run.env.update(R=record,Hub=record.Hub)
            self.run.library('PublishDiagnostics')
            return record.Snapshot[22]
        self.assertEqual(phase(),'planning')
        self.complete(success=False)
        self.assertEqual(phase(),'layout_retry')
        self.retry();self.assertEqual(phase(),'planning')
        self.fail_build=True;self.complete(index=1)
        self.assertEqual(phase(),'build_retry')
        self.fail_build=False;self.retry()
        self.assertEqual(phase(),'')

    def test_other_hub_cannot_use_saved_plans(self):
        record=self.start();self.complete();self.finish(record)
        record.LayoutPlanHub=Component(exists=True)
        record.Target=2;self.run.library('QueueExpansion')
        self.assertTrue(record.LayoutPending)
        self.assertFalse(record.Build.exists)
