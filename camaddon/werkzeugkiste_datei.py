# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Werkzeugkiste um eigene Dateien erweitern (T-007; Manuel, 2026-10-04: „gibt's einen
Importer … wo du über JSON was hinzufügen lassen kannst“; 2026-10-10: „wichtig ist mir hierbei,
zu erkennen, wenn es Doppelimporte gibt … wenn jemand 3 mal den Schaftfräser 12 von Hoffmann
einpflegen will, ist das unnötig – daher muss das schon exakt geschaut und verglichen werden“).

Das Format steht in docs/werkzeugkiste_json.md. lesen() prüft eine Datei und baut aus ihr Reihen
(werkzeugkiste.Reihe) – mit Fehlern (das bleibt draußen), Hinweisen (übernommen, aber …) und
Dubletten (ausgelassen, weil es das schon gibt). einlesen() legt die geprüfte Datei in den Ordner
CamAddon/werkzeugkiste/ beim Benutzer; eingelesene() liest alle Dateien dort,
werkzeugkiste.reihen() hängt sie an die eingebauten Reihen.

Dubletten, genau verglichen – in der Datei selbst und gegen alles, was die Kiste schon hat:
1. gleiche Kennung: die Reihe ersetzt eine früher aus derselben Datei eingelesene; eine Kennung
   der eingebauten Kiste oder einer anderen Datei ist belegt (Fehler, Reihe bleibt draußen);
2. gleicher Hersteller und gleiche Artikelnummer: dieselbe Größe – ausgelassen;
3. gleiche Art, Hersteller, Marke, Beschichtung, Schneidstoff, Schneiden und alle Maße gleich:
   dasselbe Werkzeug unter anderer Nummer – ausgelassen.

