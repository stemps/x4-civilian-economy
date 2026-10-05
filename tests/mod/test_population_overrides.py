"""Population override layers, live application and options section (native UI mocked)."""
import unittest
from support import Runner, Table, List, NIL, definitions, Object


class OverrideHarness(unittest.TestCase):
    def setUp(self):
        self.run = r = Runner(); definitions(r)
        self.registry = Table(); self.created = []
        r.env.update(Registry=self.registry, faction=Table(ownerless='ownerless', civilian='civilian'))
        r.env['player']['entity'] = Table()
        for name in ('FundAccounts', 'QueueExpansion', 'AssignBuilder', 'RenameHub',
                     'UpdateHub', 'PublishDiagnostics', 'PublishAllDiagnostics'):
            r.stubs[name] = lambda: None
        r.native['add_to_group'] = lambda n: None
        r.native['set_build_plot'] = lambda n: None
        def create(n):
            hub = Object(exists=True, iswreck=False, owner=r.expr(n.get('owner')), sector=r.env['Sector'],
                         isclass=Table(container=False), buildstorage=NIL)
            self.created.append(hub); r.env['NewHub'] = hub
        r.native['create_station'] = create
        self.state = r.env['md'].CE_PopulationOverrides.State
        self.draft = r.env['md'].CE_PopulationOptions.Draft
        self.sectors = []

    def sector(self, name='Sector', macro=None):
        sector = Object(exists=True, isclass=Table(sector=True), knownname=name,
                        owner=Table(primaryrace=self.run.env['lookup'].race.list[1]),
                        macro=Table(id=macro or name.lower().replace(' ', '_') + '_macro'))
        self.run.env['Sector'] = sector
        self.run.library('md.CE_PopulationOverrides.RememberSector')
        self.sectors.append(sector)
        return sector

    def native(self, sector, population):
        """One Lua bridge row, as handled by PopulationReceived."""
        self.run.env.update(Sector=sector, Population=population)
        self.run.library('md.CE_PopulationOverrides.RememberNative')
        self.run.library('ReconcileSector')
        return self.registry[sector]

    def change(self, sector, action, millions=None):
        self.run.signals.clear()
        self.run.env.update(OverrideSector=sector, OverrideAction=action, OverrideMillions=millions)
        self.run.library('md.CE_PopulationOverrides.Change')
        valid = self.run.env['OverrideValid']
        self.assertEqual(self.run.signals, [('md.CE_CivilianHub.PopulationOverrideChanged', sector)] if valid else [])
        if valid:
            self.run.env['event'] = Table(param=sector)
            self.run.actions(self.run.tree.xpath('//cue[@name="PopulationOverrideChanged"]/actions')[0])
        return valid

    def effective(self, sector, native):
        self.run.env.update(Sector=sector, Population=native)
        self.run.library('md.CE_PopulationOverrides.Effective')
        return self.run.env['Population'], self.run.env['PopulationSource']


