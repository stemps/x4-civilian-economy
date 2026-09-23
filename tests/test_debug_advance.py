"""Execute target-level requests against native-mocked startup libraries."""
from support import Table, List, NIL, Component
from test_hub_startup import StartupHarness

class DebugAdvanceTests(StartupHarness):
    def operational(self):
        record=self.start();self.complete();self.finish_modules(record)
        return record

    def finish_modules(self, record):
        hub=record.Hub
        hub.constructionsequence=record.TargetSequence
        hub.planmodule=Table({e.id:Component(exists=True,isoperational=True) for e in record.TargetSequence})
        hub.isoperational=True;hub.buildstorage.builds.inprogress.clear()
        self.run.env.update(R=record,Hub=hub);self.run.library('UpdateHub')

    def command(self,record,command,hub=None):
        self.run.env['event']=Table(param2=command,param3=hub or record.Hub)
        self.run.actions(self.run.tree.xpath('//cue[@name="TestingCommand"]/actions')[0])

    def test_jump_one_to_ten_preserves_base_and_commits_only_after_modules_ready(self):
        record=self.operational();base=record.CompletedSequence
        raised=[]
        self.run.native['raise_lua_event']=lambda n:raised.append((self.run.expr(n.get('name')),self.run.expr(n.get('param'))))
        self.command(record,'advance_level_10')
        self.assertEqual((record.Level,record.Target),(1,10))
        self.assertTrue(record.TestUpgrade)
        self.assertIs(self.pending[1]['Base'],base)
        self.assertEqual(self.pending[1]['RequiredMacros'].count,17)
        self.command(record,'advance_level_10');self.assertEqual(len(self.pending),2)
        self.complete(index=1)
        self.assertEqual(raised,[('CEAdvanceBuildReady',record.Hub)])
        self.assertEqual(record.Level,1)
        for entry in base:self.assertIs(record.TargetSequence[entry.id].macro,entry.macro)
        self.finish_modules(record)
        self.assertEqual((record.Level,record.Target),(10,0))
        self.assertFalse(record.TestUpgrade)
        self.run.library('md.CE_DebugAdvance.Tick')
        self.assertNotIn(record.Hub,self.run.env['md'].CE_DebugAdvance.State.Targets)
        self.assertEqual(len(raised),1)

    def test_invalid_downgrade_busy_and_wrong_identity_commands_do_not_generate(self):
        record=self.operational()
        for command in ('advance_level_0','advance_level_1','advance_level_11','advance_level_2.5','advance_level_bad'):
            self.command(record,command)
        self.command(record,'advance_level_5',Component(exists=True))
        self.assertEqual(len(self.pending),1)
        record.Hub.owner='player';self.command(record,'advance_level_5')
        self.assertEqual(len(self.pending),1)
        record.Hub.owner='ownerless';record.Target=2
        self.command(record,'advance_level_5');self.assertEqual(record.Target,2)
        self.assertEqual(len(self.pending),1)

    def test_generation_failure_retains_request_for_retry_and_reload(self):
        record=self.operational();self.command(record,'advance_level_4')
        self.complete(index=1,success=False)
        self.assertEqual(record.Level,1)
        self.assertEqual(self.run.env['md'].CE_DebugAdvance.State.Targets[record.Hub],4)
        self.run.actions(self.run.tree.xpath('//cue[@name="Reload"]/actions')[0])
        self.retry();self.complete(index=2)
        self.assertTrue(record.Build.exists);self.assertEqual(record.Target,4)

    def test_normal_upgrade_never_requests_auto_completion_and_owner_change_cancels(self):
        record=self.operational();raised=[]
        self.run.native['raise_lua_event']=lambda n:raised.append(n.get('name'))
        self.command(record,'queue_upgrade');self.complete(index=1)
        self.assertEqual(raised,[])
        self.finish_modules(record);self.command(record,'advance_level_5')
        record.Hub.owner='player'
        self.run.library('md.CE_DebugAdvance.Tick')
        self.assertNotIn(record.Hub,self.run.env['md'].CE_DebugAdvance.State.Targets)

    def test_destroyed_hub_forgets_auto_completion_permission(self):
        record=self.operational();self.command(record,'advance_level_4');hub=record.Hub
        self.run.library('ForgetHub')
        self.assertNotIn(hub,self.run.env['md'].CE_DebugAdvance.State.Targets)
