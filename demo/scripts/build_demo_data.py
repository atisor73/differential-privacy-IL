from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PUBLIC_DATA_DIR = ROOT / "demo" / "public" / "data"
MAPSHAPER_DIR = ROOT / "data" / "tabblock2010_17_pophu" / "mapshaper"
DEFAULT_DP_ROOT = ROOT / "data" / "processed_data" / "DP_noise"

COUNTIES_TOPOJSON = MAPSHAPER_DIR / "counties.topojson"
TRACTS_TOPOJSON = MAPSHAPER_DIR / "tracts.topojson"
BLOCKS_GEOJSON = MAPSHAPER_DIR / "blocks.geojson"

RACE_COLS = ["white", "black", "asian", "other"]
BLOCK_SAMPLE_RATE = 0.0265
BLOCK_SAMPLE_FLOOR = 24
BLOCK_SAMPLE_SEED = 20260512
ROUND_DIGITS = 5
DEFAULT_FOCUS_COUNTY = "17031"


def parse_args():
    parser = argparse.ArgumentParser(description="Build the Svelte demo bundle from precomputed DP outputs.")
    parser.add_argument(
        "--dp-root",
        type=Path,
        default=DEFAULT_DP_ROOT,
        help="Directory containing epsilon_<value>/ release folders.",
    )
    parser.add_argument(
        "--default-epsilon",
        type=str,
        default="0.5",
        help="Default epsilon label to select in the demo if present.",
    )
    return parser.parse_args()


def epsilon_sort_key(label: str):
    try:
        return (0, float(label))
    except ValueError:
        return (1, label)


def discover_epsilons(dp_root: Path):
    epsilons = []
    for path in sorted(dp_root.glob("epsilon_*")):
        if path.is_dir():
            epsilons.append(path.name.removeprefix("epsilon_"))
    if not epsilons:
        raise ValueError(f"No epsilon_* directories found under {dp_root}")
    return sorted(epsilons, key=epsilon_sort_key)


def round_nested(value, digits=ROUND_DIGITS):
    if isinstance(value, list):
        return [round_nested(item, digits) for item in value]
    if isinstance(value, float):
        return round(value, digits)
    return value


def geometry_bbox(geometry):
    bounds = [math.inf, math.inf, -math.inf, -math.inf]

    def walk(node):
        if not node:
            return
        if isinstance(node[0], (int, float)):
            x, y = node[:2]
            bounds[0] = min(bounds[0], x)
            bounds[1] = min(bounds[1], y)
            bounds[2] = max(bounds[2], x)
            bounds[3] = max(bounds[3], y)
            return
        for child in node:
            walk(child)

    walk(geometry["coordinates"])
    return bounds


def bbox_center(bounds):
    min_x, min_y, max_x, max_y = bounds
    return ((min_x + max_x) / 2, (min_y + max_y) / 2)


def make_county_geoid(props):
    return f"{props['STATEFP10']}{props['COUNTYFP10']}"


def make_tract_geoid(props):
    return f"{props['STATEFP10']}{props['COUNTYFP10']}{props['TRACTCE10']}"


def iter_feature_collection(path: Path):
    decoder = json.JSONDecoder()
    buffer = ""
    idx = 0
    in_features = False
    eof = False

    with path.open() as handle:
        while True:
            if not eof and (len(buffer) - idx) < 2_000_000:
                chunk = handle.read(1_000_000)
                if chunk:
                    buffer += chunk
                else:
                    eof = True

            if not in_features:
                pos = buffer.find('"features"')
                if pos == -1:
                    if eof:
                        raise ValueError(f"Could not find features array in {path}")
                    if len(buffer) > 128:
                        buffer = buffer[-128:]
                    continue
                bracket = buffer.find("[", pos)
                if bracket == -1:
                    if eof:
                        raise ValueError(f"Could not parse features array in {path}")
                    continue
                idx = bracket + 1
                in_features = True

            while True:
                while idx < len(buffer) and buffer[idx] in " \r\n\t,":
                    idx += 1

                if idx < len(buffer) and buffer[idx] == "]":
                    return

                try:
                    feature, end = decoder.raw_decode(buffer, idx)
                except ValueError:
                    if eof:
                        raise
                    break

                yield feature
                idx = end

                if idx > 2_000_000:
                    buffer = buffer[idx:]
                    idx = 0
                    break

            if eof and idx >= len(buffer):
                return


