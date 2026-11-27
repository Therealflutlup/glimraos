import QtQuick
import QtWayland.Compositor

// Zeigt das Fenster eines echten Programms (Wayland-Client) an.
ShellSurfaceItem {
    id: item
    signal surfaceGone()
    signal focused()
    autoCreatePopupItems: true
    onSurfaceDestroyed: item.surfaceGone()
    onActiveFocusChanged: if (activeFocus) item.focused()
}
