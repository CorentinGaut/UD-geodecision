# Geodecision example: walking accessibility to parks

A worked example of the graph + accessibility part of `geodecision`, run
entirely through the package's own CLI/config files (no example-only
Python logic) — every parameter (bounding box, projection, trip times,
...) lives in a JSON config under `config/`, so re-running for a different
area or CRS is a matter of editing JSON, not code.

The scenario: real park polygons fetched from OpenStreetMap for a bbox in
central Lyon, walking isochrones computed from every park at once ("time
to the nearest park"), rendered as a map.

## Install

From the `geodecision/` directory (the one containing `pyproject.toml`):

```bash
uv sync
```

This creates a `.venv` with `geodecision` and its dependencies (including
the `geodecision` console-script entry point from `pyproject.toml`'s
`[project.scripts]`). Run subcommands via `uv run geodecision <command> <config.json>`,
or activate the environment (`source .venv/bin/activate`) and use `geodecision <command> <config.json>`
directly. If you'd rather not install the package, every subcommand below
also works as `uv run python -m geodecision.cli <command> <config.json>`.

`pyproject.toml` targets current, mutually-compatible dependency versions
(Python 3.11+, osmnx >=2.0, ...) — the once-pinned `env.yml` (Python 3.7,
osmnx 0.10, ...) from 2020 has been retired.

Requires internet access (`download-graph` and `fetch-polygons` query the
Overpass API / OpenStreetMap; fetching buildings for the whole bbox can
take ~1 minute).

## Run

```bash
geodecision download-graph      examples/config/graph.json
geodecision fetch-polygons      examples/config/parks.json
geodecision fetch-polygons      examples/config/buildings.json
geodecision compute-accessibility examples/config/accessibility.json
geodecision visualize           examples/config/visualize.json
```

Each command prints its output folder on success and copies the config
file it was given into that folder as `run_config.json` — so
`examples/output/` always documents exactly which parameters produced it,
even if you've since edited `config/*.json`. Progress/timing details for
every run also get appended to `activity.log` in whichever directory you
ran the command from (geodecision's existing `logger` module writes there
regardless of which subcommand is running).

| step | command | config | what it does |
|---|---|---|---|
| 1 | `download-graph` | `config/graph.json` | Downloads a walkable OSM street graph for `bbox`, adds walking-time edge weights (`walk_speed_kmh`) |
| 2 | `fetch-polygons` | `config/parks.json` | Fetches real park polygons (`osm_key`/`osm_value`) for the same `bbox` — these are the isochrone origins |
| 2 | `fetch-polygons` | `config/buildings.json` | Fetches building footprints for the same `bbox` — map context only, not used in the accessibility computation |
| 3 | `compute-accessibility` | `config/accessibility.json` | Splits each park's boundary into candidate entrance points, connects them to the street graph, and computes isochrones from all of them at once |
| 4 | `visualize` | `config/visualize.json` | Renders the isolines (street segments), each colored by its own accessibility-distance category |

## Config files

- `config/graph.json` — `geodecision.graph.download.run`, see
  `geodecision/geodecision/graph/schema.py` (`GRAPH_SCHEMA`) for all fields.
  `bbox` is `[SOUTH, WEST, NORTH, EAST]` in EPSG:4326 — the same convention
  used everywhere in this pipeline (`osmquery`'s bbox too), converted
  internally wherever a library expects a different order (e.g. osmnx's
  own `(west, south, east, north)`).
- `config/parks.json`, `config/buildings.json` — `geodecision.osmquery.methods.run`,
  see `geodecision/geodecision/osmquery/schema.py` (`POLYGON_QUERY_SCHEMA`).
- `config/accessibility.json` — the pre-existing `geodecision.accessibility.accessibility.run`,
  see `geodecision/geodecision/accessibility/schema.py` (`ACCESS_SCHEMA`).
  Points at step 1 and step 2's (parks) output files.
- `config/visualize.json` — `geodecision.visualization.plot_isochrones.run`,
  see `geodecision/geodecision/visualization/schema.py` (`VIZ_SCHEMA`).

To run this for a different city: edit `bbox` consistently across
`graph.json`/`parks.json`/`buildings.json`, and `epsg_metric` everywhere
it appears (2154 = RGF93 / Lambert-93, France-specific — use a metric CRS
appropriate for your area) in `accessibility.json`/`visualize.json`.

One gotcha in `accessibility.json`: `columns_to_keep` is a plain column
selection applied after the polygon-splitting step, so it must explicitly
include `"geometry"` (in addition to any polygon attribute columns you
want to keep, e.g. `"name"`) — leaving it out drops the geometry entirely
and the run fails with `KeyError: "['geometry'] not in index"`.

## Outputs

Written to `examples/output/` (gitignored):

| file | produced by | content |
|---|---|---|
| `edges.json`, `nodes.json` | `download-graph` | the graph, in geodecision's exchange format |
| `parks.geojson`, `buildings.geojson` | `fetch-polygons` | real OSM polygons |
| `isolines_parks.geojson` | `compute-accessibility` | every street segment reached, each tagged with the time to the *nearest* park (`iso_cat_merged`) and its Viridis `color` |
| `isochrones_parks.geojson` | `compute-accessibility` | one dissolved polygon per trip-time band |
| `5.geojson`, `10.geojson`, `15.geojson` | `compute-accessibility` | cumulative accessible area per trip time, merged with the park footprints themselves (`SpatialOperations`, keyed by trip time in minutes) |
| `updated_edges.json`, `updated_nodes.json`, `problematic_nodes.json` | `compute-accessibility` | the rest of `accessibility.run()`'s standard output set |
| `isochrones_map.png` | `visualize` | the rendered map |
| `run_config.json` | every command | the exact JSON config used for that output folder |

## Why this is a "distance to nearest park" map, not nested rings

Because there are many park origins (23 in this bbox, ~160 connected
entrance points), each street segment is tagged with the time to
*whichever* park reaches it first — the bands are disjoint (0-5 / 5-10 /
10-15 min), not nested cumulative rings the way a single-origin isochrone's
would be. Segments that fall *inside* a park polygon itself get a separate
"0 min (on site)" category (the neutral-line handling in
`Accessibility.get_results`). `visualize` plots the isolines using exactly
the colors `Accessibility` already assigned per segment, so the map
matches the underlying data with no re-derivation, and the legend is built
from whatever categories are actually present — it adapts automatically if
you change `trip_times` in `accessibility.json`.

## Is the underlying code deprecated?

Not dead, but it hadn't been run against current libraries before this.
See `HISTORY.rst`'s "Unreleased" section for the list of real
compatibility (and one correctness) bugs this uncovered and fixed in the
package itself — most notably a silently-swallowed `TypeError` in
`ConnectPoints.split_line` that was fragmenting every street graph it
touched.
