"""Compatibility update checks, including simulated future ROM metadata."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rom import Cartridge, RomError
import support

INPUT = Path(os.environ.get('DATAKIN_TEST_ROM', ROOT / 'rom/Datakin-Server-Delver.gba'))


class SupportSetupTests(unittest.TestCase):
    def test_missing_rom_never_contacts_network(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(support, 'download_json') as fetch:
            with self.assertRaisesRegex(RomError, 'Put your original ROM'):
                support.install_support(folder)
            fetch.assert_not_called()

    def test_invalid_file_never_contacts_network(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(support, 'download_json') as fetch:
            path = Path(folder) / 'rom/Datakin-Server-Delver.gba'
            path.parent.mkdir()
            path.write_bytes(b'not a ROM')
            with self.assertRaisesRegex(RomError, 'not a supported'):
                support.install_support(folder)
            fetch.assert_not_called()


@unittest.skipUnless(INPUT.is_file(), 'Supply the supported ROM to run compatibility checks.')
class SupportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'rom').mkdir()
        self.input = self.root / 'rom/Datakin-Server-Delver.gba'
        original = Cartridge.open(INPUT, ROOT / 'profiles')
        data = bytearray(original.data)
        # A new header revision with the same compatible stage ABI is sufficient
        # to test discovery. This test-only copy is never shipped or emulated.
        data[188] = 80
        data[189] = (-sum(data[160:189]) - 25) & 255
        self.data = bytes(data)
        self.input.write_bytes(self.data)
        self.profile = deepcopy(original.profile)
        self.profile.update(revision=80, label='Datakin future fixture',
                            sha256=hashlib.sha256(self.data).hexdigest())
        self.name = 'datakin-v080.json'

    def catalog(self, profile=None, filename=None, checksum=None):
        raw = json.dumps(profile or self.profile).encode()
        self.index = dict(format='datakin-profile-index-v1', profiles=[dict(
            file=filename or self.name, rom_sha256=self.profile['sha256'],
            profile_sha256=checksum or hashlib.sha256(raw).hexdigest())])
        return [(json.dumps(self.index).encode(), self.index), (raw, json.loads(raw))]

    def test_future_build_installs_and_roundtrips_without_changing_rom(self):
        with patch.object(support, 'download_json', side_effect=self.catalog()) as fetch:
            self.assertTrue(support.install_support(self.root)['installed'])
        self.assertEqual([c.args[0] for c in fetch.call_args_list], ['index.json', self.name])
        cart = Cartridge.open(self.input, self.root / 'profiles')
        self.assertEqual(cart.patch(dict(enumerate(cart.originals, 1))), self.data)
        self.assertEqual(self.input.read_bytes(), self.data)
        # Once installed, offline operation needs no download.
        with patch.object(support, 'download_json') as fetch:
            self.assertFalse(support.install_support(self.root)['installed'])
            fetch.assert_not_called()

    def test_unknown_rom_is_not_installed(self):
        index = dict(format='datakin-profile-index-v1', profiles=[])
        with patch.object(support, 'download_json', return_value=(b'', index)):
            with self.assertRaisesRegex(RomError, 'No verified support'):
                support.install_support(self.root)
        self.assertFalse((self.root / 'profiles').exists())

    def test_path_traversal_is_rejected_before_download(self):
        with patch.object(support, 'download_json', side_effect=self.catalog(filename='../server.py')) as fetch:
            with self.assertRaisesRegex(RomError, 'filename'):
                support.install_support(self.root)
            self.assertEqual(fetch.call_count, 1)

    def test_corrupt_download_is_not_installed(self):
        with patch.object(support, 'download_json', side_effect=self.catalog(checksum='0' * 64)):
            with self.assertRaisesRegex(RomError, 'checksum'):
                support.install_support(self.root)
        self.assertFalse((self.root / 'profiles').exists())

    def test_invalid_offsets_and_future_format_are_not_installed(self):
        for change in ('offset', 'format', 'field_size'):
            profile = deepcopy(self.profile)
            if change == 'offset':
                profile['stage_offset'] = len(self.data)
            elif change == 'format':
                profile['format'] = 'datakin-rom-profile-v999'
            else:
                profile['fields'][0]['format'] = '99999I'
            with self.subTest(change=change), patch.object(support, 'download_json', side_effect=self.catalog(profile)):
                with self.assertRaises(ValueError):
                    support.install_support(self.root)
        self.assertFalse((self.root / 'profiles').exists())
        self.assertEqual(self.input.read_bytes(), self.data)


if __name__ == '__main__':
    unittest.main()