Läuft ohne Oberfläche.
"""

import json
import os
import re
import shutil
from dataclasses import dataclass, field, fields, replace

import FreeCAD

from . import werkstoffe as ws
from . import werkzeuge as wz
from . import werkzeugkiste as wk
from .sprache import tr

FORMAT = "camaddon-werkzeugkiste"
VERSION = 1
ORDNERNAME = "werkzeugkiste"  # neben werkzeugverwaltung.json
BEISPIEL = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "beispiele",
    "werkzeugkiste_beispiel.json",
)
PFLICHT = ("kennung", "art", "hersteller", "titel", "quelle", "groessen")
_KENNUNG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_WERKZEUGFELDER = {f.name for f in fields(wz.Werkzeug)} | {"auskragung"}
# Felder des Werkzeugs, die eine Datei nicht setzt (sie kommen aus der Reihe oder gehören dem Benutzer).
_NICHT_AUS_DATEI = {
    "kennung", "nummer", "art", "schnittwerte", "beispiel", "name", "bezeichnung", "hersteller",
    "artikel", "link", "katalog", "halter", "laenge_spindelnase", "ae_warngrenze",
}  # fmt: skip
_TEXTE = ("artikel", "name", "link", "beschichtung", "schneidstoff", "ausfuehrung", "drehrichtung")
_ANDERE_NAMEN = {"auskraglaenge": "auskragung", "nutzlaenge": "auskragung", "zaehne": "schneiden"}
# Schneidstoffe, wie Kataloge sie schreiben – HSS-E, HSS-Co, PM sind HSS; HM, Hartmetall, VHM.
_SCHNEIDSTOFFE = {
    "vhm": wz.VHM, "hm": wz.VHM, "hartmetall": wz.VHM, "vollhartmetall": wz.VHM, "carbide": wz.VHM,
    "solid carbide": wz.VHM, "hss": wz.HSS, "hss-e": wz.HSS, "hsse": wz.HSS, "hss-e-pm": wz.HSS,
    "hss-pm": wz.HSS, "hss-co": wz.HSS, "hssco": wz.HSS, "hss co 5": wz.HSS, "hss co 8": wz.HSS,
    "hss co 10": wz.HSS, "hss-co5": wz.HSS, "hss-co8": wz.HSS, "hss-co10": wz.HSS,
}  # fmt: skip
_UMLAUTE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})
_WERTE = ("vc", "fz", "f", "ap", "ap_d", "ae", "ae_d")


def ordner():
    """Der Ordner der eingelesenen Dateien beim Benutzer."""
    return os.path.join(os.path.dirname(wz.datei_pfad()), ORDNERNAME)


def dateien():
    """Die eingelesenen Dateien, in der Reihenfolge ihrer Namen."""
    pfad = ordner()
    if not os.path.isdir(pfad):
        return []
    return sorted(
        os.path.join(pfad, name) for name in os.listdir(pfad) if name.lower().endswith(".json")
    )


@dataclass
class Pruefung:
    """Was lesen() aus einer Datei macht: die brauchbaren Reihen und je ein Satz zu allem, was
    nicht glatt ging."""

    datei: str  # der Name der Datei (ohne Ordner)
    reihen: list = field(default_factory=list)  # [werkzeugkiste.Reihe]
    fehler: list = field(default_factory=list)  # das bleibt draußen
    hinweise: list = field(default_factory=list)  # übernommen, aber …
    doppelt: list = field(default_factory=list)  # Größen, ausgelassen, weil es sie schon gibt
    ersetzt: list = field(default_factory=list)  # Kennungen, die eine frühere Fassung ersetzen
    ziel: str = ""  # wohin einlesen() die Datei gelegt hat

    @property
    def anzahl(self):
        return sum(r.anzahl for r in self.reihen)


# --- Lesen und Prüfen -----------------------------------------------------------------------


def lesen(pfad, vorhandene=None):
    """Prüft die Datei und baut ihre Reihen; `vorhandene`: die Reihen, gegen die Dubletten
    gesucht werden (ohne: alle der Kiste außer denen aus einer Datei gleichen Namens – die
    ersetzt diese). Gibt eine Pruefung zurück; eine unlesbare Datei hat nur Fehler."""
    name = os.path.basename(pfad)
    pruefung = Pruefung(datei=name)
    try:
        with open(pfad, encoding="utf-8") as datei:
            daten = json.load(datei)
    except (OSError, ValueError) as fehler:
        pruefung.fehler.append(tr("wd.fehler.json", fehler=fehler))
        return pruefung
    if not isinstance(daten, dict) or daten.get("format") != FORMAT:
        pruefung.fehler.append(tr("wd.fehler.format", format=FORMAT))
        return pruefung
    version = daten.get("version")
    if not isinstance(version, int) or isinstance(version, bool) or version > VERSION:
        pruefung.fehler.append(tr("wd.fehler.version", version=version, bekannt=VERSION))
        return pruefung
    reihen = daten.get("reihen")
    if not isinstance(reihen, list) or not reihen:
        pruefung.fehler.append(tr("wd.fehler.reihen"))
        return pruefung
    fruehere = set()
    if vorhandene is None:  # eine Datei gleichen Namens im Ordner ersetzt diese
        alle = wk.reihen()
        vorhandene = [r for r in alle if r.datei != name]
        fruehere = {r.kennung for r in alle if r.datei == name}
    index = _Index(vorhandene)
    gesehen = set()
    for nummer, daten_reihe in enumerate(reihen, 1):
        reihe = _reihe(daten_reihe, nummer, name, pruefung, gesehen, index)
        if reihe is None:
            continue
        if reihe.kennung in fruehere:
            pruefung.ersetzt.append(reihe.kennung)
        pruefung.reihen.append(reihe)
    return pruefung


def _reihe(daten, nummer, name, pruefung, gesehen, index):
    """Eine Reihe aus ihren Daten – None, wenn sie draußen bleibt (Fehler in `pruefung`)."""
    stelle = tr("wd.stelle.reihe", nummer=nummer, kennung=str(daten.get("kennung") or "?"))
    if not isinstance(daten, dict):
        pruefung.fehler.append(tr("wd.fehler.keine_reihe", stelle=stelle))
        return None
    fehlt = [f for f in PFLICHT if not daten.get(f)]
    if fehlt:
        pruefung.fehler.append(tr("wd.fehler.pflicht", stelle=stelle, felder=", ".join(fehlt)))
        return None
    kennung = str(daten["kennung"])
    if not _KENNUNG.fullmatch(kennung):
        pruefung.fehler.append(tr("wd.fehler.kennung", stelle=stelle))
        return None
    if kennung in gesehen:
        pruefung.fehler.append(tr("wd.fehler.kennung_doppelt", stelle=stelle))
        return None
    gesehen.add(kennung)
    belegt = index.kennungen.get(kennung)
    if belegt is not None:
        wo = belegt or tr("wd.eingebaut")
        pruefung.fehler.append(tr("wd.fehler.kennung_belegt", stelle=stelle, wo=wo))
        return None
    art = wz.ALTE_ARTEN.get(daten["art"], daten["art"])
    if art not in wz.ARTEN:
        pruefung.fehler.append(tr("wd.fehler.art", stelle=stelle, art=daten["art"]))
        return None
    groessen = daten["groessen"]
    if not isinstance(groessen, list) or not all(isinstance(g, dict) for g in groessen):
        pruefung.fehler.append(tr("wd.fehler.groessen", stelle=stelle))
        return None
    hersteller = str(daten["hersteller"]).strip()
    marke = str(daten.get("marke") or "").strip()
    titel = str(daten["titel"]).strip()
    gemeinsam = _felder(daten.get("gemeinsam") or {}, stelle, pruefung)
    werte_reihe = _schnittwerte(daten.get("schnittwerte"), art, stelle, pruefung)
    mit_werten = bool(werte_reihe)
    fertige = []
    for i, daten_groesse in enumerate(groessen, 1):
        stelle_g = tr("wd.stelle.groesse", stelle=stelle, nummer=i)
        groesse = _felder(daten_groesse, stelle_g, pruefung)
        for feld in _TEXTE:
            if feld in daten_groesse and feld not in groesse:
                groesse[feld] = str(daten_groesse[feld]).strip()
        werte_groesse = _schnittwerte(daten_groesse.get("schnittwerte"), art, stelle_g, pruefung)
        mit_werten = mit_werten or bool(werte_groesse)
        preis = daten_groesse.get("preis_netto")
        groesse["_werte"] = _vereint(werte_reihe, werte_groesse)
        groesse["_preis"] = float(preis) if isinstance(preis, (int, float)) else 0.0
        fertige.append(groesse)
    if not fertige:
        pruefung.fehler.append(tr("wd.fehler.groessen", stelle=stelle))
        return None
    quelle = tr("wd.quelle", quelle=str(daten["quelle"]).strip(), datei=name)
    reihe = wk.Reihe(
        kennung=kennung,
        art=art,
        hersteller=hersteller,
        titel=titel,
        quelle=quelle,
        groessen=tuple(
            _groesse(g, gemeinsam, titel, marke, hersteller, mit_werten, art) for g in fertige
        ),
        gemeinsam=_gemeinsam(gemeinsam),
        bezeichnung=titel,
        link=str(daten.get("link") or "").strip(),
        katalog=str(daten.get("katalog") or "").strip(),
        schnittwerte=wz.einsatzarten(art) is not None,
        marke=marke,
        datei=name,
    )
    # Die Werkzeuge der Reihe – erst ohne Katalogwerte: Sie geben die Maße für den Vergleich und
    # die Richtwerte, mit denen fehlende vc oder fz einer Datei aufgefüllt werden.
    werkzeuge = wk.werkzeuge(reihe)
    katalogwerte = {}
    behalten = []
    for i, (groesse, werkzeug, daten_g) in enumerate(
        zip(reihe.groessen, werkzeuge, fertige, strict=True), 1
    ):
        stelle_g = tr("wd.stelle.groesse", stelle=stelle, nummer=i)
        grund = index.dublette(reihe, groesse, werkzeug)
        if grund is not None:
            pruefung.doppelt.append(
                tr("wd.doppelt", stelle=stelle_g, name=_name(werkzeug), grund=grund)
            )
            continue
        index.merke(reihe, groesse, werkzeug)
        behalten.append(groesse)
        if reihe.schnittwerte and daten_g["_werte"]:
            katalogwerte[float(werkzeug.durchmesser)] = _katalog(werkzeug, daten_g["_werte"])
    if not behalten:
        pruefung.hinweise.append(tr("wd.doppelt.reihe", stelle=stelle))  # keine Größe: ein Hinweis
        return None
    return replace(reihe, groessen=tuple(behalten), katalogwerte=katalogwerte)


def _felder(daten, stelle, pruefung):
    """Die Felder einer Größe oder von `gemeinsam` als Werkzeugfelder: Zahlen geprüft, andere
    Schreibweisen (Umlaute, „auskraglaenge“) umgesetzt, Unbekanntes ausgelassen – je mit Hinweis."""
    ergebnis = {}
    if not isinstance(daten, dict):
        pruefung.hinweise.append(tr("wd.hinweis.kein_dict", stelle=stelle))
        return ergebnis
    for feld, wert in daten.items():
        name = str(feld).strip().lower().translate(_UMLAUTE)
        name = _ANDERE_NAMEN.get(name, name)
        if name in ("schnittwerte", "preis_netto", "beschichtung"):
            if name == "beschichtung":
                ergebnis[name] = str(wert).strip()
            continue
        if name in ("artikel", "name", "link"):
            ergebnis[name] = str(wert).strip()
            continue
        if name not in _WERKZEUGFELDER or name in _NICHT_AUS_DATEI:
            pruefung.hinweise.append(tr("wd.hinweis.unbekannt", stelle=stelle, feld=feld))
            continue
        if name != feld:
            pruefung.hinweise.append(
                tr("wd.hinweis.umbenannt", stelle=stelle, feld=feld, name=name)
            )
        if name == "schneidstoff":
            schneidstoff = _SCHNEIDSTOFFE.get(re.sub(r"\s+", " ", str(wert).strip().lower()))
            if schneidstoff is None:
                pruefung.hinweise.append(tr("wd.hinweis.schneidstoff", stelle=stelle, wert=wert))
                continue
            ergebnis[name] = schneidstoff
        elif name in ("ausfuehrung", "drehrichtung"):
            ergebnis[name] = str(wert).strip().lower()
        elif name == "schneiden":
            if isinstance(wert, bool) or not isinstance(wert, (int, float)) or wert < 0:
                pruefung.hinweise.append(tr("wd.hinweis.wert", stelle=stelle, feld=feld, wert=wert))
                continue
            ergebnis[name] = int(wert)
        else:
            if isinstance(wert, bool) or not isinstance(wert, (int, float)) or wert < 0:
                pruefung.hinweise.append(tr("wd.hinweis.wert", stelle=stelle, feld=feld, wert=wert))
                continue
            ergebnis[name] = float(wert)
    return ergebnis


def _schnittwerte(daten, art, stelle, pruefung):
    """{Klasse: {Einsatz: {Wert: Zahl}}} aus dem Abschnitt `schnittwerte` – nur bekannte Klassen,
    Einsätze der Art und Werte; alles andere mit Hinweis ausgelassen."""
    if not daten:
        return {}
    if not isinstance(daten, dict):
        pruefung.hinweise.append(tr("wd.hinweis.schnittwerte", stelle=stelle))
        return {}
    arten = wz.einsatzarten(art)
    if arten is None:
        pruefung.hinweise.append(
            tr("wd.hinweis.ohne_einsaetze", stelle=stelle, art=wz.art_text(art))
        )
        return {}
    ergebnis = {}
    for klasse, einsaetze in daten.items():
        if klasse not in ws.KLASSEN:
            pruefung.hinweise.append(tr("wd.hinweis.klasse", stelle=stelle, klasse=klasse))
            continue
        if not isinstance(einsaetze, dict):
            pruefung.hinweise.append(tr("wd.hinweis.schnittwerte", stelle=stelle))
            continue
        for einsatz, werte in einsaetze.items():
            if einsatz not in arten:
                pruefung.hinweise.append(
                    tr("wd.hinweis.einsatz", stelle=stelle, einsatz=einsatz, art=wz.art_text(art))
                )
                continue
            if not isinstance(werte, dict):
                pruefung.hinweise.append(tr("wd.hinweis.schnittwerte", stelle=stelle))
                continue
            gut = {}
            for wert, zahl in werte.items():
                if (
                    wert not in _WERTE
                    or isinstance(zahl, bool)
                    or not isinstance(zahl, (int, float))
                ):
                    pruefung.hinweise.append(
                        tr(
                            "wd.hinweis.wert",
                            stelle=stelle,
                            feld=f"{klasse}/{einsatz}/{wert}",
                            wert=zahl,
                        )
                    )
                    continue
                gut[wert] = float(zahl)
            if gut:
                ergebnis.setdefault(klasse, {})[einsatz] = gut
    return ergebnis


def _vereint(reihe, groesse):
    """Die Schnittwerte der Größe über denen der Reihe, Wert für Wert."""
    ergebnis = {k: {e: dict(w) for e, w in v.items()} for k, v in reihe.items()}
    for klasse, einsaetze in groesse.items():
        for einsatz, werte in einsaetze.items():
            ergebnis.setdefault(klasse, {}).setdefault(einsatz, {}).update(werte)
    return ergebnis


def _gemeinsam(felder):
    """Die gemeinsamen Felder für werkzeugkiste.Reihe: Maße und Schneidstoff; die Beschichtung
    nur zum Vergleichen (werkzeuge() setzt Felder mit „_“ nicht ans Werkzeug)."""
    ergebnis = {k: v for k, v in felder.items() if k not in _TEXTE or k == "schneidstoff"}
    if felder.get("beschichtung"):
        ergebnis["_beschichtung"] = felder["beschichtung"]
    return ergebnis


def _groesse(daten, gemeinsam, titel, marke, hersteller, mit_werten, art):
    """Die Felder einer Größe, wie werkzeugkiste.werkzeuge() sie nimmt: Maße, Name, Artikel,
    Link, Bezeichnung (Titel, Beschichtung, Preis; ohne Schnittwerte in der Datei: Richtwerte);
    die Beschichtung dazu als „_beschichtung“ – nur zum Vergleichen."""
    werte = {k: v for k, v in daten.items() if not k.startswith("_") and k != "beschichtung"}
    beschichtung = daten.get("beschichtung") or gemeinsam.get("beschichtung") or ""
    if beschichtung:
        werte["_beschichtung"] = beschichtung
    wer = marke or hersteller
    artikel = werte.get("artikel", "")
    if not werte.get("name"):
        d = werte.get("durchmesser")
        werte["name"] = f"{wer} {artikel}".strip() if artikel else f"{wer} D{d:g}".strip()
    teile = [titel]
    if beschichtung:
        teile.append(beschichtung)
    if daten.get("_preis"):
        teile.append(tr("wd.preis", preis=f"{daten['_preis']:.2f}"))
    if not mit_werten and wz.einsatzarten(art) is not None:
        teile.append(wk.RICHTWERTE)
    werte["bezeichnung"] = " · ".join(teile)
    return werte


def _katalog(werkzeug, werte):
    """{Klasse: {Einsatz: (vc, fz, ap, ae)}} für werkzeugkiste (katalogwerte): f wird fz je
    Schneide, ap_d und ae_d Vielfache des Durchmessers; was fehlt, sind die Richtwerte – vc nie
    über der höchsten, die die Datei für die Klasse nennt."""
    d = float(werkzeug.durchmesser)
    ergebnis = {}
    for klasse, einsaetze in werte.items():
        hoechste = max((w["vc"] for w in einsaetze.values() if "vc" in w), default=0.0)
        for einsatz, w in einsaetze.items():
            richtwert = wk.richtwert(werkzeug, einsatz, klasse)
            vc = w.get("vc")
            if vc is None:
                vc = richtwert.vc if richtwert is not None else 0.0
                if hoechste:
                    vc = min(vc, hoechste)
            fz = w.get("fz")
            if fz is None and "f" in w:
                fz = w["f"] / max(werkzeug.schneiden, 1)
            if fz is None:
                fz = richtwert.fz if richtwert is not None else 0.0
            ap = w.get("ap") if "ap" in w else (w["ap_d"] * d if "ap_d" in w else None)
            ae = w.get("ae") if "ae" in w else (w["ae_d"] * d if "ae_d" in w else None)
            ergebnis.setdefault(klasse, {})[einsatz] = (vc, fz, ap, ae)
    return ergebnis


def _name(werkzeug):
    return werkzeug.name or wz.beispielname(werkzeug)


# --- Dubletten ------------------------------------------------------------------------------


def _artikel_schluessel(hersteller, artikel):
    return (hersteller.strip().lower(), re.sub(r"\s+", "", artikel).lower()) if artikel else None


def _masse_schluessel(reihe, groesse, werkzeug):
    """Art, Hersteller, Marke, Beschichtung, Schneidstoff, Schneiden und alle Maße – gleich heißt:
    dasselbe Werkzeug."""
    beschichtung = str(groesse.get("_beschichtung") or reihe.gemeinsam.get("_beschichtung") or "")
    masse = tuple(
        (feld, round(float(getattr(werkzeug, feld, 0.0) or 0.0), 4))
        for feld in wz.ZAHLEN_FELDER
        if feld != "auskragung"
    )
    return (
        werkzeug.art,
        werkzeug.hersteller.strip().lower(),
        reihe.marke.strip().lower(),
        beschichtung.strip().lower(),
        werkzeug.schneidstoff,
        int(werkzeug.schneiden),
        masse,
    )


class _Index:
    """Was die Kiste schon hat – zum Vergleichen: Kennungen (mit der Datei, aus der sie kommen;
    "" eingebaut), Artikelnummern je Hersteller und die vollständigen Maße."""

    def __init__(self, reihen):
        self.kennungen = {}
        self.artikel = {}
        self.masse = {}
        for reihe in reihen:
            self.kennungen[reihe.kennung] = reihe.datei
            for groesse, werkzeug in zip(reihe.groessen, wk.werkzeuge(reihe), strict=True):
                self.merke(reihe, groesse, werkzeug)

    def merke(self, reihe, groesse, werkzeug):
        schluessel = _artikel_schluessel(werkzeug.hersteller, werkzeug.artikel)
        wo = tr("wd.wo", name=_name(werkzeug), kennung=reihe.kennung)
        if schluessel is not None:
            self.artikel.setdefault(schluessel, wo)
        # Je Maßsatz die Artikelnummern, unter denen er schon da ist ("" ohne Nummer).
        self.masse.setdefault(_masse_schluessel(reihe, groesse, werkzeug), {}).setdefault(
            schluessel[1] if schluessel else "", wo
        )

    def dublette(self, reihe, groesse, werkzeug):
        """Der Grund, warum diese Größe schon da ist – oder None. Gleiche Maße zählen nur, wenn
        nicht beide eine Artikelnummer haben und die verschieden sind: Zwei Artikel mit gleichen
        Maßen sind zwei Produkte (Beschichtung, Geometrie, Preis); eine Größe ohne Nummer mit
        denselben Maßen ist dasselbe Werkzeug."""
        schluessel = _artikel_schluessel(werkzeug.hersteller, werkzeug.artikel)
        if schluessel is not None and schluessel in self.artikel:
            return tr("wd.grund.artikel", artikel=werkzeug.artikel, wo=self.artikel[schluessel])
        gleiche = self.masse.get(_masse_schluessel(reihe, groesse, werkzeug)) or {}
        if not gleiche:
            return None
        if schluessel is None:
            return tr("wd.grund.masse", wo=next(iter(gleiche.values())))
        if "" in gleiche:
            return tr("wd.grund.masse", wo=gleiche[""])
        return None


# --- Der Ordner beim Benutzer ---------------------------------------------------------------

_gelesen = {}  # Pfad → (Größe, Änderungszeit, [Reihe])


def eingelesene():
    """Die Reihen aller Dateien im Ordner – jede gegen die eingebauten und die Dateien davor
    geprüft; was dabei herausfällt, sagt die Konsole. Gelesen wird nur, was sich geändert hat."""
    ergebnis = []
    vorhandene = list(wk.eingebaute())
    for pfad in dateien():
        try:
            stat = os.stat(pfad)
            stempel = (stat.st_size, stat.st_mtime_ns)
        except OSError:
            continue
        gemerkt = _gelesen.get(pfad)
        if gemerkt is None or gemerkt[0] != stempel:
            pruefung = lesen(pfad, vorhandene)
            for satz in pruefung.fehler + pruefung.doppelt:
                FreeCAD.Console.PrintWarning(f"CAM-Addon: {pruefung.datei}: {satz}\n")
            _gelesen[pfad] = (stempel, pruefung.reihen)
        reihen = _gelesen[pfad][1]
        ergebnis.extend(reihen)
        vorhandene.extend(reihen)
    return ergebnis


def vergessen():
    """Liest beim nächsten Mal alles neu (nach einlesen(), in Prüfungen)."""
    _gelesen.clear()


def einlesen(pfad):
    """Prüft die Datei und legt sie in den Ordner, wenn sie brauchbare Reihen hat – eine Datei
    gleichen Namens dort ersetzt sie. Gibt die Pruefung zurück (`ziel` gesetzt, wenn sie liegt)."""
    pruefung = lesen(pfad)
    if not pruefung.reihen:
        return pruefung
    ziel = os.path.join(ordner(), pruefung.datei)
    os.makedirs(ordner(), exist_ok=True)
    if not (os.path.exists(ziel) and os.path.samefile(pfad, ziel)):
        shutil.copyfile(pfad, ziel)
    vergessen()
    pruefung.ziel = ziel
    return pruefung


def entfernen(name):
    """Nimmt die eingelesene Datei `name` aus dem Ordner; True, wenn sie da war."""
    ziel = os.path.join(ordner(), os.path.basename(name))
    if not os.path.isfile(ziel):
        return False
    os.remove(ziel)
    vergessen()
    return True


def vorlage_schreiben(pfad):
    """Schreibt das vollständige Beispiel (beispiele/werkzeugkiste_beispiel.json) als Vorlage."""
    shutil.copyfile(BEISPIEL, pfad)
    return pfad
