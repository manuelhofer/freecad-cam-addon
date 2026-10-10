# SPDX-License-Identifier: LGPL-2.1-or-later
"""Der Abstand von Punkten zu einem Netz aus Dreiecken, mit numpy – als Schranke nach unten für
die Kollision (Spezifikation Strategien 16.5, Hebel 2): Das Teil wird einmal vernetzt
(`Netz`), die Dreiecke liegen in einem Gitter aus Zellen; für viele Punkte auf einmal sagt
`abstand`, wie weit jeder mindestens von der Oberfläche entfernt ist. Die Oberfläche selbst
liegt höchstens `toleranz` neben dem Netz (die Sehnen der Vernetzung), darum zieht `abstand`
sie ab. Ein Punkt, in dessen Umgebung von einer Zelle kein Dreieck liegt, ist mindestens eine
Zellenbreite entfernt – mehr sagt das Gitter nicht, und mehr braucht die Kollision nicht.

Was ein Netz nicht sagt: ob ein Punkt im Teil steckt. Die Kollision benutzt die Schranke nur
entlang einer stetigen Bewegung, die außerhalb begann – näher als die Schranke kommt ein Körper
der Oberfläche nicht, und durch sie hindurch käme er nur über einen Abstand 0, den die genaue
Rechnung vorher sieht (kollision._stelle)."""

import numpy as np

ZELLE_MINDESTENS = 2.0  # mm – kleiner lohnt sich nicht: je Punkt werden 27 Zellen gelesen
ZELLE_HOECHSTENS = 25.0  # mm – größer: zu viele Dreiecke je Zelle
STAPEL = 4096  # so viele Paare (Strecke, Dreieck) rechnet `kapseln` auf einmal, die nächsten zuerst
# Mehr Paare als das: zu teuer, die Abfrage gibt auf (die Kollision fragt dann OpenCascade).
PAARE_HOECHSTENS = 60000


