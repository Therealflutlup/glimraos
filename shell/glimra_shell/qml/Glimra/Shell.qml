import QtQuick
import QtQuick.Controls

// Die komplette Glimra-Oberfläche: Hintergrund, Desktop, Fenster, Taskleiste.
Item {
    id: shell
    anchors.fill: parent

    property var windows: []
    property var activeWindow: null
    property int topZ: 1
    property int cascade: 0
    property bool locked: false

    // ---------------- Apps (eigene Symbole aus icons/)
    readonly property var apps: allApps.filter(a => !a.liveOnly || backend.isLive)
    readonly property var allApps: [
        { id: "installer", name: "Vollversion installieren", icon: "drive", colors: ["#5b8cff", "#a06bff"], internal: true, size: [800, 620], liveOnly: true },
        { id: "settings",  name: "Einstellungen", icon: "settings",  colors: ["#5b8cff", "#3a5bd9"], internal: true, size: [860, 640] },
        { id: "assistant", name: "Assistent",     icon: "assistant", colors: ["#a06bff", "#6b3cff"], internal: true, size: [560, 600] },
        { id: "remote",    name: "GlimraApp",      icon: "phone",     colors: ["#2ed3a1", "#159c78"], internal: true, size: [640, 560] },
        { id: "security",  name: "Sicherheit",    icon: "shield",    colors: ["#ff6b6b", "#d63b4f"], internal: true, size: [680, 560] },
        { id: "backup",    name: "Backups",       icon: "backup",    colors: ["#ffb347", "#e07b1a"], internal: true, size: [720, 560] },
        { id: "vm",        name: "Virtuelle PCs", icon: "vm",        colors: ["#3fc5f0", "#1f86c9"], internal: true, size: [760, 580] },
        { id: "transfer",  name: "Umzug",         icon: "transfer",  colors: ["#f06bd0", "#b13fa0"], internal: true, size: [700, 560] },
        { id: "tools",     name: "Tools",         icon: "tools",     colors: ["#6c7cff", "#4250d6"], internal: true, size: [720, 540] },
        { id: "taskman",   name: "Taskmanager",   icon: "taskman",   colors: ["#4ad295", "#249e66"], internal: true, size: [660, 560] },
        { id: "wallpaper", name: "Hintergrund",   icon: "image",     colors: ["#ff8fa3", "#e0566f"], internal: true, size: [720, 520] },
        { id: "calc",      name: "Rechner",       icon: "calc",      colors: ["#8a94b8", "#5a6386"], internal: true, size: [340, 480] },
        { id: "help",      name: "Hilfe",         icon: "help",      colors: ["#5bc0ff", "#2f8fd6"], internal: true, size: [700, 560] },
        { id: "store",     name: "Glimra Store",  icon: "bag",       colors: ["#2ed3a1", "#5b8cff"], internal: true, size: [900, 620] },
        { id: "update",    name: "Glimra Update", icon: "update",    colors: ["#5b8cff", "#2ed3a1"], internal: true, size: [700, 540] },
        { id: "files",     name: "Dateien",       icon: "folder",    colors: ["#5b8cff", "#a06bff"], cmd: "pcmanfm-qt" },
        { id: "browser",   name: "Browser",       icon: "browser",   colors: ["#ff9f43", "#e85d2a"], cmd: "firefox" },
        { id: "terminal",  name: "Terminal",      icon: "terminal",  colors: ["#3a4260", "#20263d"], cmd: "foot" },
        { id: "editor",    name: "Texteditor",    icon: "editor",    colors: ["#ffd166", "#e0a92a"], cmd: "mousepad" },
        { id: "mail",      name: "E-Mail",        icon: "mail",      colors: ["#4dabf7", "#1c7ed6"], cmd: "thunderbird" },
        { id: "steam",     name: "Steam",         icon: "game",      colors: ["#2a475e", "#1b2838"], cmd: "glimra-x11 steam" }
    ]

    function appById(id) {
        for (let i = 0; i < apps.length; i++) if (apps[i].id === id) return apps[i]
        return null
    }

    property string settingsSection: "profil"

    function openApp(id, section) {
        const app = appById(id)
        if (!app) return
        if (!app.internal) { backend.launch(app.cmd); return }
        if (id === "settings") settingsSection = section || "profil"
        for (let i = 0; i < windows.length; i++) {
            if (windows[i].appId === id) { focusWindow(windows[i]); return }
        }
        const comps = { settings: settingsComp, tools: toolsComp, taskman: taskComp, wallpaper: wallComp,
                        assistant: assistantComp, remote: remoteComp, security: securityComp, backup: backupComp,
                        vm: vmComp, transfer: transferComp, help: helpComp, calc: calcComp,
                        store: storeComp, update: updateComp, installer: installerComp }
        const lw = windowLayer.width > 400 ? windowLayer.width : 1280
        const lh = windowLayer.height > 300 ? windowLayer.height : 744
        const s = [Math.min(app.size[0], lw - 20), Math.min(app.size[1], lh - 20)]
        const w = winComp.createObject(windowLayer, {
            title: app.name, icon: app.icon, appId: id, content: comps[id],
            width: s[0], height: s[1],
            x: Math.max(10, (lw - s[0]) / 2 + cascade),
            y: Math.max(10, (lh - s[1]) / 2 + cascade - 20)
        })
        registerWindow(w)
    }

    // Vom Wayland-Compositor aufgerufen, wenn ein Programm ein Fenster öffnet
    function addClient(toplevel, xdgSurface) {
        const w = winComp.createObject(windowLayer, {
            title: toplevel.title || toplevel.appId || "Programm",
            icon: "windowsapp", appId: toplevel.appId || "client",
            xdgSurface: xdgSurface, toplevel: toplevel,
            x: 80 + cascade, y: 50 + cascade
        })
        toplevel.sendConfigure(Qt.size(Math.min(1000, windowLayer.width - 160),
                                       Math.min(660, windowLayer.height - 140)), [])
        registerWindow(w)
    }

    function registerWindow(w) {
        cascade = (cascade + 28) % 140
        desktopShown = false
        w.requestFocus.connect(() => focusWindow(w))
        w.menuRequested.connect((mx, my) => { winMenu.target = w; winMenu.x = w.x + mx; winMenu.y = w.y + my; winMenu.open() })
        w.closed.connect(() => {
            windows = windows.filter(x => x !== w)
            if (activeWindow === w) activeWindow = null
        })
        windows = windows.concat([w])
        focusWindow(w)
    }

    function focusWindow(w) {
        w.minimized = false
        w.z = ++topZ
        if (activeWindow && activeWindow !== w) activeWindow.active = false
        activeWindow = w
        w.active = true
    }

    function toast(text) {
        toastText.text = text
        toastBox.opacity = 1
        toastTimer.restart()
        notes.insert(0, { text: text, time: Qt.formatTime(new Date(), "HH:mm") })
        if (notes.count > 30) notes.remove(30, notes.count - 30)
    }

    // ---------------- Fenster-Funktionen wie bei Windows
    property bool desktopShown: false
    property var hiddenByDesktop: []
    function showDesktop() {
        if (!desktopShown) {
            hiddenByDesktop = windows.filter(w => !w.minimized)
            hiddenByDesktop.forEach(w => w.minimized = true)
        } else {
            hiddenByDesktop.forEach(w => { if (windows.indexOf(w) >= 0) w.minimized = false })
            hiddenByDesktop = []
        }
        desktopShown = !desktopShown
    }
    function snapActive(dir) {
        const w = activeWindow
        if (!w || w.minimized) return
        if (dir === "up") w.snapTo("max")
        else if (dir === "down") { if (w.snapped) w.snapTo("restore"); else w.minimized = true }
        else if (dir === "left") w.snapTo(w.snapped === "right" ? "restore" : "left")
        else if (dir === "right") w.snapTo(w.snapped === "left" ? "restore" : "right")
    }
    function closeActive() { if (activeWindow) activeWindow.close() }
    function closePopups() { startMenu.close(); qsLoader.active = false; icLoader.active = false; cbLoader.active = false }

    ListModel { id: notes }
    // Klick auf den Knopf eines gerade geschlossenen Popups soll es nicht sofort wieder öffnen
    property double popupClosedAt: 0
    function justClosed() { return Date.now() - popupClosedAt < 300 }
    Timer { id: testSnap; interval: 400; onTriggered: { openApp("settings"); openApp("store"); snapActive("right"); focusWindow(windows[0]); snapActive("left") } }

    // Tastenkürzel kommen aus keys.py (funktionieren auch, wenn ein Programm den Fokus hat)
    Connections {
        target: backend
        function onShortcut(name) {
            if (shell.locked && name !== "lock") return
            switch (name) {
            case "start": case "search": startMenu.opened ? startMenu.close() : startMenu.open(); break
            case "files": shell.openApp("files"); break
            case "terminal": shell.openApp("terminal"); break
            case "lock": shell.closePopups(); shell.locked = true; break
            case "desktop": shell.showDesktop(); break
            case "settings": shell.openApp("settings"); break
            case "quick": icLoader.active = false; qsLoader.active = !qsLoader.active; break
            case "notifications": qsLoader.active = false; icLoader.active = !icLoader.active; break
            case "clipboard": cbLoader.active = !cbLoader.active; break
            case "screenshot": backend.screenshot(); break
            case "taskman": shell.openApp("taskman"); break
            case "close": shell.closeActive(); break
            case "alttab": switcher.next(); break
            case "snap-up": shell.snapActive("up"); break
            case "snap-down": shell.snapActive("down"); break
            case "snap-left": shell.snapActive("left"); break
            case "snap-right": shell.snapActive("right"); break
            }
        }
    }

    Component { id: winComp; GlimraWindow {} }
    Component { id: settingsComp; SettingsApp { section: shell.settingsSection; onOpenApp: (id) => shell.openApp(id) } }
    Component { id: storeComp; StoreApp {} }
    Component { id: updateComp; UpdateApp {} }
    Component { id: installerComp; InstallerApp { onOpenWifi: { icLoader.active = false; qsLoader.active = true } } }
    Component { id: toolsComp; ToolsApp {} }
    Component { id: taskComp; TaskManagerApp {} }
    Component { id: wallComp; WallpaperApp {} }
    Component { id: assistantComp; AssistantApp { onOpenApp: (id) => shell.openApp(id) } }
    Component { id: remoteComp; RemoteApp {} }
    Component { id: securityComp; SecurityApp {} }
    Component { id: backupComp; BackupApp {} }
    Component { id: vmComp; VmApp {} }
    Component { id: transferComp; TransferApp {} }
    Component { id: helpComp; HelpApp { onOpenApp: (id) => shell.openApp(id) } }
    Component { id: calcComp; CalcApp {} }

    Connections {
        target: backend
        function onMessage(text) { shell.toast(text) }
        function onDesktopChanged() { desktopIcons.model = backend.desktopEntries() }
        function onLockRequested() { shell.locked = true }
    }

    // ---------------- Hintergrund + Logo
    Wallpaper {
        anchors.fill: parent
        key: backend.settings.wallpaper || "aurora"
    }
    Column {
        anchors.centerIn: parent
        anchors.verticalCenterOffset: -40
        spacing: 18
        opacity: 0.9
        visible: (backend.settings.wallpaper || "").indexOf("/") !== 0
        GlimraLogo { size: 110; anchors.horizontalCenter: parent.horizontalCenter }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Glimra OS"
            color: Theme.text
            font.pixelSize: 26
            font.weight: Font.Light
            font.letterSpacing: 6
            font.family: Theme.fontFamily
        }
    }

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: (mouse) => {
            startMenu.close()
            if (mouse.button === Qt.RightButton) {
                contextMenu.x = Math.min(mouse.x, shell.width - contextMenu.width - 8)
                contextMenu.y = Math.min(mouse.y, shell.height - contextMenu.height - 60)
                contextMenu.open()
            }
        }
    }

    // ---------------- Hinweis im Live-System: Vollversion installieren
    Rectangle {
        id: liveBanner
        visible: backend.isLive && !liveBannerHidden
        property bool liveBannerHidden: false
        anchors.horizontalCenter: parent.horizontalCenter
        y: 16
        height: 52
        width: liveRow.implicitWidth + 28
        radius: 26
        color: Theme.panel
        border.color: Theme.accent
        Row {
            id: liveRow
            anchors.centerIn: parent
            spacing: 12
            Icon { name: "plug"; size: 20; anchors.verticalCenter: parent.verticalCenter }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: "Testversion vom USB-Stick"
                color: Theme.text; font.pixelSize: 14; font.family: Theme.fontFamily
            }
            GlimraButton {
                anchors.verticalCenter: parent.verticalCenter
                primary: true; icon: "download"; text: "Vollversion installieren"
                onClicked: shell.openApp("installer")
            }
            IconButton {
                anchors.verticalCenter: parent.verticalCenter
                icon: "close"
                onClicked: liveBanner.liveBannerHidden = true
            }
        }
    }

    // ---------------- Profil oben links
    Rectangle {
        x: 18; y: 16
        height: 44
        width: profileRow.implicitWidth + 24
        radius: 22
        color: Theme.panel
        border.color: Theme.border
        Row {
            id: profileRow
            anchors.centerIn: parent
            spacing: 10
            Rectangle {
                width: 30; height: 30; radius: 15
                anchors.verticalCenter: parent.verticalCenter
                gradient: Gradient {
                    GradientStop { position: 0; color: Theme.accent }
                    GradientStop { position: 1; color: Theme.accent2 }
                }
                Text {
                    anchors.centerIn: parent
                    text: (backend.settings.name || "L").charAt(0).toUpperCase()
                    color: "white"; font.pixelSize: 14; font.weight: Font.Bold
                }
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: backend.settings.name || "Profil"
                color: Theme.text; font.pixelSize: 14; font.family: Theme.fontFamily
            }
        }
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: shell.openApp("settings") }
    }

    // ---------------- Desktop-Symbole
    Column {
        x: 18; y: 80
        spacing: 6
        Repeater {
            id: desktopIcons
            model: backend.desktopEntries()
            delegate: Rectangle {
                required property var modelData
                width: 92; height: 86; radius: 10
                color: ima.containsMouse ? Qt.rgba(1, 1, 1, 0.08) : "transparent"
                Column {
                    anchors.centerIn: parent
                    spacing: 6
                    AppIcon {
                        anchors.horizontalCenter: parent.horizontalCenter
                        size: 44
                        icon: modelData.dir ? "folder" : modelData.ext === ".sh" ? "script"
                            : (modelData.ext === ".exe" || modelData.ext === ".bat" || modelData.ext === ".msi") ? "windowsapp" : "file"
                        colors: modelData.dir ? ["#5b8cff", "#a06bff"] : modelData.ext === ".sh" ? ["#4ad295", "#249e66"]
                              : (modelData.ext === ".exe" || modelData.ext === ".bat") ? ["#3fc5f0", "#1f86c9"] : ["#8a94b8", "#5a6386"]
                    }
                    Text {
                        width: 86
                        horizontalAlignment: Text.AlignHCenter
                        text: modelData.name
                        color: Theme.text; font.pixelSize: 12
                        elide: Text.ElideMiddle
                        style: Text.Raised; styleColor: "#80000000"
                    }
                }
                MouseArea {
                    id: ima
                    anchors.fill: parent
                    hoverEnabled: true
                    onDoubleClicked: backend.openPath(modelData.path)
                }
            }
        }
    }

    // ---------------- Fensterebene
    Item {
        id: windowLayer
        anchors { left: parent.left; right: parent.right; top: parent.top; bottom: taskbar.top }
    }

    // Vorschau beim Andocken (Fenster an den Rand ziehen)
    Rectangle {
        readonly property string hint: shell.activeWindow ? shell.activeWindow.snapHint : ""
        visible: hint !== ""
        z: 99999
        x: hint === "right" ? windowLayer.width / 2 + 6 : 6
        y: 6
        width: (hint === "max" ? windowLayer.width : windowLayer.width / 2) - 12
        height: windowLayer.height - 12
        radius: 14
        color: Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.16)
        border.color: Theme.accent; border.width: 2
    }

    // Fenstermenü (Rechtsklick auf die Titelleiste)
    Popup {
        id: winMenu
        property var target: null
        width: 220; padding: 6
        background: Rectangle { radius: 12; color: Theme.panelSolid; border.color: Theme.border }
        contentItem: Column {
            spacing: 2
            Repeater {
                model: [ { l: "Links andocken", i: "snap", a: "left" }, { l: "Rechts andocken", i: "snap", a: "right" },
                         { l: "Maximieren", i: "maximize", a: "max" }, { l: "Minimieren", i: "minimize", a: "min" },
                         { l: "Schließen", i: "close", a: "close" } ]
                delegate: Rectangle {
                    required property var modelData
                    width: 208; height: 34; radius: 8
                    color: wmm.containsMouse ? Theme.hover : "transparent"
                    Row { x: 10; anchors.verticalCenter: parent.verticalCenter; spacing: 10
                          Icon { name: modelData.i; size: 16; anchors.verticalCenter: parent.verticalCenter }
                          Text { text: modelData.l; color: Theme.text; font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter } }
                    MouseArea { id: wmm; anchors.fill: parent; hoverEnabled: true
                        onClicked: {
                            const w = winMenu.target; winMenu.close(); if (!w) return
                            if (modelData.a === "min") w.minimized = true
                            else if (modelData.a === "close") w.close()
                            else w.snapTo(modelData.a)
                        } }
                }
            }
        }
    }

    // ---------------- Rechtsklick-Menü
    Popup {
        id: contextMenu
        width: 240
        padding: 6
        background: Rectangle { radius: 12; color: Theme.panelSolid; border.color: Theme.border }
        contentItem: Column {
            spacing: 2
            Repeater {
                model: [
                    { label: "Neuer Ordner",    icon: "folder",    act: "folder" },
                    { label: "Einstellungen",   icon: "settings",  act: "settings" },
                    { label: "Hintergrundbild", icon: "image",     act: "wallpaper" },
                    { label: "Taskmanager",     icon: "taskman",   act: "taskman" },
                    { label: "Terminal",        icon: "terminal",  act: "terminal" },
                    { label: "Bildschirmfoto",  icon: "camera",    act: "shot" },
                    { label: "Bildschirm sperren", icon: "lock",   act: "lock" }
                ]
                delegate: Rectangle {
                    required property var modelData
                    width: 228; height: 36; radius: 8
                    color: cma.containsMouse ? Theme.hover : "transparent"
                    Row {
                        x: 12; anchors.verticalCenter: parent.verticalCenter
                        spacing: 12
                        Icon { name: modelData.icon; size: 18; anchors.verticalCenter: parent.verticalCenter }
                        Text { text: modelData.label; color: Theme.text; font.pixelSize: 14; font.family: Theme.fontFamily; anchors.verticalCenter: parent.verticalCenter }
                    }
                    MouseArea {
                        id: cma
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: {
                            contextMenu.close()
                            if (modelData.act === "folder") backend.newFolder()
                            else if (modelData.act === "lock") shell.locked = true
                            else if (modelData.act === "shot") backend.screenshot()
                            else shell.openApp(modelData.act)
                        }
                    }
                }
            }
        }
    }

    // ---------------- Taskleiste + Startmenü
    Taskbar {
        id: taskbar
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        windows: shell.windows
        activeWindow: shell.activeWindow
        apps: shell.apps
        onStartClicked: startMenu.opened ? startMenu.close() : startMenu.open()
        onWindowClicked: (w) => {
            if (w === shell.activeWindow && !w.minimized) w.minimized = true
            else shell.focusWindow(w)
        }
        onPinnedClicked: (id) => shell.openApp(id)
        onTrayClicked: { if (!shell.justClosed()) { icLoader.active = false; qsLoader.active = !qsLoader.active } }
        onClockClicked: { if (!shell.justClosed()) { qsLoader.active = false; icLoader.active = !icLoader.active } }
        onShowDesktopClicked: shell.showDesktop()
        onCloseWindow: (w) => w.close()
    }

    // Popups nur laden, wenn sie gebraucht werden (spart Arbeitsspeicher)
    Loader {
        id: qsLoader
        active: false
        sourceComponent: QuickSettings {
            x: shell.width - width - 12
            y: shell.height - taskbar.height - height - 10
            onClosed: { shell.popupClosedAt = Date.now(); qsLoader.active = false }
            onOpenSettings: (section) => { close(); shell.openApp("settings", section) }
            Component.onCompleted: open()
        }
    }
    Loader {
        id: icLoader
        active: false
        sourceComponent: InfoCenter {
            x: shell.width - width - 12
            y: shell.height - taskbar.height - height - 10
            model: notes
            onClosed: { shell.popupClosedAt = Date.now(); icLoader.active = false }
            Component.onCompleted: open()
        }
    }
    Loader {
        id: cbLoader
        active: false
        sourceComponent: ClipboardPopup {
            x: (shell.width - width) / 2
            y: shell.height - taskbar.height - height - 10
            onClosed: cbLoader.active = false
            Component.onCompleted: open()
        }
    }

    WindowSwitcher {
        id: switcher
        anchors.centerIn: parent
        z: 120000
        windows: shell.windows
        onChosen: (w) => shell.focusWindow(w)
    }

    QtObject {
        id: startMenu
        property bool opened: smLoader.active
        function open() { if (!shell.justClosed()) smLoader.active = true }
        function close() { smLoader.active = false }
        function setQuery(t) { if (smLoader.item) smLoader.item.setQuery(t) }
    }
    Loader {
        id: smLoader
        active: false
        sourceComponent: StartMenu {
            x: 12
            y: shell.height - taskbar.height - height - 10
            apps: shell.apps
            onLaunch: (id) => { startMenu.close(); shell.openApp(id) }
            onOpenSetting: (section) => { startMenu.close(); shell.openApp("settings", section) }
            onLockClicked: { startMenu.close(); shell.locked = true }
            onClosed: { shell.popupClosedAt = Date.now(); smLoader.active = false }
            Component.onCompleted: open()
        }
    }

    // ---------------- Meldungen
    Rectangle {
        id: toastBox
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: taskbar.top
        anchors.bottomMargin: 18
        width: toastRow.implicitWidth + 36
        height: 42
        radius: 21
        color: Theme.panelSolid
        border.color: Theme.border
        opacity: 0
        visible: opacity > 0
        z: 100000
        Behavior on opacity { NumberAnimation { duration: 220 } }
        Row {
            id: toastRow
            anchors.centerIn: parent
            spacing: 10
            Icon { name: "info"; size: 18; anchors.verticalCenter: parent.verticalCenter }
            Text { id: toastText; color: Theme.text; font.pixelSize: 14; font.family: Theme.fontFamily; anchors.verticalCenter: parent.verticalCenter }
        }
        Timer { id: toastTimer; interval: 3800; onTriggered: toastBox.opacity = 0 }
    }

    Loader {
        anchors.fill: parent
        z: 150000
        active: shell.locked
        sourceComponent: LockScreen { onUnlocked: shell.locked = false }
    }

    Loader {
        anchors.fill: parent
        z: 200000
        active: !backend.settings.setupDone
        sourceComponent: SetupWizard { onInstallRequested: Qt.callLater(shell.openApp, "installer") }
    }

    // Für Tests/Screenshots: --app quick | info | clip | start:SUCHE | snap | APP-ID
    Component.onCompleted: if (startApp) Qt.callLater(function() {
        if (startApp === "quick") qsLoader.active = true
        else if (startApp === "info") { toast("Willkommen bei Glimra OS"); icLoader.active = true }
        else if (startApp === "clip") cbLoader.active = true
        else if (startApp.indexOf("start") === 0) { startMenu.open(); if (startApp.length > 6) Qt.callLater(startMenu.setQuery, startApp.slice(6)) }
        else if (startApp === "snap") testSnap.start()
        else if (startApp.indexOf("settings:") === 0) openApp("settings", startApp.slice(9))
        else openApp(startApp)
    })
}
