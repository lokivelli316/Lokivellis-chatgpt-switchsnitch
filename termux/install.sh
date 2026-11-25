#!/data/data/com.termux/files/usr/bin/bash
set -eu
pkg install -y python termux-api
mkdir -p "$HOME/.switchsnitch" "$PREFIX/bin"
chmod 700 "$HOME/.switchsnitch"
chmod +x termux/decision.sh termux/token.sh termux/install.sh termux/bridge.py
cat > "$PREFIX/bin/snitch" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
set -eu
cd "$HOME/Lokivellis-chatgpt-switchsnitch"
exec python termux/bridge.py
EOF
cat > "$PREFIX/bin/snitch-token" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
set -eu
cd "$HOME/Lokivellis-chatgpt-switchsnitch"
exec bash termux/token.sh
EOF
chmod +x "$PREFIX/bin/snitch" "$PREFIX/bin/snitch-token"
echo "SwitchSnitch installed. Start: snitch"
echo "Manual extension provisioning: snitch-token"
