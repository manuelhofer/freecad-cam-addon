# Die Version steht nur in package.xml; das Addon liest sie von dort. Prüft,
# dass das klappt und die Angabe die Form hat, die der Addon-Manager braucht.
import os
import re
import sys

ADDON = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ADDON)

import camaddon  # noqa: E402

inhalt = open(os.path.join(ADDON, "package.xml"), encoding="utf-8").read()
version = re.search(r"<version>([^<]+)</version>", inhalt).group(1)
datum = re.search(r"<date>([^<]+)</date>", inhalt).group(1)

fehler = []
if camaddon.VERSION != version:
    fehler.append(f"Addon meldet {camaddon.VERSION}, package.xml sagt {version}")
if not re.fullmatch(r"\d+\.\d+\.\d+", version):
    fehler.append(f"Version {version!r} hat nicht die Form 1.2.3")
if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", datum):
    fehler.append(f"Datum {datum!r} hat nicht die Form JJJJ-MM-TT")
if re.search(r'VERSION\s*=\s*["\']', open(os.path.join(ADDON, "camaddon", "__init__.py"), encoding="utf-8").read()):
    fehler.append("Version steht wieder fest im Code statt aus package.xml")

assert not fehler, "\n".join(fehler)
print("OK", os.path.basename(__file__))
