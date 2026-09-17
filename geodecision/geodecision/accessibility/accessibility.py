#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#Created on Mon Sep 16 14:08:39 2019
#@author: thomas


"""Get Accessibility and Mask layers.

Usage: get_accessibility_and_mask.py [<json_params>]

  -h --help  Show this screen.
  -i         Parameters JSON file

"""
import argparse
from jsonschema import validate
#from shapely.ops import cascaded_union
#from shapely import speedups
import json
import geopandas as gpd
import os
import time
import networkx as nx

from ..logger.logger import logger, _get_duration
from .schema import ACCESS_SCHEMA
from .isochrone import Accessibility
from ..graph.utils import graph_to_gdf_points, df_to_graph, graph_to_df
from ..graph.semanticentries import GetSemanticEntries
from ..graph.connectpoints import ConnectPoints
from ..osmquery.methods import get_OSM_points
from ..spatialops.operations import SpatialOperations

#speedups.enable()

#Dict of results
results = {}


def erase_file(name):
    """
    Description
    ------------
    
    Check if a file exists and delete it
    
    Returns
    --------
    
    None
    
    Parameters
    -----------
    
    - name (str):
        - complete path file name
    """
    try:
        os.remove(name)
    except OSError:
        pass
    
def delete_list_cols(df):
    """
    Description
    ------------
    
    Delete columns containing lists in DataFrame or GeoDataFrame
    
    Returns
    --------
    
    New DataFrame or GeoDataFrame without columns containing lists
    
    Parameters
    -----------
    
    - df (DataFrame or GeoDataFra
    """
    columns = []
    for col in df.columns:
        df["tmp"] = df[col].map(lambda x: isinstance(x,list))
        if True not in df["tmp"]:
            columns.append(col)
    
    return df[columns]
    
def write_results(results, output_folder, output_format="geopackage"):
    """
    Description
    ------------
    
    Write all the results in set format(s)
    
    Returns
    --------
    
    None
    
    Parameters
    -----------
    
    - results (object):
        - results object from Accessibility class
    - output_folder (str):
        - Path to the folder to write files
    - output_format (str):
        - format of the output files
        - Default: "geopackage"
        - Options: 
            - "geopackage"
            - "geojson"
    """
    encoding = "utf-8"
    if (output_format == "geojson"):
        extension = ".geojson"
        driver = "GeoJSON"
        
        for layer, data in results.items():
            if hasattr(data, "columns"):
                if "geometry" in data.columns:
                    name = os.path.join(
                                output_folder, 
                                str(layer) + extension
                                )
                    #Delete file if already exist to avoid errors
                    erase_file(name)
                    #Delete columns containing lists before writing
                    data = delete_list_cols(data)
                    
                    try:
                        data.to_file(
                                name, 
                                driver=driver,
                                encoding=encoding
                                )
                    except:
                        cant_write = "CAN'T WRITE FILE: " + str(layer)
                        logger.info(cant_write)
        
    elif output_format == "geopackage":
        name = os.path.join(output_folder, "output.gpkg")
        #Delete file if already exist to avoid errors
        erase_file(name)
        
        for layer, data in results.items():
            #Write only if existing geometry
            if hasattr(data, "columns"):
                if "geometry" in data.columns:
                    data.to_file(
                            name,
                            layer = str(layer),
                            driver="GPKG",
                            encoding=encoding
                            )
        

