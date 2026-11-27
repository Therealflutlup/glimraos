import QtQuick
import QtQuick.Controls

// Glimra Store: Programme finden, installieren und entfernen
Item {
    id: st
    property var featured: []
    property var results: []
    property bool searching: false
    property string busy: ""
    property string category: "Alle"
    readonly property var cats: ["Alle", "Internet", "Büro", "Medien", "Kreativ", "Spiele", "Entwicklung"]

    Component.onCompleted: backend.requestFeatured()
    Connections {
        target: backend
        function onListReady(kind, items) {
            if (kind === "featured") st.featured = items
            if (kind === "store") { st.results = items; st.searching = false }
        }
        function onTaskDone(kind, ok, text) {
            if (kind === "install" || kind === "remove") { st.busy = ""; backend.toast(text); backend.requestFeatured(); if (search.text.length > 1) backend.storeSearch(search.text) }
        }
    }

    Column {
        anchors.fill: parent
        anchors.margins: 22
        spacing: 14

        Row {
            width: parent.width
            PageHeader { title: "Glimra Store"; subtitle: "Programme und Spiele installieren"; icon: "bag"; colors: ["#2ed3a1", "#5b8cff"]; width: parent.width - 300 }
            GlimraField {
                id: search
                width: 300
                leftPadding: 38
                placeholderText: "Apps suchen, z. B. Discord"
                onAccepted: if (text.length > 1) { st.searching = true; st.results = []; backend.storeSearch(text) }
                onTextChanged: if (text.length === 0) st.results = []
                Icon { name: "search"; size: 16; x: 12; anchors.verticalCenter: parent.verticalCenter; opacity: 0.7 }
            }
        }

        Row {
            visible: search.text.length === 0
            spacing: 6
            Repeater {
                model: st.cats
                delegate: Rectangle {
                    required property string modelData
                    width: cl.implicitWidth + 26; height: 32; radius: 16
                    color: st.category === modelData ? Theme.accent : (cma.containsMouse ? Theme.hover : Theme.card)
                    Text { id: cl; anchors.centerIn: parent; text: modelData; color: Theme.text; font.pixelSize: 13 }
                    MouseArea { id: cma; anchors.fill: parent; hoverEnabled: true; onClicked: st.category = modelData }
                }
            }
        }

        Text { visible: st.searching; text: "Suche …"; color: Theme.textDim; font.pixelSize: 13 }

        GridView {
            id: grid
            width: parent.width
            height: parent.height - 120
            clip: true
            cellWidth: width > 760 ? Math.floor(width / 2) : width; cellHeight: 86
            ScrollBar.vertical: ScrollBar {}
            model: search.text.length > 1 ? st.results : st.featured.filter(f => st.category === "Alle" || f.cat === st.category)
            delegate: Item {
                required property var modelData
                width: grid.cellWidth; height: grid.cellHeight
                Rectangle {
                    anchors.fill: parent; anchors.margins: 5
                    radius: 12; color: Theme.card; border.color: Theme.border
                    Row {
                        x: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 12
                        AppIcon { icon: modelData.icon || "apps"; size: 44; colors: modelData.id.indexOf("flatpak:") === 0 ? ["#a06bff", "#6b3cff"] : ["#5b8cff", "#3a5bd9"]; anchors.verticalCenter: parent.verticalCenter }
                        Column {
                            width: grid.cellWidth - 220; anchors.verticalCenter: parent.verticalCenter
                            Text { text: modelData.name; color: Theme.text; font.pixelSize: 14; font.weight: Font.DemiBold; width: parent.width; elide: Text.ElideRight }
                            Text { text: modelData.desc; color: Theme.textDim; font.pixelSize: 12; width: parent.width; elide: Text.ElideRight }
                            Text { text: modelData.cat; color: Theme.textDim; font.pixelSize: 11; opacity: 0.8 }
                        }
                    }
                    GlimraButton {
                        anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter
                        implicitHeight: 34
                        primary: !modelData.installed
                        danger: false
                        text: st.busy === modelData.id ? "…" : modelData.installed ? "Entfernen" : "Installieren"
                        onClicked: {
                            if (st.busy) return
                            st.busy = modelData.id
                            modelData.installed ? backend.storeRemove(modelData.id) : backend.storeInstall(modelData.id)
                            if (!backend.isLumen) st.busy = ""
                        }
                    }
                }
            }
        }
    }
}
