"""One-command local launcher: py run.py. Ctrl+C stops processes started here."""
from pathlib import Path
import argparse
import importlib.util
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import venv
import webbrowser

ROOT = Path(__file__).resolve().parent
LOCAL = ROOT / '.local'


def port_open(port):
    with socket.socket() as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(('127.0.0.1', port)) == 0


def get_json(url):
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    os.chdir(ROOT)
    python = ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.exists():
        print('Creating Python environment...', flush=True)
        venv.create(ROOT / '.venv', with_pip=True)
    if Path(sys.prefix).resolve() != (ROOT / '.venv').resolve():
        return subprocess.call([str(python), '-B', '-u', str(Path(__file__).resolve()), *sys.argv[1:]])
    if any(importlib.util.find_spec(module) is None for module in ['fastapi', 'uvicorn', 'mysql', 'pymongo', 'dotenv']):
        subprocess.run([str(python), '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
    from dotenv import dotenv_values
    from pymongo import MongoClient
    from scripts.setup_data import setup
    from scripts.setup_mongo import install
    if not (ROOT / '.env').exists():
        raise RuntimeError('Create .env from .env.example and set your local MySQL credentials. See README.md.')
    config = dotenv_values(ROOT / '.env')
    npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
    node = shutil.which('node')
    if not npm or not node:
        raise RuntimeError('Node.js/npm is required. Install Node.js, then run this command again.')
    if not (ROOT / 'frontend/node_modules/vite').exists():
        subprocess.run([npm, 'ci'], cwd=ROOT / 'frontend', check=True)
    LOCAL.mkdir(exist_ok=True)
    children, logs = [], []

    def start(command, name, cwd=ROOT):
        log = (LOCAL / f'{name}.log').open('a', encoding='utf-8')
        logs.append(log)
        options = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {'start_new_session': True}
        process = subprocess.Popen(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, **options)
        children.append((name, process))
        return process

    def wait_for(check, name, process=None):
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if process is not None and process.poll() is not None:
                raise RuntimeError(f'{name} exited. See .local/{name}.log.')
            try:
                if check():
                    return
            except Exception:
                pass
            time.sleep(0.5)
        raise RuntimeError(f'{name} did not become ready. See .local/{name}.log.')

    try:
        uri = config.get('MONGO_URI') or 'mongodb://127.0.0.1:27017'
        def mongo_ready():
            with MongoClient(uri, serverSelectionTimeoutMS=1000) as client:
                return client.admin.command('ping')['ok'] == 1
        try:
            ready = mongo_ready()
        except Exception:
            ready = False
        if not ready:
            if uri.rstrip('/') not in ('mongodb://127.0.0.1:27017', 'mongodb://localhost:27017'):
                raise RuntimeError('Configured external MongoDB is unreachable. Check MONGO_URI.')
            if port_open(27017):
                raise RuntimeError('Port 27017 is occupied by a service that does not respond as MongoDB.')
            mongo = shutil.which('mongod') or str(install())
            data = LOCAL / 'mongodb'
            data.mkdir(exist_ok=True)
            process = start([mongo, '--dbpath', str(data), '--bind_ip', '127.0.0.1', '--port', '27017'], 'mongodb')
            wait_for(mongo_ready, 'mongodb', process)
        setup()
        if not port_open(8000):
            process = start([str(python), '-B', '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000'], 'api')
            wait_for(lambda: get_json('http://127.0.0.1:8000/health')['status'] == 'ready', 'api', process)
        else:
            schema = get_json('http://127.0.0.1:8000/openapi.json')
            if schema.get('info', {}).get('title') != 'Food Bridge API' or '/health' not in schema.get('paths', {}):
                raise RuntimeError('Port 8000 has another or older API running. Stop it and run again.')
            if get_json('http://127.0.0.1:8000/health')['status'] != 'ready':
                raise RuntimeError('Existing API is not ready.')
        if not port_open(5173):
            process = start([node, str(ROOT / 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '5173', '--strictPort'], 'frontend', ROOT / 'frontend')
            wait_for(lambda: port_open(5173), 'frontend', process)
        with urllib.request.urlopen('http://127.0.0.1:5173', timeout=5) as response:
            if 'Food Bridge' not in response.read().decode('utf-8'):
                raise RuntimeError('Port 5173 is occupied by another website.')
        print('\nFOOD BRIDGE IS READY\nWebsite: http://127.0.0.1:5173\nAPI docs: http://127.0.0.1:8000/docs\nMySQL and MongoDB: connected\nKeep this window open. Press Ctrl+C to stop.\n', flush=True)
        if not args.no_browser:
            webbrowser.open('http://127.0.0.1:5173')
        while True:
            for name, process in children:
                if process.poll() is not None:
                    raise RuntimeError(f'{name} stopped unexpectedly. See .local/{name}.log.')
            time.sleep(1)
    except KeyboardInterrupt:
        print('\nStopping Food Bridge...', flush=True)
    finally:
        for name, process in reversed(children):
            if process.poll() is not None:
                continue
            try:
                if name == 'mongodb':
                    with MongoClient(uri, serverSelectionTimeoutMS=2000) as client:
                        client.admin.command('shutdown')
                elif os.name == 'nt':
                    process.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    os.killpg(process.pid, signal.SIGTERM)
            except Exception:
                pass
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    os.killpg(process.pid, signal.SIGKILL)
        for log in logs:
            log.close()
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f'\nStartup failed: {error}', file=sys.stderr)
        raise SystemExit(1)
