# Prüft die Werkzeugbibliothek ohne Oberfläche: anlegen, kopieren, Nummern,
# Speichern und Laden (mit .bak), eine beschädigte Datei und eigene
# Werkstoffe.
import json
import os
import sys
import tempfile
from pathlib import Path

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

from camaddon import sprache
from camaddon import werkstoffe as ws
from camaddon import werkzeuge as wz

fehler = []


def pruefe(bedingung, text):
    if not bedingung:
        fehler.append(text)


vorher = sprache.gewaehlte_sprache() or ""
sprache.setze_sprache("de")
ordner = tempfile.mkdtemp()
pfad = os.path.join(ordner, "CamAddon", wz.DATEINAME)

# Ohne Datei: leer.
b = wz.Bibliothek.laden(pfad)
pruefe(b.werkzeuge == [] and b.eigene_werkstoffe == [], "ohne Datei nicht leer")

# Anlegen: nächste freie Nummer, auch mit Lücke.
t1 = b.neues_werkzeug()
t1.durchmesser, t1.schneiden, t1.schneidenlaenge = 12, 3, 26
t2 = b.neues_werkzeug()
t2.nummer = 5
t3 = b.neues_werkzeug()
pruefe((t1.nummer, t3.nummer) == (1, 2), f"Nummern {t1.nummer}, {t3.nummer}")
pruefe(b.naechste_nummer() == 3, f"nächste Nummer {b.naechste_nummer()}")
pruefe(b.mit_nummer(5, ausser=t1) is t2 and b.mit_nummer(5, ausser=t2) is None, "mit_nummer")

# Neues Werkzeug: Beispielwerte (Ø 12), gültig, als Beispiel gemerkt, nicht gespeichert.
neu = wz.Bibliothek().neues_werkzeug()
pruefe(
    (neu.art, neu.durchmesser, neu.schneiden, neu.schneidenlaenge) == (wz.SCHAFTFRAESER, 12, 3, 26)
    and neu.beispiel == {"durchmesser", "schneiden", "schneidenlaenge"},
    f"Beispielwerte: {neu} {neu.beispiel}",
)
pruefe("beispiel" not in neu.als_dict(), "Beispiel-Merker gespeichert")
pruefe(wz.Werkzeug.aus_dict(neu.als_dict()).beispiel == set(), "geladen noch Beispiel")
pruefe(set(wz.BEISPIELE) == set(wz.ARTEN), "nicht jede Art hat Beispielwerte")
# Andere Art: Beispielfelder und leere Felder bekommen ihre Beispiele, eigene Werte bleiben.
neu.durchmesser = 10
neu.beispiel.discard("durchmesser")
neu.art = wz.TORUSFRAESER
wz.beispielwerte_setzen(neu)
pruefe(
    (neu.durchmesser, neu.schneiden, neu.eckradius) == (10, 4, 1)
    and neu.beispiel == {"schneiden", "schneidenlaenge", "eckradius"},
    f"Torus: {neu} {neu.beispiel}",
)
neu.art = wz.BOHRER
wz.beispielwerte_setzen(neu)
pruefe(
    (neu.durchmesser, neu.schneidenlaenge, neu.eckradius) == (10, 60, 0)
    and neu.beispiel == {"schneiden", "schneidenlaenge"},
    f"Bohrer: {neu} {neu.beispiel}",
)
# Ein geladenes Werkzeug: nur leere Felder bekommen ein Beispiel.
vorhanden = wz.Werkzeug(durchmesser=8, schneiden=2, schneidenlaenge=20)
vorhanden.art = wz.TORUSFRAESER
wz.beispielwerte_setzen(vorhanden)
pruefe(
    (vorhanden.durchmesser, vorhanden.schneiden, vorhanden.schneidenlaenge, vorhanden.eckradius)
    == (8, 2, 20, 1)
    and vorhanden.beispiel == {"eckradius"},
    f"geladen → Torus: {vorhanden} {vorhanden.beispiel}",
)

# In inch: Listenzeile, Beispielname und Beispielwerte in Zoll – gespeichert metrisch.
from camaddon import einheiten  # noqa: E402

