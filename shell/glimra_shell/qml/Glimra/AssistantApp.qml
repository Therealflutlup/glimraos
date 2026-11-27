import QtQuick
import QtQuick.Controls

// Glimra Assistent: tippen oder sprechen
Item {
    id: asst
    signal openApp(string id)
    property bool listening: false
    property string pendingPower: ""
    ListModel { id: chat }

    Component.onCompleted: chat.append({ me: false, text: "Hallo" + (backend.settings.name ? " " + backend.settings.name : "") + "! Frag mich etwas oder sag „Öffne den Browser“." })

    Connections {
        target: backend
        function onAssistantReply(heard, reply, action, value) {
            asst.listening = false
            if (heard) chat.append({ me: true, text: heard })
            chat.append({ me: false, text: reply })
            if (action === "open") asst.openApp(value)
            if (action === "confirm") asst.pendingPower = value
            list.positionViewAtEnd()
        }
    }

    function send() {
        if (!input.text.trim()) return
        const t = input.text
        input.text = ""
        backend.ask(t)
    }

    PageHeader {
        id: head
        x: 20; y: 18
        title: "Glimra Assistent"
        subtitle: backend.voiceAvailable() ? "Tippen oder auf das Mikrofon klicken" : "Tippen – Sprache: Profil „Assistent“ installieren"
        icon: "assistant"; colors: ["#a06bff", "#6b3cff"]
    }

    ListView {
        id: list
        anchors { top: head.bottom; topMargin: 16; left: parent.left; right: parent.right; bottom: confirmBar.top; margins: 20 }
        spacing: 10
        clip: true
        model: chat
        ScrollBar.vertical: ScrollBar {}
        delegate: Item {
            required property bool me
            required property string text
            width: ListView.view.width
            height: bubble.height
            Rectangle {
                id: bubble
                anchors.right: me ? parent.right : undefined
                width: Math.min(msg.implicitWidth + 28, parent.width * 0.8)
                height: msg.height + 20
                radius: 14
                color: me ? Theme.accent : Theme.card
                border.color: me ? "transparent" : Theme.border
                Text {
                    id: msg
                    x: 14; y: 10
                    width: parent.width - 28
                    text: parent.parent.text
                    wrapMode: Text.WordWrap
                    color: Theme.text; font.pixelSize: 14; font.family: Theme.fontFamily
                }
            }
        }
    }

    Row {
        id: confirmBar
        visible: asst.pendingPower !== ""
        height: visible ? 46 : 0
        anchors { left: parent.left; leftMargin: 20; bottom: inputRow.top; bottomMargin: 8 }
        spacing: 10
        GlimraButton { danger: true; icon: "power"; text: asst.pendingPower === "reboot" ? "Ja, neu starten" : "Ja, ausschalten"; onClicked: { backend.power(asst.pendingPower); asst.pendingPower = "" } }
        GlimraButton { text: "Abbrechen"; onClicked: asst.pendingPower = "" }
    }

    Row {
        id: inputRow
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 20 }
        spacing: 8
        GlimraField {
            id: input
            width: parent.width - 100
            placeholderText: "Nachricht an den Assistenten …"
            onAccepted: asst.send()
        }
        Rectangle {
            width: 42; height: 40; radius: 10
            color: asst.listening ? Theme.danger : (mma.containsMouse ? Theme.hover : Theme.card)
            border.color: Theme.border
            opacity: backend.voiceAvailable() ? 1 : 0.4
            Icon { anchors.centerIn: parent; name: "mic"; size: 18 }
            MouseArea {
                id: mma; anchors.fill: parent; hoverEnabled: true
                onClicked: {
                    if (!backend.voiceAvailable()) { backend.toast("Sprache: In Einstellungen → Nutzungsprofil das Profil „Assistent“ installieren."); return }
                    asst.listening = true
                    chat.append({ me: false, text: "Ich höre zu … (5 Sekunden)" })
                    backend.listen()
                }
            }
        }
        Rectangle {
            width: 42; height: 40; radius: 10
            color: sma.containsMouse ? Qt.lighter(Theme.accent, 1.1) : Theme.accent
            Icon { anchors.centerIn: parent; name: "send"; size: 18 }
            MouseArea { id: sma; anchors.fill: parent; hoverEnabled: true; onClicked: asst.send() }
        }
    }
}
