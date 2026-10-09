# Geodecision examples

Two independent example workflows, each runnable entirely through `geodecision`'s own CLI/config files — every parameter (bounding box, projection, thresholds, ...) lives in a JSON config under `config/`, so re-running for a different area is a matter of editing JSON, not code. They don't depend on each other and use different input data:

1. **[Accessibility to parks](#workflow-1-accessibility-to-parks)** — park polygons from a local GeoJSON file (`input/parcs_300.geojson`, the Lyon metropole's parks) or fetched from OpenStreetMap, walking isochrones computed from every park at once ("time to the nearest park"), rendered as a map.
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
`compute-accessibility` all query OpenStreetMap).

### Input polygons: local file or OpenStreetMap

The park polygons the isochrones start from can come from either source.
Every command reads them through a plain file path, so switching is just
a matter of editing that path in the configs:

- **Local file (default)**: the example configs point at
  [`input/parcs_300.geojson`](input/parcs_300.geojson), which holds the
  Lyon metropole's parks (EPSG:2154, id column `uid`, name column `nom`).
  Any polygon GeoJSON works, in any CRS: it is read with its own CRS and
  reprojected to `epsg_metric`. You only need its id column to hold
  unique values.
- **OpenStreetMap**: run `fetch-polygons examples/config/parks.json`
  first, then point the configs at its output
  (`examples/output/parks.geojson`, id column `poly_id`, name column
  `name`).

The fields to edit when switching are:

| config | fields |
|---|---|
| `accessibility.json` | `polygons_geojsonfile`, `id_column`, `columns_to_keep` |
| `graph.json`, `buildings.json` | `select_park.parks_geojsonfile`, `select_park.id_column` |
| `visualize.json` | `parks_geojsonfile`, `id_column` |

### Pipeline

With the local file (default configs):

```bash
geodecision fetch-polygons        examples/config/parks.json # if no local files
geodecision download-graph        examples/config/graph.json
geodecision fetch-polygons        examples/config/buildings.json
geodecision compute-accessibility examples/config/accessibility.json
geodecision visualize             examples/config/visualize.json
geodecision compute-impact-zone   examples/config/impact_zone.json
```

With OpenStreetMap parks, first run
`geodecision fetch-polygons examples/config/parks.json` and repoint the
configs as described above.

> ⚠️ The default configs cover **the whole local file**: 1,286 parks
> across the Lyon metropole (about 28 × 37 km). The graph and buildings
> downloads are large, and `compute-accessibility` can take hours. For a
> quick try, select a single park (see below), e.g.
> `"select_id": "PAR-69386-06016"` (Parc de la Tête d'Or).

What `compute-accessibility` actually does: it finds real OSM
entrance/gate points near each park's boundary (falling back to
evenly-spaced boundary points for parks with too few tagged ones),
connects them to the street graph, and computes isochrones from all of
them at once.

### Single park or whole extent

The same commands generate isochrones for either mode. Pick one by
setting a park id or leaving it empty (`""`):

- **Whole extent (default)**: `select_id` is `""` in
  `accessibility.json`, in `visualize.json` (`highlight_id`) and in
  `graph.json`/`buildings.json` (`select_park.select_id`).
  `compute-accessibility` pools every park in the polygons file together,
  measuring "time to the *nearest* park" across all of them. `select_park`
  derives the graph and buildings query extent from the **whole file's**
  extent, buffered by the impact-zone distance.
- **Single selected park**: set a park id from the polygons file's
  `id_column` in `select_id` (`accessibility.json`), `highlight_id`
  (`visualize.json`) and `select_park.select_id` (`graph.json`,
  `buildings.json`). `compute-accessibility` then computes the isochrone
  from that one park only. `select_park` derives the query extent from
  that park's own buffered impact zone, and `visualize.json`'s
  `highlight_id` picks the park out on the map (orange fill/outline,
  "Selected park" in the legend).

In both modes the buffer is `max(trip_times)` at `walk_speed_kmh`, or an
explicit `buffer_m` (see
`geodecision/geodecision/spatialops/extent.py`). You can also set a
literal `bbox` in `graph.json`/`buildings.json` instead of `select_park`.

### Selecting parks by attributes

`input/parcs_300.geojson` carries per-park attributes (`surface_parc` in
m², `pct_vegetation` and `pct_canopee` in %). Set a `filters` block to keep
only the parks matching thresholds (`min`/`max`, inclusive, each
optional; any numeric column works):

```json
"filters": {
    "surface_parc":   {"min": 5000},
    "pct_vegetation": {"min": 50},
    "pct_canopee":    {"min": 20}
}
```

`{}` (the default) keeps every park. Put the **same** `filters` in
`accessibility.json`, `visualize.json` and in `select_park` of
`graph.json`/`buildings.json`, so the computed isochrones, the map and the
OSM query extent all use the same parks. Filters combine with `select_id`
(both must match). `compute-accessibility` writes the selected parks to
`output/selected_parks.geojson` and logs how many were kept.

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

`parks.json` stays `bbox`-based (there's no park to select yet) and is
only needed for OSM-sourced parks. `buildings.json` uses `select_park` in
the example config.
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
| `filters` | optional | `{}` (all parks — see [Selecting parks by attributes](#selecting-parks-by-attributes)) |
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

To run this for a different city, point the configs at that city's
polygons file (local, or `parks.json` with a new `bbox` for OSM). Then
edit `epsg_metric` everywhere it appears, including inside
`graph.json`/`buildings.json`'s `select_park` blocks (2154 = RGF93 /
Lambert-93 is France-specific, so use a metric CRS appropriate for your
area). If you're using single-park mode, also update every `select_id`
to an id from the new file.

### Outputs

Written to `examples/output/` (gitignored), grouped by the command that
produces them:


| file | content |
|---|---|
| `edges.json`, `nodes.json` | the graph, in geodecision's exchange format |
| `parks.geojson`, `buildings.geojson` | real OSM polygons (`parks.geojson` only when parks are fetched from OSM) |
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
