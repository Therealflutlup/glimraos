# Glimra OS Handbuch

## 1. Glimra OS bekommen

| Datei | Wofür |
|---|---|
| `glimraos-desktop-1.0.0-x86_64.iso` | Glimra OS für PC und Laptop |
| `glimraos-server-1.0.0-x86_64.iso` | Glimra OS als Heimserver |
| `GlimraSetup.exe` | Hilft unter Windows beim Wechsel (PC prüfen, ISO, USB-Stick, Daten) |
| `GlimraApp-1.0.0.apk` | Handy-App für Android 8 oder neuer |
| `SHA256SUMS.txt` | Prüfsummen, um Downloads zu kontrollieren |

Alles gibt es unter **Releases** auf GitHub oder auf der Glimra-OS-Webseite.

**Download prüfen (Windows PowerShell):** `Get-FileHash glimraos-desktop-1.0.0-x86_64.iso` – der Wert muss mit `SHA256SUMS.txt` übereinstimmen.

## 2. Voraussetzungen

- 64-Bit-PC mit **UEFI**, mindestens 4 GB RAM, 30 GB Speicher (empfohlen 8 GB RAM, 60 GB)
- **Secure Boot ausschalten** (im BIOS/UEFI-Menü, meist mit F2 oder Entf beim Start)
- Für die Installation: Internetverbindung (Kabel oder WLAN)

## 3. USB-Stick erstellen

Am einfachsten mit `GlimraSetup.exe` → „USB-Stick erstellen“. Oder von Hand mit Rufus: ISO wählen, Stick wählen,
„DD-Abbild-Modus“, Start. Danach den PC vom Stick starten (Bootmenü meist F12, F11 oder ESC).

## 4. Installieren

1. Vom Stick starten – Glimra OS läuft zuerst als Testversion (Live-System). Alles, was du dort änderst,
   ist nach einem Neustart wieder weg.
2. Oben auf dem Desktop auf **„Vollversion installieren“** klicken (auch im Startmenü zu finden).
3. Internet verbinden (LAN-Kabel oder „WLAN wählen“), dann das **Laufwerk auswählen**.
   **Das gewählte Laufwerk wird komplett gelöscht.** Der USB-Stick selbst wird nicht angeboten.
4. Benutzername, PC-Name und Passwort eingeben, das Löschen bestätigen und „Jetzt installieren“ klicken.
   Glimra OS wird aus dem Internet geladen und fest installiert (ca. 10–30 Minuten).
5. „Jetzt neu starten“ klicken und den Stick abziehen, sobald der Bildschirm schwarz wird.

Für Profis geht es auch im Terminal: `glimra-install` fragt alles Schritt für Schritt ab.

## 5. Erste Schritte (Desktop)

- **Einrichtung:** Beim ersten Start fragt Glimra OS nach Name, E-Mail und „Wofür verwendest du mich?“. Die Antwort installiert passende Programme.
- **Startmenü:** Glimra-Knopf unten links – alle Apps mit Suche.
- **Rechtsklick auf den Desktop:** Neuer Ordner, Einstellungen, Hintergrundbild, Taskmanager, Terminal, Sperren.
- **Sperren:** Startmenü → Schloss. In Einstellungen → Konto & Sperre eine PIN festlegen.

## 6. Bedienung wie bei Windows

| Taste | Wirkung |
|---|---|
| Windows-Taste | Startmenü (einfach lostippen zum Suchen) |
| Win + E | Dateien |
| Win + I | Einstellungen |
| Win + L | Sperren |
| Win + D | Desktop anzeigen |
| Win + A | Schnelleinstellungen (WLAN, Bluetooth, Lautstärke, Helligkeit …) |
| Win + N | Info-Center (Benachrichtigungen, Kalender) |
| Win + V | Zwischenablage-Verlauf |
| Win + Pfeiltasten | Fenster links/rechts andocken, maximieren, minimieren |
| Alt + Tab | Fenster wechseln |
| Alt + F4 | Fenster schließen |
| Druck oder Win + Umschalt + S | Bildschirmfoto (landet in Bilder/Bildschirmfotos und in der Zwischenablage) |
| Strg + Umschalt + Esc | Taskmanager |

