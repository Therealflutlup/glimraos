import QtQuick
import QtQuick.Controls

// Zwischenablage-Verlauf (Win+V)
Popup {
    id: cp
    width: 380
    height: Math.min(460, 90 + backend.clipHistory.length * 64)
    padding: 14
    background: Rectangle { radius: 16; color: Theme.panelSolid; border.color: Theme.border }
    contentItem: Column {
        spacing: 10
        Row {
            width: 352
            Text { text: "Zwischenablage"; color: Theme.text; font.pixelSize: 15; font.weight: Font.DemiBold; width: parent.width - 110; anchors.verticalCenter: parent.verticalCenter }
            GlimraButton { text: "Alle löschen"; implicitHeight: 30; onClicked: backend.clipboardClear() }
        }
        Text { visible: backend.clipHistory.length === 0; width: 352; wrapMode: Text.WordWrap; text: "Noch nichts kopiert. Kopierte Texte erscheinen hier (Win + V)."; color: Theme.textDim; font.pixelSize: 13 }
        ListView {
            width: 352; height: cp.height - 80
            clip: true; spacing: 6
            model: backend.clipHistory
            delegate: Rectangle {
                required property string modelData
                required property int index
                width: 352; height: 56; radius: 10
                color: cm.containsMouse ? Theme.hover : Theme.card
                Text { x: 12; width: parent.width - 24; anchors.verticalCenter: parent.verticalCenter; text: modelData.replace(/\s+/g, " "); maximumLineCount: 2; wrapMode: Text.Wrap; elide: Text.ElideRight; color: Theme.text; font.pixelSize: 13 }
                MouseArea { id: cm; anchors.fill: parent; hoverEnabled: true; onClicked: { backend.clipboardPick(index); backend.toast("Kopiert – mit Strg + V einfügen."); cp.close() } }
            }
        }
    }
}
