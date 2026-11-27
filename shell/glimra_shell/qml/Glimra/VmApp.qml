import QtQuick
import QtQuick.Controls

// Virtuelle PCs (KVM/QEMU) – z. B. Windows oder ein anderes Linux im Fenster
Item {
    id: vmApp
    property bool avail: backend.vmAvailable()
    property var vms: backend.vmList()
    property var isos: backend.isoFiles()
    property int isoIndex: 0
    property bool creating: false

    function refresh() { avail = backend.vmAvailable(); vms = backend.vmList(); isos = backend.isoFiles() }
    Timer { interval: 4000; running: vmApp.visible && vmApp.avail; repeat: true; onTriggered: vmApp.vms = backend.vmList() }
    Connections {
        target: backend
        function onTaskDone(kind, ok, text) {
            if (kind === "vm") { if (text) backend.toast(text); vmApp.creating = false; vmApp.refresh() }
            if (kind === "profile") vmApp.refresh()
        }
    }

    Column {
        anchors.fill: parent
        anchors.margins: 22
        spacing: 14

        PageHeader { title: "Virtuelle PCs"; subtitle: "Andere Betriebssysteme im Fenster ausführen"; icon: "vm"; colors: ["#3fc5f0", "#1f86c9"] }

        Card {
            visible: !vmApp.avail
            width: parent.width
            Column {
                width: parent.width; spacing: 10
                Text { text: "Der VM-Dienst ist noch nicht installiert."; color: Theme.text; font.pixelSize: 14 }
                Text { width: parent.width; wrapMode: Text.WordWrap; text: "Installiert QEMU/KVM, libvirt und den Viewer. Danach einmal ab- und wieder anmelden."; color: Theme.textDim; font.pixelSize: 13 }
                GlimraButton { primary: true; icon: "download"; text: "VM-Dienst installieren"; onClicked: backend.applyProfile("vm") }
            }
        }

        Card {
            visible: vmApp.avail
            width: parent.width
            Column {
                width: parent.width; spacing: 10
                Text { text: "Neuen virtuellen PC erstellen"; color: Theme.text; font.pixelSize: 15; font.weight: Font.DemiBold }
                Row {
                    spacing: 10
                    GlimraField { id: vmName; width: 170; placeholderText: "Name, z. B. Windows11" }
                    GlimraField { id: vmRam; width: 110; placeholderText: "RAM (MB)"; text: "4096" }
                    GlimraField { id: vmDisk; width: 110; placeholderText: "Platte (GB)"; text: "60" }
                }
                Row {
                    spacing: 10
                    Rectangle {
                        width: 400; height: 40; radius: 9; color: Theme.titleBg; border.color: Theme.border
                        Text { x: 12; width: parent.width - 60; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideMiddle; color: vmApp.isos.length ? Theme.text : Theme.textDim; font.pixelSize: 13
                               text: vmApp.isos.length ? vmApp.isos[vmApp.isoIndex] : "Keine ISO in Downloads gefunden" }
                        IconButton { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; size: 34; icon: "chevron"; visible: vmApp.isos.length > 1
                                     onClicked: vmApp.isoIndex = (vmApp.isoIndex + 1) % vmApp.isos.length }
                    }
                    GlimraButton {
                        primary: true; icon: "plus"; text: vmApp.creating ? "Erstelle …" : "Erstellen"
                        onClicked: {
                            if (!vmApp.isos.length) { backend.toast("Lege zuerst eine ISO-Datei in Downloads."); return }
                            vmApp.creating = true
                            backend.vmCreate(vmName.text, vmApp.isos[vmApp.isoIndex], parseInt(vmRam.text) || 4096, parseInt(vmDisk.text) || 60)
                        }
                    }
                }
            }
        }

        ListView {
            visible: vmApp.avail
            width: parent.width
            height: parent.height - 300
            spacing: 6
            clip: true
            model: vmApp.vms
            ScrollBar.vertical: ScrollBar {}
            delegate: Rectangle {
                required property var modelData
                readonly property bool on: modelData.state === "running" || modelData.state === "läuft"
                width: ListView.view.width; height: 54; radius: 10
                color: Theme.card; border.color: Theme.border
                Row {
                    x: 14; anchors.verticalCenter: parent.verticalCenter; spacing: 12
                    Icon { name: "vm"; size: 22; anchors.verticalCenter: parent.verticalCenter }
                    Column {
                        width: vmApp.width - 330; anchors.verticalCenter: parent.verticalCenter
                        Text { text: modelData.name; color: Theme.text; font.pixelSize: 14 }
                        Text { text: parent.parent.parent.on ? "läuft" : "aus"; color: parent.parent.parent.on ? Theme.ok : Theme.textDim; font.pixelSize: 12 }
                    }
                    IconButton { icon: "computer"; onClicked: backend.vmAction(modelData.name, "view") }
                    IconButton { icon: parent.parent.on ? "stop" : "play"; onClicked: backend.vmAction(modelData.name, parent.parent.on ? "shutdown" : "start") }
                    IconButton { icon: "power"; onClicked: backend.vmAction(modelData.name, "destroy") }
                    IconButton { icon: "trash"; danger: true; onClicked: backend.vmAction(modelData.name, "delete") }
                }
            }
        }
    }
}
