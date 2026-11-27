import QtQuick

// Ein Fenster in der Glimra Shell. Entweder eine interne Glimra-App (content)
// oder ein echtes Programm (xdgSurface/toplevel vom Wayland-Compositor).
Rectangle {
    id: win
    property string title: "Fenster"
    property string icon: "windowsapp"
    property string appId: ""
    property Component content: null
    property var xdgSurface: null
    property var toplevel: null
    readonly property bool isClient: xdgSurface !== null
    property bool active: false
    property bool minimized: false
    property bool maximized: false
    property rect restoreRect: Qt.rect(0, 0, 0, 0)
    property string snapped: ""      // "", "left", "right", "max"
    property string snapHint: ""     // Vorschau beim Ziehen an den Rand
    readonly property int titleH: 38

    signal requestFocus()
    signal closed()
    signal menuRequested(real mx, real my)

    visible: !minimized
    radius: maximized ? 0 : Theme.radius
    color: Theme.windowBg
    border.color: active ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.7) : Theme.border
    border.width: 1
    clip: true

    width: 760
    height: 520
    Binding on width {
        when: win.isClient && clientLoader.item !== null
        value: clientLoader.item ? clientLoader.item.width + 2 : 0
    }
    Binding on height {
        when: win.isClient && clientLoader.item !== null
        value: clientLoader.item ? clientLoader.item.height + win.titleH + 1 : 0
    }

    function close() {
        if (isClient && toplevel) toplevel.sendClose()
        else destroyWindow()
    }
    function destroyWindow() {
        closed()
        win.destroy()
    }
    function toggleMaximize() { snapTo(maximized ? "restore" : "max") }

    // Andocken wie bei Windows: links, rechts, maximiert oder zurück
    function snapTo(side) {
        const area = win.parent
        if (side === "restore") {
            if (!snapped) return
            x = restoreRect.x; y = restoreRect.y
            if (isClient) toplevel.sendUnmaximized(Qt.size(restoreRect.width - 2, restoreRect.height - titleH - 1))
            else { width = restoreRect.width; height = restoreRect.height }
            snapped = ""; maximized = false
            return
        }
        if (!snapped) restoreRect = Qt.rect(x, y, width, height)
        const w = side === "max" ? area.width : Math.floor(area.width / 2)
        x = side === "right" ? area.width - w : 0
        y = 0
        if (isClient) {
            if (side === "max") toplevel.sendMaximized(Qt.size(w - 2, area.height - titleH - 1))
            else toplevel.sendConfigure(Qt.size(w - 2, area.height - titleH - 1), [])
        } else { width = w; height = area.height }
        snapped = side
        maximized = side === "max"
    }
    function resizeTo(w, h) {
        w = Math.max(320, w); h = Math.max(200, h)
        if (isClient) toplevel.sendConfigure(Qt.size(w - 2, h - titleH - 1), [])
        else { width = w; height = h }
    }

    // Klick irgendwo ins Fenster holt es nach vorne
    MouseArea {
        anchors.fill: parent
        z: -1
        onPressed: (mouse) => { win.requestFocus(); mouse.accepted = false }
    }

    // ---------------- Titelleiste
    Rectangle {
        id: titleBar
        width: parent.width
        height: win.titleH
        color: Theme.titleBg
        radius: win.radius
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: win.radius; color: parent.color }

        Row {
            x: 14
            anchors.verticalCenter: parent.verticalCenter
            spacing: 10
            Icon { name: win.icon; size: 16; anchors.verticalCenter: parent.verticalCenter; opacity: win.active ? 1 : 0.6 }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: win.title
                color: win.active ? Theme.text : Theme.textDim
                font.pixelSize: 13
                font.family: Theme.fontFamily
                font.weight: Font.DemiBold
                elide: Text.ElideRight
                width: win.width - 170
            }
        }

        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            property point start
            onPressed: (mouse) => {
                win.requestFocus()
                start = Qt.point(mouse.x, mouse.y)
                if (mouse.button === Qt.RightButton) win.menuRequested(mouse.x, mouse.y)
            }
            onPositionChanged: (mouse) => {
                if (!(pressedButtons & Qt.LeftButton)) return
                if (win.snapped) {
                    // aus dem angedockten Zustand herausziehen
                    const ratio = mouse.x / win.width
                    win.snapTo("restore")
                    start = Qt.point(win.width * ratio, mouse.y)
                }
                win.x += mouse.x - start.x
                win.y = Math.max(0, win.y + mouse.y - start.y)
                const p = mapToItem(win.parent, mouse.x, mouse.y)
                win.snapHint = p.y <= 4 ? "max" : p.x <= 4 ? "left" : p.x >= win.parent.width - 4 ? "right" : ""
            }
            onReleased: {
                if (win.snapHint) { win.snapTo(win.snapHint); win.snapHint = "" }
            }
            onDoubleClicked: (mouse) => { if (mouse.button === Qt.LeftButton) win.toggleMaximize() }
        }

        Row {
            anchors.right: parent.right
            anchors.rightMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            spacing: 6
            Repeater {
                model: [
                    { sym: "minimize", act: "min" },
                    { sym: win.maximized ? "restore" : "maximize", act: "max" },
                    { sym: "close", act: "close" }
                ]
                delegate: Rectangle {
                    required property var modelData
                    width: 30; height: 24; radius: 6
                    color: bma.containsMouse ? (modelData.act === "close" ? Theme.danger : Theme.hover) : "transparent"
                    Icon { anchors.centerIn: parent; name: modelData.sym; size: 14 }
                    MouseArea {
                        id: bma
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: {
                            if (modelData.act === "min") win.minimized = true
                            else if (modelData.act === "max") win.toggleMaximize()
                            else win.close()
                        }
                    }
                }
            }
        }
    }

    // ---------------- Inhalt
    Loader {
        id: contentLoader
        active: !win.isClient
        x: 1; y: win.titleH
        width: win.width - 2
        height: win.height - win.titleH - 1
        sourceComponent: win.content
    }

    Loader {
        id: clientLoader
        x: 1; y: win.titleH
        Component.onCompleted: {
            if (win.isClient)
                setSource(Qt.resolvedUrl("../ClientSurface.qml"), { shellSurface: win.xdgSurface })
        }
        Connections {
            target: clientLoader.item
            ignoreUnknownSignals: true
            function onSurfaceGone() { win.destroyWindow() }
            function onFocused() { win.requestFocus() }
        }
    }

    Connections {
        target: win.toplevel
        ignoreUnknownSignals: true
        function onTitleChanged() { if (win.toplevel.title) win.title = win.toplevel.title }
    }

    // ---------------- Größe ändern (Ecke unten rechts)
    MouseArea {
        visible: !win.snapped
        width: 18; height: 18
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        cursorShape: Qt.SizeFDiagCursor
        property point start
        property size startSize
        onPressed: (mouse) => {
            start = mapToItem(win.parent, mouse.x, mouse.y)
            startSize = Qt.size(win.width, win.height)
        }
        onPositionChanged: (mouse) => {
            if (!pressed) return
            const p = mapToItem(win.parent, mouse.x, mouse.y)
            win.resizeTo(startSize.width + p.x - start.x, startSize.height + p.y - start.y)
        }
    }
}
