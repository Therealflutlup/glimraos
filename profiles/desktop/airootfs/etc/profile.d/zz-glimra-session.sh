# shellcheck shell=sh
# Startet die Glimra Shell automatisch nach der Anmeldung auf tty1.
if [ "$(tty)" = "/dev/tty1" ] && [ -z "$SSH_TTY" ] && [ -z "$WAYLAND_DISPLAY" ] && [ -z "$GLIMRA_NO_SHELL" ]; then
    /usr/local/bin/glimra-session
fi
