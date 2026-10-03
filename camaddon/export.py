# SPDX-License-Identifier: LGPL-2.1-or-later
"""Übergabe an die CAM-Maschinendefinition von FreeCAD (W-001, Stufe 2).

Aus dem Maschinenobjekt wird eine `Machine` aus `Mod/CAM/Machine` gebaut und
als `.fcm`-Datei dort gespeichert, wo CAM seine Maschinen sucht. Danach steht
die Maschine in CAM zur Auswahl. Übertragen wird je Betriebsart:

    Linear          -> LinearAxis
    Positionieren   -> RotaryAxis
    Spindel         -> Toolhead
    Revolver        -> nichts, die CAM-Definition kennt keinen Revolver

Was die CAM-Definition nicht kennt – Beschleunigung, Ruck, größter Vorschub,
Revolver –, bleibt im Dokument. Der Bericht sagt dem Benutzer in Worten, was
übertragen wurde und was nicht.

Eine schräge Achse (W-001, Abschnitt 7c) kennt die CAM-Definition auch nicht.
Die Bahnen sind ohnehin rechtwinklig, umrechnen tut die Steuerung. Deshalb
bekommt CAM statt der schrägen Richtung die rechtwinklige des Programms, mit
umgerechneten Grenzen und Eilgang; der Bericht sagt, dass diese Grenzen nur
gelten, solange die ausgleichende Achse Platz hat.

Die CAM-Maschinendefinition gibt es erst im Wochen-Build, nicht in
FreeCAD 1.1 – deshalb `verfuegbar()` und die Importe erst in den Funktionen.

Läuft ohne Oberfläche.
"""

import math
from dataclasses import dataclass, field

import FreeCAD

from . import einheiten, schraege_achse
from . import kette as kette_modul
from . import maschine as m
from .kette import LINEAR
from .sprache import tr

# Ohne Begrenzung am Gelenk: ein Bereich so groß, dass CAM nie daran stößt.
OHNE_GRENZE_MM = 100000.0
OHNE_GRENZE_GRAD = 360.0

# Fehlt ein Pflichtwert, gilt FreeCADs eigene Vorgabe. Der Dialog hat vor der
# Übergabe schon gewarnt.
VORGABE_EILGANG = 10000.0  # mm/min
VORGABE_DREHGESCHWINDIGKEIT = 100.0  # U/min (in FreeCAD: 36000 °/min)
# Für die Zeit (fahrzeit): festgesetzt wie eine kleine oder nachgerüstete Maschine (Manuel,
# 2026-10-01); die Maschine selbst darf mehr sagen („Maschine bearbeiten“, Beschleunigung).
VORGABE_BESCHLEUNIGUNG = 1.0  # m/s² je Linearachse
VORGABE_DREHBESCHLEUNIGUNG = 1.0  # U/s² je Rundachse

# Kennwerte, die die CAM-Definition nicht kennt.
NICHT_IN_CAM = ("VorschubMax", "Beschleunigung", "Ruck")


@dataclass
class Bericht:
    """Was die Übergabe getan hat, in fertigen Sätzen für den Benutzer."""

    uebertragen: list = field(default_factory=list)  # in CAM angekommen
    zu_pruefen: list = field(default_factory=list)  # angekommen, aber mit Ersatzwerten
    nicht_uebertragen: list = field(default_factory=list)  # bleibt nur im Dokument
    datei: object = None  # Pfad der gespeicherten .fcm-Datei


def verfuegbar():
    """Hat diese FreeCAD-Version die CAM-Maschinendefinition? FreeCAD 1.1 hat sie nicht."""
    try:
        import Machine.models.machine  # noqa: F401
    except ImportError:
        return False
    return True


