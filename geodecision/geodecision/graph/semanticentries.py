#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Get real park entry points (OSM entrance/gate nodes) with a per-park
fallback to GetSplitNodes' geometric boundary-splitting when too few
real entries are found near a park.
"""

import geopandas as gpd
import pandas as pd

from .splittednodes import GetSplitNodes


class GetSemanticEntries:
    """
    Description
    ------------

    Get park entry points, preferring real OSM entrance/gate nodes near
    each park's boundary and falling back to GetSplitNodes' geometric
    boundary-splitting for parks with too few real matches.

    Returns
    --------

    Entry points GeoPandas GeoDataFrame with the same contract as
    GetSplitNodes.get_split_nodes() (a unique id in "unique_id"), plus
    two extra columns:
    - "entry_source": "osm_entrance" / "osm_gate" / "synthetic"
    - "entry_tag": the raw OSM tag value for real entries (e.g. "yes",
      "main", "gate"), None for synthetic ones

    Parameters
    -----------

    - gdf_polys (GeoDataFrame):
        - park polygons GeoPandas GeoDataFrame
        - Must have a metric projection (distance measure in meters)
    - osm_points (GeoDataFrame or None):
        - candidate OSM entrance/gate points, same metric projection as
          gdf_polys, with "entrance"/"barrier" tag columns
        - None or empty means "no real candidates anywhere": every park
          falls back to the synthetic split points
    - dist_split (int):
        - Split distance (in meters), passed through to GetSplitNodes
          for the fallback
    - id_column (str):
        - Name of the column with unique id for each polygon
    - entrance_buffer_dist (float):
        - Max distance (in meters) from a park's boundary for an OSM
          point to be considered as belonging to it
        - Default: 15
    - min_entries_per_park (int):
        - Minimum count of matched real points required to skip the
          synthetic fallback for a park (fallback is additive: a park
          below this threshold keeps its partial real matches AND gets
          the full synthetic set on top)
        - Default: 2
    - columns(list):
        - List of columns name (columns that will be kept)
        - Default: []
        - If default, keep all columns but geometry column other than
          Points
    """

    def __init__(
            self,
            gdf_polys,
            osm_points,
            dist_split,
            id_column,
            entrance_buffer_dist=15,
            min_entries_per_park=2,
            columns=[]
            ):
        self.gdf_polys = gdf_polys
        self.osm_points = osm_points
        self.dist_split = dist_split
        self.id = id_column
        self.entrance_buffer_dist = entrance_buffer_dist
        self.min_entries_per_park = min_entries_per_park
        if columns == []:
            self.columns = list(gdf_polys.columns)
            self.columns.remove("geometry")
        else:
            self.columns = columns
        self.crs = self.gdf_polys.crs

    def _empty_real_entries(self):
        """
        Description
        ------------

        Build an empty (but correctly-columned) GeoDataFrame for the
        "no real candidates" case, so downstream code never needs to
        special-case a None/empty osm_points input.
        """
        columns = [self.id] + self.columns + [
                "entry_source", "entry_tag", "osm_id", "geometry"
                ]
        columns = list(dict.fromkeys(columns))
        return gpd.GeoDataFrame(
                {col: [] for col in columns if col != "geometry"},
                geometry=gpd.GeoSeries([], crs=self.crs),
                crs=self.crs
                )

    def _boundary_buffers(self):
        """
        Description
        ------------

        Build one row per park: id_column only, geometry = the park's
        full boundary (all rings/parts) buffered by entrance_buffer_dist.
        Deliberately carries no other park attribute so the later spatial
        join can't collide with the OSM points' own tag columns (e.g.
        both a park and a gate node can carry a "barrier" tag); park
        attributes are merged back in afterwards, by id, once the raw OSM
        tags have already been consumed for classification.

        Returns
        --------

        GeoDataFrame of buffered boundary polygons, indexed like
        gdf_polys.
        """
        boundaries = self.gdf_polys["geometry"].map(
                lambda poly: poly.boundary
                )
        buffered = boundaries.buffer(self.entrance_buffer_dist)
        gdf_buffers = self.gdf_polys[[self.id]].copy()
        gdf_buffers["geometry"] = buffered
        return gpd.GeoDataFrame(gdf_buffers, geometry="geometry", crs=self.crs)

    @staticmethod
    def _classify(row):
        """
        Description
        ------------

        Classify a matched OSM point into (entry_source, entry_tag),
        preferring an "entrance" tag over "barrier=gate" when both are
        present on the same node.
        """
        entrance_value = row.get("entrance")
        if pd.notna(entrance_value):
            return "osm_entrance", entrance_value
        return "osm_gate", "gate"

    def _match_real_entries(self):
        """
        Description
        ------------

        Spatial-join candidate OSM points against each park's buffered
        boundary; classify and id each match, then merge back the
        requested park attribute columns (e.g. "name") by id_column.

        Returns
        --------

        GeoDataFrame with [id_column, *columns, geometry, entry_source,
        entry_tag, osm_id]. A single OSM point may match more than one
        adjacent park (e.g. a shared gate) - both rows are kept.
        """
        if self.osm_points is None or len(self.osm_points) == 0:
            return self._empty_real_entries()

        # Keep only what's needed for the join/classification, so no OSM
        # tag column can collide with a park attribute column of the
        # same name (e.g. both a park and a gate node can carry
        # "barrier").
        points = self.osm_points[["geometry"]].copy()
        for tag in ("entrance", "barrier"):
            points[tag] = self.osm_points[tag] if tag in self.osm_points.columns else None
        points["osm_id"] = (
                self.osm_points["osm_id"] if "osm_id" in self.osm_points.columns
                else self.osm_points.index.astype(str)
                )

        matches = gpd.sjoin(
                points,
                self._boundary_buffers(),
                predicate="within",
                how="inner"
                )
        if matches.empty:
            return self._empty_real_entries()

        matches[["entry_source", "entry_tag"]] = matches.apply(
                lambda row: pd.Series(self._classify(row)), axis=1
                )
        matches = matches.drop(columns=["entrance", "barrier", "index_right"])

        # Merge back requested park attribute columns now that the raw
        # OSM tags have been consumed - no more collision risk.
        park_attrs = self.gdf_polys[list(dict.fromkeys([self.id] + self.columns))]
        matches = matches.merge(park_attrs, on=self.id, how="left")

        return gpd.GeoDataFrame(matches, geometry="geometry", crs=self.crs)

    def get_entries(self):
        """
        Description
        ------------

        Get park entry points: real OSM entrance/gate points where
        enough were found near a park, the full synthetic
        (GetSplitNodes) set otherwise - added on top of any partial
        real matches.

        Returns
        --------

        GeoPandas GeoDataFrame, same contract as
        GetSplitNodes.get_split_nodes() plus "entry_source"/"entry_tag".
        """
        real = self._match_real_entries()

        counts = real.groupby(self.id).size() if not real.empty else pd.Series(dtype=int)
        under_served_ids = [
                poly_id for poly_id in self.gdf_polys[self.id]
                if counts.get(poly_id, 0) < self.min_entries_per_park
                ]
        synthetic_subset = self.gdf_polys[
                self.gdf_polys[self.id].isin(under_served_ids)
                ]

        if not synthetic_subset.empty:
            synthetic = GetSplitNodes(
                    synthetic_subset,
                    self.dist_split,
                    self.id,
                    columns=list(self.columns)
                    ).get_split_nodes()
            synthetic["entry_source"] = "synthetic"
            synthetic["entry_tag"] = None
            synthetic["unique_id"] = "synth_" + synthetic["unique_id"].astype(str)
        else:
            synthetic = gpd.GeoDataFrame(
                    {col: [] for col in self.columns + [
                            "entry_source", "entry_tag", "unique_id"
                            ]},
                    geometry=gpd.GeoSeries([], crs=self.crs),
                    crs=self.crs
                    )

        real = real.copy()
        real["unique_id"] = (
                "real_"
                + real[self.id].astype(str)
                + "_"
                + real["osm_id"].astype(str)
                )
        real = real.drop(columns=["osm_id"])

        combined = gpd.GeoDataFrame(
                pd.concat([real, synthetic], ignore_index=True, sort=False),
                crs=self.crs
                )

        return combined
