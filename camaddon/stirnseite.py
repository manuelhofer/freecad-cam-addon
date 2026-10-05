# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fräsen an der Stirnseite mit axialem Werkzeug an der Drehmaschine (Manuel, 2026-10-05).

„Generell, wenn wir jetzt planfräsen mit der Maschine … dass die Werkzeug-Z-Achse parallel zur
Hauptspindel-Z-Achse liegt … gibt es ja zwei Modi: komplett mit der Y-Achse oder interpoliert mit
der C-Achse. Ich finde, immer wenn es möglich ist, sollte die Y-Achse benutzt werden, bis zu
einem Verfahrweg von maximal 85 % von dem, was in der Maschine angegeben ist – danach muss die
C-Achse arbeiten und sich drehen“; dazu: beide Arten, C zu nutzen, wählbar; für alles an der
Stirn (Planfräsen, Taschen, Konturen, Nuten, Zapfen, Gravur, Bohrungen); die 85 % einstellbar.

Die Bahnen der Operationen bleiben, wie FreeCAD sie rechnet: X, Y, Z im Job, das Werkzeug längs
Z. `befehle` macht daraus die Sätze, die die Maschine fährt: C steht, solange die Spitze im
Rahmen liegt – X von der Grenze der Maschine, Y bis zum eingestellten Anteil ihres Wegs
(`Rahmen`). Liegt ein Punkt außerhalb, dreht C das Teil:

- `MIT` („C dreht beim Fräsen mit“): gerade so weit, dass der Punkt am Rand des Rahmens liegt –
  X, Y und C fahren zusammen, in kurzen Sätzen in G93 (die Zeit je Satz aus dem Weg am Teil).
- `SCHRITTE` („C in Schritten, dann Y“): C steht beim Fräsen. Verlässt die Bahn den Rahmen,
  fährt das Werkzeug auf die sichere Höhe, C dreht so, dass die Stelle auf der Mitte (Y 0)
  liegt, und es taucht dort wieder ein.

Die Sätze sind „ohne TCPM“ wie die der Rundum-Bahnen: X, Y im Rahmen der Maschine bei C 0, C
dreht das Teil darunter – so lesen sie das Prüffenster (kinematik) und der Postprozessor, der C
nach DIN 66217 schreibt.

Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass

MIT = "mit"
SCHRITTE = "schritte"
MODI = (MIT, SCHRITTE)
Y_NUTZEN = 85.0  # % des Y-Wegs der Maschine, vorbelegt (Manuel)

SCHRITT_MM = 0.5  # so dicht wird eine Strecke abgetastet, auf der C dreht
SCHRITT_GRAD = 0.5  # höchstens so weit dreht C je Satz
BOGEN_TOLERANZ = 0.002  # mm – Sehne eines Bogens, der in Strecken zerfällt
GENAU = 1e-9
ZYKLEN = ("G73", "G81", "G82", "G83", "G84", "G85", "G86", "G89")


@dataclass
class Rahmen:
    """Wo die Spitze bei C 0 hinkommt – in Koordinaten des Programms (X als Radius) – und wie C
    dreht. `drehsinn` +1: +C dreht das Teil rechtsherum um +Z des Programms (wie das Gelenk
    zählt, kinematik); `mitte`: die Drehachse in X, Y des Programms."""

    x_min: float
    x_max: float
    y_min: float
    y_max: float
    mitte: tuple = (0.0, 0.0)
    drehsinn: int = 1
    buchstabe: str = "C"

    def enthaelt(self, x, y):
        return (
            self.x_min - GENAU <= x <= self.x_max + GENAU
            and self.y_min - GENAU <= y <= self.y_max + GENAU
        )


def y_nutzen(maschine):
    """Wie viel Prozent ihres Wegs die Y-Achse an der Stirnseite fährt, bevor C hilft (der Wert
    „YNutzen“ an ihrer Betriebsart, sonst Y_NUTZEN)."""
    from . import maschine as m

    for ba in m.betriebsarten(maschine):
        if ba.Art == m.ART_LINEAR and m.programmname(ba).upper() == "Y":
            wert = float(getattr(ba, "YNutzen", 0.0) or 0.0)
            return wert if 0.0 < wert <= 100.0 else Y_NUTZEN
    return Y_NUTZEN


