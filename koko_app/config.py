import os
import subprocess
import sys

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".koko_gui_config.json")
PIPELLM_BASE_URL = "https://cc-api.pipellm.ai"
PIPELLM_MODEL = "claude-sonnet-4-6"
U2NET_MODEL_DIR = os.path.expanduser("~/.u2net")
U2NET_MODEL_PATH = os.path.join(U2NET_MODEL_DIR, "u2net.onnx")


def ensure_runtime_dependencies():
    # Packaged apps must rely on bundled dependencies instead of mutating
    # the user's Python environment at startup.
    if getattr(sys, "frozen", False):
        return

    try:
        import scipy  # noqa: F401
    except ImportError:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "scipy", "--break-system-packages", "-q"],
            capture_output=True,
        )
