import QtQuick
import QtQuick.Controls

// Praktische Netzwerk-Tools: IP-Adresse, MAC, Gateway, DNS
Item {
    id: tools
    property var nets: backend.networkInfo()
    property var route: backend.routeInfo()

    function refresh() { nets = backend.networkInfo(); route = backend.routeInfo() }

    Flickable {
        anchors.fill: parent
        anchors.margins: 22
        contentHeight: col.height
        clip: true
        ScrollBar.vertical: ScrollBar {}

        Column {
            id: col
            width: parent.width
            spacing: 14

            Row {
                width: parent.width
                PageHeader { title: "Netzwerk-Tools"; subtitle: "IP-Adresse, MAC, Gateway, DNS"; icon: "tools"; colors: ["#6c7cff", "#4250d6"]; width: parent.width - 150 }
                GlimraButton { text: "Aktualisieren"; icon: "refresh"; onClicked: tools.refresh() }
            }

            Row {
                spacing: 12
                Repeater {
                    model: [ { k: "Rechner", v: backend.hostname() },
                             { k: "Gateway", v: tools.route.gateway },
                             { k: "DNS", v: tools.route.dns } ]
                    delegate: Rectangle {
                        required property var modelData
                        width: (col.width - 24) / 3; height: 72; radius: 12
                        color: Theme.card; border.color: Theme.border
                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            x: 14; spacing: 6
                            Text { text: modelData.k; color: Theme.textDim; font.pixelSize: 12; font.family: Theme.fontFamily }
                            Text { text: modelData.v; color: Theme.text; font.pixelSize: 15; font.weight: Font.DemiBold; font.family: Theme.fontFamily }
                        }
                    }
                }
            }

            Repeater {
                model: tools.nets
                delegate: Rectangle {
                    required property var modelData
                    width: col.width; height: 128; radius: 12
                    color: Theme.card; border.color: Theme.border
                    Column {
                        x: 16; y: 14; spacing: 8
                        Row {
                            spacing: 10
                            Icon { name: "plug"; size: 18; anchors.verticalCenter: parent.verticalCenter }
                            Text { text: modelData.name; color: Theme.text; font.pixelSize: 16; font.weight: Font.DemiBold; font.family: Theme.fontFamily }
                            Rectangle {
                                width: st.implicitWidth + 14; height: 20; radius: 10
                                color: modelData.state === "UP" ? Qt.rgba(0.29, 0.82, 0.58, 0.2) : Qt.rgba(1, 0.36, 0.42, 0.2)
                                Text { id: st; anchors.centerIn: parent; text: modelData.state; color: modelData.state === "UP" ? Theme.ok : Theme.danger; font.pixelSize: 11 }
                            }
                        }
                        Repeater {
                            model: [ ["IP-Adresse (IPv4)", modelData.ipv4], ["IPv6", modelData.ipv6], ["MAC-Adresse", modelData.mac] ]
                            delegate: Row {
                                required property var modelData
                                Text { width: 150; text: modelData[0]; color: Theme.textDim; font.pixelSize: 13; font.family: Theme.fontFamily }
                                Text { text: modelData[1]; color: Theme.text; font.pixelSize: 13; font.family: "monospace" }
                            }
                        }
                    }
                }
            }
        }
    }
}