def rahmen(pruefung, aufnahme, laenge=100.0, nullpunkt_des_jobs=None):
    """Der Rahmen (Rahmen) der Maschine der Prüfung für ein Werkzeug auf `aufnahme` mit `laenge`
    – None, wenn sie keine C-Achse hat, die das Werkstück dreht. Aus dem Modell gerechnet: wie
    X und Y des Programms die Schlitten fahren, wo die Drehachse liegt, wie herum C dreht; Y bis
    y_nutzen Prozent ihrer Grenzen."""
    import FreeCAD

    from . import kinematik as km
    from . import maschine as m
    from .kette import LINEAR

    p = pruefung
    # Die C-Achse der Hauptspindel – nur an der Drehmaschine; ein Rundtisch C einer Fräse dreht
    # anders (3+2, 5 Achsen).
    haupt_c = m.spindeln(p.maschine).haupt_c
    c_achse = next(
        (
            a
            for a in p.kette.achsen
            if a.art != LINEAR and haupt_c is not None and a.gelenk == haupt_c.Gelenk
        ),
        None,
    )
    if c_achse is None or aufnahme is None or p.programmbuchstabe(c_achse) != "C":
        return None
    k = km.Kinematik(p, aufnahme, laenge, nullpunkt_des_jobs or FreeCAD.Vector())
    null = k.stellungen((0.0, 0.0, 0.0), {"C": 0.0})
    if null is None:
        return None

    def bereich(richtung, anteil):
        """(von, bis) im Programm längs `richtung`, so weit die Linearachsen kommen."""
        eins = k.stellungen(tuple(richtung), {"C": 0.0})
        if eins is None:  # keine Achse dafür (eine Drehmaschine ohne Y): nur 0
            return 0.0, 0.0
        von, bis = -math.inf, math.inf
        for achse in k.linear:
            je_mm = eins[achse] - null[achse]
            if abs(je_mm) < 1e-9:
                continue
            for grenze in (achse.minimum, achse.maximum):
                if grenze is None:
                    continue
                # Vom Stand bei 0 aus nur `anteil` des Wegs bis zur Grenze.
                t = (null[achse] + anteil * (grenze - null[achse]) - null[achse]) / je_mm
                if t > 0:
                    bis = min(bis, t)
                else:
                    von = max(von, t)
        return von, bis

    anteil_y = y_nutzen(p.maschine) / 100.0
    x_min, x_max = bereich((1.0, 0.0, 0.0), 1.0)
    y_min, y_max = bereich((0.0, 1.0, 0.0), anteil_y)
    # Drehachse und Drehsinn: wohin zwei Punkte des Programms mit C 90° am Teil wandern.
    gedreht_90 = dict(null)
    gedreht_90[c_achse] = null[c_achse] + 90.0
    q0 = k.am_werkstueck(gedreht_90)
    zehn = k.stellungen((10.0, 0.0, 0.0), {"C": 0.0})
    zehn[c_achse] = zehn[c_achse] + 90.0
    q1 = k.am_werkstueck(zehn)
    # Am Teil steht die Spitze um −C gedreht: (q1 − q0) = R(−a)·(10, 0).
    a = -math.degrees(math.atan2(q1[1] - q0[1], q1[0] - q0[0]))
    drehsinn = 1 if a > 0 else -1
    # q0 = R(−a)·(0 − m) + m → (I − R(−a))·m = q0
    c, s = math.cos(math.radians(-a)), math.sin(math.radians(-a))
    a11, a12, a21, a22 = 1.0 - c, s, -s, 1.0 - c
    det = a11 * a22 - a12 * a21
    mitte = ((q0[0] * a22 - a12 * q0[1]) / det, (a11 * q0[1] - a21 * q0[0]) / det)
    return Rahmen(x_min, x_max, y_min, y_max, mitte, drehsinn, "C")


EIGENSCHAFT = "StirnModus"  # am Job: MIT oder SCHRITTE


def modus(job):
    """Wie C an der Stirnseite dieses Jobs hilft, wo Y nicht reicht – MIT ohne Angabe."""
    wert = str(getattr(job, EIGENSCHAFT, "") or "")
    return wert if wert in MODI else MIT


