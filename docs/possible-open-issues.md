# Possible open issues

## DEMs are gridded in Web Mercator, so cell sizes aren't true meters

The PDAL pipelines (`veg_a/pipelines.py`, as used by notebook 05) reproject points to
EPSG:3857 (`outCRS=3857`) before gridding. Web Mercator units are only true meters at the
equator; they stretch by 1/cos(latitude). At Minneapolis (~45°N) a "2 m" DEM cell is about
1.4 m on the ground, and areas computed in 3857 are about 2x too large.

Seen in a real run: a ~200 m AOI in Seward came out as a 142×140 grid at "2 m" resolution.

- Canopy heights are unaffected, since Z values stay in real meters.
- Point count estimates are unaffected, since they are area ratios within the same CRS.
- **Possible fix:** grid in a meter-based CRS, e.g. `outCRS=32615` (UTM 15N), which
  `prepare-inputs.ipynb` already names as the project CRS.

## `prepare-inputs.ipynb` is unfinished

Cells 4 and 6 have syntax errors, and cell 10 is empty. These look like work in progress
toward a non-interactive version of notebook 05:

- **Cell 4:** `PROEJCT_CRS = EPSG:32615` is presumably meant to be
  `PROJECT_CRS = "EPSG:32615"`, a single CRS for all outputs.
- **Cell 6:** `read_aoi()` and an unfinished `def` are stubs for the steps in the cell 8
  outline (read AOI → validate → standardize CRS → download catalog → find datasets →
  report → fetch point clouds).
- **Cell 10:** the empty cell is the planned 3DEP catalog download.

`veg_a/aoi.py` already covers reading the AOI, the catalog download, finding intersecting
datasets, and the point estimate. Still missing:

- AOI validation beyond the missing-CRS check (invalid or multipart geometry)
- Reprojecting to the project CRS

## Affects results

Numbers below are from a real run on a ~200 m AOI in Seward, Minneapolis.

- **Buildings are counted as canopy.** CHM = DSM − DTM uses all first returns, so roofs
  show up as vegetation height. For a vegetation assessment the DSM should probably use only
  vegetation classes (3–5), or at least exclude buildings (class 6).
- **Overlapping 3DEP datasets get merged.** The Seward AOI matched both
  `MN_CentralMissRiver_4_B22` and `MN_FullState`, which are separate lidar collections of the
  same ground. Notebook 05 reads every match, mixing surveys, and the point estimate adds
  them together.
- **DSM and DTM come out on different grids.** PDAL sizes each grid to its own points
  (DSM 143 rows vs. DTM 142 here). `align_rasters` resamples to fix this, which shifts values
  slightly. Passing the same explicit `bounds` to both `writers.gdal` stages would make the
  grids identical.
- **The DTM has holes.** 7% of DTM cells had no ground points (probably under buildings), so
  7% of the CHM is NoData. `writers.gdal`'s `window_size` option can fill small gaps.
- **Some heights are negative.** 2.6% of CHM cells were below zero (min −0.4 m), likely
  interpolation artifacts. There's no clipping or QA step.

## Workflow and repo hygiene

- **Colab path is broken.** The Colab setup cells clone the upstream OpenTopography repo, so
  the `veg_a` package isn't installed there.
- **Streaming vs. reclassify is a manual toggle.** `execute_streaming()` or `execute()` has
  to be chosen by commenting lines to match `reclassify`; the wrong one fails or runs out of
  memory.

## Smaller items

- No automated tests for the network or PDAL parts; CI runs only the offline tests.
- `shapely.ops.transform` (used in `veg_a/aoi.py`) is deprecated in current Shapely.
- **Attribution (unverified).** The code in `veg_a` is adapted from OpenTopography's
  notebooks, and this repo is GPL-3.0. Their license terms and attribution are worth checking.
