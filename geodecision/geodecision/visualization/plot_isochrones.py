#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render isochrone isolines, colored by accessibility distance.

Usage: plot_isochrones.py [<json_params>]

  -h --help  Show this screen.

"""
import argparse
import json
import os
import time

import geopandas as gpd
import matplotlib.pyplot as plt
from jsonschema import validate
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from ..logger.logger import logger, _get_duration
from ..impact.impact_zone import _read_zone
from .schema import VIZ_SCHEMA

_HIGHLIGHT_FILL = "#f5a623"
_HIGHLIGHT_EDGE = "#8b3a00"


def run(json_params):
    """
    Description
    ------------

    Plot the street segments ("isolines") written by
    accessibility.accessibility.run(), each colored by its own
    accessibility-distance category (the `color`/`iso_cat_merged` columns
    Accessibility already computes - no re-binning here), with optional
    park/building polygons for map context.

    Returns
    --------

    dict with the written PNG path.

    Parameters
    -----------

    - json_params (str):
        - Complete path to a JSON parameters file, see
          visualization.schema.VIZ_SCHEMA
        - Fields:
            - isolines_geojsonfile (str): output of accessibility.run()'s
              output_isolines_layername, must have "geometry", "color" and
              "iso_cat_merged" columns
            - parks_geojsonfile (str, optional): polygons drawn as context
            - buildings_geojsonfile (str, optional): polygons drawn as context
            - epsg_metric (number): CRS to plot in
            - output_folder (str)
            - output_png (str): output filename
            - title (str, optional)
            - linewidth (number, optional): isoline width, default 2.5
            - zones_folder, zones_format, trip_times (optional): draw the
              cumulative impact-zone extent (SpatialOperations.dict_unions
              output from compute-accessibility, or compute-impact-zone's
              own zones_folder/zones_format) as translucent bands, one per
              trip time, colored to match the isolines' own trip-time
              colors
            - id_column, highlight_id (str, optional): highlight the single
              feature in parks_geojsonfile matching
              parks[id_column] == highlight_id (e.g. the park a
              select_id-scoped compute-accessibility run was computed from).
              "" (or the field being absent) means "no highlight"
    """
    start_process = time.time()
    with open(json_params) as f:
        params = json.load(f)

    validate(instance=params, schema=VIZ_SCHEMA)

    output_folder = params["output_folder"]
    os.makedirs(output_folder, exist_ok=True)

    epsg_metric = params["epsg_metric"]
    linewidth = params.get("linewidth", 2.5)
    title = params.get("title", "Walking distance to nearest feature")

    start = time.time()
    isolines = gpd.read_file(params["isolines_geojsonfile"]).to_crs(epsg_metric)

    fig, ax = plt.subplots(figsize=(12, 12))

    # Colors keyed by trip-time category, taken directly from the isolines'
    # own (Viridis) coloring - reused below for the impact-zone bands so
    # both stay visually consistent with the isoline legend.
    cat_color = {}
    for cat in sorted(isolines["iso_cat_merged"].dropna().unique()):
        cat_color[cat] = isolines.loc[isolines["iso_cat_merged"] == cat, "color"].iloc[0]

    # Impact-zone extent: translucent bands, one per trip time, drawn
    # largest/farthest first so nearer bands layer visibly on top - behind
    # everything else (buildings, parks, isolines).
    if params.get("zones_folder"):
        zones_format = params.get("zones_format", "geojson")
        for trip_time in sorted(params["trip_times"], reverse=True):
            color = cat_color.get(float(trip_time))
            if color is None:
                continue
            zone = _read_zone(params["zones_folder"], zones_format, trip_time)
            zone = zone.to_crs(epsg_metric)
            zone.plot(
                    ax=ax, color=color, alpha=0.18,
                    edgecolor=color, linewidth=1, zorder=0.4
                    )

    if params.get("buildings_geojsonfile"):
        buildings = gpd.read_file(params["buildings_geojsonfile"]).to_crs(epsg_metric)
        buildings.plot(ax=ax, color="black", edgecolor="none", zorder=1)

    # "" (or the field being absent) means "no selection" - one config file
    # toggles the single-park highlight rather than needing a separate one.
    highlight_id = params.get("highlight_id") or None
    id_column = params.get("id_column", "poly_id")
    highlighted_park = None
    if params.get("parks_geojsonfile"):
        parks = gpd.read_file(params["parks_geojsonfile"]).to_crs(epsg_metric)
        if highlight_id is not None:
            is_highlighted = parks[id_column].astype(str) == str(highlight_id)
            highlighted_park = parks.loc[is_highlighted]
            parks = parks.loc[~is_highlighted]
        parks.plot(ax=ax, color="#1a7a3c", edgecolor="#0f4d24", linewidth=0.5, zorder=2)

    # Each street segment already carries its own accessibility color
    # (Viridis, assigned by Accessibility) - use it directly, don't
    # re-derive/re-bin colors here.
    isolines.plot(ax=ax, color=isolines["color"], linewidth=linewidth, zorder=3)

    # Drawn last/on top so the selected park is never hidden by isolines.
    if highlighted_park is not None and not highlighted_park.empty:
        highlighted_park.plot(
                ax=ax, color=_HIGHLIGHT_FILL, edgecolor=_HIGHLIGHT_EDGE,
                linewidth=2, zorder=4
                )

    # Legend built from the distinct (iso_cat_merged, color) pairs actually
    # present in the data, so it always matches what's drawn regardless of
    # how many trip_times the isochrone computation used.
    legend_elements = []
    if 0.0 in cat_color:
        legend_elements.append(
            Line2D([0], [0], color=cat_color[0.0], lw=3, label="0 min (on site)")
        )
    prev = 0
    for cat in sorted(c for c in cat_color if c != 0.0):
        legend_elements.append(
            Line2D([0], [0], color=cat_color[cat], lw=3, label=f"{int(prev)}-{int(cat)} min")
        )
        prev = cat

    if highlighted_park is not None and not highlighted_park.empty:
        legend_elements.append(
            Patch(facecolor=_HIGHLIGHT_FILL, edgecolor=_HIGHLIGHT_EDGE, label="Selected park")
        )

    minx, miny, maxx, maxy = isolines.total_bounds
    pad = max(maxx - minx, maxy - miny) * 0.03
    ax.set_xlim(minx - pad, maxx + pad)
    ax.set_ylim(miny - pad, maxy + pad)
    ax.set_axis_off()
    ax.set_title(title, fontsize=14)
    ax.legend(handles=legend_elements, loc="lower left", frameon=True, title="Walking time")

    output_path = os.path.join(output_folder, params["output_png"])
    fig.savefig(output_path, dpi=600, bbox_inches="tight")
    plt.close(fig)

    logger.info(
                """
                | visualization.plot_isochrones |
                | run |

                Render isochrone map:
                    Isolines: {}
                    Total time : {}
                """.format(
                    len(isolines),
                    _get_duration(start)
                )
                )
    logger.info(
                """
                | visualization.plot_isochrones |
                | run |

                TOTAL PROCESS:
                    Total time : {}
                """.format(
                    _get_duration(start_process)
                )
                )

    return {"output_path": output_path}


if __name__ == "__main__":
    text = """
    Render isochrone isolines colored by accessibility distance
    """
    parser = argparse.ArgumentParser(description=text)
    parser.add_argument("json_config")
    args = parser.parse_args()
    run(args.json_config)