def baue_cam_maschine(maschine, kette=None):
    """Baut die CAM-Maschine. Gibt (Machine, Bericht) zurück; gespeichert wird nichts."""
    from Machine.models.machine import Machine, Toolhead

    if kette is None:
        kette = kette_modul.lies_kette(m.assembly_von(maschine))
    rollen, _meldungen = m.rollen(kette, maschine)  # die Meldungen zeigt schon der Dialog
    schraeg = schraege_achse.gueltige(maschine, kette)  # Gelenk -> (Eintrag, α, ausgleichend)
    bericht = Bericht()

    cam = Machine(name=maschine.Label)
    cam.description = tr("export.beschreibung", dokument=maschine.Document.Label)
    cam.linear_axes = {}
    cam.rotary_axes = {}
    cam.toolheads = []

    # Die Achsen der Kette stehen vom Bett nach außen; das wird ihre
    # Reihenfolge in CAM.
    spindeln = m.spindeln(maschine)
    for reihenfolge, achse in enumerate(kette.achsen):
        ba = _achs_betriebsart(maschine, achse.gelenk)
        if ba is None:
            continue  # z. B. eine reine Spindel: in CAM keine Achse
        if spindeln.ist_antrieb_c(ba):
            # Die C-Achse eines Werkzeugantriebs richtet das Werkzeug aus – keine Achse der Bahn.
            bericht.nicht_uebertragen.append(tr("export.antrieb_c", name=m.name_von(ba)))
            continue
        name = m.name_von(ba)
        if achse.gelenk not in rollen:
            bericht.zu_pruefen.append(tr("export.rolle_unbekannt", name=name))
        im_kopf = rollen.get(achse.gelenk) == m.KOPF
        gemeinsam = {  # Felder, die beide Achsarten gleich haben
            "name": name,
            "sequence": reihenfolge,
            "parent": _eltern_name(maschine, kette, achse),
        }
        if achse.art == LINEAR and achse.gelenk in schraeg:
            eilgang = _schraege_achse(cam, bericht, maschine, kette, achse, ba, im_kopf, gemeinsam)
            if not ba.Eilgang:
                gezeigt = _zahl(einheiten.gerundet(VORGABE_EILGANG, einheiten.VORSCHUB))
                bericht.zu_pruefen.append(tr("export.eilgang_vorgabe", name=name, eilgang=gezeigt))
        elif achse.art == LINEAR:
            eilgang = ba.Eilgang or VORGABE_EILGANG
            cam.linear_axes[name] = _linearachse(achse, eilgang, im_kopf, **gemeinsam)
            # Im Bericht in mm/min oder ipm; an CAM geht er in mm/min.
            gezeigt = _zahl(einheiten.gerundet(eilgang, einheiten.VORSCHUB))
            bericht.uebertragen.append(tr("export.linear", name=name, eilgang=gezeigt))
            if not ba.Eilgang:
                bericht.zu_pruefen.append(tr("export.eilgang_vorgabe", name=name, eilgang=gezeigt))
        else:
            u_min = ba.Geschwindigkeit or VORGABE_DREHGESCHWINDIGKEIT
            cam.rotary_axes[name] = _drehachse(achse, u_min, ba.Endlos, im_kopf, **gemeinsam)
            bericht.uebertragen.append(tr("export.dreh", name=name, geschwindigkeit=_zahl(u_min)))
            if not ba.Geschwindigkeit:
                bericht.zu_pruefen.append(
                    tr("export.geschwindigkeit_vorgabe", name=name, geschwindigkeit=_zahl(u_min))
                )

        endlos = achse.art != LINEAR and ba.Endlos  # braucht keine Begrenzung
        if not endlos and (achse.minimum is None or achse.maximum is None):
            bericht.zu_pruefen.append(_satz_fehlende_grenzen(name, achse))
        for eigenschaft in NICHT_IN_CAM:
            if getattr(ba, eigenschaft):
                bericht.nicht_uebertragen.append(
                    tr("export.wert_bleibt", name=name, wert=m.wert_text(eigenschaft))
                )

    for ba in m.betriebsarten(maschine):
        name = m.name_von(ba)
        if ba.Art == m.ART_SPINDEL:
            cam.toolheads.append(Toolhead(name=name, id=name, max_rpm=ba.Drehzahl))
            if ba.Drehzahl:
                satz = tr("export.spindel", name=name, drehzahl=_zahl(ba.Drehzahl))
                bericht.uebertragen.append(satz)
            else:
                # Drehzahl 0 heißt für CAM „keine Grenze“ – so rechnet sein
                # Schnittdaten-Rechner (Path/Tool/FeedsSpeeds/resolver.py).
                bericht.uebertragen.append(tr("export.spindel_ohne_drehzahl", name=name))
                bericht.zu_pruefen.append(tr("export.drehzahl_fehlt", name=name))
        elif ba.Art == m.ART_REVOLVER:
            anzahl = len(m.plaetze(maschine, kette, ba))
            bericht.nicht_uebertragen.append(tr("export.revolver", name=name, anzahl=anzahl))

    for fehler in cam.validate_kinematic_chain():
        bericht.zu_pruefen.append(tr("export.kette_fehler", fehler=fehler))
    return cam, bericht


