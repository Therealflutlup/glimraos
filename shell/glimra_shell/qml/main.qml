import QtQuick
import QtQuick.Window
import QtWayland.Compositor
import QtWayland.Compositor.XdgShell
import Glimra

// Glimra Shell als Wayland-Compositor: Programme öffnen ihre Fenster hier drin.
WaylandCompositor {
    id: compositor
    socketName: "wayland-glimra"

    WaylandOutput {
        id: output
        sizeFollowsWindow: true
        window: Window {
            id: screen
            width: 1280
            height: 800
            visible: true
            visibility: Window.FullScreen
            color: Theme.bg
            title: "Glimra Shell"

            Shell { id: shell }
        }
    }

    XdgShell {
        onToplevelCreated: (toplevel, xdgSurface) => shell.addClient(toplevel, xdgSurface)
    }

    // Programme sollen keine eigenen Titelleisten zeichnen – das macht Glimra
    XdgDecorationManagerV1 {
        preferredMode: XdgToplevel.ServerSideDecoration
    }

    Component.onCompleted: {
        compositor.retainedSelection = true      // Zwischenablage bleibt erhalten
        compositor.defaultSeat.keymap.layout = "de"  // deutsche Tastatur für Programme
    }
}
