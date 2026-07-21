#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Schema for graph.download.run() JSON parameters.
"""

GRAPH_SCHEMA = {
        "type": "object",
        "properties": {
                "bbox":
                    {"type": "array"},
                "network_type":
                    {"type": "string"},
                "epsg_origin":
                    {"type": "number"},
                "walk_speed_kmh":
                    {"type": "number"},
                "output_folder":
                    {"type": "string"},
                "edges_filename":
                    {"type": "string"},
                "nodes_filename":
                    {"type": "string"},
                },
        "required": [
                "bbox",
                "output_folder",
                "edges_filename",
                "nodes_filename",
                ],
        }
