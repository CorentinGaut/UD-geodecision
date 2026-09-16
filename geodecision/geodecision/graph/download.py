#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Download a walkable street graph from OpenStreetMap.

Usage: download.py [<json_params>]

  -h --help  Show this screen.

"""
import argparse
import json
import os
import time

import osmnx as ox
from jsonschema import validate

from ..logger.logger import logger, _get_duration
from ..spatialops.extent import resolve_bbox
from .schema import GRAPH_SCHEMA
from .utils import graph_to_df, graph_with_time


def run(json_params):
    """
    Description
    ------------

    Download a street network graph from OpenStreetMap for a bounding box,
    add walking-time edge weights, and write it out in the edges/nodes JSON
    format consumed by geodecision.accessibility.accessibility.run().

    Returns
    --------

    dict with the written file paths and node/edge counts.

    Parameters
    -----------

    - json_params (str):
        - Complete path to a JSON parameters file, see graph.schema.GRAPH_SCHEMA
        - Fields:
            - bbox (array): [SOUTH, WEST, NORTH, EAST] in EPSG:4326 (WGS84),
              same convention as osmquery.methods.get_OSM_poly
            - select_park (object, alternative to bbox): resolve the bbox
              from a selected park's buffered impact zone instead of a
              literal extent - see spatialops.extent.resolve_bbox
            - network_type (str): osmnx network type, default "walk"
            - epsg_origin (number): CRS of the downloaded graph's node
              coordinates - always 4326 for osmnx, kept here so downstream
              configs (e.g. accessibility.run()'s epsg_graph) can be checked
              against it. Default 4326.
            - walk_speed_kmh (number): walking speed used to convert edge
              length (meters) to time (minutes), default 5
            - output_folder (str)
            - edges_filename (str)
            - nodes_filename (str)
    """
    start_process = time.time()
    with open(json_params) as f:
        params = json.load(f)

    validate(instance=params, schema=GRAPH_SCHEMA)

    output_folder = params["output_folder"]
    os.makedirs(output_folder, exist_ok=True)

    network_type = params.get("network_type", "walk")
    walk_speed_kmh = params.get("walk_speed_kmh", 5)

    # get_OSM_poly's bbox convention is (SOUTH, WEST, NORTH, EAST); osmnx
    # itself expects (west, south, east, north) - convert here so every
    # geodecision config uses the same bbox order.
    south, west, north, east = resolve_bbox(params)

    start = time.time()
    G = ox.graph_from_bbox((west, south, east, north), network_type=network_type)
    logger.info(
                """
                | graph.download |
                | run |

                Download graph from OSM:
                    Nodes: {}
                    Edges: {}
                    Total time : {}
                """.format(
                    G.number_of_nodes(),
                    G.number_of_edges(),
                    _get_duration(start)
                )
                )

    start = time.time()
    G = graph_with_time(G, distance=walk_speed_kmh * 1000)
    logger.info(
                """
                | graph.download |
                | run |

                Add walking time to edges:
                    Total time : {}
                """.format(
                    _get_duration(start)
                )
                )

    edges_path = os.path.join(output_folder, params["edges_filename"])
    nodes_path = os.path.join(output_folder, params["nodes_filename"])
    graph_to_df(G, edges_path, nodes_path)

    logger.info(
                """
                | graph.download |
                | run |

                TOTAL PROCESS:
                    Total time : {}
                """.format(
                    _get_duration(start_process)
                )
                )

    return {
            "edges_path": edges_path,
            "nodes_path": nodes_path,
            "n_nodes": G.number_of_nodes(),
            "n_edges": G.number_of_edges(),
            }


if __name__ == "__main__":
    text = """
    Download an OSM street graph and add walking time weights
    """
    parser = argparse.ArgumentParser(description=text)
    parser.add_argument("json_config")
    args = parser.parse_args()
    run(args.json_config)