def run(json_params):
    """
    Description
    ------------
    
    Run all the scripts based on input parameters and write output files
    
    Returns
    --------
    
    Results (object from Accessibility class)
    
    Parameters
    -----------
    
    - json_params (str):
        - Complete path file name to JSON parameters file
        - ex: "./parameters/Lyon/test_params.json"
    """
    
    start_process = time.time() #required for log
    #Load params JSON file
    with open(json_params) as f:
        params = json.load(f)
        
    
    #Set output
    output_folder = params["output_folder"]
    output_format = params["output_format"]
    
    #Check with schema
    validate(instance=params, schema=ACCESS_SCHEMA)
    
    start = time.time()
    #Get polygons as GeoDataFrame
    gdf_features = gpd.read_file(params["polygons_geojsonfile"])
    #Optionally scope the run to a single feature (e.g. one park) instead
    # of pooling every feature in polygons_geojsonfile together.
    # "" (or the field being absent) means "no selection" - one config file
    # toggles between the two modes rather than needing a separate one.
    select_id = params.get("select_id") or None
    if select_id is not None:
        gdf_features = gdf_features.loc[
                gdf_features[params["id_column"]].astype(str) == str(select_id)
                ]
        if gdf_features.empty:
            raise ValueError(
                    "No feature with {!r} == {!r} in {!r}".format(
                            params["id_column"],
                            select_id,
                            params["polygons_geojsonfile"]
                            )
                    )
    #Drop duplicates based on geometry
    gdf_features = gdf_features.drop_duplicates(subset="geometry")
    gdf_features = gdf_features.to_crs(
            "EPSG:{}".format(
                    params["epsg_metric"]
                    )
            )
    
    logger.info(
                """"
                Get Polygons GeoDataFrame and project to metric:
                    Total time : {}
                """.format(
                    _get_duration(start)
                )
                )
    
    start = time.time()
    #Get real semantic entry points (OSM entrance=*/barrier=gate nodes)
    # near each park's boundary, falling back to the geometric splitter
    # (segments of a set distance in meters) for parks with too few real
    # matches, so every park still gets entry nodes to connect to the
    # graph (*edges*).
    entrance_buffer_dist = params.get("entrance_buffer_dist", 15)
    query_geom = gdf_features["geometry"].unary_union.buffer(entrance_buffer_dist)
    minx, miny, maxx, maxy = gpd.GeoSeries(
            [query_geom], crs=gdf_features.crs
            ).to_crs(4326).total_bounds
    bbox = (miny, minx, maxy, maxx)

    try:
        osm_points = get_OSM_points(
                bbox, tags={"entrance": True, "barrier": "gate"}
                )
        # osmnx returns a (element, id) MultiIndex - flatten it into a
        # readable, unique "osm_id" column (same pattern as
        # osmquery.methods.run()'s id_column construction).
        osm_points = osm_points.reset_index()
        osm_points["osm_id"] = (
                osm_points["element"].astype(str) + "_" + osm_points["id"].astype(str)
                )
        osm_points_metric = osm_points.to_crs(gdf_features.crs)
    except Exception as e:
        logger.info(
                "Could not fetch OSM entrance/gate points, falling back "
                "to fully synthetic entries: {}".format(e)
                )
        osm_points_metric = None

    polygons_points_metric = GetSemanticEntries(
            gdf_features,
            osm_points_metric,
            params["dist_split"],
            params["id_column"],
            entrance_buffer_dist=entrance_buffer_dist,
            min_entries_per_park=params.get("min_entries_per_park", 2)
            ).get_entries()

    #Keep only desired columns
    ## force-keep "unique_id" and the semantic entry columns, the same
    ## way "unique_id" was already unconditionally kept
    for col in ("unique_id", "entry_source", "entry_tag"):
        if col not in params["columns_to_keep"]:
            params["columns_to_keep"].append(col)
    polygons_points_metric = polygons_points_metric[params["columns_to_keep"]]
    
    logger.info(
        """
        | get_accessibility.py | 
        | run |
        
        Splitter:
            Total time : {}
        """.format(
            _get_duration(start)
        )
    )
    
    #Import graph from json files and transform to NetworkX MultiDiGraph
    start = time.time()
    G = df_to_graph(
            params["graph_edges_jsonfile"], 
            params["graph_nodes_jsonfile"]
            )
    
    logger.info(
                """
                Import Graph:
                    Total time : {}
                """.format(
                    _get_duration(start)
                )
                )
    
       
    start = time.time()
    #Get points and lines GeoDataFrames from Graph
    # graph_to_gdf_points's signature is (G, lon, lat, epsg, ...) - pass by
    # keyword to avoid the positional lat/lon mixup that used to be here
    # (params["lat"]/params["lon"] were passed in lon/lat argument order,
    # silently building Point(lat, lon) instead of Point(lon, lat)).
    gdf_pts, gdf_lines = graph_to_gdf_points(
            G,
            lon=params["lon"],
            lat=params["lat"],
            epsg=params["epsg_graph"],
            get_lines=True
            )
    #To metric
    gdf_pts_metric = gdf_pts.to_crs(
            "EPSG:{}".format(params["epsg_metric"])
            )
    gdf_lines_metric = gdf_lines.to_crs(
            "EPSG:{}".format(params["epsg_metric"])
            )
    
    logger.info(
        """
        | get_accessibility.py | 
        | run |
        
        Get lines and points GeoDataFrames:
            Total time : {}
        """.format(
            _get_duration(start)
        )
    )
        
    start = time.time()
    #Get the updated nodes and edges (nodes from splitting polygons exterior
    # LineStrings)
    #Connexion and get updated nodes and edges
    nodes, edges, non_valid_nodes = ConnectPoints(
            polygons_points_metric, 
            gdf_pts_metric, 
            gdf_lines_metric,
            params["access_type"],
            params["prefix"],
            key_col="unique_id",
            path = None,
            threshold= params["threshold"], 
            knn=params["knn"],
            distance=params["distance"]
        ).process()
    
    logger.info(
        """
        | get_accessibility.py | 
        | run |
        
        Make connections :
            Total time : {}
        """.format(
            _get_duration(start)
        )
    )
    
    start = time.time()
    #Measure accessibility
    ## Get updated Graph from new edges and nodes
    updated_G = df_to_graph(edges, nodes, driver="gdf")
    
    #TODO: remove this and write G (nodes and edges) and points, lines after update
    results["nodes"] = nodes
    results["edges"] = edges
    
    ## Get starting nodes for isochrones
    starting_nodes = nodes.loc[
            nodes["access_type"] == params["access_type"]
            ]["osmid"].to_list()
