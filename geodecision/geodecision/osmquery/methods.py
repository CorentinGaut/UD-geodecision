#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 25 11:50:32 2019

@author: thomas
"""

#import overpass
import argparse
import os
import time

import osmnx as ox
import geojson
import json
import geopandas as gpd
from jsonschema import validate

from ..graph.utils import islist
from ..logger.logger import logger, _get_duration
from .schema import POLYGON_QUERY_SCHEMA

#def get_OSM_poly(
#        bbox, 
#        key, 
#        value="all", 
#        timeout=40,
#        endpoint="https://overpass-api.de/api/interpreter",
#        gdf=True
#        ):
#    """
#    Description
#    -----------
#    Get OSM data with key/value pair and that is Polygon by making
#    queries on Overpass
#    
#    Return
#    ------
#    GeoJSON Polygons FeatureCollection
#    
#    Parameters
#    ----------
#    - bbox(tuple):
#        - bounding box for the query
#        - must be (SOUTH, WEST, NORTH, EAST)
#        - must be EPSG 4326 (WGS84) projection
#        - ex: (45.772, 4.864, 45.778, 4.875)
#    - key(str):
#        - key for the OSM query
#    - value(str):
#        - value for the OSM query
#    - timeout(int):
#        - time in seconds for the timeout
#        - default: 40
#    - endpoint(str):
#        - endpoint for the queries
#        - default: "https://overpass-api.de/api/interpreter"
#    - gdf(boolean):
#        - if GeoDataFrame for output
#        - default: True
#    """
#    
#    #if bbox is list, transform to tuple
#    if isinstance(bbox, list):
#        bbox = tuple(bbox)
#    api = overpass.API(
#            timeout=timeout, 
#            endpoint=endpoint
#            )
#    if value == "all":
#        requ =  """
#        (
#            node["{0}"]{1};
#            way["{0}"]{1};
#            relation["{0}"]{1};
#        );
#        (._;>;);
#        out geom;
#        """.format(key,bbox)
#    else:
#        requ =  """
#        (
#            node["{0}"="{1}"]{2};
#            way["{0}"="{1}"]{2};
#            relation["{0}"="{1}"]{2};
#        );
#        (._;>;);
#        out geom;
#        """.format(key, value,bbox)
#        
#    data = api.get(requ, verbosity='geom', responseformat="geojson")
#    polys_geojson = _from_lines_to_polys(data, key, value)
#    
#    if gdf == True:
#        polys = gpd.GeoDataFrame.from_features(polys_geojson)
#        polys = polys.dropna(axis=1, how='all')
#        polys.crs = {"init":"epsg:4326"}
#        #Try to avoid wrong geometry by buffering with 0
#        polys["new_geom"] = polys["geometry"].buffer(0) 
#        polys = polys.rename(
#                columns={
#                        "geometry":"old_geometry"
#                        }
#                )
#        polys = polys.rename(
#                columns={
#                        "new_geom":"geometry"
#                        }
#                ).set_geometry("geometry")
#        polys.drop("old_geometry", inplace=True, axis=1)
#        
#        return polys
#    
#    else:
#        return polys_geojson

# Try to avoid using overpass that is not a conda package
# Try to use osmnx instead
# TODO: remove commented section above if not needed after changes

def get_OSM_poly(
        bbox, 
        key, 
        value="all"
        ):
    """
    Description
    -----------
    Get OSM data with key/value pair and that is Polygon by making
    queries on Overpass
    
    Return
    ------
    GeoDataFrame
    
    Parameters
    ----------
    - bbox(tuple):
        - bounding box for the query
        - must be (SOUTH, WEST, NORTH, EAST)
        - must be EPSG 4326 (WGS84) projection
        - ex: (45.772, 4.864, 45.778, 4.875)
    - key(str):
        - key for the OSM query
    - value(str):
        - value for the OSM query
    """
    
    #Get GDF using osmnx (features_from_bbox replaces the removed
    # ox.footprints.create_footprints_gdf; bbox order for osmnx is
    # (west, south, east, north))
    tags = {key: True} if value == "all" else {key: value}
    gdf = ox.features_from_bbox(
            bbox=(bbox[1], bbox[0], bbox[3], bbox[2]),
            tags=tags
            )

    #Keep only polygon geometries
    gdf = gdf[gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]

    #Filter if necessary
    if value != "all":
        gdf = gdf.loc[gdf[key] == value]

    #Remove columns containing lists (to avoid Fiona writing crashes)
    for col in gdf.columns:
        if isinstance(gdf[col].iloc[0], list):
            gdf.drop(col, axis=1, inplace=True)

    return gdf
    

