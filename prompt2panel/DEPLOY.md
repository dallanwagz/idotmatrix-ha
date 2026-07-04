# Deploy — prompt2panel on CT150 (as deployed)

The **brain** (generation + `/prompt`) runs on **CT150 = `claude-chat-bot` = `10.10.2.9`**, next to
the existing Signal/Telegram bot. It POSTs finished GIFs to the **hands** (the `idm-panel-api`
container on the Pi at `bt.local:8080`). Signal comes in through the *existing* bot via a `/panel`
command — no separate Signal bot.

```
Signal ─▶ claude-chat-bot (/panel cmd) ─┐
Voice-bridge ──────────────────────────┼─▶ prompt2panel /prompt @ CT150:8090
                                        │      (Sonnet → render → validate/repair)
                                        └─────────────▶ POST /push @ bt.local:8080 ─BLE─▶ panel
```

## What's installed on CT150
1. **mDNS + tools** so CT150 resolves the Pi:
   ```bash
   apt-get install -y libnss-mdns curl git
   curl -s http://bt.local:8080/health      # sanity: reaches the panel API
   ```
2. **Repo + venv:**
   ```bash
   git clone https://github.com/dallanwagz/idotmatrix-ha.git /opt/idotmatrix-ha
   python3 -m venv /opt/prompt2panel-venv
   /opt/prompt2panel-venv/bin/pip install -r /opt/idotmatrix-ha/prompt2panel/requirements.txt
   ```
3. **Env** — `/etc/prompt2panel.env` (chmod 600). The Anthropic key is copied from the bot's `.env`
   (single source; not duplicated by hand):
   ```bash
   grep '^ANTHROPIC_API_KEY=' /opt/claude-chat-bot/.env > /etc/prompt2panel.env
   cat >> /etc/prompt2panel.env <<'ENV'
   IDM_API_URL=http://bt.local:8080
   IDM_PANEL=big
   P2P_MODEL=claude-sonnet-4-6
   P2P_PROMPT_PORT=8090
   P2P_WORK_DIR=/opt/prompt2panel-out
   P2P_MAX_REPAIR=3
   ENV
   chmod 600 /etc/prompt2panel.env
   ```
4. **Service** — `/etc/systemd/system/prompt2panel.service` (enabled; survives reboot):
   ```ini
   [Unit]
   Description=prompt2panel /prompt service (describe -> GIF -> panel)
   After=network-online.target
   Wants=network-online.target
   [Service]
   Type=simple
   WorkingDirectory=/opt/idotmatrix-ha/prompt2panel
   EnvironmentFile=/etc/prompt2panel.env
   ExecStart=/opt/prompt2panel-venv/bin/python interfaces/http_prompt.py
   Restart=on-failure
   RestartSec=5
   [Install]
   WantedBy=multi-user.target
   ```
   ```bash
   systemctl enable --now prompt2panel.service
   curl -s http://127.0.0.1:8090/health      # {"status":"ok"}
   ```
5. **Signal integration** — a `/panel <description>` command was added to the existing bot
   (`dallanwagz/claude-chat-bot`, `core/router.py`, handled async in `respond()`), which POSTs to
   `http://127.0.0.1:8090/prompt`. Shipped in that repo's PR #1.

## Use it
- **Signal:** text the bot `/panel a red guitar sliding across black`.
- **Voice-bridge / any client:** `POST http://10.10.2.9:8090/prompt` (see [CONTRACT.md](CONTRACT.md)).
- **Direct test:**
  ```bash
  curl -s -X POST http://10.10.2.9:8090/prompt -H 'content-type: application/json' \
       -d '{"prompt":"a spinning gold star","source":"test"}'
  ```

## Update / operate
```bash
# on CT150 (needs a git credential for the private-less pull, or re-clone):
cd /opt/idotmatrix-ha && git pull && systemctl restart prompt2panel.service
journalctl -u prompt2panel.service -n 50      # logs
systemctl restart claude-chat-bot.service      # after any bot change
```
Notes: model is `claude-sonnet-4-6` (matches the bot's working model; bump `P2P_MODEL` to try
another). Generation reuses the bot's Anthropic credits. Pushes serialize on the panel's single BLE
link and auto-retry.
