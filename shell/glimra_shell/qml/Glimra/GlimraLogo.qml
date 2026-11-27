import QtQuick

// Das Glimra-Logo: leuchtender Ring mit Glanzpunkt
Item {
    id: logo
    property real size: 120
    property bool glow: true
    width: size; height: size

    Rectangle {
        visible: logo.glow
        anchors.centerIn: parent
        width: logo.size * 1.35; height: width; radius: width / 2
        color: Theme.accent
        opacity: 0.12
    }
    Image {
        anchors.fill: parent
        source: Qt.resolvedUrl("logo.svg")
        sourceSize: Qt.size(logo.size * 2, logo.size * 2)
        smooth: true
    }
}
