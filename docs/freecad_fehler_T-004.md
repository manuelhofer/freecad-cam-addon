# T-004: Fehlerbericht an FreeCAD (zum Einreichen)

**Für Manuel:** Der Text unten ist fertig zum Einreichen. Weg: GitHub →
[FreeCAD/FreeCAD → Issues → New issue](https://github.com/FreeCAD/FreeCAD/issues/new/choose)
→ „Bug report“ → die Abschnitte unten in die gleichnamigen Felder kopieren.
Dauert fünf Minuten. Danach die Nummer des Issues im Snapshot bei T-004
eintragen.

Worum es geht: Speichert CAM eine Maschine und lädt sie wieder, kommt eine
Linearachse verdreht zurück, sobald ihr Gelenk-Ursprung nicht (0,0,0) ist.
Das Addon umgeht das, indem es Linearachsen mit Ursprung 0 übergibt
(`camaddon/export.py`, `_linearachse`); für eine Linearachse zählt nur die
Richtung. Nachgestellt am 2026-09-26 mit dem Wochen-Build 26.3.0 dev vom
2026-09-16 (P-2026-09-26-14); FreeCAD 1.1.3 hat die Maschinenmodelle noch
nicht.

---

**Title:** CAM: `Machine.from_dict()` swaps origin and direction of a linear axis whose joint origin is not (0,0,0)

**Version:** FreeCAD 26.3.0 dev, revision 20260916 (weekly build), Linux.
The code in question is `src/Mod/CAM/Machine/models/machine.py`.

**Problem description**

`Machine.to_dict()` writes every axis joint as `[origin, direction]`:

```python
joint = [axis_obj.joint_origin, [dir_vec.x, dir_vec.y, dir_vec.z]]
```

`Machine.from_dict()` has to guess the order for the array format. For
linear axes it takes the *first* vector as the direction as soon as it is
non-zero:

```python
if axis_type == "linear":
    if vec0.Length > 1e-6:  # joint[0] is direction vector (old structure)
        axis_vector = [vec0.x, vec0.y, vec0.z]
        joint_origin = joint[1] if len(joint[1]) >= 3 else [0, 0, 0]
```

So a linear axis with a non-zero joint origin comes back with its origin as
direction and its direction as origin. Saving a machine configuration and
loading it again turns such an axis. Rotary axes are not affected: there
the second vector is checked first.

**Steps to reproduce** (Python console or FreeCADCmd)

```python
import FreeCAD
from Machine.models.machine import AxisRole, LinearAxis, Machine

machine = Machine(name="Repro")
machine.linear_axes["X"] = LinearAxis(
    name="X",
    direction_vector=FreeCAD.Vector(1, 0, 0),
    min_limit=0,
    max_limit=200,
    max_velocity=10000,
    role=AxisRole("table_linear"),
    joint_origin=[100.0, 25.0, 20.0],
)
data = machine.to_dict()
print("joint written:", data["machine"]["axes"]["X"]["joint"])
axis = Machine.from_dict(data).linear_axes["X"]
print("direction after:", axis.direction_vector)
print("origin after:   ", axis.joint_origin)
```

**Expected behavior**

```
joint written: [[100.0, 25.0, 20.0], [1.0, 0.0, 0.0]]
direction after: Vector (1.0, 0.0, 0.0)
origin after:    [100.0, 25.0, 20.0]
```

**Actual behavior**

```
joint written: [[100.0, 25.0, 20.0], [1.0, 0.0, 0.0]]
direction after: Vector (0.9523809523809523, 0.23809523809523808, 0.19047619047619047)
origin after:    [1.0, 0.0, 0.0]
```

**Possible fix**

Check the second vector first for linear axes too, as for rotary axes – that
is the order `to_dict()` writes – and fall back to the first one only when
the second is zero:

```python
if axis_type == "linear":
    if vec1.Length > 1e-6:  # [origin, direction] as written by to_dict()
        axis_vector = [vec1.x, vec1.y, vec1.z]
        joint_origin = joint[0] if len(joint[0]) >= 3 else [0, 0, 0]
    elif vec0.Length > 1e-6:  # old structure [direction, origin]
        axis_vector = [vec0.x, vec0.y, vec0.z]
        joint_origin = joint[1] if len(joint[1]) >= 3 else [0, 0, 0]
```

Tried on a patched copy of `machine.py`: the example above then loads as
expected, and an old-style joint `[[0, 1, 0], [0, 0, 0]]` still loads with
direction (0, 1, 0). Only an old-style joint with a non-zero origin stays
ambiguous with this check. Writing the joint in the object format
(`{"origin": …, "axis": …}`), which `from_dict()` already understands, would
remove the guessing altogether.
