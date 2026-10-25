# SPDX-License-Identifier: LGPL-2.1-or-later
"""Das NC-Programm eines Jobs rechnen – ohne Oberfläche, auch auf einem Nebenrechner.

Das Fenster „Programm schreiben“ (gui_programm) rechnete die Abschnitte (die Bahnen mit der
Maschine), das Programm und das Nachlesen in sich selbst: am Nasen-Testteil (236 000 Sätze)
stand es beim Öffnen 2,1 s und beim Speichern 2,3 s, ohne einen Klick anzunehmen (Manuel,
2026-10-09: „ein Lag … wo ich nichts klicken kann … sowas muss unbedingt vermieden werden“).
Ab IM_HINTERGRUND_AB Sätzen im Job rechnet es darum programm() auf einem Nebenrechner, auf einer
Kopie des Dokuments – die Abschnitte enthalten Path.Command und gehen nicht durch die Verbindung,
also rechnet der Arbeiter alles bis zum Text und gibt nur ihn, die Hinweise und die Befunde
zurück. Die Abschnitte behält er für die nächste Einstellung (_ABSCHNITTE). Kleinere Jobs rechnet
das Fenster wie bisher selbst. Läuft ohne Oberfläche (P-2026-10-11-50).
"""

import FreeCAD

from . import postprozessor as pp
from . import reichweite as rw
from . import werkzeuge as wz
from .sprache import tr

IM_HINTERGRUND_AB = 20000  # Sätze im Job: ab so vielen rechnet das Fenster auf einem Nebenrechner

_ABSCHNITTE = {}  # (Dokument, Job, Maschine) -> (Abschnitte, ohne Kette) – nur die letzten


def bibliothek():
    """Die Werkzeugverwaltung für die Werkzeuglängen – oder None, wenn sie sich nicht lesen
    lässt (dann gilt die Länge der CAM-Werkzeuge, und die Hinweise sagen es)."""
    try:
        return wz.Bibliothek.laden()
    except (wz.BeschaedigteDatei, OSError):
        return None


def abschnitte_und_kette(job, gewaehlt):
    """(pp.abschnitte des Jobs mit der Maschine `gewaehlt` – (Name, Pfad, Dokument) aus
    pp.maschinen_zur_wahl, oder None –, ohne Kette): ob eine Ebene ohne die Kette einer Maschine
    mit zwei Rundachsen gerechnet ist – dann gilt der gedachte Tisch A, C um den Nullpunkt. Hat
    der Job Ebenen (3+2), rechnet das Programm ohne Schwenkzyklus die Rundachsen und Punkte aus
    ihrer Kette, je Werkzeug mit seiner Länge, wie „Auf der Maschine prüfen“; liegt die Maschine
    nur in ihrer Datei, wird sie dafür verborgen geöffnet und wieder geschlossen. Operationen mit
    Werkzeugachse je Satz (Kugelfräser angestellt, Flanke) brauchen die Maschine auch – ohne sie
    sagt das Programm selbst, was es schreibt."""
    from . import schwenken as sw
    from . import simultan_operation as so

    if gewaehlt is None:
        teile = pp.abschnitte(job)
        ohne = bool(sw.ist_ebene(job) or sw.ebenen_von(job) or so.im_job(job))
        if ohne and (
            getattr(job, rw.EIGENSCHAFT_MASCHINE, "")
            or getattr(rw.grundjob_von(job), rw.EIGENSCHAFT_MASCHINE, "")
        ):
            # Der Job hat seine Maschine: pp.abschnitte rechnet Ebenen und Simultanbahnen mit ihr
            # (maschinenzugang) – ohne Kette ist nur, was es dabei auslassen musste.
            ohne = any(a.hinweis for a in teile)
        return teile, ohne
    _name, pfad, dok = gewaehlt
    verborgen = None
    if dok is None:
        try:
            dok = verborgen = FreeCAD.openDocument(pfad, True)
        except Exception:  # nicht lesbar: wie ohne Maschine
            return pp.abschnitte(job), True
    try:
        fuer = maschine_je_operation(job, dok)
        if fuer is None:
            return pp.abschnitte(job), True
        ohne = []

        def gemerkt(op):
            maschine = fuer(op)
            if maschine is None and not so.ist_simultan(op):
                ohne.append(op)
            return maschine

        return pp.abschnitte(job, gemerkt), bool(ohne)
    finally:
        if verborgen is not None:
            FreeCAD.closeDocument(verborgen.Name)


