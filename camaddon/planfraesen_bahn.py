# SPDX-License-Identifier: LGPL-2.1-or-later
"""Die Bahn „Planfräsen“ (W-006 S3, 4.1 Punkt 1): eine Fläche oben eben – Zeilen hin und her,
in Lagen vom Rohteil bis auf die Fläche plus Aufmaß.

- Je gewählter ebener Fläche nach oben (hoehenfeld.ebenen_oben) die Lagen in gleichen
  Schritten von höchstens der Zustellung, von der Oberkante (das Rohteil) bis auf ihre Höhe
  plus Aufmaß.
- Zeilen in der längeren Richtung der Fläche (längs x oder längs y), quer höchstens den
  Zeilenabstand (ae) auseinander; der ebene Teil der Stirn ragt seitlich um SEITE_ANTEIL · Ø
  über den Rand – so bleibt dort kein Grat –, eine Zeile in der Mitte, wenn die Fläche
  schmaler ist. Zeilen, unter denen kein Rohteil liegt, fallen weg (keine Leerzeile, W-006
  Grundsatz 5).
- Längs reicht jede Zeile um den Überlauf (UEBERLAUF_ANTEIL · Ø, W-006 4.1.1) über die Fläche
  hinaus; wo die Hüllfläche (hoehenfeld.je_zeile, das Teil ohne diese Fläche) höher liegt als
  die Lage – eine Wand, ein Absatz nach oben –, hält sie an. Hin und her
  (vierachs_bahn._fahrten): Am Ende einer Zeile ein Halbkreis (G2/G3) zur nächsten, wo beide
  Zeilen dort frei sind; sonst in der Tiefe quer hinüber, oder abheben. Die erste Zeile einer
  Lage beginnt an dem Ende, das in der Luft liegt.
- Hinein: in der Luft (neben dem Rohteil) senkrecht mit dem Eintauchvorschub; im Material
  über die Rampe mit dem Eintauchwinkel längs der ersten Zeile (vierachs_bahn._rampe).
- Beim Austritt aus dem Rohteil fährt die Zeile mit AUSTRITT_ANTEIL des Vorschubs (W-006 E6,
  erster Schritt: Grat beim Austritt).
- Gleichlauf durchgehend (Grundsatz 4) kommt mit der Spirale von außen nach innen, sobald das
  Bahnmodell Konturen versetzen kann (S3e); hin und her ist jede zweite Zeile Gegenlauf.
- Mit Materialstand (W-012, materialstand): Was die Operationen davor schon weggenommen haben,
  fräst es nicht noch einmal. Die Lagen beginnen am höchsten Material, das die Zeilen
  erreichen; je Lage fährt eine Zeile nur, wo ihre Stirn Material über der Lage trifft – über
  eine kurze Lücke im Vorschub hinweg (wie das Räumen). Senkrecht hinein, wo unter der Stirn
  höchstens am Rand ein Streifen ae steht (wie neben der vorigen Zeile) – die Rampe nur, wo
  Material unter ihrer Mitte steht; der Eilgang hinab endet über dem Material unter der Stirn.

Gerechnet in (u, v, z): u längs der Zeilen, v quer, z nach oben; die Punkte am Ende in x und
y des Jobs (bahn.Punkt). Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass

import numpy as np

from . import bahn as bn
from . import hoehenfeld as hf
from . import spindel as sp
from . import vierachs_bahn as vb
from . import vierachs_planbahn as vp
from .sprache import tr

UEBERLAUF_ANTEIL = 0.6  # vom Fräser-Ø: so weit läuft die Mitte längs über die Fläche hinaus
SEITE_ANTEIL = 0.2  # vom Fräser-Ø: so weit ragt der ebene Teil der Stirn seitlich über den Rand
WANDZEILE_NAH = 0.05  # mm – liegt eine Zeile so nah an der Zeile an der Wand, fährt sie allein
AUSTRITT_ANTEIL = 0.5  # vom Vorschub: so langsam beim Austritt aus dem Rohteil
SCHRITT = hf.SCHRITT  # mm – Raster längs der Zeilen
VORSCHAU_SCHRITT = 1.0  # mm – für die Vorschau im Assistenten
GLEICH = vb.GLEICH
# Mit Materialstand: So viel muss über einer Lage stehen, damit es als Material zählt; eine Lücke
# im Weggefrästen bis LUECKE Durchmesser (mindestens LUECKE_MIN) fährt die Zeile im Vorschub durch
# – Abheben und wieder Einfahren dauert länger (wie raeumen_bahn).
MATERIAL = 0.05  # mm
LUECKE = 2.0
LUECKE_MIN = 20.0  # mm


@dataclass(frozen=True)
class Planwerte:
    """Was das Planfräsen braucht; Längen in mm, z nach oben im Job."""

    form: object  # fraeserform.Form des Fräsers – mit ebener Stirn (Schaft-, Torus-, Planfräser)
    zustellung: float  # ap: höchstens so tief je Lage
    zeilenabstand: float  # ae: höchstens so weit rücken die Zeilen quer
    aufmass: float  # bleibt auf der Fläche stehen (0: fertig)
    oben: float  # z der Oberkante: das Rohteil (hier beginnen die Lagen)
    sicher: float  # z für den Eilgang über allem
    rohteil: tuple  # (x_von, x_bis, y_von, y_bis) des Rohteils von oben
    ueberlauf: float = None  # längs über die Fläche hinaus (Mitte des Fräsers); None: Vorschlag
    seite: float = None  # seitlich über den Rand (ebener Teil der Stirn); None: Vorschlag
    sicherheit: float = vb.SICHERHEIT  # so weit über dem Material endet der Eilgang hinab
    eintauchwinkel: float = vb.EINTAUCHWINKEL  # Grad, für die Rampe ins Material
    austritt: float = AUSTRITT_ANTEIL
    # Die Zeilen längs x (True) oder längs y (False); None: beide rechnen, die schnellere nehmen
    # (Grundsatz 0 der Strategien: die Zeit entscheidet).
    laengs: bool = None
    vorschub: float = 0.0  # mm/min – für die Zeit im Vergleich; 0: 1000
    eintauchen: float = 0.0  # mm/min senkrecht ins Material; 0: wie der Vorschub
    # Nur im Gleichlauf (Manuel 2026-10-02: „auswählbar, ob er abhebt und wieder von vorne
    # anfängt“): jede Zeile in dieselbe Richtung, danach abheben und von vorne
    # (vierachs_bahn._einzeln);
    # sonst hin und her. `gleichlauf`: die Richtung dafür bei M3 (spindel.fuer_m3).
    nur_gleichlauf: bool = False
    gleichlauf: bool = True


@dataclass
class Planbahn:
    """Ergebnis von planen()."""

    punkte: list  # [bahn.Punkt], der erste ist der Start (Eilgang, oben)
    flaechen: int  # so viele Flächen
    lagen: int  # Lagen, über alle Flächen
    zeilen: int  # Zeilen, über alle Flächen und Lagen
    z_min: float  # die tiefste Spitze (mm)
    laenge: float  # mm im Vorschub
    richtungen: tuple = ()  # je gefräster Fläche: True = Zeilen längs x, False = längs y
    zeit: float = 0.0  # Minuten (bahn.zeit: Vorschub, Eilgang, Beschleunigung, Ecken)
    zeit_andere: float = None  # Minuten in der anderen Zeilenrichtung; None: nicht gerechnet
    # Mit Materialstand (W-012): was über den Flächen noch steht und was die Operationen davor
    # dort schon weggenommen haben (mm³), und welche das waren.
    noch: float = 0.0
    weg: float = 0.0
    davor: list = None


@dataclass
class _Ebene:
    """Die Bahn über eine Fläche in einer Zeilenrichtung."""

    punkte: list
    lagen: int
    zeilen: int
    z_min: float
    laenge: float
    laengs_x: bool
    zeit: float  # Minuten
    noch: float = 0.0  # mit Materialstand: wie Planbahn
    weg: float = 0.0
    davor: tuple = ()


def ueberlauf_vorschlag(form):
    """Der Überlauf längs, wenn nichts anderes gesagt ist: UEBERLAUF_ANTEIL · Ø."""
    return UEBERLAUF_ANTEIL * 2 * form.radius


def rest_an_der_wand(zeilenabstand):
    """So viel lässt das Planfräsen an einer Wand höchstens stehen – so breit ist der Rest für
    die Kontur danach (P-2026-10-02-17): ein Zeilenabstand und die Zugabe der Hüllfläche. Seit
    der Zeile an der Wand (P-2026-10-02-18) ist es meist nur die Zugabe; der Zeilenabstand
    bleibt die sichere Grenze (Bögen zwischen Zeilenenden an runden Wänden)."""
    return zeilenabstand + hf.TOLERANZ + vb.RAND


def planen(netz, werte, ebenen, schritt=SCHRITT, stand=None):
    """Die Bahn „Planfräsen“ (Planbahn) über die Flächen `ebenen` ([hoehenfeld.Ebene]) mit den
    Werten `werte`; `netz` ist das Teil ohne diese Flächen (hoehenfeld.netz_ohne). Je Fläche
    die Zeilen längs x oder längs y – ohne Vorgabe (`werte.laengs` None) beide gerechnet und
    die schnellere genommen (bahn.zeit mit Vorschub, Eilgang und Beschleunigung). `stand`: der
    Materialstand davor (materialstand, W-012) – was die Operationen davor weggenommen haben,
    fräst es nicht noch einmal. ValueError mit einem Satz, wenn es nicht geht."""
    w = werte
    form = w.form
    r_eben = vp.ebener_radius(form)
    if r_eben <= 0:
        raise ValueError(tr("pf.fehler.form"))
    if w.zustellung <= 0 or w.zeilenabstand <= 0:
        raise ValueError(tr("pf.fehler.werte"))
    if w.zeilenabstand > 2 * r_eben:
        raise ValueError(tr("pf.fehler.zeilenabstand"))
    if not ebenen:
        raise ValueError(tr("pf.fehler.keine_ebene"))
    ueberlauf = ueberlauf_vorschlag(form) if w.ueberlauf is None else w.ueberlauf
    seite = SEITE_ANTEIL * 2 * form.radius if w.seite is None else w.seite
    toleranz = hf.netz_fuer(netz, ebenen[0]).toleranz if ebenen else hf.TOLERANZ
    zugabe = toleranz + vb.RAND
    geformt = form.mit_aufmass(toleranz)
    punkte = []
    lagen_gesamt = zeilen_gesamt = gefraest = 0
    z_min = math.inf
    laenge = zeit = zeit_andere = 0.0
    richtungen = []
    noch = weg = 0.0
    davor = []
    kandidaten = (True, False) if w.laengs is None else (bool(w.laengs),)
    fertig = []  # die Flächen darüber, schon in dieser Bahn
    for ebene in sorted(ebenen, key=lambda e: -e.z):
        # Liegt die Fläche ganz unter einer, die diese Bahn schon geplant hat (der Boden einer
        # Tasche unter der Oberseite), beginnen ihre Lagen dort – darüber ist weggeräumt, wie
        # beim Räumen (P-2026-10-01-49; vorher ab dem Rohteil, die oberen Lagen in der Luft).
        oben = w.oben
        for darueber in fertig:
            if _umfasst(darueber, ebene):
                oben = min(oben, darueber.z + w.aufmass)
        fertig.append(ebene)
        tiefere = [e for e in ebenen if e.z < ebene.z - GLEICH]
        ergebnisse = []
        for laengs_x in kandidaten:
            e = _ebene(
                hf.netz_fuer(netz, ebene),
                w,
                ebene,
                laengs_x,
                r_eben,
                ueberlauf,
                seite,
                zugabe,
                geformt,
                schritt,
                oben,
                tiefere,
                stand,
            )
            if e is not None:
                ergebnisse.append(e)
        if stand is not None and ergebnisse:
            # Was über der Fläche noch steht und wer dort schon war – aus der ersten Richtung.
            noch += ergebnisse[0].noch
            weg += ergebnisse[0].weg
            davor += [name for name in ergebnisse[0].davor if name not in davor]
            ergebnisse = [e for e in ergebnisse if e.lagen]
        if not ergebnisse:
            continue
        ergebnisse.sort(key=lambda e: e.zeit)
        beste = ergebnisse[0]
        punkte.extend(beste.punkte)
        gefraest += 1
        lagen_gesamt += beste.lagen
        zeilen_gesamt += beste.zeilen
        z_min = min(z_min, beste.z_min)
        laenge += beste.laenge
        zeit += beste.zeit
        richtungen.append(beste.laengs_x)
        if zeit_andere is not None:
            zeit_andere = zeit_andere + ergebnisse[1].zeit if len(ergebnisse) > 1 else None
    if gefraest == 0:
        if davor:
            from . import materialstand as mst  # erst hier: es bringt den Job mit

            raise mst.schon_weg(davor)
        raise ValueError(tr("pf.fehler.nichts"))
    return Planbahn(
        punkte,
        gefraest,
        lagen_gesamt,
        zeilen_gesamt,
        z_min if math.isfinite(z_min) else 0.0,
        laenge,
        tuple(richtungen),
        zeit,
        zeit_andere,
        noch,
        weg,
        davor,
    )


def _umfasst(oben, unten):
    """Liegt die Fläche `unten` (hoehenfeld.Ebene) in der Ausdehnung von `oben` und tiefer?"""
    return (
        unten.z < oben.z - GLEICH
        and oben.x_von - GLEICH <= unten.x_von
        and unten.x_bis <= oben.x_bis + GLEICH
        and oben.y_von - GLEICH <= unten.y_von
        and unten.y_bis <= oben.y_bis + GLEICH
    )


def _ebene(
    netz,
    w,
    ebene,
    laengs_x,
    r_eben,
    ueberlauf,
    seite,
    zugabe,
    geformt,
    schritt,
    oben,
    tiefere=(),
    stand=None,
    gesenkt=False,
):
    """Die Bahn über eine Fläche mit den Zeilen längs x (`laengs_x`) oder längs y, die Lagen ab
    `oben` – None, wenn nichts zu fräsen ist (nichts drüber, keine Zeile mit Rohteil).
    `tiefere`: die tieferen Flächen derselben Bahn (_abgedeckt). `stand`: der Materialstand
    davor – ohne Lage, wenn über der Fläche nichts mehr steht, was die Zeilen erreichen;
    `gesenkt`: `oben` kommt schon aus ihm."""
    punkte = []
    lagen_gesamt = zeilen_gesamt = 0
    z_min = math.inf
    laenge = 0.0
    ziel = ebene.z + w.aufmass
    if oben <= ziel + GLEICH:
        return None  # steht nichts drüber
    if laengs_x:
        u_von, u_bis, v_von, v_bis = ebene.x_von, ebene.x_bis, ebene.y_von, ebene.y_bis
        roh_u, roh_v = w.rohteil[0:2], w.rohteil[2:4]
    else:
        u_von, u_bis, v_von, v_bis = ebene.y_von, ebene.y_bis, ebene.x_von, ebene.x_bis
        roh_u, roh_v = w.rohteil[2:4], w.rohteil[0:2]
    # Das Raster längs: die Zeilen reichen um den Überlauf über die Fläche hinaus, die
    # Hüllfläche um den halben Zeilenabstand weiter – dort prüft der Halbkreis, ob er frei ist.
    halb = w.zeilenabstand / 2
    u0, u1 = u_von - ueberlauf - halb, u_bis + ueberlauf + halb
    anzahl = max(2, int(math.ceil((u1 - u0) / schritt - 1e-9)) + 1)
    u_stellen = np.linspace(u0, u1, anzahl)
    schritt_u = float(u_stellen[1] - u_stellen[0])
    # Der Rand der Fläche quer: Vor einer Wand fährt die Wandfahrt über die erste und letzte
    # Zeile hinaus bis an den Rand – so weit es dort erlaubt ist (_wandfahrt).
    v_rand = (float(v_von), float(v_bis))
    roh_rand = hf.je_zeile(netz, geformt, v_rand, u0, schritt_u, anzahl, laengs_x).T
    hoehe_rand = roh_rand + zugabe
    # Offen: am Rand, mehr als R von den Enden der Fläche weg (dort reichte die Stirn an eine Wand
    # quer, etwa den Absatz neben der Fläche – um R berührt sie ihn gerade), steht nichts höher
    # als die Fläche.
    mitte = (u_von + u_bis) / 2
    weg_vom_ende = r_eben + zugabe + schritt_u
    von, bis = min(u_von + weg_vom_ende, mitte), max(u_bis - weg_vom_ende, mitte)
    am_rand = np.abs(u_stellen - np.clip(u_stellen, von, bis)) <= schritt_u / 2 + GLEICH
    offen = [not np.any(roh_rand[i][am_rand] > ziel + GLEICH) for i in (0, 1)]
    abgedeckt = [_abgedeckt(tiefere, laengs_x, (u_von, u_bis), (v_von, v_bis), i) for i in (0, 1)]
    # Die Lagen. Steht vor der ersten Zeile eine Wand (in einer Tasche immer), hat sie keine
    # freie Seite und schneidet in voller Breite: dann je Lage höchstens so tief, dass
    # 2 R · Tiefe nicht über ae · ap liegt (P-2026-10-01-49; im Taschenboden der Platte 20 tief).
    zustellung = w.zustellung
    if not offen[0] or abgedeckt[0]:
        zustellung = min(zustellung, w.zeilenabstand * w.zustellung / (2 * r_eben))
    anzahl_lagen = max(1, int(math.ceil((oben - ziel - hf.LAGEN_SPIEL) / zustellung)))
    lagen = oben - (oben - ziel) * np.arange(1, anzahl_lagen + 1) / anzahl_lagen
    # Auf einer offenen Seite (am Rand steht nichts höher als die Fläche, keine Wand) greifen
    # die erste und die letzte Zeile höchstens so breit ins Rohteil, dass Breite · Tiefe der
    # Lage nicht über ae · ap liegt (P-2026-10-01-49): Mit SEITE_ANTEIL allein griff die erste
    # Zeile 0,8 · Ø breit – auf der Platte 20 mm tief, ein Vollschnitt; ragt das Rohteil weiter
    # als R über die Fläche, war es ein Schlitz in voller Breite. Flache Lagen (Planen 1 mm)
    # behalten den Überlauf.
    tiefe_lage = (oben - ziel) / anzahl_lagen
    breit = max(
        w.zeilenabstand,
        min(2 * r_eben - seite, w.zeilenabstand * w.zustellung / max(tiefe_lage, GLEICH)),
    )
    v_start = v_von + r_eben - seite
    v_ende = v_bis - (r_eben - seite)
    # Über die offene Seite bis an den Rand des Rohteils – außer eine tiefere Fläche derselben
    # Bahn liegt dahinter: Deren Lagen beginnen am Rohteil und räumen es dort ohnehin; am Zapfen
    # fräste die Oberseite sonst die ganze Platte 1 mm ab und der Boden darum danach noch einmal
    # (P-2026-10-02-21). Ohne Ausgriff schneidet die erste Zeile dann in voller Breite – darum
    # oben die Zustellung wie vor einer Wand.
    if offen[0] and not abgedeckt[0]:
        v_start = min(v_start, roh_v[0] - r_eben + breit)
    if offen[1] and not abgedeckt[1]:
        v_ende = max(v_ende, roh_v[1] + r_eben - breit)
    v_zeilen = _zeilen_quer(v_start, v_ende, 0.0, w.zeilenabstand)
    # Vor einer Wand längs der Zeilen (die Seite ist nicht offen) ragte die letzte Zeile in die
    # Wand und fiel weg – die vorige ließ an ihr bis zu einem Zeilenabstand stehen (gemessen
    # 0,5 mm, P-2026-10-02-18). Dazu eine Zeile, die an der Wand entlang fräst: die Stirn im
    # Abstand der Zugabe von ihr.
    r_voll = float(w.form.radius)
    for seite_zu, v_wand in (
        (not offen[0], v_von + r_voll + zugabe),
        (not offen[1], v_bis - r_voll - zugabe),
    ):
        if seite_zu and not np.any(np.abs(v_zeilen - v_wand) < WANDZEILE_NAH):
            v_zeilen = np.sort(np.append(v_zeilen, v_wand))
    # Keine Leerzeile: nur Zeilen, unter denen das Rohteil liegt.
    v_zeilen = v_zeilen[
        (v_zeilen + r_eben > roh_v[0] + GLEICH) & (v_zeilen - r_eben < roh_v[1] - GLEICH)
    ]
    if not len(v_zeilen):
        return None
    huelle = hf.je_zeile(netz, geformt, v_zeilen, u0, schritt_u, anzahl, laengs_x)
    roh = huelle.T  # (Zeilen, Stellen); −inf, wo er nichts trifft
    hoehe = roh + zugabe
    # Zwischen weit auseinanderliegenden Zeilen: Prüfzeilen für Schritt, Halbkreis und die
    # Fahrten an der Wand – auch vor der ersten und hinter der letzten bis an den Rand.
    zwischen_v, zwischen_von = vb._zwischen(v_zeilen, r_voll)
    rand_v, rand_von = [], []
    for seite_i, (a, b) in enumerate(((v_rand[0], v_zeilen[0]), (v_zeilen[-1], v_rand[1]))):
        werte_rand, _von = vb._zwischen(np.array([a, b]), r_voll)
        rand_v.extend(werte_rand)
        rand_von.extend([seite_i] * len(werte_rand))
    pruef_v = np.concatenate([zwischen_v, np.array(rand_v)])
    if len(pruef_v):
        roh_zw = hf.je_zeile(netz, geformt, pruef_v, u0, schritt_u, anzahl, laengs_x).T
    else:
        roh_zw = np.zeros((0, anzahl))
    hoehe_zw = roh_zw + zugabe
    im_ueberlauf = (u_stellen >= u_von - ueberlauf - GLEICH) & (
        u_stellen <= u_bis + ueberlauf + GLEICH
    )
    im_rohteil = (u_stellen + r_eben > roh_u[0] + GLEICH) & (u_stellen - r_eben < roh_u[1] - GLEICH)
    material = None
    noch = weg = 0.0
    davor = ()
    if stand is not None:
        r_voll = float(w.form.radius)
        innen, aussen = max(r_voll - stand.schritt, 0.0), r_voll + stand.schritt
        uu, vv = np.meshgrid(u_stellen, v_zeilen)  # (Zeilen, Stellen)
        xx, yy = (uu, vv) if laengs_x else (vv, uu)
        # Was über der Fläche noch steht und wer dort schon war: wohin die Stirn auf ihr kommt.
        boden = ((hoehe <= ziel + GLEICH) | (roh <= ziel + GLEICH)) & im_ueberlauf[None, :]
        bereich = stand.maske_um_punkte(xx[boden], yy[boden], r_voll)
        noch, weg = stand.volumen(bereich, ziel)
        davor = tuple(stand.wer(bereich))
        # Was die Zeilen überhaupt erreichen (auf der obersten Lage dürfen sie am weitesten).
        frei_oben = ((hoehe <= oben + GLEICH) | (roh <= ziel + GLEICH)) & im_ueberlauf[None, :]
        reich = stand.maske_um_punkte(xx[frei_oben], yy[frei_oben], innen)
        voll = bool(reich.any()) and bool((stand.quader.h[reich] >= oben - GLEICH).all())
        if not voll:  # sonst steht überall noch das ganze Rohteil: wie ohne Materialstand
            hoechste = stand.hoechste(reich)
            if hoechste is None or hoechste <= ziel + MATERIAL:
                return _Ebene([], 0, 0, math.inf, 0.0, laengs_x, 0.0, noch, weg, davor)
            if not gesenkt and hoechste < oben - GLEICH:
                # Die Lagen beginnen am höchsten Material, das die Zeilen erreichen.
                return _ebene(
                    netz,
                    w,
                    ebene,
                    laengs_x,
                    r_eben,
                    ueberlauf,
                    seite,
                    zugabe,
                    geformt,
                    schritt,
                    hoechste,
                    tiefere,
                    stand,
                    True,
                )
            mitte = max(r_voll - w.zeilenabstand, 0.0)  # der Teil der Stirn ohne den Streifen ae
            material = (xx, yy, innen, aussen, max(LUECKE * 2.0 * r_voll, LUECKE_MIN), mitte)
    vorige = oben
    vorher_drin = None
    for lage in lagen:
        lage = float(lage)
        # Die Lage darf dorthin, wo die Hüllfläche nicht höher liegt – und über den Rand
        # der Fläche hinaus auch, wo nichts höher steht als die Fläche selbst: Die
        # Seitenwand des Teils endet genau auf ihrer Höhe, die Zugabe hielte die unterste
        # Lage sonst vor ihr an (wie bei Plan indexiert, P-2026-10-01-10).
        erlaubt = (hoehe <= lage + GLEICH) | (roh <= ziel + GLEICH)
        erlaubt_rand = (hoehe_rand <= lage + GLEICH) | (roh_rand <= ziel + GLEICH)
        erlaubt_zw = (hoehe_zw <= lage + GLEICH) | (roh_zw <= ziel + GLEICH)
        zwischen = np.ones((max(len(v_zeilen) - 1, 0), anzahl), dtype=bool)
        for k, m in enumerate(zwischen_von):
            zwischen[m] &= erlaubt_zw[k]
        zum_rand = np.ones((2, anzahl), dtype=bool)
        for k, seite_i in enumerate(rand_von):
            zum_rand[seite_i] &= erlaubt_zw[len(zwischen_von) + k]
        drin = erlaubt & im_ueberlauf[None, :]  # die Zeilen selbst
        mitte_frei = None
        if material is not None:
            # Nur, wo die Stirn Material über der Lage trifft – über kurze Lücken hinweg; wo
            # unter der Mitte der Stirn nichts steht, senkrecht hinein.
            xx, yy, innen, aussen, luecke, mitte = material
            ganz = drin
            drin = drin & stand.trifft(lage, innen, xx, yy)
            drin = _luecken_zu(drin, ganz, schritt_u, luecke)
            mitte_frei = ~stand.trifft(lage, mitte, xx, yy)
        if not drin.any():
            vorige = lage
            continue
        raster = _Raster(
            u_stellen,
            v_zeilen,
            drin,
            erlaubt,
            im_rohteil,
            laengs_x,
            roh_u,
            r_eben,
            w.zeilenabstand,
            v_rand,
            erlaubt_rand,
            zwischen,
            zum_rand,
            mitte_frei,
            vorher_drin,
            stand if material is not None else None,
            material[3] if material is not None else 0.0,
        )
        # Von dem Ende beginnen, das in der Luft liegt – sonst vom Anfang.
        erste = int(np.flatnonzero(drin.any(axis=1))[0])
        js = np.flatnonzero(drin[erste])
        if not im_rohteil[js[0]] and not im_rohteil[js[-1]]:
            pass
        elif not im_rohteil[js[-1]]:
            raster = raster.umgekehrt()
        mit_luecke = np.zeros((len(v_zeilen), anzahl + 2), dtype=bool)
        mit_luecke[:, 1:-1] = raster.drin
        if w.nur_gleichlauf:
            fahrten = vb._einzeln(mit_luecke, _steigend(raster, w.gleichlauf))
            fahrten = [(raster, fahrt) for fahrt in fahrten]
        else:
            fahrten = _zellenfahrten(raster, mit_luecke)
        for raster_fahrt, fahrt in fahrten:
            laenge += _fahrt(punkte, fahrt, raster_fahrt, lage, vorige, w)
            zeilen_gesamt += len({m for art, m, _js in fahrt if art == "zeile"})
        lagen_gesamt += 1
        vorige = lage
        vorher_drin = drin
        z_min = min(z_min, lage)
    zeit = bn.zeit(punkte, w.vorschub if w.vorschub > 0 else 1000.0, w.eintauchen or None)
    return _Ebene(
        punkte, lagen_gesamt, zeilen_gesamt, z_min, laenge, laengs_x, zeit, noch, weg, davor
    )


def _zellen(drin):
    """Die Zellen des Bereichs (Zeilen × Stellen, mit der Lücke an beiden Enden): Stücke
    benachbarter Zeilen, die sich eins zu eins überlappen – teilt sich der Bereich an einer Insel
    oder läuft er hinter ihr wieder zusammen, endet die Zelle. [[(m, anfang, länge), …], …] in
    der Reihenfolge ihrer ersten Zeile."""
    stuecke = [vb._bereiche(drin[m]) for m in range(drin.shape[0])]
    zellen, offen = [], {}  # offen: Stück der vorigen Zeile → Nummer seiner Zelle

    def ueber(a, laenge, liste):
        return [k for k, (b, l_b) in enumerate(liste) if b <= a + laenge - 1 and a <= b + l_b - 1]

    for m, liste in enumerate(stuecke):
        vorher = stuecke[m - 1] if m else []
        neu = {}
        for k, (anfang, laenge) in enumerate(liste):
            oben = ueber(anfang, laenge, vorher)
            if len(oben) == 1 and oben[0] in offen and ueber(*vorher[oben[0]], liste) == [k]:
                neu[k] = offen[oben[0]]
                zellen[neu[k]].append((m, anfang, laenge))
                continue
            zellen.append([(m, anfang, laenge)])
            neu[k] = len(zellen) - 1
        offen = neu
    return zellen


def _monoton(zelle, vor=0):
    """Die Zelle in Stücke, die sich in einer Richtung fahren lassen, ohne dass ein Ende der
    Zeile über das der vorigen hinaus vorrückt (mehr als `vor` Stellen): Vor einer Insel fräste
    das vorrückende Stück sonst neben ihr waagrecht in voller Breite (Spezifikation Strategien,
    Abschnitt 11). [(Zeilen, aufwärts erlaubt, abwärts erlaubt)] – aufwärts: zur letzten Zeile
    hin."""
    teile, start, auf, ab = [], 0, True, True
    for i in range(len(zelle) - 1):
        _m0, a0, l0 = zelle[i]
        _m1, a1, l1 = zelle[i + 1]
        e0, e1 = a0 + l0 - 1, a1 + l1 - 1
        weiter_auf = auf and not (a1 < a0 - vor or e1 > e0 + vor)
        weiter_ab = ab and not (a0 < a1 - vor or e0 > e1 + vor)
        if not (weiter_auf or weiter_ab):
            teile.append((zelle[start : i + 1], auf, ab))
            start, auf, ab = i + 1, True, True
        else:
            auf, ab = weiter_auf, weiter_ab
    teile.append((zelle[start:], auf, ab))
    return teile


def _bereit(fertig, zeilen, auf):
    """Darf die Zelle so beginnen? Ihre erste Zeile braucht daneben – vor ihr in Fahrtrichtung –
    schon Gefrästes oder kein Material: Sonst schnitte sie in voller Breite (an der Platte 253 mm,
    als eine Zelle über dem Zapfen von oben her begann, bevor die Zeilen darüber gefräst waren)."""
    m, anfang, laenge = zeilen[0] if auf else zeilen[-1]
    nachbar = m - 1 if auf else m + 1
    if not 0 <= nachbar < fertig.shape[0]:
        return True
    return bool(fertig[nachbar, anfang : anfang + laenge].all())


def _zellenfahrten(raster, mit_luecke):
    """Die Fahrten einer Lage Zelle für Zelle (Spezifikation Strategien, Abschnitt 11): Jede
    Zelle hin und her für sich, in einer Richtung, in der die Zeilenenden an einer Insel oder
    Wand nicht vorrücken (_monoton), und erst, wenn vor ihrer ersten Zeile schon gefräst ist
    (_bereit) – bis P-2026-10-03-29 wechselte die Bahn hinter einer Insel nach jeder Zeile die
    Seite, jede Zeile wurde eine Fahrt mit Rampe (am Zapfen 54). Die nächste Zelle: lieber eine,
    die in der Luft beginnt, sonst die nächstgelegene. [(Raster, Fahrt)] – das Raster gespiegelt
    für Zellen, die zur ersten Zeile hin laufen."""
    gespiegelt = raster.gespiegelt()
    zeilen = len(raster.v_zeilen)
    n = mit_luecke.shape[1]
    stuecke = [t for zelle in _zellen(mit_luecke) for t in _monoton(zelle)]
    # Was schon gefräst ist – und was es nie wird (kein Material): beides „fertig“.
    fertig = ~mit_luecke
    hier = None  # (u, v) – wo der Fräser steht
    ergebnis = []
    while stuecke:
        beste = None
        for nur_bereite in (True, False):
            for nummer, (zeilen_, darf_auf, darf_ab) in enumerate(stuecke):
                for auf in [r for r, darf in ((True, darf_auf), (False, darf_ab)) if darf]:
                    if nur_bereite and not _bereit(fertig, zeilen_, auf):
                        continue
                    m, anfang, laenge = zeilen_[0] if auf else zeilen_[-1]
                    for stelle, richtung in ((anfang, 1), (anfang + laenge - 1, -1)):
                        j = min(max(stelle - 1, 0), len(raster.u_stellen) - 1)
                        u, v = float(raster.u_stellen[j]), float(raster.v_zeilen[m])
                        luft = not bool(raster.im_rohteil[j])
                        weg = 0.0 if hier is None else math.hypot(u - hier[0], v - hier[1])
                        schluessel = (not luft, weg, m if auf else zeilen - 1 - m)
                        if beste is None or schluessel < beste[0]:
                            beste = (schluessel, nummer, auf, richtung)
            if beste is not None:
                break
        _schluessel, nummer, auf, richtung = beste
        zeilen_, _darf_auf, _darf_ab = stuecke.pop(nummer)
        for m, anfang, laenge in zeilen_:
            fertig[m, anfang : anfang + laenge] = True
        r_ = raster if auf else gespiegelt
        feld = mit_luecke if auf else mit_luecke[::-1]
        folge = zeilen_ if auf else [(zeilen - 1 - m, a, l_) for m, a, l_ in reversed(zeilen_)]
        fahrten, fahrt, ende = [], None, 0
        for m, anfang, laenge in folge:
            letzte = anfang + laenge - 1
            teile = None
            if fahrt:
                teile = vb._anschluss(feld[m - 1], ende, anfang, laenge, richtung, m, n)
            if teile is None:
                if fahrt:
                    fahrten.append(fahrt)
                js = vb._von_bis(anfang, letzte) if richtung > 0 else vb._von_bis(letzte, anfang)
                fahrt = [("zeile", m, js)]
            else:
                fahrt.extend(teile)
            ende = int(fahrt[-1][2][-1])
            richtung = -richtung
        fahrten.append(fahrt)
        for teil in vb._geteilt(fahrten, r_.zwischen):
            ergebnis.append((r_, teil))
        m_ende = int(fahrt[-1][1])
        j_ende = min(max(ende - 1, 0), len(raster.u_stellen) - 1)
        hier = (float(r_.u_stellen[j_ende]), float(r_.v_zeilen[m_ende]))
    return ergebnis


def _luecken_zu(drin, ganz, schritt_u, laenge):
    """`drin` (Zeilen × Stellen: fährt die Zeile hier?) mit den Lücken je Zeile gefüllt, die
    höchstens `laenge` (mm) lang sind und ganz in `ganz` liegen – zwischen zwei Stücken
    derselben Zeile (wie raeumen_bahn._luecken_zu)."""
    ergebnis = drin.copy()
    for m in range(drin.shape[0]):
        stellen = np.flatnonzero(drin[m])
        for a, b in zip(stellen[:-1], stellen[1:], strict=True):
            if b - a > 1 and (b - a) * schritt_u <= laenge and ganz[m, a + 1 : b].all():
                ergebnis[m, a + 1 : b] = True
    return ergebnis


def _abgedeckt(tiefere, laengs_x, u, v, seite):
    """Liegt hinter der Seite `seite` (0: v_von, 1: v_bis) der Fläche mit den Ausdehnungen `u`
    und `v` eine der `tiefere` Flächen (hoehenfeld.Ebene) – über die ganze Länge der Fläche,
    von ihrem Rand an nach außen?"""
    for e in tiefere:
        eu = (e.x_von, e.x_bis) if laengs_x else (e.y_von, e.y_bis)
        ev = (e.y_von, e.y_bis) if laengs_x else (e.x_von, e.x_bis)
        if eu[0] > u[0] + GLEICH or eu[1] < u[1] - GLEICH:
            continue
        if seite == 0 and ev[0] < v[0] - GLEICH and ev[1] >= v[0] - GLEICH:
            return True
        if seite == 1 and ev[1] > v[1] + GLEICH and ev[0] <= v[1] + GLEICH:
            return True
    return False


def _steigend(raster, gleichlauf):
    """Läuft eine Zeile im Gleichlauf mit wachsenden Stellen? Die Zeilen folgen einander quer mit
    wachsendem v – dort liegt das Material; der Fräser zeigt nach unten (spindel.ist_gleichlauf,
    `gleichlauf` aus spindel.fuer_m3)."""
    r_ = raster
    du = 1.0 if len(r_.u_stellen) < 2 or r_.u_stellen[1] > r_.u_stellen[0] else -1.0
    fx, fy = r_.xy(du, 0.0)
    mx, my = r_.xy(0.0, 1.0)
    return sp.ist_gleichlauf((0.0, 0.0, -1.0), (fx, fy, 0.0), (mx, my, 0.0)) == bool(gleichlauf)


def _zeilen_quer(v_von, v_bis, rand, abstand):
    """Die Zeilen quer: von v_von + rand bis v_bis − rand gleich weit auseinander, höchstens
    `abstand`; eine in der Mitte, wenn die Fläche dafür zu schmal ist."""
    breite = v_bis - v_von
    if breite <= 2 * rand + GLEICH:
        return np.array([(v_von + v_bis) / 2])
    anzahl = int(math.ceil((breite - 2 * rand) / abstand - 1e-9)) + 1
    return np.linspace(v_von + rand, v_bis - rand, anzahl)


@dataclass
class _Raster:
    """Eine Lage im Raster: die Stellen längs (in der Reihenfolge, in der die Fahrten gezählt
    werden), die Zeilen quer, wo gefräst wird, wo das Rohteil liegt."""

    u_stellen: np.ndarray  # (N,) in Zählrichtung
    v_zeilen: np.ndarray  # (Zeilen,)
    drin: np.ndarray  # (Zeilen, N): hier fährt die Zeile
    erlaubt: np.ndarray  # (Zeilen, N): die Lage darf dorthin – für den Halbkreis am Ende
    im_rohteil: np.ndarray  # (N,): die Stirn trifft dort das Rohteil
    laengs_x: bool
    roh_u: tuple  # (von, bis) des Rohteils längs
    r_eben: float
    zeilenabstand: float
    v_rand: tuple  # (von, bis) der Fläche quer – vor und hinter der ersten und letzten Zeile
    erlaubt_rand: np.ndarray  # (2, N): die Lage darf an den Rand – für die Wandfahrt
    zwischen: np.ndarray  # (Zeilen − 1, N): zwischen Zeile m und m + 1 frei (_zwischen)
    zum_rand: np.ndarray  # (2, N): vor der ersten, hinter der letzten Zeile bis an den Rand frei
    # Mit Materialstand: wo unter der Mitte der Stirn (ohne den Streifen ae) nichts über der
    # Lage steht, wo die Lage davor fuhr, der Stand und wie weit um eine Stelle das Material für
    # den Eilgang hinab zählt.
    mitte_frei: np.ndarray = None  # (Zeilen, N)
    vorher_drin: np.ndarray = None  # (Zeilen, N)
    stand: object = None
    aussen: float = 0.0

    def umgekehrt(self):
        return _Raster(
            self.u_stellen[::-1],
            self.v_zeilen,
            self.drin[:, ::-1],
            self.erlaubt[:, ::-1],
            self.im_rohteil[::-1],
            self.laengs_x,
            self.roh_u,
            self.r_eben,
            self.zeilenabstand,
            self.v_rand,
            self.erlaubt_rand[:, ::-1],
            self.zwischen[:, ::-1],
            self.zum_rand[:, ::-1],
            None if self.mitte_frei is None else self.mitte_frei[:, ::-1],
            None if self.vorher_drin is None else self.vorher_drin[:, ::-1],
            self.stand,
            self.aussen,
        )

    def gespiegelt(self):
        """Quer gespiegelt: die Zeilen von der letzten an gezählt – für Zellen, die zur ersten
        Zeile hin gefahren werden (_zellenfahrten)."""
        return _Raster(
            self.u_stellen,
            self.v_zeilen[::-1],
            self.drin[::-1],
            self.erlaubt[::-1],
            self.im_rohteil,
            self.laengs_x,
            self.roh_u,
            self.r_eben,
            self.zeilenabstand,
            (self.v_rand[1], self.v_rand[0]),
            self.erlaubt_rand[::-1],
            self.zwischen[::-1],
            self.zum_rand[::-1],
            None if self.mitte_frei is None else self.mitte_frei[::-1],
            None if self.vorher_drin is None else self.vorher_drin[::-1],
            self.stand,
            self.aussen,
        )

    def vor(self, v_a, v_b):
        """Liegt v_b in Zählrichtung der Zeilen mehr als GLEICH hinter v_a?"""
        steigend = len(self.v_zeilen) < 2 or self.v_zeilen[-1] >= self.v_zeilen[0]
        return (v_b - v_a if steigend else v_a - v_b) > GLEICH

    def xy(self, u, v):
        return (float(u), float(v)) if self.laengs_x else (float(v), float(u))


def _fahrt(punkte, fahrt, raster, lage, vorige, w):
    """Eine Fahrt (vierachs_bahn._fahrten mit Zeile = Zeile quer, Winkelschritt = Stelle
    längs, mit der Lücke an beiden Enden) an die Bahn: hinein über das erste Stück, die Zeilen,
    zwischen ihnen Halbkreis oder Schritt, am Ende hinauf. Gibt die Länge im Vorschub zurück."""
    r_ = raster
    teile = []  # (art, m, js) mit js ohne die Lücke (0 … N − 1)
    for art, m, js in fahrt:
        if art == "zeile":
            teile.append((art, m, np.asarray(js) - 1))
        else:
            teile.append((art, m, int(js) - 1))
    _art, m0, js0 = teile[0]
    # Nur im Gleichlauf: Lief die vorige Zeile schon über den Anfang, steht dort nur noch ihr
    # Streifen ae – senkrecht hinein statt der Rampe von oben.
    nachbar = w.nur_gleichlauf and m0 > 0 and bool(r_.drin[m0 - 1, int(js0[0])])
    laenge = _einfahrt(punkte, r_, m0, js0, lage, vorige, w, nachbar)
    if w.nur_gleichlauf and len(js0) > 1:
        # Beginnt die Zeile an einer Wand, bliebe dort zwischen ihr und der vorigen die Ecke
        # der Stirn stehen (hin und her nimmt sie der Schritt): an der Wand hin und zurück.
        richtung = 1 if js0[-1] > js0[0] else -1
        start = r_.xy(r_.u_stellen[js0[0]], r_.v_zeilen[m0])
        da = abs(punkte[-1].x - start[0]) < GLEICH and abs(punkte[-1].y - start[1]) < GLEICH
        if da and _wand(r_, m0, int(js0[0]), -richtung):
            laenge += _wandfahrt(punkte, r_, m0, int(js0[0]), lage, teile, 0)
            laenge += _ueber_die_letzte(punkte, r_, m0, int(js0[0]), lage)
    for nummer, (art, m, js) in enumerate(teile):
        if art == "zeile":
            laenge += _zeile(punkte, r_, m, js, lage, w, nummer == 0)
            continue
        laenge += _schritt(punkte, r_, m, js, lage, teile, nummer)
    art, m, js = teile[-1]
    if art == "zeile" and len(js) > 1 and _wand(r_, m, int(js[-1]), 1 if js[-1] > js[0] else -1):
        laenge += _wandfahrt(punkte, r_, m, int(js[-1]), lage, teile, len(teile), ende=True)
    letzter = punkte[-1]
    punkte.append(bn.Punkt(True, letzter.x, letzter.y, w.sicher))
    return laenge


def _wand(r_, m, j, richtung):
    """Endet Zeile m an der Stelle j in Richtung `richtung` vor einer Wand – die nächste Stelle
    ist dort nicht erlaubt? Am Rand des Rasters (dem Überlauf) nicht."""
    k = j + richtung
    return 0 <= k < len(r_.u_stellen) and not bool(r_.erlaubt[m, k])


def _wandfahrt(punkte, r_, m, j, lage, teile, nummer, ende=False):
    """Vor einer Wand (Zeile m endet an der Stelle j): An der Wand bleibt zwischen zwei Zeilen
    stehen, was keine der beiden mit der Rundung der Stirn erreicht – die Zeilen hin und her
    lassen jeden zweiten Zwischenraum an der Wand aus (der Schritt zur nächsten Zeile liegt am
    anderen Ende), und vor der ersten und hinter der letzten Zeile bleibt die Ecke. Darum fährt
    der Fräser hier an der Wand entlang: zurück zur vorigen Zeile, an die Stelle, die der Wand am
    nächsten liegt – vor der ersten Zeile bis an den Rand der Fläche, so weit es dort erlaubt ist
    – und wieder her; am `ende` einer Fahrt erst hinter die letzte Zeile bis an den Rand, dann
    zurück, ohne wieder herzukommen. Gibt die Länge zurück."""
    hier = punkte[-1]
    u = float(r_.u_stellen[j])
    v_m = float(r_.v_zeilen[m])
    ziele = []
    letzte = len(r_.v_zeilen) - 1
    if (
        ende
        and m == letzte
        and bool(r_.erlaubt_rand[1, j])
        and bool(r_.zum_rand[1, j])
        and r_.vor(v_m, r_.v_rand[1])
    ):
        ziele.append(r_.xy(u, r_.v_rand[1]))
    vorige = next(
        (js for art, m_, js in reversed(teile[:nummer]) if art == "zeile" and m_ == m - 1), None
    )
    unten = None
    if vorige is not None and len(vorige):
        # Die vorige Zeile an dieser Wand: ihre Stelle, die j am nächsten liegt – nicht ihr
        # Anfang: Vor einem Zapfen endet diese Zeile mitten in der Fläche, die vorige begann am
        # anderen Ende, und die Wandfahrt zu ihrem Anfang lief quer durch den Zapfen (der
        # Prüfstand fand es, P-2026-10-01-26).
        # Liegen die Zeilen weit auseinander (großer Fräser, großes ae), muss auch dazwischen
        # frei sein – am runden Zapfen lief die Fahrt sonst quer hinein (P-2026-10-02-30).
        k = int(vorige[int(np.argmin(np.abs(np.asarray(vorige) - j)))])
        if bool(r_.zwischen[m - 1, min(j, k) : max(j, k) + 1].all()):
            unten = (float(r_.u_stellen[k]), float(r_.v_zeilen[m - 1]))
    elif m >= 1 and bool(r_.erlaubt[m - 1, j]) and bool(r_.zwischen[m - 1, j]):
        unten = (u, float(r_.v_zeilen[m - 1]))
    if (
        m <= 1
        and bool(r_.erlaubt_rand[0, j])
        and bool(r_.zum_rand[0, j])
        and r_.vor(r_.v_rand[0], float(r_.v_zeilen[0]))
        and (m == 0 or (bool(r_.erlaubt[0, j]) and bool(r_.zwischen[0, j])))
    ):
        unten = (u, r_.v_rand[0])  # über die erste Zeile hinaus bis an den Rand
    if unten is not None:
        ziele.append(r_.xy(*unten))
    if not ziele:
        return 0.0
    if not ende:
        ziele.append((hier.x, hier.y))
    laenge = 0.0
    for x, y in ziele:
        punkt = bn.Punkt(False, x, y, lage)
        laenge += bn.weg(punkte[-1], punkt)
        punkte.append(punkt)
    return laenge


def _einfahrt(punkte, r_, m, js, lage, vorige, w, nachbar=False):
    """Über den Anfang der ersten Zeile im Eilgang, hinab bis knapp über das Material: in der
    Luft senkrecht mit dem Eintauchvorschub auf die Lage; im Rohteil senkrecht bis ans Material
    und dann über die Rampe längs der Zeile – `nachbar` (neben der eben gefrästen Zeile, nur der
    Streifen ae am Rand der Stirn) senkrecht. Gibt die Länge der Rampe zurück."""
    u = r_.u_stellen[js]
    v = float(r_.v_zeilen[m])
    x0, y0 = r_.xy(u[0], v)
    punkte.append(bn.Punkt(True, x0, y0, w.sicher))
    luft = not r_.im_rohteil[js[0]]
    oben = lage if luft else vorige
    if r_.stand is not None and not luft:
        # Mit Materialstand: Der Eilgang hinab endet über dem höchsten Material unter der Stirn –
        # fuhr die Lage davor hier, höchstens auf ihr; steht unter der Mitte nichts, senkrecht.
        hoch = r_.stand.hoechste_bei(x0, y0, r_.aussen)
        if r_.vorher_drin is not None and bool(r_.vorher_drin[m, js[0]]):
            hoch = min(hoch, vorige)
        if hoch <= lage + MATERIAL:
            luft, oben = True, lage
        else:
            nachbar = nachbar or bool(r_.mitte_frei[m, js[0]])
            oben = hoch if nachbar else max(vorige, hoch)
    knapp = min(w.sicher, oben + w.sicherheit)
    if knapp < w.sicher:
        punkte.append(bn.Punkt(True, x0, y0, knapp))
    if luft or len(js) < 2 or vorige <= lage + GLEICH or nachbar:
        punkte.append(bn.Punkt(False, x0, y0, lage, True))
        return 0.0
    punkte.append(bn.Punkt(False, x0, y0, vorige, True))  # bis ans Material
    tiefe = np.full(len(u), lage)
    still = np.zeros(len(u))
    laenge = 0.0
    for stelle_u, stelle_z, _phi in vb._rampe(u, tiefe, still, 0, len(u) - 1, vorige, w):
        x, y = r_.xy(stelle_u, v)
        punkt = bn.Punkt(False, x, y, float(stelle_z))
        laenge += bn.weg(punkte[-1], punkt)
        punkte.append(punkt)
    return laenge


def _zeile(punkte, r_, m, js, lage, w, erste):
    """Die Zeile m über die Stellen js (in Fahrtrichtung): bis zum Ende, beim Austritt aus dem
    Rohteil langsamer. Den Anfang gibt es schon (Einfahrt oder Schritt). Gibt die Länge
    zurück."""
    v = float(r_.v_zeilen[m])
    u_a, u_b = float(r_.u_stellen[js[0]]), float(r_.u_stellen[js[-1]])
    laenge = 0.0
    if abs(u_b - u_a) < GLEICH:
        return 0.0
    vorwaerts = u_b > u_a
    kante = r_.roh_u[1] - r_.r_eben if vorwaerts else r_.roh_u[0] + r_.r_eben
    zwischen = (u_a < kante < u_b) if vorwaerts else (u_b < kante < u_a)
    ganz_drin = (u_b <= kante + GLEICH) if vorwaerts else (u_b >= kante - GLEICH)
    if zwischen:
        x, y = r_.xy(kante, v)
        punkt = bn.Punkt(False, x, y, lage)
        laenge += bn.weg(punkte[-1], punkt)
        punkte.append(punkt)
    x, y = r_.xy(u_b, v)
    anteil = 1.0 if ganz_drin else w.austritt
    punkt = bn.Punkt(False, x, y, lage, anteil=anteil)
    laenge += bn.weg(punkte[-1], punkt)
    punkte.append(punkt)
    return laenge


def _schritt(punkte, r_, m, j, lage, teile, nummer):
    """Von Zeile m zur nächsten an der Stelle j: ein Halbkreis in Fahrtrichtung hinaus, wenn
    beide Zeilen dort und auf dem Bogen frei sind – sonst gerade quer, vor einer Wand erst
    noch an ihr entlang zur vorigen Zeile und zurück (_wandfahrt). Gibt die Länge
    zurück."""
    v_von, v_bis = float(r_.v_zeilen[m]), float(r_.v_zeilen[m + 1])
    u = float(r_.u_stellen[j])
    x1, y1 = r_.xy(u, v_bis)
    # Die Richtung der Zeile davor: hin (wachsende Stellen) oder zurück.
    richtung = 1
    for art, _m, js in reversed(teile[:nummer]):
        if art == "zeile" and len(js) > 1:
            richtung = 1 if js[-1] > js[0] else -1
            break
    halb = abs(v_bis - v_von) / 2
    schritt_u = abs(float(r_.u_stellen[1] - r_.u_stellen[0])) if len(r_.u_stellen) > 1 else 1.0
    weit = int(math.ceil(halb / schritt_u - 1e-9))
    bis = j + richtung * weit
    frei = 0 <= bis < len(r_.u_stellen)
    if frei:
        stellen = np.arange(j, bis + richtung, richtung)
        frei = bool(
            r_.erlaubt[m, stellen].all()
            and r_.erlaubt[m + 1, stellen].all()
            and r_.zwischen[m, stellen].all()
        )
    laenge = 0.0
    if frei and halb > GLEICH:
        u_mitte = u
        u_durch = u + richtung * halb
        v_mitte = (v_von + v_bis) / 2
        mx, my = r_.xy(u_mitte, v_mitte)
        durch = r_.xy(u_durch, v_mitte)
        von = (punkte[-1].x, punkte[-1].y)
        uhr = bn.im_uhrzeigersinn(von, (x1, y1), durch)
        punkt = bn.Punkt(False, x1, y1, lage, bogen=(mx, my, uhr))
    else:
        if _wand(r_, m, j, richtung):
            laenge += _wandfahrt(punkte, r_, m, j, lage, teile, nummer)
        punkt = bn.Punkt(False, x1, y1, lage)
    laenge += bn.weg(punkte[-1], punkt)
    punkte.append(punkt)
    if punkt.bogen is None and _wand(r_, m, j, richtung):
        laenge += _ueber_die_letzte(punkte, r_, m + 1, j, lage)
    return laenge


def _ueber_die_letzte(punkte, r_, m, j, lage):
    """Beginnt die letzte Zeile m vor einer Wand (an der Stelle j), bleibt hinter ihr an der
    Wand die Ecke stehen: erst an der Wand entlang bis an den Rand der Fläche und zurück, so
    weit es dort erlaubt ist (wie _wandfahrt vor der ersten Zeile). Gibt die Länge zurück."""
    v_m = float(r_.v_zeilen[m])
    if (
        m != len(r_.v_zeilen) - 1
        or not bool(r_.erlaubt_rand[1, j])
        or not bool(r_.zum_rand[1, j])
        or not r_.vor(v_m, r_.v_rand[1])
    ):
        return 0.0
    hier = punkte[-1]
    laenge = 0.0
    for x, y in (r_.xy(float(r_.u_stellen[j]), r_.v_rand[1]), (hier.x, hier.y)):
        punkt = bn.Punkt(False, x, y, lage)
        laenge += bn.weg(punkte[-1], punkt)
        punkte.append(punkt)
    return laenge
