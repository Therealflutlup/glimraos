# shellcheck shell=sh
# Beim ersten Start den Server-Assistenten zeigen, danach nur den Status.
if [ "$(tty)" = "/dev/tty1" ] && [ -z "$SSH_TTY" ]; then
    if [ ! -f /etc/glimra/panel.json ] && [ "$(id -u)" = "0" ]; then
        /usr/local/bin/glimra-server-setup
    else
        /usr/local/bin/glimra-server-status
    fi
fi