class Netz:
    """Die Dreiecke einer Form in einem Gitter. `toleranz`: die Sehnenabweichung der
    Vernetzung (mm). `zelle`: die Zellenbreite (mm), ohne Angabe nach der Größe der Form."""

    def __init__(self, form, toleranz=0.02, zelle=None):
        # Eine Form, die schon feiner vernetzt war, bliebe so fein (OpenCascade merkt sich das
        # Netz an der Form); eine Kopie ohne Netz wird so grob wie verlangt.
        punkte, dreiecke = form.copy(False, False).tessellate(toleranz)
        self.toleranz = float(toleranz)
        if not dreiecke:
            self.ecken = np.zeros((0, 3, 3))
            self.zelle = ZELLE_MINDESTENS
            self.ursprung = np.zeros(3)
            self.anzahl = np.ones(3, dtype=np.int64)
            self.start = np.zeros(2, dtype=np.int64)
            self.index = np.zeros(0, dtype=np.int64)
            return
        ecken = np.array([(p.x, p.y, p.z) for p in punkte], dtype=np.float64)
        self.ecken = ecken[np.array(dreiecke, dtype=np.int64)]  # (m, 3, 3)
        unten = self.ecken.min(axis=(0, 1))
        oben = self.ecken.max(axis=(0, 1))
        if zelle is None:
            # etwa 24 Zellen längs der größten Kante, in Grenzen
            zelle = min(ZELLE_HOECHSTENS, max(ZELLE_MINDESTENS, float(np.max(oben - unten)) / 24))
        self.zelle = float(zelle)
        self.ursprung = unten - self.zelle  # eine Zelle Rand: Punkte knapp daneben fallen hinein
        self.anzahl = np.maximum(
            np.ceil((oben + self.zelle - self.ursprung) / self.zelle).astype(np.int64) + 1, 1
        )
        self._gitter_bauen()

    def _gitter_bauen(self):
        """Jedes Dreieck in jede Zelle, die sein Hüllquader berührt (CSR: `start` je Zelle,
        `index` die Dreiecke)."""
        d_unten = self.ecken.min(axis=1)
        d_oben = self.ecken.max(axis=1)
        i0 = self._zelle_von(d_unten)
        i1 = self._zelle_von(d_oben)
        spannen = i1 - i0 + 1  # (m, 3) Zellen je Achse
        eintraege = []
        for ox in range(int(spannen[:, 0].max())):
            for oy in range(int(spannen[:, 1].max())):
                for oz in range(int(spannen[:, 2].max())):
                    welche = (spannen[:, 0] > ox) & (spannen[:, 1] > oy) & (spannen[:, 2] > oz)
                    if not welche.any():
                        continue
                    ix = i0[welche, 0] + ox
                    iy = i0[welche, 1] + oy
                    iz = i0[welche, 2] + oz
                    eintraege.append((self._zellennummer(ix, iy, iz), np.flatnonzero(welche)))
        zellen = np.concatenate([e[0] for e in eintraege])
        dreiecke = np.concatenate([e[1] for e in eintraege])
        reihenfolge = np.argsort(zellen, kind="stable")
        zellen = zellen[reihenfolge]
        self.index = dreiecke[reihenfolge]
        self.d_unten = self.ecken.min(axis=1)  # Hüllquader je Dreieck, für die Vorauswahl
        self.d_oben = self.ecken.max(axis=1)
        gesamt = int(np.prod(self.anzahl))
        self.start = np.zeros(gesamt + 1, dtype=np.int64)
        np.add.at(self.start, zellen + 1, 1)
        np.cumsum(self.start, out=self.start)

    def _zelle_von(self, punkte):
        """Zellenindizes (…, 3) der Punkte, in das Gitter geklemmt."""
        i = np.floor((punkte - self.ursprung) / self.zelle).astype(np.int64)
        return np.clip(i, 0, self.anzahl - 1)

    def _zellennummer(self, ix, iy, iz):
        return (ix * self.anzahl[1] + iy) * self.anzahl[2] + iz

    def _dreiecke_in(self, zellen):
        """Die Dreiecke (Indizes) in den Zellen (…, 3; jede Zelle einmal), ungültige übergangen.
        Ein Dreieck, das in mehreren Zellen liegt, kommt mehrmals – das ist billiger als
        `np.unique`, und zweimal gerechnet ändert ein Minimum nicht."""
        zellen = zellen.reshape(-1, 3)
        gueltig = np.all((zellen >= 0) & (zellen < self.anzahl), axis=1)
        if not gueltig.any():
            return np.zeros(0, dtype=np.int64)
        nummern = self._zellennummer(zellen[gueltig, 0], zellen[gueltig, 1], zellen[gueltig, 2])
        anfang = self.start[nummern]
        laengen = self.start[nummern + 1] - anfang
        welche = np.flatnonzero(laengen)
        if len(welche) == 0:
            return np.zeros(0, dtype=np.int64)
        laengen = laengen[welche]
        anfang = anfang[welche]
        lauf = np.arange(int(laengen.sum())) - np.repeat(np.cumsum(laengen) - laengen, laengen)
        return self.index[np.repeat(anfang, laengen) + lauf]

    def kapseln(self, von, nach, reichweite=None):
        """Je Strecke (von, nach: (k, 3)): so weit ist sie mindestens von der Oberfläche
        entfernt – wie `abstand`, für Strecken statt Punkte (eine Kapsel mit Radius r ist dann
        mindestens Ergebnis − r entfernt). Höchstens `reichweite` (ohne Angabe eine
        Zellenbreite) minus `toleranz`: So weit sucht es um die Strecken; eine Kapsel mit
        Radius r braucht mindestens r plus den Abstand, der entscheiden soll."""
        von = np.asarray(von, dtype=np.float64).reshape(-1, 3)
        nach = np.asarray(nach, dtype=np.float64).reshape(-1, 3)
        k = len(von)
        reichweite = self.zelle if reichweite is None else float(reichweite)
        ergebnis = np.full(k, reichweite)
        if k == 0 or len(self.ecken) == 0:
            return ergebnis - self.toleranz
        # Die Dreiecke um alle Strecken auf einmal (sie liegen meist nah beieinander – die
        # Teile eines Werkzeugs auf einer Achse); dann jede Strecke gegen jedes davon.
        unten = np.minimum(von, nach).min(axis=0)
        oben = np.maximum(von, nach).max(axis=0)
        i0 = self._zelle_von(unten - reichweite)
        i1 = self._zelle_von(oben + reichweite)
        zellen = np.stack(
            np.meshgrid(
                np.arange(i0[0], i1[0] + 1),
                np.arange(i0[1], i1[1] + 1),
                np.arange(i0[2], i1[2] + 1),
                indexing="ij",
            ),
            axis=-1,
        )
        dreiecke = self._dreiecke_in(zellen)
        m = len(dreiecke)
        if m == 0:
            return ergebnis - self.toleranz
        # Nur Dreiecke, deren Hüllquader der Strecke näher als die Suchweite kommt – und die
        # nächsten zuerst: Sobald das Beste je Strecke unter der Lücke der übrigen liegt,
        # können die nichts mehr ändern (ihr Abstand ist mindestens ihre Lücke).
        d_unten, d_oben = self.d_unten[dreiecke], self.d_oben[dreiecke]  # (m, 3)
        s_unten, s_oben = np.minimum(von, nach), np.maximum(von, nach)  # (k, 3)
        luecke = np.maximum(
            np.maximum(
                s_unten[:, None, :] - d_oben[None, :, :], d_unten[None, :, :] - s_oben[:, None, :]
            ),
            0.0,
        )
        luecke = np.sqrt(np.einsum("kmj,kmj->km", luecke, luecke))  # (k, m)
        paare_k, paare_m = np.nonzero(luecke < reichweite)
        if len(paare_k) == 0:
            return ergebnis - self.toleranz
        if len(paare_k) > PAARE_HOECHSTENS * k:
            return np.zeros(k)  # nichts entschieden – billiger als die Rechnung
        luecken = luecke[paare_k, paare_m]
        reihenfolge = np.argsort(luecken, kind="stable")
        for anfang in range(0, len(reihenfolge), STAPEL):
            stapel = reihenfolge[anfang : anfang + STAPEL]
            kk = paare_k[stapel]
            offen = luecken[stapel] < ergebnis[kk]
            if not offen.any():
                if luecken[stapel[0]] >= ergebnis.max():
                    break  # alle weiteren Lücken sind mindestens so groß
                continue
            kk, mm = kk[offen], paare_m[stapel[offen]]
            d = segment_dreieck_abstand(von[kk], nach[kk], self.ecken[dreiecke[mm]])
            np.minimum.at(ergebnis, kk, d)
        return ergebnis - self.toleranz

    def abstand(self, punkte):
        """Je Punkt (n, 3): so weit ist er mindestens von der Oberfläche entfernt – der Abstand
        zum Netz minus `toleranz`, höchstens eine Zellenbreite minus `toleranz` (weiter sieht das
        Gitter nicht). Nie mehr als der wahre Abstand zur Oberfläche."""
        punkte = np.asarray(punkte, dtype=np.float64).reshape(-1, 3)
        n = len(punkte)
        ergebnis = np.full(n, self.zelle)
        if n == 0 or len(self.ecken) == 0:
            return ergebnis - self.toleranz
        mitte = self._zelle_von(punkte)
        # Punkte außerhalb des Gitters (mit Rand): mindestens so weit wie bis zum Rand, höchstens
        # eine Zelle – der Rand liegt eine Zelle neben der Form.
        innen = np.all(
            (punkte >= self.ursprung) & (punkte < self.ursprung + self.anzahl * self.zelle), axis=1
        )
        if not innen.all():
            draussen = punkte[~innen]
            luecke = np.maximum(
                np.maximum(
                    self.ursprung - draussen, draussen - (self.ursprung + self.anzahl * self.zelle)
                ),
                0.0,
            )
            ergebnis[~innen] = np.minimum(self.zelle, np.linalg.norm(luecke, axis=1) + self.zelle)
        # Die 27 Zellen um jeden Punkt – alle Dreiecke, die ihm näher als eine Zelle sein können.
        versatz = np.array([(x, y, z) for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1)])
        zellen = mitte[:, None, :] + versatz[None, :, :]  # (n, 27, 3)
        gueltig = np.all((zellen >= 0) & (zellen < self.anzahl), axis=2)
        nummern = self._zellennummer(zellen[..., 0], zellen[..., 1], zellen[..., 2])
        nummern = np.where(gueltig, nummern, 0)
        anfang = self.start[nummern]
        laengen = np.where(gueltig, self.start[nummern + 1] - anfang, 0)  # (n, 27)
        je_punkt = laengen.sum(axis=1)
        gesamt = int(je_punkt.sum())
        if gesamt == 0:
            return ergebnis - self.toleranz
        # Paare (Punkt, Dreieck) ausgerollt: je Zelle ein Bereich in `index`.
        flach_laengen = laengen.ravel()
        flach_anfang = anfang.ravel()
        welche = np.flatnonzero(flach_laengen)
        punkt_je_bereich = welche // 27
        wiederholt = np.repeat(np.arange(len(welche)), flach_laengen[welche])
        lauf = np.arange(gesamt) - np.repeat(
            np.cumsum(flach_laengen[welche]) - flach_laengen[welche], flach_laengen[welche]
        )
        dreieck = self.index[flach_anfang[welche][wiederholt] + lauf]
        punkt = punkt_je_bereich[wiederholt]
        d = punkt_dreieck_abstand(punkte[punkt], self.ecken[dreieck])
        np.minimum.at(ergebnis, punkt, d)
        return ergebnis - self.toleranz