def decode_topology_arc(raw_arc, transform):
    scale_x, scale_y = transform["scale"]
    translate_x, translate_y = transform["translate"]
    x = 0
    y = 0
    coords = []
    for delta_x, delta_y in raw_arc:
        x += delta_x
        y += delta_y
        coords.append(
            [
                round(translate_x + x * scale_x, ROUND_DIGITS),
                round(translate_y + y * scale_y, ROUND_DIGITS),
            ]
        )
    return coords


def stitch_arc_indexes(arc_indexes, decoded_arcs):
    stitched = []
    for index in arc_indexes:
        arc = decoded_arcs[index] if index >= 0 else list(reversed(decoded_arcs[-index - 1]))
        if stitched:
            stitched.extend(arc[1:])
        else:
            stitched.extend(arc)
    return stitched


def topo_geometry_to_geojson(geometry, decoded_arcs):
    geom_type = geometry["type"]
    if geom_type == "Polygon":
        return {
            "type": "Polygon",
            "coordinates": [stitch_arc_indexes(ring, decoded_arcs) for ring in geometry["arcs"]],
        }
    if geom_type == "MultiPolygon":
        return {
            "type": "MultiPolygon",
            "coordinates": [
                [stitch_arc_indexes(ring, decoded_arcs) for ring in polygon]
                for polygon in geometry["arcs"]
            ],
        }
    raise ValueError(f"Unsupported TopoJSON geometry type: {geom_type}")


def iter_topology_features(path: Path):
    topology = json.loads(path.read_text())
    transform = topology["transform"]
    decoded_arcs = [decode_topology_arc(raw_arc, transform) for raw_arc in topology["arcs"]]
    object_name = next(iter(topology["objects"]))
    for geometry in topology["objects"][object_name]["geometries"]:
        yield {
            "type": "Feature",
            "properties": geometry.get("properties", {}),
            "geometry": topo_geometry_to_geojson(geometry, decoded_arcs),
        }


def build_geojson_outputs():
    county_bbox_lookup = {}

    county_features = []
    for feature in iter_topology_features(COUNTIES_TOPOJSON):
        props = feature["properties"]
        geoid = make_county_geoid(props)
        county_bbox_lookup[geoid] = geometry_bbox(feature["geometry"])
        county_features.append(
            {
                "type": "Feature",
                "properties": {"geoid": geoid},
                "geometry": round_nested(feature["geometry"]),
            }
        )

    tract_features = []
    for feature in iter_topology_features(TRACTS_TOPOJSON):
        props = feature["properties"]
        tract_features.append(
            {
                "type": "Feature",
                "properties": {
                    "geoid": make_tract_geoid(props),
                    "countyGeoid": make_county_geoid(props),
                },
                "geometry": round_nested(feature["geometry"]),
            }
        )

    (PUBLIC_DATA_DIR / "counties.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": county_features}, separators=(",", ":"))
    )
    (PUBLIC_DATA_DIR / "tracts.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": tract_features}, separators=(",", ":"))
    )

    return county_bbox_lookup


def load_release_metrics(level: str, dp_root: Path, epsilons: list[str]):
    metrics = {}
    for epsilon_index, epsilon in enumerate(epsilons):
        path = dp_root / f"epsilon_{epsilon}" / f"DF_IL_2010_{level.upper()}_DP.csv"
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                geoid = row["geoid"]
                if not geoid or not geoid.startswith("17"):
                    continue
                entry = metrics.setdefault(
                    geoid,
                    {
                        "geoid": geoid,
                        "parentGeoid": row.get("parent_geoid", ""),
                        "truePop": int(row["true_pop"]),
                        "white": int(row["white"]),
                        "black": int(row["black"]),
                        "asian": int(row["asian"]),
                        "other": int(row["other"]),
                        "adjPop": [0] * len(epsilons),
                        "adjWhite": [0] * len(epsilons),
                        "adjBlack": [0] * len(epsilons),
                        "adjAsian": [0] * len(epsilons),
                        "adjOther": [0] * len(epsilons),
                    },
                )
                entry["adjPop"][epsilon_index] = int(row["adj_pop"])
                entry["adjWhite"][epsilon_index] = int(row["adj_white"])
                entry["adjBlack"][epsilon_index] = int(row["adj_black"])
                entry["adjAsian"][epsilon_index] = int(row["adj_asian"])
                entry["adjOther"][epsilon_index] = int(row["adj_other"])
    return list(metrics.values())


