> ***GeoDecision => Decision-making tools for urban management***

## Presentation

Geodecision is a set of tools to help urban decision-making:
* (*Updated*) Accessibility/network operations and measures.
* (*Updated*) CityGML parsing to get roofs and measures:
  * slopes
  * area
  * compactness
  * minimum width
  * estimated number of floors
  * ...
* (*Deprecated*) OSM queries
* (*Deprecated*) Classification (*automatic best classification from data - for example INSEE gridded data*)
* (*Deprecated*) Spatial operations:
  * intersections between GeoDataFrame

Geodecision inputs and outputs are geospatial data:
* [GeoJSON](https://geojson.org/)
* [GeoPackages (an OGC open format)](https://www.geopackage.org/)

## Installation
### Warnings/Disclaimer
Our package requires libraries with **spatial functionality** such as [GeoPandas](https://geopandas.org). Those depend on open source C libraries ([GEOS](https://geos.osgeo.org/), [GDAL](https://www.gdal.org/), [PROJ](https://proj.org/)), but the underlying Python packages (`shapely`, `fiona`, `pyproj`, `rtree`) now ship prebuilt wheels bundling these libraries on PyPI, so no separate compiler or system install is required.

We use [uv](https://docs.astral.sh/uv/) - *a fast Python package and project manager* - to install and work with our package.

### How to
#### Install geodecision
1. Get & install [uv](https://docs.astral.sh/uv/getting-started/installation/)
2. Clone or download this repository
3. Open a Command Line Interface inside the cloned `geodecision/` directory (the one containing `pyproject.toml`)
4. Create the virtual environment and install GeoDecision and its dependencies:
    ```bash
    uv sync
    ```


#### Try the examples
Two **independent** example workflows — they use different input data and neither depends on the other — live in [`geodecision/examples/`](geodecision/examples/README.md), both runnable entirely through the package's own CLI, so no example-only code is needed. Dependency versions are pinned in [`geodecision/pyproject.toml`](geodecision/pyproject.toml) and kept current (Python 3.11+).

##### Workflow 1: Accessibility to parks
Walking accessibility to real OpenStreetMap park polygons, end to end:

```bash
cd geodecision
uv sync
source .venv/bin/activate
geodecision download-graph        examples/config/graph.json
geodecision fetch-polygons        examples/config/parks.json
geodecision fetch-polygons        examples/config/buildings.json
geodecision compute-accessibility examples/config/accessibility.json
geodecision visualize             examples/config/visualize.json # optional: generate a png file to visualize the result
geodecision compute-impact-zone   examples/config/impact_zone.json # optional: count buildings served per trip time
```
> `fetch-polygons`, `compute-accessibility` and `visualize` can be long depending on the bounding box size — `compute-accessibility` took ~10 minutes on an average laptop for the Lyon example above

This downloads a walkable street network and real park polygons for a bounding box in Lyon, computes isochrones (walking time to the nearest park), and renders a map to `geodecision/examples/output/isochrones_map.png`.
Every parameter (bounding box, projection, trip times, ...) is set in the JSON config files under `examples/config/`, so re-running for a different area is a matter of editing JSON. To scope the isochrone to a single park instead of pooling all of them, set `select_id` in `accessibility.json` to that park's `poly_id` (leave it `""` for the default pooled behavior); `compute-impact-zone` then reports how many buildings fall in each trip-time zone. Set the matching `highlight_id` in `visualize.json` to render that park picked out on the map, with the impact-zone bands overlaid.

Once the GeoJSON result is generated, there are two ways to visualize it:
1. **Built-in PNG rendering** — the `visualize` step above renders the isolines/isochrones to a PNG map (`isochrones_map.png`).
2. **3D web visualization** — integrate the GeoJSON result file into a visualization library such as [iTowns](https://www.itowns-project.org/). A live example is available [here](https://vcityteam.github.io/itowns-accessibility/), with its source code on [GitHub](https://github.com/VCityTeam/itowns-accessibility).

See [`geodecision/examples/README.md`](geodecision/examples/README.md#workflow-1-accessibility-to-parks) for the full walkthrough and what each output file contains.

##### Workflow 2: CityGML roofs
If you have CityGML (3D building) data for your area, a single command derives per-building roof slope/area/compactness/floor-count and an optional "roof potential" selection — no relation to the accessibility workflow above, and no OpenStreetMap data involved:

```bash
geodecision process-citygml examples/config/citygml.json
```

See [`geodecision/examples/README.md`](geodecision/examples/README.md#workflow-2-citygml-roofs) for where to get CityGML data, the config fields, and what each output file contains.

#### Use it
Once installed, you can use it as other packages:
```python
import geodecision
from geodecision import [specific]
```

### Architecture
#### Python geodecision module and sub-modules
```
geodecision/
├── accessibility
│   ├── accessibility.py
│   ├── __init__.py
│   ├── isochrone.py
│   └── schema.py
├── citygml
│   ├── analyseroofs.py
│   ├── categories.py
│   ├── citygml.py
│   ├── constants.py
│   ├── schema.py
│   └── __init__.py
├── cli.py
├── geodecision.py
├── graph
│   ├── connectpoints.py
│   ├── __init__.py
│   ├── splittednodes.py
│   └── utils.py
├── __init__.py
├── logger
│   ├── __init__.py
│   └── logger.py
├── osmquery
│   ├── __init__.py
│   └── methods.py
└── spatialops
    ├── __init__.py
    └── operations.py
```

## Developer's notes
### Work with geodecision and make changes
[uv](https://docs.astral.sh/uv/) manages the virtual environment, dependencies (including dev tools), and an editable install of the package all at once.

### Create the environment and install geodecision (editable) with its dev dependencies
```bash
cd [path/to/geodecision]
uv sync --group dev
```

### Run commands inside this environment
```bash
uv run geodecision --help
uv run pytest
```
Or activate the environment directly:
```bash
source [path/to/geodecision]/.venv/bin/activate
```
### Build after changes
Run `uv build` from the `geodecision/` directory to produce sdist/wheel artifacts in `dist/` (see [`geodecision/Makefile`](geodecision/Makefile)'s `dist` target).

<!-- ### Documentation
> We use [Sphinx](http://www.sphinx-doc.org/) for documentation

#### Generate documentation with Sphinx
> ***/!\ If you use the [numpydoc docstrings](https://numpydoc.readthedocs.io/en/latest/format.html#), add the [napoleon sphinx extension](http://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html) in ```conf.py```***:
```
mymodule:
   |___ docs
        |--- conf.py
```
```python
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode', 'sphinx.ext.napoleon']
```

Then generate documentation with command lines. Start a command line inside ```docs``` repository:
```
sphinx-apidoc -f -o . ../mymodule/
```
It will generate a bunch of ***rst*** files. Then, to get ***html*** pages (*in a ```_build``` directory for example*):
```
cd ..
sphinx-build -b html docs/ _build/ -->
```
