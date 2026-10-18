# SPDX-License-Identifier: LGPL-2.1-or-later
"""„Plan indexiert“ mit der Stirnseite daneben (Auftrag 2; Manuel, 2026-10-18, an der Nase: „diese
fläche kann man mit der stirn eines schaftfräsers bearbeiten sozusagen und klar gleichzeitig die
stirnseite der welle .. das ist eine kombination“; zum Bild mit Zahlen: „So bauen, mit
Ausspann-Hinweis … wichtig ist das die züge die ap nicht überschreiten … und halt auch die ae
einhalten“).

Eine ebene Fläche längs der Stange (Ebene, an der Nase Face8, sie schaut zur Drehmitte) und an
ihrem hinteren Ende eine Stirnseite quer zur Stange, die nach vorn schaut (Stirn, an der Nase die
Stirnseite der Welle, Face3 – dort geht Drehen nicht, die Nase steht im Weg): In derselben
Stellung der Rundachse fräst der radiale Schaftfräser die Ebene mit seiner Stirn und die
Stirnseite mit seinem Umfang – Züge quer (mit dem Y), die Werkzeugachse auf die Ebene.

- **Lagen längs der Stange**, von dem, was über der Stirnseite steht (die Stange oder nach dem
  Schruppen der Rest), bis auf sie plus Aufmaß – je höchstens ae (Planwerte.zeilenabstand): Der
  Umfang greift so tief wie die Lage ein, die Flanke des Fräsers liegt auf ihrer Unterkante.
- **Bänder längs der Werkzeugachse** je Lage, von oben bis auf die Ebene plus Aufmaß – dort fräst
  die Stirn die Ebene –, und daneben weiter bis an den unteren Rand der Stirnseite (an der Nase
  die Monde neben ihr): je höchstens ap (Planwerte.zustellung).
- **Ein Zug je Band**, quer über die Stirnseite und das Material daneben; wo der Fräser nicht
  hinunter darf (die Hüllfläche des ganzen Teils, vierachs_huelle.je_versatz – neben der Nase),
  teilt er sich. Hinein und hinaus immer neben dem Material, wo es in der Höhe des Bandes und
  darüber frei ist: senkrecht im Eilgang hinab, dann im Freivorschub bis ans Material (Grundsatz
  5). Ein Stück, das an beiden Enden frei ist, fährt im Gleichlauf (oder hin und her, wenn nicht
  „nur Gleichlauf“); eines, das an der Nase endet, beginnt auf der freien Seite.
- Ob der Halter dabei an die Welle kommt, prüft der Assistent wie für jede Bahn
  (vierachs_halter.pruefen) und sagt, wie weit der Fräser heraus muss.

Gerechnet im Rahmen der Ebene: a längs, die Höhe h längs ihrer Normale (zum Werkzeug), quer
q = (längs × Normale) – wie vierachs_planbahn. Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass

import numpy as np

from . import spindel as sp
from . import vierachs_bahn as vb
from . import vierachs_huelle as vh

GLEICH = vb.GLEICH
VORN = math.cos(math.radians(5.0))  # so genau schaut eine Stirnseite längs nach vorn
LIEGT_AN = 0.05  # mm: so nah liegt die Stirnseite am hinteren Ende der Ebene
QUER_SCHRITT = 0.25  # mm: so fein wird quer nachgesehen (Hüllfläche, Material)
HOEHE_SCHRITT = 0.5  # mm: so fein in der Höhe (Material neben dem Zug)
FREI_RAND = 1.0  # mm: so weit neben dem Material beginnt und endet ein Zug (über den Radius hinaus)
KONTAKT = 0.01  # mm: so weit über der Stirnseite (und der Zugabe) prüft die Hüllfläche
MATERIAL = 0.05  # mm: so viel muss stehen, damit es als Material zählt
MINDEST_ZUG = 0.5  # mm: kürzere Stücke fallen weg
BREITER = 1.0  # mm: so weit muss die Stirnseite quer über die Ebene hinausgehen


@dataclass(frozen=True)
class Stirn:
    """Eine Stirnseite quer zur Stange, die nach vorn schaut und hinten an eine Ebene grenzt."""

    name: str  # „Face3“
    a: float  # wo sie liegt, längs
    hq: object  # (n, 2): Höhe und quer ihrer Vernetzung im Rahmen der Ebene


def rahmen_der_ebene(laengs, radial, phi_grad):
    """(l, n, qv) als numpy-Vektoren im Job: längs, die Normale der Ebene (zum Werkzeug) unter
    φ und quer = l × n (wie vierachs_planbahn.ebenen_rechnen)."""
    l_, u_, v_ = vh.rahmen(laengs, radial)
    phi = math.radians(phi_grad)
    n = u_ * math.cos(phi) + v_ * math.sin(phi)
    return l_, n, np.cross(l_, n)


def stirnseiten(form, laengs, radial, ebene, toleranz=0.05):
    """[Stirn] – die ebenen Flächen von `form` (Part.Shape im Job), deren Außennormale längs nach
    vorn zeigt (zum freien Ende der Stange) und die am hinteren Ende von `ebene`
    (vierachs_planbahn.Ebene) an sie grenzen: an der Nase die Stirnseite der Welle neben Face8.
    Nur, wenn die Ebene vorn bis ans Ende des Teils reicht (die Nase ist seine Spitze) und die
    Stirnseite quer über sie hinausgeht – die Wand hinter einer Abflachung ist keine Stirnseite
    der Welle, die Abflachung fährt ihre Zeilen."""
    from . import vierachs_rohteil as vr

    l_, n, qv = rahmen_der_ebene(laengs, radial, ebene.phi)
    vorne = max(float(np.dot([v.X, v.Y, v.Z], l_)) for v in form.Vertexes)
    if ebene.a_bis < vorne - LIEGT_AN:
        return []
    try:
        flaeche_ebene = form.getElement(ebene.name)
    except Exception:  # noqa: BLE001 – die Fläche gibt es nicht (mehr)
        return []
    ergebnis = []
    for i, flaeche in enumerate(form.Faces):
        name = f"Face{i + 1}"
        if name == ebene.name or not vr.ist_eben(flaeche):
            continue
        normale = vr.aussennormale(flaeche)
        if float(np.dot([normale.x, normale.y, normale.z], l_)) < VORN:
            continue
        punkte, _dreiecke = flaeche.copy().tessellate(toleranz)
        if not punkte:
            continue
        p = np.array([[pt.x, pt.y, pt.z] for pt in punkte], dtype=float)
        a = float(np.mean(p @ l_))
        if abs(a - ebene.a_von) > LIEGT_AN:
            continue
        if flaeche.distToShape(flaeche_ebene)[0] > LIEGT_AN:
            continue
        q = p @ qv
        if q.min() > ebene.q_von - BREITER and q.max() < ebene.q_bis + BREITER:
            continue  # nicht breiter als die Ebene: eine Wand, keine Stirnseite der Welle
        ergebnis.append(Stirn(name, a, np.column_stack([p @ n, q])))
    return ergebnis


def _material(w, phi_grad, a_von, a_bis, h, q):
    """Steht zwischen a_von und a_bis an den Stellen (h, q) im Rahmen der Ebene unter φ Material
    – in der Stange, oder nach dem Schruppen im Rest (w.rest: je Strahl das Äußerste; der
    höchste Nachbar zählt)? bool wie h."""
    h = np.asarray(h, dtype=float)
    q = np.asarray(q, dtype=float)
    rho = np.hypot(h, q)
    if a_von > w.a_stange_vorne:
        return np.zeros(np.broadcast(h, q).shape, dtype=bool)
    if w.rest is None:
        return rho <= w.stange_radius + GLEICH
    rest_a, rest_phi, rest_r = w.rest
    schritt_a = float(rest_a[1] - rest_a[0]) if len(rest_a) > 1 else 1.0
    i0 = int(np.searchsorted(rest_a, a_von - schritt_a))
    i1 = int(np.searchsorted(rest_a, a_bis + schritt_a, side="right"))
    if i1 <= i0:
        return np.zeros(np.broadcast(h, q).shape, dtype=bool)
    r = rest_r[i0:i1].max(axis=0)
    r = np.maximum(r, np.maximum(np.roll(r, 1), np.roll(r, -1)))
    schritt_phi = float(rest_phi[1] - rest_phi[0])
    theta = math.radians(phi_grad) + np.arctan2(q, h)
    j = np.rint(np.mod(theta - float(rest_phi[0]), 2 * math.pi) / schritt_phi).astype(np.int64)
    return rho <= r[j % len(r)] + GLEICH


def _oben(w, ebene, stirn, a_unten, form_radius):
    """Bis wohin längs über der Stirnseite noch Material steht – über ihr und vor der Ebene (dort
    fräst die Stirn); a_unten, wenn nichts."""
    hq = stirn.hq
    q_ebene = np.linspace(ebene.q_von, ebene.q_bis, 9)
    h_ebene = np.linspace(ebene.tiefe, ebene.tiefe + form_radius, 5)
    hh, qq = np.meshgrid(h_ebene, q_ebene, indexing="ij")
    h = np.concatenate([hq[:, 0], hh.ravel()])
    q = np.concatenate([hq[:, 1], qq.ravel()])
    oben = a_unten
    a = a_unten + HOEHE_SCHRITT
    while a <= w.a_stange_vorne + HOEHE_SCHRITT:
        if _material(w, ebene.phi, a - HOEHE_SCHRITT, a, h, q).any():
            oben = a
        a += HOEHE_SCHRITT
    return min(oben, w.a_stange_vorne)


def _stufen(oben, unten, schritt):
    """Die Höhen von oben (ausschließlich) bis unten (einschließlich), gleich weit, höchstens
    `schritt` auseinander."""
    if oben <= unten + GLEICH:
        return []
    anzahl = max(1, int(math.ceil((oben - unten) / schritt - 1e-9)))
    return [oben - (k + 1) * (oben - unten) / anzahl for k in range(anzahl)]


def _stuecke(erlaubt):
    """[(von, bis)] – die Läufe von True in `erlaubt` (Indizes, einschließlich)."""
    stuecke = []
    anfang = None
    for i, ja in enumerate(erlaubt.tolist()):
        if ja and anfang is None:
            anfang = i
        elif not ja and anfang is not None:
            stuecke.append((anfang, i - 1))
            anfang = None
    if anfang is not None:
        stuecke.append((anfang, len(erlaubt) - 1))
    return stuecke


@dataclass
class Kombination:
    """Ergebnis von punkte()."""

    punkte: list  # [vierachs_bahn.Punkt]
    lagen: int
    zuege: int
    r_min: float


def punkte(form_teil, laengs, radial, ebene, stirn, w, sicher, toleranz):
    """Die Züge für `ebene` (vierachs_planbahn.Ebene, mit der Stirn) und `stirn` (Stirn) mit den
    Werten `w` (vierachs_planbahn.Planwerte) – Kombination, oder None, wenn nichts zu tun ist.
    Beginnt und endet über der Stange (`sicher`)."""
    form = w.form
    radius = float(form.radius)
    aufmass = max(float(w.aufmass), 0.0)
    l_, n, qv = rahmen_der_ebene(laengs, radial, ebene.phi)
    phi_rad = math.radians(ebene.phi)
    a_unten = stirn.a + aufmass  # die Flanke in der letzten Lage
    oben = _oben(w, ebene, stirn, a_unten, radius)
    lagen = _stufen(oben, a_unten, max(float(w.zeilenabstand), GLEICH))
    if not lagen:
        return None
    netz = vh.vernetze(form_teil, toleranz)
    geformt = form.mit_aufmass(netz.toleranz)
    zugabe = netz.toleranz + vb.RAND
    hq = stirn.hq
    h_ebene = ebene.tiefe + aufmass  # hier fräst die Stirn die Ebene
    h_unten = float(hq[:, 0].min())
    # Quer: über die Stirnseite und das Material daneben (in der Stange höchstens ihr Radius).
    q_weit = float(w.stange_radius) + radius + FREI_RAND + float(w.sicherheit)
    q_werte = np.arange(-q_weit, q_weit + QUER_SCHRITT / 2, QUER_SCHRITT)
    # Die Bänder beginnen oben an der Stirnseite – oder höher, wo über ihr in den Lagen noch
    # Material steht (ohne Schruppen davor die Stange).
    h_alle = np.arange(h_unten, float(w.stange_radius) + HOEHE_SCHRITT, HOEHE_SCHRITT)
    hh, qq = np.meshgrid(h_alle, q_werte, indexing="ij")
    ueber = _material(w, ebene.phi, a_unten, lagen[0] + 2 * radius, hh, qq).any(axis=1)
    h_oben = float(hq[:, 0].max())
    if ueber.any():
        h_oben = max(h_oben, float(h_alle[np.flatnonzero(ueber)[-1]]))
    ap = max(float(w.zustellung), GLEICH)
    baender = _stufen(h_oben, h_ebene, ap) + _stufen(h_ebene, h_unten, ap)
    # Gleichlauf: das Material liegt längs unter der Mitte des Fräsers (zur Stirnseite hin), die
    # Werkzeugachse vom Halter zur Spitze ist −n.
    plus_gleich = sp.ist_gleichlauf(tuple(-n), tuple(qv), tuple(-l_))
    richtung_gleich = 1 if plus_gleich == bool(w.gleichlauf) else -1
    ergebnis = []
    zuege = 0
    r_min = math.inf
    seite = None  # hin und her: auf welcher Seite der letzte Zug endete
    for a_flanke in lagen:
        a_mitte = a_flanke + radius
        # Die Flanke liegt auf der Stirnseite: geprüft wird um die Zugabe darüber – sonst
        # streifte der vergrößerte Fräser die Welle darunter.
        roh = vh.je_versatz(
            netz, laengs, radial, geformt, phi_rad, a_mitte + zugabe + KONTAKT, 1.0, 1, q_werte
        )[0]
        roh_frei = np.where(np.isfinite(roh), roh, -math.inf)
        huelle = roh_frei + zugabe
        # Wo neben dem Material frei ist: in jeder Höhe von unten bis über die Stange.
        h_frei = np.arange(h_unten, sicher + HOEHE_SCHRITT, HOEHE_SCHRITT)
        hh, qq = np.meshgrid(h_frei, q_werte, indexing="ij")
        steht = _material(w, ebene.phi, a_flanke, a_mitte + radius, hh, qq).any(axis=0)
        steht |= huelle > h_unten  # das Teil selbst (die Nase) auch
        if not steht.any():
            continue
        frei_links = float(q_werte[np.flatnonzero(steht)[0]]) - radius - FREI_RAND
        frei_rechts = float(q_werte[np.flatnonzero(steht)[-1]]) + radius + FREI_RAND
        h_vorher = h_oben
        for h in baender:
            # Was der Zug quer abdecken muss: die Stirnseite im Band und das Material im Band.
            im_band = (hq[:, 0] >= h - GLEICH) & (hq[:, 0] <= h_vorher + GLEICH)
            hb, qb = np.meshgrid(np.arange(h, h_vorher + HOEHE_SCHRITT, HOEHE_SCHRITT), q_werte,
                                 indexing="ij")  # fmt: skip
            # Material im Band, das der Fräser von oben erreicht (der Rest zählt das Teil mit –
            # die Nase selbst ist kein Material zum Wegfräsen).
            band = (
                _material(w, ebene.phi, a_flanke, a_mitte + radius, hb, qb)
                & (hb >= roh_frei[None, :] - GLEICH)
            ).any(axis=0)
            h_vorher = h
            # Wo die Mitte des Fräsers hin muss: über das Material im Band und, in der letzten
            # Lage, über die Stirnseite im Band (dort liegt seine Flanke auf ihr).
            letzte = a_flanke <= a_unten + GLEICH
            mitten = []
            if letzte and im_band.any():
                mitten += [float(hq[im_band, 1].min()), float(hq[im_band, 1].max())]
            if band.any():
                mitten += [float(q_werte[np.flatnonzero(band)[0]])]
                mitten += [float(q_werte[np.flatnonzero(band)[-1]])]
            if not mitten:
                continue
            q_von, q_bis = min(mitten) - radius, max(mitten) + radius  # dazwischen schneidet er
            # Anfang und Ende neben beidem, wo es in jeder Höhe frei ist.
            aussen_links = min(q_von - FREI_RAND, frei_links)
            aussen_rechts = max(q_bis + FREI_RAND, frei_rechts)
            # Auf der Höhe der Ebene fräst die Stirn sie fertig: dort zählt die Hüllfläche ohne
            # die Zugabe (ihre Kanten liegen genau so hoch).
            if abs(h - h_ebene) <= GLEICH:
                erlaubt = roh_frei <= h + netz.toleranz + GLEICH
            else:
                erlaubt = huelle <= h + GLEICH
            for i0, i1 in _stuecke(erlaubt):
                s_von, s_bis = float(q_werte[i0]), float(q_werte[i1])
                von, bis = max(s_von, aussen_links), min(s_bis, aussen_rechts)
                if min(bis, q_bis) - max(von, q_von) < MINDEST_ZUG:
                    continue  # schnitte nichts
                links_frei = s_von <= aussen_links + GLEICH
                rechts_frei = s_bis >= aussen_rechts - GLEICH
                if not links_frei and not rechts_frei:
                    continue  # zwischen zwei Sperren: hinein nur durchs Material
                if links_frei and rechts_frei:
                    if w.nur_gleichlauf or seite is None:
                        vorwaerts = richtung_gleich > 0
                    else:
                        vorwaerts = seite == "links"  # dort weiter, wo der letzte endete
                else:
                    vorwaerts = links_frei  # von der freien Seite zur Sperre
                start, ende = (von, bis) if vorwaerts else (bis, von)
                # Bis ans Material im Freivorschub, schneiden, hinter ihm wieder im Freivorschub.
                material_von, material_bis = max(von, q_von), min(bis, q_bis)
                hinein, hinaus = (
                    (material_von, material_bis) if vorwaerts else (material_bis, material_von)
                )
                _hinein(ergebnis, a_mitte, h, start, ebene.phi, sicher, seite, vorwaerts)
                if abs(hinein - start) > GLEICH:
                    ergebnis.append(vb.Punkt(False, a_mitte, h, ebene.phi, q=hinein, frei=True))
                ergebnis.append(vb.Punkt(False, a_mitte, h, ebene.phi, q=hinaus))
                if abs(ende - hinaus) > GLEICH:
                    ergebnis.append(vb.Punkt(False, a_mitte, h, ebene.phi, q=ende, frei=True))
                beide = links_frei and rechts_frei
                seite = ("rechts" if vorwaerts else "links") if beide else None
                if not beide or w.nur_gleichlauf:
                    ergebnis.append(vb.Punkt(True, a_mitte, sicher, ebene.phi, q=ende))
                    seite = None
                zuege += 1
                r_min = min(r_min, h)
        if ergebnis and not ergebnis[-1].eilgang:
            letzter = ergebnis[-1]
            ergebnis.append(vb.Punkt(True, letzter.a, sicher, ebene.phi, q=letzter.q))
            seite = None
    if not zuege:
        return None
    return Kombination(ergebnis, len(lagen), zuege, r_min)


def _hinein(punkte_, a, h, q, phi_grad, sicher, seite, vorwaerts):
    """Zum Anfang eines Zugs (neben dem Material): Endete der letzte auf derselben Seite (hin und
    her), senkrecht im Eilgang hinab – dort ist es frei; sonst über die Stange und hinab."""
    gleiche_seite = seite is not None and (seite == "links") == vorwaerts
    if punkte_ and gleiche_seite and abs(punkte_[-1].a - a) <= GLEICH:
        punkte_.append(vb.Punkt(True, a, punkte_[-1].r, phi_grad, q=q))
        punkte_.append(vb.Punkt(True, a, h, phi_grad, q=q))
        return
    if punkte_ and not punkte_[-1].eilgang:
        letzter = punkte_[-1]
        punkte_.append(vb.Punkt(True, letzter.a, sicher, phi_grad, q=letzter.q))
    punkte_.append(vb.Punkt(True, a, sicher, phi_grad, q=q))
    punkte_.append(vb.Punkt(True, a, h, phi_grad, q=q))
