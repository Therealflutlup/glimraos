import QtQuick

// Alt + Tab: zwischen offenen Fenstern wechseln
Rectangle {
    id: sw
    property var windows: []
    property int index: 0
    signal chosen(var w)
    visible: false
    width: Math.min(parent ? parent.width - 80 : 800, Math.max(260, windows.length * 170 + 32))
    height: 170
    radius: 18
    color: Theme.panelSolid
    border.color: Theme.border

    function next() {
        if (windows.length === 0) return
        if (!visible) { index = windows.length > 1 ? 1 : 0; visible = true }
        else index = (index + 1) % windows.length
        commit.restart()
    }
    Timer { id: commit; interval: 900; onTriggered: { sw.visible = false; if (sw.windows[sw.index]) sw.chosen(sw.windows[sw.index]) } }

    Row {
        anchors.centerIn: parent
        spacing: 12
        Repeater {
            model: sw.windows
            delegate: Rectangle {
                required property var modelData
                required property int index
                width: 158; height: 132; radius: 12
                color: index === sw.index ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.22) : Theme.card
                border.color: index === sw.index ? Theme.accent : Theme.border
                border.width: index === sw.index ? 2 : 1
                Column {
                    anchors.centerIn: parent
                    spacing: 10
                    Icon { anchors.horizontalCenter: parent.horizontalCenter; name: modelData.icon; size: 40 }
                    Text { width: 140; horizontalAlignment: Text.AlignHCenter; elide: Text.ElideRight; text: modelData.title; color: Theme.text; font.pixelSize: 13 }
                }
                MouseArea { anchors.fill: parent; onClicked: { commit.stop(); sw.visible = false; sw.chosen(modelData) } }
            }
        }
    }
}
