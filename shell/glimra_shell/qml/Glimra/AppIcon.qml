import QtQuick

// App-Symbol: farbige Kachel mit weißem Glimra-Symbol
Rectangle {
    id: tile
    property string icon: "apps"
    property var colors: ["#5b8cff", "#3a5bd9"]
    property int size: 44
    width: size
    height: size
    radius: size * 0.28
    gradient: Gradient {
        GradientStop { position: 0.0; color: tile.colors[0] }
        GradientStop { position: 1.0; color: tile.colors[1] }
    }
    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        color: "transparent"
        border.color: Qt.rgba(1, 1, 1, 0.12)
    }
    Icon { anchors.centerIn: parent; name: tile.icon; size: Math.round(tile.size * 0.56) }
}
