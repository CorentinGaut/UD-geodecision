#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 17 15:10:51 2020

@author: thomleysens
"""
import geopandas as gpd
import fiona
import time
from shapely import speedups
from shapely.geometry import Polygon, MultiPolygon
import osmnx as ox
import os
import re
from copy import deepcopy

from ..logger.logger import _get_duration, logger

    
class GetIntersections:
    """
    Description:
    ------------
    Get intersections of base (Multi-)Polygons layers with intersecting
    (Multi-)Polygons layers from GeoPackage files
    Write feather files (very fast writing compared to GeoJSON writing or 
    GPKG writing so useful for testing)
    Once all done, read and convert feather files to GPKG (GeoPackages) if 
    write_gpkg is set to True (also delete feather files and directory).
    
    Warnings: 
        - writing GPKG could be a very long process according to data size
        - intersecting_gpkg needs layers' name with integer
    

    Parameters
    ----------
    source_gpkg(GeoPackage): 
        GeoPackage with base polygons layers
    intersecting_gpkg(GeoPackage): 
        GeoPackage with intersecting polygons layers
    output(str): 
        path to results directory
    epsg(int) : 
        EPSG for outputs 
        The default is "2154".
    quadrat_width(real) :
        Width for grid (for intersection computing)
        The default is 500.
    driver(str) :
        Driver for writing: "FEATHER", "GEOJSON" or "GPKG"
        Default: "GPKG"

    Returns
    -------
    None.

    """
    def __init__(
            self, 
            source_gpkg,
            intersecting_gpkg,
            output,
            epsg=2154,
            quadrat_width = 500,
            driver = "GPKG"
            ):
        
        self.source_gpkg = source_gpkg
        self.intersecting_gpkg = intersecting_gpkg
        self.output = output
        self.epsg = epsg
        self.quadrat_width = quadrat_width
        self.driver = driver
        
        self.classes = {
            int(
                re.search(r'\d+', name
                          ).group()
                ):False for name in fiona.listlayers(self.intersecting_gpkg)
            }
        
        self.get_all_intersected()

            
    def get_intersect_matches(self, possible_intersected, intersecting):
        """
        Description:
        ------------
        
        Get the geometries (possible_intersected) that intersect with the 
        base geometry (base)
        
        Parameters:
        -----------
        
        - base(Shapely Polygon)
        - possible_intersected(GeoDataFrame)
        """
        
        matches = []
        sindex = possible_intersected.sindex
        
        for poly in intersecting:
            possible_matches_index = list(sindex.intersection(poly.bounds))
            possible_matches = possible_intersected.iloc[possible_matches_index]
            precise_matches = possible_matches[
                    possible_matches.intersects(poly)
                    ]
            matches.extend(precise_matches.index)
            
        matches = list(set(matches))
        
        return matches
        
    def buffer_repare(self, polygon):
        """
        Description:
        ------------
        Buffer a (Multi-)Polygon
    
        Parameters
        ----------
        polygon(Shapely Polygon): Polygon or Multi-Polygon
    
        Returns
        -------
        (Multi-)Polygon with 0.0 buffer
    
        """
        return polygon.buffer(0.0)
        
    def repare_geom(self, gdf):
        """
        Description:
        ------------
        Try to repare invalid geometry with a 0.0 buffering
    
        Parameters
        ----------
        gdf(GeoDataFrame): GeoPandas GeoDataFrame with (Multi-)Polygons
    
        Returns
        -------
        GeoDataFrame with fixed geometries
    
        """
        gdf["validity"] = gdf["geometry"].is_valid
        gdf.loc[gdf["validity"] == False]["geometry"].map(self.buffer_repare)
        #Check if still invalid geometries
        gdf["validity"] = gdf["geometry"].is_valid
        
        return gdf
    
    def prepare_geom(self, gdf):
        """
        Description:
        ------------
        Quadrat cut the geometry (iloc[0] of the GeoDataFrame

        Parameters
        ----------
        gdf(GeoDataFrame): GeoPandas GeoDataFrame with (Multi-)Polygons

        Returns
        -------
        Osmnx quadrat cut geometry

        """
        # make the geometry a multipolygon if it's not already
        geometry = gdf["geometry"].iloc[0]
        if isinstance(geometry, Polygon):
            geometry = MultiPolygon([geometry])
            
        return ox.quadrat_cut_geometry(
            geometry,
            quadrat_width = self.quadrat_width
            )  
   
    def get_all_intersected(self):
        """
        Description:
        ------------
        Get all intersecting (Multi-) Polygons
        Writes files
        objects. 
    
        Returns
        -------
        None.
    
        """    
        start = time.time()
        
        sources = []
        
        for source_name in fiona.listlayers(self.source_gpkg):
            source_gdf = gpd.read_file(
                self.source_gpkg, 
                layer=source_name
                )
            sources.append(source_gdf)
        
        self.source_gdf = gpd.pd.concat(sources)
        self.source_gdf = self.repare_geom(self.source_gdf)
        self.source_gdf = self.source_gdf.to_crs(epsg=self.epsg)
        self.source_gdf = self.source_gdf.loc[
            self.source_gdf["validity"]==True
            ]
        self.source_gdf.reset_index(inplace=True)
        
        self.source_gdf["classes"] = [
            deepcopy(self.classes) for i in range(len(self.source_gdf))
            ]
        invalid = self.source_gdf.loc[self.source_gdf["validity"]==False]
        
        logger.warning(
                """
                Concatenation:         {}
                """.format(
                _get_duration(start)
                )
            )
        
        for intersecting_name in fiona.listlayers(self.intersecting_gpkg):
            start = time.time()
            intersecting_gdf = gpd.read_file(
                self.intersecting_gpkg, 
                layer=intersecting_name
                )
            intersecting_gdf = self.repare_geom(intersecting_gdf)
            intersecting_gdf = intersecting_gdf.to_crs(epsg=self.epsg)
            intersecting = self.prepare_geom(intersecting_gdf)
            
            matches = self.get_intersect_matches(self.source_gdf, intersecting)
            matches = list(set(matches))
            classe = int(re.search(r'\d+', intersecting_name).group())

            #Update classes
            for match in matches:
                self.source_gdf.at[match, "classes"].update({classe:True})
            
            logger.warning(
                """
                Intersecting layer:         {}
                Intersection process:       {}  
                """.format(
                intersecting_name, 
                _get_duration(start)
                )
            )
        
        start = time.time()
        
        if self.driver == "GPKG":
            self.source_gdf.to_file(
                self.output, 
                layer = "classified", 
                driver="GPKG"
                )
            if invalid.empty is False:
                invalid.to_file(self.output, layer = "invalid", driver="GPKG")

        elif self.driver == "GEOJSON":
            self.source_gdf.to_file(self.output, driver="GeoJSON")
            if invalid.empty is False:
                invalid_name = os.path.splitext(self.output)[0]
                invalid_name = invalid_name + "_invalid_.geojson"
                invalid.to_file(invalid_name, driver="GeoJSON")
        
        logger.warning(
                """
                Writing process:       {}  
                """.format(
                _get_duration(start)
                )
            )