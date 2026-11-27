pragma Singleton
import QtQuick

QtObject {
    readonly property color accent: backend.settings.accent || "#5b8cff"
    readonly property color accent2: "#a06bff"
    readonly property color bg: "#0d1020"
    readonly property color panel: "#cc141829"
    readonly property color panelSolid: "#161a2c"
    readonly property color windowBg: "#1a1f33"
    readonly property color titleBg: "#20263d"
    readonly property color card: "#232a44"
    readonly property color hover: "#2c3555"
    readonly property color border: "#2f3858"
    readonly property color text: "#eef1fb"
    readonly property color textDim: "#9ea7c4"
    readonly property color danger: "#ff5d6c"
    readonly property color ok: "#4ad295"
    readonly property int radius: 12
    readonly property string fontFamily: "Inter, Noto Sans, Segoe UI, sans-serif"

    // Hintergrundbilder als Farbverläufe: [oben, unten, Glow]
    readonly property var wallpapers: ({
        "aurora": ["#0b1030", "#2a1458", "#5b8cff"],
        "sunset": ["#2b0f2e", "#c2484f", "#ffb36b"],
        "ocean":  ["#021b2e", "#0b5f7a", "#3fe0d0"],
        "forest": ["#07170f", "#1f4d2c", "#8be28b"],
        "night":  ["#05060c", "#151a2e", "#6c7cff"]
    })

    // "auto": Hintergrund passend zur Tageszeit
    function wallpaperFor(key) {
        if (key === "auto") {
            const h = new Date().getHours()
            if (h >= 6 && h < 11) return wallpapers.ocean
            if (h >= 11 && h < 17) return wallpapers.aurora
            if (h >= 17 && h < 21) return wallpapers.sunset
            return wallpapers.night
        }
        return wallpapers[key] || wallpapers.aurora
    }
}
