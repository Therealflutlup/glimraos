import QtQuick
import QtQuick.Controls

TextField {
    id: field
    implicitHeight: 40
    color: Theme.text
    placeholderTextColor: Theme.textDim
    font.pixelSize: 14
    font.family: Theme.fontFamily
    leftPadding: 12
    selectByMouse: true
    background: Rectangle {
        radius: 9
        color: Theme.card
        border.color: field.activeFocus ? Theme.accent : Theme.border
        border.width: field.activeFocus ? 2 : 1
    }
}
