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
the `geodecision` console-script entry point). Run subcommands via
`uv run geodecision <command> <config.json>`, or activate the environment
(`source .venv/bin/activate`) and use `geodecision <command> <config.json>`
directly.

Every command prints its output folder on success and copies the config
file it was given into that folder as `run_config.json` — so
`examples/output/` always documents exactly which parameters produced it.
Progress/timing details for every run also get appended to `activity.log`
in whichever directory you ran the command from.

---

## Workflow 1: Accessibility to parks

Requires internet access (`download-graph`, `fetch-polygons`, and
`compute-accessibility` all query OpenStreetMap; fetching buildings for the
whole bbox can take ~1 minute).

### Pipeline

Each box below is a config file; each arrow is a `geodecision` command.
Dotted arrows mean "this file's `select_park` can derive its query extent
from that park", not a hard file dependency.


```bash
geodecision fetch-polygons        examples/config/parks.json
geodecision download-graph        examples/config/graph.json
geodecision fetch-polygons        examples/config/buildings.json
geodecision compute-accessibility examples/config/accessibility.json
geodecision visualize             examples/config/visualize.json
geodecision compute-impact-zone   examples/config/impact_zone.json
```

`compute-accessibility` is the slowest step — it took ~10 minutes on an
average laptop for the Lyon example. What it actually does: finds real OSM
entrance/gate points near each park's boundary (falling back to
evenly-spaced boundary points for parks with too few tagged ones), connects
them to the street graph, and computes isochrones from all of them at once.

### Single park or whole extent

Two ways to generate isochrones with the same commands — pick one by
setting (or leaving empty) a `poly_id`:

- **Whole extent (default)** — `bbox` drives `graph.json`/`parks.json`/`buildings.json`,
  and `select_id` is left empty (`""`) in `accessibility.json`/`visualize.json`.
  `compute-accessibility` pools every park in the bbox together, measuring
  "time to the *nearest* park" across all of them at once.
- **Single selected park** — run `fetch-polygons` on `parks.json` once,
  pick a `poly_id` from the resulting `parks.geojson`, and set it in
  `select_id` (`accessibility.json`, `visualize.json`) and
  `select_park.select_id` (`graph.json`, `buildings.json`). `compute-accessibility`
  then computes the isochrone from that one park only; `select_park`
  also derives `graph.json`/`buildings.json`'s query extent from that
  park's own buffered impact zone (`max(trip_times)` at `walk_speed_kmh`,
  or an explicit `buffer_m` — see `geodecision/geodecision/spatialops/extent.py`)
  instead of a hand-picked `bbox`; `visualize.json`'s `highlight_id` picks
  the park out on the map (orange fill/outline, "Selected park" in the
  legend).

Either way, `parks.json` itself always stays `bbox`-based (a broad,
one-time lookup — there's no park to select until it's run once), which
is why step 1 must run before step 2.

### Config cheat-sheet

Full schemas: `geodecision/geodecision/{graph,osmquery,accessibility,visualization,impact}/schema.py`.

<details>
<summary><code>config/graph.json</code> — <code>geodecision.graph.download.run</code></summary>

| field | | default |
|---|---|---|
| `output_folder`, `edges_filename`, `nodes_filename` | required | — |
| `bbox` **or** `select_park` | required (one of) | — |
| `network_type` | optional | `"walk"` |
| `walk_speed_kmh` | optional | `5` |

`bbox` is `[SOUTH, WEST, NORTH, EAST]` in **EPSG:4326** — the same
convention used everywhere in this pipeline, converted internally
wherever a library expects a different order (e.g. osmnx's own
`(west, south, east, north)`).
</details>

<details>
<summary><code>config/parks.json</code>, <code>config/buildings.json</code> — <code>geodecision.osmquery.methods.run</code></summary>

| field | | default |
|---|---|---|
| `osm_key`, `output_folder`, `polygons_geojsonfile` | required | — |
| `bbox` **or** `select_park` | required (one of) | — |
| `osm_value` | optional | `"all"` |
| `epsg_origin` | optional | `4326` |
| `id_column` | optional | `"poly_id"` |

