"""Local, standard-library-only host for the ROM edition of Level Workshop."""
import argparse
import hashlib
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

from rom import Cartridge, RomError
from validation import validate
from support import install_support

ROOT = Path(__file__).resolve().parent
ROM_NAME = 'Datakin-Server-Delver.gba'
OUTPUT_NAME = 'Datakin-Edited.gba'
TOKEN = secrets.token_urlsafe(32)
PROJECT = 'rom-workshop-' + hashlib.sha256(str(ROOT).encode()).hexdigest()[:16]


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + secrets.token_hex(6) + '.tmp')
    try:
        temp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


class Workspace:
    def __init__(self, root):
        self.root = Path(root)
        self.cartridge = None
        self.lock = threading.RLock()
        self.job = dict(state='idle', message='Build an edited ROM after making changes.')
        self.drafts = self.root / 'workspace/drafts'
        self.applied = self.root / 'workspace/applied'
        self.output = self.root / 'output' / OUTPUT_NAME

    def cart(self):
        with self.lock:
            if self.cartridge is None:
                self.cartridge = Cartridge.open(self.root / 'rom' / ROM_NAME, self.root / 'profiles')
            return self.cartridge

    def record(self, slot, stage, backup=False):
        return dict(slot=slot, stage=stage, backup=backup,
                    base_sha256=self.cart().profile['sha256'])

    def read_record(self, path):
        data = json.loads(path.read_text(encoding='utf-8'))
        if data.get('base_sha256') != self.cart().profile['sha256']:
            raise RomError('This workspace layout belongs to a different ROM profile. '
                           'Import its JSON into the matching editor version.')
        slot = data['slot']
        self.cart().check_slot(slot)
        stage, _ = validate(data['stage'])
        return {**data, 'stage': stage}

    def load(self, slot):
        cart = self.cart()
        cart.check_slot(slot)
        path = self.applied / f'stage{slot}.json'
        return self.read_record(path)['stage'] if path.is_file() else cart.originals[slot - 1]

    def checked(self, data):
        if not isinstance(data, dict):
            raise ValueError('Choose a stage and a layout.')
        slot = data.get('slot')
        self.cart().check_slot(slot)
        stage, warnings = self.cart().checked(slot, data.get('stage'))
        return slot, stage, warnings

    def draft_catalog(self):
        result = []
        for path in sorted(self.drafts.glob('*.json'), reverse=True):
            try:
                d = self.read_record(path)
                name = ('Backup before apply · ' if d.get('backup') else '') + d['stage']['name']
                result.append(dict(id=path.name, name=name))
            except (ValueError, KeyError, OSError, TypeError):
                # A damaged draft shouldn't prevent opening the whole workshop.
                result.append(dict(id=path.name, name='Unreadable draft (kept on disk)'))
        return result

    def save(self, slot, stage, backup=False):
        name = f'{time.time_ns()}-{secrets.token_hex(3)}.json'
        atomic_json(self.drafts / name, self.record(slot, stage, backup))
        return name

    def apply(self, slot, stage):
        with self.lock:
            stage, warnings = self.cart().checked(slot, stage)
            backup = self.save(slot, self.load(slot), backup=True)
            atomic_json(self.applied / f'stage{slot}.json', self.record(slot, stage))
            self.job = dict(state='idle', message='Applied in this editor workspace. Build an edited ROM to play.')
            return dict(ok=True, stage=stage, backup=backup, warnings=warnings)

    def build(self, slot, stage):
        with self.lock:
            try:
                cart = self.cart()
                layouts = {i: self.load(i) for i in range(1, cart.count + 1)}
                layouts[slot] = stage
                data = cart.patch(layouts)
                self.output.parent.mkdir(parents=True, exist_ok=True)
                pending = self.output.with_suffix('.next.gba')
                pending.write_bytes(data)
                try:
                    os.replace(pending, self.output)
                except PermissionError:
                    raise RomError('Close the edited ROM in your emulator and try again. '
                                   'The previous output is kept.') from None
                self.job = dict(state='ready', bytes=len(data), rom='/api/rom',
                                message='Built all applied stages + your open draft. '
                                'Saved to output/Datakin-Edited.gba. Open it in your '
                                'emulator or copy it to your cartridge. Rebuild after more edits.')
            except Exception as exc:
                self.job = dict(state='error', message=str(exc))
            return self.job.copy()


