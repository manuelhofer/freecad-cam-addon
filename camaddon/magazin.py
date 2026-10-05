# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Nummer eines Werkzeugs im Job aus dem Magazin der Maschine (W-002 Stufe H2; Manuel,
2026-10-05: „E3 a ja, E7 a ja“).

Hat die Maschine des Jobs ein Magazin (werkzeuge.Magazin – was ihre Steuerung kennt), ruft das
Programm ein Werkzeug an einer Fräse mit der T-Nummer aus dem Magazin auf. Steht es dort nicht
(E3 a), bekommt es eine freie Nummer – keine, die im Magazin oder im Job schon vergeben ist –,
und der Assistent sagt, dass es an der Maschine nicht angelegt ist („ins Magazin übernehmen“).
Hat der Job das Werkzeug schon, behält es seine Nummer. Am Revolver bleibt die Nummer im Job der
Platz (Stufe G – danach setzen Prüfung und Kollision das Werkzeug auf seine Station): beladen der
Platz aus dem Magazin, sonst der erste freie, auf dem nichts beladen ist
(bestueckung.platz_fuer). Ohne Magazin bleibt alles wie bisher.

In den Listen der Assistenten (E7 a) stehen die Werkzeuge des Magazins vorn, beladene zuerst,
mit ihrer Nummer im Magazin („T3 · P5“); die übrigen danach, „nicht im Magazin“.

