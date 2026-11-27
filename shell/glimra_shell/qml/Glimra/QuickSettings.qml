import QtQuick
import QtQuick.Controls

// Schnelleinstellungen (Win+A): WLAN, Bluetooth, Flugmodus, Energie, Lautstärke, Helligkeit, Akku
Popup {
    id: qs
    width: 452
    padding: 16
    property var st: null
    property string page: "main"   // main | wifi | bt
    property var wifiNets: []
    property var btDevs: []
    property string pwFor: ""
    signal openSettings(string section)

    onOpened: { page = "main"; backend.requestQuickState() }
    background: Rectangle { radius: 16; color: Theme.panelSolid; border.color: Theme.border }

    // Werte nur abfragen, solange das Fenster offen ist (spart CPU)
    Timer { interval: 4000; running: qs.opened && qs.page === "main"; repeat: true; onTriggered: backend.requestQuickState() }

    Connections {
        target: backend
        function onQuickStateReady(state) { qs.st = state }
        function onListReady(kind, items) {
            if (kind === "wifi") qs.wifiNets = items
            if (kind === "bt") qs.btDevs = items
        }
        function onTaskDone(kind, ok, text) { if (kind === "wifi" || kind === "bt") { backend.toast(text); if (ok) qs.page = "main"; backend.requestQuickState() } }
    }

    contentItem: Column {
        spacing: 14

        // ---------- Hauptseite
        Grid {
            visible: qs.page === "main"
            columns: 3; spacing: 8
            QuickToggle {
                icon: "wifi"; label: "WLAN"
                enabledTile: !!qs.st && qs.st.wifi.available
                on: !!qs.st && qs.st.wifi.enabled
                sub: qs.st && qs.st.wifi.connected ? qs.st.wifi.connected : (on ? "Nicht verbunden" : "Aus")
                onToggled: backend.setWifi(!on)
                onMore: { qs.page = "wifi"; qs.wifiNets = []; backend.requestWifiList() }
            }
            QuickToggle {
                icon: "bluetooth"; label: "Bluetooth"
                enabledTile: !!qs.st && qs.st.bt.available
                on: !!qs.st && qs.st.bt.enabled
                sub: on ? "An" : "Aus"
                onToggled: backend.setBluetooth(!on)
                onMore: { qs.page = "bt"; qs.btDevs = []; backend.requestBtDevices(false) }
            }
            QuickToggle {
                icon: "plane"; label: "Flugmodus"
                on: !!qs.st && qs.st.airplane
                sub: on ? "An" : "Aus"
                onToggled: backend.setAirplane(!on)
                onMore: qs.openSettings("netz")
            }
            QuickToggle {
                icon: "bolt"; label: "Energie"
                enabledTile: !!qs.st && qs.st.power.available
                on: !!qs.st && qs.st.power.current === "performance"
                sub: {
                    if (!qs.st || !qs.st.power.available) return "nicht verfügbar"
                    const o = qs.st.power.options.find(x => x.id === qs.st.power.current)
                    return o ? o.label : ""
                }
                onToggled: {
                    const opts = qs.st.power.options.map(o => o.id)
                    const i = opts.indexOf(qs.st.power.current)
                    backend.setPowerProfile(opts[(i + 1) % opts.length])
                }
                onMore: qs.openSettings("energie")
            }
            QuickToggle {
                icon: "camera"; label: "Bildschirmfoto"; sub: "Druck-Taste"
                onToggled: { qs.close(); backend.screenshot() }
                onMore: { qs.close(); backend.screenshot() }
            }
            QuickToggle {
                icon: "lock"; label: "Sperren"; sub: "Win + L"
                onToggled: { qs.close(); backend.lockNow() }
                onMore: { qs.close(); backend.lockNow() }
            }
        }

        Column {
            visible: qs.page === "main"
            width: 420; spacing: 6
            Row {
                spacing: 10; width: parent.width
                IconButton { icon: qs.st && qs.st.volume.muted ? "minimize" : "volume"; size: 32; iconSize: 17; onClicked: { backend.toggleMute(); backend.requestQuickState() } }
                GlimraSlider {
                    width: parent.width - 90; anchors.verticalCenter: parent.verticalCenter
                    from: 0; to: 100; stepSize: 1
                    value: qs.st ? qs.st.volume.level : 0
                    onMoved: backend.setVolume(value)
                }
                Text { anchors.verticalCenter: parent.verticalCenter; text: qs.st ? qs.st.volume.level : ""; color: Theme.textDim; font.pixelSize: 12; width: 30 }
            }
            Row {
                visible: !!qs.st && qs.st.brightness.available
                spacing: 10; width: parent.width
                Item { width: 32; height: 32; Icon { anchors.centerIn: parent; name: "sun"; size: 17 } }
                GlimraSlider {
                    width: parent.width - 90; anchors.verticalCenter: parent.verticalCenter
                    from: 5; to: 100; stepSize: 1
                    value: qs.st ? qs.st.brightness.level : 50
                    onMoved: backend.setBrightness(value)
                }
                Text { anchors.verticalCenter: parent.verticalCenter; text: qs.st ? qs.st.brightness.level : ""; color: Theme.textDim; font.pixelSize: 12; width: 30 }
            }
        }

        Rectangle {
            visible: qs.page === "main"
            width: 420; height: 44; radius: 10; color: Theme.card
            Row {
                x: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 8
                Icon { name: "battery"; size: 18; visible: !!qs.st && qs.st.battery.present; anchors.verticalCenter: parent.verticalCenter }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    color: Theme.text; font.pixelSize: 13
                    text: !qs.st ? "" : qs.st.battery.present ? qs.st.battery.level + " %" + (qs.st.battery.charging ? " · lädt" : "") : "Netzbetrieb"
                }
            }
            IconButton { anchors.right: parent.right; anchors.rightMargin: 6; anchors.verticalCenter: parent.verticalCenter; icon: "settings"; size: 32; iconSize: 17; onClicked: qs.openSettings("profil") }
        }

        // ---------- WLAN-Liste
        Column {
            visible: qs.page === "wifi"
            width: 420; spacing: 6
            Row { spacing: 8; IconButton { icon: "chevron"; rotation: 180; size: 32; iconSize: 15; onClicked: qs.page = "main" }
                  Text { text: "WLAN-Netze"; color: Theme.text; font.pixelSize: 16; font.weight: Font.DemiBold; anchors.verticalCenter: parent.verticalCenter } }
            Text { visible: qs.wifiNets.length === 0; text: "Suche …"; color: Theme.textDim; font.pixelSize: 13 }
            Repeater {
                model: qs.wifiNets
                delegate: Column {
                    required property var modelData
                    width: 420; spacing: 6
                    Rectangle {
                        width: 420; height: 44; radius: 10
                        color: modelData.active ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.18) : (wm.containsMouse ? Theme.hover : Theme.card)
                        Row {
                            x: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 10
                            Icon { name: "wifi"; size: 17; opacity: 0.4 + modelData.signal / 160; anchors.verticalCenter: parent.verticalCenter }
                            Text { text: modelData.ssid; color: Theme.text; font.pixelSize: 13; width: 270; elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter }
                            Icon { visible: modelData.secure; name: "lock"; size: 13; opacity: 0.6; anchors.verticalCenter: parent.verticalCenter }
                            Text { visible: modelData.active; text: "verbunden"; color: Theme.ok; font.pixelSize: 11; anchors.verticalCenter: parent.verticalCenter }
                        }
                        MouseArea { id: wm; anchors.fill: parent; hoverEnabled: true
                                    onClicked: { if (modelData.active) return; if (modelData.secure) qs.pwFor = modelData.ssid; else backend.wifiConnect(modelData.ssid, "") } }
                    }
                    Row {
                        visible: qs.pwFor === modelData.ssid
                        spacing: 8
                        GlimraField { id: pw; width: 290; echoMode: TextInput.Password; placeholderText: "WLAN-Passwort"; onAccepted: go.clicked() }
                        GlimraButton { id: go; primary: true; text: "Verbinden"; onClicked: { backend.wifiConnect(modelData.ssid, pw.text); qs.pwFor = "" } }
                    }
                }
            }
        }

        // ---------- Bluetooth-Geräte
        Column {
            visible: qs.page === "bt"
            width: 420; spacing: 6
            Row { spacing: 8; IconButton { icon: "chevron"; rotation: 180; size: 32; iconSize: 15; onClicked: qs.page = "main" }
                  Text { text: "Bluetooth-Geräte"; color: Theme.text; font.pixelSize: 16; font.weight: Font.DemiBold; anchors.verticalCenter: parent.verticalCenter } }
            GlimraButton { icon: "search"; text: "Neue Geräte suchen (8 s)"; onClicked: { qs.btDevs = []; backend.requestBtDevices(true) } }
            Text { visible: qs.btDevs.length === 0; text: "Keine Geräte. Gerät in den Kopplungsmodus versetzen und suchen."; color: Theme.textDim; font.pixelSize: 13; width: 420; wrapMode: Text.WordWrap }
            Repeater {
                model: qs.btDevs
                delegate: Rectangle {
                    required property var modelData
                    width: 420; height: 44; radius: 10; color: Theme.card
                    Row {
                        x: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 10
                        Icon { name: "bluetooth"; size: 16; anchors.verticalCenter: parent.verticalCenter }
                        Text { text: modelData.name; color: Theme.text; font.pixelSize: 13; width: 230; elide: Text.ElideRight; anchors.verticalCenter: parent.verticalCenter }
                    }
                    GlimraButton {
                        anchors.right: parent.right; anchors.rightMargin: 6; anchors.verticalCenter: parent.verticalCenter
                        implicitHeight: 32
                        text: modelData.connected ? "Trennen" : "Verbinden"
                        onClicked: modelData.connected ? backend.btDisconnect(modelData.mac) : backend.btConnect(modelData.mac)
                    }
                }
            }
        }
    }
}
