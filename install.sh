#!/bin/sh
set -e

REPO="https://github.com/Yaseenn786/jarrvis-agent/archive/refs/heads/main.tar.gz"
HUB_URL="${JARRVIS_HUB_URL:-https://api.jarrviss.com}"
INSTALL_DIR="/opt/jarrvis"
CONFIG_DIR="/etc/jarrvis"
CODE="$1"

say()  { echo "  $*"; }
fail() { echo "error: $*" >&2; exit 1; }

# ---- checks ----------------------------------------------------------------
[ "$(id -u)" = "0" ] || fail "run with sudo"
[ -n "$CODE" ]       || fail "no pairing code. get one at https://jarrviss.com/pair"
[ "$(uname -s)" = "Linux" ] || fail "Linux only for now (found $(uname -s))"

echo ""
echo "  jarrviss installer"
echo ""

# ---- dependencies ----------------------------------------------------------
say "checking dependencies..."

if command -v dnf >/dev/null 2>&1; then
    dnf install -y python3 python3-pip tar >/dev/null 2>&1 || true
elif command -v apt-get >/dev/null 2>&1; then
    apt-get update -qq >/dev/null 2>&1 || true
    apt-get install -y python3 python3-venv python3-pip tar >/dev/null 2>&1 || true
fi

command -v python3 >/dev/null 2>&1 || fail "python3 not found and could not be installed"

# ---- fetch agent -----------------------------------------------------------
say "downloading agent..."

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

curl -sSL "$REPO" -o "$TMP/agent.tar.gz" || fail "download failed"
tar -xzf "$TMP/agent.tar.gz" -C "$TMP" || fail "extract failed"

SRC="$(find "$TMP" -maxdepth 1 -type d -name 'jarrvis-agent-*' | head -1)"
[ -n "$SRC" ] || fail "unexpected archive layout"

rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp -r "$SRC"/. "$INSTALL_DIR"/

# ---- python env ------------------------------------------------------------
say "installing python packages..."

python3 -m venv "$INSTALL_DIR/venv" 2>/dev/null || fail "could not create venv (install python3-venv)"
"$INSTALL_DIR/venv/bin/pip" install -q --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -q -r "$INSTALL_DIR/requirements.txt" || fail "pip install failed"

# ---- config ----------------------------------------------------------------
say "writing config..."

mkdir -p "$CONFIG_DIR"
chmod 700 "$CONFIG_DIR"

SERVER_NAME="$(hostname -s 2>/dev/null || hostname)"

cat > "$CONFIG_DIR/jarrvis.yml" <<EOF
watch: []

patterns:
  - "\\\\bERROR\\\\b"
  - "\\\\bFATAL\\\\b"
  - "Exception"
  - "Traceback"

hub:
  url: $HUB_URL
  server_name: $SERVER_NAME

log_copy:
  enabled: true
  dir: /var/lib/jarrvis/logs
  max_storage_mb: 100
  retention_days: 1
EOF

mkdir -p /var/lib/jarrvis/logs

# ---- service ---------------------------------------------------------------
say "setting up service..."

cat > /etc/systemd/system/jarrvis.service <<EOF
[Unit]
Description=Jarrviss monitoring agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR/agent
Environment="JARRVIS_CONFIG=$CONFIG_DIR/jarrvis.yml"
Environment="JARRVIS_KEY_PATH=$CONFIG_DIR/.jarrvis_key"
Environment="JARRVIS_HUB_URL=$HUB_URL"
Environment="JARRVIS_SERVER_NAME=$SERVER_NAME"
ExecStart=$INSTALL_DIR/venv/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable jarrvis >/dev/null 2>&1
systemctl restart jarrvis

# ---- wait for first beat ---------------------------------------------------
say "waiting for first check-in..."

i=0
while [ $i -lt 30 ]; do
    [ -f "$CONFIG_DIR/.jarrvis_key" ] && break
    sleep 1
    i=$((i + 1))
done

[ -f "$CONFIG_DIR/.jarrvis_key" ] || fail "agent did not start — check: journalctl -u jarrvis -n 50"

sleep 3

# ---- pair ------------------------------------------------------------------
say "pairing..."

cd "$INSTALL_DIR/agent"
JARRVIS_CONFIG="$CONFIG_DIR/jarrvis.yml" \
JARRVIS_KEY_PATH="$CONFIG_DIR/.jarrvis_key" \
JARRVIS_HUB_URL="$HUB_URL" \
"$INSTALL_DIR/venv/bin/python3" pair.py "$CODE" || fail "pairing failed — code may have expired"

echo ""
echo "  done — $SERVER_NAME is connected"
echo "  your dashboard should have opened already"
echo ""
echo "  logs:    journalctl -u jarrvis -f"
echo "  restart: systemctl restart jarrvis"
echo ""