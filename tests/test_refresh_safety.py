"""Failure boundaries: use actual MD actions, including continued engine errors."""
import copy
import unittest
import test_profiles
from test_prototype import Table, List, Ware, NIL
from test_galaxy import Object


class RefreshSafetyTests(unittest.TestCase):
    def setUp(self):
        fixture=test_profiles.ProfileTests()
        fixture.setUp()
        fixture.apply()
        self.run,self.r=fixture.run,fixture.r
        self.r['Hub']=Object(exists=True,iswreck=False)
        self.r.Wares['water'].update(Reserve=125,Delivered=75,Paid=90000)
        self.r['GrowthSeconds']=1080
        self.run.library('AccrueAll')
        self.run.env['Registry']=Table({Object(self.run.env['Sector']):self.r})
        self.run.env['player']['entity']=Table()

    def protected(self):
        return copy.deepcopy({key:self.r[key] for key in
                              ('Definitions','Wares','Level','Target','GrowthSeconds','Transfers','DisplayOrder')})

    def test_builder_does_not_mutate_saved_profile_or_demand(self):
        before=self.protected()
        self.run.library('md.CE_PopulationProfiles.Build')
        self.assertEqual(self.protected(),before)
        self.assertTrue(self.run.env['CandidateComplete'])

    def test_missing_discovery_keeps_last_valid_state_and_recovers(self):
        before=self.protected()
        lookup=self.run.env['lookup']
        self.run.env['lookup']=Table(ware=Table(list=List()),race=Table(list=List()))
        self.run.library('RefreshProfile')
        self.assertTrue(self.r.ProfileError)
        self.assertEqual(self.protected(),before)
        self.run.env['lookup']=lookup
        self.run.library('RefreshProfile')
        self.assertFalse(self.r.ProfileError)
        self.assertEqual(self.protected(),before)

    def test_interrupted_candidate_cannot_commit_previous_scratch(self):
        before=self.protected()
        self.run.env.update(CandidateComplete=True,CandidateValid=True,CandidateDefinitions=List())
        self.run.stubs['md.CE_PopulationProfiles.Build']=lambda:None
        self.run.library('RefreshProfile')
        self.assertTrue(self.r.ProfileError)
        self.assertEqual(self.protected(),before)

    def test_invalid_string_key_continues_like_engine_without_committing(self):
        before=self.protected()
        node=self.run.profiles.xpath('//set_value[starts-with(@name,"$ProfileWares.{")]')[0]
        node.set('name','$ProfileWares.{$ProfileWare.id}')
        self.run.continue_on_invalid_key=True
        self.run.library('RefreshProfile')
        self.assertTrue(self.run.engine_errors)
        self.assertTrue(self.r.ProfileError)
        self.assertEqual(self.protected(),before)

    def test_interrupted_rate_preparation_cannot_commit(self):
        before=self.protected()
        self.run.env['CandidateRatesComplete']=True
        self.run.stubs['PrepareRates']=lambda:None
        self.run.library('RefreshProfile')
        self.assertTrue(self.r.ProfileError)
        self.assertEqual(self.protected(),before)

    def test_malformed_configuration_is_not_an_intentionally_empty_profile(self):
        before=self.protected()
        node=self.run.profiles.xpath('//library[@name="Configure"]//set_value[@name="$ProfileCommon"]')[0]
        node.set('exact','null')
        self.run.library('RefreshProfile')
        self.assertTrue(self.r.ProfileError)
        self.assertEqual(self.protected(),before)

    def test_duplicate_or_invalid_rate_candidate_never_changes_live_state(self):
        before=self.protected()
        def candidate(rows):
            self.run.env.update(CandidateComplete=True,CandidateValid=True,
                                CandidateDefinitions=rows,CandidateRace='argon')
        for rows in (List([List([Ware('water'),1,2000]),List([Ware('water'),1,3000])]),
                     List([List([Ware('water'),1,-1])])):
            self.run.stubs['md.CE_PopulationProfiles.Build']=lambda: candidate(rows)
            self.run.library('RefreshProfile')
            self.assertEqual(self.protected(),before)
            self.assertTrue(self.r.ProfileError)

    def test_snapshot_reads_live_state_without_definitions_or_controller_scope(self):
        self.r.pop('Definitions')
        deal=Object(buyer=self.r.Hub,transferredamount=25,unitprice=1200)
        self.r.Transfers[deal]=Ware('water')
        # Only explicitly captured state and engine globals exist in this scope.
        self.run.env={key:self.run.env[key] for key in ('player','Registry','null','true','false')}
        self.run.env.update(R=self.r,Hub=self.r.Hub,event=Table(param=deal))
        self.run.stubs['UpdateOffers']=lambda:None
        self.run.library('RecordDelivery')
        self.assertEqual([row[1] for row in self.r.Snapshot[9]],['foodrations','water'])
        self.assertEqual(self.r.Snapshot[9][2][2],150)
        self.assertEqual(self.r.Snapshot[9][2][6],100)
        self.assertFalse(self.r.Snapshot[15])

    def test_incomplete_snapshot_retains_previous_rows_and_recovers(self):
        self.run.library('PublishDiagnostics')
        old=self.r.Snapshot
        order=self.r.DisplayOrder
        self.r['DisplayOrder']=List()
        self.run.library('PublishDiagnostics')
        self.assertEqual(self.r.Snapshot[9],old[9])
        self.assertTrue(self.r.Snapshot[15])
        self.r['DisplayOrder']=order
        self.run.library('PublishDiagnostics')
        self.assertFalse(self.r.Snapshot[15])

    def test_metadata_migration_does_not_reset_history(self):
        old_history=self.r.Wares['water'].Reserve
        self.r.pop('DisplayOrder')
        for w in self.r.Wares.values():w.pop('Active')
        self.run.library('PublishDiagnostics')
        self.assertEqual(self.r.GrowthSeconds,1080)
        self.assertEqual(self.r.Wares['water'].Reserve,old_history)
        self.assertEqual([row[1] for row in self.r.Snapshot[9]],['foodrations','water'])

    def test_intentionally_empty_profile_is_valid_but_failed_first_profile_is_not(self):
        self.run.env['lookup'].race.list=List([Table(id='argon',workforce=Table(resources=List()))])
        configure=self.run.profiles.xpath('//library[@name="Configure"]/actions/set_value[@name="$ProfileCommon"]')[0]
        configure.set('exact','[]')
        self.run.library('RefreshProfile')
        self.run.library('PublishDiagnostics')
        self.assertFalse(self.r.ProfileError)
        self.assertEqual(self.r.Snapshot[9],[])
        self.assertFalse(self.r.Snapshot[15])
        self.r.pop('Definitions');self.r.pop('Snapshot')
        self.run.library('PublishDiagnostics')
        self.assertTrue(self.r.SnapshotError)
        self.assertIs(self.r.Snapshot,NIL)

    def test_reload_actions_preserve_history_and_deal_references(self):
        deal=Object(exists=True)
        self.r.Transfers[deal]=Ware('water')
        history=self.r.Wares['water'].Reserve
        self.run.native['cancel_cue']=lambda n:None
        self.run.stubs.update(Reconcile=lambda:None,RenameHub=lambda:None)
        self.run.actions(self.run.tree.xpath('//cue[@name="Reload"]/actions')[0])
        self.assertEqual(self.r.Wares['water'].Reserve,history)
        self.assertIn(deal,self.r.Transfers)
        self.assertEqual(self.r.GrowthSeconds,1080)
        self.assertEqual(len(self.r.Snapshot[9]),2)
