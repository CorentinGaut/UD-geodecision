#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 11 16:15:41 2019

@author: thomas
"""

from pyproj import Transformer
from shapely.geometry import Point, LineString
from collections import namedtuple
import pandas as pd
import geopandas as gpd
import networkx as nx
import json
import numpy as np


Points = namedtuple("Points",["coordinates","geometry"])

def islist(x, columns):
    """
    Description
    ------------
    
    Check if (Geo)DataFrame cell is list for each columns. 
    Useful to avoid writing crashes due to list
    
    Returns
    --------
    
    Boolean 
    
    Parameters
    -----------
    
    - x (cell value of Geo-DataFrame)
    - columns (list):
        - columns to parse
    
    """
    list_ = False
    for col in columns:
        if isinstance(x[col], list):
            list_ = True
    
    return list_


def reproject_points(pts, epsg_in, epsg_out):
    """
    Description
    ------------
    
    Reproject points with pyproj.Transformer
    
    Returns
    --------
    
    Namedtuple Points object with:
        - coordinates: tuple with 2 lists (xs and ys)
        - geometry: list of Shapely Points
    
    Parameters
    -----------
    
    - pts (list of tuples coordinates):
        - List of coordinates
        - ex: [(4.56, 45.8), (4.8, 46.29)]
    - epsg_in (int):
        - Input EPSG
        - ex: 4326
    - epsg_out (int):
        - Output EPSG
        - ex: 2154
    
    """
    
    transformer = Transformer.from_proj(epsg_in, epsg_out)
    xcoords,ycoords = map(list,zip(*pts))
    
    coords = transformer.transform(xcoords, ycoords)
    
    points = [Point(x, y) for x,y in zip(coords[0], coords[1])]
    
    return Points(
            [
                    (x,y) for x,y in zip(
                            coords[0], 
                            coords[1]
                            )
                    ], 
            points
            )


def graph_to_df(graph, edges_path, nodes_path):
    """
    Description
    ------------
    Write json files with edges and nodes
    
    Parameters
    -----------
    - graph(Networkx graph): 
        graph with geometries
    - edges_path(str): 
        complete path with filename for edges
    - nodes_path(str): 
        complete path with filename for nodes
    
    """
    #Get edges and write GeoJSON
    df_edges = nx.to_pandas_edgelist(graph)
    df_edges = df_edges[["source", "target", "time"]]
    df_edges.to_json(edges_path, force_ascii=True, orient="records")

    #Get nodes (get 'x' and 'y' for futur center_nodes operations)
    # and write json to get a dict of nodes attributes
    l_nodes = list(graph.nodes(data=True))
    nodes = dict(l_nodes)
    with open(nodes_path, "w") as fp:
        json.dump(nodes, fp, ensure_ascii=False)
    
def df_to_graph(
        edges_source, 
        nodes_source, 
        source="source", 
        target="target",
        driver="json"
        ):
    """
    Description
    ------------
    Get edges and nodes json files and return G, a Networkx graph
    
    Returns
    --------
    Graph G
    
    Parameters
    -----------
    - edges_source(str OR GeoDataframe): 
        complete path with filename for edges (when driver is "json" or "shp")
        OR GeoDataframe (when driver is "gdf")
    - nodes_source(str OR GeoDataframe): 
        complete path with filename for nodes (when driver is "json" or "shp")
        OR GeoDataframe (when driver is "gdf")
    - source(str): 
        name of source field
        default: "source"
    - target(str): 
        name of target field
        default: "target"
    - driver(str):
        source file type ("json", "shp")
        default: "json"
    """
    
    if driver == "json": 
        df_edges = pd.read_json(edges_source, orient="records")
        dict_edges = df_edges.to_dict(orient="list")
        edges = pd.DataFrame(dict_edges)
        G = nx.from_pandas_edgelist(
                edges, 
                source=source, 
                target=target, 
                edge_attr=True
                )
        
        with open(nodes_source, "r") as fp:
            attrs = json.load(fp)
    
    elif driver == "shp" or driver == "gdf":
        if driver == "shp":
            df_edges = gpd.read_file(edges_source)
            df_nodes = gpd.read_file(nodes_source)
        else:
            df_edges = edges_source
            df_nodes = nodes_source
            
        del df_edges["geometry"]
        G = nx.from_pandas_edgelist(
                df_edges, 
                source=source, 
                target=target, 
                edge_attr=True
                )
        
        del df_nodes["geometry"]
        tmp = df_nodes.to_dict(orient="records")
        attrs = {}
        
        # Create a dict with osmid as key and attr as value in order to 
        ## set node attributes of the output graph
        for attr in tmp:
            attrs[attr["osmid"]] = attr
    
    if driver == "gdf":
        nx.set_node_attributes(G, attrs)
    else:
        new_attrs = {}
        for key,value in attrs.items():
            new_attrs[np.int64(key)] = value
        nx.set_node_attributes(G, new_attrs)
        
    return G

def graph_with_time(G, distance):
    """
    Description
    ------------
    Get edges and nodes json files
    
    Returns
    --------
    Networkx Graph with time distance based on walk distance speed
    
    Parameters
    -----------
    - G (NetworkX graph):
        - Graph based on OSM data (build with Osmnx library)
    - distance(int):
        - distance in meters that could be reached within 1 hour
        - ex: 5000
    """
    meters_per_minute = distance/60

    for u, v, k, data in G.edges(data=True, keys=True):
        data['time'] = data['length'] / meters_per_minute
    
    return G

def graph_to_gdf_points(G, lon, lat, epsg, get_lines=False):
    """
    Description
    ------------
    From Networkx Graph nodes from OSM data, make a GeoDataFrame with Points
    
    Returns
    --------
    Points GeoDataFrame
    
    Parameters
    -----------
    - G (NetworkX graph):
        - Graph based on OSM data (build with Osmnx library)
    - lat(str):
        - name of column with lat coordinates
    - lon(str):
        - name of column with lon coordinates
    - epsg(str):
        - EPSG of coordinates
    - get_lines(bool):
        - if set to True, return points and lines GeoDataFrame
        - default: False
        
    """
    df = pd.DataFrame.from_dict(
            dict(
                    list(
                            G.nodes(data=True)
                            )
                    ), 
            orient="index"
            )
    
    df["tuple"] = list(zip(df[lon], df[lat]))
    df["geometry"] = df["tuple"].map(lambda x: Point(x))
    del df["tuple"]

    # Node ids only live in the index at this point (NetworkX node keys);
    # downstream code (e.g. graph.connectpoints.ConnectPoints) expects an
    # explicit "osmid" column, so expose it here too.
    df["osmid"] = df.index

    gdf = gpd.GeoDataFrame(df)
    gdf.set_geometry("geometry")
    gdf.crs = "EPSG:{}".format(epsg)
    
    if get_lines == True:
        edges = nx.to_pandas_edgelist(G)
        edges["from"] = edges["source"].map(
                lambda x: gdf.at[(
                        np.int64(x),
                        "geometry"
                        )]
                )
        edges["to"] = edges["target"].map(
                lambda x: gdf.at[(
                        np.int64(x),
                        "geometry"
                        )]
                )
        edges["tuple"] = list(zip(edges["from"], edges["to"]))
        edges["geometry"] = edges["tuple"].map(lambda x: LineString(x))
        
        gdf_lines = gpd.GeoDataFrame(edges)
        gdf_lines.set_geometry("geometry")
        gdf_lines.crs = "EPSG:{}".format(epsg)
        del gdf_lines["from"]
        del gdf_lines["to"]
        del gdf_lines["tuple"]
        
        return gdf, gdf_lines
    
    return gdf
