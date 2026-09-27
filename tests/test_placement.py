"""Current-plot-first retries exercise the real construction/placement libraries."""
from support import Table, List, NIL, Component
from support_startup import StartupHarness
from support_construction import sequence


class PlotRetryTests(StartupHarness):
    def state(self,record):
        return self.run.env['md'].CE_Placement.State.Sites[record.Hub]

    def exhaust_plot_attempts(self):
        for _ in range(3):
            self.complete(index=len(self.pending)-1,success=False)
            self.retry()

    def test_initial_layout_uses_default_plot_without_enlargement(self):
        self.safe_plot=False
        record=self.start()
        self.assertEqual(len(self.pending),1)
        self.assertEqual(self.plot_calls,[])
        self.assertFalse(record.Hub.buildstorage.exists)
        self.complete()
        self.assertTrue(record.Build.exists)
        self.assertTrue(record.Hub.buildstorage.exists)
        self.assertEqual(list(record.Hub.buildplot.max.values()),[5000]*3)
        self.assertEqual(self.moves,[])

    def test_failure_waits_then_grows_exactly_checked_increment(self):
        record=self.start()
        self.assertEqual(self.pending[-1]['LayoutBias'],1.0)
        for bias in (0.5,2.0):
            self.complete(index=len(self.pending)-1,success=False)
            self.assertEqual(self.state(record).NextTry,self.run.env['player'].age+1)
            self.assertFalse(record.PlotReady)
            count=len(self.pending);self.start();self.assertEqual(len(self.pending),count)
            self.retry()
            self.assertEqual(self.pending[-1]['LayoutBias'],bias)
            self.assertEqual(self.plot_calls,[])
        self.complete(index=2,success=False)
        self.assertEqual(self.state(record).NextTry,self.run.env['player'].age+300)
        self.retry()
        self.assertEqual(self.plot_calls,[dict(negx=2000,posx=2000,negy=2000,posy=2000,negz=2000,posz=2000)])
        self.assertEqual(list(record.Hub.buildplot.max.values()),[7000]*3)
        self.assertEqual(self.moves,[])
        self.assertEqual(self.pending[-1]['LayoutBias'],1.0)
        self.complete(index=3)
        self.assertEqual(self.state(record).Failures,0)
        self.assertTrue(record.PlotReady)

    def test_blocked_extension_repositions_only_empty_shell_and_bounds_moves(self):
        self.safe_plot=False
        record=self.start(); hub=record.Hub
        for i in range(5):
            self.exhaust_plot_attempts()
        self.assertEqual(self.moves,[hub]*3)
        self.assertIs(record.Hub,hub)
        self.assertEqual(self.state(record).Moves,3)
        self.assertEqual(list(hub.buildplot.max.values()),[5000]*3)
        self.assertFalse(hub.buildstorage.exists)
        self.assertEqual(len(self.hubs),1)
        self.complete(index=len(self.pending)-1)
        self.assertTrue(record.Build.exists)

    def test_relocation_guards_cover_every_nonempty_state(self):
        for guard in ('operational','initialized','completed','target','build','pending','modules','storage','owner','wreck','destroyed'):
            with self.subTest(guard=guard):
                self.setUp(); record=self.start(); record.LayoutPending=False
                hub=record.Hub
                if guard=='operational':record.Operational=True
                if guard=='initialized':record.InitializedHub=hub
                if guard=='completed':record.CompletedSequence=sequence([self.components['storage']])
                if guard=='target':record.TargetSequence=sequence([self.components['storage']])
                if guard=='build':record.Build=Component(exists=True)
                if guard=='pending':record.LayoutPending=True
                if guard=='modules':hub.constructionsequence=sequence([self.components['storage']])
                if guard=='storage':hub.buildstorage=Component(exists=True)
                if guard=='owner':hub.owner='player'
                if guard=='wreck':hub.iswreck=True
                if guard=='destroyed':hub.exists=False
                self.run.env.update(R=record,Hub=hub,Placement=self.state(record))
                self.run.library('md.CE_Placement.Relocate')
                self.assertEqual(self.moves,[])
                self.assertEqual(self.state(record).Moves,0)

    def test_off_center_and_oversized_plots_never_shrink_or_shift_center(self):
        record=self.start(); hub=record.Hub
        hub.buildplot.max=Table(x=15000,y=17000,z=7000)
        hub.buildplot.center=Table(x=4000,y=-2000,z=1000)
        self.exhaust_plot_attempts()
        self.assertEqual(self.plot_calls[0],dict(negx=1000,posx=1000,negy=0,posy=0,negz=2000,posz=2000))
        self.assertEqual(list(hub.buildplot.max.values()),[16000,17000,9000])
        self.assertEqual(list(hub.buildplot.center.values()),[4000,-2000,1000])

    def test_size_cap_skips_enlargement_and_attempts_empty_placement(self):
        record=self.start(); record.Hub.buildplot.max=Table(x=16000,y=16000,z=16000)
        self.exhaust_plot_attempts()
        self.assertEqual(self.plot_calls,[])
        self.assertEqual(self.moves,[record.Hub])

    def test_failed_extension_action_detects_no_change(self):
        self.run.native['extend_build_plot']=lambda n:None
        record=self.start(); self.exhaust_plot_attempts()
        self.assertEqual(self.moves,[record.Hub])
        self.assertTrue(any('extension_no_change' in args for _,args in self.logs))

    def test_malformed_result_and_failed_build_retry_without_growth(self):
        record=self.start()
        self.complete(result=sequence([self.components['storage']]))
        self.assertFalse(self.state(record).Resize)
        self.retry(); self.fail_build=True; self.complete(index=1)
        self.retry()
        self.assertEqual(self.plot_calls,[]); self.assertEqual(self.moves,[])
        self.fail_build=False; self.retry()
        self.assertTrue(record.Build.exists)

    def test_established_hub_keeps_operating_and_preserves_base_when_blocked(self):
        record=self.start(); self.complete(); hub=record.Hub
        hub.constructionsequence=record.TargetSequence
        hub.planmodule=Table({entry.id:Component(exists=True,isoperational=True) for entry in record.TargetSequence})
        hub.isoperational=True; hub.buildstorage.builds.inprogress.clear()
        self.run.env.update(R=record,Hub=hub); self.run.library('UpdateHub')
        base=record.CompletedSequence
        record.LayoutPlans=NIL;record.LayoutPlanHub=NIL
        record.Target=2; self.run.library('QueueExpansion')
        self.safe_plot=False; self.complete(index=1,success=False)
        self.retry(); self.run.library('UpdateHub')
        self.assertTrue(record.Operational)
        self.assertEqual((record.Level,record.Target),(1,2))
        self.assertIs(record.CompletedSequence,base)
        self.assertEqual(self.moves,[])
        self.complete(index=2)
        self.assertTrue(record.Build.exists)

    def test_saved_retry_state_and_reload_preserve_delay_and_attempt_count(self):
        record=self.start(); self.complete(success=False)
        sites=self.run.env['md'].CE_Placement.State.Sites
        before=dict(self.state(record))
        # MD stores cue variables and object-keyed tables. Reattach a copied state
        # table as a save/load stand-in; actual engine restoration is a runtime gate.
        sites[record.Hub]=Table(before)
        self.run.actions(self.run.tree.xpath('//cue[@name="Reload"]/actions')[0])
        self.start(); self.assertEqual(len(self.pending),1)
        self.assertEqual(dict(self.state(record)),before)
        self.retry(); self.assertEqual(self.state(record).Attempts,2)
        self.complete(index=0)
        self.assertTrue(record.LayoutPending)
        self.assertFalse(record.Build.exists)
        self.complete(index=1)
        self.assertTrue(record.Build.exists)

    def test_logs_identify_retry_reason_hub_sector_attempt_and_result(self):
        self.safe_plot=False
        record=self.start(); self.exhaust_plot_attempts(); self.complete(index=len(self.pending)-1)
        kinds=[template.split(':')[0] for template,_ in self.logs]
        for kind in ('Layout attempt','Layout retry scheduled','Plot retry','Placement retry','Layout retry resolved'):
            self.assertIn('[CE] '+kind,kinds)
        for template,args in self.logs:
            self.assertIs(args[0],record.Hub)
            self.assertIs(args[1],self.sector)
            self.assertEqual(args[2],'Test sector')
            self.assertIn('attempt=%s',template)
        failed=next(args for template,args in self.logs if 'retry scheduled' in template)
        self.assertIn('generation_failed',failed)
        self.assertTrue(any('extension_unsafe' in args for _,args in self.logs))
        self.assertTrue(any('empty_shell_repositioned' in args for _,args in self.logs))

    def test_noop_warp_is_logged_as_no_change_and_consumes_bounded_attempt(self):
        self.safe_plot=False
        self.run.native['warp']=lambda n:None
        record=self.start(); self.exhaust_plot_attempts()
        self.assertEqual(self.state(record).Moves,1)
        self.assertTrue(any('relocation_no_change' in args for _,args in self.logs))

    def test_rejected_duplicate_callback_does_not_delay_new_attempt(self):
        record=self.start(); self.complete(success=False)
        before=dict(self.state(record)); log_count=len(self.logs)
        self.complete(success=False)
        self.assertEqual(dict(self.state(record)),before)
        self.assertEqual(len(self.logs),log_count)
        self.retry(); current=dict(self.state(record))
        self.complete(index=0,success=False)
        self.assertEqual(dict(self.state(record)),current)
        self.assertTrue(record.LayoutPending)

    def test_forgetting_hub_discards_only_that_sites_retry_state(self):
        first=self.start(); self.complete(success=False)
        other=Component(exists=True,isclass=Table(sector=True),owner=self.owner,knownname='Other')
        second=self.start(other)
        self.run.env['R']=first
        self.run.library('md.CE_Placement.Forget')
        sites=self.run.env['md'].CE_Placement.State.Sites
        self.assertNotIn(first.Hub,sites)
        self.assertIn(second.Hub,sites)

    def test_old_saved_resize_gets_same_plot_attempts_before_enlargement(self):
        record=self.start();self.complete(success=False)
        site=self.state(record)
        del site['SamePlotFailures'];site.Resize=True
        self.retry()
        self.assertEqual(self.plot_calls,[])
        self.assertEqual(site.SamePlotFailures,0)
        self.assertFalse(site.Resize)

    def test_unstageable_candidates_do_not_enlarge_plot(self):
        record=self.start()
        for _ in range(3):
            self.complete(index=len(self.pending)-1,result=sequence([self.components['storage']]))
            self.retry()
        self.assertEqual(self.plot_calls,[])
        self.assertEqual(self.moves,[])
        self.assertFalse(record.Build.exists)
