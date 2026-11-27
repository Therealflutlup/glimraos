import QtQuick

// Einrichtung beim ersten Start: Willkommen → Profil → "Wofür verwendest du mich?" → Fertig
Rectangle {
    id: wiz
    color: Theme.bg
    property int page: 0
    property string choice: ""

    Wallpaper { anchors.fill: parent; key: "aurora"; opacity: 0.8 }
    MouseArea { anchors.fill: parent }  // Klicks nicht zum Desktop durchlassen

    Rectangle {
        id: card
        anchors.centerIn: parent
        width: Math.min(640, parent.width - 40)
        height: 460
        radius: 22
        color: Theme.panelSolid
        border.color: Theme.border

        // Fortschrittspunkte
        Row {
            anchors.top: parent.top; anchors.topMargin: 22
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 8
            Repeater {
                model: 4
                delegate: Rectangle {
                    required property int index
                    width: index === wiz.page ? 26 : 8; height: 8; radius: 4
                    color: index <= wiz.page ? Theme.accent : Theme.border
                    Behavior on width { NumberAnimation { duration: 180 } }
                }
            }
        }

        // ---- Seite 0: Willkommen
        Column {
            visible: wiz.page === 0
            anchors.centerIn: parent
            spacing: 22
            GlimraLogo { size: 96; anchors.horizontalCenter: parent.horizontalCenter }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Willkommen bei Glimra"
                color: Theme.text; font.pixelSize: 30; font.weight: Font.DemiBold; font.family: Theme.fontFamily
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Wir richten Glimra OS in wenigen Schritten für dich ein."
                color: Theme.textDim; font.pixelSize: 15; font.family: Theme.fontFamily
            }
        }

        // ---- Seite 1: Profil
        Column {
            visible: wiz.page === 1
            anchors.centerIn: parent
            width: card.width - 120
            spacing: 14
            Text {
                text: "Wer bist du?"
                color: Theme.text; font.pixelSize: 26; font.weight: Font.DemiBold; font.family: Theme.fontFamily
            }
            Text {
                text: "Name und E-Mail erscheinen in deinem Profil."
                color: Theme.textDim; font.pixelSize: 14; font.family: Theme.fontFamily
            }
            Item { width: 1; height: 6 }
            GlimraField { id: nameField; width: parent.width; placeholderText: "Name"; text: backend.settings.name || "" }
            GlimraField { id: mailField; width: parent.width; placeholderText: "E-Mail (optional)"; text: backend.settings.email || "" }
        }

        // ---- Seite 2: Wofür verwendest du mich?
        Column {
            visible: wiz.page === 2
            anchors.centerIn: parent
            spacing: 16
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Wofür verwendest du mich?"
                color: Theme.text; font.pixelSize: 26; font.weight: Font.DemiBold; font.family: Theme.fontFamily
            }
            Grid {
                anchors.horizontalCenter: parent.horizontalCenter
                columns: 2
                spacing: 12
                Repeater {
                    model: [
                        { id: "gaming",   icon: "game",      colors: ["#2ed3a1", "#159c78"], name: "Zocken / Gaming", desc: "Steam, Wine, Gamemode" },
                        { id: "leistung", icon: "bolt",      colors: ["#ffb347", "#e07b1a"], name: "Leistung",        desc: "Energieprofile, Monitoring" },
                        { id: "arbeit",   icon: "briefcase", colors: ["#5b8cff", "#3a5bd9"], name: "Arbeit",          desc: "Office, E-Mail" },
                        { id: "apps",     icon: "apps",      colors: ["#a06bff", "#6b3cff"], name: "Arbeits-Apps",    desc: "App-Store mit Flatpak" }
                    ]
                    delegate: Rectangle {
                        required property var modelData
                        width: 230; height: 96; radius: 14
                        color: wiz.choice === modelData.id ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.18)
                             : (oma.containsMouse ? Theme.hover : Theme.card)
                        border.color: wiz.choice === modelData.id ? Theme.accent : Theme.border
                        border.width: wiz.choice === modelData.id ? 2 : 1
                        Row {
                            anchors.verticalCenter: parent.verticalCenter
                            x: 16; spacing: 14
                            AppIcon { icon: modelData.icon; colors: modelData.colors; size: 46; anchors.verticalCenter: parent.verticalCenter }
                            Column {
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 4
                                Text { text: modelData.name; color: Theme.text; font.pixelSize: 15; font.weight: Font.DemiBold; font.family: Theme.fontFamily }
                                Text { text: modelData.desc; color: Theme.textDim; font.pixelSize: 12; font.family: Theme.fontFamily }
                            }
                        }
                        MouseArea { id: oma; anchors.fill: parent; hoverEnabled: true; onClicked: wiz.choice = modelData.id }
                    }
                }
            }
        }

        // ---- Seite 3: Fertig
        Column {
            visible: wiz.page === 3
            anchors.centerIn: parent
            spacing: 18
            AppIcon { anchors.horizontalCenter: parent.horizontalCenter; icon: "sparkle"; colors: [Theme.accent, Theme.accent2]; size: 76 }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Alles bereit" + (nameField.text ? ", " + nameField.text : "") + "!"
                color: Theme.text; font.pixelSize: 28; font.weight: Font.DemiBold; font.family: Theme.fontFamily
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Rechtsklick auf den Desktop öffnet das Menü,\nder Glimra-Knopf unten links alle Apps."
                horizontalAlignment: Text.AlignHCenter
                color: Theme.textDim; font.pixelSize: 15; font.family: Theme.fontFamily
            }
        }

        // ---- Knöpfe
        Row {
            anchors.bottom: parent.bottom; anchors.bottomMargin: 24
            anchors.right: parent.right; anchors.rightMargin: 28
            spacing: 10
            GlimraButton {
                visible: wiz.page > 0 && wiz.page < 3
                text: "Zurück"
                onClicked: wiz.page--
            }
            GlimraButton {
                primary: true
                text: wiz.page === 3 ? "Los geht's" : (wiz.page === 2 && !wiz.choice ? "Überspringen" : "Weiter")
                onClicked: {
                    if (wiz.page === 1) {
                        backend.setSetting("name", nameField.text.trim())
                        backend.setSetting("email", mailField.text.trim())
                    }
                    if (wiz.page === 2 && wiz.choice) {
                        backend.setSetting("profile", wiz.choice)
                        backend.applyProfile(wiz.choice)
                    }
                    if (wiz.page === 3) {
                        backend.setSetting("setupDone", true)
                        wiz.page = 0
                        return
                    }
                    wiz.page++
                }
            }
        }
    }
}
