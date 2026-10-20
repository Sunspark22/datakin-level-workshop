"""Package just the editor from an explicit allowlist (Python standard library)."""
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parent
FILES = (
    '.gitignore', '.gitattributes', '.github/workflows/checks.yml', 'README.md', 'LICENSE',
    'Start Editor.cmd', 'server.py', 'rom.py', 'validation.py', 'package.json',
    'build_release.py', 'support.py', 'rom/PUT-ROM-HERE.txt', 'profiles/index.json',
    'web/app.js', 'web/model.js', 'web/index.html', 'web/style.css', 'web/setup.html', 'web/setup.js',
    'tests/test_workshop.py', 'tests/test_support.py', 'tests/model.mjs',
)


def update_index():
    entries = []
    for path in sorted((ROOT / 'profiles').glob('datakin-*.json')):
        if path.is_symlink() or not re.fullmatch(r'datakin-v[0-9]{3,}(?:-[0-9a-f]{12})?\.json', path.name):
            raise ValueError('Invalid profile filename: ' + path.name)
        raw = path.read_bytes()
        profile = json.loads(raw)
        if profile.get('format') != 'datakin-rom-profile-v1':
            raise ValueError('Unsupported profile format: ' + path.name)
        entries.append(dict(file=path.name, label=profile['label'], rom_sha256=profile['sha256'],
                            profile_sha256=hashlib.sha256(raw).hexdigest()))
    (ROOT / 'profiles/index.json').write_text(json.dumps(dict(
        format='datakin-profile-index-v1', profiles=entries), indent=2) + '\n', encoding='utf-8', newline='\n')
    return FILES + tuple('profiles/' + entry['file'] for entry in entries)


def make_release(destination=None):
    destination = Path(destination or ROOT / 'dist/Datakin-Level-Workshop.zip')
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest = []
    files = update_index()
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in files:
            path = ROOT / name
            if not path.is_file() or path.is_symlink():
                raise ValueError('Missing or linked editor file: ' + name)
            data = path.read_bytes()
            if any(b'C:' + prefix in data for prefix in (b'\\Users\\', b'/Users/')):
                raise ValueError('Local machine path in public file: ' + name)
            manifest.append(hashlib.sha256(data).hexdigest() + '  ' + name)
            # Fixed metadata makes the same sources produce the same download.
            item = zipfile.ZipInfo('Datakin-Level-Workshop/' + name, (2026, 10, 19, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.external_attr = 0o100644 << 16
            archive.writestr(item, data)
        item = zipfile.ZipInfo('Datakin-Level-Workshop/MANIFEST.sha256', (2026, 10, 19, 0, 0, 0))
        item.compress_type = zipfile.ZIP_DEFLATED
        item.external_attr = 0o100644 << 16
        archive.writestr(item, '\n'.join(manifest) + '\n')
    print(f'{destination.name}: {destination.stat().st_size:,} bytes; '
          f'{len(files)} editor files + manifest; no ROM, game assets, or saves.')
    return destination


if __name__ == '__main__':
    make_release()
