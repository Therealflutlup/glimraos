import QtQuick
import QtQuick.Controls

// Hilfe & Support
Item {
    id: help
    signal openApp(string id)
    property int open: -1
    readonly property var faq: [
        { q: "Wie installiere ich Programme?", a: "Über ein Nutzungsprofil (Einstellungen → Nutzungsprofil) oder im Terminal mit „sudo pacman -S name“. Mit dem Profil „Arbeits-Apps“ bekommst du außerdem Flatpak-Apps." },
        { q: "Wie starte ich .exe-Dateien?", a: "Installiere das Gaming-Profil (bringt Wine mit). Danach reicht ein Doppelklick auf die .exe auf dem Desktop." },
        { q: "Steam startet nicht im Fenster?", a: "Steam braucht das Gaming-Profil (gamescope + Steam). Es öffnet sich dann in einem eigenen Glimra-Fenster." },
        { q: "Wie verbinde ich mein Handy?", a: "GlimraApp installieren, im selben WLAN öffnen und den Code aus der App „GlimraApp“ am PC eingeben." },
        { q: "Mein System startet nicht mehr richtig.", a: "Nach zwei fehlgeschlagenen Starts lädt Glimra OS automatisch das letzte Backup. Im Bootmenü kannst du unter „Glimra OS Backups“ auch selbst einen älteren Stand wählen." },
        { q: "Wie ziehe ich von Windows um?", a: "Glimra Setup-Manager (GlimraSetup.exe) auf dem Windows-PC starten → „Daten umziehen“. Danach in Glimra OS die App „Umzug“ öffnen." },
        { q: "Wo melde ich Fehler?", a: "Erstelle unten einen Systembericht und hänge ihn an deine Fehlermeldung im GitHub-Projekt (Issues) an." }
    ]

    Flickable {
        anchors.fill: parent
        anchors.margins: 22
        contentHeight: col.height
        clip: true
        ScrollBar.vertical: ScrollBar {}
        Column {
            id: col
            width: parent.width
            spacing: 10
            PageHeader { title: "Hilfe & Support"; subtitle: "Häufige Fragen und Systembericht"; icon: "help"; colors: ["#5bc0ff", "#2f8fd6"] }
            Item { width: 1; height: 4 }
            Repeater {
                model: help.faq
                delegate: Rectangle {
                    required property var modelData
                    required property int index
                    width: col.width
                    height: help.open === index ? 52 + ans.height + 12 : 52
                    radius: 10; color: Theme.card; border.color: Theme.border; clip: true
                    Behavior on height { NumberAnimation { duration: 150 } }
                    Row {
                        x: 14; y: 16; spacing: 10
                        Icon { name: "chevron"; size: 16; rotation: help.open === index ? 90 : 0 }
                        Text { text: modelData.q; color: Theme.text; font.pixelSize: 14; font.weight: Font.DemiBold }
                    }
                    Text { id: ans; visible: help.open === index; x: 40; y: 48; width: parent.width - 60; wrapMode: Text.WordWrap; text: modelData.a; color: Theme.textDim; font.pixelSize: 13 }
                    MouseArea { anchors.fill: parent; onClicked: help.open = help.open === index ? -1 : index }
                }
            }
            Item { width: 1; height: 6 }
            Row {
                spacing: 10
                GlimraButton { primary: true; icon: "file"; text: "Systembericht erstellen"; onClicked: backend.systemReport() }
                GlimraButton { icon: "assistant"; text: "Assistent fragen"; onClicked: help.openApp("assistant") }
            }
        }
    }
}
