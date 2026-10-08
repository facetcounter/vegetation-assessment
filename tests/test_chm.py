import numpy as np
import pytest
import rioxarray
import xarray as xr

from src.chm import align_rasters, compute_chm, downsample_dem

NODATA = -9999


def make_raster(values, x0=500_000.0, y0=5_000_000.0, res=2.0):
    """2-D raster in UTM 15N with its upper-left corner at (x0, y0)."""
    values = np.asarray(values, dtype="float32")
    rows, cols = values.shape
    da = xr.DataArray(
        values,
        dims=("y", "x"),
        coords={"y": y0 - res * (np.arange(rows) + 0.5), "x": x0 + res * (np.arange(cols) + 0.5)},
    )
    return da.rio.write_crs("EPSG:32615").rio.write_nodata(NODATA)


def write_and_open(da, path):
    """Round-trip through a GeoTIFF the way the notebook opens PDAL output."""
    da.rio.to_raster(path)
    return rioxarray.open_rasterio(path, masked=True).squeeze("band", drop=True)


def test_align_same_shape_is_noop():
    dsm, dtm = make_raster(np.full((3, 4), 10)), make_raster(np.full((3, 4), 2))
    a_dsm, a_dtm = align_rasters(dsm, dtm)
    assert a_dsm.shape == a_dtm.shape == (3, 4)
    np.testing.assert_array_equal(a_dsm.values, dsm.values)


def test_align_snaps_float_noise_in_coords():
    dsm, dtm = make_raster(np.full((3, 4), 10)), make_raster(np.full((3, 4), 2))
    dsm = dsm.assign_coords(x=dsm.x + 1e-9)
    a_dsm, a_dtm = align_rasters(dsm, dtm)
    assert (a_dsm - a_dtm).shape == (3, 4)


@pytest.mark.parametrize("larger", ["dsm", "dtm"])
def test_align_clips_larger_to_smaller(larger):
    big, small = make_raster(np.ones((6, 6))), make_raster(np.ones((4, 5)))
    dsm, dtm = (big, small) if larger == "dsm" else (small, big)
    a_dsm, a_dtm = align_rasters(dsm, dtm)
    assert a_dsm.shape == a_dtm.shape == (4, 5)


def test_compute_chm_values(tmp_path):
    dsm = write_and_open(make_raster([[12, 15], [3, 30]]), tmp_path / "dsm.tif")
    dtm = write_and_open(make_raster([[2, 5], [3, 10]]), tmp_path / "dtm.tif")
    chm = compute_chm(dsm, dtm)
    np.testing.assert_array_equal(chm.values, [[10, 10], [0, 20]])


def test_compute_chm_propagates_nodata(tmp_path):
    dsm = write_and_open(make_raster([[12, NODATA], [3, 30]]), tmp_path / "dsm.tif")
    dtm = write_and_open(make_raster([[2, 5], [NODATA, 10]]), tmp_path / "dtm.tif")
    chm = compute_chm(dsm, dtm)
    assert np.isnan(chm.values[0, 1]) and np.isnan(chm.values[1, 0])
    assert chm.values[1, 1] == 20


def test_compute_chm_writes_nodata_to_geotiff(tmp_path):
    dsm = write_and_open(make_raster([[12, NODATA], [7, 8]]), tmp_path / "dsm.tif")
    dtm = write_and_open(make_raster([[2, 5], [1, 1]]), tmp_path / "dtm.tif")
    compute_chm(dsm, dtm).rio.to_raster(tmp_path / "chm.tif")

    raw = rioxarray.open_rasterio(tmp_path / "chm.tif")
    assert raw.rio.nodata == NODATA
    np.testing.assert_array_equal(raw.values.squeeze(), [[10, NODATA], [6, 7]])
    assert raw.rio.crs.to_epsg() == 32615


def test_downsample_small_raster_unchanged():
    dem = make_raster(np.ones((10, 20)))
    assert downsample_dem(dem, target_shape=(10, 20)) is dem


def test_downsample_clamps_each_axis():
    # Tall, narrow raster: only the height should shrink.
    dem = make_raster(np.ones((40, 8)))
    out = downsample_dem(dem, target_shape=(10, 10))
    assert (out.rio.height, out.rio.width) == (10, 8)


def test_downsample_preserves_extent():
    dem = make_raster(np.random.default_rng(0).random((50, 30)))
    out = downsample_dem(dem, target_shape=(10, 10))
    assert (out.rio.height, out.rio.width) == (10, 10)
    np.testing.assert_allclose(out.rio.bounds(), dem.rio.bounds())
