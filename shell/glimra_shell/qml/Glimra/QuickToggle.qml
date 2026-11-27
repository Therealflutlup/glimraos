import QtQuick

// Kachel in den Schnelleinstellungen (wie bei Windows 11)
Rectangle {
    id: qt
    property string icon: "wifi"
    property string label: ""
    property string sub: ""
    property bool on: false
    property bool enabledTile: true
    signal toggled()
    signal more()
    width: 132; height: 72; radius: 12
    opacity: enabledTile ? 1 : 0.45
    color: on ? Theme.accent : (tma.containsMouse ? Theme.hover : Theme.card)
    border.color: on ? "transparent" : Theme.border
    Column {
        x: 12; anchors.verticalCenter: parent.verticalCenter
        spacing: 4
        Icon { name: qt.icon; size: 18 }
        Text { text: qt.label; color: Theme.text; font.pixelSize: 13; font.weight: Font.DemiBold; font.family: Theme.fontFamily; width: qt.width - 40; elide: Text.ElideRight }
        Text { visible: qt.sub !== ""; text: qt.sub; color: qt.on ? "#e6ecff" : Theme.textDim; font.pixelSize: 11; width: qt.width - 40; elide: Text.ElideRight }
    }
    MouseArea { id: tma; anchors.fill: parent; hoverEnabled: true; enabled: qt.enabledTile; onClicked: qt.toggled() }
    Rectangle {
        visible: qt.enabledTile
        anchors { right: parent.right; top: parent.top; bottom: parent.bottom }
        width: 30; radius: 12; color: "transparent"
        Icon { anchors.centerIn: parent; name: "chevron"; size: 14; opacity: 0.8 }
        MouseArea { anchors.fill: parent; onClicked: qt.more() }
    }
}
