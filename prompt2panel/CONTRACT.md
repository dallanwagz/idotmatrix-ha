# `/prompt` contract — for the voice-bridge (and any UI) that calls the pipeline

This is the frozen seam between an interface and the shared core. The **voice-bridge**
(ESP32 → Opus → ASR → text) POSTs the transcript here and speaks the reply back.

## Endpoint
```
POST http://<bot-host>:8090/prompt        Content-Type: application/json
```
- **Host:** the **bot host CT150 = `10.10.2.9`** (it holds `ANTHROPIC_API_KEY`; the core runs there).
- **Port:** `8090` (default; override with env `P2P_PROMPT_PORT`).
- Health: `GET http://10.10.2.9:8090/health` → `{"status":"ok"}`.

## Request
```json
{
  "prompt": "a spinning red heart",     // REQUIRED — the transcribed description
  "source": "voice",                    // optional label (voice | signal | ui | ...)
  "mode":   "now",                      // optional: "now" (live, default) | "store" (persist)
  "dwell":  30,                         // optional: seconds, only for mode=store
  "panel":  "big"                       // optional: panel name (default "big")
}
```
(`text` is accepted as an alias for `prompt`, but send `prompt`.)

## Response
`200` on a completed attempt (whether or not the push succeeded — check `pushed`):
```json
{
  "ok": true,                           // true iff it rendered AND pushed to the panel
  "message": "Done — it's on the panel (1 attempt).",   // SPEAK THIS back to the user
  "pushed": true,
  "attempts": 1
}
```
`400` if `prompt` is empty: `{"ok": false, "message": "Give me something to make."}`.

**The bridge should just speak `message`.** It's written to be spoken (success, "couldn't build that
one: …", or a push failure), so no formatting needed on your side.

## Async / fast-ack (opt-in — for the voice UX)
By default `/prompt` blocks ~15–60 s and returns the final result. To avoid dead air, a caller can
opt into fast-ack: get an immediate spoken "on it", with the result delivered when it's ready.

Trigger it by adding a `callback` URL (recommended) and/or `async: true`:
```json
{ "prompt": "a spinning red heart", "source": "voice",
  "callback": "http://<bridge-host>:<port>/panel_done" }
```
Immediate response (`202`) — speak `message` right away:
```json
{ "ok": true, "async": true, "job": "3f9a1c2b", "message": "On it — making that now." }
```
When generation finishes, the server POSTs the final result to `callback` (speak this `message` too):
```json
{ "job": "3f9a1c2b", "ok": true, "message": "Done — it's on the panel (1 attempt).",
  "pushed": true, "attempts": 1 }
```
If your bridge can't receive a callback, poll instead:
```
GET /status/<job>  ->  {"ok":true,"status":"running","message":"Still working on it…"}
                       {"ok":true,"status":"done","message":"Done — …","pushed":true,"attempts":1}
                       404 if the job is unknown
```
Jobs are in-memory and ephemeral (lost on a service restart) — fine for fire-and-speak voice.
**Sync callers (no `callback`/`async`) are unchanged.**

## Timing (plan for it)
One call runs: Sonnet writes a generator → sandboxed render → validate→repair (≤3) → **Bluetooth
upload**. Expect **~15–60 s** end to end (the BLE push of a ~90 KB GIF is the long pole). Use a long
client timeout (≥120 s). A good UX: speak an interim "working on it…" immediately, then speak
`message` when the POST returns.

## Library endpoints (saved assets — the chooser + save half)
Same host/port as `/prompt`.
- `GET  /library` → `{"names": [...]}` — list saved assets.
- `POST /show`  `{"name": "surprise_1", "mode": "now|store"?, "dwell"?, "panel"?}` → push a saved
  asset; bare `{}`/no name returns the list. `→ {"ok", "message"}`.
- `POST /save`  `{"name": "gold_star"}` → promote the **last generated** GIF into the library.
  `→ {"ok", "message", "name"}` (409 if nothing generated yet).

Bot commands wired to these: **`/panel <desc>`** (generate; if `<desc>` is a saved name, shows it),
**`/show <name>`** (chooser; bare `/show` lists), **`/save <name>`**, **`/list`**.

## Deployment topology
```
ESP32 --WS/Opus--> voice-bridge (your piece; ASR) --POST /prompt--> core @ CT150:8090
                                                                       │ (has ANTHROPIC_API_KEY)
                                                                       ▼ POST /push
                                                              idm-panel-api @ bt.local:8080 --BLE--> panel
```
- The **voice-bridge does not need the Anthropic key** — it only reaches `/prompt`. Run it wherever
  (Pi / OptiPlex / CT150).
- `core` + `signal_bot` + `http_prompt` all run on **CT150** (env `ANTHROPIC_API_KEY`, and
  `IDM_API_URL=http://bt.local:8080` so it can reach the panel driver).

## Test it against the stub (before the ASR half exists)
```bash
curl -s -X POST http://10.10.2.9:8090/prompt \
  -H 'content-type: application/json' \
  -d '{"prompt":"a spinning red heart","source":"voice"}'
```
(Returns a real result once the core has `ANTHROPIC_API_KEY` + can reach `idm-panel-api`.)
