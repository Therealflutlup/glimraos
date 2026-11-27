import QtQuick
import QtQuick.Controls

// Vollversion installieren: Glimra OS vom USB-Stick fest auf eine Festplatte bringen.
// Schritte: Start → Laufwerk → Konto → Bestätigen → Installation → Fertig
Item {
    id: inst
    signal openWifi()

    property int page: 0
    property var disks: []
    property var chosen: null
    property bool online: false
    property bool netChecking: false
    property string error: ""
    property int step: 0
    property int steps: 6
    property string stepText: ""
    property string lastLog: ""
    property bool running: false
    property bool success: false
    property string resultText: ""
    readonly property bool server: backend.edition === "server"

    function refreshDisks() { disks = backend.installerDisks() }
    function checkNet() { netChecking = true; backend.checkInternet() }

    Component.onCompleted: { refreshDisks(); checkNet() }

    Connections {
        target: backend
        function onTaskDone(kind, ok, text) {
            if (kind === "net") { inst.online = ok; inst.netChecking = false }
            else if (kind === "install") {
                inst.running = false; inst.success = ok; inst.resultText = text
                inst.page = 5
                backend.toast(ok ? "Glimra OS ist fest installiert" : "Installation abgebrochen")
            }
        }
        function onTaskProgress(kind, text) {
            if (kind === "install-step") {
                const p = text.split("|")
                inst.step = parseInt(p[0]); inst.steps = parseInt(p[1]); inst.stepText = p.slice(2).join("|")
            } else if (kind === "install-log") inst.lastLog = text
        }
    }

    // ---------- kleine Bausteine
    component StepDots: Row {
        spacing: 6
        Repeater {
            model: 4
            Rectangle {
                required property int index
                width: index === Math.min(inst.page, 3) ? 22 : 8; height: 8; radius: 4
                color: index <= Math.min(inst.page, 3) ? Theme.accent : Theme.border
                Behavior on width { NumberAnimation { duration: 160 } }
            }
        }
    }
    component Hint: Text {
        color: Theme.textDim; font.pixelSize: 13; font.family: Theme.fontFamily
        wrapMode: Text.WordWrap
    }

    Column {
        anchors.fill: parent
        anchors.margins: 22
        spacing: 16

        Row {
            width: parent.width
            PageHeader {
                width: parent.width - dots.width
                title: "Vollversion installieren"
                subtitle: "Glimra OS fest auf diesen PC bringen – ohne USB-Stick"
                icon: "drive"; colors: ["#5b8cff", "#a06bff"]
            }
            StepDots { id: dots; anchors.verticalCenter: parent.verticalCenter; visible: inst.page < 4 }
        }

        // ================= 0: Start
        Column {
            visible: inst.page === 0
            width: parent.width
            spacing: 14

            Card {
                width: parent.width
                Column {
                    width: parent.width
                    spacing: 10
                    Text { text: "Du nutzt gerade die Testversion vom USB-Stick"; color: Theme.text; font.pixelSize: 17; font.weight: Font.DemiBold }
                    Hint {
                        width: parent.width
                        text: "Alles, was du jetzt änderst, ist nach einem Neustart wieder weg. Mit der Vollversion wird Glimra OS "
                            + "aus dem Internet geladen und fest auf eine Festplatte installiert – mit deinem Konto, Backups und Updates."
                    }
                }
            }

            Card {
                width: parent.width
                Row {
                    width: parent.width
                    spacing: 12
                    Rectangle {
                        width: 40; height: 40; radius: 20
                        color: inst.online ? Qt.rgba(0.29, 0.82, 0.58, 0.2) : Qt.rgba(1, 0.36, 0.42, 0.2)
                        Icon { anchors.centerIn: parent; name: inst.online ? "check" : "wifi"; size: 20 }
                    }
                    Column {
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width - 52 - netBtn.width - 12
                        Text {
                            text: inst.netChecking ? "Internet wird geprüft …" : inst.online ? "Mit dem Internet verbunden" : "Keine Internetverbindung"
                            color: Theme.text; font.pixelSize: 14; font.weight: Font.DemiBold
                        }
                        Hint { width: parent.width; text: inst.online ? "Die Vollversion kann geladen werden." : "Steck ein LAN-Kabel ein oder verbinde dich mit einem WLAN." }
                    }
                    GlimraButton {
                        id: netBtn
                        anchors.verticalCenter: parent.verticalCenter
                        visible: !inst.online
                        icon: "wifi"; text: "WLAN wählen"
                        onClicked: inst.openWifi()
                    }
                }
            }

            Row {
                spacing: 10
                GlimraButton {
                    primary: true; icon: "download"; text: "Weiter"
                    onClicked: {
                        if (!inst.online) { inst.checkNet(); backend.toast("Für die Vollversion wird Internet gebraucht"); return }
                        inst.refreshDisks(); inst.page = 1
                    }
                }
                GlimraButton { visible: !inst.online; icon: "refresh"; text: "Erneut prüfen"; onClicked: inst.checkNet() }
            }
        }

        // ================= 1: Laufwerk
        Column {
            visible: inst.page === 1
            width: parent.width
            spacing: 12

            Row {
                width: parent.width
                Text { width: parent.width - refresh.width; text: "Auf welches Laufwerk soll Glimra OS?"; color: Theme.text; font.pixelSize: 16; font.weight: Font.DemiBold; anchors.verticalCenter: parent.verticalCenter }
                GlimraButton { id: refresh; icon: "refresh"; text: "Neu suchen"; onClicked: inst.refreshDisks() }
            }

            ListView {
                width: parent.width
                height: Math.min(contentHeight, inst.height - 290)
                clip: true; spacing: 8
                model: inst.disks
                ScrollBar.vertical: ScrollBar {}
                delegate: Rectangle {
                    required property var modelData
                    readonly property bool sel: inst.chosen && inst.chosen.path === modelData.path
                    width: ListView.view.width; height: 66; radius: 12
                    color: sel ? Qt.rgba(0.36, 0.55, 1, 0.18) : (ma.containsMouse && modelData.usable ? Theme.hover : Theme.card)
                    border.color: sel ? Theme.accent : Theme.border
                    border.width: sel ? 2 : 1
                    opacity: modelData.usable ? 1 : 0.5
                    Row {
                        x: 14; anchors.verticalCenter: parent.verticalCenter
                        spacing: 14
                        Icon { name: modelData.removable ? "plug" : "drive"; size: 28; anchors.verticalCenter: parent.verticalCenter }
                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            Text { text: modelData.model + "  ·  " + modelData.sizeText; color: Theme.text; font.pixelSize: 15; font.weight: Font.DemiBold }
                            Text {
                                text: modelData.problem !== "" ? modelData.problem : modelData.kind + "  ·  " + modelData.path
                                color: modelData.problem !== "" ? Theme.danger : Theme.textDim; font.pixelSize: 12
                            }
                        }
                    }
                    Rectangle {
                        anchors { right: parent.right; rightMargin: 16; verticalCenter: parent.verticalCenter }
                        width: 22; height: 22; radius: 11
                        color: parent.sel ? Theme.accent : "transparent"
                        border.color: parent.sel ? Theme.accent : Theme.border; border.width: 2
                        Icon { anchors.centerIn: parent; visible: parent.parent.sel; name: "check"; size: 14 }
                    }
                    MouseArea {
                        id: ma
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: modelData.usable ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: if (modelData.usable) inst.chosen = modelData
                    }
                }
            }
            Hint { visible: inst.disks.length === 0; text: "Kein Laufwerk gefunden. Schließ eine Festplatte an und klick auf „Neu suchen“." }

            Rectangle {
                width: parent.width; height: warnText.implicitHeight + 20; radius: 10
                color: Qt.rgba(1, 0.36, 0.42, 0.12); border.color: Qt.rgba(1, 0.36, 0.42, 0.4)
                Text {
                    id: warnText
                    x: 12; y: 10; width: parent.width - 24
                    text: "Achtung: Alles auf dem gewählten Laufwerk wird gelöscht – auch Windows, wenn es darauf ist."
                    color: Theme.text; font.pixelSize: 13; wrapMode: Text.WordWrap
                }
            }

            Row {
                spacing: 10
                GlimraButton { text: "Zurück"; onClicked: inst.page = 0 }
                GlimraButton {
                    primary: inst.chosen !== null; text: "Weiter"
                    onClicked: if (inst.chosen) { inst.error = ""; inst.page = 2 }
                }
            }
        }

        // ================= 2: Konto
        Column {
            visible: inst.page === 2
            width: parent.width
            spacing: 10

            Text { text: "Dein Konto auf dem neuen System"; color: Theme.text; font.pixelSize: 16; font.weight: Font.DemiBold }
            Grid {
                columns: 2; columnSpacing: 14; rowSpacing: 10
                width: parent.width
                readonly property real cw: (width - columnSpacing) / 2
                Column { spacing: 4; width: parent.cw
                    Hint { text: "Benutzername" }
                    GlimraField { id: fUser; width: parent.width; placeholderText: "z. B. leon"; text: (backend.settings.name || "").toLowerCase().replace(/[^a-z0-9_-]/g, "") }
                }
                Column { spacing: 4; width: parent.cw
                    Hint { text: "Name des PCs" }
                    GlimraField { id: fHost; width: parent.width; placeholderText: "z. B. leon-pc"; text: inst.server ? "glimra-server" : "glimra-pc" }
                }
                Column { spacing: 4; width: parent.cw
                    Hint { text: "Passwort" }
                    GlimraField { id: fPw1; width: parent.width; echoMode: TextInput.Password; placeholderText: "Passwort" }
                }
                Column { spacing: 4; width: parent.cw
                    Hint { text: "Passwort wiederholen" }
                    GlimraField { id: fPw2; width: parent.width; echoMode: TextInput.Password; placeholderText: "noch einmal" }
                }
                Column { spacing: 4; width: parent.cw; visible: inst.server
                    Hint { text: "Passwort für das Glimra Panel (mind. 8 Zeichen)" }
                    GlimraField { id: fPanel; width: parent.width; echoMode: TextInput.Password }
                }
            }
            Hint { width: parent.width; text: "Mit diesem Passwort meldest du dich an und bestätigst Änderungen am System." }
            Text { visible: inst.error !== ""; text: inst.error; color: Theme.danger; font.pixelSize: 13; width: parent.width; wrapMode: Text.WordWrap }

            Row {
                spacing: 10
                GlimraButton { text: "Zurück"; onClicked: inst.page = 1 }
                GlimraButton {
                    primary: true; text: "Weiter"
                    onClicked: {
                        inst.error = backend.installerCheck(fHost.text, fUser.text, fPw1.text, fPw2.text, inst.server ? fPanel.text : "")
                        if (inst.error === "") { confirmBox.checked = false; inst.page = 3 }
                    }
                }
            }
        }

        // ================= 3: Bestätigen
        Column {
            visible: inst.page === 3
            width: parent.width
            spacing: 12

            Text { text: "Alles bereit"; color: Theme.text; font.pixelSize: 16; font.weight: Font.DemiBold }
            Card {
                width: parent.width
                Column {
                    width: parent.width
                    spacing: 8
                    Repeater {
                        model: [
                            ["Laufwerk", inst.chosen ? inst.chosen.model + " (" + inst.chosen.sizeText + ", " + inst.chosen.path + ")" : ""],
                            ["Version", "Glimra OS " + backend.version + " " + (inst.server ? "Server" : "Desktop")],
                            ["Benutzer", fUser.text],
                            ["PC-Name", fHost.text],
                            ["Dauer", "ca. 10–30 Minuten, je nach Internet"]
                        ]
                        Row {
                            required property var modelData
                            spacing: 10
                            Text { width: 110; text: modelData[0]; color: Theme.textDim; font.pixelSize: 13 }
                            Text { text: modelData[1]; color: Theme.text; font.pixelSize: 13 }
                        }
                    }
                }
            }
            Row {
                spacing: 10
                Rectangle {
                    id: confirmBox
                    property bool checked: false
                    width: 22; height: 22; radius: 6
                    color: checked ? Theme.danger : "transparent"
                    border.color: checked ? Theme.danger : Theme.border; border.width: 2
                    Icon { anchors.centerIn: parent; visible: confirmBox.checked; name: "check"; size: 14 }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: confirmBox.checked = !confirmBox.checked }
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Ja, alle Daten auf " + (inst.chosen ? inst.chosen.path : "") + " dürfen gelöscht werden."
                    color: Theme.text; font.pixelSize: 13
                    MouseArea { anchors.fill: parent; onClicked: confirmBox.checked = !confirmBox.checked }
                }
            }
            Row {
                spacing: 10
                GlimraButton { text: "Zurück"; onClicked: inst.page = 2 }
                GlimraButton {
                    danger: confirmBox.checked; icon: "download"; text: "Jetzt installieren"
                    onClicked: {
                        if (!confirmBox.checked) { backend.toast("Bitte erst das Löschen bestätigen"); return }
                        inst.running = true; inst.step = 0; inst.stepText = "Wird gestartet …"; inst.lastLog = ""
                        inst.page = 4
                        backend.startInstall(inst.chosen.path, fHost.text, fUser.text, fPw1.text, inst.server ? fPanel.text : "")
                        fPw1.text = ""; fPw2.text = ""; fPanel.text = ""
                    }
                }
            }
        }

        // ================= 4: Installation läuft
        Column {
            visible: inst.page === 4
            width: parent.width
            spacing: 14

            Item { width: 1; height: 10 }
            Text { text: "Glimra OS wird installiert"; color: Theme.text; font.pixelSize: 18; font.weight: Font.DemiBold }
            Hint { text: "Schritt " + Math.max(inst.step, 1) + " von " + inst.steps + ":  " + inst.stepText }
            Rectangle {
                width: parent.width; height: 10; radius: 5; color: Theme.card
                Rectangle {
                    height: parent.height; radius: 5; color: Theme.accent
                    width: parent.width * Math.max(0.03, (inst.step - 0.5) / inst.steps)
                    Behavior on width { NumberAnimation { duration: 400 } }
                }
            }
            Text { text: inst.lastLog; color: Theme.textDim; font.pixelSize: 11; font.family: "monospace"; width: parent.width; elide: Text.ElideRight }
            Hint { width: parent.width; text: "Bitte den PC nicht ausschalten und den USB-Stick nicht abziehen. Du kannst nebenbei weiter im Internet surfen." }
        }

        // ================= 5: Fertig / Fehler
        Column {
            visible: inst.page === 5
            width: parent.width
            spacing: 14

            Item { width: 1; height: 10 }
            Rectangle {
                width: 64; height: 64; radius: 32
                color: inst.success ? Qt.rgba(0.29, 0.82, 0.58, 0.2) : Qt.rgba(1, 0.36, 0.42, 0.2)
                Icon { anchors.centerIn: parent; name: inst.success ? "check" : "close"; size: 30 }
            }
            Text {
                text: inst.success ? "Fertig! Glimra OS ist installiert." : "Die Installation hat nicht geklappt"
                color: Theme.text; font.pixelSize: 18; font.weight: Font.DemiBold
            }
            Hint {
                width: parent.width
                text: inst.success
                    ? "Starte den PC neu und zieh den USB-Stick ab, sobald der Bildschirm schwarz wird. Danach startet Glimra OS direkt von der Festplatte."
                    : inst.resultText + "\nDas ausführliche Protokoll liegt unter /run/user/0/glimra-install.log. Auf dem Laufwerk kann jetzt ein halbes System sein – einfach noch einmal installieren."
            }
            Row {
                spacing: 10
                GlimraButton { visible: inst.success; primary: true; icon: "reboot"; text: "Jetzt neu starten"; onClicked: backend.power("reboot") }
                GlimraButton { visible: !inst.success; primary: true; icon: "refresh"; text: "Noch einmal"; onClicked: { inst.page = 0; inst.checkNet() } }
            }
        }
    }
}