`parks.json` stays `bbox`-based (there's no park to select yet);
`buildings.json` uses `select_park` in the example config.
</details>

<details open>
<summary><code>config/accessibility.json</code> — <code>geodecision.accessibility.accessibility.run</code></summary>

| paths & ids | crs & graph mapping |
|---|---|
| `polygons_geojsonfile` | `epsg_graph` |
| `graph_nodes_jsonfile`, `graph_edges_jsonfile` | `epsg_input` |
| `id_column`, `columns_to_keep` | `epsg_metric` |
| `output_folder`, `output_format` | `lat`, `lon` |
| `output_isolines_layername`, `output_buffered_isolines_union_layername` | |
| `prefix`, `access_type` | |

All required — no code-level default.

| tuning knob | required? | default |
|---|---|---|
| `trip_times`, `threshold`, `dist_split`, `knn`, `distance`, `distance_buffer`, `weight`, `tolerance` | required | — |
| `select_id` | optional | none (whole extent) |
| `entrance_buffer_dist` | optional | `15` (meters — max distance from a park's boundary for a real OSM entrance/gate point to count) |
| `min_entries_per_park` | optional | `2` (real matches needed to skip the synthetic fallback for that park) |

> ⚠️ `columns_to_keep` is a plain column selection applied after
> entry-point generation, so it must explicitly include `"geometry"` —
> leaving it out fails with `KeyError: "['geometry'] not in index"`.
</details>

<details>
<summary><code>config/visualize.json</code> — <code>geodecision.visualization.plot_isochrones.run</code></summary>

| field | | default |
|---|---|---|
| `isolines_geojsonfile`, `epsg_metric`, `output_folder`, `output_png` | required | — |
| `parks_geojsonfile`, `buildings_geojsonfile` | optional | not drawn if omitted |
| `zones_folder` | optional | impact-zone bands not drawn if omitted |
| `zones_format` | optional | `"geojson"` |
| `trip_times` | optional | used with `zones_folder` to pick which trip-time bands to draw |
| `title` | optional | `"Walking distance to nearest feature"` |
| `linewidth` | optional | `2.5` |
| `id_column` | optional | `"poly_id"` |
| `highlight_id` | optional | none |

`zones_folder`/`zones_format`/`trip_times` draw the impact-zone extent as
translucent bands, colored to match the isolines' own trip-time colors;
`id_column`/`highlight_id` pick out one park with a distinct fill/outline.
</details>

<details>
<summary><code>config/impact_zone.json</code> — <code>geodecision.impact.impact_zone.run</code></summary>

| field | | default |
|---|---|---|
| `zones_folder`, `zones_format`, `trip_times`, `buildings_geojsonfile`, `epsg_metric`, `output_folder`, `output_format` | required | — (every field is required, no fallback) |

Points at `compute-accessibility`'s per-trip-time zone outputs
(`zones_folder`/`zones_format` matching that run's `output_folder`/
`output_format`) and at `buildings.json`'s output.
</details>

To run this for a different city: edit `parks.json`'s `bbox`, and
`epsg_metric` everywhere it appears (2154 = RGF93 / Lambert-93,
France-specific — use a metric CRS appropriate for your area), including
inside `graph.json`/`buildings.json`'s `select_park` blocks. Their
`select_park.select_id` also needs updating to a real `poly_id` from the
new area's `parks.geojson` — or set `bbox` directly in `graph.json`/
`buildings.json` instead of `select_park` to use the whole-extent mode.

### Outputs

Written to `examples/output/` (gitignored), grouped by the command that
produces them:


| file | content |
|---|---|
| `edges.json`, `nodes.json` | the graph, in geodecision's exchange format |
| `parks.geojson`, `buildings.geojson` | real OSM polygons |
| `isolines_parks.geojson` | every street segment reached, tagged with the time to the *nearest* park (`iso_cat_merged`) and its Viridis `color` |
| `isochrones_parks.geojson` | one dissolved polygon per trip-time band |
| `5.geojson`, `10.geojson`, `15.geojson` | cumulative accessible area per trip time, merged with the park footprints (`SpatialOperations`, keyed by trip time in minutes) |
| `updated_edges.json`, `updated_nodes.json` | the connected street graph. `updated_nodes.json`'s access nodes carry `entry_source` (`osm_entrance` / `osm_gate` / `synthetic`) and `entry_tag` (the raw OSM tag, `null` for synthetic points) |
| `problematic_nodes.json` | access nodes that couldn't be connected within `threshold` |
| `isochrones_map.png` | the rendered map (park highlight and impact-zone bands depend on `visualize.json`'s `highlight_id`/`zones_folder`) |
| `impact_zone_5/10/15.geojson` | the buildings intersecting each trip-time zone |
| `impact_zone_summary.json` | one entry per trip time: `n_buildings`, `building_area_m2`, `zone_area_m2` |
| `run_config.json` | the exact JSON config used for that output folder |

### Visualize the result

Once `isolines_parks.geojson` / `isochrones_parks.geojson` exist, there are two ways to look at them:

1. **Built-in PNG rendering** — `geodecision visualize examples/config/visualize.json` renders the isolines, colored by accessibility-distance category, to `examples/output/isochrones_map.png`.
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

### Pipeline

```bash
geodecision process-citygml examples/config/citygml.json
```

### Config cheat-sheet

<details open>
<summary><code>config/citygml.json</code> — <code>geodecision.citygml.citygml.run</code></summary>

| field | | default |
|---|---|---|
| `gml_dir`, `epsg_in`, `epsg_out`, `output_folder` | required | — |
| `driver` | optional | `"GeoJSON"` (or `"GPKG"`, `"ESRI Shapefile"`) |
| `palette` | optional | `"viridis"` (or `"magma"`, `"plasma"`) — Bokeh palette for the roof-slope `categories` column |
| `attributes` | optional | `[]` — building attribute fields combined into `attribute`, used to flag `public_access` (see `geodecision/geodecision/citygml/constants.py`'s `PUBLIC` keyword list); every merged file must expose the same columns |
| `selection` | optional | none — if set, filters the merged roofs to those with "potential" and writes `selection.<ext>`. Independently optional thresholds: `min_width`/`compactness`/`area` (keep rows `>=` value) and `max_slope` (keep rows `<=` value) |

Check the `.gml` file's own `srsName` attribute for `epsg_in` — Grand Lyon
publishes in EPSG:3946 (RGF93 / CC46).
</details>

Per-file outputs also land in `examples/output/citygml/per_file/`
(one `<name>_roofs`/`<name>_grounds`/`<name>.json` per input `.gml` file),
alongside the merged results below — handy for spot-checking a single
district before trusting the merge.

### Outputs

Written to `examples/output/citygml/` (gitignored):

| file | content |
|---|---|
| `roofs.geojson` | every roof surface, merged, with `angles` (slope, degrees), `area` (m²), `compactness`, `min_width` (m), `nb_levels`/`heights`, `categories`/`colors`, and the building attribute columns (incl. `public_access`) |
| `grounds.geojson` | every building footprint, merged |
| `buildings.json` | per-building attribute dump, merged |
| `selection.<ext>` | only present if `selection` is set — the subset of `roofs.geojson` meeting every configured threshold |
| `run_config.json` | the exact JSON config used for this run |
