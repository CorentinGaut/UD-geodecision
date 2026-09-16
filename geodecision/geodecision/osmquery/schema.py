#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Schema for osmquery.methods.run() JSON parameters.

Adapted from the (previously unused) OSM-query fields sketched in
accessibility.schema.SCHEMA - relocated here since that's what they
actually describe.
"""

POLYGON_QUERY_SCHEMA = {
        "type": "object",
        "properties": {
                "bbox":
                    {"type": "array"},
                "select_park":
                    {"type": "object"},
                "osm_key":
                    {"type": "string"},
                "osm_value":
                    {"type": "string"},
                "epsg_origin":
                    {"type": "number"},
                "output_folder":
                    {"type": "string"},
                "polygons_geojsonfile":
                    {"type": "string"},
                "id_column":
                    {"type": "string"},
                },
        "required": [
                "osm_key",
                "output_folder",
                "polygons_geojsonfile",
                ],
        }
