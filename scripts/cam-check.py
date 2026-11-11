"""Check named pad groups on positive-copper Gerbers with round plated through holes."""
import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--pcb-skill", type=Path, required=True)
    parser.add_argument("--resolution", type=float, required=True, help="grid step in mm")
    args = parser.parse_args()
    if args.output.exists() or args.resolution <= 0:
        parser.error("use a new report path and a positive grid step")
    sys.path.insert(0, str(args.pcb_skill.resolve() / "scripts" / "verify"))
    from scipy.ndimage import label
    from gerber import parse_gerber, parse_excellon
    from raster import Grid

    m = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    layers, points, nets = m["layers"], m["pads"], set(m["nets"])
    if not layers or len(layers) != len(set(layers)) or not points or not nets:
        raise ValueError("empty or duplicated copper layers, missing pads or nets")
    if {p["net"] for p in points} != nets or len({p["id"] for p in points}) != len(points):
        raise ValueError("expected net set or unique pad IDs disagree with manifest")
    bounds = m["bounds_mm"]
    grid = Grid(*bounds, res=args.resolution, margin=args.resolution * 2)
    def pixel(x, y):
        if not (bounds[0] <= x <= bounds[2] and bounds[1] <= y <= bounds[3]):
            raise ValueError("feature outside manifest bounds")
        return grid.row(y), grid.col(x)

    anchors = defaultdict(list)
    for p in points:
        if not p["layers"] or set(p["layers"]) - set(layers):
            raise ValueError("unknown pad layers: " + p["id"])
        for layer in p["layers"]:
            anchors[layer].append((p["id"], pixel(*p["xy_mm"])))

    parent = {}
    def root(k):
        parent.setdefault(k, k)
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    pads = defaultdict(set)
    missing = []
    with ZipFile(args.archive) as z:
        if z.testzip():
            raise ValueError("archive CRC failed")
        holes = []
        for name in m["plated_through"]:
            txt = z.read(name).decode()
            for axis in re.findall(r"[XY](-?[\d.]+)", txt):
                if "." not in axis and int(axis) != 0:
                    raise ValueError("implicit decimal drill coordinates require conversion to explicit mm")
            if re.search(r"^G91\s*$", txt, re.M):
                raise ValueError("incremental drill coordinates require normalization")
            _, hits, plated = parse_excellon(txt, name)
            if not plated or "G85" in txt or "M15" in txt:
                raise ValueError("only explicitly plated round through hits supported: " + name)
            holes.extend(pixel(h.x, h.y) for h in hits)
        for layer in layers:
            txt = z.read(layer).decode()
            if "%LPC" in txt or "%IPNEG" in txt or "%SR" in txt:
                raise ValueError("unsupported polarity or step-and-repeat: " + layer)
            artwork = parse_gerber(txt, layer)
            if len(artwork.regions) != txt.count("G36*"):
                raise ValueError("region count mismatch: " + layer)
            labels, _ = label(grid.rasterise(artwork))
            for i, pos in enumerate(holes):
                component = int(labels[pos])
                if component:
                    parent[root((layer, component))] = root(("hole", i))
            for pad, pos in anchors[layer]:
                component = int(labels[pos])
                if component:
                    pads[pad].add((layer, component))
                else:
                    missing.append((pad, layer))
            del labels
    groups, owners = defaultdict(set), defaultdict(set)
    for p in points:
        net = p["net"]
        for k in pads[p["id"]]:
            group = root(k)
            groups[net].add(group)
            owners[group].add(net)
    counts = {net: len(groups[net]) for net in sorted(nets)}
    shorts = [sorted(v) for v in owners.values() if len(v) > 1]
    passed = not missing and not shorts and all(n == 1 for n in counts.values())
    report = dict(passed=passed, resolution_mm=args.resolution, named_pads=len(points),
                  archive_sha256=hashlib.sha256(args.archive.read_bytes()).hexdigest(),
                  manifest_sha256=hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
                  components_per_net=counts, shared_components=shorts, missing_pad_copper=missing)
    with args.output.open("x", encoding="utf8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"{len(nets)} nets, {len(points)} pads, passed={passed}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
