#!/usr/bin/env bash
# Runs ON the VPS (piped over SSH by .github/workflows/deploy.yml).
# Installs/updates vinted-alerts, wires Telegram, restarts the service.
set -euo pipefail
APP_DIR=/opt/vintedapp
REPO=https://github.com/iamblake21/vintedapp.git

echo "==> Server: $(. /etc/os-release && echo "$PRETTY_NAME"), RAM disponibile: $(free -m | awk '/Mem:/ {print $7}') MB"

if ! command -v git >/dev/null; then
  apt-get update -qq && apt-get install -y -qq git >/dev/null
fi
if [[ -d $APP_DIR/.git ]]; then
  git -C "$APP_DIR" pull -q --ff-only
else
  git clone -q "$REPO" "$APP_DIR"
fi
cd "$APP_DIR"
bash deploy/install.sh

# Searches come from the repo; keep the server-only [telegram] section (with the token).
if [[ -f deploy/config.toml ]]; then
  TELEGRAM_SECTION=$(sed -n '/^\[telegram\]/,$p' config.toml)
  cp deploy/config.toml config.toml
  [[ -n "$TELEGRAM_SECTION" ]] && printf '\n%s\n' "$TELEGRAM_SECTION" >> config.toml
  echo "==> Ricerche aggiornate: $(grep -c '^\[\[watch\]\]' config.toml)"
fi

TELEGRAM_BOT_TOKEN=$(printf '%s' "${TELEGRAM_BOT_TOKEN:-}" | tr -d '[:space:]')
export TELEGRAM_BOT_TOKEN
if [[ -n "$TELEGRAM_BOT_TOKEN" ]] && ! grep -q '^\[telegram\]' config.toml; then
  CHAT_ID=$(.venv/bin/python - <<'PY'
import os, sys, requests
api = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN'].strip()}"
me = requests.get(f"{api}/getMe", timeout=15).json()
print("Telegram getMe:", me.get("ok"), me.get("result", {}).get("username"), me.get("description", ""),
      file=sys.stderr)
r = requests.get(f"{api}/getUpdates", timeout=15).json()
if r.get("error_code") == 409:  # a webhook is set: getUpdates is disabled until it is removed
    requests.get(f"{api}/deleteWebhook", timeout=15)
    r = requests.get(f"{api}/getUpdates", timeout=15).json()
print("Telegram getUpdates:", r.get("ok"), len(r.get("result", [])), "aggiornamenti",
      r.get("description", ""), file=sys.stderr)
chats = [u[k]["chat"]["id"] for u in r.get("result", []) for k in ("message", "my_chat_member") if k in u]
print(chats[-1] if chats else "")
PY
)
  if [[ -n "$CHAT_ID" ]]; then
    printf '\n[telegram]\nbot_token = "%s"\nchat_id = "%s"\n' "$TELEGRAM_BOT_TOKEN" "$CHAT_ID" >> config.toml
    echo "==> Telegram configurato"
  else
    echo "==> TELEGRAM: nessuna chat trovata. Apri il bot su Telegram, premi Avvia (/start) e rilancia il deploy."
  fi
fi

if grep -q '^\[telegram\]' config.toml; then
  .venv/bin/python -m vinted_alerts test-notify >/dev/null && echo "==> Notifica di prova inviata su Telegram"
fi

systemctl restart vinted-alerts
sleep 45
echo "==> Stato servizio: $(systemctl is-active vinted-alerts)"
journalctl -u vinted-alerts --no-pager -n 30 -o cat