vorher_mass = einheiten.gewaehltes_masssystem()
einheiten.setze_masssystem(einheiten.ZOLL)
zoll = wz.Werkzeug(nummer=4, durchmesser=12.7, schneidenlaenge=25.4)
pruefe(wz.zeile(zoll) == "T4  Schaftfräser Ø 0.5 · z 3 · VHM", f"Zeile in Zoll: {wz.zeile(zoll)!r}")
pruefe(wz.beispielname(zoll) == "Schaftfräser T4 VHM D0.5 L1", f"Name: {wz.beispielname(zoll)!r}")
neu_zoll = wz.Bibliothek().neues_werkzeug()
pruefe(
    (neu_zoll.durchmesser, neu_zoll.schneidenlaenge) == (12.7, 25.4),
    f"Beispielwerte in Zoll: {neu_zoll.durchmesser}, {neu_zoll.schneidenlaenge}",
)
pruefe(set(wz.BEISPIELE_ZOLL) == set(wz.ARTEN), "nicht jede Art hat Beispiele in Zoll")
einheiten.setze_masssystem(vorher_mass)

# Die 26 Arten (Spezifikation Werkzeugarten): jede in einer Gruppe, Beispiele,
# Pflichtfelder und übliche Winkel nur für Felder, die die Art hat.
pruefe(len(wz.ARTEN) == 26, f"{len(wz.ARTEN)} Arten statt 26")
pruefe(
    sum(len(wz.arten_der_gruppe(g)) for g in wz.GRUPPEN) == 26, "Arten ohne oder in zwei Gruppen"
)
for art, daten in wz.ARTDATEN.items():
    for beispiele in (daten.beispiel, daten.beispiel_zoll):
        fremd = set(beispiele) - set(daten.felder)
        pruefe(not fremd, f"{art}: Beispiele für Felder, die es nicht gibt: {fremd}")
    pruefe(set(daten.pflicht) <= set(daten.felder), f"{art}: Pflichtfeld fehlt")
    pruefe(set(daten.ueblich) <= set(wz.WINKEL_FELDER) & set(daten.felder), f"{art}: üblich")
    pruefe(wz.art_text(art) and wz.art_text(art) != art, f"{art}: kein Name")
    for feld in daten.felder:
        pruefe(bool(wz.feld_text(feld, art)), f"{art}: Feld {feld} ohne Beschriftung")
pruefe(wz.feld_text("durchmesser", wz.ZENTRIERBOHRER) == "Zapfen-Ø", "Zapfen-Ø")
pruefe(wz.ueblich(wz.NC_ANBOHRER, "spitzenwinkel") == 90, "NC-Anbohrer 90°")
pruefe(wz.spitzenwinkel_fuer_cam(wz.Werkzeug(art=wz.ZENTRIERBOHRER)) == 60, "Zentrierbohrer 60°")
# Einsätze je Art (Spezifikation Werkzeugarten, 5): „eigen“ geht immer,
# Drehwerkzeuge und Taster haben keine Schnittwerte.
pruefe(set(wz.EINSAETZE_JE_ART) == set(wz.ARTEN), "Einsätze nicht für jede Art festgelegt")
pruefe(
    wz.einsatzarten(wz.SCHAFTFRAESER)
    == (wz.VOLLNUT, wz.SCHRUPPEN, wz.DYNAMISCH, wz.SCHLICHTEN, wz.EIGEN),
    f"Schaftfräser: {wz.einsatzarten(wz.SCHAFTFRAESER)}",
)
pruefe(wz.einsatzarten(wz.GEWINDEBOHRER_LINKS) == (wz.GEWINDEBOHREN, wz.EIGEN), "Gewindebohrer")
pruefe(wz.einsatzarten(wz.DREHWERKZEUG) is None, "Drehwerkzeug mit Einsätzen")
pruefe(wz.einsatzarten(wz.TASTER) is None, "Taster mit Einsätzen")
pruefe(wz.bohrend(wz.REIBAHLE) and not wz.bohrend(wz.PLANFRAESER), "bohrend")
plan = wz.vorlage(wz.Werkzeug(art=wz.PLANFRAESER, durchmesser=50, schneidenlaenge=6), wz.PLANEN)
pruefe((plan.ae, plan.ap) == (37.5, 2), f"Planen vorbelegt: {plan}")
pruefe(wz.Einsatz.aus_dict({"art": "gewindebohren"}).art == wz.GEWINDEBOHREN, "neue Einsatzart")
pruefe(all(wz.einsatzart_text(art) for art in wz.EINSATZARTEN), "Einsatzart ohne Namen")