class PopulationOverrideTests(OverrideHarness):
    def test_player_override_replaces_native_including_zero(self):
        sector = self.sector('Argon Prime')
        record = self.native(sector, 8524100000)
        self.assertTrue(self.change(sector, 'add', 1000))
        self.assertEqual(record.Population, 1000000000)
        self.assertAlmostEqual(record.Wares['foodrations'].Rate, 7140 * 1000000000 / 8524100000)
        self.native(sector, 8524100000)
        self.assertEqual(record.Population, 1000000000)
        self.assertTrue(self.change(sector, 'set', 0))
        self.assertEqual(record.Population, 0)
        self.native(sector, 8524100000)
        self.assertEqual(record.Population, 0, 'a zero override must not fall back to native')

    def test_zero_results_apply_immediately(self):
        # In game, 'set 0' and a reset to a native 0 waited for the next reconcile.
        argon = self.sector('Argon Prime')
        record = self.native(argon, 8524100000)
        self.assertTrue(self.change(argon, 'add', 100000))
        self.assertEqual(record.Population, 100000000000)
        self.assertTrue(self.change(argon, 'set', 0))
        self.assertEqual(record.Population, 0)
        empty = self.sector('Family Tkr')
        self.run.env.update(Sector=empty, Population=0)
        self.run.library('md.CE_PopulationOverrides.RememberNative')
        self.assertTrue(self.change(empty, 'add', 31385))
        self.assertEqual(self.registry[empty].Population, 31385000000)
        self.assertTrue(self.change(empty, 'reset'))
        self.assertEqual(self.registry[empty].Population, 0)

    def test_native_zero_is_a_baseline(self):
        # Added before any reading; the first reading is a real 0 and must anchor.
        sector = self.sector('Family Kritt')
        self.assertTrue(self.change(sector, 'add', 6182))
        self.assertEqual(self.native(sector, 0).Population, 6182000000)
        self.assertEqual(self.state.Player['$family_kritt_macro'].Baseline, 0)
        self.assertEqual(self.native(sector, 400000000).Population, 6582000000)
        preset = self.sector('Preset Zero')
        self.state.Presets['$preset_zero_macro'] = 2000000000
        self.assertEqual(self.effective(preset, 0), (2000000000, 'preset'))
        self.assertEqual(self.state.PresetBaselines['$preset_zero_macro'], 0)
        self.assertEqual(self.effective(preset, 300000000), (2300000000, 'preset'))

    def test_empty_sector_override_creates_a_hub(self):
        sector = self.sector('Family Kritt')
        self.run.env.update(Sector=sector, Population=0)
        self.run.library('md.CE_PopulationOverrides.RememberNative')
        self.run.library('ReconcileSector')
        self.assertNotIn(sector, self.registry)
        self.assertTrue(self.change(sector, 'add', 5000))
        self.assertEqual(self.registry[sector].Population, 5000000000)
        self.assertEqual(len(self.created), 1)

    def test_override_is_anchored_to_native_growth(self):
        terraformed = self.sector('Black Hole Sun IV')
        self.run.env.update(Sector=terraformed, Population=0)
        self.run.library('md.CE_PopulationOverrides.RememberNative')
        self.assertTrue(self.change(terraformed, 'add', 2000))
        self.assertEqual(self.native(terraformed, 400000000).Population, 2400000000)
        # Saving again re-anchors at the current native value.
        self.assertTrue(self.change(terraformed, 'set', 2000))
        self.assertEqual(self.registry[terraformed].Population, 2000000000)
        lowered = self.sector('Argon Prime')
        self.native(lowered, 8524100000)
        self.assertTrue(self.change(lowered, 'add', 1000))
        self.assertEqual(self.native(lowered, 8624100000).Population, 1100000000)
        self.assertEqual(self.native(lowered, 8000000000).Population, 1000000000, 'growth is never negative')

    def test_missing_baseline_is_filled_from_first_reading(self):
        sector = self.sector('Unmeasured')
        self.assertTrue(self.change(sector, 'add', 2000))
        entry = self.state.Player['$unmeasured_macro']
        self.assertNotIn('Baseline', entry)
        self.assertEqual(self.registry[sector].Population, 2000000000, 'applies without a native reading')
        self.assertEqual(self.native(sector, 500000000).Population, 2000000000)
        self.assertEqual(entry.Baseline, 500000000)
        self.assertEqual(self.native(sector, 600000000).Population, 2100000000)

    def test_preset_layer_and_reset(self):
        sector = self.sector('Preset Sector')
        self.state.Presets['$preset_sector_macro'] = 3000000000
        self.state.Presets['$not_in_this_galaxy_macro'] = 9000000000
        self.assertEqual(self.effective(sector, 1000000000), (3000000000, 'preset'))
        self.assertEqual(self.state.PresetBaselines['$preset_sector_macro'], 1000000000)
        self.assertFalse(self.change(sector, 'add', 500), 'preset sectors cannot be added twice')
        self.assertTrue(self.change(sector, 'set', 500))
        self.assertEqual(self.effective(sector, 1000000000), (500000000, 'player'))
        self.assertTrue(self.change(sector, 'reset'))
        self.assertEqual(self.effective(sector, 1200000000), (3200000000, 'preset'))
        stray = Object(exists=True, isclass=Table(sector=True), macro=Table(id='not_in_this_galaxy_macro'))
        self.assertEqual(self.effective(stray, 7), (7, 'native'))

    def test_validation_and_duplicates(self):
        sector = self.sector('Valid')
        for bad in (-1, 100001, 'x', NIL):
            self.assertFalse(self.change(sector, 'add', bad))
        self.assertFalse(self.change(sector, 'set', 10), 'nothing to edit yet')
        self.assertFalse(self.change(sector, 'reset'))
        self.assertTrue(self.change(sector, 'add', 12.4))
        self.assertEqual(self.state.Player['$valid_macro'].Population, 12000000)
        self.assertFalse(self.change(sector, 'add', 20))
        self.assertTrue(self.change(sector, 'set', 12.6))
        self.assertEqual(self.state.Player['$valid_macro'].Population, 13000000)
        self.assertTrue(self.change(sector, 'set', 100000))
        self.assertEqual(self.state.Player['$valid_macro'].Population, 100000000000)
        self.assertFalse(self.change(NIL, 'add', 10))

    def test_values_above_32_bits_do_not_wrap(self):
        # MEASURED in game: 6182 M was stored as 1,887,032,704 and 38518 M went negative.
        for millions in (6182, 38518, 100000):
            sector = self.sector('Large %d' % millions)
            self.assertTrue(self.change(sector, 'add', millions))
            self.assertEqual(self.registry[sector].Population, millions * 1000000)

    def test_repair_drops_impossible_saved_values(self):
        self.run.library('md.CE_PopulationOverrides.Ensure')
        self.state.Player.update({'$negative': Table(Population=-136705664), '$text': Table(Population='x'),
                                  '$huge': Table(Population=100000000001), '$valid': Table(Population=1887032704)})
        self.run.library('md.CE_PopulationOverrides.Repair')
        self.assertEqual(list(self.state.Player), ['$valid'])

    def test_debug_fixed_population_wins_and_is_not_a_baseline(self):
        sector = self.sector('Debug')
        record = self.native(sector, 200000000)
        self.assertTrue(self.change(sector, 'add', 700))
        record.PopulationOverride = 5000000000.0
        self.state.Player['$debug_macro'].pop('Baseline')
        self.run.env.update(Sector=sector, Population=5000000000.0)
        self.run.library('ReconcileSector')
        self.assertEqual(record.Population, 5000000000.0)
        self.assertNotIn('Baseline', self.state.Player['$debug_macro'])
        calls = []
        self.run.stubs['md.CE_CivilianHub.ReconcileSector'] = lambda: calls.append(self.run.env['Sector'])
        self.run.library('md.CE_PopulationOverrides.ReconcileOverrides')
        self.assertEqual(calls, [])

    def test_reconcile_overrides_without_native_reading(self):
        sector = self.sector('Offline')
        self.state.Player['$offline_macro'] = Table(Population=300000000)
        self.run.library('md.CE_PopulationOverrides.ReconcileOverrides')
        self.assertEqual(self.registry[sector].Population, 300000000)
        self.assertEqual(len(self.created), 1)

    def test_reset_restores_cached_native_rates(self):
        sector = self.sector('Restore')
        record = self.native(sector, 8524100000)
        native_rate = record.Wares['foodrations'].Rate
        self.assertTrue(self.change(sector, 'add', 4262.05))
        self.assertAlmostEqual(record.Wares['foodrations'].Rate, 7140 * 4262000000 / 8524100000)
        self.assertTrue(self.change(sector, 'reset'))
        self.assertEqual(record.Population, 8524100000)
        self.assertAlmostEqual(record.Wares['foodrations'].Rate, native_rate)

    def test_removed_override_without_native_reading_waits_for_reconcile(self):
        sector = self.sector('Pending')
        self.assertTrue(self.change(sector, 'add', 300))
        record = self.registry[sector]
        self.assertTrue(self.change(sector, 'reset'))
        self.assertEqual(record.Population, 300000000, 'kept until the next native reading')
        self.assertEqual(self.native(sector, 150000000).Population, 150000000)

    def test_debug_reset_keeps_player_overrides(self):
        # Overrides are player settings: the global reset only clears controller state.
        from lxml import etree as E
        self.assertNotIn('CE_PopulationOverrides', E.tostring(self.run.scripts['CE_DebugReset']).decode())


