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
                "zones_folder":
                    {"type": "string"},
                "zones_format":
                    {"type": "string"},
                "trip_times":
                    {"type": "array"},
                "id_column":
                    {"type": "string"},
                "highlight_id":
                    {"type": "string"},
                },
        "required": [
                "isolines_geojsonfile",
                "epsg_metric",
                "output_folder",
                "output_png",
                ],
        }