WORKSPACE = Workspace(ROOT)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, data, status=200, mime='application/json'):
        if mime == 'application/json':
            data = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' blob:; "
                         "style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'")
        if mime == 'application/octet-stream':
            self.send_header('Content-Disposition', 'attachment; filename="' + OUTPUT_NAME + '"')
        self.end_headers()
        self.wfile.write(data)

    def allowed(self):
        return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'

    def do_GET(self):
        if not self.allowed():
            return self.send(dict(error='Use the local editor address.'), 403)
        path = urllib.parse.urlsplit(self.path).path
        w = WORKSPACE
        try:
            if path == '/api/health':
                return self.send(dict(project=PROJECT, editor='Datakin Workshop · ROM edition'))
            if path == '/':
                try:
                    w.cart()
                except (ValueError, OSError) as exc:
                    page = (ROOT / 'web/setup.html').read_text(encoding='utf-8')
                    return self.send(page.replace('STATUS_MESSAGE', html.escape(str(exc)))
                                     .replace('SESSION_TOKEN', TOKEN).encode(),
                                     mime='text/html; charset=utf-8')
                return self.send((ROOT / 'web/index.html').read_bytes(), mime='text/html; charset=utf-8')
            if path == '/api/catalog':
                cart = w.cart()
                return self.send(dict(token=TOKEN, stages=[dict(slot=i, name=w.load(i)['name'])
                                 for i in range(1, cart.count + 1)], drafts=w.draft_catalog(),
                                 limits=cart.limits(), profile=cart.profile['label'],
                                 enemy_pool=cart.fields['enemies']['capacity'],
                                 summon_reserve=cart.profile['summon_reserve'],
                                 profile_hash=cart.profile['sha256'], project=PROJECT))
            if path.startswith('/api/stage/'):
                return self.send(w.load(int(path.rsplit('/', 1)[-1])))
            if path.startswith('/api/draft/'):
                name = path.rsplit('/', 1)[-1]
                if not re.fullmatch(r'\d{16,22}-[0-9a-f]{6}\.json', name):
                    raise ValueError('Invalid draft name.')
                return self.send(w.read_record(w.drafts / name))
            if path == '/api/job':
                return self.send(w.job.copy())
            if path == '/api/rom':
                if w.job['state'] != 'ready':
                    raise ValueError('Build an edited ROM first.')
                return self.send(w.output.read_bytes(), mime='application/octet-stream')
            files = {'/app.js': 'app.js', '/model.js': 'model.js', '/style.css': 'style.css',
                     '/setup.js': 'setup.js'}
            if path not in files:
                return self.send(dict(error='Not found.'), 404)
            file = ROOT / 'web' / files[path]
            return self.send(file.read_bytes(), mime=mimetypes.guess_type(file.name)[0] or 'text/plain')
        except (ValueError, KeyError, TypeError, OSError) as exc:
            self.send(dict(error=str(exc)), 400)

    def do_POST(self):
        origin = self.headers.get('Origin')
        if (not self.allowed() or self.headers.get('X-Editor-Token') != TOKEN or
                (origin and origin != f'http://127.0.0.1:{self.server.server_port}')):
            return self.send(dict(error='Reopen the editor to reconnect.'), 403)
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 1024 * 1024:
                raise ValueError('The request is too large or empty.')
            if not self.headers.get('Content-Type', '').startswith('application/json'):
                raise ValueError('Expected JSON content.')
            data = json.loads(self.rfile.read(size))
            path = urllib.parse.urlsplit(self.path).path
            if path == '/api/stop':
                self.send(dict(ok=True))
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            w = WORKSPACE
            if path == '/api/support':
                with w.lock:
                    result = install_support(w.root)
                    w.cartridge = None
                return self.send(result)
            # Drafts may retain an oversized design for JSON export. Applying or
            # building is stricter and always enforces the ROM's actual storage.
            if path in ('/api/save', '/api/validate'):
                slot = data.get('slot')
                w.cart().check_slot(slot)
                stage, warnings = validate(data.get('stage'))
                try:
                    w.cart().checked(slot, stage)
                except RomError as exc:
                    warnings.append(str(exc))
                if path == '/api/validate':
                    return self.send(dict(ok=True, warnings=warnings))
                return self.send(dict(ok=True, id=w.save(slot, stage), warnings=warnings))
            slot, stage, warnings = w.checked(data)
            if path == '/api/check':
                return self.send(dict(ok=True, warnings=warnings))
            if path == '/api/apply':
                return self.send(w.apply(slot, stage))
            if path == '/api/build':
                return self.send(w.build(slot, stage))
            return self.send(dict(error='Not found.'), 404)
        except (ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
            self.send(dict(error=str(exc), issues=getattr(exc, 'issues', [])), 400)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--open', action='store_true', help='Open the local editor in your browser')
    parser.add_argument('--port', type=int, default=8776)
    parser.add_argument('--check-rom', action='store_true', help='Verify the supplied ROM and exit')
    args = parser.parse_args()
    if args.check_rom:
        try:
            cart = WORKSPACE.cart()
            print(f"Ready: {cart.profile['label']}, {cart.count} editable stage slots.")
        except (ValueError, OSError) as exc:
            parser.exit(1, str(exc) + '\n')
        return
    for port in range(args.port, min(args.port + 10, 65536)):
        url = f'http://127.0.0.1:{port}'
        try:
            with urllib.request.urlopen(url + '/api/health', timeout=.3) as response:
                if json.load(response).get('project') == PROJECT:
                    if args.open:
                        webbrowser.open(url)
                    print('Already running: ' + url)
                    return
        except (OSError, ValueError):
            pass
        try:
            server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
            break
        except OSError:
            continue
    else:
        parser.exit(1, 'No free local port. Try --port with another number.\n')
    print('Datakin Level Workshop · ROM edition\n' + url, flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
