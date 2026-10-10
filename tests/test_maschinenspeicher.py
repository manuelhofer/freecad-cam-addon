# Prüft den Maschinen-Speicher (W-011 S1): Die Beispielmaschinen gebaut, gespeichert und in die
# Liste genommen; die Art aus den Achsen – die Drehmaschine mit Revolver (12 Plätze, C, Y), die
# 3-Achs-Fräse, die drei 5-Achs-Fräsen und eine 4-Achs-Fräse (die 5-Achs-Fräse Tisch/Tisch ohne
# ihre Achse A). Zweimal merken gibt einen Eintrag, ein neuer Name schreibt ihn neu; eine nie
# gespeicherte Maschine kommt nicht hinein; eine fehlende Datei steht als nicht vorhanden;
# Entfernen nimmt den Eintrag heraus, die Datei bleibt; eine kaputte Liste liest sich als leer.
# reichweite.merke_maschine (Prüfen, Assistenten) nimmt die Maschine des Jobs in die Liste.
import os
import shutil
import sys
import tempfile

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import FreeCAD

from camaddon import beispielmaschine as bm
from camaddon import maschine as m
from camaddon import maschinenspeicher as ms
from camaddon import reichweite as rw
from camaddon import sprache

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


sprache.setze_sprache("de")
ordner = tempfile.mkdtemp()
liste = os.path.join(ordner, "CamAddon", ms.DATEINAME)


def gespeichert(baue, name):
    """Baut eine Beispielmaschine und speichert sie unter `name`.FCStd."""
    asm, ma = baue()
    datei = os.path.join(ordner, name + ".FCStd")
    asm.Document.saveAs(datei)
    return asm, ma, datei


# --- Die Art aus den Achsen -----------------------------------------------------------------
pruefe(ms.laden(liste) == [], "Liste am Anfang nicht leer")
asm, ma, dreh = gespeichert(bm.drehmaschine, "dreh")
eintrag = ms.merken(asm, ma, liste)
pruefe(
    eintrag is not None
    and eintrag.art == ms.DREHMASCHINE
    and eintrag.revolver
    and eintrag.plaetze == 12
    and eintrag.rundachsen == ["C"]
    and eintrag.achsen == ["X", "Y", "Z", "C"],
    f"Drehmaschine: {eintrag}",
)
pruefe(
    ms.art_text(eintrag) == "Drehmaschine mit Revolver (12 Plätze), C, Y",
    f"Drehmaschine: {ms.art_text(eintrag)!r}",
)

faelle = (
    (bm.fraesmaschine, "fraese", ms.FRAESE_3, [], "3-Achs-Fräse"),
    (bm.fuenfachs_tisch_tisch, "tisch_tisch", ms.FRAESE_5, ["A", "C"], "5-Achs-Fräse (A, C)"),
    (bm.fuenfachs_kopf_tisch, "kopf_tisch", ms.FRAESE_5, ["B", "C"], "5-Achs-Fräse (B, C)"),
    (bm.fuenfachs_kopf_kopf, "kopf_kopf", ms.FRAESE_5, ["A", "B"], "5-Achs-Fräse (A, B)"),
)
for baue, name, art, rund, text in faelle:
    asm, ma, _datei = gespeichert(baue, name)
    eintrag = ms.merken(asm, ma, liste)
    pruefe(
        eintrag is not None and eintrag.art == art and eintrag.rundachsen == rund,
        f"{name}: {eintrag}",
    )
    pruefe(ms.art_text(eintrag) == text, f"{name}: {ms.art_text(eintrag)!r}")
    pruefe(eintrag.drehzahl > 0 and eintrag.plaetze >= 1, f"{name}: {eintrag}")

# 4-Achs: die 5-Achs-Fräse Tisch/Tisch ohne ihre Achse A.
asm, ma, vier = gespeichert(bm.fuenfachs_tisch_tisch, "vier")
for ba in m.betriebsarten(ma):
    if ba.Art == m.ART_POSITIONIEREN and m.programmname(ba) == "A":
        asm.Document.removeObject(ba.Name)
asm.Document.save()
eintrag = ms.merken(asm, ma, liste)
pruefe(
    eintrag.art == ms.FRAESE_4 and ms.art_text(eintrag) == "4-Achs-Fräse (C)",
    f"4-Achs: {eintrag} {ms.art_text(eintrag)!r}",
)

