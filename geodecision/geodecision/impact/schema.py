#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Schema for impact.impact_zone.run() JSON parameters.
"""

IMPACT_ZONE_SCHEMA = {
        "type": "object",
        "properties": {
                "zones_folder":
                    {"type": "string"},
                "zones_format":
                    {"type": "string"},
                "trip_times":
                    {"type": "array"},
                "buildings_geojsonfile":
                    {"type": "string"},
                "epsg_metric":
                    {"type": "number"},
                "output_folder":
                    {"type": "string"},
                "output_format":
                    {"type": "string"},
                },
        "required": [
                "zones_folder",
                "zones_format",
                "trip_times",
                "buildings_geojsonfile",
                "epsg_metric",
                "output_folder",
                "output_format",
                ],
        }