def dateiname(maschine):
    """Dateiname der .fcm-Datei: der Name der Maschine, Sonderzeichen durch „_“ ersetzt."""
    erlaubt = [z if z.isalnum() or z in "-_" else "_" for z in maschine.Label.strip()]
    return ("".join(erlaubt) or "Maschine") + ".fcm"


def exportiere(maschine, kette=None):
    """Baut die CAM-Maschine und speichert sie in CAMs Maschinenordner.

    Eine erneute Übergabe derselben Maschine überschreibt die Datei.
    """
    from Machine.models.machine import MachineFactory

    cam, bericht = baue_cam_maschine(maschine, kette)
    bericht.datei = MachineFactory.save_configuration(cam, dateiname(maschine))
    return bericht


def _achs_betriebsart(maschine, gelenk):
    """Die Betriebsart eines Gelenks, die in CAM eine Achse ist (Linear oder Positionieren).

    An einer Hauptspindel mit S4 und C4 ist das C4; S4 wird ein Toolhead.
    """
    return next(
        (
            ba
            for ba in m.betriebsarten(maschine)
            if ba.Gelenk == gelenk and ba.Art in (m.ART_LINEAR, m.ART_POSITIONIEREN)
        ),
        None,
    )


def _eltern_name(maschine, kette, achse):
    """NC-Name der nächsten Achse zum Bett hin, die in CAM eine Achse ist – oder None.

    Daraus baut CAM seine kinematische Kette. Gelenke ohne CAM-Achse (etwa
    eine reine Spindel) werden übersprungen.
    """
    for vorgaenger in kette.pfad_zum_bett(achse.eltern):
        ba = _achs_betriebsart(maschine, vorgaenger.gelenk)
        if ba is not None:
            return m.name_von(ba)
    return None


def _satz_fehlende_grenzen(name, achse):
    """Hinweis, dass am Gelenk eine oder beide Begrenzungen fehlen.

    Für eine fehlende Seite bekommt CAM OHNE_GRENZE_MM bzw. OHNE_GRENZE_GRAD.
    """
    if achse.minimum is None and achse.maximum is None:
        return tr("export.ohne_grenzen", name=name)
    return tr("export.eine_grenze", name=name)