#    starting_nodes = [
#            node for node in starting_nodes if node not in non_valid_nodes
#            ]
    logger.info(
                """"
                Get starting nodes:
                    Total time : {}
                """.format(
                    _get_duration(start)
                )
                )
    start = time.time()
    #Get accessibility
    start = time.time()
    access = Accessibility(
            updated_G, 
            params["trip_times"], 
            params["distance_buffer"],
            params["weight"],
            starting_nodes,
            gdf_features["geometry"].unary_union,
            epsgs = {
                "origin":params["epsg_input"],
                "metric":params["epsg_metric"],
                "vis":3857
                }
            )
    access.get_results()
    results["updated_graph"] = access.G
    results["problematic_nodes"] = nodes.loc[
            nodes["osmid"].isin(
                    access.pb_nodes
                    )
            ]
    
    logger.info(
                """
                | get_accessibility.py | 
                | run |
        
                Get accessibility:
                    Total time : {}
                """.format(
                    _get_duration(start)
                )
                )    
    
    start = time.time()
    #Add to results
    #TODO REMOVE COMMENT IF BUFFERED ISOLINES WITH NO UNION NEEDED
    ##BECAUSE IT PRODUCES A REALLY HEAVY FILE NOT NECESSERALY NEEDED
    results[params["output_isolines_layername"]] = access.lines
#    results[
#            params["output_buffered_isolines_layername"]
#            ] = access.buffered
    results[
            params["output_buffered_isolines_union_layername"]
            ] = access.union
    
    
    ## Spatial operations
    dict_unions = SpatialOperations(
            params["trip_times"], 
            gdf_features, 
            access.union,
            "iso_cat_merged",
            epsg=params["epsg_metric"],
            tolerance=params["tolerance"]
            ).dict_unions
    
    results.update(dict_unions)        
        
    logger.info(
                """"
                | get_accessibility.py | 
                | run |
                
                Making layers:
                    Total time : {}
                """.format(
                    _get_duration(start)
                )
                )    
    
    #Write spatial outputs
    start = time.time()    
    write_results(
            results, 
            output_folder=output_folder, 
            output_format=output_format
            )
    
    #Write updated graph files (nodes and edges)
    graph_to_df(
            results["updated_graph"], 
            os.path.join(output_folder, "updated_edges.json"), 
            os.path.join(output_folder, "updated_nodes.json")
            )
    
    #Write problematic nodes
    with open(os.path.join(output_folder, "problematic_nodes.json"),"w") as f:
        json.dump(
                gpd.pd.DataFrame(
                        results["problematic_nodes"]
                        ).to_json(orient="records"), f
                )
    
    logger.info(
                """"
                | get_accessibility.py | 
                | run |
                
                Writing files:
                    Total time : {}
                """.format(
                    _get_duration(start)
                )
                )
                
    logger.info(
                """"
                TOTAL PROCESS:
                    Total time : {}
                """.format(
                    _get_duration(start_process)
                )
                )

    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    text = """
    Get accessibility measures & masks
    """
    parser = argparse.ArgumentParser(description = text)
    parser.add_argument("json_config")
    args = parser.parse_args()
    run(args.json_config)