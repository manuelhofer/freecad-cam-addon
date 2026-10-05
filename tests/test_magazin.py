# Prüft ohne Oberfläche die Nummern im Job aus dem Magazin der Maschine (W-002 Stufe H2; Manuel,
# 2026-10-05: „E3 a ja, E7 a ja“): An der Fräse ruft das Programm ein Werkzeug mit der T-Nummer
# aus dem Magazin auf; eins, das dort fehlt, bekommt eine Nummer, die weder im Magazin noch im
# Job vergeben ist; hat der Job das Werkzeug schon, bleibt seine Nummer. Am Revolver der Platz,
# auf dem es beladen ist – sonst der erste freie, auf dem nichts beladen ist. Die Listen: beladen
# vorn, dann das Magazin, dann der Rest „nicht im Magazin“. „Ins Magazin übernehmen“. Die
# Rüstliste (Stufe H3): beladen, einsetzen, anlegen, umnummerieren; „Nummern aus dem Magazin“
# (E4); im Kopf des Programms und der Name an der Steuerung im Wechsel.
import os
import sys
import tempfile
from types import SimpleNamespace

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

from camaddon import bestueckung as bs
from camaddon import job_schnittwerte as js
from camaddon import magazin as mg
from camaddon import sprache
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


def job_mit(*paare):
    """Ein Job (nur, was magazin liest) mit Controllern: (Werkzeug, T-Nummer)."""
    controller = [
        SimpleNamespace(ToolNumber=n, Tool=SimpleNamespace(ToolBitID=js.PRAEFIX + w.kennung))
        for w, n in paare
    ]
    return SimpleNamespace(Tools=SimpleNamespace(Group=controller))


vorher = sprache.gewaehlte_sprache() or ""
sprache.setze_sprache("de")
ordner = tempfile.mkdtemp()
fraese = os.path.join(ordner, "dmu.FCStd")

fraeser12 = wz.Werkzeug(nummer=1, name="VHM 12", durchmesser=12, schneiden=3)
anbohrer = wz.Werkzeug(nummer=2, art=wz.NC_ANBOHRER, durchmesser=10)
bohrer = wz.Werkzeug(nummer=3, art=wz.BOHRER, durchmesser=8.5)
fase = wz.Werkzeug(nummer=0, art=wz.FASENFRAESER, durchmesser=10)
bib = wz.Bibliothek([fraeser12, anbohrer, bohrer, fase])
magazin = bib.neues_magazin("DMU", fraese)
magazin.hinzufuegen(anbohrer, 1)  # an dieser Maschine ist T1 der Anbohrer
magazin.hinzufuegen(fraeser12, 7)
magazin.eintrag_von(fraeser12).platz = 4

# Fräse: die Nummer aus dem Magazin – nicht die aus der Werkzeugverwaltung.
pruefe(mg.nummer(magazin, None, anbohrer) == 1, "Anbohrer nicht T1")
pruefe(mg.nummer(magazin, None, fraeser12) == 7, "Fräser nicht T7")
# Nicht im Magazin (E3 a): die kleinste, die weder im Magazin noch im Job vergeben ist.
pruefe(mg.nummer(magazin, None, bohrer) == 2, f"Bohrer: {mg.nummer(magazin, None, bohrer)}")
job = job_mit((fraeser12, 7), (fase, 2))
pruefe(mg.nummer(magazin, job, bohrer) == 3, f"Bohrer im Job: {mg.nummer(magazin, job, bohrer)}")
pruefe(
    mg.nummer(magazin, job, bohrer, vorgemerkt={3: fase.kennung}) == 4,
    "vorgemerkte Nummer vergeben",
)
# Hat der Job das Werkzeug schon, behält es seine Nummer (E4: umnummeriert nur auf Knopfdruck).
pruefe(mg.nummer(magazin, job, fase) == 2, "Nummer im Job nicht behalten")
pruefe(mg.nummer(magazin, job_mit((anbohrer, 9)), anbohrer) == 9, "Anbohrer im Job nicht T9")

