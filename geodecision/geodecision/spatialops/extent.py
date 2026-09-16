#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Resolve the bbox that graph.download and osmquery.methods query.

Shared by both so they can be driven by the same selected park's impact
zone instead of a hand-typed bounding box.
"""
import geopandas as gpd


def resolve_bbox(params):
    """
    Description
    ------------

    Resolve the (SOUTH, WEST, NORTH, EAST) bbox, in EPSG:4326, that a
    graph.download / osmquery.methods run should query.

    If params["bbox"] is set, it's returned as-is. Otherwise
    params["select_park"] must be set, describing a single park to buffer
    into a bbox - see graph.schema.GRAPH_SCHEMA / osmquery.schema.
    POLYGON_QUERY_SCHEMA for its fields.

    Returns
    --------

    tuple: (south, west, north, east)

    Parameters
    -----------

    - params (dict):
        - run() params, with either "bbox" or "select_park" set:
            - parks_geojsonfile (str): geojson to select the park from
              (e.g. a prior fetch-polygons run's output)
            - id_column (str): column holding the park's id
            - select_id (str): id of the park to select, matching a value
              in id_column
            - epsg_metric (number): CRS to buffer the park in
            - buffer_m (number, optional): buffer distance in meters. If
              omitted, derived from trip_times/walk_speed_kmh instead
            - trip_times (list), walk_speed_kmh (number): used to derive
              buffer_m (max(trip_times) at walk_speed_kmh) when buffer_m
              isn't given directly
    """
    bbox = params.get("bbox")
    if bbox:
        return tuple(bbox)

    select_park = params.get("select_park")
    if not select_park:
        raise ValueError(
                "Either 'bbox' or 'select_park' must be set to resolve "
                "the extent to query."
                )

    parks_geojsonfile = select_park["parks_geojsonfile"]
    id_column = select_park["id_column"]
    select_id = select_park["select_id"]

    gdf = gpd.read_file(parks_geojsonfile)
    matches = gdf.loc[gdf[id_column].astype(str) == str(select_id)]
    if matches.empty:
        raise ValueError(
                "No feature with {!r} == {!r} in {!r}".format(
                        id_column, select_id, parks_geojsonfile
                        )
                )

    epsg_metric = select_park["epsg_metric"]
    park_geom = matches.to_crs("EPSG:{}".format(epsg_metric)).geometry.unary_union

    buffer_m = select_park.get("buffer_m")
    if buffer_m is None:
        trip_times = select_park["trip_times"]
        walk_speed_kmh = select_park.get("walk_speed_kmh", 5)
        buffer_m = max(trip_times) * (walk_speed_kmh * 1000 / 60)

    buffered = gpd.GeoSeries(
            [park_geom.buffer(buffer_m)], crs="EPSG:{}".format(epsg_metric)
            )
    minx, miny, maxx, maxy = buffered.to_crs(4326).total_bounds

    return (miny, minx, maxy, maxx)
