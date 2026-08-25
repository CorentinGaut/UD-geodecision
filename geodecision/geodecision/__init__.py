"""Top-level package for geodecision."""

__author__ = """Thomas Leysens"""
__email__ = 'thomleysens@gmail.com'
__version__ = '0.1.0'

from . import _version
__version__ = _version.get_versions()['version']

from .accessibility.accessibility import run
from .accessibility.isochrone import Accessibility
from .graph.connectpoints import ConnectPoints
from .graph.splittednodes import GetSplitNodes
from .graph.utils import graph_to_df, df_to_graph
from .graph.download import run as download_graph
from .osmquery.methods import get_OSM_poly
from .osmquery.methods import run as fetch_polygons
from .spatialops.operations import SpatialOperations, gdf_to_geosource
from .spatialops.intersections import GetIntersections
from .citygml.analyseroofs import GetRoofsAndSlopes
from .visualization.plot_isochrones import run as plot_isochrones
