#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 11 09:44:18 2019

@author: thomas
"""

import geopandas as gpd
from shapely.geometry import LineString

class GetSplitNodes:
    """
    Description
    ------------
    
    Get nodes from splitting polygon's perimeter linestrings
    
    Returns
    --------
    
    Split points GeoPandas GeoDataFrame with unique id for each new points
    in a specific column/Serie: "unique_id"
    
    Parameters
    -----------
    
    - gdf_polys (GeoDataFrame):
        - polygons GeoPandas GeoDataFrame
        - Must have a metric projection (distance measure in meters)
    - dist_split (int):
        - Split distance (in meters)
    - id_column (str):
        - Name of the column with unique id for each polygon
    - columns(list):
        - List of columns name (columns that will be kept)
        - Default: []
        - If default, keep all columns but geometry column other than Points
    """
    
    def __init__(self, gdf_polys, dist_split, id_column, columns=[]):
        """
        Init
        """
        
        self.gdf_polys = gdf_polys
        self.dist_split = dist_split
        if columns == []:
            self.columns = list(gdf_polys.columns)
            self.columns.remove("geometry")
        else:
            self.columns = columns
        
        self.crs = self.gdf_polys.crs
        self.id = id_column
        
#    def _loop_on_line(self):
#        """
#        Description
#        ------------
#        
#        Split linestring and return a list of Shapely Points
#        
#        Returns
#        --------
#        
#        Shapely MultiPoints
#        
#        Parameters
#        -----------
#        
#        - line (Shapely LineString)
#        """
#        
#        for i in range(len(self.line.coords[:-1])):
#                line_tmp = LineString(
#                        [
#                                self.line.coords[i], 
#                                self.line.coords[i+1]
#                                ]
#                        )
#                nb_split = int(line_tmp.length//self.dist_split)
#                if nb_split <= 1:
#                    nb_split = 2
#                    
#                points.extend(
#                        list(
#                                [line_tmp.interpolate(
#                                        (i/nb_split), 
#                                        normalized=True
#                                        ) for i in range(
#                                                1, 
#                                                nb_split
#                                                )
#                                ]
#                            )
#                        )
        
        
    def _splitter(self, line):
        """
        Description
        ------------
        
        Split linestring and return a list of Shapely Points
        
        Returns
        --------
        
        Shapely MultiPoints
        
        Parameters
        -----------
        
        - line (Shapely LineString)
        """
        
        #Split each segment of the LineString in order to get at least
        ## one potential connection point on each "side"
        points = []
        
#        if isinstance(line, MultiLineString):
#            for element in line:
#                self.line = element
#                self._loop_on_line()
#        elif isinstance(line, LineString):
#            self.line = element
#            self._loop_on_line()
#                
#        
#        if line:
#            for i in range(len(line.coords[:-1])):
#                line_tmp = LineString(
#                        [
#                                line.coords[i], line.coords[i+1]
#                                ]
#                        )
#                nb_split = int(line_tmp.length//self.dist_split)
#                if nb_split <= 1:
#                    nb_split = 2
#                    
#                points.extend(
#                        list(
#                                [line_tmp.interpolate(
#                                        (i/nb_split), 
#                                        normalized=True
#                                        ) for i in range(
#                                                1, 
#                                                nb_split
#                                                )
#                                ]
#                            )
#                        )
#        except:
#            print("OUPS")
#            LINE = line
#            print("IIIII")
         #TODO: remove the following after above tested multiple times   
        nb_split = int(line.length//self.dist_split)
        #Manage when nb_split <= 1 to avoid further interpolation errors
        
        #TODO; try with a minimum of 4 splits. 
        if nb_split <= 2: 
            nb_split = 3
        points = list(
                            [line.interpolate(
                                    (i/nb_split), 
                                    normalized=True
                                    ) for i in range(
                                            1, 
                                            nb_split
                                            )
                            ]
                        )
                            
                            
        
#        if isinstance(line, MultiLineString):
#            for element in line:
#                points.extend(
#                        [Point(x) for x in element.coords]
#                        )
#        elif isinstance(line, LineString):
#            points.extend(
#                    [Point(x) for x in line.coords]
#                    )
        
        return points
    
    def _get_boundary(self, poly):
        """
        Description
        ------------
        
        Get LineStrings of Polygon's exterior
        
        Returns
        --------
        
        List of LineStrings
        
        Parameters
        -----------
        
        - poly (Shapely Polygon)
        """
        
        if poly.geom_type == "Polygon":
            boundary = poly.boundary
        elif poly.geom_type == "MultiPolygon":
            # Shapely >=2.0 removed direct indexing on multi-part
            # geometries; use the largest part's boundary via .geoms.
            boundary = max(poly.geoms, key=lambda p: p.area).boundary
        return boundary
        

    def get_split_nodes(self):
        """
        Description
        ------------
        
        Get Points from splitting polygon's perimeter Linestrings 
        
        Returns
        --------
        
        Split points GeoPandas GeoDataFrame
        
        """
        points_column = "points"
        self.columns.append(points_column)
        self.gdf_polys["boundary"] = self.gdf_polys["geometry"].map(
                self._get_boundary
                )
        self.gdf_polys[points_column] = self.gdf_polys["boundary"].map(
                self._splitter
                )
        gdf_points = self.gdf_polys[self.columns]
        gdf_points = gdf_points.explode(points_column).reset_index()
        geometry = gdf_points[points_column]
        del gdf_points[points_column]
        gdf_points = gpd.GeoDataFrame(
                gdf_points,
                geometry=geometry,
                crs=self.crs
                )
        
        #Set a unique id based on index for future manipulations
        gdf_points["index_tmp"] = [i for i in range(0,len(gdf_points))]
        gdf_points["unique_id"] = gdf_points.apply(
                lambda x: str(x[self.id]) + "_" + str(x["index_tmp"]),
                axis=1
                    )
        
        del gdf_points["index"]
        del gdf_points["index_tmp"]        
        
        return gdf_points
        