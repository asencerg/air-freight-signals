"""Exercise the actual bridge lifecycle without adding runtime dependencies."""
from pathlib import Path
import shutil
import subprocess
import pytest


def test_component_rerender_and_unmount_lifecycle():
    node = shutil.which('node')
    if node is None:
        pytest.skip('Optional Node executable is needed for the JavaScript lifecycle test')
    subprocess.run([node, str(Path(__file__).with_name('map_component_lifecycle.mjs'))], check=True, timeout=15)
