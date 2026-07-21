#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 27 15:24:26 2019

@author: thomas
"""


ACCESS_SCHEMA = {
        "type":"object",
        "properties" : {
                "polygons_geojsonfile":
                    {"type" : "string"},
                "graph_nodes_jsonfile" : 
                    {"type" : "string"},
                "graph_edges_jsonfile" : 
                    {"type" : "string"},
                "epsg_graph" : 
                    {"type" : "number"},
                "epsg_input" : 
                    {"type" : "number"},
                "epsg_metric" : 
                    {"type" : "number"},
                "output_features_layername" : 
                    {"type" : "string"},
                "output_isolines_layername" : 
                    {"type" : "string"},
                "output_buffered_isolines_layername" : 
                    {"type" : "string"},
                "output_buffered_isolines_union_layername" : 
                    {"type" : "string"},
                "output_format" : 
                    {"type" : "string"},
                "output_folder" : 
                    {"type" : "string"},
                "trip_times" : 
                    {"type" : "array"},
                "threshold":
                    {"type" : "integer"},
                "dist_split":
                    {"type" : "integer"},
                "knn":
                    {"type" : "integer"},
                "distance":
                    {"type" : "integer"},
                "weight":
                    {"type" : "string"},
                "access_type":
                    {"type" : "string"},
                "prefix":
                    {"type" : "string"},
                "columns_to_keep":
                    {"type" : "array"},
                "id_column":
                    {"type" : "string"},
                "distance_buffer" : 
                    {"type" : "number"},
                "lat" : 
                    {"type" : "string"},
                "lon" : 
                    {"type" : "string"},
                },
        }