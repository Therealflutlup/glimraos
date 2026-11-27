import QtQuick

Rectangle {
    default property alias content: inner.data
    property int pad: 16
    radius: 12
    color: Theme.card
    border.color: Theme.border
    implicitHeight: inner.childrenRect.height + pad * 2
    Item {
        id: inner
        x: parent.pad; y: parent.pad
        width: parent.width - parent.pad * 2
        height: childrenRect.height
    }
}
