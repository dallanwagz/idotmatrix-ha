# prompt2panel — design

Turn a natural-language description into a validated GIF and push it to the iDotMatrix panel,
from **any** interface (Signal, voice/ESP32, HTTP, and later the on-Pi TFT), through **one** shared
workflow. DRY-first: the pipeline is written once; interfaces are thin adapters.

## Architecture

```
   Signal bot        Voice / ESP32 buddy        HTTP /prompt        (existing REST /push, raw GIFs)
       │                     │                       │                          │
       └─────────┬───────────┴───────────┬───────────┘                          │
                 ▼   Job{prompt, opts}    ▼                                      │
        ┌──────────────────────────────────────────────┐                        │
        │  CORE  pipeline.core.prompt_to_panel(job)       │                        │
        │   1. GENERATE  Sonnet writes Pillow/assetlib    │                        │
        │      code → run sandboxed → GIF                 │                        │
        │   2. VALIDATE  validate_gif.check()             │                        │
        │   3. REPAIR    feed failures back to Sonnet     │                        │
        │      (≤N tries) — compliant by construction     │                        │
        │   4. DELIVER  POST → idm-panel-api /push  ───────┼────────────┐          │
        └─────────────────────────────────────────────────┘            │          │
                                                                        ▼          ▼
                                                            idm-panel-api (Pi, built) → BLE → panel
```

**The seam is the REST API we already built.** The core's last step is the same `POST /push`
any client uses, so "brain" (generation; needs Anthropic + Python) and "hands" (the Pi that owns
the Bluetooth) are decoupled — the brain can run on the Pi or a separate box with no code change.

## Why "LLM writes the generator," not "LLM draws pixels"
Sonnet emits a small **Pillow/`assetlib` Python program** that renders the GIF (exactly how the
deluxe World Cup packs were made). Benefits: spec-compliant *by construction*, cheap (one code-gen
call + local render), reuses the whole toolkit, deterministic to re-run/cache. A **validate→repair
loop** feeds any spec-check failures back to the model to fix its code, so nothing non-compliant
ever reaches the panel.

## Contracts (the DRY core)
```python
Job(prompt, source="api", panel="big", mode="now", dwell=30, max_repair=3)
Result(ok, message, gif_path, preview_path, validation, pushed, attempts, code, error)
prompt_to_panel(job) -> Result          # generate → validate → repair → deliver
```
Every interface builds a `Job`, calls `prompt_to_panel`, and renders `Result.message`
(+ `preview_path`) in its own medium. A new interface = a new adapter, zero pipeline changes.

## Components
| Path | Role |
|---|---|
| `pipeline/generate.py` | Anthropic call (Sonnet) → generator code → sandboxed exec → GIF; repair loop |
| `pipeline/deliver.py` | `POST` the GIF to `idm-panel-api /push` (reuse the container) |
| `pipeline/core.py` | orchestrates generate→validate→repair→deliver; returns `Result` |
| `pipeline/config.py` | env-based config (API key, model, panel-api URL, dirs) |
| `interfaces/signal_bot.py` | Signal ↔ core (signal-cli JSON-RPC); replies with preview + status |
| `interfaces/http_prompt.py` | `POST /prompt {text}` for the voice/ESP32 buddy + future UIs |
| `interfaces/tft_*` (stretch) | on-Pi touchscreen: a "recent pushes" cache/browser + a re-push button |

## Deployment topologies (both supported by the seam)
- **All-on-Pi:** the Pi runs `idm-panel-api` *and* the brain (Anthropic call + code exec are light).
- **Split brain/hands:** a beefier "bot host" runs the brain + Signal/voice; it POSTs finished GIFs
  to the Pi's `idm-panel-api`. Matches "the bot with Anthropic credits" being a separate box.

## Open questions (fill in when specifics arrive)
1. **ESP32 buddy** integration model — HTTP webhook / MQTT / tool-plugin? Decides whether it hits
   `/prompt` directly or via a bridge. (It already solves voice capture + STT + TTS.)
2. **Bot host + creds** — Pi or separate box; `ANTHROPIC_API_KEY` location.
3. **Signal** — number / `signal-cli` registration to bind.

## Security notes
- Executing model-written code runs in a **subprocess** with a clean env (no secrets), a scratch
  CWD, a timeout, and no network. It's still model-authored code — keep the brand host trusted.
- Rate-limit the interfaces; the panel push is already serialized (single BLE central).
