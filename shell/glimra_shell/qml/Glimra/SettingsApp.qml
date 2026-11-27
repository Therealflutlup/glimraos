import QtQuick
import QtQuick.Controls

// Einstellungen: Seitenleiste links, Inhalt rechts (wie in der Skizze)
Item {
    id: app
    signal openApp(string id)
    property string section: "profil"
    property var info: backend.systemInfo()
    property var qs: null
    property var sinks: []
    Connections {
        target: backend
        function onQuickStateReady(state) { app.qs = state }
        function onListReady(kind, items) { if (kind === "sinks") app.sinks = items }
    }
    onSectionChanged: { contentFlick.contentY = 0; if (["ton", "anzeige", "energie", "netz"].indexOf(section) >= 0) { backend.requestQuickState(); if (section === "ton") backend.requestSinks() } }
    Component.onCompleted: sectionChanged()

    Rectangle {
        id: sidebar
        width: 214; height: parent.height
        color: Theme.titleBg

        Column {
            x: 12; y: 16
            width: parent.width - 24
            spacing: 3

            Row {
                spacing: 10
                bottomPadding: 14
                Rectangle {
                    width: 40; height: 40; radius: 20
                    gradient: Gradient {
                        GradientStop { position: 0; color: Theme.accent }
                        GradientStop { position: 1; color: Theme.accent2 }
                    }
                    Text { anchors.centerIn: parent; text: (backend.settings.name || "L").charAt(0).toUpperCase(); color: "white"; font.pixelSize: 17; font.weight: Font.Bold }
                }
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    Text { text: backend.settings.name || "Glimra-Nutzer"; color: Theme.text; font.pixelSize: 14; font.weight: Font.DemiBold; font.family: Theme.fontFamily }
                    Text { text: backend.settings.email || "keine E-Mail"; color: Theme.textDim; font.pixelSize: 11; font.family: Theme.fontFamily; width: 130; elide: Text.ElideRight }
                }
            }

            Repeater {
                model: [
                    { id: "profil",  label: "Profil",           icon: "user" },
                    { id: "konto",   label: "Konto & Sperre",   icon: "key" },
                    { id: "design",  label: "Personalisierung", icon: "palette" },
                    { id: "nutzung", label: "Nutzungsprofil",   icon: "target" },
                    { id: "netz",    label: "WLAN & Bluetooth", icon: "wifi" },
                    { id: "ton",     label: "Ton",              icon: "volume" },
                    { id: "anzeige", label: "Anzeige",          icon: "sun" },
                    { id: "energie", label: "Energie & Akku",   icon: "battery" },
                    { id: "tasten",  label: "Tastenkürzel",     icon: "windowsapp" },
                    { id: "update",  label: "Update & Store",   icon: "update" },
                    { id: "system",  label: "System",           icon: "computer" },
                    { id: "ueber",   label: "Über Glimra OS",     icon: "info" }
                ]
                delegate: Rectangle {
                    required property var modelData
                    width: parent.width; height: 34; radius: 9
                    color: app.section === modelData.id ? Theme.card : (sbm.containsMouse ? Theme.hover : "transparent")
                    Rectangle { visible: app.section === modelData.id; width: 3; height: 18; radius: 2; color: Theme.accent; anchors.verticalCenter: parent.verticalCenter }
                    Row {
                        x: 14; anchors.verticalCenter: parent.verticalCenter
                        spacing: 12
                        Icon { name: modelData.icon; size: 17; anchors.verticalCenter: parent.verticalCenter }
                        Text { text: modelData.label; color: Theme.text; font.pixelSize: 14; font.family: Theme.fontFamily; anchors.verticalCenter: parent.verticalCenter }
                    }
                    MouseArea { id: sbm; anchors.fill: parent; hoverEnabled: true; onClicked: app.section = modelData.id }
                }
            }
        }
    }

    Flickable {
        id: contentFlick
        anchors { left: sidebar.right; right: parent.right; top: parent.top; bottom: parent.bottom; margins: 26 }
        contentHeight: pages.childrenRect.height + 10
        clip: true
        ScrollBar.vertical: ScrollBar {}
        Item {
        id: pages
        width: contentFlick.width

        component Heading: Text { color: Theme.text; font.pixelSize: 22; font.weight: Font.DemiBold; font.family: Theme.fontFamily }
        component Label: Text { color: Theme.textDim; font.pixelSize: 13; font.family: Theme.fontFamily }
        component InfoRow: Row {
            property string k
            property string v
            Text { width: 160; text: parent.k; color: Theme.textDim; font.pixelSize: 14; font.family: Theme.fontFamily }
            Text { text: parent.v; color: Theme.text; font.pixelSize: 14; font.family: Theme.fontFamily }
        }

        // Profil
        Column {
            visible: app.section === "profil"
            width: parent.width; spacing: 12
            Heading { text: "Profil" }
            Label { text: "Name" }
            GlimraField { id: nameF; width: Math.min(380, parent.width); text: backend.settings.name || "" }
            Label { text: "E-Mail" }
            GlimraField { id: mailF; width: Math.min(380, parent.width); text: backend.settings.email || "" }
            GlimraButton {
                primary: true; text: "Speichern"; icon: "check"
                onClicked: { backend.setSetting("name", nameF.text.trim()); backend.setSetting("email", mailF.text.trim()) }
            }
        }

        // Konto & Sperre
        Column {
            visible: app.section === "konto"
            width: parent.width; spacing: 12
            Heading { text: "Konto & Sperre" }
            Label { width: parent.width; wrapMode: Text.WordWrap; text: "Mit einer PIN ist der Sperrbildschirm geschützt – auch wenn du den PC über die GlimraApp sperrst." }
            Label { text: backend.hasPin() ? "PIN ist eingerichtet." : "Noch keine PIN." }
            Row {
                spacing: 10
                GlimraField { id: pinF; width: 180; placeholderText: "Neue PIN (4–8 Ziffern)"; echoMode: TextInput.Password; inputMethodHints: Qt.ImhDigitsOnly }
                GlimraButton {
                    primary: true; text: "PIN speichern"; icon: "key"
                    onClicked: {
                        if (backend.setPin(pinF.text)) { backend.toast("PIN gespeichert."); pinF.text = "" }
                        else backend.toast("Die PIN muss aus 4 bis 8 Ziffern bestehen.")
                    }
                }
                GlimraButton { text: "PIN entfernen"; onClicked: { backend.setPin(""); backend.toast("PIN entfernt.") } }
            }
            Item { width: 1; height: 8 }
            Label { width: parent.width; wrapMode: Text.WordWrap; text: "Glimra-Konto: Name, E-Mail, Farben und Hintergrund als Datei sichern und auf einem anderen Glimra-OS-PC übernehmen (z. B. über deine Cloud)." }
            Row {
                spacing: 10
                GlimraButton { text: "Konto exportieren"; icon: "upload"; onClicked: backend.exportSettings() }
                GlimraButton { text: "Konto importieren"; icon: "download"; onClicked: backend.importSettings() }
            }
            Label { text: "Datei: glimra-konto.json im persönlichen Ordner" }
            Item { width: 1; height: 8 }
            GlimraButton { text: "Jetzt sperren"; icon: "lock"; onClicked: backend.lockNow() }
        }

        // Personalisierung
        Column {
            visible: app.section === "design"
            width: parent.width; spacing: 14
            Heading { text: "Personalisierung" }
            Label { text: "Akzentfarbe" }
            Row {
                spacing: 10
                Repeater {
                    model: ["#5b8cff", "#a06bff", "#ff6b9a", "#ff9f43", "#2ed3a1", "#3fc5f0"]
                    delegate: Rectangle {
                        required property string modelData
                        width: 34; height: 34; radius: 17
                        color: modelData
                        border.color: "white"
                        border.width: backend.settings.accent === modelData ? 3 : 0
                        MouseArea { anchors.fill: parent; onClicked: backend.setSetting("accent", modelData) }
                    }
                }
            }
            Label { text: "Hintergrundbild" }
            GlimraButton { text: "Hintergrund wählen"; icon: "image"; onClicked: app.openApp("wallpaper") }
        }

        // Nutzungsprofil
        Column {
            visible: app.section === "nutzung"
            width: parent.width; spacing: 12
            Heading { text: "Nutzungsprofil" }
            Label { text: "Aktuell: " + ({ gaming: "Gaming", leistung: "Leistung", arbeit: "Arbeit", apps: "Arbeits-Apps" }[backend.settings.profile] || "keins") }
            Label { width: parent.width; wrapMode: Text.WordWrap; text: "Ein Profil installiert passende Programme. Du kannst mehrere nacheinander installieren." }
            Flow {
                width: parent.width; spacing: 10
                Repeater {
                    model: [ { id: "gaming", t: "Gaming", i: "game" }, { id: "leistung", t: "Leistung", i: "bolt" },
                             { id: "arbeit", t: "Arbeit", i: "briefcase" }, { id: "apps", t: "Arbeits-Apps", i: "apps" } ]
                    delegate: GlimraButton {
                        required property var modelData
                        text: modelData.t; icon: modelData.i
                        onClicked: { backend.setSetting("profile", modelData.id); backend.applyProfile(modelData.id) }
                    }
                }
            }
            Item { width: 1; height: 10 }
            GlimraButton { text: "Einrichtung erneut starten"; icon: "refresh"; onClicked: backend.resetSetup() }
        }

        // Ton
        Column {
            visible: app.section === "ton"
            width: parent.width; spacing: 12
            Heading { text: "Ton" }
            Label { text: "Lautstärke" + (app.qs && app.qs.volume.muted ? " (stumm)" : "") }
            Row {
                spacing: 10
                GlimraSlider { width: 320; from: 0; to: 100; value: app.qs ? app.qs.volume.level : 0; onMoved: backend.setVolume(value) }
                GlimraButton { text: "Stumm"; icon: "volume"; onClicked: { backend.toggleMute(); backend.requestQuickState() } }
            }
            Label { text: "Ausgabegerät" }
            Text { visible: app.sinks.length === 0; text: "Keine Geräte gefunden."; color: Theme.textDim; font.pixelSize: 13 }
            Repeater {
                model: app.sinks
                delegate: Rectangle {
                    required property var modelData
                    width: Math.min(460, parent.width); height: 42; radius: 10
                    color: modelData.default ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.18) : Theme.card
                    border.color: modelData.default ? Theme.accent : Theme.border
                    Row { x: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 10
                          Icon { name: "volume"; size: 16; anchors.verticalCenter: parent.verticalCenter }
                          Text { text: modelData.label; color: Theme.text; font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter } }
                    MouseArea { anchors.fill: parent; onClicked: { backend.setSink(modelData.name); backend.requestSinks() } }
                }
            }
        }

        // Anzeige
        Column {
            visible: app.section === "anzeige"
            width: parent.width; spacing: 12
            Heading { text: "Anzeige" }
            Label { text: app.qs && app.qs.brightness.available ? "Helligkeit" : "Helligkeit lässt sich hier nur bei Laptop-Bildschirmen einstellen." }
            GlimraSlider { visible: !!app.qs && app.qs.brightness.available; width: 320; from: 5; to: 100; value: app.qs ? app.qs.brightness.level : 50; onMoved: backend.setBrightness(value) }
            Label { text: "Hintergrund und Farben" }
            GlimraButton { text: "Personalisierung öffnen"; icon: "palette"; onClicked: app.section = "design" }
        }

        // Energie
        Column {
            visible: app.section === "energie"
            width: parent.width; spacing: 12
            Heading { text: "Energie & Akku" }
            Label { text: !app.qs ? "" : app.qs.battery.present ? "Akku: " + app.qs.battery.level + " %" + (app.qs.battery.charging ? " (lädt)" : "") : "Kein Akku – Netzbetrieb" }
            Label { text: "Energiemodus" }
            Text { visible: !!app.qs && !app.qs.power.available; text: "Energiemodi brauchen den Dienst power-profiles-daemon."; color: Theme.textDim; font.pixelSize: 13 }
            Row {
                spacing: 8
                Repeater {
                    model: app.qs ? app.qs.power.options : []
                    delegate: GlimraButton {
                        required property var modelData
                        primary: app.qs.power.current === modelData.id
                        text: modelData.label
                        icon: modelData.id === "power-saver" ? "battery" : modelData.id === "performance" ? "bolt" : "sun"
                        onClicked: backend.setPowerProfile(modelData.id)
                    }
                }
            }
            Label { width: parent.width; wrapMode: Text.WordWrap; text: "„Energiesparen“ senkt Prozessortakt und Stromverbrauch, „Leistung“ ist gut für Spiele." }
        }

        // Tastenkürzel
        Column {
            visible: app.section === "tasten"
            width: parent.width; spacing: 6
            Heading { text: "Tastenkürzel" }
            Label { text: "Wie bei Windows – die Windows-Taste heißt hier auch so." }
            Item { width: 1; height: 6 }
            Repeater {
                model: backend.shortcutHelp()
                delegate: Row {
                    required property var modelData
                    Rectangle {
                        width: 230; height: 30; radius: 7; color: Theme.titleBg
                        Text { x: 10; anchors.verticalCenter: parent.verticalCenter; text: modelData.keys; color: Theme.text; font.pixelSize: 12; font.family: "monospace" }
                    }
                    Text { leftPadding: 14; anchors.verticalCenter: parent.verticalCenter; text: modelData.action; color: Theme.text; font.pixelSize: 13 }
                }
            }
        }

        // Update & Store
        Column {
            visible: app.section === "update"
            width: parent.width; spacing: 12
            Heading { text: "Update & Store" }
            Label { width: parent.width; wrapMode: Text.WordWrap; text: "Glimra OS sucht alle 6 Stunden nach Updates und meldet sich. Vor jedem Update entsteht automatisch ein Backup." }
            Row {
                spacing: 10
                GlimraButton { primary: true; icon: "update"; text: "Glimra Update öffnen"; onClicked: app.openApp("update") }
                GlimraButton { icon: "bag"; text: "Glimra Store öffnen"; onClicked: app.openApp("store") }
            }
        }

        // Netzwerk
        Column {
            visible: app.section === "netz"
            width: parent.width; spacing: 12
            Heading { text: "WLAN & Bluetooth" }
            Row {
                spacing: 10
                GlimraButton { icon: "wifi"; primary: !!app.qs && app.qs.wifi.enabled; text: "WLAN " + (app.qs && app.qs.wifi.enabled ? "an" : "aus"); onClicked: backend.setWifi(!(app.qs && app.qs.wifi.enabled)) }
                GlimraButton { icon: "bluetooth"; primary: !!app.qs && app.qs.bt.enabled; text: "Bluetooth " + (app.qs && app.qs.bt.enabled ? "an" : "aus"); onClicked: backend.setBluetooth(!(app.qs && app.qs.bt.enabled)) }
                GlimraButton { icon: "plane"; primary: !!app.qs && app.qs.airplane; text: "Flugmodus"; onClicked: backend.setAirplane(!(app.qs && app.qs.airplane)) }
            }
            Label { text: app.qs && app.qs.wifi.connected ? "Verbunden mit: " + app.qs.wifi.connected : "Netze und Geräte wählst du in den Schnelleinstellungen (Win + A)." }
            Repeater {
                model: backend.networkInfo()
                delegate: InfoRow { required property var modelData; k: modelData.name; v: modelData.ipv4 + "   (" + modelData.state + ")" }
            }
            Row {
                spacing: 10
                GlimraButton { text: "Netzwerk-Tools"; icon: "tools"; onClicked: app.openApp("tools") }
                GlimraButton { text: "Handy verbinden"; icon: "phone"; onClicked: app.openApp("remote") }
            }
        }

        // System
        Column {
            visible: app.section === "system"
            width: parent.width; spacing: 12
            Heading { text: "System" }
            InfoRow { k: "Rechnername"; v: app.info.hostname }
            InfoRow { k: "Prozessor"; v: app.info.cpu }
            InfoRow { k: "Arbeitsspeicher"; v: app.info.ramUsed ? app.info.ramUsed + " von " + app.info.ramTotal : "–" }
            InfoRow { k: "Laufzeit"; v: app.info.uptime || "–" }
            InfoRow { k: "Kernel"; v: app.info.kernel }
            Row {
                spacing: 10
                GlimraButton { text: "Taskmanager"; icon: "taskman"; onClicked: app.openApp("taskman") }
                GlimraButton { text: "Backups"; icon: "backup"; onClicked: app.openApp("backup") }
                GlimraButton { text: "Sicherheit"; icon: "shield"; onClicked: app.openApp("security") }
            }
        }

        // Über
        Column {
            visible: app.section === "ueber"
            width: parent.width; spacing: 16
            GlimraLogo { size: 70 }
            Heading { text: "Glimra OS Desktop " + backend.version + " „" + backend.codename + "“" }
            Label { text: app.info.os }
            Label { width: parent.width; wrapMode: Text.WordWrap; text: "Eigene Oberfläche: Glimra Shell (Wayland-Compositor) mit eigenem Symbolset. Unterbau: Arch Linux. Freie Software unter der GNU GPL v3." }
        }
    }
    }
}
