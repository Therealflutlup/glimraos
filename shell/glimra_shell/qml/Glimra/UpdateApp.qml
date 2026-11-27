import QtQuick
import QtQuick.Controls

// Glimra Update: wie Windows Update – prüfen, installieren, vorher automatisch Backup
Item {
    id: up
    property var updates: []
    property bool checking: true
    property bool running: false
    property string log: ""
    property string result: ""

    Component.onCompleted: backend.requestUpdates()
    Connections {
        target: backend
        function onListReady(kind, items) { if (kind === "updates") { up.updates = items; up.checking = false } }
        function onTaskProgress(kind, text) { if (kind === "update") up.log = text }
        function onTaskDone(kind, ok, text) {
            if (kind === "update") { up.running = false; up.result = text; backend.toast(text); up.checking = true; backend.requestUpdates() }
        }
    }

    Column {
        anchors.fill: parent
        anchors.margins: 22
        spacing: 16

        PageHeader { title: "Glimra Update"; subtitle: "System und Apps aktuell halten"; icon: "update"; colors: ["#5b8cff", "#2ed3a1"] }

        Card {
            width: parent.width
            Row {
                width: parent.width
                spacing: 14
                Rectangle {
                    width: 52; height: 52; radius: 26
                    color: up.updates.length ? Qt.rgba(1, 0.7, 0.28, 0.2) : Qt.rgba(0.29, 0.82, 0.58, 0.2)
                    Icon { anchors.centerIn: parent; name: up.updates.length ? "update" : "check"; size: 26 }
                }
                Column {
                    width: parent.width - 240
                    anchors.verticalCenter: parent.verticalCenter
                    Text {
                        text: up.checking ? "Suche nach Updates …" : up.running ? "Updates werden installiert …"
                            : up.updates.length ? up.updates.length + " Updates verfügbar" : "Alles ist aktuell"
                        color: Theme.text; font.pixelSize: 17; font.weight: Font.DemiBold
                    }
                    Text { text: up.running ? up.log : "Vor jedem Update legt Glimra OS automatisch ein Backup an."; color: Theme.textDim; font.pixelSize: 12; width: parent.width; elide: Text.ElideRight }
                }
                GlimraButton {
                    anchors.verticalCenter: parent.verticalCenter
                    primary: up.updates.length > 0 && !up.running
                    icon: up.updates.length ? "download" : "refresh"
                    text: up.running ? "Läuft …" : up.updates.length ? "Jetzt installieren" : "Erneut prüfen"
                    onClicked: {
                        if (up.running || up.checking) return
                        if (up.updates.length) { up.running = true; up.result = ""; backend.runUpdates() }
                        else { up.checking = true; backend.requestUpdates() }
                    }
                }
            }
        }

        Text { visible: up.result !== ""; text: up.result; color: Theme.ok; font.pixelSize: 13 }
        Text { visible: up.updates.length > 0; text: "Details"; color: Theme.textDim; font.pixelSize: 12; font.weight: Font.DemiBold }

        ListView {
            width: parent.width
            height: parent.height - 220
            clip: true; spacing: 4
            model: up.updates
            ScrollBar.vertical: ScrollBar {}
            delegate: Rectangle {
                required property var modelData
                width: ListView.view.width; height: 36; radius: 8; color: Theme.card
                Row {
                    x: 12; anchors.verticalCenter: parent.verticalCenter
                    Text { width: 300; text: modelData.name; color: Theme.text; font.pixelSize: 13; elide: Text.ElideRight }
                    Text { text: (modelData.old ? modelData.old + "  →  " : "") + modelData.new; color: Theme.textDim; font.pixelSize: 12 }
                }
            }
        }
    }
}
