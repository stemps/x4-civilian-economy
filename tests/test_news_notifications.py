"""Execute real notification routing; engine cutscene playback remains mocked."""
import unittest
from support import Runner, Table, List, Component, NIL, ROOT, REF
from lxml import etree as E


class NewsNotifications(unittest.TestCase):
    def setUp(self):
        self.run = Runner()
        self.tree = self.run.scripts['CE_UnrestNotifications']
        self.object = Component(exists=True)
        self.sector = Component(exists=True)
        self.run.env.update(IncidentObject=self.object, IncidentSector=self.sector,
                            IncidentText='Full incident details', IncidentPriority=3,
                            BroadcastKey='ce_news_raid', BroadcastCaption='Pirate mobilisation - Sector')
        self.events = []
        self.return_id = 91

        def play(node):
            self.events.append(('play', self.run.expr(node.get('key')),
                                self.run.expr(node.get('caption'))))
            self.assertEqual(node.get('targetmonitor'), 'true')
            self.assertEqual(node.get('timeout'), '12s')
            self.assertEqual(node.get('sound'), "'notification_warning'")
            interaction = node.find('interaction')
            self.assertEqual(self.run.expr(interaction.get('param')), List([self.object, self.sector]))
            self.assertEqual(interaction.get('param2'), "'ce_unrest_broadcast_map'")
            self.run.set(node.get('result'), self.return_id)

        self.run.native.update(
            play_cutscene=play,
            show_notification=lambda n: self.events.append(('ticker', self.run.expr(n.get('text')))),
            show_interactive_notification=lambda n: self.events.append(('popup', self.run.expr(n.get('text')))),
            write_to_logbook=lambda n: self.events.append(('log', self.run.expr(n.get('text')), self.run.expr(n.get('object')))),
            stop_cutscene=lambda n: self.events.append(('stop', self.run.expr(n.get('cutscene')))),
            open_menu=lambda n: self.events.append(('map', self.run.expr(n.get('param'))[7][2])),
            debug_text=lambda n: self.run.expr(n.get('text')))

    def test_all_broadcasts_keep_full_details_in_one_log_entry(self):
        for key in ('ce_news_raid', 'ce_news_sabotage', 'ce_news_hacking'):
            self.events.clear()
            self.run.env['BroadcastKey'] = key
            self.run.library('md.CE_UnrestNotifications.Broadcast')
            self.assertEqual([e[0] for e in self.events], ['ticker', 'play', 'log'])
            self.assertEqual(self.events[0], ('ticker', 'Full incident details'))
            self.assertEqual(self.events[1][1], key)
            self.assertEqual(self.events[2], ('log', 'Full incident details', self.object))

    def test_null_id_falls_back_without_duplicate_log_entry_or_stale_handle(self):
        self.run.library('md.CE_UnrestNotifications.Broadcast')
        self.events.clear();self.return_id=NIL
        self.run.library('md.CE_UnrestNotifications.Broadcast')
        self.assertEqual([e[0] for e in self.events], ['ticker', 'play', 'popup', 'log'])
        self.assertIs(self.run.env['IncidentCutscene'], NIL)

    def test_critical_popup_does_not_reuse_previous_broadcast_inputs(self):
        self.run.library('md.CE_UnrestNotifications.Popup')
        self.assertEqual([e[0] for e in self.events], ['popup', 'log'])

    def test_broadcast_interaction_stops_its_own_clip_before_map_and_falls_back_to_sector(self):
        self.run.env['event'] = Table(param=List([self.object,self.sector]), param3=91)
        actions=self.tree.xpath('//cue[@name="OpenBroadcast"]/actions')[0]
        self.run.actions(actions)
        self.assertEqual(self.events, [('stop',91),('map',self.object)])
        self.events.clear();self.object.exists=False
        self.run.actions(actions)
        self.assertEqual(self.events, [('stop',91),('map',self.sector)])
        self.events.clear();self.sector.exists=False
        self.run.actions(actions)
        self.assertEqual(self.events, [('stop',91)])

    def test_original_popup_interaction_never_stops_a_cutscene(self):
        self.run.env['event'] = Table(param=List([self.object,self.sector]), param3=123)
        self.run.actions(self.tree.xpath('//cue[@name="OpenIncident"]/actions')[0])
        self.assertEqual(self.events, [('map',self.object)])

    def test_production_cutscene_schema_and_shipped_video_reference(self):
        schema = E.XMLSchema(E.parse(str(REF / 'cutscenes/cutscenes.xsd')))
        for key in ('ce_news_raid', 'ce_news_sabotage', 'ce_news_hacking'):
            tree = E.parse(str(ROOT / f'cutscenes/{key}.xml'))
            schema.assertValid(tree)
            self.assertEqual(tree.find('director').get('key'), key)
            video = tree.find('.//video').get('name')
            path = ROOT / (video.removeprefix('extensions/civilian_economy/') + '.mkv')
            self.assertTrue(path.is_file())
            self.assertGreater(path.stat().st_size, 1000)


if __name__ == '__main__':
    unittest.main()
