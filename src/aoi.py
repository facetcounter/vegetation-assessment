"""
Area of interest (AOI) helpers: reprojection, shapefile import, and finding the
3DEP datasets that cover an AOI.

Extracted from notebooks/05_3DEP_Generate_Canopy_Height_Models_User_AOI.ipynb.
"""
import geopandas as gpd
import pyproj
import requests
from shapely.ops import transform

WGS84 = pyproj.CRS("EPSG:4326")
WEB_MERCATOR = pyproj.CRS("EPSG:3857")

BOUNDARIES_URL = 'https://raw.githubusercontent.com/hobuinc/usgs-lidar/master/boundaries/resources.geojson'


def proj_to_3857(poly, orig_crs):
    """
    Reproject a polygon from any CRS to both geographic coordinates (EPSG:4326) and
    Web Mercator (EPSG:3857).

    Parameters:
        poly (shapely polygon): User area of interest (AOI)
        orig_crs (str or pyproj.CRS): CRS of `poly`

    Returns:
        user_poly_proj4326 (shapely polygon): User AOI in EPSG 4326
        user_poly_proj3857 (shapely polygon): User AOI in EPSG 3857
    """
    project_gcs = pyproj.Transformer.from_crs(orig_crs, WGS84, always_xy=True).transform
    project_wm = pyproj.Transformer.from_crs(orig_crs, WEB_MERCATOR, always_xy=True).transform
    return transform(project_gcs, poly), transform(project_wm, poly)


def gcs_to_proj(poly):
    """
    Reproject a polygon from geographic coordinates (EPSG:4326) to Web Mercator (EPSG:3857).

    Parameters:
        poly (shapely polygon): User area of interest (AOI)

    Returns:
        user_poly_proj3857 (shapely polygon): User AOI in EPSG 3857
    """
    project = pyproj.Transformer.from_crs(WGS84, WEB_MERCATOR, always_xy=True).transform
    return transform(project, poly)


def import_shapefile_to_shapely(path):
    """
    Load the first geometry of a shapefile as the AOI.

    Parameters:
        path (filepath): location of shapefile; must have a CRS assigned (.prj)

    Returns:
        (user_shp_epsg4326, user_shp_epsg3857): AOI in EPSG 4326 and EPSG 3857
    """
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        raise ValueError(f"{path} has no CRS; a .prj file is required.")
    return proj_to_3857(gdf.geometry.iloc[0], gdf.crs)


def fetch_3dep_boundaries(url=BOUNDARIES_URL, dest='resources.geojson'):
    """
    Download the 3DEP dataset boundary polygons (maintained by Hobu Inc.) and save a local copy.

    Returns:
        boundaries (GeoDataFrame): one row per 3DEP dataset with 'name', 'url', 'count', geometry (EPSG:4326)
    """
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    with open(dest, 'w') as f:
        f.write(r.content.decode("utf-8"))
    return gpd.read_file(dest)


def find_intersecting_datasets(boundaries, aoi_epsg3857):
    """
    Select the 3DEP datasets whose boundary intersects the AOI.

    Parameters:
        boundaries (GeoDataFrame): 3DEP boundaries in EPSG:4326, as from fetch_3dep_boundaries()
        aoi_epsg3857 (shapely polygon): AOI in Web Mercator

    Returns:
        intersecting (GeoDataFrame): matching rows, with an added 'geometry_3857' column
    """
    projected = boundaries.geometry.to_crs(WEB_MERCATOR)
    mask = projected.intersects(aoi_epsg3857)
    intersecting = boundaries[mask].copy()
    intersecting['geometry_3857'] = projected[mask]
    return intersecting


def estimate_point_count(intersecting, aoi_epsg3857):
    """
    Estimate the number of lidar points in the AOI at full resolution, assuming points are
    spread uniformly over each dataset's footprint. Only the part of the AOI inside each
    dataset counts toward that dataset, so AOIs straddling datasets aren't double counted.

    Parameters:
        intersecting (GeoDataFrame): output of find_intersecting_datasets()
        aoi_epsg3857 (shapely polygon): AOI in Web Mercator

    Returns:
        num_pts_est (int): estimated total point count
    """
    return sum(int((aoi_epsg3857.intersection(geom).area / geom.area) * count)
               for geom, count in zip(intersecting['geometry_3857'], intersecting['count']))