def _schraege_achse(cam, bericht, maschine, kette, achse, ba, im_kopf, gemeinsam):
    """Die schräge Achse als rechtwinklige Achse des Programms; gibt den Eilgang zurück.

    Richtung rechtwinklig zur ausgleichenden Achse, Grenzen · cos α, Eilgang
    so hoch, wie beide Schlitten zusammen schaffen (schraege_achse.hoechstwert).
    """
    trafo, alpha, ausgleich = schraege_achse.gueltige(maschine, kette)[achse.gelenk]
    ba_ausgleich = trafo.Ausgleich
    faktor = math.cos(math.radians(alpha))
    eilgang = schraege_achse.hoechstwert(
        alpha, ba.Eilgang or VORGABE_EILGANG, ba_ausgleich.Eilgang or VORGABE_EILGANG
    )
    minimum = None if achse.minimum is None else achse.minimum * faktor
    maximum = None if achse.maximum is None else achse.maximum * faktor
    name = gemeinsam["name"]
    cam.linear_axes[name] = _linearachse(
        achse,
        eilgang,
        im_kopf,
        richtung=schraege_achse.programmrichtung(kette, trafo),
        grenzen=(minimum, maximum),
        **gemeinsam,
    )
    bericht.uebertragen.append(
        tr(
            "export.linear",
            name=name,
            eilgang=_zahl(einheiten.gerundet(eilgang, einheiten.VORSCHUB)),
        )
    )
    bericht.zu_pruefen.append(
        tr(
            "export.schraege_achse",
            name=name,
            ausgleich=m.name_von(ba_ausgleich),
            winkel=schraege_achse.winkel_text(alpha),
            programm=trafo.NameSchraeg,
        )
    )
    return eilgang


def _linearachse(achse, eilgang, im_kopf, richtung=None, grenzen=None, **gemeinsam):
    """Die Linearachse für CAM. `richtung` und `grenzen` (min, max) ersetzen die des
    Gelenks – bei einer schrägen Achse die des Programms."""
    from Machine.models.machine import AxisRole, LinearAxis

    minimum, maximum = grenzen if grenzen is not None else (achse.minimum, achse.maximum)
    return LinearAxis(
        direction_vector=FreeCAD.Vector(richtung if richtung is not None else achse.richtung),
        min_limit=_oder(minimum, -OHNE_GRENZE_MM),
        max_limit=_oder(maximum, OHNE_GRENZE_MM),
        max_velocity=eilgang,
        role=AxisRole.HEAD_LINEAR if im_kopf else AxisRole.TABLE_LINEAR,
        # Fehler in FreeCAD (26.3 dev, Machine.from_dict): Ist der Ursprung
        # einer Linearachse nicht (0,0,0), liest FreeCAD ihn beim Laden als
        # Richtung – die Achse käme verdreht zurück. Für eine Linearachse
        # zählt nur die Richtung, also bleibt der Ursprung 0 (T-004).
        joint_origin=[0.0, 0.0, 0.0],
        **gemeinsam,
    )


def _drehachse(achse, u_min, endlos, im_kopf, **gemeinsam):
    from Machine.models.machine import AxisRole, RotaryAxis, WrapStrategy

    return RotaryAxis(
        rotation_vector=FreeCAD.Vector(achse.richtung),
        min_limit=_oder(achse.minimum, -OHNE_GRENZE_GRAD),
        max_limit=_oder(achse.maximum, OHNE_GRENZE_GRAD),
        max_velocity=u_min * 360.0,  # CAM rechnet in Grad je Minute
        role=AxisRole.HEAD_ROTARY if im_kopf else AxisRole.TABLE_ROTARY,
        joint_origin=[achse.ursprung.x, achse.ursprung.y, achse.ursprung.z],
        # Endlos: CAM gibt Winkel zwischen 0 und 360° aus (MODULO).
        # Sonst gibt es den Winkel ohne Umrechnung aus (UNWOUND).
        wrap_strategy=WrapStrategy.MODULO if endlos else WrapStrategy.UNWOUND,
        **gemeinsam,
    )


def _oder(wert, ersatz):
    """`wert`, oder `ersatz`, wenn er fehlt (None). Anders als `or` bleibt 0 erhalten."""
    return ersatz if wert is None else wert


def _zahl(wert):
    """Zahl für einen Satz: 10000.0 -> „10000“, 2.5 -> „2.5“."""
    return f"{wert:g}"
