import QtQuick

// Sicherheit: Firewall + Virenschutz (ClamAV)
Item {
    id: sec
    property var st: backend.securityStatus()
    property string scanResult: ""
    property bool scanOk: true
    property string busy: ""

    Connections {
        target: backend
        function onTaskDone(kind, ok, text) {
            if (kind === "scan") { sec.scanResult = text; sec.scanOk = ok }
            if (kind === "scan" || kind === "firewall" || kind === "virusdb") {
                sec.busy = ""; sec.st = backend.securityStatus(); backend.toast(text)
            }
        }
    }

    Column {
        anchors.fill: parent
        anchors.margins: 22
        spacing: 14

        PageHeader { title: "Sicherheit"; subtitle: "Firewall und Virenschutz"; icon: "shield"; colors: ["#ff6b6b", "#d63b4f"] }

        Card {
            width: parent.width
            Row {
                width: parent.width
                spacing: 14
                Icon { name: "shield"; size: 28; anchors.verticalCenter: parent.verticalCenter }
                Column {
                    width: parent.width - 190
                    anchors.verticalCenter: parent.verticalCenter
                    Text { text: "Firewall"; color: Theme.text; font.pixelSize: 15; font.weight: Font.DemiBold }
                    Text { text: sec.st.firewall === "active" ? "Aktiv – unerwünschte Verbindungen von außen werden blockiert." : "Aus (" + sec.st.firewall + ")"; color: sec.st.firewall === "active" ? Theme.ok : Theme.textDim; font.pixelSize: 13; width: parent.width; wrapMode: Text.WordWrap }
                }
                GlimraButton {
                    anchors.verticalCenter: parent.verticalCenter
                    primary: sec.st.firewall !== "active"
                    text: sec.busy === "fw" ? "…" : (sec.st.firewall === "active" ? "Ausschalten" : "Einschalten")
                    onClicked: { sec.busy = "fw"; backend.setFirewall(sec.st.firewall !== "active") }
                }
            }
        }

        Card {
            width: parent.width
            Column {
                width: parent.width
                spacing: 12
                Row {
                    spacing: 14
                    Icon { name: "search"; size: 28; anchors.verticalCenter: parent.verticalCenter }
                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        Text { text: "Virenschutz"; color: Theme.text; font.pixelSize: 15; font.weight: Font.DemiBold }
                        Text { text: sec.st.clamav ? ("Datenbank: " + (sec.st.db || "noch nicht geladen")) : "ClamAV ist nicht installiert."; color: Theme.textDim; font.pixelSize: 13 }
                    }
                }
                Flow {
                    width: parent.width
                    spacing: 10
                    GlimraButton { primary: true; icon: "search"; text: sec.busy === "scan" ? "Prüfe …" : "Persönlichen Ordner prüfen"; onClicked: { sec.busy = "scan"; sec.scanResult = ""; backend.virusScan("") } }
                    GlimraButton { icon: "download"; text: "Downloads prüfen"; onClicked: { sec.busy = "scan"; sec.scanResult = ""; backend.virusScan("~/Downloads") } }
                    GlimraButton { icon: "refresh"; text: sec.busy === "db" ? "Lädt …" : "Datenbank aktualisieren"; onClicked: { sec.busy = "db"; backend.updateVirusDb() } }
                }
                Rectangle {
                    visible: sec.scanResult !== ""
                    width: parent.width; height: res.height + 20; radius: 10
                    color: sec.scanOk ? Qt.rgba(0.29, 0.82, 0.58, 0.14) : Qt.rgba(1, 0.36, 0.42, 0.14)
                    Row {
                        x: 12; y: 10; spacing: 10
                        Icon { name: sec.scanOk ? "check" : "info"; size: 18 }
                        Text { id: res; width: sec.width - 120; wrapMode: Text.WordWrap; text: sec.scanResult; color: Theme.text; font.pixelSize: 13 }
                    }
                }
            }
        }
    }
}
