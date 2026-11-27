import QtQuick
import QtQuick.Controls

Item {
    id: tm
    property var procs: backend.processes()
    property var info: backend.systemInfo()
    property int selected: -1

    Timer { interval: 3000; running: tm.visible; repeat: true; onTriggered: { tm.procs = backend.processes(); tm.info = backend.systemInfo() } }

    Column {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        Row {
            width: parent.width
            Column {
                width: parent.width - 120
                Text { text: "Taskmanager"; color: Theme.text; font.pixelSize: 22; font.weight: Font.DemiBold; font.family: Theme.fontFamily }
                Text { text: "RAM: " + (tm.info.ramUsed ? tm.info.ramUsed + " / " + tm.info.ramTotal : "–") + "   ·   " + tm.procs.length + " Prozesse"; color: Theme.textDim; font.pixelSize: 13; font.family: Theme.fontFamily }
            }
            GlimraButton {
                danger: true; text: "Beenden"
                opacity: tm.selected > 0 ? 1 : 0.4
                onClicked: if (tm.selected > 0) { backend.killProcess(tm.selected); tm.selected = -1 }
            }
        }

        Rectangle {
            width: parent.width; height: 32; radius: 8; color: Theme.titleBg
            Row {
                x: 12; anchors.verticalCenter: parent.verticalCenter
                Text { width: 280; text: "Name"; color: Theme.textDim; font.pixelSize: 12; font.weight: Font.DemiBold }
                Text { width: 100; text: "PID"; color: Theme.textDim; font.pixelSize: 12; font.weight: Font.DemiBold }
                Text { width: 120; text: "Arbeitsspeicher"; color: Theme.textDim; font.pixelSize: 12; font.weight: Font.DemiBold }
            }
        }

        ListView {
            width: parent.width
            height: parent.height - 120
            clip: true
            model: tm.procs
            ScrollBar.vertical: ScrollBar {}
            delegate: Rectangle {
                required property var modelData
                width: ListView.view.width; height: 32; radius: 6
                color: tm.selected === modelData.pid ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.22)
                     : (rma.containsMouse ? Theme.hover : "transparent")
                Row {
                    x: 12; anchors.verticalCenter: parent.verticalCenter
                    Text { width: 280; text: modelData.name; color: Theme.text; font.pixelSize: 13; elide: Text.ElideRight }
                    Text { width: 100; text: modelData.pid; color: Theme.textDim; font.pixelSize: 13 }
                    Text { width: 120; text: modelData.mem + " MB"; color: Theme.text; font.pixelSize: 13 }
                }
                MouseArea { id: rma; anchors.fill: parent; hoverEnabled: true; onClicked: tm.selected = modelData.pid }
            }
        }
    }
}
