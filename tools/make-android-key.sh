#!/usr/bin/env bash
# Erstellt EINMAL den Signaturschlüssel für die GlimraApp und zeigt, welche GitHub-Secrets du anlegen musst.
# Den Schlüssel sicher aufbewahren: Ohne ihn lassen sich keine Updates der App mehr installieren!
set -euo pipefail
OUT=${1:-$HOME/glimraapp-release.jks}
[[ -e $OUT ]] && { echo "$OUT existiert schon – nicht überschreiben!"; exit 1; }
read -rsp "Passwort für den Schlüssel (mind. 6 Zeichen): " PW; echo
keytool -genkeypair -v -keystore "$OUT" -alias glimraapp -keyalg RSA -keysize 4096 -validity 10000 \
    -storepass "$PW" -keypass "$PW" -dname "CN=Glimra OS, O=Glimra OS, C=DE"
echo
echo "Fertig: $OUT"
echo "Jetzt in GitHub → Settings → Secrets and variables → Actions anlegen:"
echo "  ANDROID_KEYSTORE_BASE64  = Inhalt von:  base64 -w0 \"$OUT\""
echo "  ANDROID_KEYSTORE_PASSWORD = dein Passwort"
echo "Oder mit der GitHub-CLI:"
echo "  base64 -w0 \"$OUT\" | gh secret set ANDROID_KEYSTORE_BASE64"
echo "  gh secret set ANDROID_KEYSTORE_PASSWORD"
