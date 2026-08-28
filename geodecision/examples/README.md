# Geodecision examples

Two independent example workflows, each runnable entirely through `geodecision`'s own CLI/config files — every parameter (bounding box, projection, thresholds, ...) lives in a JSON config under `config/`, so re-running for a different area is a matter of editing JSON, not code. They don't depend on each other and use different input data:

1. **[Accessibility to parks](#workflow-1-accessibility-to-parks)** — real OpenStreetMap park polygons for a bbox in central Lyon, walking isochrones computed from every park at once ("time to the nearest park"), rendered as a map.
2. **[CityGML roofs](#workflow-2-citygml-roofs)** — 3D building models (CityGML) parsed for per-building roof slope/area/compactness/floor-count, optionally filtered down to roofs with "potential" (e.g. for solar panels).

## Install

From the `geodecision/` directory (the one containing [pyproject.toml](./../pyproject.toml)):

```bash
uv sync
```

This creates a `.venv` with `geodecision` and its dependencies (including
the `geodecision` console-script entry point from `pyproject.toml`'s). Run subcommands via `uv run geodecision <command> <config.json>`,
or activate the environment (`source .venv/bin/activate`) and use `geodecision <command> <config.json>`
directly. If you'd rather not install the package, every subcommand below
also works as `uv run python -m geodecision.cli <command> <config.json>`.

`pyproject.toml` targets current, mutually-compatible dependency versions (Python 3.11+, osmnx >=2.0, ...).

Every command prints its output folder on success and copies the config
file it was given into that folder as `run_config.json` — so
`examples/output/` always documents exactly which parameters produced it,
even if you've since edited `config/*.json`. Progress/timing details for
every run also get appended to `activity.log` in whichever directory you
ran the command from (geodecision's existing `logger` module writes there
regardless of which subcommand is running).

---

## Workflow 1: Accessibility to parks

Requires internet access (`download-graph` and `fetch-polygons` query the Overpass API / OpenStreetMap; fetching buildings for the whole bbox can take ~1 minute).

### Run

```bash
geodecision download-graph        examples/config/graph.json
geodecision fetch-polygons        examples/config/parks.json
geodecision fetch-polygons        examples/config/buildings.json
geodecision compute-accessibility examples/config/accessibility.json
geodecision visualize             examples/config/visualize.json
```

| step | command | config | what it does |
|---|---|---|---|
| 1 | `download-graph` | `config/graph.json` | Downloads a walkable OSM street graph for `bbox`, adds walking-time edge weights (`walk_speed_kmh`) |
| 2 | `fetch-polygons` | `config/parks.json` | Fetches real park polygons (`osm_key`/`osm_value`) for the same `bbox` — these are the isochrone origins |
| 2 | `fetch-polygons` | `config/buildings.json` | Fetches building footprints for the same `bbox` — map context only, not used in the accessibility computation |
| 3 | `compute-accessibility` | `config/accessibility.json` | Splits each park's boundary into candidate entrance points, connects them to the street graph, and computes isochrones from all of them at once |
| 4 | `visualize` | `config/visualize.json` | Renders the isolines (street segments), each colored by its own accessibility-distance category |

### Config files

- `config/graph.json` — `geodecision.graph.download.run`, see
  `geodecision/geodecision/graph/schema.py` for all fields.
  `bbox` is `[SOUTH, WEST, NORTH, EAST]` in **EPSG:4326**. The same convention
  used everywhere in this pipeline (`osmquery`'s bbox too), converted
  internally wherever a library expects a different order (e.g. osmnx's
  own `(west, south, east, north)`).
- `config/parks.json`, `config/buildings.json` — `geodecision.osmquery.methods.run`, see `geodecision/geodecision/osmquery/schema.py`.
- `config/accessibility.json` — the pre-existing `geodecision.accessibility.accessibility.run`, see `geodecision/geodecision/accessibility/schema.py`.
  Points at step 1 and step 2's (parks) output files.
- `config/visualize.json` — `geodecision.visualization.plot_isochrones.run`,
  see `geodecision/geodecision/visualization/schema.py`.

To run this for a different city: edit `bbox` consistently across
`graph.json`/`parks.json`/`buildings.json`, and `epsg_metric` everywhere
it appears (2154 = RGF93 / Lambert-93, France-specific use a metric CRS
appropriate for your area) in `accessibility.json`/`visualize.json`.

<!-- One gotcha in `accessibility.json`: `columns_to_keep` is a plain column
selection applied after the polygon-splitting step, so it must explicitly
include `"geometry"` (in addition to any polygon attribute columns you
want to keep, e.g. `"name"`) — leaving it out drops the geometry entirely
and the run fails with `KeyError: "['geometry'] not in index"`. -->

### Outputs

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

### Visualize the result

Once `isolines_parks.geojson` / `isochrones_parks.geojson` exist, there are two ways to look at them:

1. **Built-in PNG rendering** — step 4 above (`geodecision visualize examples/config/visualize.json`) renders the isolines, colored by accessibility-distance category, to `examples/output/isochrones_map.png`. `fetch-polygons` and `visualize` can take a while depending on the bounding box size; step 3, `compute-accessibility`, is the slowest — it took ~10 minutes on an average laptop for the Lyon example.
2. **3D web visualization** — load the GeoJSON output into a visualization library such as [iTowns](https://www.itowns-project.org/). A live example built from this same kind of accessibility output is available [here](https://vcityteam.github.io/itowns-accessibility/), with its source code on [GitHub](https://github.com/VCityTeam/itowns-accessibility).

---

## Workflow 2: CityGML roofs

A single, independent command — `process-citygml` — parses 3D building
models (CityGML) to derive per-building roof slope, area, compactness,
minimum width, and an estimated number of floors: data OpenStreetMap
doesn't provide. It shares no inputs or outputs with Workflow 1 above;
run it whenever you have CityGML data for your study area, regardless of
whether you've run the accessibility workflow at all.

### Get CityGML data

CityGML files aren't fetched automatically (there's no Overpass-style API
for it) — download them yourself, e.g. from
[Grand Lyon's open data portal](https://data.beta.grandlyon.com/fr/jeux-de-donnees/maquettes-3d-texturees-a-commune-arrondissement-2009-2012-2015-metropole-lyon/info)
(one `.gml` file per district). Put every `.gml` file you want processed
together in one directory — `process-citygml` merges all of them into a
single result, matching one call to one study area (e.g. a city and its
districts, or a city and a neighboring commune):

```bash
mkdir -p examples/data/city_gml
# copy/extract your downloaded *.gml files into examples/data/city_gml/
```

### Run

```bash
geodecision process-citygml examples/config/citygml.json
```

### Config files

- `config/citygml.json` — `geodecision.citygml.citygml.run`, see
  `geodecision/geodecision/citygml/schema.py` for all fields:

| field | meaning |
|---|---|
| `gml_dir` | directory containing the `*.gml` files to parse (one per district, for instance) |
| `epsg_in` / `epsg_out` | CRS of the CityGML coordinates / CRS to reproject roofs and grounds into. Check the `.gml` file's own `srsName` attribute for `epsg_in` — Grand Lyon publishes in EPSG:3946 (RGF93 / CC46) |
| `driver` | output format: `"GeoJSON"` (default), `"GPKG"`, or `"ESRI Shapefile"` |
| `palette` | Bokeh color palette used for the roof-slope `categories` column: `"viridis"` (default), `"magma"`, or `"plasma"` |
| `attributes` | building attribute field names to combine into a single `attribute` column, used to flag `public_access` (see `geodecision/geodecision/citygml/constants.py`'s `PUBLIC` keyword list). Every file being merged must expose the same attribute columns |
| `selection` (optional) | if present, filter the merged roofs to those with "potential" (e.g. for solar panels) and write `selection.<ext>`. Every threshold is independently optional: `min_width`/`compactness`/`area` (keep rows `>=` the value, in meters / ratio / m²) and `max_slope` (keep rows `<=` the value, in degrees) |

Per-file outputs also land in `examples/output/citygml/per_file/`
(one `<name>_roofs`/`<name>_grounds`/`<name>.json` per input `.gml` file),
alongside the merged results below — handy for spot-checking a single
district before trusting the merge.

### Outputs

Written to `examples/output/citygml/` (gitignored):

| file | content |
|---|---|
| `roofs.geojson` | every roof surface from every input file, merged, with `angles` (slope, degrees), `area` (m²), `compactness`, `min_width` (m), `nb_levels`/`heights`, `categories`/`colors`, and the building attribute columns (incl. `public_access`) |
| `grounds.geojson` | every building footprint, merged |
| `buildings.json` | per-building attribute dump, merged |
| `selection.<ext>` | only present if `selection` is set in the config — the subset of `roofs.geojson` meeting every configured threshold |
| `run_config.json` | the exact JSON config used for this run |
