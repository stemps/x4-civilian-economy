"""CE-specific translation contract; coverage and formatting are `x4mod translations`."""
import re
import unittest
import xml.etree.ElementTree as ET

from support import MOD


class TranslationEscapeTests(unittest.TestCase):
    def test_md_notification_percent_signs_are_escaped(self):
        paths = sorted((MOD / 't').glob('0001*.xml'))
        self.assertEqual(len(paths), 16)
        for path in paths:
            entries = {node.get('id'): node.text for node in ET.parse(path).findall('.//t')}
            for key in ('201', '202', '333', '334'):
                remainder = re.sub(r'%%|%[1-9]\d*', '', entries[key])
                self.assertNotIn('%', remainder, f'{path.name}: {key}')


if __name__ == '__main__':
    unittest.main()
