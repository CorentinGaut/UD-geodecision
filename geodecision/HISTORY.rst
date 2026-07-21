=======
History
=======

Unreleased
----------

* Added a config-driven, reproducible pipeline for the graph +
  accessibility part of the package: ``geodecision.graph.download``
  (download a street graph from OpenStreetMap), ``geodecision.osmquery.methods.run``
  (fetch and save an OSM polygon layer), and ``geodecision.visualization.plot_isochrones``
  (render isochrone isolines colored by accessibility distance). Each
  follows the existing ``run(json_params)`` + ``jsonschema`` convention
  used by ``geodecision.accessibility.accessibility.run``. All four stages
  (plus the pre-existing accessibility computation) are now runnable as
  CLI subcommands via ``geodecision.cli`` (``geodecision download-graph``,
  ``fetch-polygons``, ``compute-accessibility``, ``visualize``), wired up
  through a new ``console_scripts`` entry point in ``setup.py``. See
  ``geodecision/examples/`` for a full worked example.
* Fixed several real bugs surfaced by running the package against current
  osmnx/networkx/geopandas/shapely/pandas for the first time since ~2020
  (previously it only ran against the versions pinned in ``env.yml``,
  themselves no longer installable):

  * ``osmquery/methods.py::get_OSM_poly`` called ``ox.footprints.create_footprints_gdf``,
    removed in osmnx >=1.0. Rewritten against the current ``ox.features_from_bbox``.
  * ``spatialops/operations.py::get_intersect_matches`` and
    ``graph/splittednodes.py::GetSplitNodes._get_boundary`` both iterated
    or indexed a ``MultiPolygon`` directly, which Shapely >=2.0 no longer
    allows. Fixed to use ``.geoms``.
  * ``graph/connectpoints.py::ConnectPoints.split_line`` — the most
    impactful one: ``shapely.ops.split()`` now returns a
    ``GeometryCollection``, which (like the ``MultiPolygon`` cases above)
    no longer supports direct iteration. The resulting ``TypeError`` was
    being silently swallowed and turned into an empty split, meaning every
    street edge that should have been split around a new connection point
    was simply deleted and never replaced - fragmenting the street graph
    into ~170 disconnected pieces every time a POI was connected to it.
    Fixed to read ``.geoms`` off the result.
  * ``graph/connectpoints.py``: ``.iteritems()`` (removed in pandas >=2.0)
    replaced with ``.items()``; ``self.points.groupby(['kne_idx'])``
    (grouping by a list, even length-1) now yields tuple keys under recent
    pandas instead of scalars, breaking a coordinate/edge-index lookup -
    fixed to group by the column name directly.
  * ``graph/utils.py::graph_to_gdf_points`` never added an ``osmid``
    column (node ids only lived in the DataFrame index), but
    ``ConnectPoints`` requires ``nodes['osmid']`` to build its
    coordinate-to-id lookup. Fixed by exposing the index as an ``osmid``
    column.
  * ``accessibility/isochrone.py::Accessibility.get_results``: a chained
    assignment (``gdf.col.iloc[...] = value``) used to zero out isolines
    inside the origin polygon is a silent no-op under pandas'
    Copy-on-Write (default since pandas 2.x) - fixed to use
    ``.loc[rows, col] = value``. The same method also mislabeled isoline
    geometries (already in the metric CRS, coming out of
    ``ConnectPoints``/``GetSplitNodes``, both of which require metric
    input) as being in the ``origin`` CRS and reprojected them again -
    reprojecting large metric coordinates as if they were lon/lat degrees
    produced ``inf`` values, which crashed the process (``SIGSEGV`` inside
    GEOS during ``.buffer()``, not a Python exception). Fixed to label the
    geometries with the metric CRS directly.
  * ``setup.py``: a missing comma in ``install_requires`` silently merged
    ``"fiona"`` and ``"geopandas>=0.6.0"`` into one invalid requirement
    string, breaking ``pip install``.

0.1.0 (2019-12-05)
------------------

* First release on PyPI.
