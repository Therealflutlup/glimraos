#!/usr/bin/env bash
# Baut eine Glimra-OS-ISO.
#   sudo ./build.sh desktop
#   sudo ./build.sh server
# Läuft auf Arch Linux oder im Docker-Container "archlinux" (so macht es GitHub Actions).
set -euo pipefail

EDITION=${1:-desktop}
case $EDITION in desktop|server) ;; *) echo "Nutzung: $0 desktop|server" >&2; exit 1 ;; esac

ROOT=$(cd "$(dirname "$0")" && pwd)
VERSION=$(cat "$ROOT/VERSION")
WORK=${WORK:-$ROOT/work/$EDITION}
OUT=${OUT:-$ROOT/out}
P=$WORK/profile

[[ $EUID -eq 0 ]] || { echo "Bitte als root ausführen (sudo ./build.sh $EDITION)." >&2; exit 1; }
command -v mkarchiso >/dev/null || pacman -S --noconfirm --needed archiso

echo "==> Glimra OS $VERSION ($EDITION) wird gebaut"
rm -rf "$WORK"
mkdir -p "$WORK" "$OUT"

# 1. Arch-"releng"-Profil als Grundlage (Bootloader, Kernel, Live-System)
cp -r /usr/share/archiso/configs/releng "$P"

# 2. Glimra-OS-Dateien darüberlegen
cp -a "$ROOT/profiles/common/airootfs/." "$P/airootfs/"
cp -a "$ROOT/profiles/$EDITION/airootfs/." "$P/airootfs/"
mkdir -p "$P/airootfs/usr/lib/glimra" "$P/airootfs/etc/glimra"
cp -r "$ROOT/shell/glimra_shell" "$ROOT/panel/glimra_panel" "$P/airootfs/usr/lib/glimra/"
find "$P/airootfs/usr/lib/glimra" -name __pycache__ -prune -exec rm -rf {} +

# 3. Paketliste
grep -hv '^\s*#' "$ROOT/profiles/common/packages.extra" "$ROOT/profiles/$EDITION/packages.extra" \
    | sed '/^\s*$/d' > "$P/airootfs/etc/glimra/packages.list"
cat "$P/airootfs/etc/glimra/packages.list" >> "$P/packages.x86_64"
sort -u -o "$P/packages.x86_64" "$P/packages.x86_64"
echo "$EDITION" > "$P/airootfs/etc/glimra/edition"
echo "$VERSION" > "$P/airootfs/etc/glimra/version"
CODENAME=$(sed -n 's/^CODENAME = "\(.*\)"/\1/p' "$ROOT/shell/glimra_shell/__init__.py")
sed -i -e "s/@VERSION@/$VERSION/g" -e "s/@CODENAME@/$CODENAME/g" \
       -e "s/@CODENAME_LC@/$(echo "$CODENAME" | tr '[:upper:]' '[:lower:]')/g" "$P/airootfs/etc/os-release"
echo "glimra-$EDITION" > "$P/airootfs/etc/hostname"

# multilib-Paketquelle (für Steam und Wine)
sed -i '/^#\[multilib\]/{N;s/#//g}' "$P/pacman.conf"

# 4. Name, Version, Bootmenü
LABEL="GLIMRAOS_$(echo "$EDITION" | tr '[:lower:]' '[:upper:]')"
sed -i \
    -e "s|^iso_name=.*|iso_name=\"glimraos-$EDITION\"|" \
    -e "s|^iso_label=.*|iso_label=\"$LABEL\"|" \
    -e "s|^iso_publisher=.*|iso_publisher=\"Glimra OS\"|" \
    -e "s|^iso_application=.*|iso_application=\"Glimra OS $EDITION\"|" \
    -e "s|^iso_version=.*|iso_version=\"$VERSION\"|" \
    "$P/profiledef.sh"
TITLE="Glimra OS $(echo "${EDITION:0:1}" | tr '[:lower:]' '[:upper:]')${EDITION:1}"
find "$P/grub" "$P/efiboot" "$P/syslinux" -type f \( -name '*.cfg' -o -name '*.conf' \) \
    -exec sed -i -e "s/Arch Linux install medium/$TITLE/g" -e "s/Arch Linux/Glimra OS/g" {} +

# Dateirechte für Glimra-OS-Programme
PERMS=""
while IFS= read -r f; do PERMS+="  [\"/$f\"]=\"0:0:755\"\n"; done \
    < <(cd "$P/airootfs" && find usr/local/bin -type f -name 'glimra-*')
PERMS+="  [\"/etc/sudoers.d/20-glimra\"]=\"0:0:440\"\n"
sed -i "/^file_permissions=(/a\\
$(printf '%b' "$PERMS" | sed 's/$/\\/' | sed '$ s/\\$//')" "$P/profiledef.sh"

# 5. Dienste im Live-System
# Das releng-Profil nutzt iwd + systemd-networkd. Die Glimra Shell steuert WLAN, Flugmodus und
# Verbindungen über NetworkManager – also wie im installierten System NetworkManager starten.
W="$P/airootfs/etc/systemd/system"
rm -f "$W/multi-user.target.wants/iwd.service" \
      "$W/multi-user.target.wants/systemd-networkd.service" \
      "$W/sockets.target.wants/systemd-networkd.socket" \
      "$W/network-online.target.wants/systemd-networkd-wait-online.service" \
      "$W/systemd-networkd-wait-online.service.d/"*.conf 2>/dev/null || true
mkdir -p "$W/multi-user.target.wants" "$W/network-online.target.wants"
ln -sf /usr/lib/systemd/system/NetworkManager.service "$W/multi-user.target.wants/NetworkManager.service"
ln -sf /usr/lib/systemd/system/NetworkManager-wait-online.service \
    "$W/network-online.target.wants/NetworkManager-wait-online.service"
ln -sf /usr/lib/systemd/system/NetworkManager-dispatcher.service "$W/dbus-org.freedesktop.nm-dispatcher.service"
if [[ $EDITION == desktop ]]; then
    ln -sf /usr/lib/systemd/system/bluetooth.service "$W/multi-user.target.wants/bluetooth.service"
fi
if [[ $EDITION == server ]]; then
    mkdir -p "$P/airootfs/etc/systemd/system/multi-user.target.wants"
    ln -sf /etc/systemd/system/glimra-panel.service \
        "$P/airootfs/etc/systemd/system/multi-user.target.wants/glimra-panel.service"
fi

# 6. ISO bauen
mkarchiso -v -r -w "$WORK/tmp" -o "$OUT" "$P"
echo "==> Fertig: $(ls -1 "$OUT"/glimraos-"$EDITION"-*.iso | tail -1)"
