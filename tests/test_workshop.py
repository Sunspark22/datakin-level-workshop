"""Standard-library tests. Provide the original ROM locally; it is not bundled."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rom import Cartridge, RomError
import server

INPUT = Path(os.environ.get('DATAKIN_TEST_ROM', ROOT / 'rom/Datakin-Server-Delver.gba'))


class MissingRomTests(unittest.TestCase):
    def test_missing_rom_is_explained(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(RomError, 'Put your original ROM'):
                Cartridge.open(Path(folder) / 'missing.gba', ROOT / 'profiles')

    def test_arbitrary_rom_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'fake.gba'
            p.write_bytes(b'not a game')
            with self.assertRaisesRegex(RomError, 'Unsupported ROM'):
                Cartridge.open(p, ROOT / 'profiles')


@unittest.skipUnless(INPUT.is_file(), 'Supply the supported ROM to run ROM checks.')
class RomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cart = Cartridge.open(INPUT, ROOT / 'profiles')
        cls.hash_before = hashlib.sha256(INPUT.read_bytes()).hexdigest()

    @classmethod
    def tearDownClass(cls):
        assert hashlib.sha256(INPUT.read_bytes()).hexdigest() == cls.hash_before

    def fixture(self):
        return deepcopy(self.cart.originals[0])

    def test_every_stage_roundtrips_exactly(self):
        self.assertEqual(self.cart.count, 17)
        patched = self.cart.patch(dict(enumerate(self.cart.originals, 1)))
        self.assertEqual(patched, self.cart.data)

    def test_change_is_confined_to_level_table(self):
        s = self.fixture()
        s['spawn']['x'] += 8
        patched = self.cart.patch({1: s})
        offset = self.cart.offset + self.cart.fields['spawn']['offset']
        self.assertEqual(struct.unpack_from('<i', patched, offset)[0], s['spawn']['x'])
        self.assertEqual(patched[:offset], self.cart.data[:offset])
        self.assertEqual(patched[offset + 4:], self.cart.data[offset + 4:])

    def test_rename_appends_and_does_not_overwrite_shared_strings(self):
        s = self.fixture()
        s['name'] = 'MY LEVEL'
        data = self.cart.patch({1: s})
        self.assertEqual(len(data), len(self.cart.data) + 16)
        offset = self.cart.offset + self.cart.fields['name']['offset']
        self.assertEqual(struct.unpack_from('<I', data, offset)[0], 0x08000000 + len(self.cart.data))
        self.assertEqual(data[len(self.cart.data):], b'MY LEVEL' + b'\0' * 8)
        self.assertEqual(data[:offset], self.cart.data[:offset])
        self.assertEqual(data[offset + 4:len(self.cart.data)], self.cart.data[offset + 4:])

    def test_input_must_be_exact_version(self):
        data = bytearray(self.cart.data)
        data[-1] ^= 1
        with self.assertRaisesRegex(RomError, 'Unsupported ROM'):
            Cartridge(data, self.cart.profile)

    def test_every_collection_cap_is_enforced(self):
        # Repeated valid rows for non-reference arrays cover the bounded binary
        # writes. References and linked/sorted collections are tested separately.
        for key in ('enemies', 'pickups', 'movers', 'winds', 'spikes', 'traps',
                    'lasers', 'grass', 'waters', 'vines', 'lava', 'jets', 'caches',
                    'chemicals', 'emitters', 'arcs', 'belts', 'spotlights',
                    'crushers', 'storms', 'sections'):
            original = next((s for s in self.cart.originals if s[key]), None)
            if original is None:
                continue
            s = deepcopy(original)
            slot = self.cart.originals.index(original) + 1
            cap = self.cart.limits(s)[key]
            s[key] = [deepcopy(s[key][0]) for _ in range(cap + 1)]
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.cart.patch({slot: s})

    def test_surface_total_and_summon_reserves(self):
        s = self.fixture()
        s['platforms'] = [deepcopy(s['platforms'][0]) for _ in range(66)]
        s['movers'] = [dict(x=100,y=80,w=32,h=8,axis=0,travel=32,period=180,phase=0)] * 13
        with self.assertRaisesRegex(RomError, 'combined'):
            self.cart.patch({1: s})
        sky = deepcopy(self.cart.originals[1])
        self.assertEqual(self.cart.limits(sky)['enemies'], 42)
        sky['spotlights'] = [dict(x=100,y=30,w=32,h=32,travel=0,period=180,phase=0,dir=1,on=180,off=180)]
        self.assertEqual(self.cart.limits(sky)['enemies'], 34)
        water = deepcopy(self.cart.originals[6])
        water['spotlights'] = sky['spotlights']
        self.assertEqual(self.cart.limits(water)['enemies'], 32)

    def test_stage_theme_and_reward_identity_are_protected(self):
        s = self.fixture()
        s['theme'] = 1
        with self.assertRaisesRegex(RomError, 'environment fixed'):
            self.cart.patch({1: s})
        s = self.fixture()
        s['byte_id'] = 5
        self.assertEqual(self.cart.patch({1: s}), self.cart.data)

    def test_invalid_platform_reference_is_rejected(self):
        s = self.fixture()
        s['vanish'] = [len(s['platforms'])]
        with self.assertRaisesRegex(ValueError, 'invalid platform reference'):
            self.cart.patch({1: s})

    def test_headroom_preserves_runtime_coordinate_origin(self):
        s = self.fixture()
        s['headroom'] = s.get('headroom', 0) + 160
        s['height'] += 160
        for value in s.values():
            for p in value if isinstance(value, list) else [value]:
                if isinstance(p, dict) and 'y' in p:
                    p['y'] += 160
        data = self.cart.patch({1: s})
        b = self.cart.offset
        for name in ('spawn', 'platforms', 'height', 'enemies'):
            field = self.cart.fields[name]
            size = struct.calcsize('<' + field['format'])
            self.assertEqual(data[b+field['offset']:b+field['offset']+size],
                             self.cart.data[b+field['offset']:b+field['offset']+size])
        self.assertEqual(struct.unpack_from('<i', data, b + self.cart.fields['top']['offset'])[0], -s['headroom'])


@unittest.skipUnless(INPUT.is_file(), 'Supply the supported ROM to run HTTP checks.')
class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        (cls.root / 'rom').mkdir()
        shutil.copy2(INPUT, cls.root / 'rom' / server.ROM_NAME)
        shutil.copytree(ROOT / 'profiles', cls.root / 'profiles')
        cls.previous = server.WORKSPACE
        cls.w = server.WORKSPACE = server.Workspace(cls.root)
        cls.http = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        cls.url = f'http://127.0.0.1:{cls.http.server_port}'
        threading.Thread(target=cls.http.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        server.WORKSPACE = cls.previous
        cls.temp.cleanup()

    def call(self, path, data=None, headers=None, binary=False):
        h = {'X-Editor-Token': server.TOKEN, 'Content-Type': 'application/json'}
        h.update(headers or {})
        request = urllib.request.Request(self.url + path, headers=h,
                  data=None if data is None else json.dumps(data).encode())
        with urllib.request.urlopen(request) as response:
            return response.read() if binary else json.load(response)

    def test_catalog_and_every_slot(self):
        self.assertEqual(len(self.call('/api/catalog')['stages']), 17)
        for slot in range(1, 18):
            s = self.call('/api/stage/' + str(slot))
            self.assertTrue(self.call('/api/check', dict(slot=slot, stage=s))['ok'])

    def test_apply_multiple_stages_build_and_restore(self):
        s1 = deepcopy(self.w.cart().originals[0])
        s2 = deepcopy(self.w.cart().originals[1])
        s3 = deepcopy(self.w.cart().originals[2])
        s1['name'] = 'FIRST EDIT'
        s2['name'] = 'SECOND EDIT'
        s3['name'] = 'OPEN DRAFT'
        r = self.call('/api/apply', dict(slot=1, stage=s1))
        self.call('/api/apply', dict(slot=2, stage=s2))
        job = self.call('/api/build', dict(slot=3, stage=s3))
        self.assertEqual(job['state'], 'ready')
        data = self.call('/api/rom', binary=True)
        expected = self.w.cart().patch({1:s1,2:s2,3:s3})
        self.assertEqual(data, expected)
        self.assertEqual(self.w.output.read_bytes(), data)
        reopened = server.Workspace(self.root)
        self.assertEqual(reopened.load(2)['name'], 'SECOND EDIT')
        backup = self.call('/api/draft/' + r['backup'])
        self.call('/api/apply', backup)
        self.assertEqual(self.w.load(1), self.w.cart().originals[0])
        self.assertEqual((self.root/'rom'/server.ROM_NAME).read_bytes(), self.w.cart().data)

    def test_failure_keeps_previous_output(self):
        s = deepcopy(self.w.cart().originals[0])
        self.call('/api/build', dict(slot=1,stage=s))
        before = self.w.output.read_bytes()
        s['enemies'] = [dict(x=200,y=80,hp=2,kind=0)] * 43
        with self.assertRaises(urllib.error.HTTPError):
            self.call('/api/build', dict(slot=1,stage=s))
        self.assertEqual(self.w.output.read_bytes(), before)
        self.assertTrue(self.call('/api/save', dict(slot=1,stage=s))['warnings'])

    def test_no_rom_or_private_files_served(self):
        for path in ('/rom/Datakin-Server-Delver.gba', '/server.py', '/profiles/datakin-v078.json',
                     '/../../CLAUDE.md', '/api/draft/%2e%2e%2fserver.py'):
            with self.subTest(path=path), self.assertRaises(urllib.error.HTTPError):
                self.call(path)

    def test_mutations_require_token_and_local_origin(self):
        s = deepcopy(self.w.cart().originals[0])
        for headers in ({'X-Editor-Token':'bad'}, {'Origin':'https://example.invalid'},
                        {'Host':'example.invalid'}):
            with self.subTest(headers=headers), self.assertRaises(urllib.error.HTTPError) as error:
                self.call('/api/apply', dict(slot=1,stage=s), headers)
            self.assertEqual(error.exception.code, 403)

    def test_bad_slots_and_bad_bodies_are_rejected(self):
        for path in ('/api/stage/0', '/api/stage/18', '/api/stage/nope'):
            with self.assertRaises(urllib.error.HTTPError):
                self.call(path)
        for body in ([], None, {'slot':True}, {'slot':1,'stage':{}}):
            if body is None:
                continue
            with self.assertRaises(urllib.error.HTTPError):
                self.call('/api/build', body)


if __name__ == '__main__':
    unittest.main()