# Liste und Name je Art – die alten Arten wie bisher.
gewinde = wz.Werkzeug(nummer=4, art=wz.GEWINDEBOHRER_RECHTS)
wz.beispielwerte_setzen(gewinde, neu=True)
pruefe(
    wz.zeile(gewinde) == "T4  Gewindebohrer rechts Ø 10 · P 1.5 · VHM",
    f"Zeile Gewindebohrer: {wz.zeile(gewinde)!r}",
)
pruefe(
    wz.beispielname(gewinde) == "Gewindebohrer rechts T4 VHM D10 P1.5 L20",
    f"Name Gewindebohrer: {wz.beispielname(gewinde)!r}",
)
dreh = wz.Werkzeug(nummer=9, art=wz.DREHWERKZEUG)
wz.beispielwerte_setzen(dreh, neu=True)
pruefe(wz.zeile(dreh) == "T9  Drehwerkzeug r 0.8 · VHM", f"Zeile Drehwerkzeug: {wz.zeile(dreh)!r}")
pruefe(wz.kurz(dreh) == "Drehwerkzeug", f"kurz: {wz.kurz(dreh)!r}")
pruefe(dreh.ausfuehrung == wz.RECHTS and "ausfuehrung" in dreh.beispiel, "Ausführung Beispiel")
# Zurück zum Fräser: Die Ausführung (Beispiel) wird wieder leer, z wieder das Beispiel.
dreh.art = wz.SCHAFTFRAESER
wz.beispielwerte_setzen(dreh)
pruefe((dreh.ausfuehrung, dreh.schneiden) == ("", 3), f"zurück zum Fräser: {dreh}")
dreh.art = wz.DREHWERKZEUG
wz.beispielwerte_setzen(dreh)
# Neue Felder werden gespeichert; unsinnige Werte begrenzt.
gewinde.flankenwinkel, gewinde.hals_d = 55, 7.5
geladen = wz.Werkzeug.aus_dict(gewinde.als_dict())
pruefe(
    (geladen.steigung, geladen.flankenwinkel, geladen.hals_d) == (1.5, 55, 7.5),
    f"neue Felder: {geladen}",
)
pruefe(wz.Werkzeug.aus_dict(dreh.als_dict()).ausfuehrung == wz.RECHTS, "Ausführung gespeichert")
kaputt = wz.Werkzeug.aus_dict({"kegelwinkel": 400, "steigung": -1, "ausfuehrung": "oben"})
pruefe(
    (kaputt.kegelwinkel, kaputt.steigung, kaputt.ausfuehrung) == (180, 0, ""),
    f"Grenzen: {kaputt}",
)
# Steigung in inch als Gänge je Zoll.
einheiten.setze_masssystem(einheiten.ZOLL)
pruefe(wz.steigung_text(25.4 / 13) == "13", f"13 Gänge: {wz.steigung_text(25.4 / 13)!r}")
pruefe(abs(wz.steigung_lesen(16) - 1.5875) < 1e-9, "16 Gänge je Zoll")
unc = wz.Werkzeug(nummer=6, art=wz.GEWINDEBOHRER_LINKS)
wz.beispielwerte_setzen(unc, neu=True)
pruefe(wz.zeile(unc) == "T6  Gewindebohrer links Ø 0.5 · 13 Gg/Zoll · VHM", wz.zeile(unc))
einheiten.setze_masssystem(vorher_mass)

# Kopieren: neue Kennung, nächste Nummer, gleiche Werte.
kopie = b.kopiere(t1)
pruefe(kopie.kennung != t1.kennung and kopie.nummer == 3, f"Kopie {kopie}")
pruefe((kopie.durchmesser, kopie.schneidenlaenge) == (12, 26), "Kopie ohne Werte")

