#!/usr/bin/env python
"""Tests for `geodecision.spatialops.selection.select_features`."""

import geopandas as gpd
import pytest
from shapely.geometry import Point

from geodecision.spatialops.selection import select_features


@pytest.fixture
def parks():
    return gpd.GeoDataFrame(
            {
                    "uid": ["A", "B", "C", "D"],
                    "surface_parc": [1000.0, 6000.0, 20000.0, None],
                    "pct_vegetation": [90.0, 40.0, 80.0, 95.0],
                    "pct_canopee": [10.0, 30.0, 50.0, 60.0],
                    },
            geometry=[Point(i, 0).buffer(0.4) for i in range(4)],
            crs="EPSG:2154",
            )


def _ids(gdf):
    return list(gdf["uid"])


def test_no_selection_is_passthrough(parks):
    assert _ids(select_features(parks)) == ["A", "B", "C", "D"]
    assert _ids(select_features(parks, select_id="", filters={})) == ["A", "B", "C", "D"]


def test_min_only(parks):
    assert _ids(select_features(parks, filters={"pct_canopee": {"min": 30}})) == ["B", "C", "D"]


def test_max_only(parks):
    assert _ids(select_features(parks, filters={"pct_vegetation": {"max": 80}})) == ["B", "C"]


def test_min_and_max_and_nan_dropped(parks):
    out = select_features(parks, filters={"surface_parc": {"min": 5000, "max": 20000}})
    assert _ids(out) == ["B", "C"]


def test_several_filters(parks):
    out = select_features(parks, filters={
            "surface_parc": {"min": 5000},
            "pct_vegetation": {"min": 50},
            "pct_canopee": {"min": 20},
            })
    assert _ids(out) == ["C"]


def test_combined_with_select_id(parks):
    assert _ids(select_features(parks, select_id="C", id_column="uid",
                                filters={"pct_canopee": {"min": 20}})) == ["C"]
    with pytest.raises(ValueError):
        select_features(parks, select_id="A", id_column="uid",
                        filters={"pct_canopee": {"min": 20}})


def test_unknown_column(parks):
    with pytest.raises(ValueError, match="not in"):
        select_features(parks, filters={"nope": {"min": 1}})


def test_empty_result(parks):
    with pytest.raises(ValueError, match="matches filters"):
        select_features(parks, filters={"pct_canopee": {"min": 99}})
