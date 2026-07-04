"""Environment-based config for prompt2panel. Nothing secret is hard-coded."""
import os

# Anthropic
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = os.environ.get("P2P_MODEL", "claude-sonnet-5")          # Sonnet by default
MAX_REPAIR = int(os.environ.get("P2P_MAX_REPAIR", "3"))

# The panel driver (the REST API container we already built). Brain talks to hands over HTTP.
IDM_API_URL = os.environ.get("IDM_API_URL", "http://bt.local:8080")
DEFAULT_PANEL = os.environ.get("IDM_PANEL", "big")

# Where generated artifacts land (gif + preview + code), for caching / the TFT browser.
WORK_DIR = os.environ.get("P2P_WORK_DIR", os.path.expanduser("~/prompt2panel-out"))

# Sandbox limits for running model-written generator code
GEN_TIMEOUT_S = int(os.environ.get("P2P_GEN_TIMEOUT", "40"))

# path to the repo's pi-quickstart (assetlib/validate_gif) — importable by generated code + us
REPO_ROOT = os.environ.get("P2P_REPO_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
PI_QUICKSTART = os.path.join(REPO_ROOT, "pi-quickstart")
SPEC_PATH = os.path.join(REPO_ROOT, "docs", "idm64-gif-spec.md")
