#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Schema for citygml.citygml.run() JSON parameters.
"""

CITYGML_SCHEMA = {
        "type": "object",
        "properties": {
                "gml_dir":
                    {"type": "string"},
                "epsg_in":
                    {"type": "number"},
                "epsg_out":
                    {"type": "number"},
                "output_folder":
                    {"type": "string"},
                "driver":
                    {"type": "string"},
                "palette":
                    {"type": "string"},
                "attributes":
                    {"type": "array"},
                "selection": {
                        "type": "object",
                        "properties": {
                                "min_width":
                                    {"type": "number"},
                                "compactness":
                                    {"type": "number"},
                                "area":
                                    {"type": "number"},
                                "max_slope":
                                    {"type": "number"},
                                },
                        },
                },
        "required": [
                "gml_dir",
                "epsg_in",
                "epsg_out",
                "output_folder",
                ],
        }
