"""Build a standalone executable on the target OS. Requires the iphone extra."""
import hashlib
from pathlib import Path
import platform
import subprocess
import sys
import tarfile

root = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
    '--onefile', '--name', 'InstinctBridge', '--collect-data', 'instinct_bridge',
    '--collect-all', 'mitmproxy', '--collect-all', 'mitmproxy_rs',
    '--collect-all', 'publicsuffix2', '--collect-submodules', 'qrcode',
    '--distpath', 'dist', '--workpath', 'build', '--specpath', 'build',
    'scripts/desktop.py'], cwd=root, check=True)
filename = 'InstinctBridge.exe' if sys.platform == 'win32' else 'InstinctBridge'
binary = root / 'dist' / filename
checksums = [(filename, binary)]
if sys.platform.startswith('linux'):
    archive = root / 'dist' / f'InstinctBridge-linux-{platform.machine().lower()}.tar.gz'
    with tarfile.open(archive, 'w:gz') as package:
        package.add(binary, arcname=filename)
    checksums.append((archive.name, archive))
(root / 'dist' / 'SHA256SUMS').write_text(''.join(
    hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + name + '\n'
    for name, path in checksums))
