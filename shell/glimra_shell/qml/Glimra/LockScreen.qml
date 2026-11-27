import QtQuick

// Sperrbildschirm – über Startmenü, Rechtsklick, Assistent oder die GlimraApp
Item {
    id: lock
    signal unlocked()
    property string now: ""
    property string today: ""

    onVisibleChanged: if (visible) { pin.text = ""; err.text = ""; pin.forceActiveFocus() }

    Wallpaper { anchors.fill: parent; key: backend.settings.wallpaper || "aurora" }
    Rectangle { anchors.fill: parent; color: "#99070912" }
    MouseArea { anchors.fill: parent; onClicked: pin.forceActiveFocus() }

    Timer {
        interval: 1000; running: lock.visible; repeat: true; triggeredOnStart: true
        onTriggered: { const d = new Date(); lock.now = Qt.formatTime(d, "HH:mm"); lock.today = Qt.formatDate(d, "dddd, d. MMMM") }
    }

    Column {
        anchors.horizontalCenter: parent.horizontalCenter
        y: parent.height * 0.16
        spacing: 6
        Text { anchors.horizontalCenter: parent.horizontalCenter; text: lock.now; color: Theme.text; font.pixelSize: 96; font.weight: Font.Light; font.family: Theme.fontFamily }
        Text { anchors.horizontalCenter: parent.horizontalCenter; text: lock.today; color: Theme.textDim; font.pixelSize: 20; font.family: Theme.fontFamily }
    }

    Column {
        anchors.horizontalCenter: parent.horizontalCenter
        y: parent.height * 0.55
        spacing: 14
        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 76; height: 76; radius: 38
            gradient: Gradient { GradientStop { position: 0; color: Theme.accent } GradientStop { position: 1; color: Theme.accent2 } }
            Text { anchors.centerIn: parent; text: (backend.settings.name || "L").charAt(0).toUpperCase(); color: "white"; font.pixelSize: 32; font.weight: Font.Bold }
        }
        Text { anchors.horizontalCenter: parent.horizontalCenter; text: backend.settings.name || "Glimra-Nutzer"; color: Theme.text; font.pixelSize: 20; font.family: Theme.fontFamily }
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 8
            GlimraField {
                id: pin
                visible: backend.hasPin()
                width: 220
                echoMode: TextInput.Password
                placeholderText: "PIN eingeben"
                horizontalAlignment: TextInput.AlignHCenter
                onAccepted: unlockBtn.clicked()
            }
            GlimraButton {
                id: unlockBtn
                primary: true
                icon: "lock"
                text: "Entsperren"
                onClicked: {
                    if (backend.checkPin(pin.text)) lock.unlocked()
                    else { err.text = "Falsche PIN"; pin.text = "" }
                }
            }
        }
        Text { id: err; anchors.horizontalCenter: parent.horizontalCenter; color: Theme.danger; font.pixelSize: 14 }
    }
}