# Listenzeile.
pruefe(wz.zeile(t1) == "T1  Schaftfräser Ø 12 · z 3 · VHM", f"Zeile: {wz.zeile(t1)!r}")
t3.durchmesser, t3.art, t3.schneiden = 8.5, wz.BOHRER, 2
pruefe(wz.zeile(t3) == "T2  Bohrer Ø 8.5 · z 2 · VHM", f"Zeile Bohrer: {wz.zeile(t3)!r}")
leer = wz.Werkzeug(nummer=9)
pruefe("Ø ?" in wz.zeile(leer), f"Zeile ohne Durchmesser: {wz.zeile(leer)!r}")

# Eigene Werkstoffe stehen vor den mitgelieferten.
eigen = ws.Werkstoff("eigen-1", kurzname="Hartholz", gruppe="Holz", iso="N", eigen=True)
b.eigene_werkstoffe.append(eigen)
pruefe(b.alle_werkstoffe()[0] is eigen, "eigener Werkstoff nicht vorn")
pruefe(len(b.alle_werkstoffe()) == len(ws.mitgelieferte()) + 1, "Werkstoffe gezählt")

# Speichern und wieder laden: gleicher Inhalt, Werkzeuge nach Nummer sortiert.
b.speichern(pfad)
geladen = wz.Bibliothek.laden(pfad)
pruefe(geladen.gleich(b), "nach Laden nicht gleich")
pruefe([w.nummer for w in geladen.werkzeuge] == [1, 2, 3, 5], "Reihenfolge in der Datei")
pruefe(geladen.eigene_werkstoffe[0].eigen, "eigener Werkstoff nach Laden nicht eigen")
pruefe(not os.path.exists(pfad + ".bak"), ".bak beim ersten Speichern")

# Zweites Speichern: die vorige Fassung bleibt als .bak.
t1.bezeichnung = "Hoffmann 12 mm"
b.speichern(pfad)
alt = json.loads(Path(pfad + ".bak").read_text("utf-8"))
pruefe(alt["werkzeuge"][0]["bezeichnung"] == "", ".bak enthält nicht die vorige Fassung")
pruefe(not os.path.exists(pfad + ".neu"), "Zwischendatei blieb liegen")

# kopie() ist unabhängig; gleich() merkt Änderungen.
k = b.kopie()
k.werkzeuge[0].durchmesser = 99
pruefe(not k.gleich(b) and b.werkzeuge[0].durchmesser == 12, "kopie() nicht unabhängig")

# Gesamtlänge und Schaft: leer geschätzt, eingetragen gespeichert; alte Dateien ohne sie laden.
t1.gesamtlaenge, t1.schaft = 83, 10
pruefe(wz.Werkzeug.aus_dict(t1.als_dict()) == t1, "Gesamtlänge/Schaft nicht gespeichert")
pruefe((wz.laenge_fuer_cam(t1), wz.schaft_fuer_cam(t1)) == (83, 10), "eingetragen")
alt_eintrag = {k: v for k, v in t1.als_dict().items() if k not in ("gesamtlaenge", "schaft")}
w = wz.Werkzeug.aus_dict(alt_eintrag)
pruefe((w.gesamtlaenge, w.schaft) == (0, 0), "alte Datei: Gesamtlänge/Schaft nicht 0")
pruefe(
    (wz.laenge_fuer_cam(w), wz.schaft_fuer_cam(w)) == (w.schneidenlaenge + 24, 12),
    f"geschätzt: {wz.laenge_fuer_cam(w)}, {wz.schaft_fuer_cam(w)}",
)
# Länge ab Spindelnase (für „Auf der Maschine prüfen“): gespeichert; alte Dateien ohne sie: 0.
t1.laenge_spindelnase = 142.5
pruefe(wz.Werkzeug.aus_dict(t1.als_dict()).laenge_spindelnase == 142.5, "Länge ab Spindelnase")
ohne = {k: v for k, v in t1.als_dict().items() if k != "laenge_spindelnase"}
pruefe(wz.Werkzeug.aus_dict(ohne).laenge_spindelnase == 0, "alte Datei: Länge ab Spindelnase")
pruefe(wz.Werkzeug.aus_dict({**ohne, "laenge_spindelnase": -3}).laenge_spindelnase == 0, "negativ")
t1.laenge_spindelnase = 0.0
pruefe(wz.geschaetzte_laenge(wz.Werkzeug(durchmesser=10)) == 40, "ohne Schneidenlänge: 2D + 2D")
pruefe(wz.geschaetzte_laenge(wz.Werkzeug(durchmesser=10, schneidenlaenge=2)) == 30, "mind. 3D")
# Mit Hals reicht das Werkzeug weiter unter den Schaft: 15 + 20 + 2 × 10.
gf = wz.Werkzeug(art=wz.GEWINDEFRAESER, durchmesser=10, schneidenlaenge=15, hals_laenge=20)
pruefe(wz.geschaetzte_laenge(gf) == 55, f"Gewindefräser: {wz.geschaetzte_laenge(gf)}")
# Leere Maße schätzt mass() je Art; ein Feld, das die Art nicht hat, zählt nicht.
sw = wz.Werkzeug(art=wz.SCHWALBENSCHWANZFRAESER, durchmesser=20, hals_laenge=50)
pruefe(wz.mass(sw, "hals_laenge") == 6 and wz.mass(sw, "hals_d") == 8, "Schwalbenschwanz")
pruefe(wz.mass(sw, "schneidenlaenge") == 5 and wz.schaft_fuer_cam(sw) == 20, "Schätzung")
taster = wz.Werkzeug(art=wz.TASTER, durchmesser=4)
pruefe(abs(wz.schaft_fuer_cam(taster) - 2.4) < 1e-9, "Taststift 0,6 × D")

