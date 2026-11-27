import QtQuick

// Rechner
Item {
    id: calc
    property string expr: ""
    property string result: "0"

    function press(k) {
        if (k === "C") { expr = ""; result = "0"; return }
        if (k === "⌫") { expr = expr.slice(0, -1); return }
        if (k === "=") {
            const clean = expr.replace(/×/g, "*").replace(/÷/g, "/").replace(/,/g, ".")
            if (!/^[0-9+\-*/(). %]+$/.test(clean)) { result = "Fehler"; return }
            try {
                const v = Function('"use strict"; return (' + clean.replace(/%/g, "/100") + ')')()
                result = isFinite(v) ? String(Math.round(v * 1e10) / 1e10).replace(".", ",") : "Fehler"
                expr = result.replace(",", ".") === "Fehler" ? "" : result
            } catch (e) { result = "Fehler" }
            return
        }
        expr += k
    }

    focus: true
    Keys.onPressed: (e) => {
        const map = { "Return": "=", "Enter": "=", "Backspace": "⌫", "Escape": "C" }
        if (e.text && "0123456789+-*/().,%".indexOf(e.text) >= 0) press(e.text === "*" ? "×" : e.text === "/" ? "÷" : e.text)
        else if (e.key === Qt.Key_Return || e.key === Qt.Key_Enter) press("=")
        else if (e.key === Qt.Key_Backspace) press("⌫")
        else if (e.key === Qt.Key_Escape) press("C")
    }

    Column {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 10
        Rectangle {
            width: parent.width; height: 96; radius: 12; color: Theme.titleBg
            Text { anchors { right: parent.right; rightMargin: 14; top: parent.top; topMargin: 12 } text: calc.expr || " "; color: Theme.textDim; font.pixelSize: 16 }
            Text { anchors { right: parent.right; rightMargin: 14; bottom: parent.bottom; bottomMargin: 10 } text: calc.result; color: Theme.text; font.pixelSize: 36; font.weight: Font.Light }
        }
        Grid {
            columns: 4
            spacing: 8
            Repeater {
                model: ["C", "(", ")", "÷", "7", "8", "9", "×", "4", "5", "6", "-", "1", "2", "3", "+", "%", "0", ",", "="]
                delegate: Rectangle {
                    required property string modelData
                    width: (calc.width - 32 - 24) / 4; height: 54; radius: 12
                    color: modelData === "=" ? (km.containsMouse ? Qt.lighter(Theme.accent, 1.1) : Theme.accent)
                         : "÷×-+C()%".indexOf(modelData) >= 0 ? (km.containsMouse ? Theme.hover : Theme.titleBg)
                         : (km.containsMouse ? Theme.hover : Theme.card)
                    Text { anchors.centerIn: parent; text: modelData; color: Theme.text; font.pixelSize: 20 }
                    MouseArea { id: km; anchors.fill: parent; hoverEnabled: true; onClicked: { calc.press(modelData); calc.forceActiveFocus() } }
                }
            }
        }
    }
}
