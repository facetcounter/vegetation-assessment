# Testing

Tests use [pytest](https://docs.pytest.org/) and live in `tests/`. They cover the code in
`src/`, not the notebooks. They run offline on small synthetic data, without needing PDAL,
and take a couple of seconds.

## Running tests

From the repo root, with the `veg` environment (see the README):

```
conda activate veg
pytest
```

If your shell isn't set up for `conda activate`, run it through conda instead:

```
~/miniforge3/bin/conda run -n veg pytest
```

`pytest.ini` puts the repo root on the import path, so tests import `src.*` directly. Always
run pytest from the repo root.

Useful variations:

| Command | What it does |
|---|---|
| `pytest -v` | List each test by name |
| `pytest tests/test_chm.py` | Run one file |
| `pytest tests/test_chm.py::test_compute_chm_values` | Run one test |
| `pytest -k nodata` | Run tests whose names contain "nodata" |
| `pytest -x` | Stop at the first failure |
| `pytest -p no:warnings` | Hide the warnings summary |

Some deprecation warnings come from the libraries themselves (rioxarray, Shapely). They're
safe to ignore.

## What's covered

| File | Module | Covers |
|---|---|---|
| `tests/test_aoi.py` | `src/aoi.py` | Reprojection, shapefile import, finding intersecting 3DEP datasets, point count estimate |
| `tests/test_pipelines.py` | `src/pipelines.py` | PDAL pipeline structure: readers, filters, writers, DSM vs. DTM, argument validation |
| `tests/test_chm.py` | `src/chm.py` | DSM/DTM alignment, CHM values, NoData handling, GeoTIFF output, downsampling |

**Not covered:** downloading the 3DEP catalog (`fetch_3dep_boundaries`), actually running
PDAL pipelines, and the notebooks themselves. See "Manual end-to-end check" below.

## Writing tests

- **Keep them offline and fast.** Build small inputs in the test instead of downloading data.
- **Use `tmp_path`** (a pytest fixture) for any files a test writes.
- **Don't import PDAL.** Pipeline tests check the dicts that `src/pipelines.py` builds.
- **For rasters, use the helpers in `tests/test_chm.py`:**
  - `make_raster(values, x0, y0, res)` builds a georeferenced 2-D raster (UTM 15N, NoData
    -9999) from a nested list or array. Use at least 2 rows and 2 columns; with a single row
    or column, rioxarray can't work out the geotransform.
  - `write_and_open(da, path)` writes a raster to GeoTIFF and reopens it with
    `masked=True`, the way the notebook opens PDAL output.
- **For geometry, build shapes with `shapely.geometry.box`** and compare them with
  `pytest.approx` or `equals_exact`. Shapefiles reorder polygon vertices, so normalize shapes
  read from a shapefile before comparing: `a.normalize().equals_exact(b.normalize(), tol)`.

## Manual end-to-end check

To check the full workflow against real 3DEP data (needs network access and PDAL), run this
from a scratch directory. It fetches a ~200 m square in Minneapolis and builds a CHM:

```python
import json, pdal, rioxarray
from shapely.geometry import box
from src.aoi import fetch_3dep_boundaries, find_intersecting_datasets, gcs_to_proj
from src.pipelines import make_DEM_pipeline
from src.chm import compute_chm

aoi = gcs_to_proj(box(-93.2370, 44.9580, -93.2345, 44.9598))
names = list(find_intersecting_datasets(fetch_3dep_boundaries(), aoi)['name'])
for kind in ('dsm', 'dtm'):
    p = make_DEM_pipeline(aoi.wkt, names[:1], 2.0, 2.0, demType=kind, dem_outName=kind)
    pdal.Pipeline(json.dumps(p)).execute_streaming(chunk_size=1000000)

chm = compute_chm(rioxarray.open_rasterio('dsm.tif', masked=True),
                  rioxarray.open_rasterio('dtm.tif', masked=True))
print(chm.shape, float(chm.median()), float(chm.max()))
```

Run it with the repo root on the path, e.g.
`PYTHONPATH=/path/to/vegetation-assessment python check.py`. Expect a CHM of about 140×140
cells, with a median of a few meters and a maximum under ~20 m.