# --- Die Liste ------------------------------------------------------------------------------
eintraege = ms.laden(liste)
pruefe(
    [os.path.basename(e.datei) for e in eintraege]
    == ["dreh.FCStd", "fraese.FCStd", "tisch_tisch.FCStd", "kopf_tisch.FCStd",
        "kopf_kopf.FCStd", "vier.FCStd"],
    f"Liste: {[e.datei for e in eintraege]}",
)  # fmt: skip
# Noch einmal merken: kein zweiter Eintrag; ein neuer Name schreibt ihn neu.
ma.Label = "Rundtisch-Fräse"
ms.merken(asm, ma, liste)
eintraege = ms.laden(liste)
pruefe(len(eintraege) == 6, f"doppelt: {len(eintraege)}")
pruefe(ms.finde(eintraege, vier).name == "Rundtisch-Fräse", "neuer Name nicht übernommen")
# Eine nie gespeicherte Maschine hat keine Datei: Sie kommt erst beim Speichern hinein.
asm_neu, ma_neu = bm.fraesmaschine()
pruefe(ms.merken(asm_neu, ma_neu, liste) is None, "ungespeicherte Maschine in der Liste")
pruefe(len(ms.laden(liste)) == 6, "ungespeicherte Maschine mitgezählt")
# Alle Maschinen eines Dokuments beim Speichern (der Beobachter in gui_maschinen).
asm_neu.Document.saveAs(os.path.join(ordner, "neu.FCStd"))
pruefe(len(ms.merken_dokument(asm_neu.Document, liste)) == 1, "merken_dokument")
pruefe(len(ms.laden(liste)) == 7, "nach dem Speichern nicht in der Liste")

# Eine Datei verschoben: nicht vorhanden – der Eintrag bleibt, bis man ihn sucht oder entfernt.
weg = os.path.join(ordner, "weg.FCStd")
shutil.move(os.path.join(ordner, "kopf_kopf.FCStd"), weg)
kopf = ms.finde(ms.laden(liste), os.path.join(ordner, "kopf_kopf.FCStd"))
pruefe(kopf is not None and not kopf.vorhanden, f"verschoben: {kopf}")
pruefe(ms.finde(ms.laden(liste), dreh).vorhanden, "Drehmaschine nicht vorhanden?")

# Entfernen: aus der Liste, die Datei bleibt.
pruefe(ms.entfernen(dreh, liste) and not ms.entfernen(dreh, liste), "entfernen")
pruefe(ms.finde(ms.laden(liste), dreh) is None and os.path.isfile(dreh), "Datei weg?")

# Eine kaputte Liste liest sich als leer.
kaputt = os.path.join(ordner, "kaputt.json")
with open(kaputt, "w", encoding="utf-8") as kaputte_liste:
    kaputte_liste.write("{ nicht json")
pruefe(ms.laden(kaputt) == [], "kaputte Liste")
pruefe(ms.laden(os.path.join(ordner, "gibt_es_nicht.json")) == [], "fehlende Liste")

# --- Prüfen und Assistenten merken die Maschine: reichweite.merke_maschine --------------------
ms.datei_pfad = lambda: liste
teil = FreeCAD.newDocument("Teil")
job = teil.addObject("App::FeaturePython", "Job")
pruefe(ms.finde(ms.laden(liste), dreh) is None, "Drehmaschine noch in der Liste")
rw.merke_maschine(job, dreh)  # die Datei ist offen – die Drehmaschine von oben
pruefe(ms.finde(ms.laden(liste), dreh) is not None, "merke_maschine nimmt sie nicht auf")
pruefe(getattr(job, rw.EIGENSCHAFT_MASCHINE, "") == dreh, "am Job nicht gemerkt")

# Verschwundene Dateien aus dem temporären Ordner (P-2026-10-10-04): aufraeumen() nimmt sie aus
# der Liste; eine fehlende Datei anderswo bleibt – dort hat „Suchen …“ Sinn.
im_tmp = os.path.join(tempfile.gettempdir(), "camaddon_probe_weg", "weg.FCStd")
# „Woanders“ ist nicht das Profil: Das legen die Prüfläufer mit mktemp an, also im temporären
# Ordner (P-2026-10-10-44) – der Ordner dieser Datei liegt sicher nicht dort.
woanders = os.path.join(os.path.dirname(os.path.abspath(__file__)), "camaddon_probe_weg.FCStd")
pruefe(ms.fluechtig(im_tmp) and not ms.fluechtig(woanders), "fluechtig erkennt den Ordner nicht")
eintraege = ms.laden(liste)
eintraege.append(ms.Eintrag(name="Weg (tmp)", datei=im_tmp))
eintraege.append(ms.Eintrag(name="Weg (woanders)", datei=woanders))
ms.speichern(eintraege, liste)
weg = ms.aufraeumen(liste)
# Auch die verschobene Kopf/Kopf-Maschine geht: Ihr Ordner kam aus mkdtemp, liegt also im
# temporären Ordner, und ihre Datei ist weg (P-2026-10-10-44).
pruefe(
    sorted(e.name for e in weg) == sorted(["Weg (tmp)", kopf.name]),
    f"aufraeumen: {[e.name for e in weg]}",
)
namen = [e.name for e in ms.laden(liste)]
pruefe("Weg (tmp)" not in namen and "Weg (woanders)" in namen, "aufraeumen nahm das Falsche")
pruefe(ms.aufraeumen(liste) == [], "aufraeumen nicht idempotent")

shutil.rmtree(ordner, ignore_errors=True)
if fehler:
    raise AssertionError("\n".join(fehler))
print()
print("OK", os.path.basename(__file__))
