import QtQuick

Rectangle {
    id: btn
    property string text: ""
    property string icon: ""
    property bool primary: false
    property bool danger: false
    signal clicked()

    implicitWidth: Math.max(110, label.implicitWidth + 32 + (icon ? 26 : 0))
    implicitHeight: 38
    radius: 9
    color: danger ? (ma.containsMouse ? "#ff7480" : Theme.danger)
         : primary ? (ma.containsMouse ? Qt.lighter(Theme.accent, 1.15) : Theme.accent)
         : (ma.containsMouse ? Theme.hover : Theme.card)
    border.color: primary || danger ? "transparent" : Theme.border

    Row {
      anchors.centerIn: parent
      spacing: 8
      Icon { visible: btn.icon !== ""; name: btn.icon; size: 16; anchors.verticalCenter: parent.verticalCenter }
      Text {
        id: label
        anchors.verticalCenter: parent.verticalCenter
        text: btn.text
        color: Theme.text
        font.pixelSize: 14
        font.weight: btn.primary ? Font.DemiBold : Font.Normal
        font.family: Theme.fontFamily
      }
    }
    MouseArea {
        id: ma
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: btn.clicked()
    }
}