# Spitzenwinkel des Bohrers: leer der übliche (118°), eingetragen gespeichert, begrenzt.
pruefe(wz.spitzenwinkel_fuer_cam(wz.Werkzeug(art=wz.BOHRER)) == 118, "üblicher Spitzenwinkel")
t3.spitzenwinkel = 130
pruefe(wz.Werkzeug.aus_dict(t3.als_dict()).spitzenwinkel == 130, "Spitzenwinkel nicht gespeichert")
pruefe(wz.spitzenwinkel_fuer_cam(t3) == 130, "eingetragener Spitzenwinkel")
t3.spitzenwinkel = 200
pruefe(wz.Werkzeug.aus_dict(t3.als_dict()).spitzenwinkel == 180, "Spitzenwinkel nicht begrenzt")
t3.spitzenwinkel = 0

# Warngrenze des Planers: Vorgabe 10 %, gespeichert; alte Dateien ohne sie: 10 %; 0 bleibt 0.
pruefe(wz.Werkzeug().ae_warngrenze == 10, "Vorgabe der Warngrenze")
t1.ae_warngrenze = 12
pruefe(wz.Werkzeug.aus_dict(t1.als_dict()).ae_warngrenze == 12, "Warngrenze nicht gespeichert")
ohne = {k: v for k, v in t1.als_dict().items() if k != "ae_warngrenze"}
pruefe(wz.Werkzeug.aus_dict(ohne).ae_warngrenze == 10, "alte Datei: Warngrenze nicht 10")
for gespeichert, soll in ((0, 0), (150, 100), (-5, 0)):
    t1.ae_warngrenze = gespeichert
    geladen_grenze = wz.Werkzeug.aus_dict(t1.als_dict()).ae_warngrenze
    pruefe(geladen_grenze == soll, f"Warngrenze {gespeichert} → {geladen_grenze} statt {soll}")
t1.ae_warngrenze = 10

# Suche: jedes Wort in Zeile oder Bezeichnung; Komma wie Punkt, Ø darf fehlen.
torus = wz.Werkzeug(nummer=5, art=wz.TORUSFRAESER, durchmesser=10.5, bezeichnung="Hoffmann")
for suche, soll in (
    ("", True),
    ("torus", True),
    ("10,5", True),
    ("ø10.5 hoff", True),
    ("T5", True),
    ("T6", False),
    ("torus 12", False),
):
    pruefe(wz.passt(torus, suche) == soll, f"Suche {suche!r}: {wz.passt(torus, suche)}")

