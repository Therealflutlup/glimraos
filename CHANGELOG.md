# Änderungen

Alle wichtigen Änderungen an Glimra OS. Versionen folgen [Semantic Versioning](https://semver.org/lang/de/).

## [1.0.0] – 2026-11-27 „Funke“

Erste öffentliche Version.

### Glimra OS Desktop
- Glimra Shell: eigene Oberfläche als Wayland-Compositor mit Desktop, Taskleiste, Startmenü mit Suche, Rechtsklick-Menü und Fenstern
- Eigenes Glimra-Symbolset (58 Symbole) in allen Teilen des Systems
- Einrichtung beim ersten Start: Profil und „Wofür verwendest du mich?“ (Gaming, Leistung, Arbeit, Arbeits-Apps)
- Sperrbildschirm mit PIN, Konto exportieren/importieren
- Glimra Assistent: deutsche Befehle getippt oder gesprochen (offline mit Vosk)
- Sicherheit: Firewall (ufw) und Virenscan (ClamAV)
- Backups vor jedem Update, Wiederherstellen per Klick und automatischer Boot-Check
- Virtuelle PCs (KVM/QEMU), Umzug von Windows/Linux, Netzwerk-Tools, Taskmanager, Rechner, Hilfe
- Steam und Windows-Programme (Wine) über gamescope im Glimra-Fenster
- Installer mit Btrfs, Snapshots und Snapshot-Bootmenü
- Bedienung wie bei Windows: Windows-Taste öffnet das Startmenü, Win+E/I/L/D/A/N/V/S/R, Alt+Tab, Alt+F4, Druck,
  Strg+Umschalt+Esc, Fenster per Ziehen an den Rand oder Win+Pfeiltasten andocken, Fenstermenü, „Desktop anzeigen“
- Schnelleinstellungen: WLAN (mit Netzauswahl), Bluetooth (koppeln), Flugmodus, Energiemodus, Lautstärke, Helligkeit, Akku
- Info-Center mit Benachrichtigungen und Kalender, Zwischenablage-Verlauf, Bildschirmfotos
- Startmenü-Suche findet Apps, Einstellungen und Dateien
- Glimra Store (Programme aus Arch-Paketquellen und Flathub) und Glimra Update (prüft alle 6 Stunden)
- Einstellungen für Ton (Ausgabegerät), Anzeige, Energie & Akku und eine Tastenkürzel-Übersicht
- Sparsam: Shell braucht im Leerlauf ca. 110 MB RAM und 0 % CPU; komprimierter Arbeitsspeicher (zram),
  systemd-oomd gegen Einfrieren bei vollem Speicher, sparsame Firefox-Voreinstellungen

### Glimra OS Server
- Glimra Panel im Browser (HTTPS): Übersicht, Dienste, Benutzer mit Samba, Snapshots, Updates, Ein/Aus
- Erststart-Assistent

### GlimraApp (Android)
- Findet Glimra-OS-PCs und -Server im WLAN, Koppeln per Code
- PC sperren, Zwischenablage, Dateien senden, Nachrichten, Links, Lautstärke, Medien, Energie
- „Teilen“ aus jeder App an den PC

### Glimra Setup-Manager (Windows)
- PC prüfen, Glimra OS herunterladen, USB-Stick mit Rufus, Daten-Umzug per USB oder Netzwerk

[1.0.0]: https://github.com/therealflutlup/glimraos/releases/tag/v1.0.0
