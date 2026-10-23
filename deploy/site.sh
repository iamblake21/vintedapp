#!/usr/bin/env bash
# Runs ON the VPS (piped over SSH by .github/workflows/deploy-site.yml).
# Publishes the static site from /tmp/blakecards-site with nginx, and gets a
# Let's Encrypt certificate once the domain's DNS points at this server.
set -euo pipefail
SRC=/tmp/blakecards-site
ROOT=/var/www/blakecards
DOMAIN=blakecards.it
NAMES=("$DOMAIN" "www.$DOMAIN")
CONF=/etc/nginx/sites-available/blakecards
CERT=/etc/letsencrypt/live/$DOMAIN

echo "==> Server: $(. /etc/os-release && echo "$PRETTY_NAME")"

if ! command -v nginx >/dev/null; then
  # Don't fight another web server already holding port 80.
  if ss -ltnH '( sport = :80 )' | grep -q .; then
    echo "!! La porta 80 è già usata da un altro programma:" >&2
    ss -ltnp '( sport = :80 )' >&2
    exit 1
  fi
  echo "==> Installo nginx e certbot"
  apt-get update -qq
  apt-get install -y -qq nginx certbot >/dev/null
  rm -f /etc/nginx/sites-enabled/default
fi
for pkg in certbot curl; do command -v $pkg >/dev/null || apt-get install -y -qq $pkg >/dev/null; done

if command -v ufw >/dev/null && ufw status | grep -q 'Status: active'; then
  ufw allow 80/tcp >/dev/null && ufw allow 443/tcp >/dev/null
fi

echo "==> Copio i file del sito in $ROOT"
mkdir -p "$ROOT"
rm -rf "$ROOT.new" && cp -r "$SRC" "$ROOT.new"
rm -f "$ROOT.new/README.md" "$ROOT.new/_headers"
mkdir -p "$ROOT.new/.well-known/acme-challenge"
chmod -R a+rX "$ROOT.new"
rm -rf "$ROOT.old" && mv "$ROOT" "$ROOT.old" && mv "$ROOT.new" "$ROOT" && rm -rf "$ROOT.old"
rm -rf "$SRC"

HEADERS='
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header X-Frame-Options "DENY" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), interest-cohort=()" always;
    add_header Content-Security-Policy "default-src '"'"'self'"'"'; img-src '"'"'self'"'"' data:; style-src '"'"'self'"'"'; script-src '"'"'none'"'"'; frame-ancestors '"'"'none'"'"'; base-uri '"'"'self'"'"'; form-action '"'"'none'"'"'" always;'
SITE="
    root $ROOT;
    index index.html;
    error_page 404 /404.html;
    server_tokens off;
    charset utf-8;
$HEADERS
    location / { try_files \$uri \$uri/ =404; }
    location /assets/ { expires 7d; }"
# Listen on IPv6 only where the server has it, or nginx refuses to start.
V6=""; [[ -s /proc/net/if_inet6 ]] && V6=1
l6() { [[ -n $V6 ]] && echo "    listen [::]:$1;"; return 0; }
ACME="
    location /.well-known/acme-challenge/ { root $ROOT; }"

write_http_only() {
  cat > "$CONF" <<NGINX
server {
    listen 80;
$(l6 80)
    server_name ${NAMES[*]};
$ACME
$SITE
}
NGINX
}

write_https() {
  cat > "$CONF" <<NGINX
server {
    listen 80;
$(l6 80)
    server_name ${NAMES[*]};
$ACME
    location / { return 301 https://www.$DOMAIN\$request_uri; }
}
server {
    listen 443 ssl;
$(l6 "443 ssl")
    http2 on;
    server_name $DOMAIN;
    ssl_certificate $CERT/fullchain.pem;
    ssl_certificate_key $CERT/privkey.pem;
    return 301 https://www.$DOMAIN\$request_uri;
}
server {
    listen 443 ssl;
$(l6 "443 ssl")
    http2 on;
    server_name www.$DOMAIN;
    ssl_certificate $CERT/fullchain.pem;
    ssl_certificate_key $CERT/privkey.pem;
    add_header Strict-Transport-Security "max-age=31536000" always;
$SITE
}
NGINX
  # "http2 on" needs nginx >= 1.25.1; older ones take it on the listen line.
  if ! nginx -t 2>/dev/null; then
    sed -i -e '/http2 on;/d' -e 's/\(listen .*443 ssl\);/\1 http2;/' "$CONF"
  fi
}

reload() {
  ln -sf "$CONF" /etc/nginx/sites-enabled/blakecards
  nginx -t
  systemctl enable --now nginx >/dev/null
  systemctl reload nginx
}

if [[ -d $CERT ]]; then
  write_https
else
  write_http_only
fi
reload

if [[ ! -d $CERT ]]; then
  MY_IP=$(curl -4 -fsS --max-time 10 https://api.ipify.org || true)
  echo "==> IP pubblico del server: ${MY_IP:-sconosciuto}"
  ready=1
  for n in "${NAMES[@]}"; do
    ips=$(getent ahostsv4 "$n" | awk '{print $1}' | sort -u | tr '\n' ' ')
    echo "    $n -> ${ips:-nessun record}"
    [[ -n $MY_IP && " $ips " == *" $MY_IP "* ]] || ready=0
  done
  if [[ $ready == 1 ]]; then
    echo "==> DNS pronto: chiedo il certificato HTTPS a Let's Encrypt"
    certbot certonly --webroot -w "$ROOT" -d "$DOMAIN" -d "www.$DOMAIN" \
      --non-interactive --agree-tos --register-unsafely-without-email \
      --deploy-hook "systemctl reload nginx"
    write_https
    reload
  else
    echo "==> HTTPS non ancora attivo: su Register.it crea due record A (@ e www) verso ${MY_IP:-IP della VPS},"
    echo "    aspetta la propagazione e rilancia questo deploy."
  fi
fi

echo "==> Fatto. nginx: $(systemctl is-active nginx), HTTPS: $([[ -d $CERT ]] && echo attivo || echo 'non ancora')"
echo "==> Bot Vinted: $(systemctl is-active vinted-alerts 2>/dev/null || echo 'non installato')"