def load_block_counts(dp_root: Path):
    counts = Counter()
    epsilon_dirs = sorted(path for path in dp_root.glob("epsilon_*") if path.is_dir())
    if not epsilon_dirs:
        raise ValueError(f"No epsilon directories available under {dp_root}")
    path = epsilon_dirs[0] / "DF_IL_2010_BLOCK_DP.csv"
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            geoid = row["geoid"]
            if not geoid or len(geoid) != 15 or not geoid.startswith("17"):
                continue
            counts[geoid[:5]] += 1
    return counts


def block_sample_quotas(counts):
    quotas = {}
    for county_geoid, count in counts.items():
        quota = max(BLOCK_SAMPLE_FLOOR, round(count * BLOCK_SAMPLE_RATE))
        quotas[county_geoid] = min(count, quota)
    return quotas


def sample_blocks(quotas):
    rngs = {county: random.Random(BLOCK_SAMPLE_SEED + int(county)) for county in quotas}
    seen = Counter()
    samples = defaultdict(list)

    for feature in iter_feature_collection(BLOCKS_GEOJSON):
        props = feature["properties"]
        geoid = props["BLOCKID10"]
        county_geoid = f"{props['STATEFP10']}{props['COUNTYFP10']}"
        tract_geoid = f"{props['STATEFP10']}{props['COUNTYFP10']}{props['TRACTCE10']}"
        quota = quotas.get(county_geoid, 0)
        if quota <= 0:
            continue

        seen[county_geoid] += 1
        lon, lat = bbox_center(geometry_bbox(feature["geometry"]))
        item = {
            "geoid": geoid,
            "countyGeoid": county_geoid,
            "tractGeoid": tract_geoid,
            "lon": round(lon, ROUND_DIGITS),
            "lat": round(lat, ROUND_DIGITS),
            "geometry": round_nested(feature["geometry"]),
        }

        bucket = samples[county_geoid]
        if len(bucket) < quota:
            bucket.append(item)
            continue

        slot = rngs[county_geoid].randint(0, seen[county_geoid] - 1)
        if slot < quota:
            bucket[slot] = item

    out = []
    for county_geoid in sorted(samples):
        out.extend(samples[county_geoid])
    return out


def load_sampled_block_metrics(sampled_blocks, dp_root: Path, epsilons: list[str]):
    sample_lookup = {item["geoid"]: item for item in sampled_blocks}

    for epsilon_index, epsilon in enumerate(epsilons):
        path = dp_root / f"epsilon_{epsilon}" / "DF_IL_2010_BLOCK_DP.csv"
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                geoid = row["geoid"]
                if geoid not in sample_lookup or len(geoid) != 15 or not geoid.startswith("17"):
                    continue

                entry = sample_lookup[geoid]
                if "truePop" not in entry:
                    entry["truePop"] = int(row["true_pop"])
                    entry["white"] = int(row["white"])
                    entry["black"] = int(row["black"])
                    entry["asian"] = int(row["asian"])
                    entry["other"] = int(row["other"])
                    entry["adjPop"] = [0] * len(epsilons)
                    entry["adjWhite"] = [0] * len(epsilons)
                    entry["adjBlack"] = [0] * len(epsilons)
                    entry["adjAsian"] = [0] * len(epsilons)
                    entry["adjOther"] = [0] * len(epsilons)

                entry["adjPop"][epsilon_index] = int(row["adj_pop"])
                entry["adjWhite"][epsilon_index] = int(row["adj_white"])
                entry["adjBlack"][epsilon_index] = int(row["adj_black"])
                entry["adjAsian"][epsilon_index] = int(row["adj_asian"])
                entry["adjOther"][epsilon_index] = int(row["adj_other"])

    return list(sample_lookup.values())


def load_block_truth_records(dp_root: Path, epsilons: list[str]):
    records = []
    path = dp_root / f"epsilon_{epsilons[0]}" / "DF_IL_2010_BLOCK_DP.csv"
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            geoid = row["geoid"]
            if not geoid or len(geoid) != 15 or not geoid.startswith("17"):
                continue
            records.append(
                {
                    "geoid": geoid,
                    "tractGeoid": row["parent_geoid"],
                    "countyGeoid": geoid[:5],
                    "truePop": int(row["true_pop"]),
                    "white": int(row["white"]),
                    "black": int(row["black"]),
                    "asian": int(row["asian"]),
                    "other": int(row["other"]),
                }
            )
    return records