def punkt_dreieck_abstand(p, dreiecke):
    """Abstand je Paar: Punkte (k, 3) zu Dreiecken (k, 3, 3) – der nächste Punkt auf dem
    Dreieck nach Ericson, Real-Time Collision Detection 5.1.5, als Vektorrechnung."""
    a, b, c = dreiecke[:, 0], dreiecke[:, 1], dreiecke[:, 2]
    ab, ac, ap = b - a, c - a, p - a
    d1 = np.einsum("ij,ij->i", ab, ap)
    d2 = np.einsum("ij,ij->i", ac, ap)
    bp = p - b
    d3 = np.einsum("ij,ij->i", ab, bp)
    d4 = np.einsum("ij,ij->i", ac, bp)
    cp = p - c
    d5 = np.einsum("ij,ij->i", ab, cp)
    d6 = np.einsum("ij,ij->i", ac, cp)
    vc = d1 * d4 - d3 * d2
    vb = d5 * d2 - d1 * d6
    va = d3 * d6 - d5 * d4
    naechster = np.empty_like(p)
    fertig = np.zeros(len(p), dtype=bool)

    def setze(maske, punkt):
        neu = maske & ~fertig
        naechster[neu] = punkt[neu]
        fertig[neu] = True

    setze((d1 <= 0) & (d2 <= 0), a)  # Ecke A
    setze((d3 >= 0) & (d4 <= d3), b)  # Ecke B
    setze((d6 >= 0) & (d5 <= d6), c)  # Ecke C
    with np.errstate(divide="ignore", invalid="ignore"):
        v = d1 / (d1 - d3)
        setze((vc <= 0) & (d1 >= 0) & (d3 <= 0), a + v[:, None] * ab)  # Kante AB
        w = d2 / (d2 - d6)
        setze((vb <= 0) & (d2 >= 0) & (d6 <= 0), a + w[:, None] * ac)  # Kante AC
        w2 = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        setze((va <= 0) & (d4 - d3 >= 0) & (d5 - d6 >= 0), b + w2[:, None] * (c - b))  # BC
        summe = va + vb + vc
        v3 = vb / summe
        w3 = vc / summe
        setze(~fertig, a + v3[:, None] * ab + w3[:, None] * ac)  # innen
    abstand = np.linalg.norm(p - naechster, axis=1)
    # Ein entartetes Dreieck (keine Fläche) ergibt NaN; seine Kanten gehören auch zu Nachbarn.
    return np.where(np.isnan(abstand), np.inf, abstand)