def assert_slider_rows_exclusive(test, calls):
    """Native rule (debug.txt): a slider cell excludes other interactive cells in its row."""
    rows = []
    for cue, args in calls:
        cue = cue.rsplit('.', 1)[-1]
        if cue == 'Add_Row':
            rows.append([])
        elif cue.startswith('Make_') and rows:
            rows[-1].append(cue)
    for row in rows:
        if 'Make_Slider' in row:
            test.assertEqual([c for c in row if c != 'Make_Text'], ['Make_Slider'], row)


class PopulationOptionsTests(OverrideHarness):
    def build(self):
        calls = []
        self.run.native['signal_cue_instantly'] = lambda n: calls.append((n.get('cue').rsplit('.', 1)[-1], self.run.expr(n.get('param') or 'null')))
        self.run.native['find_sector'] = lambda n: self.run.set(n.get('name'), List(list(self.sectors)))
        self.run.library('md.CE_PopulationOptions.Build')
        del self.run.native['signal_cue_instantly']
        assert_slider_rows_exclusive(self, calls)
        return calls

    def callback(self, cue, **param):
        refreshed = []
        self.run.native['signal_cue_instantly'] = lambda n: (refreshed.append(n.get('cue')) if n.get('cue').endswith('Refresh_Menu') else self.run.signals.append((n.get('cue'), self.run.expr(n.get('param')))))
        self.run.env['event'] = Table(param=Table(param))
        self.run.actions(self.run.scripts['CE_PopulationOptions'].xpath('//cue[@name=$n]/actions', n=cue)[0])
        del self.run.native['signal_cue_instantly']
        self.assertEqual(refreshed, ['md.Simple_Menu_API.Refresh_Menu'])

    def test_add_flow_rows_and_dropdown(self):
        zeta, alpha, preset, custom = (self.sector(n) for n in ('Zeta', 'Alpha', 'Preset', 'Custom'))
        self.state.Presets['$preset_macro'] = 2000000000
        self.state.Presets['$elsewhere_macro'] = 1
        self.state.Player['$custom_macro'] = Table(Population=150000000)
        calls = self.build()
        dropdown = next(args for cue, args in calls if cue == 'Make_Dropdown')
        self.assertEqual([o.text for o in dropdown.options], ['Alpha', 'Zeta'])
        self.assertEqual(dropdown.startOption, '')
        sliders = [args for cue, args in calls if cue == 'Make_Slider']
        self.assertEqual([s.echo.Sector for s in sliders], [custom, preset])
        self.assertEqual([s.start for s in sliders], [150, 2000])
        buttons = [args for cue, args in calls if cue == 'Make_Button']
        self.assertEqual([b.active for b in buttons], [True, False], 'reset is disabled while the preset applies')
        # Pick, adjust, confirm.
        self.run.env.update(Sector=zeta, Population=3123456789)
        self.run.library('md.CE_PopulationOverrides.RememberNative')
        self.callback('Pick', option=Table(Sector=zeta))
        self.assertEqual((self.draft.Sector, self.draft.Millions), (zeta, 3123))
        calls = self.build()
        dropdown = next(args for cue, args in calls if cue == 'Make_Dropdown')
        self.assertEqual(dropdown.startOption, 2)
        draft = next(args for cue, args in calls if cue == 'Make_Slider' and args.id == 'ce_pop_draft')
        self.assertEqual(draft.start, 3123)
        self.callback('DraftSlider', value=4000.4, valuechanged=True)
        self.assertEqual(self.draft.Millions, 4000)
        self.callback('DraftSlider', value=-5, valuechanged=True)
        self.assertEqual(self.draft.Millions, 4000)
        self.callback('Confirm')
        self.assertFalse(self.draft.Sector)
        self.assertEqual(self.state.Player['$zeta_macro'].Population, 4000000000)
        self.assertIn(('md.CE_CivilianHub.PopulationOverrideChanged', zeta), self.run.signals)
        calls = self.build()
        dropdown = next(args for cue, args in calls if cue == 'Make_Dropdown')
        self.assertEqual([o.text for o in dropdown.options], ['Alpha'])

    def test_slider_starts_stay_inside_their_range(self):
        # The engine rejects the whole page if a slider starts outside min/max.
        low, high = self.sector('Low'), self.sector('High')
        self.state.Player['$low_macro'] = Table(Population=-136705664)
        self.state.Player['$high_macro'] = Table(Population=500000000000)
        starts = [args.start for cue, args in self.build() if cue == 'Make_Slider']
        self.assertEqual(starts, [100000, 0])
        self.run.env.update(Sector=low, Population=900000000000)
        self.run.library('md.CE_PopulationOverrides.RememberNative')
        del self.state.Player['$low_macro']
        self.callback('Pick', option=Table(Sector=low))
        self.assertEqual(self.draft.Millions, 100000)

    def test_native_zero_tooltip_is_a_value_not_unmeasured(self):
        sector = self.sector('Zero')
        self.state.Player['$zero_macro'] = Table(Population=1000000000)
        self.run.env.update(Sector=sector, Population=0)
        self.run.library('md.CE_PopulationOverrides.RememberNative')
        slider = next(args for cue, args in self.build() if cue == 'Make_Slider')
        self.assertEqual(slider.mouseOverText, (974201, 444, (0,)))

    def test_edit_cancel_and_remove(self):
        sector = self.sector('Edit')
        self.state.Player['$edit_macro'] = Table(Population=150000000)
        self.callback('OverrideSlider', echo=Table(Sector=sector), value=250, valuechanged=True)
        self.assertEqual(self.state.Player['$edit_macro'].Population, 250000000)
        self.callback('Reset', echo=Table(Sector=sector))
        self.assertNotIn('$edit_macro', self.state.Player)
        self.callback('Pick', option=Table(Sector=sector))
        self.callback('Cancel')
        self.assertFalse(self.draft.Sector)


if __name__ == '__main__':
    unittest.main()
