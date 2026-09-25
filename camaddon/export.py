# SPDX-License-Identifier: LGPL-2.1-or-later
"""Export in die CAM-Maschinendefinition von FreeCAD (Spezifikation W-001, Stufe 2).

Aus dem Maschinenobjekt wird ein `Machine` aus `Mod/CAM/Machine` gebaut und
als `.fcm` dort gespeichert, wo CAM seine Maschinen sucht – danach steht die
Maschine in CAM zur Auswahl.

Was die CAM-Definition nicht kennt (Beschleunigung, Ruck, größter Vorschub,
Revolver), bleibt im Dokument; der Bericht sagt das in Worten.

Läuft ohne Oberfläche.
"""

from dataclasses import dataclass, field

import FreeCAD

from . import kette as kette_modul
from . import maschine as m
from .kette import LINEAR
from .sprache import tr

# Ohne Begrenzung am Gelenk: so weit, dass CAM nie daran stößt.
OHNE_GRENZE_MM = 100000.0
OHNE_GRENZE_GRAD = 360.0


@dataclass
class Bericht:
    uebertragen: list = field(default_factory=list)  # Sätze: was in CAM angekommen ist
    nicht_uebertragen: list = field(default_factory=list)  # Sätze: was nur im Dokument bleibt
    datei: object = None


def _achs_betriebsart(maschine, gelenk_objekt):
    """Die Betriebsart eines Gelenks, die in CAM eine Achse ist (Linear/Positionieren)."""
    for ba in m.betriebsarten(maschine):
        if ba.Gelenk == gelenk_objekt and ba.Art in (m.ART_LINEAR, m.ART_POSITIONIEREN):
            return ba
    return None


def baue_cam_maschine(maschine, kette=None):
    """Baut die CAM-Maschine. Gibt (Machine, Bericht) zurück, speichert nichts."""
    from Machine.models.machine import (
        AxisRole,
        LinearAxis,
        Machine,
        RotaryAxis,
        Toolhead,
        WrapStrategy,
    )

    assembly = m.assembly_von(maschine)
    if kette is None:
        kette = kette_modul.lies_kette(assembly)
    rollen, _meldungen = m.rollen(kette, maschine)
    bericht = Bericht()

    cam = Machine(name=maschine.Label)
    cam.description = tr("export.beschreibung", dokument=maschine.Document.Label)
    cam.linear_axes = {}
    cam.rotary_axes = {}
    cam.toolheads = []

    eltern_von = {g.kind: g for g in kette.gelenke}

    def eltern_achse(gelenk):
        """NC-Name der nächsten Achse zum Bett hin (für die kinematische Kette)."""
        vorher = eltern_von.get(gelenk.eltern)
        while vorher is not None:
            ba = _achs_betriebsart(maschine, vorher.objekt)
            if ba is not None:
                return m.name_von(ba)
            vorher = eltern_von.get(vorher.eltern)
        return None

    for tiefe, gelenk in enumerate(kette.gelenke):
        ba = _achs_betriebsart(maschine, gelenk.objekt)
        if ba is None:
            continue
        name = m.name_von(ba)
        rolle = rollen.get(gelenk.objekt)
        if rolle is None:
            bericht.nicht_uebertragen.append(tr("export.rolle_unbekannt", name=name))
        ursprung = [gelenk.ursprung.x, gelenk.ursprung.y, gelenk.ursprung.z]
        if gelenk.art == LINEAR:
            # Fehler in FreeCAD (26.3 dev, Machine.from_dict): Ist der Ursprung
            # einer Linearachse nicht (0,0,0), liest FreeCAD ihn beim Laden als
            # Richtung – die Achse käme verdreht zurück. Für eine Linearachse
            # zählt nur die Richtung, also Ursprung 0 (P-2026-09-25-20).
            ursprung = [0.0, 0.0, 0.0]
            achse = LinearAxis(
                name,
                FreeCAD.Vector(gelenk.richtung),
                gelenk.minimum if gelenk.minimum is not None else -OHNE_GRENZE_MM,
                gelenk.maximum if gelenk.maximum is not None else OHNE_GRENZE_MM,
                ba.Eilgang or 10000,
                tiefe,
                AxisRole.HEAD_LINEAR if rolle == m.KOPF else AxisRole.TABLE_LINEAR,
                eltern_achse(gelenk),
                ursprung,
            )
            cam.linear_axes[name] = achse
            bericht.uebertragen.append(
                tr("export.linear", name=name, eilgang=_zahl(achse.max_velocity))
            )
        else:
            endlos = bool(ba.Endlos)
            achse = RotaryAxis(
                name,
                FreeCAD.Vector(gelenk.richtung),
                gelenk.minimum if gelenk.minimum is not None else -OHNE_GRENZE_GRAD,
                gelenk.maximum if gelenk.maximum is not None else OHNE_GRENZE_GRAD,
                # CAM rechnet in °/min, eingegeben wird U/min.
                (ba.Geschwindigkeit or 100) * 360.0,
                tiefe,
                role=AxisRole.HEAD_ROTARY if rolle == m.KOPF else AxisRole.TABLE_ROTARY,
                parent=eltern_achse(gelenk),
                joint_origin=ursprung,
                wrap_strategy=WrapStrategy.MODULO if endlos else WrapStrategy.UNWOUND,
            )
            cam.rotary_axes[name] = achse
            bericht.uebertragen.append(
                tr("export.dreh", name=name, geschwindigkeit=_zahl(achse.max_velocity))
            )
        if gelenk.minimum is None and gelenk.maximum is None and not (
            gelenk.art != LINEAR and ba.Endlos
        ):
            bericht.nicht_uebertragen.append(tr("export.ohne_grenzen", name=name))
        for eigenschaft in ("VorschubMax", "Beschleunigung", "Ruck"):
            if eigenschaft in ba.PropertiesList and getattr(ba, eigenschaft):
                bericht.nicht_uebertragen.append(
                    tr("export.wert_bleibt", name=name, wert=m.wert_text(eigenschaft))
                )

    for ba in m.betriebsarten(maschine):
        name = m.name_von(ba)
        if ba.Art == m.ART_SPINDEL:
            cam.toolheads.append(Toolhead(name, id=name, max_rpm=ba.Drehzahl))
            bericht.uebertragen.append(tr("export.spindel", name=name, drehzahl=_zahl(ba.Drehzahl)))
        elif ba.Art == m.ART_REVOLVER:
            anzahl = len(m.plaetze(maschine, kette, ba))
            bericht.nicht_uebertragen.append(tr("export.revolver", name=name, anzahl=anzahl))

    for fehler in cam.validate_kinematic_chain():
        bericht.nicht_uebertragen.append(tr("export.kette_fehler", fehler=fehler))
    return cam, bericht


def dateiname(maschine):
    """Dateiname der .fcm – aus dem Namen der Maschine, ohne Sonderzeichen."""
    erlaubt = [z if z.isalnum() or z in "-_" else "_" for z in maschine.Label.strip()]
    return ("".join(erlaubt) or "Maschine") + ".fcm"


def exportiere(maschine, kette=None):
    """Baut die CAM-Maschine und speichert sie in CAMs Maschinenordner.

    Dieselbe Maschine wird beim nächsten Export überschrieben (gleicher Name).
    """
    from Machine.models.machine import MachineFactory

    cam, bericht = baue_cam_maschine(maschine, kette)
    bericht.datei = MachineFactory.save_configuration(cam, dateiname(maschine))
    return bericht


def _zahl(wert):
    return f"{wert:g}"
