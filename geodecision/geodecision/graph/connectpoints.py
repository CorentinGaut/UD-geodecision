#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 12 16:16:55 2019

Source: https://github.com/ywnch/toolbox (Yuwen Chang)
License of the source:
    MIT License
    
    Copyright (c) 2019 Yuwen
    
    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:
    
    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.
    
    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.

@adaptation: thomas
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import rtree
import itertools
from shapely.geometry import MultiPoint, LineString
from shapely.ops import snap, split
import os

from ..logger.logger import logger

pd.options.mode.chained_assignment = None

class ConnectPoints:
    """
    Description
    ------------
    
    Connect and integrate a set of POIs into an existing road network.
    Given a road network in the form of two GeoDataFrames: nodes and edges,
    link each POI to the nearest edge (road segment) based on its projection
    point (PP) and generate a new integrated road network including the POIs,
    the projected points, and the connection edge.
    
    Returns
    --------
    
    - nodes (GeoDataFrame): the original gdf with POIs and PPs appended
    - edges (GeoDataFrame): the original gdf with connection edges appended
                          and existing edges updated (if PPs are present)
    
    Parameters
    -----------
    
    - pois (GeoDataFrame): 
        - GDF of POI (geom: Point)
        - Must be in metric projection (same for nodes, pois and edges)
    - nodes (GeoDataFrame): 
        - GDF of road network nodes (geom: Point)
        - Must be in metric projection (same for nodes, pois and edges)
    - edges (GeoDataFrame): 
        - GDF of road network edges (geom: LineString)
        - Must be in metric projection (same for nodes, pois and edges)
    - access_type (str):
        - Type of polygon that have to be connected to the network
        - Ex: "park", "building", ...
    - prefix(str):
        - Prefix for the name of new nodes and edges files
        - Ex: "Lyon_area_parks" 
    - key_col (str): 
        - a unique key column of pois should be provided,
          e.g., 'index', 'osmid', 'poi_number', etc.
          Currently, this will be renamed into 'osmid' in the output.
    - path (str): 
        - directory path to use for saving files (nodes and edges).
    - threshold (int): 
        - the max length (in meters) of a POI connection edge, POIs with
          connection edge beyond this length will be removed.
    - knn (int): 
        - k nearest neighbors to query for the nearest edge.
          Consider increasing this number up to 10 if the connection
          output is slightly unreasonable. But higher knn number will
          slow down the process.
    - distance(int):
        - distance reachable in 60 minutes
        - required to measure the time distance of an edge
        - default: 5000 (meters)

    """
    
    def __init__(
            self, 
            points, 
            nodes, 
            edges,
            access_type,
            prefix,
            key_col=None, 
            path=None, 
            threshold=50, 
            knn=5,
            distance=5000
            ):
        self.points = points
        self.nodes = nodes
        self.edges = edges
        self.access_type = access_type
        self.prefix = prefix
        self.key_col = key_col
        self.path = path
        self.threshold = threshold
        self.knn = knn
        self.node_highway_pp = 'projected_pap'  # Access Point
        self.node_highway_access = 'access'
        self.edge_highway = 'projected_footway'
        self.osmid_prefix = 9990000000 
        self.distance = distance
        
        #Build Rtree
        self.Rtree = rtree.index.Index()
        [self.Rtree.insert(
                fid,
                geom.bounds
                ) for fid, geom in self.edges['geometry'].items()];
        
    
    def update_nodes_process(self):
        """
        Description
        ------------
        
        Update the NetworkX Graph object with input nodes and nodes created
        during the splitting edges operation
        
        Returns
        --------
        
        None
        
        Parameters
        -----------
        
        None
        """
        #Update nodes with new access nodes
        self.nodes, self.new_nodes = self.update_nodes(
                self.nodes, 
                self.points,
                ptype = "access"
                )
        
        #Update nodes with new created nodes (interpolated points)
        # locate nearest edge (kne) and projected point (pp)
        self.points['near_idx'] = [
                list(
                        self.Rtree.nearest(point.bounds, self.knn)
                        ) for point in self.points['geometry']
                ]  # slow
        self.points['near_lines'] = [
                self.edges['geometry'][near_idx] for near_idx in
                                    self.points['near_idx']
                                    ]  # very slow
        self.points['kne_idx'], knes = zip(
            *[
                    self.find_kne(
                            point, 
                            near_lines
                            ) for point, near_lines in
              zip(
                      self.points['geometry'], 
                      self.points['near_lines']
                      )
              ]
            )  # slow
        self.points['pp'] = [
                self.get_pp(
                        point, 
                        kne
                        ) for point, kne in
                            zip(
                                    self.points['geometry'], 
                                    knes
                                    )
                            ]
        
        self.nodes, self.new_nodes = self.update_nodes(
                self.nodes, 
                list(self.points['pp']),
                ptype='pp'
                )
        nodes_coord = self.nodes['geometry'].map(lambda x: x.coords[0])
        self.nodes_id_dict = dict(
                zip(
                        nodes_coord, 
                        self.nodes['osmid'].astype('str')
                        )
                )
                
    def update_edges_process(self):
        """
        Description
        ------------
        
        Update the NetworkX Graph object with edges created
        during the splitting edges operation
        
        Returns
        --------
        
        None
        
        Parameters
        -----------
        
        None
        """
        #Update existing edges 
        ## Split edges to segments
        # Grouping by a list (even length-1) now yields tuple keys under
        # recent pandas; group by the column name directly for scalar keys
        # that match self.edges' index labels.
        self.line_pps_dict = {
                k: MultiPoint(list(v)) for k, v in
                     self.points.groupby('kne_idx')['pp']
                     }
        new_lines = [
                self.split_line(
                        self.edges['geometry'][idx], 
                        pps
                        ) for idx, pps in self.line_pps_dict.items()]  # bit slow
        self.edges, self.new_edges = self.update_edges(
                self.edges, 
                new_lines, 
                replace=True
                )
        # Update external edges (projected footways connected to pois)
        # establish new_edges
        pps_gdf = self.nodes[self.nodes['highway'] == self.node_highway_pp]
        new_lines = [
                LineString([p1, p2]) for p1, p2 in zip(
                        self.points['geometry'], 
                        pps_gdf['geometry']
                        )
                ]
        self.edges, self.new_edges = self.update_edges(
                self.edges, 
                new_lines, 
                replace=False
                )
        
    def find_kne(self, point, lines):
        """
        
        """
        dists = np.array(
                list(
                        map(
                                lambda l: l.distance(point), 
                                lines
                                )
                        )
                )
        kne_pos = dists.argsort()[0]
        kne = lines.iloc[[kne_pos]]
        kne_idx = kne.index[0]
        
        return kne_idx, kne.values[0]
    
    def get_pp(self, point, line):
        """
        Description
        ------------
        
        Get the projected point (pp) of 'point' on 'line'.
        
        Returns
        --------
        
        Projected points
        
        Parameters
        -----------
        
        - point(Shapely Point object):
            - Point
        - line(Shapely LineString object):
            - LineString
        """
        
        # project new Point to be interpolated
        pp = line.interpolate(line.project(point))  # PP as a Point
        return pp

    def split_line(self, line, pps):
        """
        Description
        ------------
        
        Split 'line' by all intersecting 'pps' (as multipoint)
        
        Returns
        --------
        
        New_lines (list): a list of all line segments after the split
        
        Parameters
        -----------
        
        None
        """
        
        """.
        Returns:
            
        """
        # IMPORTANT FIX for ensuring intersection between splitters and the line
        # but no need for updating edges_meter manually because the old lines will be
        # replaced anyway
        line = snap(line, pps, 1e-8)  # slow?

        try:
            # Shapely >=2.0 returns a GeometryCollection from split(), which
            # (like other multi-part geometries) no longer supports direct
            # iteration - list(...) raises TypeError here on every call,
            # which used to be silently swallowed below and turned into an
            # empty split (i.e. the original edge got dropped and never
            # replaced, disconnecting the network at every split point).
            # Use .geoms explicitly instead.
            result = split(line, pps)
            new_lines = list(result.geoms) if hasattr(result, "geoms") else [result]
            return new_lines
        except TypeError as e:
            logger.info('Error when splitting line: {}\n{}\n{}\n'.format(e, line, pps))
            return []

    def update_nodes(self, nodes, new_points, ptype):
        """
        Description:
        ------------
        Update nodes with a list (pp) or a GeoDataFrame (access) of new_points.
        
        Parameters:
        -----------
        - ptype(str): 
            - type of Point list to append, 'pp' or 'access'
        """
        # create gdf of new nodes (projected PAPs)
        if ptype == 'pp':
            new_nodes = gpd.GeoDataFrame(new_points, columns=['geometry'],
                                         crs=self.points.crs)
            n = len(new_nodes)
            new_nodes['highway'] = self.node_highway_pp
            new_nodes['osmid'] = [str(self.osmid_prefix + i) for i in range(n)]

        # create gdf of new nodes
        elif ptype == 'access':
            new_nodes = new_points[['geometry', self.key_col]]
            new_nodes.columns = ['geometry', 'osmid']
            new_nodes['access_type'] = self.access_type
            new_nodes['highway'] = self.node_highway_access
            new_nodes['osmid'] = new_nodes['osmid'].astype(str)

        else:
            logger.info("Unknown ptype when updating nodes.")

        # merge new nodes (it is safe to ignore the index for nodes)
        gdfs = [nodes, new_nodes]
        nodes = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True, sort=False),
                                 crs=gdfs[0].crs)

        return nodes, new_nodes  # all nodes, newly added nodes only

    def update_edges(self, edges, new_lines, replace):
        """
        Description:
        ------------
        
        Update edge info by adding new_lines; or,
        replace existing ones with new_lines (n-split segments).
        
        Parameters:
        -----------
        - edges(DataFrame):
            - Edges DataFrame
        - new_lines(list):
            - list of new lines to add
        - replace: 
            -treat new_lines (flat list) as newly added edges if False,
            else replace existing edges with new_lines (often a nested list)
        
        Note:
            kne_idx refers to 'fid in Rtree'/'label'/'loc', not positional iloc
        """
        # for interpolation (split by pp): replicate old line
        if replace:
            # create a flattened gdf with all line segs and corresponding kne_idx
            kne_idxs = list(self.line_pps_dict.keys())
            lens = [len(item) for item in new_lines]
            new_lines_gdf = gpd.GeoDataFrame(
                {
                        'kne_idx': np.repeat(
                                kne_idxs, 
                                lens
                                ),
                        'geometry': list(
                                itertools.chain.from_iterable(new_lines)
                                )
                        }
                )
            # merge to inherit the data of the replaced line
            cols = list(edges.columns)
            cols.remove('geometry')  # don't include the old geometry
            new_edges = new_lines_gdf.merge(
                    edges[cols], 
                    how='left', 
                    left_on='kne_idx', 
                    right_index=True
                    )
            new_edges.drop('kne_idx', axis=1, inplace=True)
            new_lines = new_edges['geometry']  # now a flatten list
        # for connection (to external poi): append new lines
        else:
            new_edges = gpd.GeoDataFrame(
                    self.points[[self.key_col]], 
                    geometry=new_lines,
                    columns=[self.key_col, 'geometry']
                    )
            new_edges['oneway'] = False
            new_edges['highway'] = self.edge_highway

        # update features (a bit slow)
        new_edges['length'] = [l.length for l in new_lines]
        ## add walkable time
        meters_per_minute = self.distance/60
        new_edges['time'] = [l.length / meters_per_minute for l in new_lines]
        
        new_edges['source'] = new_edges['geometry'].map(
            lambda x: self.nodes_id_dict.get(list(x.coords)[0], 'None'))
        new_edges['target'] = new_edges['geometry'].map(
            lambda x: self.nodes_id_dict.get(list(x.coords)[-1], 'None'))
        new_edges['osmid'] = ['_'.join(s) for s in zip(new_edges['source'],
                                                       new_edges['target'])]

        # remember to reindex to prevent duplication when concat
        start = edges.index[-1] + 1
        stop = start + len(new_edges)
        new_edges.index = range(start, stop)

        # for interpolation: remove existing edges
        if replace:
            edges = edges.drop(kne_idxs, axis=0)
        # for connection: filter invalid links
        else:
            #Get non-valid nodes list 
            ##(nodes not used because too far from network)        
            non_valid = np.where(new_edges['length'] > self.threshold)[0]
            self.non_valid_nodes = new_edges.iloc[non_valid]["unique_id"].to_list()
            
            #Get valid edges
            valid_pos = np.where(new_edges['length'] <= self.threshold)[0]
            n = len(new_edges)
            n_fault = n - len(valid_pos)
            f_pct = n_fault / n * 100
            logger.info(
                    "Remove faulty projections: {}/{} ({:.2f}%)".format(
                    n_fault,
                    n,
                    f_pct
                    )
            )
            
            new_edges = new_edges.iloc[valid_pos]  # use 'iloc' here
                    

        # merge new edges
        dfs = [edges, new_edges]
        edges = gpd.GeoDataFrame(pd.concat(dfs, ignore_index=False, sort=False),
                                 crs=dfs[0].crs)

        # all edges, newly added edges only
        return edges, new_edges
    
    def process(self):
        """
        Description:
        ------------
        
        Run the complete process
        """
        self.non_valid_nodes = [] #required to filter too far nodes
        self.update_nodes_process()
        self.update_edges_process()
        
        self.nodes['x'] = [p.x for p in self.nodes['geometry']]
        self.nodes['y'] = [p.y for p in self.nodes['geometry']]
        
        # edges.reset_index(drop=True, inplace=True)
        self.edges['length'] = self.edges['length'].astype(float)
        self.edges['source'] = self.edges['source'].astype(str) 
        self.edges['target'] = self.edges['target'].astype(str)
        self.nodes['osmid'] = self.nodes['osmid'].astype(str)
        
        # report issues
        # - examine key duplication
        if len(self.nodes) != len(self.nodes_id_dict):
            key_duplication = "NOTE: duplication in node coordinates keys"
            key_duplication += "Nodes count: " + str(
                    len(self.nodes)
                    )
            key_duplication += "Node coordinates key count: " + str(
                            len(self.nodes_id_dict)
                            )
            logger.info(key_duplication)
        # - examine missing nodes
        missing_nodes = "MISSING NODES: \n"
        missing_nodes += "Missing 'from' nodes: " + str(
                        len(self.edges[self.edges['source'] == 'None'])
                        )
        missing_nodes += "\nMissing 'target' nodes: " + str(
                len(
                        self.edges[self.edges['target'] == 'None']
                        )
                )
        logger.info(missing_nodes)
        
        #Remove non valid nodes
        self.nodes = self.nodes.loc[
                ~self.nodes["osmid"].isin(
                        self.non_valid_nodes
                        )
                ]
    
        # save and return
        if self.path:
            nodes_name = self.prefix + "_nodes.geojson"
            self.nodes.to_file(
                    os.path.join(self.path, nodes_name),
                    driver="GeoJSON"
                    )
            edges_name = self.prefix + "_edges.geojson"
            self.edges.to_file(
                    os.path.join(self.path, edges_name),
                    driver="GeoJSON"
                    )
        
        #Log for non_valid_nodes
        non_valid_nodes_str = "LIST OF NON_VALID_NODES: \n"
        for node in self.non_valid_nodes:
            non_valid_nodes_str += str(node) + "\n"
        logger.info(non_valid_nodes_str)
    
        return self.nodes, self.edges, self.non_valid_nodes