def maschine_je_operation(job, dok):
    """Eine Funktion Operation → schwenken.Maschine (je Werkzeugnummer einmal) für die erste
    Maschine im Dokument – None, wenn es keine gibt; die Funktion gibt None, wenn die Maschine
    für das Werkzeug keine Aufnahme hat; feste und einzelne Rundachsen bleiben erhalten."""
    from . import maschine as m
    from . import schwenken as sw

    gefunden = next(
        (
            (o, m.finde_maschine(o))
            for o in dok.Objects
            if o.TypeId == "Assembly::AssemblyObject" and m.finde_maschine(o) is not None
        ),
        None,
    )
    if gefunden is None:
        return None
    try:
        pruefung = rw.Pruefung(*gefunden)
    except Exception as fehler:  # eine kaputte Maschine: wie ohne
        FreeCAD.Console.PrintLog(f"CAM-Addon: Programm: {fehler}\n")
        return None
    werkzeuge = bibliothek()
    if werkzeuge is not None:
        # Mit dem Magazin der Maschine: die Länge, wie das Werkzeug an seinem Platz steckt – so
        # rechnen auch Vorschau und „Kollision prüfen“ (Manuels Kugel: im Magazin 113 mm ab
        # Spindelnase, in der Werkzeugliste anders).
        from . import magazin as mg

        mg.des_jobs(job, werkzeuge, gefunden[0])
    nullpunkt = rw.nullpunkt(job)
    je_nummer = {}

    def fuer(op):
        tc = getattr(op, "ToolController", None)
        nummer = int(getattr(tc, "ToolNumber", 0) or 0)
        if nummer not in je_nummer:
            aufnahme = pruefung.werkzeugaufnahme(nummer) if tc is not None else None
            maschine = None
            if aufnahme is not None:
                laenge = rw.einspannung(tc, werkzeuge)
                maschine = sw.Maschine(pruefung, aufnahme, laenge, nullpunkt)
            je_nummer[nummer] = maschine
        return je_nummer[nummer]

    return fuer


def programm(
    dokument,
    job_name,
    maschine,
    s,
    info,
    vorschau=None,
    datei="",
    rohteil=None,
    nachlesen=False,
):
    """Auch auf einem Nebenrechner: das Programm des Jobs `job_name` im Dokument (der Kopie) –
    `maschine`: None, der Pfad ihrer Datei oder ihr Dokument (eine Kopie); `s` die Steuerung,
    `info` die Maschineninfo, `vorschau`: so viele Sätze (None: alle), `datei` und `rohteil` wie
    pp.programm. {zeilen, hinweise, saetze} – mit `nachlesen` dazu {befunde, nachgelesen, groesse}
    (pp.nachlesen, pp.groesse_text). Die Abschnitte bleiben für den nächsten Aufruf gemerkt."""
    job = dokument.getObject(job_name)
    if job is None:
        raise ValueError(f"Job „{job_name}“ fehlt im Dokument {dokument.Name}")
    if maschine is None:
        gewaehlt, kennung = None, None
    elif isinstance(maschine, str):
        gewaehlt, kennung = ("", maschine, None), maschine
    else:
        gewaehlt, kennung = ("", "", maschine), maschine.Name
    schluessel = (dokument.Name, job_name, kennung)
    if schluessel not in _ABSCHNITTE:
        _ABSCHNITTE.clear()  # nur die letzten: eine neue Kopie macht die alten wertlos
        _ABSCHNITTE[schluessel] = abschnitte_und_kette(job, gewaehlt)
    teile, ohne = _ABSCHNITTE[schluessel]
    from . import n_eck as ne

    ergebnis = pp.programm(
        teile, s, info, job.Label, vorschau, datei=datei, rohteil=rohteil,
        einrichten=ne.einrichten_text(job),
    )  # fmt: skip
    if ohne and not (s.schwenkzyklus and s.schwenken):
        # Sonst stillschweigend: der gedachte Tisch A, C um den Nullpunkt (schwenken).
        ergebnis.hinweise.append(tr("pp.hinweis.ebene_ohne_kette"))
    antwort = {"zeilen": ergebnis.zeilen, "hinweise": ergebnis.hinweise, "saetze": ergebnis.saetze}
    if nachlesen:
        befunde, saetze = pp.nachlesen(ergebnis, s, info)
        antwort.update(befunde=befunde, nachgelesen=saetze, groesse=pp.groesse_text(ergebnis, s))
    return antwort
