#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract roofs, slopes and buildings from a directory of CityGML files.

Usage: citygml.py [<json_params>]

  -h --help  Show this screen.

"""
import argparse
import glob
import json
import os
import time

import geopandas as gpd
import pandas as pd
from jsonschema import validate

from ..logger.logger import logger, _get_duration
from .analyseroofs import GetRoofsAndSlopes
from .schema import CITYGML_SCHEMA

EXTENSIONS = {
        "GeoJSON": ".geojson",
        "ESRI Shapefile": ".shp",
        "GPKG": ".gpkg",
        }


def run(json_params):
    """
    Description
    ------------

    Parse every CityGML (.gml) file in a directory with
    citygml.analyseroofs.GetRoofsAndSlopes, merge the per-file roofs/grounds/
    buildings results into single outputs for the whole area, and optionally
    select roofs meeting solar/installation-potential thresholds (minimum
    width, compactness, area, maximum slope), mirroring the UC_Parks
    dashboard's manual workflow.

    Returns
    --------

    dict with the written file paths and building/roof/selection counts.

    Parameters
    -----------

    - json_params (str):
        - Complete path to a JSON parameters file, see
          citygml.schema.CITYGML_SCHEMA
        - Fields:
            - gml_dir (str): directory containing one or more *.gml files
              (e.g. one per city district)
            - epsg_in (number): CRS of the CityGML coordinates
            - epsg_out (number): CRS to reproject roofs/grounds into
            - output_folder (str)
            - driver (str, optional): output format for merged files,
              default "GeoJSON", choices "GeoJSON"/"ESRI Shapefile"/"GPKG"
            - palette (str, optional): color palette for slope categories,
              default "viridis", choices viridis/magma/plasma
            - attributes (array, optional): building attribute names used
              to qualify public_access, default []
            - selection (object, optional): if present, filter the merged
              roofs by "roof potential" thresholds and write a
              selection.<ext> file
                - min_width (number, optional): minimum min_width (meters)
                - compactness (number, optional): minimum compactness ratio
                - area (number, optional): minimum roof area (m^2)
                - max_slope (number, optional): maximum roof slope (degrees)
    """
    start_process = time.time()
    with open(json_params) as f:
        params = json.load(f)

    validate(instance=params, schema=CITYGML_SCHEMA)

    gml_dir = params["gml_dir"]
    epsg_in = params["epsg_in"]
    epsg_out = params["epsg_out"]
    output_folder = params["output_folder"]
    os.makedirs(output_folder, exist_ok=True)

    driver = params.get("driver", "GeoJSON")
    palette = params.get("palette", "viridis")
    attributes = params.get("attributes", [])
    extension = EXTENSIONS[driver]

    per_file_dir = os.path.join(output_folder, "per_file")
    os.makedirs(per_file_dir, exist_ok=True)

    gml_files = sorted(glob.glob(os.path.join(gml_dir, "*.gml")))

    start = time.time()
    list_gdf_roofs = []
    list_gdf_grounds = []
    list_df_buildings = []
    for gml_file in gml_files:
        name = os.path.splitext(os.path.basename(gml_file))[0]
        result = GetRoofsAndSlopes(
                gml_file,
                epsg_in,
                epsg_out,
                name=name,
                out_dir=per_file_dir,
                palette=palette,
                driver=driver,
                attributes=attributes,
                )
        list_gdf_roofs.append(result.gdf_roofs)
        list_gdf_grounds.append(result.gdf_grounds)
        list_df_buildings.append(result.df_buildings)

    logger.info(
                """
                | citygml.citygml |
                | run |

                Parse CityGML files:
                    Files: {}
                    Total time : {}
                """.format(
                    len(gml_files),
                    _get_duration(start)
                )
                )

    start = time.time()
    gdf_roofs = gpd.GeoDataFrame(
            pd.concat(list_gdf_roofs, ignore_index=True),
            crs=list_gdf_roofs[0].crs
            )
    gdf_grounds = gpd.GeoDataFrame(
            pd.concat(list_gdf_grounds, ignore_index=True),
            crs=list_gdf_grounds[0].crs
            )
    df_buildings = pd.concat(list_df_buildings)

    roofs_path = os.path.join(output_folder, "roofs" + extension)
    grounds_path = os.path.join(output_folder, "grounds" + extension)
    buildings_path = os.path.join(output_folder, "buildings.json")

    if os.path.exists(roofs_path):
        os.remove(roofs_path)
    if os.path.exists(grounds_path):
        os.remove(grounds_path)

    gdf_roofs.to_file(roofs_path, driver=driver, encoding="utf-8")
    gdf_grounds.to_file(grounds_path, driver=driver, encoding="utf-8")

    data = df_buildings.to_json(orient="index")
    with open(buildings_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    logger.info(
                """
                | citygml.citygml |
                | run |

                Merge and write outputs:
                    Buildings: {}
                    Roofs: {}
                    Total time : {}
                """.format(
                    len(df_buildings),
                    len(gdf_roofs),
                    _get_duration(start)
                )
                )

    selection_path = None
    n_selected = 0
    selection_params = params.get("selection")
    if selection_params:
        start = time.time()
        mask = pd.Series(True, index=gdf_roofs.index)
        if "min_width" in selection_params:
            mask &= gdf_roofs["min_width"] >= selection_params["min_width"]
        if "compactness" in selection_params:
            mask &= gdf_roofs["compactness"] >= selection_params["compactness"]
        if "area" in selection_params:
            mask &= gdf_roofs["area"] >= selection_params["area"]
        if "max_slope" in selection_params:
            mask &= gdf_roofs["angles"] <= selection_params["max_slope"]

        gdf_selection = gdf_roofs.loc[mask]
        n_selected = len(gdf_selection)

        selection_path = os.path.join(output_folder, "selection" + extension)
        if os.path.exists(selection_path):
            os.remove(selection_path)
        gdf_selection.to_file(selection_path, driver=driver, encoding="utf-8")

        pct = 100 * n_selected / len(gdf_roofs) if len(gdf_roofs) else 0
        area_selected = gdf_selection["area"].sum()
        area_total = gdf_roofs["area"].sum()
        pct_area = 100 * area_selected / area_total if area_total else 0

        logger.info(
                    """
                    | citygml.citygml |
                    | run |

                    Roof selection (potential):
                        Roofs selected: {} / {} ({:.1f}%)
                        Area selected: {:.1f} / {:.1f} m2 ({:.1f}%)
                        Total time : {}
                    """.format(
                        n_selected,
                        len(gdf_roofs),
                        pct,
                        area_selected,
                        area_total,
                        pct_area,
                        _get_duration(start)
                    )
                    )

    logger.info(
                """
                | citygml.citygml |
                | run |

                TOTAL PROCESS:
                    Total time : {}
                """.format(
                    _get_duration(start_process)
                )
                )

    output = {
            "roofs_path": roofs_path,
            "grounds_path": grounds_path,
            "buildings_path": buildings_path,
            "n_buildings": len(df_buildings),
            "n_roofs": len(gdf_roofs),
            "n_selected": n_selected,
            }
    if selection_path is not None:
        output["selection_path"] = selection_path
    return output


if __name__ == "__main__":
    text = """
    Extract roofs, slopes and buildings from a directory of CityGML files
    """
    parser = argparse.ArgumentParser(description=text)
    parser.add_argument("json_config")
    args = parser.parse_args()
    run(args.json_config)