def segment_segment_abstand(p0, p1, q0, q1):
    """Abstand je Paar von Strecken (k, 3) – Ericson 5.1.9, als Vektorrechnung; eine Strecke
    der Länge 0 ist ein Punkt."""
    d1, d2, r = p1 - p0, q1 - q0, p0 - q0
    a = np.einsum("ij,ij->i", d1, d1)
    e = np.einsum("ij,ij->i", d2, d2)
    f = np.einsum("ij,ij->i", d2, r)
    c = np.einsum("ij,ij->i", d1, r)
    b = np.einsum("ij,ij->i", d1, d2)
    winzig = 1e-18
    with np.errstate(divide="ignore", invalid="ignore"):
        nenner = a * e - b * b
        s = np.where(nenner > winzig, np.clip((b * f - c * e) / nenner, 0.0, 1.0), 0.0)
        s = np.where(a <= winzig, 0.0, s)
        t = np.where(e > winzig, (b * s + f) / e, 0.0)
        # t außerhalb [0, 1]: klemmen und s dazu neu
        unter, ueber = t < 0.0, t > 1.0
        t = np.clip(t, 0.0, 1.0)
        s_unter = np.where(a > winzig, np.clip(-c / a, 0.0, 1.0), 0.0)
        s_ueber = np.where(a > winzig, np.clip((b - c) / a, 0.0, 1.0), 0.0)
        s = np.where(unter, s_unter, np.where(ueber, s_ueber, s))
    c1 = p0 + s[:, None] * d1
    c2 = q0 + t[:, None] * d2
    return np.linalg.norm(c1 - c2, axis=1)


