# Glimra OS veröffentlichen

## Einmalig einrichten

1. **Repository anlegen:** auf GitHub `therealflutlup/glimraos` (öffentlich), ohne README.
2. **Hochladen:**
   ```bash
   git init && git add . && git commit -m "Glimra OS 1.0.0"
   git branch -M main
   git remote add origin https://github.com/therealflutlup/glimraos.git
   git push -u origin main
   ```
   → Unter **Actions** läuft „Bauen und prüfen“ (Tests, ISO, APK, EXE).
3. **Feste App-Signatur (empfohlen):** einmal `tools/make-android-key.sh` ausführen (braucht Java/keytool) und die zwei
   angezeigten Secrets unter *Settings → Secrets and variables → Actions* anlegen. **Den Schlüssel sicher aufheben** –
   ohne ihn können Nutzer spätere App-Versionen nicht als Update installieren.
4. **Webseite:** *Settings → Pages → Source: GitHub Actions*. Danach unter *Actions → Webseite → Run workflow*.
   Adresse: `https://therealflutlup.github.io/glimraos/`
5. **Sicherheitsmeldungen:** *Settings → Code security → Private vulnerability reporting* einschalten.

## Neue Version veröffentlichen

```bash
python3 tools/bump_version.py 1.0.1      # nur bei neuer Version, 1.0.0 ist schon gesetzt
# CHANGELOG.md: Abschnitt ## [1.0.1] – Datum ergänzen
git commit -am "Glimra OS 1.0.1"
git tag v1.0.1
git push --follow-tags
```

Der Workflow „Veröffentlichen“ baut alles, prüft, dass Tag und VERSION zusammenpassen, erstellt `SHA256SUMS.txt`
und legt das Release mit den Notizen aus dem CHANGELOG an. Die Webseite und der Setup-Manager zeigen automatisch auf die neuen Dateien.

## Vor der ersten Veröffentlichung prüfen

- [ ] Desktop-ISO in einer VM (UEFI an) gestartet: Einrichtung, Apps, `glimra-install`, Neustart
- [ ] Nach der Installation: Backup erstellen und wiederherstellen
- [ ] Server-ISO: Panel unter `https://IP:8443`, Benutzer anlegen, Samba-Freigabe von Windows öffnen
- [ ] APK auf einem Android-Handy: PC finden, koppeln, sperren, Datei senden
- [ ] GlimraSetup.exe unter Windows: PC prüfen, ISO laden, Umzug per Netzwerk
- [ ] Domain `glimraos.de` (und ggf. `glimraos.com`) bei einem Anbieter registriert, falls gewünscht

## Hinweise

- **Eigene Domain (optional):** Nach dem Registrieren von `glimraos.de` im Ordner `site/` eine Datei `CNAME` mit dem Inhalt
  `glimraos.de` anlegen und beim Domain-Anbieter einen CNAME-Eintrag `www` → `therealflutlup.github.io` bzw. die
  GitHub-Pages-IP-Adressen für die Hauptdomain setzen. Danach unter *Settings → Pages* die Domain eintragen und „Enforce HTTPS“ aktivieren.

- **Windows SmartScreen:** Ohne gekauftes Code-Signing-Zertifikat warnt Windows beim ersten Start von GlimraSetup.exe.
  Das ist bei kleinen Open-Source-Projekten normal; im Handbuch steht, wie man trotzdem startet.
- **Google Play:** Die App ist für die Verteilung über GitHub (und F-Droid, Metadaten in `android/fastlane/`) vorbereitet.
  Für Google Play braucht es ein Entwicklerkonto (einmalig 25 $) und ein App-Bundle (`gradle bundleRelease`).
- **Impressum:** Ob die Webseite ein Impressum braucht, hängt davon ab, ob sie als geschäftsmäßig gilt (z. B. bei Spenden,
  Werbung oder Verkauf). Im Zweifel eins ergänzen oder rechtlich beraten lassen.