def setze_modus(job, wert):
    """Merkt sich am Job, wie C an der Stirnseite hilft (MIT oder SCHRITTE)."""
    from .sprache import tr

    if EIGENSCHAFT not in job.PropertiesList:
        job.addProperty("App::PropertyString", EIGENSCHAFT, "CAM-Addon", tr("st.eigenschaft"))
    if job.getPropertyByName(EIGENSCHAFT) != wert:
        setattr(job, EIGENSCHAFT, wert)


def job_von(op):
    """Der Job der Operation, oder None."""
    from . import job_schnittwerte as js

    for job in js.jobs(op.Document):
        if op in js.operationen(job):
            return job
    return None


def sicher_z(op):
    """Die sichere Höhe der Operation (ClearanceHeight, sonst SafeHeight) – None ohne."""
    for name in ("ClearanceHeight", "SafeHeight"):
        wert = getattr(op, name, None)
        if wert is None:
            continue
        try:
            return float(wert.getValueAs("mm")) if hasattr(wert, "getValueAs") else float(wert)
        except (TypeError, ValueError):
            continue
    return None


def ist_stirn(op, befehle_):
    """Fräst die Operation an der Stirnseite – eine Bahn in X, Y, Z ohne Rundachsen, keine der
    4-Achs-Operationen des Addons und keine mit Achse je Satz?"""
    from . import simultan_operation as so
    from . import vierachs_operation as vo

    if vo.ist_rundum(op) or so.ist_simultan(op):
        return False
    return not any(set(b.Parameters) & {"A", "B", "C"} for b in befehle_)


def gedreht(rahmen, x, y, winkel):
    """Wo der Punkt (x, y) des Teils steht, wenn das Teil um `winkel` (Grad, rechtsherum um +Z)
    gedreht ist – X, Y der Maschine bei C 0."""
    cx, cy = rahmen.mitte
    c, s = math.cos(math.radians(winkel)), math.sin(math.radians(winkel))
    dx, dy = x - cx, y - cy
    return cx + c * dx - s * dy, cy + s * dx + c * dy


def erreichbar(rahmen, x, y, winkel):
    return rahmen.enthaelt(*gedreht(rahmen, x, y, winkel))


def drehung_fuer(rahmen, x, y, winkel, modus):
    """Wie weit das Teil gedreht stehen muss (Grad, fortlaufend), damit (x, y) im Rahmen liegt –
    `winkel`, wenn es schon passt. MIT: die kleinste Drehung von `winkel` aus (der Punkt dann am
    Rand); SCHRITTE: so, dass der Punkt auf der Mitte (Y wie die Drehachse) vor ihr liegt, die
    nächste solche Stellung. ValueError, wenn keine Drehung ihn in den Rahmen bringt."""
    if erreichbar(rahmen, x, y, winkel):
        return winkel
    cx, cy = rahmen.mitte
    rho = math.hypot(x - cx, y - cy)
    alpha = math.degrees(math.atan2(y - cy, x - cx))
    if modus == SCHRITTE:
        ziel = -alpha  # der Punkt auf +X vor der Achse
        ziel += 360.0 * round((winkel - ziel) / 360.0)
        if erreichbar(rahmen, x, y, ziel):
            return ziel
    # Die kleinste Drehung: in Schritten von 0,25° abtasten, dann die Grenze genau.
    for k in range(1, 1441):
        for vorzeichen in (1.0, -1.0):
            versuch = winkel + vorzeichen * 0.25 * k
            if erreichbar(rahmen, x, y, versuch):
                innen, aussen = versuch, versuch - vorzeichen * 0.25
                for _ in range(40):
                    mitte = 0.5 * (innen + aussen)
                    if erreichbar(rahmen, x, y, mitte):
                        innen = mitte
                    else:
                        aussen = mitte
                return innen
    from .sprache import tr

    raise ValueError(tr("st.nicht_erreichbar", x=f"{x:.3f}", y=f"{y:.3f}", radius=f"{rho:.3f}"))


def befehle(befehle_, rahmen, modus=MIT, sicher_z=None):
    """Die Sätze einer Operation an der Stirnseite, wie die Maschine sie fährt (siehe oben):
    Path-Befehle mit X, Y im Rahmen der Maschine und C. `sicher_z`: auf diese Höhe fährt das
    Werkzeug, bevor C in SCHRITTE dreht (ohne: die höchste Z der Bahn). Absolut (G90); ein G91
    – ValueError."""
    import Path

    return _Umrechnung(rahmen, modus, sicher_z, Path.Command).rechne(list(befehle_))


