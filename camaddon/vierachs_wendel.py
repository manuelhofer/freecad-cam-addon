"""Wendelnut erkennen und ihr nach fahren (W-030).

Manuel, 2026-10-18, an seinem Wendel-Testteil (Ø 80, runde Nut R 11, Steigung 60): „die wendel
ist entgegen der drehrichtung ... da muss man sich was einfallen lassen das das dennoch sauber
herzustellen ist ... dann muss man vll mal hinten anfangen um die wendel zu fahren ??“ – und zum
Vorschlag mit Bild (27 → etwa 15,5 min): „Ja, vorgewählt bei Wendelnut“.

In der Abwicklung (a längs, φ rundum) ist eine Wendelnut ein schräges Band: Ihre Mitte liegt bei
a = a0 + p · φ / 360° (p: Steigung mit Vorzeichen, φ in Grad im Rahmen vierachs_huelle.rahmen),
mehrgängig um p / Gänge versetzt. erkennen() findet das Band in der Hüllfläche eines dünnen
Tasters; versaetze() legt die Bahnen quer über die Nut so, dass zwischen ihnen höchstens die
Kammhöhe stehen bleibt – am wirklichen Profil der Nut, nicht auf einer Ebene (in der Rundung R 11
mit der Kugel R 6 liegen die Bahnen enger als auf einer ebenen Fläche).
"""

import math
from dataclasses import dataclass

import numpy as np

from . import vierachs_huelle as vh

SCHRITT_A = 0.5  # mm – Raster längs zum Erkennen
SCHRITT_PHI = 2.0  # Grad – Raster rundum zum Erkennen
TASTER = 0.25  # mm – Radius des Stifts, der die Nut abtastet (fast ein Strahl)
TIEFE_MINDESTENS = 0.5  # mm unter dem Außenradius an dieser Stelle: dort ist Nut
SPALTEN_MINDESTENS = 0.5  # an so viel des Umfangs muss die Nut vorkommen
STIMMIG_MINDESTENS = 0.8  # so viele Schritte von Winkel zu Winkel mit derselben Steigung
STIMMIG_TOLERANZ = 0.6  # mm – so weit darf ein Schritt von der Steigung abweichen
GAENGE_HOECHSTENS = 4
GAENGE_EINIG = 0.9  # so dicht müssen die Gänge beieinander liegen (Länge des Mittelwerts)
PROFIL_SCHRITT = 0.05  # mm – so fein wird das Profil quer über die Nut abgetastet


@dataclass(frozen=True)
class Wendel:
    """Eine erkannte Wendelnut."""

    steigung: float  # mm je Umdrehung, mit Vorzeichen: a = a0 + steigung · φ / 360°
    a0: float  # a der Mitte von Gang 0 bei φ = 0
    gaenge: int  # so viele Gänge (um steigung / gaenge versetzt)
    breite: float  # axial an der Oberfläche (mm)
    tiefe: float  # so tief unter dem Außenradius daneben (mm)
    r_aussen: float  # Außenradius des Teils neben der Nut (mm)

    @property
    def teilung(self):
        """Abstand längs zwischen zwei Gängen (mm)."""
        return abs(self.steigung) / self.gaenge

    def mitte_bei(self, a_nah, winkel=0.0):
        """a der Nutmitte am Winkel `winkel` (Grad), die `a_nah` am nächsten liegt."""
        basis = self.a0 + self.steigung * winkel / 360.0
        return basis + self.teilung * round((a_nah - basis) / self.teilung)


def erkennen(netz, laengs, radial):
    """Die Wendelnut am Teil (`netz`, vierachs_huelle.vernetze, im Job) – oder None. Eine Nut
    zählt, wenn sie an mindestens SPALTEN_MINDESTENS des Umfangs vorkommt, ihre Mitte von Winkel
    zu Winkel stimmig um dieselbe Strecke wandert (das ist die Steigung, mindestens so groß wie
    die Nut breit – sonst ist es eine Ringnut) und die Gänge zusammenpassen."""
    l_, _u, _v = vh.rahmen(laengs, radial)
    a_teil = netz.punkte @ l_
    a_von, a_bis = float(a_teil.min()), float(a_teil.max())
    if a_bis - a_von < 8 * SCHRITT_A:
        return None
    a_werte = vh.raster_a(a_von + SCHRITT_A / 2, a_bis - SCHRITT_A, SCHRITT_A)
    phi = vh.raster_phi(SCHRITT_PHI)
    huelle = vh.schaftfraeser(netz, laengs, radial, TASTER, a_werte, phi, nur_vorne=True)
    return aus_huelle(huelle)