# bestueckung.platz_fuer mit der Maschine: an der Fräse (ohne Revolver) die aus dem Magazin.
pruefe(bs.platz_fuer(None, anbohrer, bib, [], maschine=fraese) == 1, "platz_fuer Fräse")
pruefe(bs.platz_fuer(None, bohrer, bib, [], maschine=fraese) == 2, "platz_fuer frei")
# Eine Maschine ohne Magazin: wie bisher die Nummer der Werkzeugverwaltung.
andere = os.path.join(ordner, "andere.FCStd")
pruefe(bs.platz_fuer(None, anbohrer, bib, [], maschine=andere) == 2, "ohne Magazin")
# Am Revolver (Plätze 1–6): der beladene Platz; sonst der erste freie, auf dem nichts beladen ist.
plaetze = list(range(1, 7))
pruefe(bs.platz_fuer(None, fraeser12, bib, plaetze, maschine=fraese) == 4, "beladen nicht P4")
magazin.eintrag_von(anbohrer).platz = 1
pruefe(bs.platz_fuer(None, bohrer, bib, plaetze, maschine=fraese) == 2, "frei: nicht P2")
pruefe(
    bs.platz_fuer(None, fraeser12, bib, plaetze, {4: bohrer.kennung}, maschine=fraese) == 2,
    "P4 im Job belegt: nicht P2",
)
pruefe(
    bs.platz_fuer(None, bohrer, bib, plaetze, {2: fase.kennung}, maschine=fraese) == 3,
    "frei nach vorgemerkt: nicht P3",
)
# Alle freien beladen: der erste freie (dann rüstet der Bediener um).
voll = dict.fromkeys((2, 3, 5, 6), fase.kennung)
pruefe(bs.platz_fuer(None, bohrer, bib, plaetze, voll, maschine=fraese) == 1, "alles beladen")
voll[1] = fraeser12.kennung
voll[4] = anbohrer.kennung
pruefe(bs.platz_fuer(None, bohrer, bib, plaetze, voll, maschine=fraese) is None, "alles belegt")
magazin.eintrag_von(anbohrer).platz = 0

# Die Listen (E7 a): beladen vorn, dann das Magazin nach seiner Nummer, dann die anderen.
reihe = mg.sortiert(bib.werkzeuge, magazin)
pruefe(reihe == [fraeser12, anbohrer, bohrer, fase], f"Reihenfolge: {[w.nummer for w in reihe]}")
pruefe(mg.sortiert(bib.werkzeuge, None)[0] is fraeser12, "ohne Magazin nicht nach Nummer")
pruefe(mg.zeile(fraeser12, magazin).startswith("T7 · P4  "), mg.zeile(fraeser12, magazin))
pruefe(mg.zeile(fraeser12, magazin, platz=False).startswith("T7  "), "ohne Platz")
pruefe(mg.zeile(anbohrer, magazin).startswith("T1  "), mg.zeile(anbohrer, magazin))
pruefe(
    mg.zeile(bohrer, magazin).startswith("–  ") and "nicht im Magazin" in mg.zeile(bohrer, magazin),
    mg.zeile(bohrer, magazin),
)
pruefe(mg.zeile(bohrer, None) == wz.zeile(bohrer), "ohne Magazin andere Zeile")
satz = mg.fehlt_text(bohrer, magazin)
pruefe("nicht im Magazin „DMU“" in satz and "Bohrer" in satz, f"gelber Satz: {satz!r}")
pruefe(not mg.fehlt_text(anbohrer, magazin) and not mg.fehlt_text(bohrer, None), "Satz zu viel")

# „Ins Magazin übernehmen“: mit der Nummer, die es im Job hat, wenn sie im Magazin frei ist –
# sonst der nächsten freien; die Werkzeugverwaltung gespeichert.
gespeichert = []
bib.speichern = lambda pfad=None: gespeichert.append(pfad)
eintrag = mg.uebernehmen(bib, magazin, bohrer, job_mit((bohrer, 5)))
pruefe(eintrag.nummer == 5 and magazin.eintrag_von(bohrer) is eintrag, f"übernommen: {eintrag}")
eintrag = mg.uebernehmen(bib, magazin, fase, job_mit((fase, 7)))  # T7 ist der Fräser
pruefe(eintrag.nummer == 2, f"belegte Nummer übernommen: {eintrag}")
pruefe(len(gespeichert) == 2 and len(magazin.eintraege) == 4, "nicht gespeichert")

# --- Die Rüstliste (Stufe H3): was an der Maschine zu tun ist ---------------------------------
# Jetzt im Magazin: T1 Anbohrer, T7 Fräser (P4), T5 Bohrer, T2 Fase.
pruefe(mg.ruesten(fraeser12, magazin, 7) == (mg.GERUESTET, "beladen auf P4"), "T7 beladen")
pruefe(mg.ruesten(anbohrer, magazin, 1)[0] == mg.EINSETZEN, "T1 einsetzen")
pruefe(mg.ruesten(anbohrer, magazin, 1, revolver=True)[1].endswith("auf P1 einsetzen"), "P1")
pruefe(
    mg.ruesten(fraeser12, magazin, 3)
    == (mg.UMNUMMERIEREN, "im Magazin T7 – Nummern aus dem Magazin"),
    f"T3 statt T7: {mg.ruesten(fraeser12, magazin, 3)}",
)
pruefe(mg.ruesten(fraeser12, magazin, 3, revolver=True)[0] == mg.UMNUMMERIEREN, "P3 statt P4")
pruefe(mg.ruesten(fraeser12, magazin, 4, revolver=True)[0] == mg.GERUESTET, "P4 am Revolver")
neu = wz.Werkzeug(nummer=9, durchmesser=6)
pruefe(mg.ruesten(neu, magazin, 9)[0] == mg.ANLEGEN, "nicht im Magazin: anlegen")
pruefe(mg.ruesten(None, magazin, 9)[0] == mg.ANLEGEN, "ohne Werkzeugverwaltung: anlegen")
pruefe(mg.ruesten(neu, None, 9) == ("", ""), "ohne Magazin")
pruefe(mg.genannt(fraeser12, magazin) == "T7" and mg.genannt(fraeser12, None) == "T1", "genannt")
pruefe(mg.genannt(neu, magazin) == wz.kurz(neu), "genannt ohne Eintrag")


