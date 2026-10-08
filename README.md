# vegetation-assessment

Measure vegetation height from public USGS 3DEP lidar. Pick an area of interest, pull the
point cloud from the AWS EPT bucket, grid it into surface and terrain models, and subtract
them to get a canopy height model (CHM).

```
     lidar  |   |   |   |   |   |   |
            v   v   v   v   v   v   v
           .@@@@@.    ^      .@@@.                  <- DSM: first returns (treetops)
         .@@@@@@@@@.  |    .@@@@@@@.
         @@@@@@@@@@@  |    @@@@@@@@@
          '@@@@@@@'   |     '@@@@@'
             | |      | CHM   | |                   CHM = DSM - DTM
             | |      |       | |    ΛwΛ
             | |      |       | |  <=°∀°=>
             | |      |       | |    /⊃⊂
  ___________|_|______v_______|_|_<<<( O O)______   <- DTM: ground returns (bare earth)
```

The reusable code lives in `src/` (AOI handling, PDAL pipeline builders, raster math) with
tests in `tests/`. The notebooks in `notebooks/` drive the workflow.

## Getting started

1. Install [Miniforge](https://github.com/conda-forge/miniforge), then create the environment:
   ```
   conda env create -f environment.yml
   conda activate veg
   ```
2. Run the tests:
   ```
   pytest
   ```
3. Register the kernel and open a notebook:
   ```
   python -m ipykernel install --user --name veg --display-name "Python (vegetation-assessment)"
   ```
   Then open `notebooks/05_3DEP_Generate_Canopy_Height_Models_User_AOI.ipynb` and select that kernel.

The environment includes PDAL (from conda-forge) so the notebooks can execute pipelines.
The code in `src/` and the tests don't import it.
