#!/data/data/com.termux/files/usr/bin/bash
set -eu
pkg install -y python termux-api
mkdir -p "$HOME/.switchsnitch" "$PREFIX/bin"
chmod +x termux/decision.sh termux/install.sh termux/bridge.py
cat > "$PREFIX/bin/snitch" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
set -eu
cd "$HOME/Lokivellis-chatgpt-switchsnitch"
exec python termux/bridge.py
EOF
chmod +x "$PREFIX/bin/snitch"
echo "SwitchSnitch installed. Start anywhere with: snitch"
