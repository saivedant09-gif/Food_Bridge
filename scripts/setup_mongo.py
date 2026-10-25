"""Install a verified, project-local MongoDB binary. No Windows service/admin needed."""
from pathlib import Path
import hashlib
import os
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '8.0.34'
URL = f'https://fastdl.mongodb.org/windows/mongodb-windows-x86_64-{VERSION}.zip'
SHA256 = '6b021a0864494e4decf278b36477a29eb36072432773e4e62c2f42c302630db0'
DESTINATION = ROOT / '.tools' / 'mongodb'


def install():
    binary = DESTINATION / 'bin' / 'mongod.exe'
    if binary.exists():
        return binary
    if os.name != 'nt':
        raise RuntimeError('Install MongoDB on this OS and put mongod on PATH, or provide MONGO_URI.')
    DESTINATION.mkdir(parents=True, exist_ok=True)
    archive = DESTINATION / f'mongodb-{VERSION}.zip'
    if not archive.exists():
        print(f'Downloading MongoDB {VERSION} from mongodb.org...', flush=True)
        partial = archive.with_suffix('.partial')
        request = urllib.request.Request(URL, headers={'User-Agent': 'FoodBridge-LocalSetup/1.0'})
        total = 0
        with urllib.request.urlopen(request, timeout=60) as response, partial.open('wb') as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
                total += len(chunk)
                if total % (32 * 1024 * 1024) == 0:
                    print(f'Downloaded {total // (1024 * 1024)} MB', flush=True)
        partial.replace(archive)
    digest = hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest()
    if digest != SHA256:
        raise RuntimeError('MongoDB archive checksum mismatch; installation stopped. Remove the invalid archive before retrying.')
    with zipfile.ZipFile(archive) as source:
        for item in source.infolist():
            path = Path(item.filename)
            if 'bin' in path.parts and (path.name == 'mongod.exe' or path.suffix.lower() == '.dll'):
                target = DESTINATION / 'bin' / path.name
                target.parent.mkdir(exist_ok=True)
                target.write_bytes(source.read(item))
    if not binary.exists():
        raise RuntimeError('MongoDB archive did not include mongod.exe.')
    print('MongoDB installed and SHA-256 verified.', flush=True)
    return binary


if __name__ == '__main__':
    try:
        print(install())
    except Exception as error:
        print(f'MongoDB setup failed: {error}', file=sys.stderr)
        raise SystemExit(1)
