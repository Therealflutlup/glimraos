import QtQuick
import QtQuick.Controls

// Backups: Snapshots des Systems (vor jedem Update automatisch) + Wiederherstellen
Item {
    id: bk
    property var snaps: backend.snapshots()
    property int confirmNr: -1

    Connections {
        target: backend
        function onTaskDone(kind, ok, text) {
            if (kind === "snapshot" || kind === "restore") { backend.toast(text); bk.snaps = backend.snapshots() }
        }
    }

    Column {
        anchors.fill: parent
        anchors.margins: 22
        spacing: 14

        PageHeader { title: "Backups"; subtitle: "Systemzustände sichern und wiederherstellen"; icon: "backup"; colors: ["#ffb347", "#e07b1a"] }

        Text { width: parent.width; wrapMode: Text.WordWrap; color: Theme.textDim; font.pixelSize: 13
               text: "Vor jedem Update legt Glimra OS automatisch ein Backup an. Startet das System zweimal nicht richtig, lädt es selbst das letzte Backup („Ein Problem ist aufgetreten – Backup wird geladen“). Deine persönlichen Dateien bleiben dabei unverändert." }

        Row {
            spacing: 10
            GlimraField { id: desc; width: 280; placeholderText: "Beschreibung, z. B. vor Treiber-Test" }
            GlimraButton { primary: true; icon: "plus"; text: "Backup erstellen"; onClicked: { backend.createSnapshot(desc.text); desc.text = "" } }
            IconButton { icon: "refresh"; onClicked: bk.snaps = backend.snapshots() }
        }

        Rectangle {
            visible: bk.confirmNr >= 0
            width: parent.width; height: 56; radius: 10
            color: Qt.rgba(1, 0.36, 0.42, 0.14)
            Row {
                x: 14; anchors.verticalCenter: parent.verticalCenter; spacing: 10
                Text { text: "Backup " + bk.confirmNr + " wiederherstellen? Danach ist ein Neustart nötig."; color: Theme.text; font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter }
                GlimraButton { danger: true; text: "Ja, wiederherstellen"; onClicked: { backend.restoreSnapshot(bk.confirmNr); bk.confirmNr = -1 } }
                GlimraButton { text: "Abbrechen"; onClicked: bk.confirmNr = -1 }
            }
        }

        Text { visible: bk.snaps.length === 0; color: Theme.textDim; font.pixelSize: 13
               text: "Noch keine Backups (im Live-System gibt es keine – erst nach der Installation)." }

        ListView {
            width: parent.width
            height: parent.height - 260
            clip: true
            spacing: 6
            model: bk.snaps
            ScrollBar.vertical: ScrollBar {}
            delegate: Rectangle {
                required property var modelData
                width: ListView.view.width; height: 52; radius: 10
                color: Theme.card; border.color: Theme.border
                Row {
                    x: 14; anchors.verticalCenter: parent.verticalCenter; spacing: 14
                    Text { text: "#" + modelData.number; color: Theme.textDim; font.pixelSize: 13; width: 44; anchors.verticalCenter: parent.verticalCenter }
                    Column {
                        width: bk.width - 260
                        anchors.verticalCenter: parent.verticalCenter
                        Text { text: modelData.description || (modelData.type === "pre" ? "Vor Update" : "Backup"); color: Theme.text; font.pixelSize: 14; elide: Text.ElideRight; width: parent.width }
                        Text { text: modelData.date; color: Theme.textDim; font.pixelSize: 12 }
                    }
                    GlimraButton { text: "Wiederherstellen"; icon: "backup"; anchors.verticalCenter: parent.verticalCenter; onClicked: bk.confirmNr = modelData.number }
                }
            }
        }
    }
}
