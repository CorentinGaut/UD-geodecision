#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quantify the impact zone of a park (or any polygon feature).

For each trip-time band already computed by
`geodecision.accessibility.accessibility.run()` (its cumulative,
park-merged zone polygons - see `SpatialOperations.dict_unions`), this
module intersects that zone with a buildings layer and reports how many
buildings, and how much building footprint area, fall inside it.

Usage: impact_zone.py [<json_params>]

  -h --help  Show this screen.

"""
import argparse
import json
import os
import time

import geopandas as gpd
from jsonschema import validate

from ..logger.logger import logger, _get_duration
from ..spatialops.operations import get_intersect_matches
from ..accessibility.accessibility import erase_file, delete_list_cols
from .schema import IMPACT_ZONE_SCHEMA


def _read_zone(zones_folder, zones_format, trip_time):
    """
    Description
    ------------

    Read the zone polygon for one trip time, written by
    accessibility.run() (one GeoDataFrame per trip time, keyed by the
    trip time itself - see SpatialOperations.dict_unions).

    Returns
    --------

    GeoDataFrame

    Parameters
    -----------

    - zones_folder (str):
        - output_folder of the compute-accessibility run to read from
    - zones_format (str):
        - "geojson" or "geopackage", matching that run's output_format
    - trip_time (int):
        - trip time to read the zone polygon for
    """
    if zones_format == "geojson":
        path = os.path.join(zones_folder, "{}.geojson".format(trip_time))
        return gpd.read_file(path)
    elif zones_format == "geopackage":
        path = os.path.join(zones_folder, "output.gpkg")
        return gpd.read_file(path, layer=str(trip_time))
    else:
        raise ValueError(
                "Unknown zones_format: {!r} (expected 'geojson' or "
                "'geopackage')".format(zones_format)
                )


def write_results(results, output_folder, output_format="geojson"):
    """
    Description
    ------------

    Write per-trip-time buildings-in-zone layers, in set format(s).
    Mirrors accessibility.write_results().

    Returns
    --------

    None

    Parameters
    -----------

    - results (dict):
        - {layer_name: GeoDataFrame}
    - output_folder (str):
        - Path to the folder to write files
    - output_format (str):
        - "geojson" or "geopackage"
        - Default: "geojson"
    """
    encoding = "utf-8"
    if output_format == "geojson":
        for layer, data in results.items():
            name = os.path.join(output_folder, str(layer) + ".geojson")
            erase_file(name)
            data = delete_list_cols(data)
            data.to_file(name, driver="GeoJSON", encoding=encoding)

    elif output_format == "geopackage":
        name = os.path.join(output_folder, "impact_zone.gpkg")
        erase_file(name)
        for layer, data in results.items():
            data.to_file(
                    name,
                    layer=str(layer),
                    driver="GPKG",
                    encoding=encoding
                    )


def run(json_params):
    """
    Description
    ------------

    Quantify, for each trip-time zone from a prior compute-accessibility
    run, how many buildings (and how much building footprint area) fall
    inside it.

    Returns
    --------

    dict with a "summary" list (one entry per trip time) and the written
    per-trip-time buildings-in-zone GeoDataFrames

    Parameters
    -----------

    - json_params (str):
        - Complete path to a JSON parameters file, see
          impact.schema.IMPACT_ZONE_SCHEMA
    """
    start_process = time.time()
    with open(json_params) as f:
        params = json.load(f)

    validate(instance=params, schema=IMPACT_ZONE_SCHEMA)

    output_folder = params["output_folder"]
    os.makedirs(output_folder, exist_ok=True)

    epsg_metric = params["epsg_metric"]
    trip_times = sorted(params["trip_times"])

    start = time.time()
    gdf_buildings = gpd.read_file(params["buildings_geojsonfile"])
    gdf_buildings = gdf_buildings.to_crs("EPSG:{}".format(epsg_metric))
    gdf_buildings = gdf_buildings.reset_index(drop=True)
    gdf_buildings["building_area"] = gdf_buildings.geometry.area

    logger.info(
                """
                | impact_zone.py |
                | run |

                Read buildings:
                    Features: {}
                    Total time : {}
                """.format(
                    len(gdf_buildings),
                    _get_duration(start)
                )
                )

    results = {}
    summary = []
    for trip_time in trip_times:
        start = time.time()

        gdf_zone = _read_zone(
                params["zones_folder"], params["zones_format"], trip_time
                )
        gdf_zone = gdf_zone.to_crs("EPSG:{}".format(epsg_metric))
        zone_geom = gdf_zone.geometry.unary_union

        matches = get_intersect_matches(
                zone_geom, gdf_buildings, geom_col="geometry"
                )
        gdf_matched = gdf_buildings.loc[matches].copy()
        gdf_matched["trip_time"] = trip_time

        layer_name = "impact_zone_{}".format(trip_time)
        results[layer_name] = gdf_matched

        summary.append({
                "trip_time": trip_time,
                "n_buildings": len(gdf_matched),
                "building_area_m2": float(gdf_matched["building_area"].sum()),
                "zone_area_m2": float(zone_geom.area),
                })

        logger.info(
                """
                | impact_zone.py |
                | run |

                Impact zone for {} minutes:
                    Buildings: {}
                    Total time : {}
                """.format(
                    trip_time,
                    len(gdf_matched),
                    _get_duration(start)
                )
                )

    start = time.time()
    write_results(
            results,
            output_folder=output_folder,
            output_format=params["output_format"]
            )

    with open(os.path.join(output_folder, "impact_zone_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    logger.info(
                """
                | impact_zone.py |
                | run |

                Writing files:
                    Total time : {}
                """.format(
                    _get_duration(start)
                )
                )

    logger.info(
                """
                | impact_zone.py |
                | run |

                TOTAL PROCESS:
                    Total time : {}
                """.format(
                    _get_duration(start_process)
                )
                )

    results["summary"] = summary
    return results


if __name__ == "__main__":
    text = """
    Quantify the impact zone of a park (buildings served per trip time)
    """
    parser = argparse.ArgumentParser(description=text)
    parser.add_argument("json_config")
    args = parser.parse_args()
    run(args.json_config)
