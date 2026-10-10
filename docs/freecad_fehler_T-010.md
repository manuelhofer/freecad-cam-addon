# T-010: Fehlerbericht an FreeCAD (zum Einreichen)

**Für Manuel:** Der Text unten ist fertig zum Einreichen. Weg: GitHub →
[FreeCAD/FreeCAD → Issues → New issue](https://github.com/FreeCAD/FreeCAD/issues/new/choose)
→ „Bug report“ → die Abschnitte unten in die gleichnamigen Felder kopieren.
Dauert fünf Minuten. Danach die Nummer des Issues im Snapshot bei T-010
eintragen.

Worum es geht: Legt ein Skript in einer eigenen Undo-Transaktion einen CAM-Job
an (`Path.Main.Job.Create`, darin `Path.Tool.Controller.Create`), ist die
Transaktion danach zu – alles, was das Skript anschließend noch anlegt, kennt
das Rückgängig nicht. So blieb bei uns nach Strg+Z der Rohteilklon eines
geschwenkten Ebenenjobs im Baum (B-016). Ursache (eingegrenzt am 2026-10-10 in
FreeCAD 1.1.4, Szenarien K1–K29): Beim Anlegen des Werkzeugs baut CAM den
Werkzeugkörper in einem versteckten Hilfsdokument (`ToolBitShape.make_body` →
`ShapeDocFromBytes`), ändert dort Eigenschaften und schließt es wieder. Das
Hilfsdokument tritt mit der ersten Änderung der laufenden Transaktion bei
(FreeCADs dokumentübergreifende Transaktionen); beim Schließen muss FreeCAD die
Transaktion beenden – für alle beteiligten Dokumente. Mit `UndoMode = 0` am
Hilfsdokument passiert das nicht. Das Addon räumt verwaiste Klone nach dem
Rückgängig selbst auf (`camaddon/aufraeumen.py`, P-2026-10-10-21).

---

**Title:** CAM: creating a tool bit inside an open transaction silently closes that transaction (temporary shape document joins and ends it)

**Version:** FreeCAD 1.1.4 (release, Linux, package build 45040). The code in
question is `src/Mod/CAM/Path/Tool/shape/models/base.py` (`make_body`,
`ShapeDocFromBytes`) and `src/Mod/CAM/Path/Tool/toolbit/models/base.py`
(`attach_to_obj` → `_update_visual_representation`). Still present in the
current `main` sources (checked 2026-10-10).

**Problem description**

A script (or an addon) that opens its own undo transaction, creates a CAM job
and then continues to add objects, ends up with objects that undo does not
remove:

```python
import FreeCAD, Part
import Path.Main.Job as PathJob

doc = FreeCAD.newDocument("Repro")
part = doc.addObject("Part::Feature", "Part")
part.Shape = Part.makeBox(60, 40, 20)
doc.recompute()

doc.openTransaction("Create job and helper")
job = PathJob.Create("Job", [part])          # contains Path.Tool.Controller.Create(...)
helper = doc.addObject("Part::Feature", "Helper")
doc.commitTransaction()

doc.undo()
print([o.Name for o in doc.Objects])         # ['Part', 'Helper']  <- Helper survives
```

Expected: after `undo()` only `Part` is left. Actual (GUI session, `UndoMode`
1): the job is gone, but `Helper` stays – it was created after the transaction
had already been closed.

**Root cause (bisected)**

`Path.Tool.Controller.Create` → `ToolBit.attach_to_doc` →
`_update_visual_representation` → `ToolBitShape.make_body(doc)`. `make_body`
opens the shape file in a hidden temporary document (`ShapeDocFromBytes`),
changes property values there (`update_shape_object_properties`), recomputes it,
copies the body into the target document and closes the temporary document.

FreeCAD transactions span documents: the first change in the temporary
document makes it join the transaction that is open in the target document
(`Document::_checkTransaction` → `Application::getActiveTransaction`). Closing a
document that holds part of the active transaction ends the transaction for all
documents. Everything the caller does afterwards is outside any transaction.

Minimal reproduction without CAM (GUI session):

```python
import FreeCAD, Part
doc = FreeCAD.newDocument("Repro"); doc.UndoMode = 1
doc.openTransaction("T")
a = doc.addObject("Part::Feature", "A"); a.Shape = Part.makeBox(1, 1, 1)
tmp = FreeCAD.newDocument("Tmp", hidden=True)
tmp.addObject("Part::Feature", "X").Shape = Part.makeBox(1, 1, 1)   # Tmp joins "T"
FreeCAD.closeDocument(tmp.Name)                                    # ends "T" everywhere
b = doc.addObject("Part::Feature", "B"); b.Shape = Part.makeBox(2, 2, 2)
doc.commitTransaction()
doc.undo()
print([o.Name for o in doc.Objects])   # ['B'] – B is not undone
```

Variants tried in the same session (all with the same transaction pattern):

| inside the transaction | undo removes everything? |
| --- | --- |
| create and close an *unchanged* hidden document | yes |
| open an `.FCStd` hidden and close it | yes |
| change a hidden document and leave it open | yes (it shows the caller's transaction name in its `UndoNames`) |
| change a hidden document and close it | **no** |
| same, but `tmp.UndoMode = 0` before the change | yes |
| `doc.copyObject(obj_of_other_doc, True)` | yes |
| `ToolBitShape.make_body(doc)` | **no** |
| `Path.Tool.Controller.Create(...)` | **no** |
| `Path.Tool.Controller.Create(..., assignTool=False)` | yes |

Headless (`FreeCADCmd`) the problem does not show, because there the temporary
document does not join the GUI-driven active transaction.

**Suggested fix**

In `ShapeDocFromBytes` (or right after creating the temporary document in
`make_body`) set `tmp_doc.UndoMode = 0` before changing anything in it, so the
temporary document never joins the caller's transaction. Alternatively build the
body without a temporary document. Either way, `Path.Tool.Controller.Create`
and `Path.Main.Job.Create` should leave the caller's transaction open.

**Steps to reproduce**

1. Start FreeCAD (GUI), open the Python console.
2. Paste the first snippet above.
3. Observe `['Part', 'Helper']` – the helper object was not undone, and Edit →
   Undo shows nothing left to undo.

**Workaround**

Create the job (or any tool controller) in a transaction of its own, then open
a new transaction for everything that follows – or clean up afterwards, which is
what we do in our addon.
