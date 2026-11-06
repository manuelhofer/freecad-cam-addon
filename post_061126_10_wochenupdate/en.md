# Weekly update: news on GitHub, FreeCAD CAM terms, holder data (0.345.8)

*2026-11-06*

Current version 0.345.8 (“Check for updates” offers it). A quiet week at the machines, so a short update.

## News now on GitHub
The weekly updates are posted here under **Announcements** from now on, and older ones are in the [archive](https://github.com/manuelhofer/freecad-cam-addon/tree/forum#readme). Questions and ideas are welcome in [Q&A](https://github.com/manuelhofer/freecad-cam-addon/discussions/categories/q-a) and [Ideas](https://github.com/manuelhofer/freecad-cam-addon/discussions/categories/ideas); bugs please as an [issue](https://github.com/manuelhofer/freecad-cam-addon/issues).

## Same words as FreeCAD CAM
The English texts now use the terms of FreeCAD CAM's glossary: **stock to leave** for what an operation leaves on the part (axial on the floor, radial on the walls) instead of “allowance”, **stock** instead of “blank”, **post-processor**, **horizontal/vertical feed**. German is unchanged.

## Holder data corrected
Kennametal ER collet chucks (71 sizes): the catalogue's L9 is the clamping depth up to the adjustment range, not the length of the collet nut. Now L9 is the clamping depth (setup sheet, minimum insertion) and the nut has its DIN 6499 length. For the four long ER16 holders the wider body now starts 14 mm closer to the tool, as on the real holder – before, the collision check saw a slimmer holder there. Hoffmann drills: 16 309 sizes (+75).

## FreeCAD weekly build 2026.11.04
Tested against FreeCAD 27.1 dev (weekly 2026.11.04): all 142 test files pass. The 181 GUI scenarios (FreeCAD started invisibly, every window clicked through) pass as well.

## Watching upstream
FreeCAD CAM is working on tool holders on the tool bit (FreeCAD PR 33379) and on a simulator with rotary axes and tilted work planes (FreeCAD issue 29758), and there will be work on tool orientation. As soon as these are in FreeCAD, the add-on will use them instead of its own versions – the holders from the catalogues as FreeCAD tool holders, checks through FreeCAD's simulator.