Fenster lassen sich an den linken/rechten Rand ziehen (halber Bildschirm) oder nach oben (maximieren).
Rechtsklick auf die Titelleiste öffnet das Fenstermenü. Der schmale Streifen ganz rechts in der Taskleiste zeigt den Desktop.

## 7. Die Glimra-Apps

| App | Was sie macht |
|---|---|
| Einstellungen | Profil, PIN, Farben, Nutzungsprofile, Netzwerk, Systeminfos |
| Assistent | Fragen und Befehle auf Deutsch, z. B. „Öffne den Browser“, „Wie spät ist es?“, „Rechne 12 mal 7“ |
| GlimraApp | Handy koppeln (Code), gekoppelte Geräte verwalten |
| Sicherheit | Firewall an/aus, Virenscan |
| Backups | Systemstände sichern und wiederherstellen |
| Virtuelle PCs | Windows oder andere Systeme im Fenster |
| Umzug | Daten vom Windows-PC, USB-Stick oder alter Festplatte übernehmen |
| Tools | IP-Adresse, MAC, Gateway, DNS |
| Taskmanager | Laufende Programme ansehen und beenden |
| Hilfe | Häufige Fragen, Systembericht für Fehlermeldungen |
| Glimra Store | Programme suchen und mit einem Klick installieren oder entfernen (auch Discord, Spotify, Minecraft-Launcher) |
| Glimra Update | Updates für System und Apps – vorher wird automatisch ein Backup angelegt |

## 8. Handy verbinden

1. GlimraApp-APK auf dem Handy installieren (Installation aus unbekannten Quellen einmal erlauben).
2. Am PC die App **GlimraApp** öffnen – Fernsteuerung ist an, ein 6-stelliger Code wird angezeigt.
3. In der Handy-App erscheint der PC unter „Im WLAN gefunden“ → antippen → Code eingeben.

Ist die Firewall an, sind die nötigen Ports (8765, 8766) automatisch freigegeben.

## 9. Von Windows umziehen

**Übers Netzwerk:** In Glimra OS die App **Umzug** öffnen → „Empfang einschalten“. Unter Windows `GlimraSetup.exe` →
„Daten umziehen“ → „Direkt an Glimra OS im Netzwerk“, IP und Umzugs-Code eintragen → Start.
Danach in Glimra OS in der App Umzug „Ausgewählte Daten übernehmen“.

**Per USB-Stick:** Unter Windows Ziel „USB-Stick“ wählen. Stick an den Glimra-OS-PC stecken, App Umzug öffnen, übernehmen.

## 10. Glimra OS Server

1. Server-ISO starten, Panel-Passwort festlegen.
2. Im Browser `https://<IP-des-Servers>:8443` öffnen. Die Zertifikatswarnung einmal bestätigen (das Zertifikat erstellt dein Server selbst).
3. Im Panel: Dienste (SSH, Samba, Docker, VMs, Webserver), Benutzer, Backups, Updates.
4. Fest installieren mit `glimra-install`. Windows-PCs erreichen ihren Ordner dann unter `\\<IP>\<Benutzername>`.

## 11. Wenn etwas nicht klappt

| Problem | Lösung |
|---|---|
| Stick startet nicht | Secure Boot aus, UEFI-Modus, Stick im Bootmenü wählen |
| Schwarzer Bildschirm statt Oberfläche | Im Terminal (Strg+Alt+F2) anmelden, `glimra-session` starten, Fehler steht in `/run/user/$(id -u)/glimra-shell.log` |
| System startet nach Update nicht | Zweimal neu starten – Glimra OS lädt automatisch das letzte Backup. Oder im Bootmenü „Glimra OS Backups“ wählen |
| Handy findet PC nicht | Gleiches WLAN? In der App „IP-Adresse eingeben“ nutzen; Gäste-WLANs blockieren oft Geräte untereinander |
| .exe startet nicht | Gaming-Profil installieren (Einstellungen → Nutzungsprofil) |
| PC wird langsam | Taskmanager (Strg + Umschalt + Esc) öffnen und große Programme beenden; Energiemodus „Leistung“ wählen |

Fehler melden: Hilfe → „Systembericht erstellen“ und die Datei an ein GitHub-Issue anhängen.