def aus_huelle(huelle):
    """erkennen() an einer fertigen Hüllfläche (vierachs_huelle.Huelle, Strahlen von der Achse)."""
    r = np.where(np.isfinite(huelle.r), huelle.r, np.nan)
    a = huelle.a
    n_a, n_phi = r.shape
    if n_a < 8 or n_phi < 8:
        return None
    zeilen = np.isfinite(r).any(axis=1)
    if not zeilen.any():
        return None
    with np.errstate(invalid="ignore"):
        aussen = np.nanmax(np.where(zeilen[:, None], r, -np.inf), axis=1)
        nut = (r < aussen[:, None] - TIEFE_MINDESTENS) & np.isfinite(r)
    schritt_a = float(a[1] - a[0])
    # Je Winkel die Stücke Nut längs: Mitte, Breite, Tiefe; „innen“: berührt kein Ende.
    spalten = []
    breiten, tiefen = [], []
    for j in range(n_phi):
        stuecke = []
        spalte = nut[:, j]
        if spalte.any():
            wechsel = np.flatnonzero(np.diff(spalte.astype(np.int8)))
            anfaenge = list(wechsel[~spalte[wechsel]] + 1)
            enden = list(wechsel[spalte[wechsel]])
            if spalte[0]:
                anfaenge.insert(0, 0)
            if spalte[-1]:
                enden.append(n_a - 1)
            for i0, i1 in zip(anfaenge, enden, strict=True):
                innen = i0 > 0 and i1 < n_a - 1
                mitte = 0.5 * (a[i0] + a[i1])
                stuecke.append((mitte, innen))
                if innen:
                    breiten.append(a[i1] - a[i0] + schritt_a)
                    tiefen.append(float(np.max(aussen[i0 : i1 + 1] - r[i0 : i1 + 1, j])))
        spalten.append(stuecke)
    mit_nut = sum(1 for s in spalten if s)
    if mit_nut < SPALTEN_MINDESTENS * n_phi or not breiten:
        return None
    breite = float(np.median(breiten))
    # Von Winkel zu Winkel: die nächste Mitte im Nachbarn – die Schritte müssen gleich sein.
    schritte = []
    for j in range(n_phi - 1):
        jetzt = [m for m, innen in spalten[j] if innen]
        weiter = np.array([m for m, innen in spalten[j + 1] if innen])
        if not jetzt or not len(weiter):
            continue
        for m in jetzt:
            k = int(np.argmin(np.abs(weiter - m)))
            if abs(weiter[k] - m) < breite:
                schritte.append(float(weiter[k] - m))
    if len(schritte) < SPALTEN_MINDESTENS * n_phi:
        return None
    schritte = np.array(schritte)
    mittel = float(np.median(schritte))
    if np.mean(np.abs(schritte - mittel) < STIMMIG_TOLERANZ) < STIMMIG_MINDESTENS:
        return None
    winkel_schritt = 360.0 / n_phi
    # Genau: Der Schritt je Winkel ist kleiner als das Raster längs – jedes Band über die Winkel
    # verfolgen und eine Gerade hindurch (je Band ihr eigener Achsenabschnitt).
    steigung = _steigung(spalten, mittel, winkel_schritt)
    if steigung is None or abs(steigung) < breite:  # eine Ringnut oder nichts – keine Wendel
        return None
    # Die Mitten auf φ = 0 zurückgerechnet: Sie liegen um die Teilung auseinander.
    t = np.array(
        [
            m - steigung * (j * winkel_schritt) / 360.0
            for j, stuecke in enumerate(spalten)
            for m, innen in stuecke
            if innen
        ]
    )
    winkel = 2 * math.pi * np.mod(t, abs(steigung)) / abs(steigung)
    for gaenge in range(1, GAENGE_HOECHSTENS + 1):
        zeiger = np.mean(np.exp(1j * gaenge * winkel))
        if abs(zeiger) >= GAENGE_EINIG:
            break
    else:
        return None
    a0 = float(np.angle(zeiger)) / (2 * math.pi * gaenge) * abs(steigung)
    return Wendel(
        steigung=float(steigung),
        a0=a0,
        gaenge=gaenge,
        breite=breite,
        tiefe=float(np.median(tiefen)),
        r_aussen=float(np.nanmedian(aussen[zeilen])),
    )


def _steigung(spalten, schritt, winkel_schritt):
    """Die Steigung (mm je Umdrehung) aus den Mitten je Winkel (`spalten`): Bänder von Winkel zu
    Winkel verfolgt (die nächste Mitte um etwa `schritt` weiter), durch alle eine Gerade mit je
    Band eigenem Achsenabschnitt. None, wenn kein Band lang genug ist."""
    baender = []
    offen = []  # [(letzte Mitte, Liste der (Winkel, a))]
    for j, stuecke in enumerate(spalten):
        mitten = [m for m, innen in stuecke if innen]
        weiter = []
        frei = list(mitten)
        for letzte, punkte in offen:
            if not frei:
                baender.append(punkte)
                continue
            k = int(np.argmin([abs(m - (letzte + schritt)) for m in frei]))
            if abs(frei[k] - (letzte + schritt)) < STIMMIG_TOLERANZ:
                m = frei.pop(k)
                punkte.append((j * winkel_schritt, m))
                weiter.append((m, punkte))
            else:
                baender.append(punkte)
        for m in frei:
            weiter.append((m, [(j * winkel_schritt, m)]))
        offen = weiter
    baender.extend(punkte for _letzte, punkte in offen)
    zaehler = nenner = 0.0
    for punkte in baender:
        if len(punkte) < 10:
            continue
        w = np.array([p[0] for p in punkte])
        a = np.array([p[1] for p in punkte])
        w = w - w.mean()
        zaehler += float(w @ (a - a.mean()))
        nenner += float(w @ w)
    if nenner <= 0:
        return None
    return zaehler / nenner * 360.0


