import QtQuick
import QtQuick.Controls

// Umzug: Daten von Windows (Setup-Manager / USB-Stick) oder einem alten Linux übernehmen
Item {
    id: tr
    property var sources: backend.transferSources()
    property var info: backend.remoteInfo()
    property int selected: 0
    property var chosen: ({})
    property string status: ""
    property int received: 0

    function refresh() { sources = backend.transferSources(); info = backend.remoteInfo() }
    Connections {
        target: backend
        function onRemoteChanged() { tr.info = backend.remoteInfo() }
        function onTaskProgress(kind, text) {
            if (kind === "transfer") { tr.received++; tr.status = "Empfange: " + text }
            if (kind === "import") tr.status = text
        }
        function onTaskDone(kind, ok, text) { if (kind === "import") { tr.status = text; backend.toast(text) } }
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: 22
        contentHeight: col.height
        clip: true
        Column {
            id: col
            width: parent.width
            spacing: 14

            PageHeader { title: "Umzug zu Glimra OS"; subtitle: "Dateien von Windows oder Linux übernehmen"; icon: "transfer"; colors: ["#f06bd0", "#b13fa0"] }

            Card {
                width: col.width
                Column {
                    width: parent.width; spacing: 8
                    Text { text: "Über das Netzwerk (Glimra Setup-Manager auf Windows)"; color: Theme.text; font.pixelSize: 15; font.weight: Font.DemiBold }
                    Text { width: parent.width; wrapMode: Text.WordWrap; color: Theme.textDim; font.pixelSize: 13
                           text: info.enabled ? "Im Setup-Manager „Daten umziehen → Netzwerk“ wählen und eingeben:  " + info.ip + "   Code: " + info.transferCode
                                              : "Zuerst in der GlimraApp-Einstellung die Fernsteuerung einschalten." }
                    Row {
                        spacing: 10
                        GlimraButton { visible: !info.enabled; primary: true; text: "Empfang einschalten"; onClicked: backend.setRemoteEnabled(true) }
                        GlimraButton { visible: info.enabled; icon: "refresh"; text: "Neuer Code"; onClicked: backend.newTransferCode() }
                    }
                    Text { visible: tr.received > 0; text: tr.received + " Dateien empfangen (Ordner „Umzug“)"; color: Theme.ok; font.pixelSize: 13 }
                }
            }

            Row {
                spacing: 10
                Text { text: "Gefundene Daten (USB-Stick, Festplatte, Ordner „Umzug“)"; color: Theme.textDim; font.pixelSize: 12; font.weight: Font.DemiBold; anchors.verticalCenter: parent.verticalCenter }
                IconButton { icon: "refresh"; size: 30; iconSize: 15; onClicked: tr.refresh() }
            }
            Text { visible: tr.sources.length === 0; width: col.width; wrapMode: Text.WordWrap; color: Theme.textDim; font.pixelSize: 13
                   text: "Nichts gefunden. Steck den USB-Stick mit dem Ordner „GlimraUmzug“ ein oder eine alte Festplatte." }

            Repeater {
                model: tr.sources
                delegate: Rectangle {
                    required property var modelData
                    required property int index
                    width: col.width; height: 54; radius: 10
                    color: tr.selected === index ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.16) : Theme.card
                    border.color: tr.selected === index ? Theme.accent : Theme.border
                    Row {
                        x: 14; anchors.verticalCenter: parent.verticalCenter; spacing: 12
                        Icon { name: "drive"; size: 22; anchors.verticalCenter: parent.verticalCenter }
                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            Text { text: modelData.label; color: Theme.text; font.pixelSize: 13; width: col.width - 80; elide: Text.ElideMiddle }
                            Text { text: modelData.categories.join(" · "); color: Theme.textDim; font.pixelSize: 12 }
                        }
                    }
                    MouseArea { anchors.fill: parent; onClicked: { tr.selected = index; tr.chosen = ({}) } }
                }
            }

            Flow {
                visible: tr.sources.length > 0
                width: col.width; spacing: 8
                Repeater {
                    model: tr.sources.length ? tr.sources[Math.min(tr.selected, tr.sources.length - 1)].categories : []
                    delegate: Rectangle {
                        required property string modelData
                        readonly property bool on: tr.chosen[modelData] !== false
                        width: lbl.implicitWidth + 44; height: 34; radius: 17
                        color: on ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.2) : Theme.card
                        border.color: on ? Theme.accent : Theme.border
                        Row {
                            anchors.centerIn: parent; spacing: 6
                            Icon { name: parent.parent.on ? "check" : "plus"; size: 14; anchors.verticalCenter: parent.verticalCenter }
                            Text { id: lbl; text: modelData; color: Theme.text; font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter }
                        }
                        MouseArea { anchors.fill: parent; onClicked: { const c = Object.assign({}, tr.chosen); c[modelData] = !parent.on; tr.chosen = c } }
                    }
                }
            }

            GlimraButton {
                visible: tr.sources.length > 0
                primary: true; icon: "download"; text: "Ausgewählte Daten übernehmen"
                onClicked: {
                    const src = tr.sources[Math.min(tr.selected, tr.sources.length - 1)]
                    const cats = src.categories.filter(c => tr.chosen[c] !== false)
                    tr.status = "Starte …"
                    backend.importFrom(src.path, cats)
                }
            }
            Text { visible: tr.status !== ""; text: tr.status; color: Theme.text; font.pixelSize: 13 }
        }
    }
}
