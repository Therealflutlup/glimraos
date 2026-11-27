import QtQuick

// Ein Symbol aus dem eigenen Glimra-Symbolset (icons/*.svg)
Image {
    property string name: "apps"
    property int size: 20
    width: size
    height: size
    source: name ? Qt.resolvedUrl("icons/" + name + ".svg") : ""
    sourceSize: Qt.size(size * 2, size * 2)
    fillMode: Image.PreserveAspectFit
    smooth: true
}