class _Umrechnung:
    def __init__(self, rahmen, modus, sicher_z, befehl):
        self.r = rahmen
        self.modus = modus if modus in MODI else MIT
        self.sicher_z = sicher_z
        self.befehl = befehl
        self.pos = [None, None, None]  # die Spitze im Programm (am Teil)
        self.winkel = 0.0  # so weit ist das Teil gedreht (rechtsherum, Grad)
        self.f = None  # Vorschub in mm/s, wie FreeCAD ihn führt
        self.g93 = False
        self.f_g93 = None
        self.raus = []
        self.c_steht = False  # C wurde schon geschrieben

    # --- Ausgabe ---------------------------------------------------------------------------

    def _c(self, winkel):
        return winkel * self.r.drehsinn

    def _xy(self, x, y, winkel):
        return gedreht(self.r, x, y, winkel)

    def _g94(self):
        if self.g93:
            self.raus.append(self.befehl("G94"))
            self.g93 = False
            self.f_g93 = None
            return True
        return False

    def _g0(self, x, y, z, winkel):
        werte = {}
        if x is not None and y is not None:
            mx, my = self._xy(x, y, winkel)
            werte.update(X=mx, Y=my)
        if z is not None:
            werte["Z"] = z
        if not self.c_steht or abs(winkel - self.winkel) > GENAU:
            werte[self.r.buchstabe] = self._c(winkel)
            self.c_steht = True
        self.winkel = winkel
        if werte:
            self.raus.append(self.befehl("G0", werte))

    def _g1(self, x, y, z, winkel, laenge=None, f=None):
        """Ein Satz im Vorschub zu (x, y, z) am Teil, das Teil um `winkel` gedreht. Dreht C,
        in G93 mit der Zeit aus `laenge` (mm am Teil)."""
        mx, my = self._xy(x, y, winkel)
        werte = {"X": mx, "Y": my, "Z": z}
        dreht = abs(winkel - self.winkel) > GENAU
        if dreht or not self.c_steht:
            werte[self.r.buchstabe] = self._c(winkel)
            self.c_steht = True
        vorschub = f if f is not None else self.f
        if dreht and vorschub:
            if not self.g93:
                self.raus.append(self.befehl("G93"))
                self.g93 = True
            from .vierachs_bahn import _anderes_f

            zeit = max(laenge or 0.0, 1e-6) / (vorschub * 60.0)  # min
            self.f_g93 = _anderes_f(1.0 / zeit / 60.0, self.f_g93)
            werte["F"] = self.f_g93
        else:
            zurueck = self._g94()  # schreibt G94, wenn G93 noch gilt
            if (zurueck or f is not None) and vorschub:
                werte["F"] = vorschub
        self.winkel = winkel
        self.raus.append(self.befehl("G1", werte))

    # --- Bewegungen ------------------------------------------------------------------------

    def rechne(self, befehle_):
        for befehl in befehle_:
            name = befehl.Name.upper()
            p = dict(befehl.Parameters)
            if name.startswith("(") or not name:
                self.raus.append(befehl)
                continue
            if name == "G91":
                from .sprache import tr

                raise ValueError(tr("st.g91"))
            if "F" in p and name in ("G1", "G01", "G2", "G02", "G3", "G03"):
                self.f = float(p["F"])
            if name in ("G0", "G00"):
                self._eilgang(p)
            elif name in ("G1", "G01"):
                self._gerade(p, f=float(p["F"]) if "F" in p else None)
            elif name in ("G2", "G02", "G3", "G03"):
                self._bogen(name, p)
            elif name in ZYKLEN:
                self._zyklus(befehl, name, p)
            else:
                self.raus.append(befehl)
        self._g94()
        return self.raus

    def _ziel(self, p):
        x, y, z = self.pos
        return (
            float(p["X"]) if "X" in p else x,
            float(p["Y"]) if "Y" in p else y,
            float(p["Z"]) if "Z" in p else z,
        )

    def _eilgang(self, p):
        self._g94()
        x, y, z = self._ziel(p)
        if x is None or y is None:  # noch keine Stelle in X, Y: nur Z
            self.pos = [x, y, z]
            self.raus.append(self.befehl("G0", {k: v for k, v in p.items() if k in "XYZ"}))
            return
        winkel = drehung_fuer(self.r, x, y, self.winkel, self.modus)
        if self.modus == SCHRITTE and abs(winkel - self.winkel) > GENAU and z is not None:
            oben = self._sicher()
            if self.pos[2] is not None and self.pos[2] < oben - GENAU:
                self.raus.append(self.befehl("G0", {"Z": oben}))
        self._g0(x, y, z, winkel)
        self.pos = [x, y, z]

    def _sicher(self):
        if self.sicher_z is not None:
            return float(self.sicher_z)
        return max(z for z in (self.pos[2], 0.0) if z is not None)

    def _gerade(self, p, f=None):
        ziel = self._ziel(p)
        if None in self.pos:
            self.pos = list(ziel)
            if None in ziel:
                self.raus.append(self.befehl("G1", dict(p)))
                return
            self._g1(*ziel, drehung_fuer(self.r, ziel[0], ziel[1], self.winkel, self.modus), f=f)
            return
        self._strecke(tuple(self.pos), ziel, f)

    def _strecke(self, von, nach, f=None):
        """Von `von` nach `nach` (am Teil) im Vorschub."""
        laenge = math.dist(von, nach)
        if laenge < GENAU:
            return
        if self.modus == SCHRITTE:
            self._strecke_schritte(von, nach, laenge, f)
        else:
            self._strecke_mit(von, nach, laenge, f)
        self.pos = list(nach)

    def _punkt(self, von, nach, t):
        return tuple(a + t * (b - a) for a, b in zip(von, nach, strict=True))

    def _strecke_mit(self, von, nach, laenge, f):
        n = max(1, int(math.ceil(laenge / SCHRITT_MM)))
        punkte = [self._punkt(von, nach, k / n) for k in range(1, n + 1)]
        # Passt die ganze Strecke ohne zu drehen, bleibt sie ein Satz.
        if all(erreichbar(self.r, q[0], q[1], self.winkel) for q in punkte):
            self._g1(*nach, self.winkel, laenge, f)
            return
        # Schritt für Schritt längs der Strecke; dreht C weiter als SCHRITT_GRAD, halbieren –
        # nahe der Drehachse am Rand des Rahmens muss C schnell drehen (wie TRANSMIT dort).
        t, winkel, vorher = 0.0, self.winkel, von
        while t < 1.0 - GENAU:
            weiter = min(1.0, t + SCHRITT_MM / laenge)
            while True:
                q = self._punkt(von, nach, weiter)
                neu = drehung_fuer(self.r, q[0], q[1], winkel, MIT)
                if abs(neu - winkel) <= SCHRITT_GRAD + GENAU or (weiter - t) * laenge < 1e-4:
                    break
                weiter = 0.5 * (t + weiter)
            # Die Zeit des Satzes: der Weg am Teil – mindestens der Bogen, den der Punkt um die
            # Achse zieht, so dreht C nicht schneller, als der Vorschub dort läuft.
            # Durch die Drehmitte, wenn X nicht dahinter kommt, dreht C dort um 180° – wenigstens
            # so langsam wie auf 1 mm Radius.
            rho = max(1.0, math.hypot(q[0] - self.r.mitte[0], q[1] - self.r.mitte[1]))
            weg = max(math.dist(vorher, q), rho * abs(math.radians(neu - winkel)))
            self._g1(*q, neu, weg, f)
            f = None
            t, winkel, vorher = weiter, neu, q

    def _strecke_schritte(self, von, nach, laenge, f):
        n = max(1, int(math.ceil(laenge / SCHRITT_MM)))
        anfang = 0.0
        while True:
            # Die erste Stelle, an der die Strecke den Rahmen verlässt.
            raus = None
            for k in range(1, n + 1):
                t = k / n
                if t <= anfang + GENAU:
                    continue
                q = self._punkt(von, nach, t)
                if not erreichbar(self.r, q[0], q[1], self.winkel):
                    raus = t
                    break
            if raus is None:
                self._g1(*nach, self.winkel, laenge, f)
                return
            innen, aussen = max(anfang, raus - 1.0 / n), raus
            for _ in range(40):
                mitte = 0.5 * (innen + aussen)
                q = self._punkt(von, nach, mitte)
                if erreichbar(self.r, q[0], q[1], self.winkel):
                    innen = mitte
                else:
                    aussen = mitte
            grenze = self._punkt(von, nach, innen)
            if innen > anfang + GENAU:
                self._g1(*grenze, self.winkel, laenge * (innen - anfang), f)
                f = None
            # Hoch, C drehen, über der Stelle wieder hinunter.
            weiter = self._punkt(von, nach, min(1.0, innen + 0.5 / n))
            winkel = drehung_fuer(self.r, weiter[0], weiter[1], self.winkel, SCHRITTE)
            if not erreichbar(self.r, grenze[0], grenze[1], winkel):
                winkel = drehung_fuer(self.r, grenze[0], grenze[1], winkel, SCHRITTE)
            self._g94()
            self.raus.append(self.befehl("G0", {"Z": self._sicher()}))
            self._g0(grenze[0], grenze[1], None, winkel)
            vorschub = f if f is not None else self.f
            werte = {"Z": grenze[2]}
            if vorschub:
                werte["F"] = vorschub
            self.raus.append(self.befehl("G1", werte))
            anfang = innen

    def _bogen(self, name, p):
        x0, y0, z0 = self.pos
        x1, y1, z1 = self._ziel(p)
        mx, my = x0 + float(p.get("I", 0.0)), y0 + float(p.get("J", 0.0))
        r = math.hypot(x0 - mx, y0 - my)
        a0 = math.atan2(y0 - my, x0 - mx)
        a1 = math.atan2(y1 - my, x1 - mx)
        im_uhrzeigersinn = name in ("G2", "G02")
        bogen = a1 - a0
        if im_uhrzeigersinn and bogen >= -GENAU:
            bogen -= 2.0 * math.pi
        elif not im_uhrzeigersinn and bogen <= GENAU:
            bogen += 2.0 * math.pi
        schritt = 2.0 * math.acos(max(-1.0, 1.0 - BOGEN_TOLERANZ / max(r, 1e-6)))
        n = max(2, int(math.ceil(abs(bogen) / max(schritt, 1e-6))))
        punkte = [
            (
                mx + r * math.cos(a0 + bogen * k / n),
                my + r * math.sin(a0 + bogen * k / n),
                z0 + (z1 - z0) * k / n,
            )
            for k in range(1, n + 1)
        ]
        f = float(p["F"]) if "F" in p else None
        if all(erreichbar(self.r, q[0], q[1], self.winkel) for q in punkte):
            # Bleibt im Rahmen: ein Bogen, Ende und Mitte gedreht.
            ex, ey = self._xy(x1, y1, self.winkel)
            c, s = math.cos(math.radians(self.winkel)), math.sin(math.radians(self.winkel))
            i, j = float(p.get("I", 0.0)), float(p.get("J", 0.0))
            werte = {"X": ex, "Y": ey, "Z": z1, "I": c * i - s * j, "J": s * i + c * j}
            zurueck = self._g94()  # schreibt G94, wenn G93 noch gilt
            if (zurueck or f is not None) and (f or self.f):
                werte["F"] = f if f is not None else self.f
            if not self.c_steht:
                werte[self.r.buchstabe] = self._c(self.winkel)
                self.c_steht = True
            self.raus.append(self.befehl(name, werte))
            self.pos = [x1, y1, z1]
            return
        vorher = (x0, y0, z0)
        for q in punkte:
            self._strecke(vorher, q, f)
            f = None
            vorher = q

    def _zyklus(self, befehl, name, p):
        """Ein Bohrzyklus an (X, Y): C dreht davor im Eilgang, wenn die Stelle es braucht."""
        self._g94()
        x, y, z = self._ziel(p)
        if x is None or y is None:
            self.raus.append(befehl)
            return
        winkel = drehung_fuer(self.r, x, y, self.winkel, self.modus)
        if abs(winkel - self.winkel) > GENAU or not self.c_steht:
            self.raus.append(self.befehl("G0", {self.r.buchstabe: self._c(winkel)}))
            self.c_steht = True
            self.winkel = winkel
        mx, my = self._xy(x, y, winkel)
        werte = dict(p)
        werte.update(X=mx, Y=my)
        self.raus.append(self.befehl(name, werte))
        self.pos = [x, y, self.pos[2]]
