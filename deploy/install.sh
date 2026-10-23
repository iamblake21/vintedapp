#!/usr/bin/env bash
# Install vinted-alerts as a systemd service on a Debian/Ubuntu VPS.
# Usage (from the repository folder):  sudo bash deploy/install.sh
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE=vinted-alerts
RUN_USER="${SUDO_USER:-$(whoami)}"

if [[ $EUID -ne 0 ]]; then
  echo "Esegui con sudo: sudo bash deploy/install.sh" >&2
  exit 1
fi

echo "==> Installo Python"
if command -v apt-get >/dev/null; then
  apt-get update -qq
  apt-get install -y -qq python3 python3-venv python3-pip >/dev/null
fi
python3 -c 'import sys; assert sys.version_info >= (3, 10), "Serve Python 3.10+"'

echo "==> Creo l'ambiente virtuale in $APP_DIR/.venv"
sudo -u "$RUN_USER" python3 -m venv "$APP_DIR/.venv"
sudo -u "$RUN_USER" "$APP_DIR/.venv/bin/pip" install -q --upgrade pip
sudo -u "$RUN_USER" "$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

if [[ ! -f "$APP_DIR/config.toml" ]]; then
  sudo -u "$RUN_USER" cp "$APP_DIR/config.example.toml" "$APP_DIR/config.toml"
  echo "==> Creato config.toml dall'esempio: modificalo con le tue ricerche e il bot Telegram"
fi

echo "==> Installo il servizio systemd '$SERVICE' (utente $RUN_USER)"
cat > /etc/systemd/system/$SERVICE.service <<UNIT
[Unit]
Description=Vinted price alerts
After=network-online.target
Wants=network-online.target

[Service]
User=$RUN_USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/python -m vinted_alerts run -c $APP_DIR/config.toml
Restart=always
RestartSec=30
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable $SERVICE >/dev/null

cat <<MSG

Fatto. Prossimi passi:
  1. nano $APP_DIR/config.toml               # ricerche + [telegram]
  2. $APP_DIR/.venv/bin/python -m vinted_alerts test-notify -c $APP_DIR/config.toml
  3. sudo systemctl restart $SERVICE         # avvia (o riavvia dopo ogni modifica)
  4. journalctl -u $SERVICE -f               # guarda i log (Ctrl+C per uscire)
MSG
