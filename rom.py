"""Read/write level records in an explicitly supported, user-supplied ROM.

No game code or game assets are stored here. A profile contains only layout
metadata and a SHA-256 fingerprint. All base level data comes from the ROM.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import struct

from validation import validate

ROM_BASE = 0x08000000
MAX_ROM = 32 * 1024 * 1024
COUNTS = {
    'platforms': 'platform', 'enemies': 'enemy', 'pickups': 'pickup',
    'movers': 'mover', 'winds': 'wind', 'spikes': 'spike',
    'checkpoints': 'checkpoint', 'terrain': 'terrain', 'traps': 'trap',
    'lasers': 'laser', 'vanish': 'vanish', 'grass': 'grass',
    'waters': 'water', 'vines': 'vine', 'lava': 'lava', 'jets': 'jet',
    'rails': 'rail', 'arena': 'arena', 'caches': 'cache',
    'chemicals': 'chemical', 'emitters': 'emitter', 'arcs': 'arc',
    'belts': 'belt', 'spotlights': 'spotlight', 'switches': 'switch',
    'clouds': 'cloud', 'sections': 'section', 'crushers': 'crusher',
    'storms': 'storm',
}
MARKERS = ('spawn', 'checkpoint', 'exit', 'comate')
OPTIONAL = ('road_entry', 'road_return', 'miniboss_entry', 'miniboss_exit',
            'flight_start', 'flight_end', 'spiral', 'spiral_exit')
SHADOW = ('shadow_dusk', 'shadow_library_entry', 'shadow_blackout_start',
          'shadow_blackout_end')


class RomError(ValueError):
    pass


class Cartridge:
    def __init__(self, data, profile):
        self.data = bytes(data)
        self.profile = profile
        if (len(self.data) != profile['rom_bytes'] or
                hashlib.sha256(self.data).hexdigest() != profile['sha256']):
            raise RomError('Unsupported ROM. Use the original, unmodified '
                           f"{profile['label']} ROM; check README.md for its SHA-256. "
                           'Keep edited ROMs in output, not in rom.')
        self.fields = {f['name']: f for f in profile['fields']}
        self.offset = profile['stage_offset']
        self.size = profile['stage_size']
        self.count = profile['stage_count']
        if self.offset < 192 or self.offset + self.size * self.count > len(data):
            raise RomError('Invalid ROM profile: level table lies outside the file.')
        self.originals = [self.decode(slot) for slot in range(1, self.count + 1)]
        # Fail closed if an ABI/profile mistake would alter an unedited stage.
        for slot, stage in enumerate(self.originals, 1):
            if self.encode(slot, stage) != self.block(slot):
                raise RomError(f'ROM profile does not round-trip stage {slot}.')

    @classmethod
    def open(cls, path, profiles):
        path = Path(path)
        if not path.is_file():
            raise RomError('Put your original ROM at rom/Datakin-Server-Delver.gba, '
                           'then reload this page. No ROM is included with the editor.')
        if path.stat().st_size > MAX_ROM:
            raise RomError('The input ROM is larger than the GBA cartridge limit.')
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        for file in sorted(Path(profiles).glob('datakin-*.json')):
            profile = json.loads(file.read_text(encoding='utf-8'))
            if profile['sha256'] == digest:
                return cls(data, profile)
        raise RomError('Unsupported ROM (SHA-256 ' + digest + '). This editor needs '
                       'one of the original ROMs listed in README.md. Renaming a '
                       'different version does not make it compatible.')

    def check_slot(self, slot):
        if type(slot) is not int or not 1 <= slot <= self.count:
            raise RomError(f'Choose stage 1 through {self.count}.')

    def block(self, slot):
        self.check_slot(slot)
        start = self.offset + (slot - 1) * self.size
        return self.data[start:start + self.size]

    def read_field(self, block, name):
        f = self.fields[name]
        return struct.unpack_from('<' + f['format'], block, f['offset'])

    def stage_name(self, block):
        address = self.read_field(block, 'name')[0] - ROM_BASE
        if not 0 <= address < len(self.data) - 16:
            raise RomError('Invalid stage name address.')
        return self.data[address:address + 16].split(b'\0', 1)[0].decode('ascii')

    def decode(self, slot):
        block = self.block(slot)
        scalar = lambda name: self.read_field(block, name)[0]
        headroom = -scalar('top')
        s = {'format': 'datakin-stage-v1', 'name': self.stage_name(block),
             'width': scalar('width'), 'height': scalar('height') + headroom,
             'theme': scalar('theme'), 'draft': bool(scalar('draft')),
             'boss': scalar('boss'), 'byte_id': scalar('byte_id')}
        if headroom:
            s['headroom'] = headroom
        for name in MARKERS + OPTIONAL:
            x, y = self.read_field(block, name)
            if name in MARKERS or x or y:
                s[name] = {'x': x, 'y': y + headroom}
        for name in SHADOW:
            if scalar(name):
                # Only X is stored in the engine. Y is a canvas handle.
                s[name] = {'x': scalar(name), 'y': 50 + headroom}
        for name, prefix in COUNTS.items():
            count = scalar(prefix + '_count')
            f = self.fields[name]
            if not 0 <= count <= f['capacity']:
                raise RomError(f'Invalid {name} count in stage {slot}.')
            values = self.read_field(block, name)
            keys = f.get('keys')
            if keys:
                s[name] = []
                for i in range(count):
                    row = dict(zip(keys, values[i * len(keys):(i + 1) * len(keys)]))
                    if 'y' in row:
                        row['y'] += headroom
                    s[name].append(row)
            else:
                s[name] = list(values[:count])
        surfaces = self.read_field(block, 'surfaces')
        for p, surface in zip(s['platforms'] + s['movers'], surfaces):
            if surface:
                p['ice'] = surface - 1
        return validate(s)[0]

    def limits(self, stage=None):
        limits = {name: self.fields[name]['capacity'] for name in COUNTS}
        # Runtime enemies share the fixed enemy pool with summoned foes.
        reserved = self.profile['summon_reserve']
        if stage is None:
            extra = reserved['water'] + reserved['shadow']
        else:
            extra = (reserved['water'] if stage['theme'] in (6, 11) else 0)
            extra += reserved['shadow'] if stage.get('spotlights') else 0
        limits['enemies'] -= extra
        limits['surfaces'] = self.fields['surfaces']['capacity']
        return limits

    def checked(self, slot, stage):
        self.check_slot(slot)
        s, warnings = validate(stage)
        original = self.originals[slot - 1]
        if s['theme'] != original['theme']:
            raise RomError('This ROM edition keeps each stage environment fixed. '
                           'Choose a slot with the environment you want.')
        s['byte_id'] = original['byte_id']
        limits = self.limits(s)
        for name in COUNTS:
            if len(s[name]) > limits[name]:
                raise RomError(f"{name.replace('_', ' ').title()}: {len(s[name])} used, "
                               f"but this ROM supports {limits[name]} per stage. "
                               'Remove some objects or export the layout JSON for '
                               'a developer source build. The input ROM is unchanged.')
        used = len(s['platforms']) + len(s['movers'])
        if used > limits['surfaces']:
            raise RomError(f"Platforms + moving platforms: {used} used; this ROM "
                           f"supports {limits['surfaces']} combined.")
        return s, warnings

    def encode(self, slot, stage):
        s = deepcopy(stage)
        headroom = s.get('headroom', 0)
        block = bytearray(self.block(slot))

        def put(name, values):
            f = self.fields[name]
            struct.pack_into('<' + f['format'], block, f['offset'], *values)

        for name in ('width', 'theme', 'draft', 'boss', 'byte_id'):
            put(name, [int(s[name])])
        put('height', [s['height'] - headroom])
        put('top', [-headroom])
        for name in MARKERS + OPTIONAL:
            p = s.get(name)
            put(name, [p['x'], p['y'] - headroom] if p else [0, 0])
        for name in SHADOW:
            put(name, [s.get(name, {}).get('x', 0)])
        for name, prefix in COUNTS.items():
            rows = s[name]
            f = self.fields[name]
            put(prefix + '_count', [len(rows)])
            keys = f.get('keys')
            values = ([p[k] - (headroom if k == 'y' else 0)
                       for p in rows for k in keys] if keys else list(rows))
            total = f['capacity'] * (len(keys) if keys else 1)
            if len(values) > total:
                raise RomError(f'{name} exceeds ROM storage.')
            put(name, values + [0] * (total - len(values)))
        surfaces = [p.get('ice', -1) + 1 for p in s['platforms'] + s['movers']]
        count = self.fields['surfaces']['capacity']
        if len(surfaces) > count:
            raise RomError('Combined platform storage exceeded.')
        put('surfaces', surfaces + [0] * (count - len(surfaces)))
        return bytes(block)

    def patch(self, replacements):
        """Always rebuild from the immutable base; never modify it in place."""
        out = bytearray(self.data)
        for slot, stage in sorted(replacements.items()):
            s, _ = self.checked(slot, stage)
            block = bytearray(self.encode(slot, s))
            if s['name'] != self.originals[slot - 1]['name']:
                # New names are separate strings, so shared original strings
                # and surrounding ROM data can never be overwritten.
                out.extend(b'\0' * (-len(out) % 4))
                pointer = ROM_BASE + len(out)
                out.extend(s['name'].encode('ascii').ljust(16, b'\0'))
                struct.pack_into('<I', block, self.fields['name']['offset'], pointer)
            start = self.offset + (slot - 1) * self.size
            out[start:start + self.size] = block
        if len(out) > MAX_ROM:
            raise RomError('The edited ROM would exceed 32 MiB; the previous output is kept.')
        return bytes(out)
