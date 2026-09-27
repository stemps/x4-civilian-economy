"""Regression tests for full translation coverage; no game/runtime dependencies."""
from pathlib import Path
import tempfile
import unittest

from check_translations import translation_coverage_errors


class TranslationCoverageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = '<page id="90210"><t id="1">Stations</t></page>'
        self.source += '<page id="90211"><t id="1">%s/h</t></page>'
        self.write("0001-l044.xml", self.source)
        self.write("0001-l049.xml", self.source)

    def write(self, name, body):
        (self.root / name).write_text(f'<language id="{int(name[6:9])}">{body}</language>', encoding="utf-8")

    def errors(self):
        return translation_coverage_errors(self.root, {49})

    def test_complete_multiple_pages_and_shared_words_pass(self):
        self.assertEqual(self.errors(), [])

    def test_missing_entry_on_second_page_is_reported(self):
        self.write("0001-l049.xml", '<page id="90210"><t id="1">Stationen</t></page>')
        self.assertEqual(self.errors(), [
            "0001-l049.xml: page 90211, text 1: missing translation"])

    def test_missing_language_file_fails(self):
        (self.root / "0001-l049.xml").unlink()
        self.assertIn("0001-l049.xml: missing language file", self.errors())

    def test_empty_translation_fails(self):
        self.write("0001-l049.xml", self.source.replace("Stations", " \n "))
        self.assertTrue(any("empty translation" in error for error in self.errors()))

    def test_duplicate_entry_fails(self):
        self.write("0001-l049.xml", self.source + self.source)
        self.assertEqual(sum("duplicate entry" in error for error in self.errors()), 2)

    def test_all_languages_are_reported_together(self):
        self.write("0001-l033.xml", '<page id="90210"><t id="1">Stations</t></page>')
        self.write("0001-l049.xml", '<page id="90211"><t id="1">%s/h</t></page>')
        self.assertEqual(sum("missing translation" in error for error in self.errors()), 2)

    def test_malformed_xml_is_reported(self):
        (self.root / "0001-l049.xml").write_text("<language>", encoding="utf-8")
        self.assertTrue(any("no element found" in error for error in self.errors()))

    def test_extra_entry_fails(self):
        self.write("0001-l049.xml", self.source + '<page id="99"><t id="2">Extra</t></page>')
        self.assertTrue(any("absent from English source" in error for error in self.errors()))

    def test_unescaped_parentheses_checked_on_every_page_and_language(self):
        for name in ['0001-l044.xml', '0001-l049.xml', '0001-l033.xml']:
            self.write(name, self.source.replace('%s/h', '%s/h (examples)'))
        errors = self.errors()
        for name in ['0001-l044.xml', '0001-l049.xml', '0001-l033.xml']:
            self.assertIn(f'{name}: page 90211, text 1: unescaped parentheses; X4 would strip visible text', errors)
        self.assertEqual(len(errors), 3)

    def test_escaped_parentheses_and_xml_comments_are_allowed(self):
        source = self.source.replace('%s/h', r'%s/h \(examples\)')
        for name in ['0001-l044.xml', '0001-l049.xml']:
            self.write(name, source + '<!-- (translator note) -->')
        self.assertEqual(self.errors(), [])

    def test_unescaped_closing_parenthesis_is_reported(self):
        self.write('0001-l049.xml', self.source.replace('Stations', r'Stationen \(Beispiele)'))
        self.assertTrue(any('unescaped parentheses' in error for error in self.errors()))

    def test_wrong_language_id_fails(self):
        path = self.root / '0001-l049.xml'
        path.write_text(path.read_text(encoding='utf-8').replace('id="49"', 'id="44"'), encoding='utf-8')
        self.assertIn('0001-l049.xml: language id must be 49', self.errors())

    def test_missing_source_fails(self):
        (self.root / '0001-l044.xml').unlink()
        self.assertIn('0001-l044.xml: missing language file', self.errors())

    def test_empty_source_fails(self):
        self.write('0001-l044.xml', '')
        self.assertIn('0001-l044.xml: no text entries', self.errors())

    def test_wrong_root_and_missing_ids_fail(self):
        (self.root / '0001-l049.xml').write_text('<wrong id="49"><page><t>Text</t></page></wrong>', encoding='utf-8')
        self.assertTrue(any('expected a language document' in error for error in self.errors()))
        self.assertTrue(any('missing id attribute' in error for error in self.errors()))

    def assert_formats(self, english, translated, valid):
        self.write('0001-l044.xml', f'<page id="1"><t id="1">{english}</t></page>')
        self.write('0001-l049.xml', f'<page id="1"><t id="1">{translated}</t></page>')
        errors = self.errors()
        if valid:
            self.assertEqual(errors, [])
        else:
            self.assertTrue(any('formatting placeholders' in error for error in errors), errors)

    def test_lua_placeholder_type_order_precision_and_percent_are_preserved(self):
        for translated in ['%d %.1f %s %%', '%s %.0f %d %%', '%s %.1f %d %', '%s %.1f %%']:
            with self.subTest(translated=translated):
                self.assert_formats('%s %.1f %d %%', translated, False)

    def test_numbered_md_placeholders_may_be_reordered(self):
        self.assert_formats('%1 in %2: %3%.', '%3%: %2, %1.', True)

    def test_numbered_md_placeholders_cannot_be_lost_or_duplicated(self):
        for translated in ['%1 %2', '%1 %2 %2', '%1 %2 %4']:
            with self.subTest(translated=translated):
                self.assert_formats('%1 %2 %3', translated, False)

    def test_literal_percent_text_is_not_a_lua_placeholder(self):
        self.assert_formats('90% of demand; 10% for reserves', '90% des Bedarfs; 10% Reserve', True)

    def test_references_and_literal_line_breaks_are_preserved(self):
        self.assert_formats(r'{1,2}\n%s', r'{1,3}\n%s', False)
        self.assert_formats(r'{1,2}\n%s', '{1,2} %s', False)
        self.assert_formats(r'{1,2}\n%s', r'{1,2}\n%s', True)

    def test_em_dash_fails(self):
        self.write('0001-l049.xml', self.source.replace('Stations', 'A\u2014B'))
        self.assertTrue(any('unsupported em dash' in error for error in self.errors()))

    def test_shipped_translations_are_complete(self):
        from check_translations import ROOT
        self.assertEqual(translation_coverage_errors(ROOT / 't'), [])

    def test_md_notification_percent_signs_are_escaped(self):
        import re
        import xml.etree.ElementTree as ET
        from check_translations import ROOT
        for path in (ROOT / 't').glob('0001-l*.xml'):
            entries={node.get('id'):node.text for node in ET.parse(path).findall('.//t')}
            for key in ('201','202','333','334'):
                remainder=re.sub(r'%%|%[1-9]\d*','',entries[key])
                self.assertNotIn('%',remainder,f'{path.name}: {key}')


if __name__ == "__main__":
    unittest.main()

