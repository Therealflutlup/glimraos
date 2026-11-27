import QtQuick
import QtQuick.Controls

Slider {
    id: sl
    implicitHeight: 28
    background: Rectangle {
        x: sl.leftPadding; y: sl.topPadding + sl.availableHeight / 2 - height / 2
        width: sl.availableWidth; height: 6; radius: 3
        color: Theme.border
        Rectangle { width: sl.visualPosition * parent.width; height: parent.height; radius: 3; color: Theme.accent }
    }
    handle: Rectangle {
        x: sl.leftPadding + sl.visualPosition * (sl.availableWidth - width)
        y: sl.topPadding + sl.availableHeight / 2 - height / 2
        width: 18; height: 18; radius: 9
        color: "white"
        border.color: Theme.accent; border.width: 2
    }
}
