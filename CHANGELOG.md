# Änderungen

Alle wichtigen Änderungen an Glimra OS. Versionen folgen [Semantic Versioning](https://semver.org/lang/de/).

## [1.2.0] – 2026-11-27 „Funke“

### Neu
- **GlimraApp steuert jetzt auch Windows-PCs.** Der Glimra Setup-Manager hat die neue Seite „Handy verbinden“
  mit Kopplungscode, gekoppelten Geräten und Autostart (`GlimraSetup.exe --agent` läuft unsichtbar im Hintergrund).
- Neue Funktionen in der App für Windows-PCs: Bildschirm ansehen, laufende Programme sehen und beenden,
  Programme starten, Fenster-Nachricht, angemeldete Benutzer und Domäne anzeigen, Benutzer abmelden, Ruhezustand.
  Die App blendet nur ein, was das Gerät kann.
- Vorbereitet für die Benutzerverwaltung im Heimnetz: Der Agent meldet Domäne (z. B. heim.lan) und alle
  angemeldeten Benutzer.
- GlimraApp nennt bei „Nicht erreichbar“ den Grund (abgelehnt, keine Antwort, falsche Adresse).

### Behoben
- Glimra OS zeigt bei „Handy verbinden“ die IP-Adresse der Standardverbindung (nicht virbr0/docker0).

## [1.1.0] – 2026-11-27 „Funke“

### Neu
- **Vollversion installieren:** Wer Glimra OS vom USB-Stick startet, sieht oben den Hinweis
  „Testversion vom USB-Stick“ mit dem Knopf „Vollversion installieren“. Ein grafischer Assistent prüft das Internet
  (mit WLAN-Auswahl), zeigt alle Laufwerke zum Auswählen, fragt Benutzer, PC-Name und Passwort ab und installiert
  Glimra OS mit Fortschrittsanzeige fest auf die Festplatte. Danach reicht ein Klick auf „Jetzt neu starten“.
- Die Einrichtung beim ersten Start bietet im Live-System direkt „Vollversion installieren“ an.
- `glimra-install --auto` für den grafischen Installer; der Stick, von dem gestartet wurde, wird nie als Ziel angeboten.

### Behoben
- **WLAN und Flugmodus im Live-System (USB-Stick):** Das Live-System startete iwd/systemd-networkd, die Glimra Shell
  steuert aber NetworkManager – WLAN-Liste blieb leer, Schalter ohne Wirkung. Jetzt läuft auch auf dem Stick
  NetworkManager (plus Bluetooth).
- Flugmodus sperrt jetzt alle Funkgeräte über rfkill (WLAN und Bluetooth) und erkennt seinen Zustand richtig
  (vorher wurde die falsche Spalte von `nmcli radio all` gelesen).
- WLAN wird beim Einschalten auch per rfkill entsperrt (manche PCs starten mit gesperrtem WLAN).
- Schnelleinstellungen erklären, warum WLAN nicht geht: Netzwerkdienst aus, kein WLAN-Adapter oder
  WLAN per Schalter/Fn-Taste aus. „Erneut suchen“, wenn keine Netze gefunden wurden.
- Installer: Die Partition hieß nach der Umbenennung „Glimra OS“ ohne Anführungszeichen – `mkfs.btrfs` und `sgdisk`
  wären daran gescheitert. Jetzt heißt sie „GlimraOS“.
- Installer prüft das Internet zusätzlich per HTTPS (manche Netze blockieren ping).

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
