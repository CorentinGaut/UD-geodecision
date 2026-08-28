#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Sep 20 09:24:58 2019

@author: thomas
"""
import time
from shapely.ops import unary_union
from shapely import speedups
import geopandas as gpd
import json

from ..logger.logger import _get_duration, logger

#Get GeoJSON DataSource
def gdf_to_geosource(gdf):
    """
    Description
    ------------
    
    Transform a GeoPandas GeoDataFrame to GeoJSON object
    
    Returns
    --------
    
    GeoJSON object
    
    Parameters
    -----------
    
    - gdf(GeoDataFrame):
        - GeoPandas GeoDataFrame
    """     
        
    return json.dumps(
            json.loads(
                gdf.to_json()
            )
        )

def get_intersect_matches(base, possible_intersected):
        """
        Description:
        ------------
        
        Get the geometries (possible_intersected) that intersect with the 
        base geometry (base)
        
        Parameters:
        -----------
        
        - base(Shapely Polygon or MultiPolygon)
        - possible_intersected(GeoDataFrame)
        """
        #TODO: Check if intersection on "to" is necessary
        matches = []
        possible_intersected = possible_intersected.set_geometry("from")
        sindex = possible_intersected.sindex

        # Shapely >=2.0 removed direct iteration on multi-part geometries;
        # use .geoms when available, else treat base as a single geometry.
        polys = base.geoms if hasattr(base, "geoms") else [base]
        for poly in polys:
            possible_matches_index = list(sindex.intersection(poly.bounds))
            possible_matches = possible_intersected.iloc[possible_matches_index]
            precise_matches = possible_matches[
                    possible_matches.intersects(poly)
                    ]
            matches.extend(precise_matches.index)
            
        return list(set(matches))

class SpatialOperations:
    """
    Description:
    ------------
    
    Dissolve multi-polygons with holes into one polygons (with holes).
    
    Parameters:
    -----------
    
    - trip_times(list):
        - list of accessibility durations
    - gdf_base(GeoDataFrame):
        - GeoDataFrame with input polygons (accessibility measures from them)
    - gdf_access(GeoDataFrame):
        - GeoDataFrame with union of buffered lines (polygons) from 
        accessibility measures
    - duration_column(str):
        - Column used to make unary_union
    - epsg(int):
        - European Petroleum Survey Group, 
        like CRS (Coordinate Reference System)
        - default: 2154
    - tolerance(int):
        - Tolerance used in possible simplification if <0
        - default: 0
    """
    
    def __init__(
            self, 
            trip_times, 
            gdf_base, 
            gdf_access, 
            duration_column,
            epsg=2154,
            tolerance=0
            ):
        """
        Init: see Class
        """
        self.trip_times = trip_times
        self.trip_times.sort()
        self.union_base = unary_union(
                gdf_base["geometry"].to_list()
                )
        self.gdf_access = gdf_access
        self.col = duration_column
        self.epsg = epsg
        self.dict_unions = {}
        self.tolerance = tolerance
        
        self._dissolve()
        
        
    def _dissolve(self):
        """
        Description:
        ------------
        
        Unary_union (dissolve) of polygons by duration
        
        Returns:
        --------
        
        Add dict_unions object (with all unions results)
        """
        union = None
        for trip_time in self.trip_times:
            start = time.time()
            
            #Simplification to speed up the treatment if self.tolerance > 0
            ## GET THE RIGHT TRIP TIME THEN SIMPLIFY OR NOT AND UNION WITH
            ## OTHER LAYERS (TRIP TIMES AND PARKS) 
            #TODO: NEED TO EXPLAIN THIS BETTER BECAUSE I WAS LOST IN MY OWN CODE !!!
            if self.tolerance != 0:
                trip_time_polys = self.gdf_access.loc[
                                self.gdf_access[self.col] == trip_time
                                ]["geometry"].simplify(
                                tolerance=self.tolerance
                                ).unary_union
            else:
                trip_time_polys = self.gdf_access.loc[
                                self.gdf_access[self.col] == trip_time
                                ]["geometry"].unary_union
            if trip_time == min(self.trip_times): #check if min value
                tmp = [self.union_base, trip_time_polys]
            else:
                tmp = [union, trip_time_polys]
            
            union = unary_union(
                        tmp
                        )
            self.dict_unions[trip_time] = gpd.GeoDataFrame(
                    geometry=[union],
                    crs = "EPSG:{}".format(self.epsg)
                    )
            
            logger.info("""
                    | spatial_operations.py |
                    | SpatialOperations._dissolve |
                    
                    Union for {}
                        Total time : {}
                    """.format(trip_time,
                        _get_duration(start)
                    ))