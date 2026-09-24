"""Build a standalone executable on the target OS. Requires the iphone extra."""
import hashlib
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
    '--onefile', '--name', 'InstinctBridge', '--collect-data', 'instinct_bridge',
    '--collect-all', 'mitmproxy', '--collect-all', 'mitmproxy_rs',
    '--collect-all', 'publicsuffix2', '--collect-submodules', 'qrcode',
    '--distpath', 'dist', '--workpath', 'build', '--specpath', 'build',
    'scripts/desktop.py'], cwd=root, check=True)
filename = 'InstinctBridge.exe' if sys.platform == 'win32' else 'InstinctBridge'
binary = root / 'dist' / filename
(root / 'dist' / 'SHA256SUMS').write_text(hashlib.sha256(binary.read_bytes()).hexdigest() + '  ' + filename + '\n')
