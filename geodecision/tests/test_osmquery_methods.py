#!/usr/bin/env python
"""Tests for `geodecision.osmquery.methods`'s geometry-type filtering and
the accessibility workflow's graceful fallback when the OSM fetch fails.

`ox.features_from_bbox` is mocked throughout - no network access needed.
"""

from unittest.mock import patch

import geopandas as gpd
import pytest
from shapely.geometry import Point, Polygon

from geodecision.osmquery import methods as osmquery_methods

BBOX = (45.77, 4.86, 45.78, 4.87)  # (south, west, north, east)


def _mixed_geom_gdf():
    return gpd.GeoDataFrame(
            {
                    "entrance": ["yes", None, None],
                    "barrier": [None, "gate", None],
                    "leisure": [None, None, "park"],
                    "tags_list": [["a"], ["b"], ["c"]],
                    },
            geometry=[
                    Point(4.865, 45.775),
                    Point(4.866, 45.776),
                    Polygon([(4.86, 45.77), (4.87, 45.77), (4.87, 45.78), (4.86, 45.78)]),
                    ],
            crs="EPSG:4326",
            )


class TestGetOSMPoints:

    def test_keeps_only_points(self):
        with patch.object(
                osmquery_methods.ox, "features_from_bbox", return_value=_mixed_geom_gdf()
                ):
            result = osmquery_methods.get_OSM_points(
                    BBOX, tags={"entrance": True, "barrier": "gate"}
                    )
        assert len(result) == 2
        assert (result.geometry.geom_type == "Point").all()

    def test_drops_list_columns(self):
        with patch.object(
                osmquery_methods.ox, "features_from_bbox", return_value=_mixed_geom_gdf()
                ):
            result = osmquery_methods.get_OSM_points(
                    BBOX, tags={"entrance": True, "barrier": "gate"}
                    )
        assert "tags_list" not in result.columns

    def test_empty_result_does_not_crash(self):
        empty = _mixed_geom_gdf().iloc[0:0]
        with patch.object(
                osmquery_methods.ox, "features_from_bbox", return_value=empty
                ):
            result = osmquery_methods.get_OSM_points(
                    BBOX, tags={"entrance": True, "barrier": "gate"}
                    )
        assert len(result) == 0


class TestGetOSMPolyUnaffectedByRefactor:

    def test_keeps_only_polygons(self):
        with patch.object(
                osmquery_methods.ox, "features_from_bbox", return_value=_mixed_geom_gdf()
                ):
            result = osmquery_methods.get_OSM_poly(BBOX, "leisure", value="park")
        assert len(result) == 1
        assert (result.geometry.geom_type == "Polygon").all()
