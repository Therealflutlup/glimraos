import QtQuick

// GlimraApp: Handy mit dem PC koppeln
Item {
    id: rem
    property var info: backend.remoteInfo()
    Connections { target: backend; function onRemoteChanged() { rem.info = backend.remoteInfo() } }

    Flickable {
        anchors.fill: parent
        anchors.margins: 22
        contentHeight: col.height
        clip: true
        Column {
            id: col
            width: parent.width
            spacing: 14

            PageHeader { title: "GlimraApp – Handy verbinden"; subtitle: "PC sperren, Zwischenablage, Dateien senden, Lautstärke"; icon: "phone"; colors: ["#2ed3a1", "#159c78"] }

            Card {
                width: col.width
                Row {
                    width: parent.width
                    spacing: 12
                    Column {
                        width: parent.width - 130
                        spacing: 4
                        Text { text: "Fernsteuerung"; color: Theme.text; font.pixelSize: 15; font.weight: Font.DemiBold }
                        Text { text: rem.info.enabled ? "Aktiv – erreichbar unter " + rem.info.ip + ":" + rem.info.port : "Ausgeschaltet"; color: Theme.textDim; font.pixelSize: 13 }
                    }
                    GlimraButton {
                        primary: !rem.info.enabled
                        text: rem.info.enabled ? "Ausschalten" : "Einschalten"
                        onClicked: backend.setRemoteEnabled(!rem.info.enabled)
                    }
                }
            }

            Card {
                width: col.width
                visible: rem.info.enabled
                Column {
                    width: parent.width
                    spacing: 10
                    Text { text: "So koppelst du dein Handy"; color: Theme.text; font.pixelSize: 15; font.weight: Font.DemiBold }
                    Text { width: parent.width; wrapMode: Text.WordWrap; color: Theme.textDim; font.pixelSize: 13
                           text: "1. GlimraApp (APK) auf dem Handy installieren.\n2. Handy im selben WLAN – die App findet den PC automatisch.\n3. Diesen Code in der App eingeben:" }
                    Row {
                        spacing: 8
                        Repeater {
                            model: rem.info.code.split("")
                            delegate: Rectangle {
                                required property string modelData
                                width: 46; height: 58; radius: 10
                                color: Theme.titleBg; border.color: Theme.accent
                                Text { anchors.centerIn: parent; text: modelData; color: Theme.text; font.pixelSize: 30; font.weight: Font.DemiBold }
                            }
                        }
                        Item { width: 8; height: 1 }
                        IconButton { icon: "refresh"; anchors.verticalCenter: parent.verticalCenter; onClicked: backend.newPairCode() }
                    }
                    Text { text: "Manuell verbinden: " + rem.info.ip; color: Theme.textDim; font.pixelSize: 12 }
                }
            }

            Text { text: "Gekoppelte Geräte"; color: Theme.textDim; font.pixelSize: 12; font.weight: Font.DemiBold }
            Text { visible: rem.info.devices.length === 0; text: "Noch keine."; color: Theme.textDim; font.pixelSize: 13 }
            Repeater {
                model: rem.info.devices
                delegate: Card {
                    required property var modelData
                    width: col.width
                    pad: 12
                    Row {
                        width: parent.width
                        spacing: 12
                        Icon { name: "phone"; size: 22; anchors.verticalCenter: parent.verticalCenter }
                        Column {
                            width: parent.width - 120
                            anchors.verticalCenter: parent.verticalCenter
                            Text { text: modelData.name; color: Theme.text; font.pixelSize: 14 }
                            Text { text: "gekoppelt seit " + modelData.since; color: Theme.textDim; font.pixelSize: 12 }
                        }
                        IconButton { icon: "trash"; danger: true; onClicked: backend.removeDevice(modelData.name) }
                    }
                }
            }
        }
    }
}
