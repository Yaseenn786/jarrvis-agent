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
    dnf install -y python3.11 python3.11-pip tar >/dev/null 2>&1 \
        || dnf install -y python3 python3-pip tar >/dev/null 2>&1 || true
elif command -v apt-get >/dev/null 2>&1; then
    apt-get update -qq >/dev/null 2>&1 || true
    apt-get install -y python3 python3-venv python3-pip tar >/dev/null 2>&1 || true
fi

PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3; do
    command -v "$c" >/dev/null 2>&1 || continue
    if "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
        PY="$c"
        break
    fi
done

[ -n "$PY" ] || fail "python 3.10+ required, none found"
say "using $($PY --version 2>&1)"

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

"$PY" -m venv "$INSTALL_DIR/venv" 2>/dev/null || fail "could not create venv"
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

# ---- cli wrapper -----------------------------------------------------------
cat > /usr/local/bin/jarrvis <<EOF
#!/bin/sh
[ "\$(id -u)" = "0" ] || exec sudo "\$0" "\$@"

export JARRVIS_CONFIG="$CONFIG_DIR/jarrvis.yml"
export JARRVIS_KEY_PATH="$CONFIG_DIR/.jarrvis_key"
export JARRVIS_HUB_URL="$HUB_URL"
cd "$INSTALL_DIR/agent" || exit 1

case "\$1" in
  pair)    exec "$INSTALL_DIR/venv/bin/python3" pair.py "\$2" ;;
  update)
    echo "  fetching latest agent..."
    TMP="\$(mktemp -d)"
    trap 'rm -rf "\$TMP"' EXIT
    curl -sSL "$REPO" -o "\$TMP/agent.tar.gz" || { echo "  download failed"; exit 1; }
    tar -xzf "\$TMP/agent.tar.gz" -C "\$TMP" || { echo "  extract failed"; exit 1; }
    SRC="\$(find "\$TMP" -maxdepth 1 -type d -name 'jarrvis-agent-*' | head -1)"
    [ -n "\$SRC" ] || { echo "  bad archive"; exit 1; }
    find "$INSTALL_DIR" -mindepth 1 -maxdepth 1 ! -name venv -exec rm -rf {} +
    cp -r "\$SRC"/. "$INSTALL_DIR"/
    "$INSTALL_DIR/venv/bin/pip" install -q -r "$INSTALL_DIR/requirements.txt" || { echo "  pip failed"; exit 1; }
    systemctl restart jarrvis
    echo "  updated — running latest"
    ;;
  status)  exec systemctl status jarrvis ;;
  logs)    exec journalctl -u jarrvis -f ;;
  restart) exec systemctl restart jarrvis ;;
  *) echo "usage: jarrvis {pair <code>|update|status|logs|restart}"; exit 1 ;;
esac
EOF
chmod +x /usr/local/bin/jarrvis

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
echo "  logs:    jarrvis logs"
echo "  restart: jarrvis restart"
echo "  update:  jarrvis update"
echo ""