import QtQuick

Row {
    property string title: ""
    property string subtitle: ""
    property string icon: ""
    property var colors: ["#5b8cff", "#3a5bd9"]
    spacing: 14
    AppIcon { visible: parent.icon !== ""; icon: parent.icon; colors: parent.colors; size: 46; anchors.verticalCenter: parent.verticalCenter }
    Column {
        anchors.verticalCenter: parent.verticalCenter
        spacing: 2
        Text { text: title; color: Theme.text; font.pixelSize: 22; font.weight: Font.DemiBold; font.family: Theme.fontFamily }
        Text { visible: subtitle !== ""; text: subtitle; color: Theme.textDim; font.pixelSize: 13; font.family: Theme.fontFamily }
    }
}
