"""Glimra Setup-Manager – „Leichter Wechsel“ von Windows zu Glimra OS.

Willkommen → PC prüfen → Glimra OS herunterladen → USB-Stick erstellen → Daten umziehen.
Gebaut als GlimraSetup.exe (PyInstaller, siehe .github/workflows/build-exe.yml).
"""

from __future__ import annotations

import queue
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import __version__, core

BG = "#0d1020"
PANEL = "#161a2c"
CARD = "#1d2338"
HOVER = "#262e4a"
BORDER = "#2f3858"
TEXT = "#eef1fb"
DIM = "#9ea7c4"
ACCENT = "#5b8cff"
OK = "#4ad295"
BAD = "#ff5d6c"
FONT = "Segoe UI"


def asset(name: str) -> str:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return str(base / "glimra_setup" / "assets" / name)


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Glimra Setup-Manager")
        self.geometry("900x620")
        self.minsize(820, 560)
        self.configure(bg=BG)
        try:
            self.iconbitmap(asset("glimra.ico"))
        except tk.TclError:
            pass
        self.img = {n: tk.PhotoImage(file=asset(f"{n}.png")) for n in
                    ("logo", "computer", "download", "drive", "transfer", "check", "info", "folder", "network", "chevron")}
        self.q: queue.Queue = queue.Queue()
        self.cancel_flag = False
        self.iso_path: Path | None = None
        self.busy = False

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Glimra.Horizontal.TProgressbar", troughcolor=CARD, background=ACCENT,
                        bordercolor=CARD, lightcolor=ACCENT, darkcolor=ACCENT, thickness=10)

        self.container = tk.Frame(self, bg=BG)
        self.container.pack(fill="both", expand=True, padx=34, pady=26)
        self.after(100, self._poll)
        self.show_home()

    # ------------------------------------------------------------ Bausteine
    def clear(self) -> None:
        for w in self.container.winfo_children():
            w.destroy()

    def header(self, title: str, subtitle: str = "", back: bool = True) -> None:
        bar = tk.Frame(self.container, bg=BG)
        bar.pack(fill="x", pady=(0, 18))
        if back:
            b = tk.Label(bar, text="‹  Zurück", bg=BG, fg=DIM, font=(FONT, 11), cursor="hand2")
            b.pack(anchor="w")
            b.bind("<Button-1>", lambda e: self.show_home() if not self.busy else None)
        tk.Label(bar, text=title, bg=BG, fg=TEXT, font=(FONT, 22, "bold")).pack(anchor="w", pady=(6, 0))
        if subtitle:
            tk.Label(bar, text=subtitle, bg=BG, fg=DIM, font=(FONT, 11), wraplength=780, justify="left").pack(anchor="w")

    def button(self, parent, text: str, cmd, primary: bool = False, danger: bool = False) -> tk.Label:
        bg = ACCENT if primary else CARD
        fg = BAD if danger else TEXT
        b = tk.Label(parent, text=text, bg=bg, fg=fg, font=(FONT, 11, "bold" if primary else "normal"),
                     padx=18, pady=9, cursor="hand2", highlightthickness=1,
                     highlightbackground=bg if primary else BORDER)
        b.bind("<Button-1>", lambda e: cmd())
        b.bind("<Enter>", lambda e: b.configure(bg="#7aa2ff" if primary else HOVER))
        b.bind("<Leave>", lambda e: b.configure(bg=bg))
        return b

    def card(self, parent, icon: str, title: str, text: str, cmd) -> tk.Frame:
        f = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground=BORDER, cursor="hand2")
        inner = tk.Frame(f, bg=CARD)
        inner.pack(fill="both", expand=True, padx=18, pady=16)
        tile = tk.Label(inner, image=self.img[icon], bg=ACCENT, width=46, height=46)
        tile.pack(side="left", padx=(0, 14))
        col = tk.Frame(inner, bg=CARD)
        col.pack(side="left", fill="both", expand=True)
        t1 = tk.Label(col, text=title, bg=CARD, fg=TEXT, font=(FONT, 13, "bold"), anchor="w")
        t1.pack(fill="x")
        t2 = tk.Label(col, text=text, bg=CARD, fg=DIM, font=(FONT, 10), anchor="w", justify="left", wraplength=280)
        t2.pack(fill="x")
        arrow = tk.Label(inner, image=self.img["chevron"], bg=CARD)
        arrow.pack(side="right")
        widgets = (f, inner, col, t1, t2, arrow)
        for w in widgets:
            w.bind("<Button-1>", lambda e: cmd())
            w.bind("<Enter>", lambda e: [x.configure(bg=HOVER) for x in widgets])
            w.bind("<Leave>", lambda e: [x.configure(bg=CARD) for x in widgets])
        return f

    def progress_area(self, parent):
        bar = ttk.Progressbar(parent, style="Glimra.Horizontal.TProgressbar", maximum=1000)
        bar.pack(fill="x", pady=(18, 6))
        status = tk.Label(parent, text="", bg=BG, fg=DIM, font=(FONT, 10), anchor="w", justify="left", wraplength=800)
        status.pack(fill="x")
        return bar, status

    # ------------------------------------------------------------ Hintergrund-Aufgaben
    def run_task(self, fn, on_done) -> None:
        self.busy = True
        self.cancel_flag = False

        def worker():
            try:
                result = fn()
                self.q.put(("done", on_done, result, None))
            except core.Cancelled:
                self.q.put(("done", on_done, None, "Abgebrochen."))
            except Exception as e:  # noqa: BLE001
                self.q.put(("done", on_done, None, str(e)))
        threading.Thread(target=worker, daemon=True).start()

    def _poll(self) -> None:
        try:
            while True:
                msg = self.q.get_nowait()
                if msg[0] == "progress":
                    _, bar, status, value, text = msg
                    if bar.winfo_exists():
                        bar["value"] = value
                        status.configure(text=text)
                elif msg[0] == "done":
                    _, on_done, result, error = msg
                    self.busy = False
                    on_done(result, error)
                elif msg[0] == "call":
                    msg[1]()
        except queue.Empty:
            pass
        self.after(80, self._poll)

    # ------------------------------------------------------------ Startseite
    def show_home(self) -> None:
        self.clear()
        top = tk.Frame(self.container, bg=BG)
        top.pack(fill="x", pady=(10, 26))
        tk.Label(top, image=self.img["logo"], bg=BG).pack(side="left", padx=(0, 18))
        col = tk.Frame(top, bg=BG)
        col.pack(side="left")
        tk.Label(col, text="Willkommen", bg=BG, fg=TEXT, font=(FONT, 26, "bold")).pack(anchor="w")
        tk.Label(col, text="Einrichtung zu Glimra OS – in vier Schritten von Windows zu Glimra OS.",
                 bg=BG, fg=DIM, font=(FONT, 12)).pack(anchor="w")

        grid = tk.Frame(self.container, bg=BG)
        grid.pack(fill="both", expand=True)
        grid.columnconfigure((0, 1), weight=1, uniform="c")
        items = [
            ("computer", "1. PC prüfen", "Passt Glimra OS zu diesem Rechner?", self.show_check),
            ("download", "2. Glimra OS herunterladen", "Neueste Desktop- oder Server-ISO laden.", self.show_download),
            ("drive", "3. USB-Stick erstellen", "Startfähigen Stick mit Rufus erstellen.", self.show_usb),
            ("transfer", "4. Daten umziehen", "Dokumente, Bilder, Lesezeichen & Co. mitnehmen.", self.show_transfer),
        ]
        for i, (icon, title, text, cmd) in enumerate(items):
            self.card(grid, icon, title, text, cmd).grid(row=i // 2, column=i % 2, sticky="nsew", padx=8, pady=8)
        tk.Label(self.container, text=f"Glimra Setup-Manager {__version__} · deine Dateien bleiben auf diesem PC, bis du sie selbst überträgst.",
                 bg=BG, fg=DIM, font=(FONT, 9)).pack(side="bottom", anchor="w")

    # ------------------------------------------------------------ PC prüfen
    def show_check(self) -> None:
        self.clear()
        self.header("PC prüfen", "Glimra OS braucht einen 64-Bit-PC mit UEFI. Secure Boot muss für den Start aus sein.")
        box = tk.Frame(self.container, bg=BG)
        box.pack(fill="both", expand=True)
        all_ok = True
        for name, ok, hint in core.system_check():
            all_ok &= ok
            row = tk.Frame(box, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
            row.pack(fill="x", pady=5)
            tk.Label(row, image=self.img["check" if ok else "info"], bg=OK if ok else BAD, width=34, height=34).pack(side="left", padx=12, pady=10)
            tk.Label(row, text=name, bg=CARD, fg=TEXT, font=(FONT, 12, "bold")).pack(side="left")
            tk.Label(row, text=hint, bg=CARD, fg=OK if ok else BAD, font=(FONT, 11)).pack(side="right", padx=16)
        msg = "Alles bereit für Glimra OS." if all_ok else "Bitte die rot markierten Punkte beachten."
        tk.Label(box, text=msg, bg=BG, fg=OK if all_ok else BAD, font=(FONT, 12, "bold")).pack(anchor="w", pady=14)
        self.button(box, "Weiter: Glimra OS herunterladen", self.show_download, primary=True).pack(anchor="w")

    # ------------------------------------------------------------ Herunterladen
    def show_download(self) -> None:
        self.clear()
        self.header("Glimra OS herunterladen", f"Lädt die neueste ISO aus github.com/{core.REPO} (ca. 1–2 GB).")
        body = tk.Frame(self.container, bg=BG)
        body.pack(fill="both", expand=True)
        edition = tk.StringVar(value="desktop")
        for val, title, text in (("desktop", "Glimra OS Desktop", "Für deinen PC oder Laptop – mit Glimra Shell."),
                                 ("server", "Glimra OS Server", "Für einen Heimserver – Verwaltung im Browser.")):
            r = tk.Radiobutton(body, variable=edition, value=val, text=f"  {title}  –  {text}", bg=BG, fg=TEXT,
                               selectcolor=CARD, activebackground=BG, activeforeground=TEXT, font=(FONT, 11),
                               anchor="w", highlightthickness=0)
            r.pack(fill="x", pady=3)
        target = tk.StringVar(value=str(core.known_folder("Downloads")))
        row = tk.Frame(body, bg=BG)
        row.pack(fill="x", pady=(14, 0))
        tk.Label(row, text="Speichern in:", bg=BG, fg=DIM, font=(FONT, 10)).pack(side="left")
        tk.Label(row, textvariable=target, bg=BG, fg=TEXT, font=(FONT, 10)).pack(side="left", padx=8)
        self.button(row, "Ändern", lambda: target.set(filedialog.askdirectory(initialdir=target.get()) or target.get())).pack(side="right")
        bar, status = self.progress_area(body)
        btns = tk.Frame(body, bg=BG)
        btns.pack(fill="x", pady=12)

        def start():
            if self.busy:
                return
            ed = edition.get()

            def task():
                version, url, size = core.latest_iso(ed)
                dest = Path(target.get()) / url.rsplit("/", 1)[-1]
                self.q.put(("progress", bar, status, 0, f"Lade Glimra OS {version} …"))
                core.download(url, dest, lambda d, t: self.q.put(
                    ("progress", bar, status, d * 1000 / (t or size or 1), f"{core.human(d)} von {core.human(t or size)}")),
                    lambda: self.cancel_flag)
                return dest

            def done(result, error):
                if error:
                    status.configure(text="Fehler: " + error, fg=BAD)
                    return
                self.iso_path = result
                bar["value"] = 1000
                status.configure(text=f"Fertig: {result}", fg=OK)
                self.button(btns, "Weiter: USB-Stick erstellen", self.show_usb, primary=True).pack(side="left", padx=(10, 0))
            self.run_task(task, done)

        self.button(btns, "Herunterladen", start, primary=True).pack(side="left")
        self.button(btns, "Abbrechen", lambda: setattr(self, "cancel_flag", True)).pack(side="left", padx=10)

    # ------------------------------------------------------------ USB-Stick
    def show_usb(self) -> None:
        self.clear()
        self.header("USB-Stick erstellen", "Der Setup-Manager lädt das bewährte Programm Rufus und öffnet es mit deiner Glimra-OS-ISO.")
        body = tk.Frame(self.container, bg=BG)
        body.pack(fill="both", expand=True)
        steps = ("1.  USB-Stick einstecken (mind. 4 GB – er wird komplett gelöscht!).",
                 "2.  In Rufus den Stick wählen. Bei „Laufwerk“ prüfen, dass es wirklich der Stick ist.",
                 "3.  Bei Nachfrage „Im DD-Abbild-Modus schreiben“ wählen und START klicken.",
                 "4.  PC neu starten und im Bootmenü (meist F12, F11 oder ESC) den Stick wählen.")
        for s in steps:
            tk.Label(body, text=s, bg=BG, fg=TEXT, font=(FONT, 11), anchor="w", justify="left").pack(fill="x", pady=3)
        iso = tk.StringVar(value=str(self.iso_path) if self.iso_path else "")
        row = tk.Frame(body, bg=BG)
        row.pack(fill="x", pady=(16, 0))
        tk.Label(row, text="ISO:", bg=BG, fg=DIM, font=(FONT, 10)).pack(side="left")
        tk.Label(row, textvariable=iso, bg=BG, fg=TEXT, font=(FONT, 10)).pack(side="left", padx=8)
        self.button(row, "ISO wählen", lambda: iso.set(filedialog.askopenfilename(
            filetypes=[("ISO-Abbild", "*.iso")], initialdir=str(core.known_folder("Downloads"))) or iso.get())).pack(side="right")
        bar, status = self.progress_area(body)

        def start():
            if self.busy:
                return
            if not iso.get():
                messagebox.showinfo("Glimra OS", "Bitte zuerst die Glimra-OS-ISO herunterladen oder auswählen.")
                return

            def task():
                dest = Path(tempfile.gettempdir()) / "GlimraSetup" / "rufus.exe"
                if not dest.exists():
                    url = core.rufus_url()
                    core.download(url, dest, lambda d, t: self.q.put(
                        ("progress", bar, status, d * 1000 / (t or 1), f"Lade Rufus … {core.human(d)}")))
                return dest

            def done(result, error):
                if error:
                    status.configure(text="Fehler: " + error, fg=BAD)
                    return
                bar["value"] = 1000
                status.configure(text="Rufus ist geöffnet – folge den Schritten oben.", fg=OK)
                try:
                    subprocess.Popen([str(result), "-i", iso.get()])
                except OSError as e:
                    status.configure(text=f"Rufus konnte nicht starten: {e}", fg=BAD)
            self.run_task(task, done)

        self.button(body, "Rufus laden und öffnen", start, primary=True).pack(anchor="w", pady=12)

    # ------------------------------------------------------------ Umzug
    def show_transfer(self) -> None:
        self.clear()
        self.header("Daten umziehen", "Wähle, was mit zu Glimra OS soll. Danach in Glimra OS die App „Umzug“ öffnen.")
        body = tk.Frame(self.container, bg=BG)
        body.pack(fill="both", expand=True)
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)
        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=(24, 0))

        tk.Label(left, text="Was soll mit?", bg=BG, fg=DIM, font=(FONT, 10, "bold")).pack(anchor="w", pady=(0, 6))
        vars_: dict[str, tk.BooleanVar] = {}
        labels: dict[str, tk.Label] = {}
        for cat in core.CATEGORIES:
            v = tk.BooleanVar(value=cat not in ("Downloads", "Videos"))
            vars_[cat] = v
            row = tk.Frame(left, bg=BG)
            row.pack(fill="x")
            tk.Checkbutton(row, text=" " + cat, variable=v, bg=BG, fg=TEXT, selectcolor=CARD, activebackground=BG,
                           activeforeground=TEXT, font=(FONT, 11), highlightthickness=0).pack(side="left")
            labels[cat] = tk.Label(row, text="", bg=BG, fg=DIM, font=(FONT, 9))
            labels[cat].pack(side="right")

        def sizes():
            data = core.category_sizes()
            self.q.put(("call", lambda: [labels[c].configure(text=f"{n} {'Datei' if n == 1 else 'Dateien'} · {core.human(s)}")
                                         for c, (n, s) in data.items() if c in labels and labels[c].winfo_exists()]))
        threading.Thread(target=sizes, daemon=True).start()

        tk.Label(right, text="Wohin?", bg=BG, fg=DIM, font=(FONT, 10, "bold")).pack(anchor="w", pady=(0, 6))
        mode = tk.StringVar(value="folder")
        folder = tk.StringVar(value="")
        ip = tk.StringVar(value="")
        code = tk.StringVar(value="")
        tk.Radiobutton(right, text="  Auf USB-Stick / Festplatte (Ordner „GlimraUmzug“)", variable=mode, value="folder",
                       bg=BG, fg=TEXT, selectcolor=CARD, activebackground=BG, font=(FONT, 11), highlightthickness=0).pack(anchor="w")
        frow = tk.Frame(right, bg=BG)
        frow.pack(fill="x", padx=26, pady=(2, 10))
        tk.Label(frow, textvariable=folder, bg=BG, fg=TEXT, font=(FONT, 10)).pack(side="left")
        self.button(frow, "Ziel wählen", lambda: folder.set(filedialog.askdirectory() or folder.get())).pack(side="right")
        tk.Radiobutton(right, text="  Direkt an Glimra OS im Netzwerk", variable=mode, value="net",
                       bg=BG, fg=TEXT, selectcolor=CARD, activebackground=BG, font=(FONT, 11), highlightthickness=0).pack(anchor="w")
        nrow = tk.Frame(right, bg=BG)
        nrow.pack(fill="x", padx=26, pady=2)
        for label, var, width in (("IP-Adresse", ip, 18), ("Umzugs-Code", code, 10)):
            tk.Label(nrow, text=label, bg=BG, fg=DIM, font=(FONT, 9)).pack(anchor="w")
            tk.Entry(nrow, textvariable=var, width=width, bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat",
                     font=(FONT, 12), highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT).pack(anchor="w", pady=(0, 6), ipady=4)
        tk.Label(right, text="IP und Code zeigt Glimra OS in der App „Umzug“.", bg=BG, fg=DIM, font=(FONT, 9)).pack(anchor="w", padx=26)

        bar, status = self.progress_area(self.container)
        btns = tk.Frame(self.container, bg=BG)
        btns.pack(fill="x", pady=8)

        def start():
            if self.busy:
                return
            cats = [c for c, v in vars_.items() if v.get()]
            if not cats:
                return
            if mode.get() == "folder" and not folder.get():
                messagebox.showinfo("Umzug", "Bitte zuerst ein Ziel wählen (z. B. den USB-Stick).")
                return
            if mode.get() == "net" and not (ip.get() and code.get()):
                messagebox.showinfo("Umzug", "Bitte IP-Adresse und Umzugs-Code aus Glimra OS eingeben.")
                return
            work = Path(tempfile.mkdtemp(prefix="glimra-"))

            def prog(d, t, rel):
                self.q.put(("progress", bar, status, d * 1000 / t, f"{core.human(d)} von {core.human(t)} · {rel}"))

            def task():
                self.q.put(("progress", bar, status, 0, "Sammle Dateien …"))
                files = core.collect(cats, work)
                if mode.get() == "folder":
                    return core.copy_to_folder(files, Path(folder.get()), prog, lambda: self.cancel_flag)
                return core.send_to_glimra(files, ip.get(), code.get(), prog, lambda: self.cancel_flag)

            def done(result, error):
                if error:
                    status.configure(text="Fehler: " + error, fg=BAD)
                    return
                bar["value"] = 1000
                where = "auf dem Ziel im Ordner „GlimraUmzug“" if mode.get() == "folder" else "in Glimra OS im Ordner „Umzug“"
                status.configure(text=f"Fertig: {result} Dateien {where}. In Glimra OS die App „Umzug“ öffnen.", fg=OK)
            self.run_task(task, done)

        self.button(btns, "Umzug starten", start, primary=True).pack(side="left")
        self.button(btns, "Abbrechen", lambda: setattr(self, "cancel_flag", True)).pack(side="left", padx=10)


def main() -> None:
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # scharfe Schrift auf hochauflösenden Bildschirmen
        except Exception:  # noqa: BLE001
            pass
    App().mainloop()


if __name__ == "__main__":
    main()