# Ansehen ist keine Änderung: zum_bearbeiten(ALLE) legt eine leere Tabelle an.
b_ansehen = wz.Bibliothek([wz.Werkzeug(durchmesser=6)])
k_ansehen = b_ansehen.kopie()
k_ansehen.werkzeuge[0].zum_bearbeiten(wz.ALLE)
pruefe(k_ansehen.gleich(b_ansehen), "Ansehen eines Werkzeugs gilt als Änderung")
k_ansehen.werkzeuge[0].zum_bearbeiten(wz.ALLE).append(wz.Einsatz(art=wz.VOLLNUT))
pruefe(not k_ansehen.gleich(b_ansehen), "neue Zeile gilt nicht als Änderung")

# Eintauchwinkel: gespeichert, begrenzt auf 0 … 90°.
steil = wz.Werkzeug(durchmesser=10, eintauchwinkel=3)
pruefe(wz.Werkzeug.aus_dict(steil.als_dict()).eintauchwinkel == 3, "Eintauchwinkel gespeichert")
pruefe(wz.Werkzeug.aus_dict({"eintauchwinkel": 120}).eintauchwinkel == 90, "über 90°")

# Neuer Durchmesser: ae und ap aller Werkstoffe mit umrechnen, vc und fz bleiben.
zwoelf = wz.Werkzeug(durchmesser=12)
zwoelf.schnittwerte[wz.ALLE] = [wz.Einsatz(art=wz.VOLLNUT, ae=12, ap=6, vc=120, fz=0.05)]
zwoelf.eigene_anlegen("1.4301")[0].vc = 80
pruefe(zwoelf.hat_zustellungen(), "hat_zustellungen")
zwoelf.zustellungen_umrechnen(10 / 12)
for werkstoff, vc in ((wz.ALLE, 120), ("1.4301", 80)):
    e = zwoelf.einsaetze(werkstoff)[0]
    pruefe((e.ae, e.ap, e.vc, e.fz) == (10, 5, vc, 0.05), f"umgerechnet {werkstoff}: {e}")
pruefe(not wz.Werkzeug(durchmesser=6).hat_zustellungen(), "ohne Einsätze")

# Unlesbares im Eintrag: Standardwerte statt Absturz.
w = wz.Werkzeug.aus_dict({"nummer": "x", "art": "Hammer", "durchmesser": None, "schneidstoff": 3})
pruefe(
    (w.nummer, w.art, w.durchmesser, w.schneidstoff) == (1, wz.SCHAFTFRAESER, 0.0, wz.VHM), f"{w}"
)

# Bis P-2026-09-26-54 hieß der Kugelfräser „Radiusfräser“: Alte Dateien
# lesen ihn als Kugelfräser, gespeichert wird das neue Wort.
alt = wz.Werkzeug.aus_dict({"art": "radiusfraeser", "durchmesser": 8})
pruefe(
    alt.art == wz.KUGELFRAESER and alt.als_dict()["art"] == "kugelfraeser",
    f"alter Radiusfräser: {alt.art}",
)
pruefe(wz.art_text(wz.KUGELFRAESER) in ("Kugelfräser", "Ball end mill"), "Name Kugelfräser")

# Beschädigte Datei: wird beiseitegelegt, nichts geht verloren.
Path(pfad).write_text("{kaputt", "utf-8")
try:
    wz.Bibliothek.laden(pfad)
    fehler.append("beschädigte Datei: kein Fehler")
except wz.BeschaedigteDatei as f:
    pruefe(os.path.exists(f.beiseite) and not os.path.exists(pfad), "nicht beiseitegelegt")
    pruefe(Path(f.beiseite).read_text("utf-8") == "{kaputt", "Inhalt verändert")

