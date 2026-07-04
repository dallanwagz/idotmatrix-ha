# prompt2panel

Describe an animation in words → get a spec-compliant GIF → it appears on the panel. From Signal,
voice (ESP32 buddy), HTTP, or (stretch) the on-Pi touchscreen — all through **one** shared workflow.
See [DESIGN.md](DESIGN.md) for the architecture.

## Layout
```
pipeline/            the DRY core (written once)
  generate.py        Sonnet writes Pillow/assetlib code → sandboxed render → repair loop
  deliver.py         POST the GIF to idm-panel-api /push (reuse the container)
  core.py            prompt_to_panel(Job) -> Result   (generate→validate→repair→deliver)
  config.py          env-based config
interfaces/          thin adapters — each builds a Job, renders the Result
  http_prompt.py     POST /prompt {text}  ← voice/ESP32 + future web UIs
  signal_bot.py      Signal ↔ core (signal-cli JSON-RPC), replies with preview + status
```

## Setup
```bash
cd prompt2panel
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # fill in ANTHROPIC_API_KEY, IDM_API_URL, Signal number
set -a; . ./.env; set +a
```
Requires the **idm-panel-api** container running (the panel driver) — that's the `IDM_API_URL`.

## Run an interface
```bash
python3 interfaces/http_prompt.py          # POST /prompt {"text":"a spinning red heart"}
python3 interfaces/signal_bot.py           # text your Signal number a description
```

## Bot commands (Signal/Telegram) — dev panel + chooser + save
- **`/panel <description>`** — *generate* a new GIF and show it (the dev panel). If `<description>`
  is a saved asset's name, it shows that instead.
- **`/show <name>`** — *chooser*: push a saved asset. Bare `/show` (or `/list`) lists the library.
- **`/save <name>`** — save the **last generated** GIF into the library. Workflow: `/panel …` →
  "love it" → `/save brazil_2` → later `/show brazil_2`.

Saved assets live under `P2P_WORK_DIR/library/<name>.gif` (see `pipeline/library.py`); the last
generated GIF is tracked at `P2P_WORK_DIR/last.gif`.

## Status
- **Core + Signal + HTTP interfaces: scaffolded.** Generation uses Sonnet to write generator code
  (spec-compliant by construction) with a validate→repair loop; delivery reuses the REST API.
- **Voice/ESP32:** posts transcribed text to `/prompt` — exact bridge TBD on the buddy's specifics.
- **TFT dashboard (stretch):** feasible (userspace `adafruit-circuitpython-rgb-display` + XPT2046
  touch, SPI0, doesn't touch Bluetooth); will read the `P2P_WORK_DIR` cache as a "recent pushes"
  browser with re-push. Adapter to come.

## Not yet wired
Real Anthropic calls need a key + credits; Signal needs a registered `signal-cli` daemon. The code
is structured and importable; end-to-end run is pending those + your ESP32 integration model.