def kamm(mitten, i, j, radius, proben=25):
    """Wie hoch zwischen den Lagen `i` und `j` (< j) einer Kugel mit `radius` stehen bleibt
    (`mitten`: (n, 2) die Mitten (u, r) im Schnitt längs, fein gestuft): Gegen die Fläche, die
    alle Lagen dazwischen zusammen hinterließen (die Vereinigung ihrer Kreise), wie weit die
    beiden allein zurückbleiben – gemessen quer zur Sehne zwischen ihnen, zur Seite des Materials.
    inf, wenn sie weiter als den Durchmesser auseinander liegen. Ohne Ableitung: Das Profil aus
    dem Netz ist stufig."""
    a = mitten[i]
    sehne = mitten[j] - a
    d = float(np.hypot(sehne[0], sehne[1]))
    if d >= 2 * radius:
        return math.inf
    if d < 1e-12:
        return 0.0
    # quer zur Sehne, mit steigendem u zur Seite des Materials (am Grund zur Achse hin)
    quer = np.array([sehne[1], -sehne[0]]) / d
    stellen = a + np.linspace(0.0, 1.0, proben)[:, None] * sehne
    abstand = mitten[None, i : j + 1, :] - stellen[:, None, :]
    laengs = abstand @ quer
    seitlich = (abstand * abstand).sum(axis=2) - laengs * laengs
    tief = np.where(
        seitlich <= radius * radius,
        laengs + np.sqrt(np.maximum(radius * radius - seitlich, 0.0)),
        -math.inf,
    )
    alle = tief.max(axis=1)
    zwei = np.maximum(tief[:, 0], tief[:, -1])
    return float(np.max(alle - zwei))


GLAETTEN = 9  # Punkte – so breit wird das Profil geglättet, bevor seine Richtung zählt


def versaetze(u, r_spitze, radius, kammhoehe, kugel, schrittweite, r_aussen):
    """Die Versätze quer zur Nutmitte (mm, längs), auf denen die Bahnen der Wendel nach fahren.
    `u`: das Raster quer (aufsteigend, gleicher Abstand), `r_spitze`: wo die Spitze des Fräsers
    dort steht (mit Aufmaß). Von der einen Kante der Nut zur anderen; mit der Kugel (`kugel`) so
    weit auseinander, dass höchstens `kammhoehe` stehen bleibt (kamm), sonst im Abstand
    `schrittweite`. Mit der Kugel zählen nur Lagen, deren Berührpunkt in der Nut liegt – rollt sie
    nur über die Kante, schlichtet sie nichts."""
    u = np.asarray(u, dtype=float)
    r_spitze = np.asarray(r_spitze, dtype=float)
    spitze = np.where(np.isfinite(r_spitze), r_spitze, r_aussen)
    if kugel:
        # Der Berührpunkt: von der Mitte einen Radius quer zur (geglätteten) Kurve der Mitten.
        mitten_r = spitze + radius
        kern = np.ones(GLAETTEN) / GLAETTEN
        glatt = np.convolve(np.pad(mitten_r, GLAETTEN // 2, mode="edge"), kern, mode="valid")
        steigung = np.gradient(glatt, u)
        beruehrt = glatt - radius / np.sqrt(1.0 + steigung * steigung)
        in_nut = np.isfinite(r_spitze) & (beruehrt < r_aussen - 1e-2)
    else:
        in_nut = np.isfinite(r_spitze) & (r_spitze < r_aussen - 1e-3)
    if not in_nut.any():
        return []
    innen = np.flatnonzero(in_nut)
    i_lo = max(int(innen[0]) - 1, 0)
    i_hi = min(int(innen[-1]) + 1, len(u) - 1)
    if not kugel:
        u_lo, u_hi = float(u[i_lo]), float(u[i_hi])
        anzahl = max(1, int(math.ceil((u_hi - u_lo) / max(schrittweite, 1e-3) - 1e-9)))
        return list(np.linspace(u_lo, u_hi, anzahl + 1))
    mitten = np.column_stack([u, spitze + radius])
    schritt = float(u[1] - u[0]) if len(u) > 1 else 1.0
    weitest = max(1, int(2 * radius / schritt))
    ergebnis = [float(u[i_lo])]
    i = i_lo
    while i < i_hi:
        unten, oben = i + 1, min(i + weitest, i_hi)
        if kamm(mitten, i, oben, radius) <= kammhoehe:
            unten = oben
        else:
            while oben - unten > 1:
                probe = (unten + oben) // 2
                if kamm(mitten, i, probe, radius) <= kammhoehe:
                    unten = probe
                else:
                    oben = probe
        i = unten
        ergebnis.append(float(u[i]))
    return ergebnis