# --- Schnittwerte -----------------------------------------------------------
f = wz.Werkzeug(durchmesser=12, schneiden=3, schneidenlaenge=26)
pruefe(f.einsaetze("1.4301") == [], "ohne Werte nicht leer")
pruefe(f.zum_bearbeiten("1.4301") is None, "ohne eigene Werte bearbeitbar")
alle = f.zum_bearbeiten(wz.ALLE)
alle.append(wz.vorlage(f, wz.VOLLNUT))
alle.append(wz.vorlage(f, wz.DYNAMISCH))
pruefe((alle[0].ae, alle[0].ap) == (12, 6), f"Vorlage Vollnut {alle[0]}")
pruefe((alle[1].ae, alle[1].ap) == (1.2, 24), f"Vorlage dynamisch {alle[1]}")
pruefe(
    wz.vorlage(wz.Werkzeug(durchmesser=10), wz.SCHLICHTEN).ap == 10, "Vorlage ohne Schneidenlänge"
)
pruefe(f.einsaetze("1.4301") is alle, "ohne eigene Werte gelten die für alle")
pruefe(not f.hat_eigene("1.4301") and not f.hat_eigene(wz.ALLE), "hat_eigene")

eigene = f.eigene_anlegen("1.4301")
eigene[0].vc = 80
pruefe(alle[0].vc == 0 and f.einsaetze("1.4301")[0].vc == 80, "eigene Werte nicht unabhängig")
pruefe(f.einsaetze("1.0503") is alle, "anderer Werkstoff erbt nicht")
pruefe(f.hat_eigene("1.4301") and f.zum_bearbeiten("1.4301") is eigene, "eigene Werte")
pruefe(wz.einsatz_name(eigene[1]) == "Schruppen dynamisch", wz.einsatz_name(eigene[1]))

# Werkzeugname: leer gilt der Beispielname (Zahlen mit Punkt), eingetragen der eigene.
n = wz.Werkzeug(nummer=1, durchmesser=10.5, schneidenlaenge=30)
pruefe(
    wz.beispielname(n) == "Schaftfräser T1 VHM D10.5 L30", f"Beispielname {wz.beispielname(n)!r}"
)
pruefe(wz.anzeigename(n) == wz.beispielname(n) and "Fräser" not in wz.zeile(n)[:6], "ohne Namen")
pruefe(wz.passt(n, "d10.5 l30"), "Suche findet den Beispielnamen nicht")
n.name = "Fräser VHM 10,5"
pruefe(wz.zeile(n).startswith("T1  Fräser VHM 10,5 · Schaftfräser"), f"Zeile: {wz.zeile(n)!r}")
pruefe(wz.anzeigename(n) == "Fräser VHM 10,5" and wz.passt(n, "fräser vhm"), "eigener Name")
zwilling = wz.Werkzeug(nummer=2, name="fräser vhm 10,5 ")
pruefe(wz.Bibliothek([n, zwilling]).mit_name(n.name, ausser=n) is zwilling, "gleicher Name")
pruefe(wz.Bibliothek([n]).mit_name("", ausser=None) is None, "leerer Name zählt nicht")
pruefe(wz.Werkzeug.aus_dict(n.als_dict()).name == "Fräser VHM 10,5", "Name nach Speichern")
pruefe(wz.Werkzeug.aus_dict({"nummer": 4}).name == "", "alte Datei ohne Namen")

# Name einer neuen Zeile: frei bleibt er, sonst mit Nummer; die Kopie von „… 2“ wird „… 3“.
pruefe(wz.name_fuer_neuen(wz.Einsatz(art=wz.SCHLICHTEN), eigene) == "", "freier Name nummeriert")
pruefe(
    wz.name_fuer_neuen(eigene[1], eigene) == "Schruppen dynamisch 2",
    f"Kopie: {wz.name_fuer_neuen(eigene[1], eigene)!r}",
)
zweite = wz.Einsatz(art=wz.DYNAMISCH, name="Schruppen dynamisch 2")
pruefe(wz.name_fuer_neuen(zweite, eigene + [zweite]) == "Schruppen dynamisch 3", "Kopie der 2")
pruefe(wz.name_fuer_neuen(eigene[1], eigene + [zweite]) == "Schruppen dynamisch 3", "2 vergeben")
pruefe(wz.name_fuer_neuen(wz.Einsatz(name="vollnut"), eigene) == "vollnut 2", "groß/klein gleich")
zwoelf = wz.Einsatz(name="Vollnut 12")
pruefe(wz.name_fuer_neuen(zwoelf, [zwoelf]) == "Vollnut 13", "Nummer am Ende weitergezählt")