def assign_demo_vtds(sampled_blocks, county_bbox_lookup, epsilon_count: int):
    vtd_summary = {}

    for block in sampled_blocks:
        bounds = county_bbox_lookup[block["countyGeoid"]]
        min_x, min_y, max_x, max_y = bounds
        mid_x = (min_x + max_x) / 2
        mid_y = (min_y + max_y) / 2
        col = 0 if block["lon"] < mid_x else 1
        row = 0 if block["lat"] < mid_y else 1
        cell = row * 2 + col + 1
        vtd_id = f"{block['countyGeoid']}-v{cell}"
        block["demoVtd"] = vtd_id

        summary = vtd_summary.setdefault(
            vtd_id,
            {
                "id": vtd_id,
                "countyGeoid": block["countyGeoid"],
                "blockCount": 0,
                "truePop": 0,
                "white": 0,
                "black": 0,
                "asian": 0,
                "other": 0,
                "adjPop": [0] * epsilon_count,
                "adjWhite": [0] * epsilon_count,
                "adjBlack": [0] * epsilon_count,
                "adjAsian": [0] * epsilon_count,
                "adjOther": [0] * epsilon_count,
            },
        )

        summary["blockCount"] += 1
        summary["truePop"] += block["truePop"]
        summary["white"] += block["white"]
        summary["black"] += block["black"]
        summary["asian"] += block["asian"]
        summary["other"] += block["other"]
        for idx in range(epsilon_count):
            summary["adjPop"][idx] += block["adjPop"][idx]
            summary["adjWhite"][idx] += block["adjWhite"][idx]
            summary["adjBlack"][idx] += block["adjBlack"][idx]
            summary["adjAsian"][idx] += block["adjAsian"][idx]
            summary["adjOther"][idx] += block["adjOther"][idx]

    return list(vtd_summary.values())


def main():
    args = parse_args()
    PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
    dp_root = args.dp_root.resolve()
    epsilons = discover_epsilons(dp_root)
    default_epsilon = args.default_epsilon if args.default_epsilon in epsilons else epsilons[min(2, len(epsilons) - 1)]

    county_bbox_lookup = build_geojson_outputs()
    counties = load_release_metrics("county", dp_root, epsilons)
    tracts = load_release_metrics("tract", dp_root, epsilons)

    block_counts = load_block_counts(dp_root)
    quotas = block_sample_quotas(block_counts)
    sampled_blocks = sample_blocks(quotas)
    sampled_blocks = load_sampled_block_metrics(sampled_blocks, dp_root, epsilons)
    sampled_blocks = sorted(sampled_blocks, key=lambda item: (item["countyGeoid"], item["tractGeoid"], item["geoid"]))
    block_truth_records = load_block_truth_records(dp_root, epsilons)
    demo_vtds = assign_demo_vtds(sampled_blocks, county_bbox_lookup, len(epsilons))
    block_features = []
    block_metrics = []
    for block in sampled_blocks:
        block_features.append(
            {
                "type": "Feature",
                "properties": {
                    "geoid": block["geoid"],
                    "countyGeoid": block["countyGeoid"],
                    "tractGeoid": block["tractGeoid"],
                    "demoVtd": block["demoVtd"],
                },
                "geometry": block["geometry"],
            }
        )
        block_metrics.append({key: value for key, value in block.items() if key != "geometry"})

    payload = {
        "meta": {
            "epsilons": epsilons,
            "defaultLevel": "county",
            "defaultEpsilon": default_epsilon,
            "defaultCountyGeoid": DEFAULT_FOCUS_COUNTY,
            "blockSampleNote": "Sampled blocks are rendered as real sampled block polygons.",
            "vtdNote": "Synthetic demo VTDs are 2x2 spatial partitions of sampled blocks within each county.",
            "dpRoot": str(dp_root),
        },
        "counties": counties,
        "tracts": tracts,
        "blockSample": block_metrics,
        "demoVtds": demo_vtds,
    }

    (PUBLIC_DATA_DIR / "metrics.json").write_text(json.dumps(payload, separators=(",", ":")))
    (PUBLIC_DATA_DIR / "blocks_sample.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": block_features}, separators=(",", ":"))
    )
    (PUBLIC_DATA_DIR / "block_truth.json").write_text(json.dumps(block_truth_records, separators=(",", ":")))

    summary = {
        "counties": len(counties),
        "tracts": len(tracts),
        "blockTruth": len(block_truth_records),
        "sampledBlocks": len(block_metrics),
        "demoVtds": len(demo_vtds),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