Läuft ohne Oberfläche.
"""

from . import werkzeuge as wz
from .sprache import tr

BELADEN, IM_MAGAZIN, NICHT_IM_MAGAZIN = 0, 1, 2


def maschine_des_jobs(job):
    """Die Datei der Maschine, die sich der Job gemerkt hat – "" ohne (nicht die zuletzt
    benutzte: Ein Job ohne Maschine nimmt kein fremdes Magazin)."""
    from . import reichweite as rw

    return str(getattr(job, rw.EIGENSCHAFT_MASCHINE, "") or "") if job is not None else ""


def bibliothek_laden():
    """Die Werkzeugverwaltung – None, wenn sie sich nicht lesen lässt."""
    try:
        return wz.Bibliothek.laden()
    except (wz.BeschaedigteDatei, OSError):
        return None


def des_jobs(job, bibliothek=None, maschine=None):
    """Das Magazin, das für die Maschine des Jobs (oder `maschine`) gilt – None ohne."""
    maschine = maschine or maschine_des_jobs(job)
    if not maschine:
        return None
    bibliothek = bibliothek if bibliothek is not None else bibliothek_laden()
    return bibliothek.magazin_fuer(maschine) if bibliothek is not None else None


def nummern_im_job(job, ausser=None):
    """{T-Nummer} der Werkzeug-Controller des Jobs – ohne die des Werkzeugs `ausser`."""
    belegt = set()
    for tc in getattr(getattr(job, "Tools", None), "Group", None) or []:
        if ausser is not None and _kennung(tc) == ausser.kennung:
            continue
        nummer = int(getattr(tc, "ToolNumber", 0) or 0)
        if nummer > 0:
            belegt.add(nummer)
    return belegt


def nummer_im_job(job, werkzeug):
    """Die Nummer, die das Werkzeug im Job schon hat – None, wenn es dort noch keinen
    Controller hat."""
    for tc in getattr(getattr(job, "Tools", None), "Group", None) or []:
        if _kennung(tc) == werkzeug.kennung and int(getattr(tc, "ToolNumber", 0) or 0) > 0:
            return int(tc.ToolNumber)
    return None


def nummer(magazin, job, werkzeug, vorgemerkt=None):
    """Die T-Nummer für `werkzeug` in diesem Job mit diesem Magazin (an einer Fräse – am
    Revolver sucht bestueckung.platz_fuer den Platz): die im Job schon, sonst die im Magazin,
    sonst (E3 a) die kleinste, die weder im Magazin noch im Job noch in `vorgemerkt`
    ({Nummer: Kennung} – Werkzeuge, die gleich mit dazukommen) vergeben ist."""
    schon = nummer_im_job(job, werkzeug) if job is not None else None
    if schon is not None:
        return schon
    eintrag = magazin.eintrag_von(werkzeug)
    if eintrag is not None:
        return eintrag.nummer
    belegt = set(nummern_im_job(job)) if job is not None else set()
    belegt |= {n for n, kennung in (vorgemerkt or {}).items() if kennung != werkzeug.kennung}
    return magazin.naechste_nummer(auch=belegt)


def mit_revolver(maschine):
    """Hat die Maschine (ihre Datei, laut Maschinenspeicher) einen Revolver?"""
    from . import maschinenspeicher as msp

    eintrag = msp.finde(msp.laden(), maschine) if maschine else None
    return bool(eintrag is not None and eintrag.revolver)


def rang(werkzeug, magazin):
    """BELADEN, IM_MAGAZIN oder NICHT_IM_MAGAZIN – fürs Sortieren der Listen."""
    eintrag = magazin.eintrag_von(werkzeug) if magazin is not None else None
    if eintrag is None:
        return NICHT_IM_MAGAZIN
    return BELADEN if eintrag.platz > 0 else IM_MAGAZIN


def sortiert(werkzeuge, magazin):
    """Die Werkzeuge in der Reihenfolge der Listen: mit Magazin zuerst die beladenen, dann die
    übrigen des Magazins (je nach ihrer Nummer dort), dann die anderen (nach Nummer); ohne
    Magazin nach Nummer."""
    if magazin is None:
        return sorted(werkzeuge, key=wz.nach_nummer)

    def schluessel(w):
        eintrag = magazin.eintrag_von(w)
        return (rang(w, magazin), eintrag.nummer if eintrag else 0, wz.nach_nummer(w))

    return sorted(werkzeuge, key=schluessel)


def zeile(werkzeug, magazin, platz=True):
    """Die Listenzeile: ohne Magazin wie in der Werkzeugverwaltung („T3  Schaftfräser …“); mit
    Magazin „T3 · P5  …“ (beladen), „T3  …“ (im Magazin) oder „–  … – nicht im Magazin“.
    `platz` False: ohne „· P5“ (am Revolver steht der Platz im Job schon davor)."""
    if magazin is None:
        return wz.zeile(werkzeug)
    eintrag = magazin.eintrag_von(werkzeug)
    rest = wz.zeile_ohne_nummer(werkzeug)
    if eintrag is None:
        return f"–  {rest} – {tr('mg.nicht_im_magazin')}"
    if platz and eintrag.platz > 0:
        return f"T{eintrag.nummer} · P{eintrag.platz}  {rest}"
    return f"T{eintrag.nummer}  {rest}"


def fehlt_text(werkzeug, magazin, maschine_name=""):
    """Der gelbe Satz, wenn das Werkzeug nicht im Magazin steht (E3 a) – "" sonst."""
    if magazin is None or magazin.eintrag_von(werkzeug) is not None:
        return ""
    return tr(
        "mg.fehlt",
        werkzeug=wz.kurz(werkzeug),
        maschine=maschine_name or magazin.name or tr("mg.ohne_name"),
    )


def uebernehmen(bibliothek, magazin, werkzeug, job=None):
    """„Ins Magazin übernehmen“: das Werkzeug ins Magazin – mit der Nummer, die es im Job schon
    hat (wenn sie dort frei ist), sonst der nächsten freien – und die Werkzeugverwaltung
    gespeichert. Gibt den Eintrag zurück."""
    schon = nummer_im_job(job, werkzeug) if job is not None else None
    frei = schon if schon is not None and magazin.mit_nummer(schon) is None else None
    eintrag = magazin.hinzufuegen(werkzeug, frei)
    bibliothek.speichern()
    return eintrag


def _kennung(tc):
    """Die Kennung des Werkzeugs der Werkzeugverwaltung hinter einem Controller – "" ohne."""
    from . import job_schnittwerte as js

    werkzeug = getattr(tc, "Tool", None)
    kennung = str(getattr(werkzeug, "ToolBitID", "") or "")
    return kennung[len(js.PRAEFIX) :] if kennung.startswith(js.PRAEFIX) else ""
