import QtQuick

Rectangle {
    id: ib
    property string icon: "apps"
    property int size: 38
    property int iconSize: 18
    property bool danger: false
    property string tip: ""
    signal clicked()
    width: size
    height: size
    radius: 9
    color: ma.containsMouse ? (danger ? Theme.danger : Theme.hover) : "transparent"
    Icon { anchors.centerIn: parent; name: ib.icon; size: ib.iconSize }
    MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: ib.clicked() }
}
