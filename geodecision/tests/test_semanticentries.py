#!/usr/bin/env python
"""Tests for `geodecision.graph.semanticentries` and the column-preserving
change to `geodecision.graph.connectpoints.ConnectPoints.update_nodes`.

No network access required: OSM candidate points are built in-memory.
"""

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Polygon, Point

from geodecision.graph.semanticentries import GetSemanticEntries
from geodecision.graph.splittednodes import GetSplitNodes
from geodecision.graph.connectpoints import ConnectPoints

CRS = "EPSG:2154"


@pytest.fixture
def two_parks():
    park_a = Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])
    park_b = Polygon([(100, 0), (200, 0), (200, 100), (100, 100)])
    return gpd.GeoDataFrame(
            {
                    "poly_id": ["A", "B"],
                    "name": ["Park A", "Park B"],
                    "barrier": ["fence", None],
                    },
            geometry=[park_a, park_b],
            crs=CRS,
            )


@pytest.fixture
def candidate_points():
    return gpd.GeoDataFrame(
            {
                    "entrance": ["yes", None, None, None, "main"],
                    "barrier": [None, "gate", "gate", None, "gate"],
                    },
            geometry=[
                    Point(50, 0),     # on A's boundary -> entrance
                    Point(-5, 50),    # 5m outside A -> gate, within buffer
                    Point(-50, 50),   # 50m outside A -> too far, no match
                    Point(100, 50),   # shared boundary A/B -> matches both
                    Point(150, 0),    # on B's boundary, both tags -> entrance wins
                    ],
            crs=CRS,
            )


class TestClassify:

    def test_entrance_preferred_over_gate(self):
        row = {"entrance": "main", "barrier": "gate"}
        assert GetSemanticEntries._classify(row) == ("osm_entrance", "main")

    def test_gate_only(self):
        row = {"entrance": None, "barrier": "gate"}
        assert GetSemanticEntries._classify(row) == ("osm_gate", "gate")

    def test_entrance_only(self):
        row = {"entrance": "yes", "barrier": None}
        assert GetSemanticEntries._classify(row) == ("osm_entrance", "yes")


class TestMatching:

    def test_buffer_and_shared_boundary(self, two_parks, candidate_points):
        entries = GetSemanticEntries(
                two_parks, candidate_points, dist_split=30, id_column="poly_id",
                entrance_buffer_dist=15, min_entries_per_park=2,
                ).get_entries()

        counts = entries.groupby("poly_id").size()
        # A: on-boundary entrance, 5m-outside gate, shared-boundary gate = 3
        # B: shared-boundary gate, on-boundary entrance (tag priority) = 2
        assert counts["A"] == 3
        assert counts["B"] == 2
        # the 50m-away point must never appear
        assert (entries["entry_tag"] != None).sum() == len(entries)  # noqa: E711
        assert set(entries["entry_source"]) == {"osm_entrance", "osm_gate"}

    def test_no_synthetic_when_enough_real_matches(self, two_parks, candidate_points):
        entries = GetSemanticEntries(
                two_parks, candidate_points, dist_split=30, id_column="poly_id",
                entrance_buffer_dist=15, min_entries_per_park=2,
                ).get_entries()
        assert "synthetic" not in set(entries["entry_source"])

    def test_fallback_below_threshold_is_additive(self, two_parks, candidate_points):
        # raise the bar so B (2 real matches) now falls short and gets
        # synthetic points ADDED, without losing its real matches
        entries = GetSemanticEntries(
                two_parks, candidate_points, dist_split=30, id_column="poly_id",
                entrance_buffer_dist=15, min_entries_per_park=3,
                ).get_entries()
        b_entries = entries[entries["poly_id"] == "B"]
        assert (b_entries["entry_source"] == "synthetic").any()
        assert (b_entries["entry_source"] != "synthetic").any()

    def test_none_osm_points_falls_back_everywhere(self, two_parks):
        entries = GetSemanticEntries(
                two_parks, None, dist_split=30, id_column="poly_id",
                ).get_entries()
        assert (entries["entry_source"] == "synthetic").all()
        assert entries["entry_tag"].isna().all()

    def test_empty_osm_points_falls_back_everywhere(self, two_parks, candidate_points):
        empty_points = candidate_points.iloc[0:0]
        entries = GetSemanticEntries(
                two_parks, empty_points, dist_split=30, id_column="poly_id",
                ).get_entries()
        assert (entries["entry_source"] == "synthetic").all()


