#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Schema for visualization.plot_isochrones.run() JSON parameters.
"""

VIZ_SCHEMA = {
        "type": "object",
        "properties": {
                "isolines_geojsonfile":
                    {"type": "string"},
                "parks_geojsonfile":
                    {"type": "string"},
                "buildings_geojsonfile":
                    {"type": "string"},
                "epsg_metric":
                    {"type": "number"},
                "output_folder":
                    {"type": "string"},
                "output_png":
                    {"type": "string"},
                "title":
                    {"type": "string"},
                "linewidth":
                    {"type": "number"},
                },
        "required": [
                "isolines_geojsonfile",
                "epsg_metric",
                "output_folder",
                "output_png",
                ],
        }
