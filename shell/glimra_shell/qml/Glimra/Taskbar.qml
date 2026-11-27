import QtQuick

Rectangle {
    id: bar
    property var windows: []
    property var activeWindow: null
    property var apps: []
    readonly property var pinned: ["files", "browser", "terminal", "assistant", "settings"]
    signal startClicked()
    signal windowClicked(var w)
    signal pinnedClicked(string id)
    signal trayClicked()
    signal clockClicked()
    signal showDesktopClicked()
    signal closeWindow(var w)
    property var battery: ({ present: false, level: 100, charging: false })

    function app(id) {
        for (let i = 0; i < apps.length; i++) if (apps[i].id === id) return apps[i]
        return { icon: "apps", colors: ["#5b8cff", "#3a5bd9"], name: id }
    }

    height: 56
    color: Theme.panel
    Rectangle { width: parent.width; height: 1; color: Theme.border }

    Rectangle {
        id: startBtn
        x: 10
        anchors.verticalCenter: parent.verticalCenter
        width: 44; height: 44; radius: 12
        color: sma.containsMouse ? Theme.hover : "transparent"
        GlimraLogo { anchors.centerIn: parent; size: 28; glow: false }
        MouseArea { id: sma; anchors.fill: parent; hoverEnabled: true; onClicked: bar.startClicked() }
    }

    Row {
        anchors.left: startBtn.right
        anchors.leftMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        spacing: 4

        Repeater {
            model: bar.pinned
            delegate: Rectangle {
                required property string modelData
                width: 44; height: 44; radius: 10
                color: pma.containsMouse ? Theme.hover : "transparent"
                AppIcon { anchors.centerIn: parent; size: 30; icon: bar.app(modelData).icon; colors: bar.app(modelData).colors }
                MouseArea { id: pma; anchors.fill: parent; hoverEnabled: true; onClicked: bar.pinnedClicked(modelData) }
            }
        }

        Item { width: 6; height: 1 }
        Rectangle { width: 1; height: 28; color: Theme.border; anchors.verticalCenter: parent.verticalCenter }
        Item { width: 6; height: 1 }

        Repeater {
            model: bar.windows
            delegate: Rectangle {
                required property var modelData
                width: 176; height: 42; radius: 10
                anchors.verticalCenter: parent ? parent.verticalCenter : undefined
                color: modelData === bar.activeWindow && !modelData.minimized ? Theme.card
                     : wma.containsMouse ? Theme.hover : "transparent"
                Row {
                    x: 10; anchors.verticalCenter: parent.verticalCenter
                    spacing: 10
                    Icon { name: modelData.icon; size: 18; anchors.verticalCenter: parent.verticalCenter; opacity: modelData.minimized ? 0.5 : 1 }
                    Text {
                        width: 130
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.title
                        color: modelData.minimized ? Theme.textDim : Theme.text
                        font.pixelSize: 13; font.family: Theme.fontFamily
                        elide: Text.ElideRight
                    }
                }
                Rectangle {
                    anchors.bottom: parent.bottom
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: modelData === bar.activeWindow ? 28 : 10; height: 3; radius: 2
                    color: Theme.accent
                }
                MouseArea {
                    id: wma; anchors.fill: parent; hoverEnabled: true
                    acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
                    onClicked: (mouse) => {
                        if (mouse.button === Qt.LeftButton) bar.windowClicked(modelData)
                        else bar.closeWindow(modelData)   // Mittel-/Rechtsklick schließt wie bei Windows "Fenster schließen"
                    }
                }
            }
        }
    }

    // Infobereich: Klick öffnet Schnelleinstellungen bzw. Info-Center
    Row {
        anchors.right: desktopStrip.left
        anchors.rightMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        spacing: 4
        Rectangle {
            width: trayRow.implicitWidth + 20; height: 42; radius: 10
            color: tma.containsMouse ? Theme.hover : "transparent"
            Row {
                id: trayRow
                anchors.centerIn: parent
                spacing: 12
                Icon { name: "wifi"; size: 18; anchors.verticalCenter: parent.verticalCenter }
                Icon { name: "volume"; size: 18; anchors.verticalCenter: parent.verticalCenter }
                Row {
                    visible: bar.battery.present
                    spacing: 4
                    anchors.verticalCenter: parent.verticalCenter
                    Icon { name: "battery"; size: 18; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: bar.battery.level + "%"; color: Theme.text; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
                }
            }
            MouseArea { id: tma; anchors.fill: parent; hoverEnabled: true; onClicked: bar.trayClicked() }
        }
        Rectangle {
            width: clockCol.implicitWidth + 20; height: 42; radius: 10
            color: cma.containsMouse ? Theme.hover : "transparent"
            Column {
                id: clockCol
                anchors.centerIn: parent
                Text { id: clock; anchors.right: parent.right; color: Theme.text; font.pixelSize: 14; font.weight: Font.DemiBold; font.family: Theme.fontFamily }
                Text { id: date; anchors.right: parent.right; color: Theme.textDim; font.pixelSize: 11; font.family: Theme.fontFamily }
            }
            MouseArea { id: cma; anchors.fill: parent; hoverEnabled: true; onClicked: bar.clockClicked() }
        }
    }

    // Uhr: nur einmal pro Minute aktualisieren (statt jede Sekunde) – spart CPU
    function tick() {
        const now = new Date()
        clock.text = Qt.formatTime(now, "HH:mm")
        date.text = Qt.formatDate(now, "dd.MM.yyyy")
        clockTimer.interval = (60 - now.getSeconds()) * 1000 + 50
        clockTimer.restart()
    }
    Timer { id: clockTimer; repeat: false; onTriggered: bar.tick() }
    // Akku alle 2 Minuten lesen (nur eine kleine Datei)
    Timer {
        interval: 120000; running: true; repeat: true; triggeredOnStart: true
        onTriggered: bar.battery = backend.batteryInfo()
    }
    Component.onCompleted: tick()

    // Ganz rechts: Desktop anzeigen (wie bei Windows)
    Rectangle {
        id: desktopStrip
        anchors.right: parent.right
        width: 10; height: parent.height
        color: dma.containsMouse ? Theme.hover : "transparent"
        Rectangle { anchors.left: parent.left; width: 1; height: parent.height * 0.5; anchors.verticalCenter: parent.verticalCenter; color: Theme.border }
        MouseArea { id: dma; anchors.fill: parent; hoverEnabled: true; onClicked: bar.showDesktopClicked() }
    }
}
