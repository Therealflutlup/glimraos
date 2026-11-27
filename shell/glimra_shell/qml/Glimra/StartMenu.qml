import QtQuick
import QtQuick.Controls

// Startmenü mit Suche nach Apps, Einstellungen und Dateien (wie bei Windows)
Popup {
    id: menu
    property var apps: []
    property var fileHits: []
    signal launch(string id)
    signal lockClicked()
    signal openSetting(string section)

    readonly property var settingsIndex: [
        { label: "WLAN und Netzwerk", s: "netz", k: "wlan wifi internet netzwerk ip" },
        { label: "Bluetooth", s: "netz", k: "bluetooth kopfhörer maus" },
        { label: "Ton und Lautstärke", s: "ton", k: "ton sound lautstärke lautsprecher kopfhörer audio" },
        { label: "Anzeige und Helligkeit", s: "anzeige", k: "anzeige bildschirm helligkeit display" },
        { label: "Energie und Akku", s: "energie", k: "energie akku batterie strom leistung" },
        { label: "Hintergrund und Farben", s: "design", k: "hintergrund farbe design personalisierung" },
        { label: "Sperrbildschirm und PIN", s: "konto", k: "pin sperre passwort konto" },
        { label: "Tastenkürzel", s: "tasten", k: "tastenkürzel tastatur shortcuts" },
        { label: "Systeminformationen", s: "system", k: "system info prozessor ram speicher" },
        { label: "Updates", s: "update", k: "update aktualisieren" }
    ]

    function setQuery(t) { search.text = t }
    function q() { return search.text.trim().toLowerCase() }
    function appHits() { return apps.filter(a => a.name.toLowerCase().indexOf(q()) >= 0) }
    function settingHits() { return q().length < 2 ? [] : settingsIndex.filter(x => x.label.toLowerCase().indexOf(q()) >= 0 || x.k.indexOf(q()) >= 0) }

    width: 540
    height: 600
    padding: 18
    onOpened: { search.text = ""; fileHits = []; search.forceActiveFocus() }
    background: Rectangle { radius: 18; color: Theme.panelSolid; border.color: Theme.border }

    Timer { id: fileTimer; interval: 250; onTriggered: menu.fileHits = backend.searchFiles(search.text) }
    Connections { target: backend; function onIndexReady() { if (menu.opened && search.text.length > 1) fileTimer.restart() } }

    contentItem: Item {
        GlimraField {
            id: search
            width: parent.width
            leftPadding: 40
            placeholderText: "Apps, Einstellungen und Dateien suchen"
            onTextChanged: fileTimer.restart()
            onAccepted: {
                const a = menu.appHits(), st = menu.settingHits()
                if (a.length) menu.launch(a[0].id)
                else if (st.length) menu.openSetting(st[0].s)
                else if (menu.fileHits.length) { backend.openPath(menu.fileHits[0].path); menu.close() }
            }
            Keys.onEscapePressed: menu.close()
            Icon { name: "search"; size: 18; x: 12; anchors.verticalCenter: parent.verticalCenter; opacity: 0.7 }
        }

        // ---------- Alle Apps (ohne Suche)
        Text {
            id: header
            visible: search.text === ""
            anchors.top: search.bottom; anchors.topMargin: 16
            text: "Alle Apps"
            color: Theme.textDim; font.pixelSize: 12; font.weight: Font.DemiBold; font.family: Theme.fontFamily
        }
        Flickable {
            visible: search.text === ""
            anchors { top: header.bottom; topMargin: 10; left: parent.left; right: parent.right; bottom: footer.top; bottomMargin: 12 }
            contentHeight: grid.height
            clip: true
            Grid {
                id: grid
                columns: 5
                spacing: 4
                Repeater {
                    model: menu.apps
                    delegate: Rectangle {
                        required property var modelData
                        width: 98; height: 92; radius: 12
                        color: ama.containsMouse ? Theme.hover : "transparent"
                        Column {
                            anchors.centerIn: parent
                            spacing: 8
                            AppIcon { anchors.horizontalCenter: parent.horizontalCenter; icon: modelData.icon; colors: modelData.colors; size: 44 }
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                width: 94; horizontalAlignment: Text.AlignHCenter; elide: Text.ElideRight
                                text: modelData.name
                                color: Theme.text; font.pixelSize: 12; font.family: Theme.fontFamily
                            }
                        }
                        MouseArea { id: ama; anchors.fill: parent; hoverEnabled: true; onClicked: menu.launch(modelData.id) }
                    }
                }
            }
        }

        // ---------- Suchergebnisse
        Flickable {
            visible: search.text !== ""
            anchors { top: search.bottom; topMargin: 14; left: parent.left; right: parent.right; bottom: footer.top; bottomMargin: 12 }
            contentHeight: results.height
            clip: true
            Column {
                id: results
                width: parent.width
                spacing: 4

                component Hit: Rectangle {
                    property string icon: "apps"
                    property string title: ""
                    property string sub: ""
                    signal activated()
                    width: results.width; height: 46; radius: 10
                    color: hm.containsMouse ? Theme.hover : "transparent"
                    Row {
                        x: 10; anchors.verticalCenter: parent.verticalCenter; spacing: 12
                        Icon { name: parent.parent.icon; size: 20; anchors.verticalCenter: parent.verticalCenter }
                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            Text { text: parent.parent.parent.title; color: Theme.text; font.pixelSize: 14; width: results.width - 60; elide: Text.ElideRight }
                            Text { visible: text !== ""; text: parent.parent.parent.sub; color: Theme.textDim; font.pixelSize: 11; width: results.width - 60; elide: Text.ElideMiddle }
                        }
                    }
                    MouseArea { id: hm; anchors.fill: parent; hoverEnabled: true; onClicked: parent.activated() }
                }
                component Section: Text { color: Theme.textDim; font.pixelSize: 12; font.weight: Font.DemiBold; topPadding: 6; bottomPadding: 2 }

                Section { visible: menu.appHits().length > 0; text: "Apps" }
                Repeater {
                    model: menu.appHits()
                    delegate: Hit { required property var modelData; icon: modelData.icon; title: modelData.name; onActivated: menu.launch(modelData.id) }
                }
                Section { visible: menu.settingHits().length > 0; text: "Einstellungen" }
                Repeater {
                    model: menu.settingHits()
                    delegate: Hit { required property var modelData; icon: "settings"; title: modelData.label; onActivated: menu.openSetting(modelData.s) }
                }
                Section { visible: menu.fileHits.length > 0; text: "Dateien" }
                Repeater {
                    model: menu.fileHits
                    delegate: Hit { required property var modelData; icon: modelData.dir ? "folder" : "file"; title: modelData.name; sub: modelData.path
                                    onActivated: { backend.openPath(modelData.path); menu.close() } }
                }
                Text {
                    visible: menu.appHits().length + menu.settingHits().length + menu.fileHits.length === 0
                    text: "Nichts gefunden."
                    color: Theme.textDim; font.pixelSize: 13; topPadding: 10
                }
            }
        }

        Rectangle {
            id: footer
            anchors.bottom: parent.bottom
            width: parent.width; height: 54; radius: 12
            color: Theme.card
            Row {
                x: 14; anchors.verticalCenter: parent.verticalCenter
                spacing: 10
                Icon { name: "user"; size: 20; anchors.verticalCenter: parent.verticalCenter }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: backend.settings.name || "Glimra-Nutzer"
                    color: Theme.text; font.pixelSize: 14; font.family: Theme.fontFamily
                }
            }
            Row {
                anchors.right: parent.right; anchors.rightMargin: 8
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2
                IconButton { icon: "settings"; onClicked: menu.openSetting("profil") }
                IconButton { icon: "lock"; onClicked: menu.lockClicked() }
                IconButton { icon: "moon"; onClicked: backend.power("suspend") }
                IconButton { icon: "reboot"; onClicked: backend.power("reboot") }
                IconButton { icon: "power"; danger: true; onClicked: backend.power("poweroff") }
            }
        }
    }
}
