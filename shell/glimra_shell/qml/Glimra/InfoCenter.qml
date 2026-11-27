import QtQuick
import QtQuick.Controls

// Info-Center (Win+N): Benachrichtigungen und Kalender
Popup {
    id: ic
    width: 380
    padding: 16
    property var model: null       // ListModel mit {text, time}
    property date shown: new Date()
    onOpened: shown = new Date()
    background: Rectangle { radius: 16; color: Theme.panelSolid; border.color: Theme.border }

    function daysGrid() {
        const y = shown.getFullYear(), m = shown.getMonth()
        const first = (new Date(y, m, 1).getDay() + 6) % 7   // Montag zuerst
        const days = new Date(y, m + 1, 0).getDate()
        const cells = []
        for (let i = 0; i < first; i++) cells.push(0)
        for (let d = 1; d <= days; d++) cells.push(d)
        return cells
    }

    contentItem: Column {
        spacing: 12
        Row {
            width: 348
            Text { text: "Benachrichtigungen"; color: Theme.text; font.pixelSize: 15; font.weight: Font.DemiBold; width: parent.width - 110; anchors.verticalCenter: parent.verticalCenter }
            GlimraButton { text: "Alle löschen"; implicitHeight: 30; onClicked: ic.model.clear() }
        }
        Text { visible: !ic.model || ic.model.count === 0; text: "Keine neuen Benachrichtigungen"; color: Theme.textDim; font.pixelSize: 13 }
        ListView {
            visible: !!ic.model && ic.model.count > 0
            width: 348; height: Math.min(contentHeight, 240)
            clip: true; spacing: 6
            model: ic.model
            delegate: Rectangle {
                required property string text
                required property string time
                width: 348; height: nt.height + 30; radius: 10; color: Theme.card
                Text { id: nt; x: 12; y: 8; width: parent.width - 24; text: parent.text; wrapMode: Text.WordWrap; color: Theme.text; font.pixelSize: 13 }
                Text { x: 12; anchors.bottom: parent.bottom; anchors.bottomMargin: 5; text: parent.time; color: Theme.textDim; font.pixelSize: 11 }
            }
        }
        Rectangle { width: 348; height: 1; color: Theme.border }
        Row {
            width: 348
            Text { text: Qt.formatDate(ic.shown, "MMMM yyyy"); color: Theme.text; font.pixelSize: 15; font.weight: Font.DemiBold; width: parent.width - 80; anchors.verticalCenter: parent.verticalCenter }
            IconButton { icon: "chevron"; rotation: 180; size: 32; iconSize: 14; onClicked: ic.shown = new Date(ic.shown.getFullYear(), ic.shown.getMonth() - 1, 1) }
            IconButton { icon: "chevron"; size: 32; iconSize: 14; onClicked: ic.shown = new Date(ic.shown.getFullYear(), ic.shown.getMonth() + 1, 1) }
        }
        Grid {
            columns: 7; spacing: 4
            Repeater {
                model: ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
                delegate: Text { required property string modelData; width: 46; horizontalAlignment: Text.AlignHCenter; text: modelData; color: Theme.textDim; font.pixelSize: 11 }
            }
            Repeater {
                model: ic.daysGrid()
                delegate: Rectangle {
                    required property int modelData
                    readonly property bool today: modelData > 0 && modelData === new Date().getDate()
                        && ic.shown.getMonth() === new Date().getMonth() && ic.shown.getFullYear() === new Date().getFullYear()
                    width: 46; height: 32; radius: 16
                    color: today ? Theme.accent : "transparent"
                    Text { anchors.centerIn: parent; text: modelData > 0 ? modelData : ""; color: Theme.text; font.pixelSize: 13 }
                }
            }
        }
    }
}