def segment_schneidet_dreieck(p0, p1, dreiecke):
    """Je Paar: trifft die Strecke das Dreieck (Möller–Trumbore)? Parallel zur Ebene gilt
    als nein – dann entscheiden die Kanten und Endpunkte."""
    a, b, c = dreiecke[:, 0], dreiecke[:, 1], dreiecke[:, 2]
    richtung = p1 - p0
    e1, e2 = b - a, c - a
    h = np.cross(richtung, e2)
    det = np.einsum("ij,ij->i", e1, h)
    with np.errstate(divide="ignore", invalid="ignore"):
        inv = 1.0 / det
        s = p0 - a
        u = inv * np.einsum("ij,ij->i", s, h)
        q = np.cross(s, e1)
        v = inv * np.einsum("ij,ij->i", richtung, q)
        t = inv * np.einsum("ij,ij->i", e2, q)
    return (np.abs(det) > 1e-14) & (u >= 0) & (v >= 0) & (u + v <= 1) & (t >= 0) & (t <= 1)


def segment_dreieck_abstand(p0, p1, dreiecke):
    """Abstand je Paar: Strecken (k, 3) zu Dreiecken (k, 3, 3) – das Kleinste aus den
    Endpunkten zum Dreieck und der Strecke zu den drei Kanten; 0, wo sie es durchstößt."""
    a, b, c = dreiecke[:, 0], dreiecke[:, 1], dreiecke[:, 2]
    d = np.minimum(punkt_dreieck_abstand(p0, dreiecke), punkt_dreieck_abstand(p1, dreiecke))
    for q0, q1 in ((a, b), (b, c), (c, a)):
        d = np.minimum(d, segment_segment_abstand(p0, p1, q0, q1))
    d[segment_schneidet_dreieck(p0, p1, dreiecke)] = 0.0
    return d