eigene[1].name = "HPC 2xD"
pruefe(wz.einsatz_name(eigene[1]) == "HPC 2xD", "eigener Name")

# Speichern und Laden mit Schnittwerten; Kopie nimmt sie mit.
b2 = wz.Bibliothek([f])
b2.speichern(pfad)
g = wz.Bibliothek.laden(pfad).werkzeuge[0]
pruefe(g.einsaetze("1.4301")[0].vc == 80 and g.einsaetze(wz.ALLE)[1].ae == 1.2, "Laden")
pruefe(g.einsaetze("1.4301")[1].name == "HPC 2xD", "Name nach Laden")
k = b2.kopiere(f)
k.einsaetze("1.4301")[0].vc = 99
pruefe(f.einsaetze("1.4301")[0].vc == 80, "Kopie teilt Schnittwerte")
f.eigene_loeschen("1.4301")
pruefe(not f.hat_eigene("1.4301") and f.einsaetze("1.4301") is alle, "eigene löschen")
f.eigene_loeschen(wz.ALLE)
pruefe(f.einsaetze(wz.ALLE) is alle, "„für alle“ lässt sich nicht als eigene löschen")
e = wz.Einsatz.aus_dict({"art": "zaubern", "ae": "x", "vc": -5})
pruefe((e.art, e.ae, e.vc) == (wz.EIGEN, 0.0, 0.0), f"unlesbarer Einsatz: {e}")

sprache.setze_sprache(vorher)
# Manuels Standardfräser (2026-10-01): die eine Definition für alle Werkzeugwege.
standard = wz.standardwerkzeug()
pruefe(
    standard.nummer == 1
    and standard.durchmesser == 12.0
    and standard.schneiden == 4
    and standard.schneidenlaenge == 26.0
    and standard.eintauchwinkel == 3.0,
    f"Standardfräser: {standard}",
)
einsaetze = {e.art: e for e in standard.einsaetze(wz.ALLE)}
pruefe(
    set(einsaetze) == {wz.PLANEN, wz.SCHRUPPEN, wz.SCHLICHTEN}
    and all((e.ap, e.vc, e.fz) == (25.0, 85.0, 0.1) for e in einsaetze.values())
    and einsaetze[wz.SCHRUPPEN].ae == 1.5
    and einsaetze[wz.PLANEN].ae == 1.5
    and einsaetze[wz.SCHLICHTEN].ae == 0.3,
    f"Standardfräser, Einsätze: {einsaetze}",
)
pruefe(wz.standardwerkzeug(7).nummer == 7, "Standardfräser mit Nummer")

# Die Drehrichtung am Werkzeug (Manuel, 2026-10-02): jeder Fräser und Bohrer hat sie, leer gilt
# die übliche – links nur der Linksgewindebohrer –, gespeichert wie eingetragen.
pruefe(not wz.dreht_links(wz.Werkzeug(art=wz.SCHAFTFRAESER)), "Schaftfräser dreht links")
pruefe(wz.dreht_links(wz.Werkzeug(art=wz.GEWINDEBOHRER_LINKS)), "Linksgewindebohrer rechts")
links = wz.Werkzeug(art=wz.SCHAFTFRAESER, drehrichtung=wz.LINKS)
pruefe(wz.dreht_links(links), "eingetragen links, gilt nicht")
wieder = wz.Werkzeug.aus_dict(links.als_dict())
pruefe(wieder.drehrichtung == wz.LINKS, f"gespeichert: {wieder.drehrichtung!r}")
pruefe(wz.Werkzeug.aus_dict({"drehrichtung": "quer"}).drehrichtung == "", "unlesbar")
for art, soll in ((wz.SCHAFTFRAESER, True), (wz.BOHRER, True), (wz.GEWINDEBOHRER_RECHTS, True),
                  (wz.DREHWERKZEUG, False), (wz.TASTER, False)):  # fmt: skip
    pruefe(wz.hat_feld(wz.Werkzeug(art=art), wz.DREHRICHTUNG) == soll, f"{art}: Feld Drehrichtung")

if fehler:
    raise AssertionError("\n".join(fehler))
print("OK", os.path.basename(__file__))
