"""Archive behavior using isolated Git repositories; never access Nexus."""
import hashlib
import re
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from release_archive import local_zip, tagged_zip, ReleaseError
from release_support import ReleaseFixture


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.fixture = ReleaseFixture()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root

    def test_current_manifest_modules_are_included(self):
        from xml.etree import ElementTree as ET
        ROOT = Path(__file__).resolve().parents[1]
        modules = [node.attrib['name'] for node in ET.parse(ROOT / 'ui.xml').iter('file')]
        self.assertTrue(modules)
        self.fixture.write('ui.xml', (ROOT / 'ui.xml').read_text(encoding='utf-8'))
        for name in modules:
            self.fixture.write(name, (ROOT / name).read_text(encoding='utf-8'))
        # This archive exists only in the fixture's temporary repository.
        archive = local_zip(self.root)
        with zipfile.ZipFile(archive) as zipped:
            for name in modules:
                self.assertEqual(zipped.read('civilian_economy/' + name),
                                 (self.root / name).read_bytes())

    def test_dirty_new_deleted_ignored_and_excluded(self):
        f = self.fixture
        f.cmd('checkout', '-b', 'experiment')
        f.write('ui/example.lua', 'return 42\n')
        f.write('ui/new.lua', 'return 3\n')
        f.write('.gitignore', '/dist/\nui/ignored.lua\n')
        f.write('ui/ignored.lua', 'return 4\n')
        (self.root / 't/0001.xml').unlink()
        before = f.cmd('status', '--porcelain')
        commit = f.cmd('rev-parse', 'HEAD')
        metadata = (self.root / 'content.xml').read_bytes()
        archive = local_zip(self.root)
        with zipfile.ZipFile(archive) as zipped:
            self.assertEqual(set(zipped.namelist()), {'civilian_economy/' + p for p in
                             ['content.xml', 'ui.xml', 'ui/example.lua', 'ui/new.lua']})
            self.assertEqual(zipped.read('civilian_economy/ui/example.lua'), b'return 42\n')
        self.assertEqual(f.cmd('status', '--porcelain'), before)
        self.assertEqual(f.cmd('rev-parse', 'HEAD'), commit)
        self.assertEqual((self.root / 'content.xml').read_bytes(), metadata)
        self.assertFalse((self.root / 'VERSION').exists())

    def test_replace_only_after_success(self):
        archive = local_zip(self.root)
        original = archive.read_bytes()
        self.fixture.write('ui/example.lua', 'return 10\n')
        with patch('release_archive.verify_zip', side_effect=ReleaseError('invalid archive')):
            with self.assertRaises(ReleaseError):
                local_zip(self.root)
        self.assertEqual(archive.read_bytes(), original)
        local_zip(self.root)
        self.assertNotEqual(archive.read_bytes(), original)

    def test_broadcast_assets_included_without_unrelated_video_files(self):
        files = ('cutscenes/ce_news_raid.xml', 'videos/ce_news_raid.mkv',
                 'cutscenes/ce_news_sabotage.xml', 'videos/ce_news_sabotage.mkv',
                 'cutscenes/ce_news_hacking.xml', 'videos/ce_news_hacking.mkv')
        for name in files:
            self.fixture.write(name, 'synthetic test asset')
        archive = local_zip(self.root)
        with zipfile.ZipFile(archive) as zipped:
            for name in files:
                self.assertEqual(zipped.read('civilian_economy/' + name), b'synthetic test asset')

    def test_raider_logo_texture_is_packaged_without_source_artwork(self):
        texture = 'assets/textures/ui/factions/ce_unrest_skull.gz'
        self.fixture.write(texture, 'synthetic texture')
        self.fixture.write('images/ce_unrest_skull.png', 'source artwork')
        archive = local_zip(self.root)
        with zipfile.ZipFile(archive) as zipped:
            self.assertEqual(zipped.read('civilian_economy/' + texture), b'synthetic texture')
            self.assertNotIn('civilian_economy/images/ce_unrest_skull.png', zipped.namelist())

    def test_md_in_local_release_and_tagged_archives(self):
        self.fixture.write('md/ce_logistics.xml', '<mdscript name="CE_Logistics"/>\n')
        local = local_zip(self.root)
        with zipfile.ZipFile(local) as archive:
            self.assertIn('civilian_economy/md/ce_logistics.xml', archive.namelist())
        self.fixture.cmd('add', 'md')
        self.fixture.cmd('commit', '-m', 'Add MD reader')
        self.fixture.cmd('push', 'origin', 'main')  # fixture's temporary local bare repo
        public = self.fixture.run_release()
        with zipfile.ZipFile(public) as archive:
            expected = archive.read('civilian_economy/md/ce_logistics.xml')
        public.unlink()
        rebuilt, _, _ = tagged_zip(self.root, 'v0.1.0')
        with zipfile.ZipFile(rebuilt) as archive:
            self.assertEqual(archive.read('civilian_economy/md/ce_logistics.xml'), expected)

    def test_ce_runtime_directories_in_local_release_and_reconstruction(self):
        paths = ('aiscripts/order.plunder.xml',
                 'assets/structures/macros/ce_civilian_hub_macro.xml',
                 'index/macros.xml', 'libraries/constructionplans.xml',
                 'extensions/optional_mod/md/integration.xml')
        for name in paths:
            self.fixture.write(name, '<diff/>\n')
        local = local_zip(self.root)
        with zipfile.ZipFile(local) as archive:
            for name in paths:
                self.assertEqual(archive.read('civilian_economy/' + name), b'<diff/>\n')
        self.fixture.cmd('add', '--', *paths)
        self.fixture.cmd('commit', '-m', 'Add CE runtime content')
        self.fixture.cmd('push', 'origin', 'main')
        public = self.fixture.run_release()
        expected = public.read_bytes()
        with zipfile.ZipFile(public) as archive:
            for name in paths:
                self.assertEqual(archive.read('civilian_economy/' + name), b'<diff/>\n')
        public.unlink()
        rebuilt, _, _ = tagged_zip(self.root, 'v0.1.0')
        self.assertEqual(rebuilt.read_bytes(), expected)

    def test_unpackaged_runtime_looking_files_fail(self):
        # Each would work in a dev checkout (junctioned into the game) but be
        # missing from the player's ZIP.
        for name in ('videos/unrelated.mkv', 'videos/ce_news_raid.tmp.mkv', 'cutscenes/notes.txt',
                     'md/notes.txt', 'assets/banner.png', 'maps/ce_sectors.xml', 'sounds/ce_alarm.ogg',
                     'root_patch.xml'):
            with self.subTest(name=name):
                self.fixture.write(name, 'synthetic')
                with self.assertRaisesRegex(ReleaseError, 'would be left out of the ZIP: ' + re.escape(name)):
                    local_zip(self.root)
                (self.root / name).unlink()
        self.fixture.write('sounds/ce_alarm.ogg', 'synthetic')
        self.fixture.cmd('add', 'sounds')
        self.fixture.cmd('commit', '-m', 'Add unshipped sound')
        self.fixture.cmd('push', 'origin', 'main')
        with self.assertRaisesRegex(ReleaseError, 'sounds/ce_alarm.ogg'):
            self.fixture.run_release()
        self.assertEqual(self.fixture.cmd('tag', '--list'), '')

    def test_dev_folders_and_documents_are_not_flagged(self):
        for name in ('tools/probe.lua', 'docs/example.xml', 'images/cover.png', 'README.md'):
            self.fixture.write(name, 'synthetic')
        with zipfile.ZipFile(local_zip(self.root)) as archive:
            self.assertEqual(archive.namelist(), ['civilian_economy/' + name for name in
                             ('content.xml', 't/0001.xml', 'ui.xml', 'ui/example.lua')])

    def test_license_is_shipped(self):
        self.fixture.write('MIT-LICENSE', 'MIT License\n')
        with zipfile.ZipFile(local_zip(self.root)) as archive:
            self.assertEqual(archive.read('civilian_economy/MIT-LICENSE'), b'MIT License\n')

    def test_missing_manifest_fails(self):
        (self.root / 'ui.xml').unlink()
        with self.assertRaisesRegex(ReleaseError, 'Missing runtime manifests'):
            local_zip(self.root)

    def test_tag_reconstruction_is_identical_and_ignores_worktree(self):
        archive = self.fixture.run_release()
        expected = hashlib.sha256(archive.read_bytes()).hexdigest()
        self.fixture.write('ui/example.lua', 'uncommitted code')
        before = self.fixture.cmd('status', '--porcelain')
        archive.unlink()
        rebuilt, commit, notes = tagged_zip(self.root, 'v0.1.0')
        self.assertEqual(hashlib.sha256(rebuilt.read_bytes()).hexdigest(), expected)
        self.assertEqual(commit, self.fixture.cmd('rev-parse', 'v0.1.0^{}'))
        self.assertEqual(notes, '- Initial mod')
        self.assertEqual(self.fixture.cmd('status', '--porcelain'), before)

    def test_windows_release_reconstruction(self):
        f = self.fixture
        f.cmd('config', 'core.autocrlf', 'true')
        for name in ('content.xml', 'ui.xml', 'ui/example.lua', 't/0001.xml'):
            path = self.root / name
            path.write_bytes(path.read_bytes().replace(b'\n', b'\r\n'))
        f.cmd('add', '--renormalize', '.')
        archive = f.run_release()
        expected = archive.read_bytes()
        archive.unlink()
        rebuilt, _, _ = tagged_zip(self.root, 'v0.1.0')
        self.assertEqual(rebuilt.read_bytes(), expected)

    def test_remote_tag_mismatch_rejected(self):
        self.fixture.run_release()
        self.fixture.cmd('tag', '-f', '-a', 'v0.1.0', '-m', 'changed')
        with self.assertRaisesRegex(ReleaseError, 'tags do not match'):
            tagged_zip(self.root, 'v0.1.0')

    def test_existing_archive_tampering_rejected(self):
        archive = self.fixture.run_release()
        with zipfile.ZipFile(archive, 'a') as zipped:
            zipped.writestr('civilian_economy/ui/extra.lua', b'bad')
        with self.assertRaises(ReleaseError):
            tagged_zip(self.root, 'v0.1.0')


if __name__ == '__main__':
    unittest.main()