class TestUniqueId:

    def test_no_collision_between_real_and_synthetic(self, two_parks, candidate_points):
        entries = GetSemanticEntries(
                two_parks, candidate_points, dist_split=30, id_column="poly_id",
                entrance_buffer_dist=15, min_entries_per_park=3,
                ).get_entries()
        assert entries["unique_id"].is_unique
        assert not any(
                u.startswith("real_") and u.startswith("synth_")
                for u in entries["unique_id"]
                )

    def test_synthetic_only_matches_split_nodes_count(self, two_parks):
        entries = GetSemanticEntries(
                two_parks, None, dist_split=30, id_column="poly_id",
                ).get_entries()
        reference = GetSplitNodes(
                two_parks.copy(), 30, "poly_id"
                ).get_split_nodes()
        assert len(entries) == len(reference)


class TestParkAttributesPreserved:

    def test_name_column_survives(self, two_parks, candidate_points):
        entries = GetSemanticEntries(
                two_parks, candidate_points, dist_split=30, id_column="poly_id",
                entrance_buffer_dist=15, min_entries_per_park=2,
                ).get_entries()
        assert set(entries.loc[entries["poly_id"] == "A", "name"]) == {"Park A"}
        assert set(entries.loc[entries["poly_id"] == "B", "name"]) == {"Park B"}

    def test_park_barrier_tag_not_confused_with_gate_classification(
            self, two_parks, candidate_points
            ):
        # Park A itself carries barrier="fence" as an attribute; this must
        # not leak into entry_source/entry_tag classification of its
        # matched points.
        entries = GetSemanticEntries(
                two_parks, candidate_points, dist_split=30, id_column="poly_id",
                entrance_buffer_dist=15, min_entries_per_park=2,
                ).get_entries()
        a_gate_rows = entries[
                (entries["poly_id"] == "A") & (entries["entry_source"] == "osm_gate")
                ]
        assert (a_gate_rows["entry_tag"] == "gate").all()


class TestConnectPointsColumnPreservation:

    def test_extra_columns_survive_update_nodes(self):
        points = gpd.GeoDataFrame(
                {
                        "unique_id": ["p1", "p2"],
                        "entry_source": ["osm_entrance", "synthetic"],
                        "entry_tag": ["yes", None],
                        "highway": ["should_be_dropped", "should_be_dropped"],
                        },
                geometry=[Point(0, 0), Point(1, 1)],
                crs=CRS,
                )
        nodes = gpd.GeoDataFrame(
                {"osmid": ["n1"], "x": [0], "y": [0]},
                geometry=[Point(0, 0)],
                crs=CRS,
                )
        edges = gpd.GeoDataFrame(
                {"geometry": []}, geometry="geometry", crs=CRS
                )

        connector = ConnectPoints(
                points, nodes, edges, access_type="park", prefix="test",
                key_col="unique_id",
                )
        _, new_nodes = connector.update_nodes(nodes, points, ptype="access")

        assert list(new_nodes["entry_source"]) == ["osm_entrance", "synthetic"]
        assert new_nodes["entry_tag"].tolist()[0] == "yes"
        assert pd.isna(new_nodes["entry_tag"].tolist()[1])
        # the constant set by update_nodes wins over the POI's own
        # colliding "highway" column
        assert (new_nodes["highway"] == "access").all()
        assert list(new_nodes["osmid"]) == ["p1", "p2"]
        assert all(isinstance(v, str) for v in new_nodes["osmid"])
