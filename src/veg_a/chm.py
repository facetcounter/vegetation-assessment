"""
Canopy height model (CHM) raster math: align a DSM and DTM, difference them, and
downsample for plotting.

Extracted from notebooks/05_3DEP_Generate_Canopy_Height_Models_User_AOI.ipynb.
"""
from rasterio.enums import Resampling


def align_rasters(dsm, dtm):
    """
    Put the DSM and DTM on an identical grid. If their shapes differ, the raster with more
    pixels is reprojected onto the grid of the smaller one. The DSM is then given the DTM's
    exact x/y coordinates so differencing doesn't drop cells over float noise.

    Parameters:
        dsm, dtm (xarray.DataArray): rasters opened with rioxarray

    Returns:
        (dsm, dtm): aligned rasters
    """
    if dsm.shape != dtm.shape:
        if dsm.size > dtm.size:
            dsm = dsm.rio.reproject_match(dtm)
        else:
            dtm = dtm.rio.reproject_match(dsm)

    dsm = dsm.assign_coords({"x": dtm.x, "y": dtm.y})
    return dsm, dtm


def compute_chm(dsm, dtm):
    """
    Canopy height model: CHM = DSM - DTM, on aligned grids. Cells that are NoData in either
    input are NoData in the output, and the DTM's NoData value is carried over so the CHM
    is written with it by .rio.to_raster().

    Parameters:
        dsm, dtm (xarray.DataArray): rasters opened with rioxarray (ideally masked=True)

    Returns:
        chm (xarray.DataArray): canopy height in the units of the inputs
    """
    dsm, dtm = align_rasters(dsm, dtm)
    chm = dsm - dtm

    if dtm.rio.encoded_nodata is not None:
        chm = chm.rio.write_nodata(dtm.rio.encoded_nodata, encoded=True)
    elif dtm.rio.nodata is not None:
        chm = chm.rio.write_nodata(dtm.rio.nodata)
    return chm


def downsample_dem(dem, target_shape=(1000, 1000)):
    """
    Downsample a raster for plotting if it is larger than target_shape. Each axis is clamped
    independently to its target size, using bilinear resampling.

    Parameters:
        dem (xarray.DataArray): raster opened with rioxarray
        target_shape (tuple): maximum (height, width) in pixels

    Returns:
        dem (xarray.DataArray): downsampled raster, or the input unchanged if already small enough
    """
    target_height, target_width = target_shape
    height, width = dem.rio.height, dem.rio.width

    if height <= target_height and width <= target_width:
        return dem

    return dem.rio.reproject(dem.rio.crs,
                             shape=(min(height, target_height), min(width, target_width)),
                             resampling=Resampling.bilinear)
