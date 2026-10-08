"""
Builders for PDAL pipelines that fetch 3DEP point clouds from the AWS EPT bucket and grid
them into DEMs. Pipelines are plain dicts; serialize with json.dumps() and run them with
pdal.Pipeline() or the `pdal pipeline` CLI. PDAL itself is not imported here.

Extracted from notebooks/05_3DEP_Generate_Canopy_Height_Models_User_AOI.ipynb.
"""

EPT_URL = "https://s3-us-west-2.amazonaws.com/usgs-lidar-public/{}/ept.json"
DEM_NODATA = -9999
DEM_GDALOPTS = "COMPRESS=LZW,TILED=YES,blockxsize=256,blockysize=256,COPY_SRC_OVERVIEWS=YES"


def build_pdal_pipeline(extent_epsg3857, usgs_3dep_dataset_names, pc_resolution, filterNoise=False,
                        reclassify=False, savePointCloud=True, outCRS=3857, pc_outName='filter_test',
                        pc_outType='laz'):
    """
    Build a PDAL pipeline for requesting, processing, and (optionally) saving point cloud data.

    Parameters:
        extent_epsg3857 (shapely polygon or WKT str): AOI in Web Mercator (EPSG:3857)
        usgs_3dep_dataset_names (list of str): 3DEP dataset(s) to read from
        pc_resolution (float): EPT resolution limit, as a grid cell edge length in meters
            (see https://pdal.io/stages/readers.ept.html#readers-ept)
        filterNoise (bool): Remove USGS Class 7 (Low Noise) and Class 18 (High Noise) points
        reclassify (bool): Drop USGS classes and run SMRF to classify ground points only
        savePointCloud (bool): Write the point cloud to disk
        outCRS (int): Output CRS as an EPSG code
        pc_outName (str): Output point cloud name, without extension
        pc_outType (str): 'las' or 'laz'

    Returns:
        pointcloud_pipeline (dict): {'pipeline': [stage, ...]}

    Raises:
        ValueError: If savePointCloud and pc_outType is not 'las' or 'laz'.
    """
    stages = [
        {
            "type": "readers.ept",
            "filename": EPT_URL.format(name),
            "polygon": str(extent_epsg3857),
            "requests": 3,
            "resolution": pc_resolution,
        }
        for name in usgs_3dep_dataset_names
    ]

    if filterNoise:
        stages.append({"type": "filters.range", "limits": "Classification![7:7]"})
        stages.append({"type": "filters.range", "limits": "Classification![18:18]"})

    if reclassify:
        stages.append({"type": "filters.assign", "value": "Classification = 0"})
        stages.append({"type": "filters.smrf"})
        stages.append({"type": "filters.range", "limits": "Classification[2:2]"})

    stages.append({"type": "filters.reprojection", "out_srs": "EPSG:{}".format(outCRS)})

    if savePointCloud:
        if pc_outType not in ('las', 'laz'):
            raise ValueError("pc_outType must be 'las' or 'laz'.")
        writer = {"type": "writers.las", "filename": "{}.{}".format(pc_outName, pc_outType)}
        if pc_outType == 'laz':
            writer["compression"] = "laszip"
        stages.append(writer)

    return {"pipeline": stages}


def make_DEM_pipeline(extent_epsg3857, usgs_3dep_dataset_name, pc_resolution, dem_resolution,
                      filterNoise=True, reclassify=False, savePointCloud=False, outCRS=3857,
                      pc_outName='filter_test', pc_outType='laz', demType='dtm', gridMethod='idw',
                      dem_outName='dem_test', dem_outExt='tif', driver="GTiff"):
    """
    Build a PDAL pipeline that produces a DEM: a digital surface model ('dsm', all returns) or
    a digital terrain model ('dtm', ground returns only, USGS Class 2).

    Point cloud parameters are as for build_pdal_pipeline(). DEM parameters:
        dem_resolution (float): Output grid size in meters
        demType (str): 'dsm' or 'dtm'
        gridMethod (str): 'min', 'mean', 'max', or 'idw'
        dem_outName (str): Output DEM name, without extension
        dem_outExt (str): Output DEM extension (must match `driver`)
        driver (str): GDAL raster driver

    Returns:
        dem_pipeline (dict): {'pipeline': [stage, ...]}

    Raises:
        ValueError: If demType is not 'dsm' or 'dtm', or pc_outType is invalid.
    """
    if demType not in ('dsm', 'dtm'):
        raise ValueError("demType must be 'dsm' or 'dtm'.")

    dem_pipeline = build_pdal_pipeline(extent_epsg3857, usgs_3dep_dataset_name, pc_resolution,
                                       filterNoise=filterNoise, reclassify=reclassify,
                                       savePointCloud=savePointCloud, outCRS=outCRS,
                                       pc_outName=pc_outName, pc_outType=pc_outType)

    if demType == 'dtm':
        dem_pipeline['pipeline'].append({"type": "filters.range", "limits": "Classification[2:2]"})

    dem_pipeline['pipeline'].append({
        "type": "writers.gdal",
        "filename": "{}.{}".format(dem_outName, dem_outExt),
        "gdaldriver": driver,
        "nodata": DEM_NODATA,
        "output_type": gridMethod,
        "resolution": float(dem_resolution),
        "gdalopts": DEM_GDALOPTS,
    })

    return dem_pipeline