# „Nummern aus dem Magazin“ (E4): Fräse – wie im Magazin, der Rest frei und nicht im Magazin.
def eintrag(werkzeug, *nummern):
    controller = [SimpleNamespace(ToolNumber=n, Label=f"T{n} Schruppen") for n in nummern]
    return bs.Eintrag("wz:" + werkzeug.kennung, werkzeug, controller)


e_fraeser, e_neu, e_fase = eintrag(fraeser12, 1), eintrag(neu, 7), eintrag(fase, 3, 4)
ziel = bs.nummern_nach_magazin([e_fraeser, e_neu, e_fase], magazin)
pruefe(
    (ziel[id(e_fraeser)], ziel[id(e_fase)], ziel[id(e_neu)]) == (7, 2, 3),
    f"Fräse: {ziel[id(e_fraeser)]}, {ziel[id(e_fase)]}, {ziel[id(e_neu)]}",
)
e_neu2 = eintrag(neu, 9)  # T9 vergibt das Magazin nicht: bleibt
pruefe(bs.nummern_nach_magazin([e_neu2], magazin)[id(e_neu2)] == 9, "T9 nicht behalten")
# Revolver (P1–P6): beladen auf P4; P1 frei; der neue auf den ersten freien ohne Beladung.
magazin.eintrag_von(anbohrer).platz = 1
e_anbohrer = eintrag(anbohrer, 4)
ziel = bs.nummern_nach_magazin([e_fraeser, e_anbohrer, e_neu], magazin, plaetze)
pruefe(
    (ziel[id(e_fraeser)], ziel[id(e_anbohrer)], ziel[id(e_neu)]) == (4, 1, 2),
    f"Revolver: {ziel[id(e_fraeser)]}, {ziel[id(e_anbohrer)]}, {ziel[id(e_neu)]}",
)
# Die Controller folgen, ihr Name auch.
geaendert = bs._nummer_setzen(e_fase.controller, 2)
pruefe(
    [tc.ToolNumber for tc in e_fase.controller] == [2, 2]
    and e_fase.controller[0].Label == "T2 Schruppen"
    and len(geaendert) == 2,
    "Controller nicht umnummeriert",
)

# Der Kopf des Programms: je Werkzeug, was zu tun ist; der Name an der Steuerung im Wechsel
# (Siemens T="…"); im Fenster je Art ein Satz.
from camaddon import postprozessor as pp  # noqa: E402


def abschnitt(nummer, art, satz, name=""):
    befehle = [("G0", {"X": 0.0, "Y": 0.0, "Z": 5.0}), ("G1", {"Z": -1.0, "F": 300.0})]
    return pp.Abschnitt(
        f"Op T{nummer}", nummer, 3000.0, False, "None", befehle, f"Fräser {nummer}",
        name_steuerung=name, ruesten_art=art, ruesten=satz,
    )  # fmt: skip


siemens = pp.STEUERUNGEN["siemens"].ersetzt(wechsel_fraesen='T="{werkzeug}" M6')
fertig = pp.programm(
    [
        abschnitt(7, mg.GERUESTET, "beladen auf P4", "FRAESER_D12"),
        abschnitt(3, mg.UMNUMMERIEREN, "im Magazin T5 – Nummern aus dem Magazin"),
        abschnitt(9, mg.ANLEGEN, "nicht im Magazin – an der Steuerung anlegen und vermessen"),
    ],
    siemens,
    pp.Maschineninfo(name="DMU"),
    name="Teil",
)
text = fertig.text
for soll in (
    '  T7 "FRAESER_D12" Fräser 7 – beladen auf P4',
    "  T3 Fräser 3 – im Magazin T5 – Nummern aus dem Magazin",
    'T="FRAESER_D12" M6',
    'T="Fraeser 3" M6',
):
    pruefe(soll in text, f"im Programm fehlt {soll!r}:\n{text[:900]}")
hinweise = " ".join(fertig.hinweise)
pruefe(
    "T3: Im Magazin der Maschine hat das Werkzeug eine andere Nummer" in hinweise
    and "T9: nicht im Magazin der Maschine" in hinweise
    and "einsetzen" not in hinweise,
    f"Hinweise: {fertig.hinweise}",
)

sprache.setze_sprache(vorher)
if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
