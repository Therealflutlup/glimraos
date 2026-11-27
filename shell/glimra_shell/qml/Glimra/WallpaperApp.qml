import QtQuick
import QtQuick.Controls

Item {
    id: wpApp
    property var images: backend.wallpaperImages()

    Flickable {
        anchors.fill: parent
        anchors.margins: 22
        contentHeight: col.height
        clip: true
        ScrollBar.vertical: ScrollBar {}
        Column {
            id: col
            width: parent.width
            spacing: 16
            PageHeader { title: "Hintergrundbild"; subtitle: "Glimra-Farbverläufe oder eigene Bilder aus „Bilder“"; icon: "image"; colors: ["#ff8fa3", "#e0566f"] }
            Grid {
                columns: 3
                spacing: 14
                Repeater {
                    model: [ { k: "aurora", n: "Aurora" }, { k: "sunset", n: "Sonnenuntergang" }, { k: "ocean", n: "Ozean" },
                             { k: "forest", n: "Wald" }, { k: "night", n: "Nacht" }, { k: "auto", n: "Automatisch (Tageszeit)" } ]
                    delegate: Column {
                        required property var modelData
                        spacing: 6
                        Rectangle {
                            width: (col.width - 28) / 3; height: width * 0.6; radius: 12
                            clip: true
                            border.color: backend.settings.wallpaper === modelData.k ? Theme.accent : Theme.border
                            border.width: backend.settings.wallpaper === modelData.k ? 3 : 1
                            color: "transparent"
                            Wallpaper { anchors.fill: parent; anchors.margins: 3; key: modelData.k }
                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: backend.setSetting("wallpaper", modelData.k) }
                        }
                        Text { text: modelData.n; color: Theme.text; font.pixelSize: 13; font.family: Theme.fontFamily }
                    }
                }
            }
            Text { visible: wpApp.images.length > 0; text: "Eigene Bilder"; color: Theme.textDim; font.pixelSize: 12; font.weight: Font.DemiBold }
            Grid {
                columns: 3
                spacing: 14
                Repeater {
                    model: wpApp.images
                    delegate: Rectangle {
                        required property string modelData
                        width: (col.width - 28) / 3; height: width * 0.6; radius: 12; clip: true
                        color: Theme.card
                        border.color: backend.settings.wallpaper === modelData ? Theme.accent : Theme.border
                        border.width: backend.settings.wallpaper === modelData ? 3 : 1
                        Image { anchors.fill: parent; anchors.margins: 3; source: "file://" + modelData; fillMode: Image.PreserveAspectCrop; asynchronous: true; sourceSize.width: 400 }
                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: backend.setSetting("wallpaper", modelData) }
                    }
                }
            }
        }
    }
}
