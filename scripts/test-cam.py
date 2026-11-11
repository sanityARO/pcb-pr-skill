"""Portable two-layer smoke test. Run with a path to the pcb-skill checkout."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile


def trace(a, b):
    def xy(p):
        return f"X{round(p[0]*1e6)}Y{round(p[1]*1e6)}"
    return f"{xy(a)}D02*\n{xy(b)}D01*\n"


def copper(lines):
    return "%FSLAX46Y46*%\n%MOMM*%\n%ADD10C,0.40*%\nD10*\n" + lines + "M02*\n"


def run(folder, case, upstream):
    bottom = trace((2, 2), (3, 2))
    top = trace((1, 2), (2, 2)) + trace((1, 3), (3, 3))
    if case == "short":
        top += trace((1, 2), (1, 3))
    hole = "" if case == "open" else "X2.000Y2.000\n"
    with ZipFile(folder / "board.zip", "w") as z:
        z.writestr("top.GTL", copper(top))
        z.writestr("bottom.GBL", copper(bottom))
        z.writestr("vias.DRL", ";TYPE=PLATED\nM48\nMETRIC,LZ,000.000\nT01C0.20\n%\nT01\n" + hole + "M30\n")
    pads = [("A1","A",1,2,"top.GTL"), ("A2","A",3,2,"bottom.GBL"),
            ("B1","B",1,3,"top.GTL"), ("B2","B",3,3,"top.GTL")]
    manifest = dict(bounds_mm=[0,0,4,4], layers=["top.GTL","bottom.GBL"], plated_through=["vias.DRL"],
                    nets=["A","B"], pads=[dict(id=i,net=n,xy_mm=[x,y],layers=[l]) for i,n,x,y,l in pads])
    (folder / "pads.json").write_text(json.dumps(manifest))
    out = folder / (case + ".json")
    result = subprocess.run([sys.executable, "-B", str(Path(__file__).with_name("cam-check.py")),
                             str(folder/"board.zip"), str(folder/"pads.json"), str(out),
                             "--pcb-skill", upstream, "--resolution", "0.025"], check=False)
    report = json.loads(out.read_text())
    assert result.returncode == (0 if case == "good" else 1)
    assert not report["missing_pad_copper"]
    assert report["components_per_net"]["A"] == (2 if case == "open" else 1)
    assert report["shared_components"] == ([["A","B"]] if case == "short" else [])


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        for mode in ("good","open","short"):
            run(Path(tmp), mode, sys.argv[1])
