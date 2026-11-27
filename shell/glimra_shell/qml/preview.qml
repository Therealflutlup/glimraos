import QtQuick
import QtQuick.Window
import Glimra

// Vorschau der Glimra Shell als normales Fenster (Windows/Linux/macOS).
Window {
    width: 1280
    height: 800
    visible: true
    color: Theme.bg
    title: "Glimra OS – Vorschau"

    Shell { }
}
