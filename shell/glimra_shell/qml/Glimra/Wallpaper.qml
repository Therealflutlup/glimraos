import QtQuick

// Hintergrund: Farbverlauf (aurora, ocean …) oder eigenes Bild (Pfad beginnt mit /)
Item {
    id: wp
    property string key: "aurora"
    readonly property bool isImage: key.indexOf("/") === 0
    readonly property var colors: Theme.wallpaperFor(isImage ? "night" : key)

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: wp.colors[0] }
            GradientStop { position: 1.0; color: wp.colors[1] }
        }
    }
    Rectangle {
        visible: !wp.isImage
        x: parent.width * 0.55; y: -parent.height * 0.25
        width: parent.width * 0.7; height: width; radius: width / 2
        color: wp.colors[2]; opacity: 0.10
    }
    Rectangle {
        visible: !wp.isImage
        x: -parent.width * 0.2; y: parent.height * 0.5
        width: parent.width * 0.55; height: width; radius: width / 2
        color: wp.colors[2]; opacity: 0.07
    }
    Image {
        visible: wp.isImage
        anchors.fill: parent
        source: wp.isImage ? "file://" + wp.key : ""
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        sourceSize.width: 1920
    }
}
