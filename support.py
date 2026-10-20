"""Opt-in compatibility-profile updates. Never downloads or executes code."""
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import struct
import urllib.error
import urllib.request

from rom import Cartridge, MAX_ROM, RomError

BASE_URL = 'https://raw.githubusercontent.com/Sunspark22/datakin-level-workshop/main/profiles/'
PROFILE_NAME = r'datakin-v[0-9]{3,}(?:-[0-9a-f]{12})?\.json'
MAX_JSON = 256 * 1024


def download_json(name):
    request = urllib.request.Request(BASE_URL + name, headers={'User-Agent': 'Datakin-Level-Workshop'})
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            raw = response.read(MAX_JSON + 1)
    except (OSError, urllib.error.URLError):
        raise RomError('Could not check GitHub for ROM support. Check your connection and try again. '
                       'Your ROM and layouts have not changed.') from None
    if len(raw) > MAX_JSON:
        raise RomError('Compatibility download is too large.')
    try:
        return raw, json.loads(raw)
    except (ValueError, UnicodeError):
        raise RomError('GitHub did not return a valid compatibility file.') from None


def validate_profile(profile, data):
    """Bound remote metadata before it reaches struct decoding or patching."""
    def integer(n, lo, hi):
        return type(n) is int and lo <= n <= hi

    try:
        if profile['format'] != 'datakin-rom-profile-v1':
            raise ValueError('This ROM needs a newer editor. Download the latest editor release.')
        size = profile['stage_size']
        if (not integer(size, 4, 256 * 1024) or not integer(profile['stage_count'], 1, 64)
                or not integer(profile['stage_offset'], 192, len(data))
                or not integer(profile['revision'], 0, 255)
                or profile['revision'] != data[188]
                or not isinstance(profile['label'], str) or len(profile['label']) > 100):
            raise ValueError('Invalid compatibility metadata.')
        fields = profile['fields']
        if not isinstance(fields, list) or not 1 <= len(fields) <= 128:
            raise ValueError('Invalid compatibility fields.')
        names = set()
        for field in fields:
            name, offset, fmt, capacity = (field[k] for k in ('name', 'offset', 'format', 'capacity'))
            if (not isinstance(name, str) or not re.fullmatch(r'[a-z_]+', name)
                    or name in names or not integer(offset, 0, size - 1)
                    or not integer(capacity, 1, 65536) or not isinstance(fmt, str)
                    or not re.fullmatch(r'[1-9][0-9]{0,4}[iIB]', fmt)
                    or offset + struct.calcsize('<' + fmt) > size):
                raise ValueError('Invalid compatibility field.')
            names.add(name)
            keys = field.get('keys')
            if keys is not None and (not isinstance(keys, list) or not 1 <= len(keys) <= 16
                    or any(not isinstance(k, str) or not re.fullmatch(r'[a-z_]+', k) for k in keys)):
                raise ValueError('Invalid compatibility field keys.')
        reserve = profile['summon_reserve']
        if not all(integer(reserve[k], 0, 64) for k in ('water', 'shadow')):
            raise ValueError('Invalid reserved enemy slots.')
        # Exact hash + size, bounds, every stage decode, and byte-exact round-trip.
        return Cartridge(data, profile)
    except (KeyError, TypeError, IndexError, OverflowError, struct.error) as exc:
        raise RomError('This compatibility profile needs a newer editor or is invalid.') from exc


def install_support(root):
    root = Path(root)
    path = root / 'rom/Datakin-Server-Delver.gba'
    if not path.is_file():
        raise RomError('Put your original ROM in the rom folder before checking for support.')
    if not 192 <= path.stat().st_size <= MAX_ROM:
        raise RomError('This file is not a supported GBA ROM.')
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    # Already-supported originals remain usable even without a connection.
    try:
        cart = Cartridge.open(path, root / 'profiles')
        return dict(ok=True, installed=False, label=cart.profile['label'],
                    message='This ROM is already supported. Open the workshop.')
    except RomError:
        pass
    _, index = download_json('index.json')
    if not isinstance(index, dict) or index.get('format') != 'datakin-profile-index-v1':
        raise RomError('This support catalog needs a newer editor.')
    entries = index.get('profiles')
    if not isinstance(entries, list) or len(entries) > 2048:
        raise RomError('Invalid support catalog.')
    entry = next((p for p in entries if isinstance(p, dict) and p.get('rom_sha256') == digest), None)
    if entry is None:
        raise RomError('No verified support profile is published for this ROM yet. '
                       'Check again after its profile is released. No files were changed.')
    name = entry.get('file')
    if not isinstance(name, str) or not re.fullmatch(PROFILE_NAME, name):
        raise RomError('Invalid compatibility filename.')
    raw, profile = download_json(name)
    if hashlib.sha256(raw).hexdigest() != entry.get('profile_sha256'):
        raise RomError('Compatibility download checksum mismatch. Try again later.')
    cart = validate_profile(profile, data)
    folder = root / 'profiles'
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / name
    if target.exists() and target.read_bytes() != raw:
        raise RomError('A different profile already uses this filename. Please update the editor.')
    pending = folder / (name + '.' + secrets.token_hex(6) + '.tmp')
    try:
        pending.write_bytes(raw)
        os.replace(pending, target)
    finally:
        pending.unlink(missing_ok=True)
    return dict(ok=True, installed=True, label=cart.profile['label'],
                message='Added verified support for ' + cart.profile['label'] + '. Open the workshop.')