def _add_feature(features, feature):
    """
    
    """
    if len(feature.geometry["coordinates"]) > 3:
        geometry = geojson.Polygon(
            [
                feature.geometry["coordinates"]
            ]
        )
        feature.properties.update({"osm_id":feature.id})
        new_feature = geojson.Feature(
            geometry = geometry,
            properties = feature.properties
        )
        features.append(new_feature)
            
    return features

def _from_lines_to_polys(data, key, value):
    """
    Description
    -----------
    Transform OSM data from LineStrings to Polygons
    
    Return
    ------
    GeoJSON Polygons FeatureCollection
    
    Parameters
    ----------
    - data(json):
        - json from OSM query
    - key(str):
        - key used for the OSM query
    - value(str):
        - value used for the OSM query
    """
    data = geojson.loads(json.dumps(data))
    features = []
    for feature in data.features:
        if (feature.geometry["type"] == "LineString"):
            if value == "all":
                features = _add_feature(features, feature)
            else:
                if (
                    key in feature.properties and feature.properties[key] == value
                ):
                    features = _add_feature(features, feature)

    return geojson.FeatureCollection(features)


def run(json_params):
    """
    Description
    ------------

    Fetch a single OSM polygon layer (key/value) for a bounding box and
    write it to a GeoJSON file with a generated unique id column, ready to
    be used directly as accessibility.accessibility.run()'s
    polygons_geojsonfile/id_column.

    Returns
    --------

    dict with the written file path and feature count.

    Parameters
    -----------

    - json_params (str):
        - Complete path to a JSON parameters file, see
          osmquery.schema.POLYGON_QUERY_SCHEMA
        - Fields:
            - bbox (array): [SOUTH, WEST, NORTH, EAST] in EPSG:4326
            - osm_key (str): OSM tag key, e.g. "leisure", "building"
            - osm_value (str): OSM tag value to filter on, default "all"
            - epsg_origin (number): output CRS, default 4326
            - output_folder (str)
            - polygons_geojsonfile (str): output filename
            - id_column (str): name of the unique id column to generate,
              default "poly_id" (kept distinct from "unique_id", which
              GetSplitNodes/ConnectPoints use for their own generated ids)
    """
    start_process = time.time()
    with open(json_params) as f:
        params = json.load(f)

    validate(instance=params, schema=POLYGON_QUERY_SCHEMA)

    output_folder = params["output_folder"]
    os.makedirs(output_folder, exist_ok=True)

    osm_value = params.get("osm_value", "all")
    epsg_origin = params.get("epsg_origin", 4326)
    # Note: GetSplitNodes/ConnectPoints already use the column name
    # "unique_id" for their own generated split-point ids, so default to a
    # different name here to avoid confusion between the two.
    id_column = params.get("id_column", "poly_id")

    start = time.time()
    gdf = get_OSM_poly(params["bbox"], params["osm_key"], value=osm_value)
    # get_OSM_poly returns a (element, id) multiindex from osmnx - flatten
    # it into a unique string id column, and drop geometry duplicates that
    # can occur when a feature matches more than one OSM element type.
    gdf = gdf.reset_index()
    gdf[id_column] = gdf["element"].astype(str) + "_" + gdf["id"].astype(str)
    gdf = gdf.drop_duplicates(subset="geometry")
    gdf = gdf.set_crs(4326, allow_override=True)
    if epsg_origin != 4326:
        gdf = gdf.to_crs(epsg_origin)

    logger.info(
                """
                | osmquery.methods |
                | run |

                Fetch OSM polygons ({}={}):
                    Features: {}
                    Total time : {}
                """.format(
                    params["osm_key"],
                    osm_value,
                    len(gdf),
                    _get_duration(start)
                )
                )

    output_path = os.path.join(output_folder, params["polygons_geojsonfile"])
    if os.path.exists(output_path):
        os.remove(output_path)
    gdf.to_file(output_path, driver="GeoJSON")

    logger.info(
                """
                | osmquery.methods |
                | run |

                TOTAL PROCESS:
                    Total time : {}
                """.format(
                    _get_duration(start_process)
                )
                )

    return {"polygons_path": output_path, "n_features": len(gdf)}


if __name__ == "__main__":
    text = """
    Fetch an OSM polygon layer for a bounding box
    """
    parser = argparse.ArgumentParser(description=text)
    parser.add_argument("json_config")
    args = parser.parse_args()
    run(args.json_config)