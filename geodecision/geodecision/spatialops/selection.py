#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Select features (e.g. parks) from a polygons GeoDataFrame.

Shared by accessibility.run, spatialops.extent.resolve_bbox and
visualization.plot_isochrones.run so every step of the workflow scopes the
same parks from the same config fields.
"""
import pandas as pd

from ..logger.logger import logger


FILTERS_SCHEMA = {
        "type": "object",
        "additionalProperties": {
                "type": "object",
                "properties": {
                        "min": {"type": "number"},
                        "max": {"type": "number"},
                        },
                "additionalProperties": False,
                },
        }


def select_features(gdf, select_id=None, id_column=None, filters=None, source=""):
    """
    Description
    ------------

    Keep the features of gdf matching an optional id and optional numeric
    attribute thresholds (combined with AND).

    Returns
    --------

    GeoDataFrame: the selected features (a filtered copy of gdf)

    Parameters
    -----------

    - gdf (GeoDataFrame): features to select from
    - select_id (str, optional): keep only gdf[id_column] == select_id.
      "" or None: no id selection
    - id_column (str, optional): column holding the id (needed when
      select_id is set)
    - filters (dict, optional): {column: {"min": x, "max": y}}, bounds
      inclusive, each optional - e.g.
      {"surface_parc": {"min": 5000}, "pct_canopee": {"min": 20}}.
      {} or None: no attribute selection. Rows with a missing value in a
      filtered column are dropped.
    - source (str, optional): file name, only used in messages
    """
    total = len(gdf)
    select_id = select_id or None
    filters = filters or {}

    if select_id is not None:
        gdf = gdf.loc[gdf[id_column].astype(str) == str(select_id)]
        if gdf.empty:
            raise ValueError(
                    "No feature with {!r} == {!r} in {!r}".format(
                            id_column, select_id, source
                            )
                    )

    for column, bounds in filters.items():
        if column not in gdf.columns:
            raise ValueError(
                    "Filter column {!r} not in {!r} (available: {})".format(
                            column, source, ", ".join(map(str, gdf.columns))
                            )
                    )
        values = pd.to_numeric(gdf[column], errors="coerce")
        mask = values.notna()
        if "min" in bounds:
            mask &= values >= bounds["min"]
        if "max" in bounds:
            mask &= values <= bounds["max"]
        gdf = gdf.loc[mask]

    if gdf.empty:
        raise ValueError(
                "No feature in {!r} matches filters {!r}".format(source, filters)
                )

    if select_id is not None or filters:
        logger.info(
                "Selected {} / {} features from {!r} (select_id={!r}, filters={!r})".format(
                        len(gdf), total, source, select_id, filters
                        )
                )
    return gdf
