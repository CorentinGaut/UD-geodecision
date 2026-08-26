#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
city_gml_treatment.py
@author: Thomas Leysens
"""

from xml.etree import ElementTree as ET
from pyproj import Transformer
import numpy as np
import math
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon
import sys
from geopy.distance import geodesic as distance
import json
import os

from ..logger.logger import logger
from .categories import get_dict_color, make_cat
from .constants import REF_VECTOR, NAMESPACES, Coords, L_coords, PUBLIC, AVG_HEIGHT


class GetRoofsAndSlopes:
    def __init__(
            self, 
            gml_file,
            epsg_in, 
            epsg_out,
            name="",
            out_dir="",
            palette="viridis", 
            driver="GeoJSON",
            attributes = [],
            mean_height = 3.0
            ):
        """
        Description
        ------------
        
        Get roofs from GML file. 
        Measure slope, area, 
        compactness (see:https://fisherzachary.github.io/public/r-output.html) 
        and minimum_width based on minimum_rotated_rectangle 
        (see: https://shapely.readthedocs.io/en/stable/manual.html#object.minimum_rotated_rectangle).
        Write file if name is not "". 
        
        Returns
        --------
        
        DataFrame, GeoDataframe
        
        Parameters
        -----------
        
        - gml_file(str):
            - path to and name of CityGML file
        - epsg_in(int): 
            - EPSG in
        - epsg_out(int): 
            - EPSG out
        - name(str):
            - output file name
            - default: "" (no file is written)
        - out_dir(str):
            - path to the output directory
            - default: ""
        - palette(str):
            - name of colors palette, 
            - default: "viridis",
            - choices: viridis, magma, plasma
        - driver(str):
            - output format
            - default: "GeoJSON"
            - choices: "GeoJSON", "ESRI Shapefile", "GPKG"
        - attributes(list):
            - list of attributes to qualify the buildings
        - mean_height(float):
            - mean height in case of no information on building levels. Used 
            to measure a mean of levels
            - default: 3
        """        
        tree = ET.parse(gml_file)
        self.root = tree.getroot()
        
        self.name = name
        self.driver = driver
        self.epsg_out = epsg_out
        self.palette = palette
        self.attributes = attributes
        self.out_dir = out_dir

        if self.driver == "ESRI Shapefile":
            logger.warning(
                    """
                    There is a known limitation of Shapefile for length of name's field.
                    Some fields may be normalized. 
                    See https://gis.stackexchange.com/a/72133
                    """
                )
            self.extension = ".shp"
        elif self.driver == "GeoJSON":
            self.extension = ".geojson"
        elif self.driver == "GPKG":
            self.name = ''.join(e for e in name if e.isalnum())
            self.extension = ".gpkg"
            
            if epsg_out == None:
                logger.warning("For shapefile output, espg_out need to be set")
                sys.exit()
        
        if epsg_in != epsg_out:
            self.transformer = Transformer.from_proj(epsg_in, epsg_out)
            logger.info(
                "Value for espg_in: {}\nValue for epsg_out: {}".format(
                epsg_in,
                epsg_out
                )
            )
        else:
            self.transformer = None
            logger.warning(
                    "Value for espg_in: {}\nValue for epsg_out: {}".format(
                    epsg_in,
                    epsg_out
                    )
            )
        logger.info("gml_file: {}".format(gml_file))
        
        self.get_df()
    
    def _normalize(self, inputs):
        """
        Description
        ------------
        
        Normalize (remove what it is not alphanumeric)
        
        
        Returns
        --------
        
        A normalized Pandas Serie
        
        
        Parameters
        -----------
        
        - inputs(list like)
        
        """
        
        return pd.Series(
                inputs
                ).str.normalize(
                        'NFKD'
                        ).str.encode(
                                'ascii', 
                                errors='ignore'
                                ).str.decode(
                                        'utf-8'
                                        ).str.lower()
    
    def _check_if_in(self, string):
        """
        Description
        ------------
        
        Check if at least one element of a string is in self.inputs
        
        Returns
        --------
        
        value (True if element is in self.inputs, False if not)
        
        
        Parameters
        -----------
        
        - string(str)
        
        """
        
        value = False
        
        if pd.isna(string) is False:
            for x in string.split():
                if x in self.inputs:
                    value = True
        return value
        
    
    def _set_if_in(self, inputs, df, column, name):
        """
        Description
        ------------
        
        Set the value (True or False) for a specific column and from anonther
        column if element is in inputs
        
        
        Returns
        --------
        
        Dataframe
        
        Parameters
        -----------
        
        - inputs(list like):
            - list of reference elements
        - df(Pandas DataFrame):
            - DataFrame containing column to check
        - column(str): 
            - name of the column containing elements to compare to inputs
        - name(str):
            - name of the new column to create that will containing the
            True/False 
        
        """
        self.inputs = self._normalize(inputs).to_list()
        df[column + "_format"] = self._normalize(df[column])
        df[name] = df[column + "_format"].map(self._check_if_in)
        df.drop([column + "_format"], axis=1, inplace=True)
        
        return df
        
    
    def _surface_normal(self, poly):
        """
        Description
        ------------
        
        Get the surface normal of a roof polygon
        
        Sources:
            - https://fr.wikipedia.org/wiki/Normale_%C3%A0_une_surface
            - https://www.khronos.org/opengl/wiki/Calculating_a_Surface_Normal
            - https://stackoverflow.com/questions/39001642/calculating-surface-normal-in-python-using-newells-method
        
        Returns
        --------
        
        Surface normal
        
        Parameters
        -----------
        
        - poly(Shapely polygon)
        """
        #TODO: NEED TO TEST THIS FUNCTION MORE ! STRANGE BEHAVIORS
        n = [0.0, 0.0, 0.0]
    
        for i, v_curr in enumerate(poly):
            v_next = poly[(i+1) % len(poly)]
            n[0] += (v_curr.y - v_next.y) * (v_curr.z + v_next.z)
            n[1] += (v_curr.z - v_next.z) * (v_curr.x + v_next.x)
            n[2] += (v_curr.x - v_next.x) * (v_curr.y + v_next.y)
        
        if n == [0.0, 0.0, 0.0] or sum(n)==0:
            normalised = None
        else:
            normalised = [i/sum(n) for i in n]
            
        return normalised
    
    
    def _unit_vector(self, vector):
        """ 
        Description
        ------------
        
        Get the unit vector of a vector
        
        Source: https://stackoverflow.com/a/13849249
        
        Returns
        --------
        
        Unit vector of the vector
        
        Parameters
        -----------
        
        - vector(Numpy vector)
        """
        
        return vector / np.linalg.norm(vector)
    
    def _angle_between(self, v1, v2):
        """ 
        Description
        ------------
        
        Get the angle between two vectors
        
        Source: https://stackoverflow.com/a/13849249
        
        Returns
        --------
        
        Angle in radians between vectors 'v1' and 'v2'::
    
                >>> angle_between((1, 0, 0), (0, 1, 0))
                1.5707963267948966
                >>> angle_between((1, 0, 0), (1, 0, 0))
                0.0
                >>> angle_between((1, 0, 0), (-1, 0, 0))
                3.141592653589793
        
        Parameters
        -----------
        
        - v1(Numpy vector)
        - v2(Numpy vector)
        """
        v1_u = self._unit_vector(v1)
        v2_u = self._unit_vector(v2)
        
        return math.degrees(
                np.arccos(
                        np.clip(
                                np.dot(v1_u, v2_u), 
                                -1.0, 1.0
                                )
                        )
                        )
    
    def _poslist_to_coords(self, posList):
        """
        Description
        ------------
        
        Get the unit vector of a vector
        
        Source: https://stackoverflow.com/a/13849249
        
        Returns
        --------
        
        List of coordinates for Bokeh mapping and 
        list of coordinates for futur Shapely Polygon
        
        Parameters
        -----------
        
        - posList(str): 
            - list of CityGML RoofSurface coordinates
        - transformer(object): 
            - pyproj object for reprojection
        """
        xs, ys, zs = [], [], []
        poly = []
        l = list(map(eval, posList.split()))
        coords = [Coords(*l[i:i + 3]) for i in range(0, len(l), 3)]
        
        for coord in coords:
            if self.transformer is not None:
                x,y = self.transformer.transform(coord.x, coord.y)
            else:
                x = coord.x
                y = coord.y
                
            xs.append(x)
            ys.append(y)
            zs.append(coord.z)
            
            poly.append(Coords(coord.x,coord.y,coord.z))
            
        return L_coords(xs, ys, zs), poly
    
    def _add_poly(self, x):
        """
        Description
        ------------
        
        Returns Shapely Polygon when length of coordinates list >= 3
        """
        if len(x["xs"]) >= 3:
            poly =  Polygon([(x,y) for x,y in zip(x["xs"], x["ys"])])
        else:
            poly = None
            
        return poly
    
    def _get_min_width(self, poly):
        """
        Description
        ------------
        
        Get the minimum width of a polygon
        
        See: https://shapely.readthedocs.io/en/stable/manual.html#object.minimum_rotated_rectangle
        
        Returns
        --------
        
        Minimum width
        
        Parameters
        -----------
        
        - poly(Shapely polygon):
            - projection MUST BE EPSG 4326 to avoid 
            ValueError: Latitude must be in the [-90; 90] range.
        """
        
        distances = []
        min_rot_rect = poly.minimum_rotated_rectangle
        
        if isinstance(min_rot_rect, Polygon):
            coords = min_rot_rect.exterior.coords
            for i,coord in enumerate(coords[0:2]):
                distances.append(distance(coord, coords[i+1]).meters)
            
            return min(distances)
        else:
            logger.info(
                    """
                    {} is not a Polygon
                    """.format(poly.wkt)
                    )
            return np.nan
        
    
    def _get_roofs(self, building, id_building):
        """
        Description
        ------------
        
        Get roofs, roofs area and angles (from self._angle_between)
        
        Returns
        --------
        
        Areas and angles
        
        Parameters
        -----------
        
        - building(building GML):
            - City GML object
        - id_building(string): 
            - id of GML building
        """
        for RoofSurface in building.findall('.//ns2:RoofSurface', NAMESPACES):
            i=0
            for posList in RoofSurface.findall('.//ns1:posList', NAMESPACES):
                id_ = RoofSurface.attrib["{http://www.opengis.net/gml}id"]
                self.building_ids.append(id_building)
                coords, poly = self._poslist_to_coords(
                        posList.text
                        )
                self.xs.append(coords.xs)
                self.ys.append(coords.ys)
                self.zs.append(coords.zs)
                self.ids.append(id_)
                self.elements.append(i)
                vector = self._surface_normal(poly)
                if vector == None:
                    logger.warning(
                            """
                            RoofSurface with id {} has problematic posList at position {}: 
                            {}
                            Angle of this will be 90 (in degrees) to highlight the problem
                            """.format(
                                id_, 
                                i, 
                                posList.text,
                            )
                    )
                    self.angles.append(90.0)
                else:
                    self.angles.append(self._angle_between(vector, REF_VECTOR))
                
                i+=1
    
    def _get_grounds(self, building, id_building):
        """
        Description
        ------------
        
        Get grounds positions
        
        Returns
        --------
        
        
        
        Parameters
        -----------
        
        - building(building GML):
            - City GML object
        - id_building(string): 
            - id of GML building
        """
        for GroundSurface in building.findall('.//ns2:GroundSurface', NAMESPACES):
            i=0
            for posList in GroundSurface.findall('.//ns1:posList', NAMESPACES):
                id_ = GroundSurface.attrib["{http://www.opengis.net/gml}id"]
                self.building_ids_ground.append(id_building)
                coords, poly = self._poslist_to_coords(
                        posList.text
                        )
                self.xs_ground.append(coords.xs)
                self.ys_ground.append(coords.ys)
                self.zs_ground.append(coords.zs)
                self.ids_ground.append(id_)
                self.elements_ground.append(i)
                i+=1
    
    def _get_height_levels(self, building, id_building):
        """
        Description
        ------------
        
        Get height
        Append height in self.heights
        
        Parameters
        -----------
        
        - building(building GML):
            - City GML object
        - id_building(string): 
            - id of GML building
        """
        for measuredHeight in building.findall('.//ns2:measuredHeight', NAMESPACES):
            height = float(measuredHeight.text)
        
        self.heights[id_building] = height
        self.levels[id_building] = height//AVG_HEIGHT
        
    
    def _make_df_buildings(self, dict_buildings):
        """
        Description
        ------------
        

        
        Returns
        --------

        
        """
        df_buildings = pd.DataFrame.from_dict(dict_buildings, orient="index")
        #Replace space strings
        df_buildings.replace(" ", np.nan, inplace=True)
        #Drop nan
        df_buildings.dropna(how="all", inplace=True)
        
        #Drop nan with subset and filter attributes
        # ***WARNING: attributes can be problematic => 
        # https://github.com/VCityTeam/UD-SV/tree/master/UD-Doc/LessonsLearned/WorkingWithLyonOpenData#undocummented-additional-data-***
        if self.attributes != []:
            df_attributes = df_buildings[self.attributes]
            df_attributes.dropna(
                    how="all",
                    inplace=True
                    )
            df_attributes["attribute"] = df_attributes[
                    self.attributes
                    ].values.tolist()
            df_attributes["attribute"] = df_attributes["attribute"].apply(
                    lambda x:  gpd.pd.Series(x).dropna().drop_duplicates().values[0]
                    )
            df_buildings["attribute"] = df_attributes["attribute"]
        
        #Set public access value to True or False
        df_buildings = self._set_if_in(
                PUBLIC, 
                df_buildings, 
                "attribute", 
                "public_access"
                )
        
        return df_buildings
        
    
    def get_df(self):
        """
        Description
        ------------
        
        Execute all the measures and write file if needed.
        Create roofs DataFrame. 
        Get buildings informations and create a DataFrame. 
        Link buildings DataFrame and roofs DataFrame with external key,
        building_ids in roofs DataFrame (index of buildings DataFrame)
        
        
        Returns
        --------
        
        DataFrame and GeoDataframe
        
        """
        #Lists for roofs
        self.xs = []
        self.ys = []
        self.zs = []
        self.angles = []
        self.ids = []
        self.elements = []
        self.building_ids = []
        
        #Lists for grounds
        self.xs_ground = []
        self.ys_ground = []
        self.zs_ground = []
        self.ids_ground = []
        self.elements_ground = []
        self.building_ids_ground = []
        
        #Heights dict
        self.heights = {}
        self.levels = {}
        
        dict_buildings = {}
        for building in self.root.findall('.//ns2:Building', NAMESPACES):
            dict_tmp = {}
            id_building = building.attrib.get("{http://www.opengis.net/gml}id")
            for x in building:
                s = x.attrib.get("name")
                if s is not None:
                    dict_tmp[s] = x[0].text
            dict_buildings[id_building] = dict_tmp
        
            self._get_roofs(building, id_building)
            self._get_grounds(building, id_building)
            self._get_height_levels(building, id_building)
            
            
        df_roofs = pd.DataFrame.from_dict(
            {
                "ids":self.ids,
                "building_ids":self.building_ids,
                "elements":self.elements,
                "xs":self.xs,
                "ys":self.ys,
                "zs":self.zs,
                "angles":self.angles,
            }
        )
        
        df_grounds = pd.DataFrame.from_dict(
            {
                "building_ids":self.building_ids_ground,
                "ids":self.ids_ground,
                "xs":self.xs_ground,
                "ys":self.ys_ground,
                "zs":self.zs_ground,
                "elements":self.elements_ground
            }
        )
        
        df_buildings = self._make_df_buildings(dict_buildings)
#        df_buildings = pd.DataFrame.from_dict(dict_buildings, orient="index")
        
        #Get categories and colors
        df_roofs["categories"] = df_roofs["angles"].map(make_cat)
        df_roofs["colors"] = df_roofs["categories"].map(get_dict_color(choice=self.palette))
        df_roofs.sort_values(by=["angles"], ascending=False, inplace=True)
        
        #Add heights, levels
        ## Average level height => 2.70, source: 
        ## https://www.lemoniteur.fr/article/les-sept-principes-a-s-approprier.1953879
        ## WARNING: we don't have possibility to distinguish commercial/office 
        ## buildings from apartment blocks, yet they have not the same average 
        ## height for level***
        df_roofs["heights"] = df_roofs["building_ids"].map(self.heights)
        df_roofs["nb_levels"] = df_roofs["building_ids"].map(self.levels)
        
        #Create GeoDataframe to make some measures
        df_roofs["geometry"] = df_roofs.apply(self._add_poly, axis=1)
        #Combine with all df_buildings attributes
        df_roofs = df_roofs.merge(
                df_buildings, 
                right_on=df_buildings.index,
                left_on="building_ids", 
                how="right"
                )
        gdf_roofs = gpd.GeoDataFrame(df_roofs, geometry="geometry")
        gdf_roofs.set_crs(epsg=self.epsg_out, allow_override=True, inplace=True)
        
        #Drop duplicates and NaN geometries
        gdf_roofs = gdf_roofs.drop_duplicates(
                subset="geometry"
                )
        gdf_roofs["null_geom"] = gdf_roofs.geometry.isna()
        gdf_roofs = gdf_roofs.loc[gdf_roofs["null_geom"] == False]
        gdf_roofs.drop("null_geom", inplace=True, axis=1)
        
        gdf_roofs.drop(columns=["xs","ys","zs"], inplace=True) 
        #Get area of the roof 
        gdf_roofs["area"] = gdf_roofs.area
        #Calculates total surface
        gdf_roofs["total_surface"] = gdf_roofs["nb_levels"] * gdf_roofs["area"]
        #Get the convex hull ratio to get compactness ratio
        ##see: https://fisherzachary.github.io/public/r-output.html
        gdf_roofs["convex_hull_area"] = gdf_roofs.convex_hull.area
        gdf_roofs["compactness"] = gdf_roofs["area"] / gdf_roofs["convex_hull_area"]
        #Project to EPSG 4326 and drop missing geometries
        gdf_roofs = gdf_roofs.dropna(subset=["geometry"])
        #Change projection to fit with self._get_min_width requirements
        gdf_roofs = gdf_roofs.to_crs(epsg=4326)
        gdf_roofs["min_width"] = gdf_roofs["geometry"].map(self._get_min_width)
        #Back to previous EPSG
        gdf_roofs = gdf_roofs.to_crs(epsg=self.epsg_out)
        df_grounds["geometry"] = df_grounds.apply(self._add_poly, axis=1)
        gdf_grounds = gpd.GeoDataFrame(df_grounds, geometry="geometry")
        gdf_grounds.set_crs(epsg=self.epsg_out, allow_override=True, inplace=True)
        gdf_grounds.drop(
                columns=["xs","ys","zs"],
                inplace=True
                )

        if self.name != "":
            if (self.driver == "GeoJSON") or (self.driver == "ESRI Shapefile"): 
                #Check if file exists, delete it if so before writting it 
                ##(necessary because of Fiona behavior with GeoJSON)
                name_to_check = os.path.join(self.out_dir, self.name + "_roofs" + self.extension)
                try:
                    os.remove(name_to_check)
                except OSError:
                    pass
                name = self.name + "_roofs" + self.extension
                name = os.path.join(self.out_dir, name)
                gdf_roofs.to_file(
                        name,
                        driver=self.driver,
                        encoding="utf-8"
                        )
                name = self.name + "_grounds" + self.extension
                name = os.path.join(self.out_dir, name)
                gdf_grounds.to_file(
                        name, 
                        driver=self.driver,
                        encoding="utf-8"
                        )
                
            elif self.driver == "GPKG":
                name = "Roofs" + self.extension
                gdf_roofs.to_file(
                        os.path.join(self.out_dir, name), 
                        layer=self.name, 
                        driver=self.driver,
                        encoding="utf-8"
                        )
                name = "Grounds" + self.extension
                gdf_grounds.to_file(
                        os.path.join(self.out_dir, name),
                        layer=self.name,  
                        driver=self.driver,
                        encoding="utf-8"
                        )
            else:
                print ("""
                       Wrong name for the output format
                       Choice between "GeoJSON", "ESRI Shapefile" and "GPKG"
                       """)
            buildings_name = os.path.splitext(self.name)[0] + ".json" 
            buildings_name = os.path.join(self.out_dir, buildings_name)
            data = df_buildings.to_json(orient="index")
            with open(buildings_name, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        
        self.df_buildings = df_buildings
        self.df_roofs = df_roofs
        self.gdf_roofs = gdf_roofs
        self.gdf_grounds = gdf_grounds 