# Sicherheit

## Unterstützte Versionen

| Version | Sicherheitsupdates |
|---|---|
| 1.0.x | ja |
| < 1.0 | nein |

## Sicherheitslücke melden

Bitte **nicht** öffentlich als Issue melden. Nutze auf GitHub
**Security → Report a vulnerability** (private Meldung). Du bekommst innerhalb von 7 Tagen eine Antwort.

## Sicherheitsmodell (kurz)

- **Glimra Panel (Server):** HTTPS mit selbst erstelltem Zertifikat auf Port 8443, Passwort mit PBKDF2 (200 000 Runden),
  Sitzungs-Cookies `HttpOnly` + `SameSite=Strict`, Bremse bei falschen Passwörtern. Nur im Heimnetz betreiben – nicht ins Internet freigeben.
- **Glimra Remote (Desktop ↔ GlimraApp):** Port 8765 im Heimnetz. Ein Handy bekommt erst nach Eingabe eines einmaligen
  6-stelligen Codes einen Schlüssel (nur als SHA-256-Hash gespeichert). Die Verbindung ist **nicht verschlüsselt**;
  die Fernsteuerung lässt sich in der App „GlimraApp“ am PC jederzeit ausschalten und Geräte lassen sich entfernen.
- **Systemhelfer:** Die Shell darf nur fest definierte Befehle ohne Passwort ausführen (`/etc/sudoers.d/20-glimra`),
  die Helfer prüfen ihre Argumente.
- **Updates:** Arch-Linux-Pakete werden mit pacman-Signaturen geprüft. Vor jedem Update entsteht ein Snapshot.
