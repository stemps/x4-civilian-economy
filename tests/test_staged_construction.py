"""Production progression, identity and reset contracts; native actions mocked."""
from support import Table, List, NIL, Component
from support_startup import StartupHarness

class StagedConstructionTests(StartupHarness):
    def test_initial_build_retries_until_native_ready_then_revokes_permission(self):
        record=self.start();record.InitialHub=record.Hub
        self.run.env['md'].CE_CivilianHub.Init.Registry=self.run.env['Registry']
        attempts=[]
        self.run.native['raise_lua_event']=lambda n:attempts.append(n.get('name'))
        self.complete()
        self.assertFalse(record.Operational)
        self.assertEqual(attempts,["'CEInitialHubBuildReady'"])
        tick=self.run.construction.xpath('//cue[@name="InitialBuilds"]/actions')[0]
        self.run.actions(tick);self.assertEqual(len(attempts),1)
        self.run.env['player'].age+=2
        self.run.native['raise_lua_event']=self.initial_event
        self.run.actions(tick)
        self.assertTrue(record.Operational)
        self.assertIs(record.InitialHub,NIL)
        self.assertEqual(self.run.env['player'].entity.ce_initial_build_hubs,List())
        self.run.actions(tick)
        self.assertEqual(sum(k=='materialize' for k,_ in self.events),1)

    def finish(self,record):
        hub=record.Hub
        hub.constructionsequence=record.TargetSequence
        hub.planmodule=Table({e.id:Component(exists=True,isoperational=True) for e in record.TargetSequence})
        hub.isoperational=True;hub.buildstorage.builds.inprogress.clear()
        record.Build.exists=False
        self.run.env.update(R=record,Hub=hub,Sector=hub.sector)
        self.run.library('UpdateHub')

    def test_all_ten_stages_reuse_one_master_and_preserve_ids(self):
        record=self.start();self.complete();master=record.FullSequence
        previous=[]
        for level in range(1,11):
            if level>1:
                record.Target=level;self.start();self.complete(index=level-1)
            seq=record.TargetSequence
            self.assertEqual(seq.count,record.Construction.Levels[level].count)
            self.assertEqual([e.id for e in seq][:len(previous)],previous)
            self.assertIs(record.FullSequence,master)
            previous=[e.id for e in seq];self.finish(record)
            self.assertEqual(record.Level,level)
        self.assertIsInstance(self.native_requests[0][0],str)
        self.assertTrue(all(source is master for source,level in self.native_requests[1:]))
        self.assertEqual([level for source,level in self.native_requests],list(range(1,11)))

    def test_lost_task_requeues_the_same_stage_and_master(self):
        record=self.start();self.complete();master=record.FullSequence;ids=list(record.PlanIDs)
        record.Build.exists=False;record.Hub.buildstorage.builds.inprogress.clear()
        self.start();self.complete(index=1)
        self.assertIs(self.native_requests[-1][0],master)
        self.assertEqual(self.native_requests[-1][1],1)
        self.assertEqual(record.PlanIDs,ids)

    def test_invalid_stage_or_macro_never_processes_build(self):
        for mutation in ('id','macro','boundary','count'):
            with self.subTest(mutation=mutation):
                self.setUp();record=self.start();self.complete();self.finish(record)
                source=record.FullSequence
                if mutation=='id':record.PlanIDs[1]='wrong'
                elif mutation=='macro':source[1].macro=Component(id='wrong')
                elif mutation=='boundary':source.stage[1].last+=1
                else:source.pop()
                record.Target=2;self.start()
                before=sum(k=='process' for k,_ in self.events)
                self.complete(index=1)
                self.assertTrue(record.ConstructionError)
                self.assertEqual(sum(k=='process' for k,_ in self.events),before)
                self.assertFalse(record.Build.exists)

    def test_failure_uses_bounded_backoff_without_plot_growth(self):
        record=self.start();self.fail_build=True;self.complete()
        state=self.run.env['md'].CE_Placement.State.Sites[record.Hub]
        self.assertEqual(state.NextTry,self.run.env['player'].age+300)
        self.start();self.assertEqual(len(self.pending),1)
        self.fail_build=False;self.retry();self.complete(index=1)
        self.assertFalse(record.ConstructionError)
        self.assertEqual(self.moves,[]);self.assertEqual(self.plot_calls,[])
