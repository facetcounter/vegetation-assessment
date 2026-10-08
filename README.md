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

The reusable code is the `veg_a` package in `src/veg_a/` (AOI handling, PDAL pipeline builders, raster math) with
tests in `tests/`. The notebooks in `notebooks/` drive the workflow.

## Getting started

1. Install [Miniforge](https://github.com/conda-forge/miniforge). If you already have
   Anaconda or Miniconda, that works too; the environment pulls only from conda-forge.
2. Create the environment (run this from the repo root):
   ```
   conda env create -f environment.yml
   ```
3. Run the tests:
   ```
   conda run -n veg pytest
   ```
   This works without `conda activate`. To use `conda activate veg` instead, run
   `conda init` once and open a new terminal.
4. Open a notebook, either with JupyterLab:
   ```
   conda run -n veg jupyter lab
   ```
   or in VS Code: open a notebook in `notebooks/` and choose the `veg` environment as the
   kernel. If VS Code doesn't list it, register it once with
   `conda run -n veg python -m ipykernel install --user --name veg --display-name "Python (vegetation-assessment)"`.

   To try the workflow without your own shapefile, set `shapefile_path` in notebook 05 to
   `'../examples/seward_sample_aoi.geojson'` (a ~200 m square in Minneapolis).

When `environment.yml` changes, update your environment with:
```
conda env update -n veg -f environment.yml --prune
```

The environment includes PDAL (from conda-forge) so the notebooks can execute pipelines.
The `veg_a` package and the tests don't import it.

## Docs

- [Testing](docs/testing.md): running and writing tests
- [Why and how to migrate](docs/why-and-how-to-migrate.md): what changed from the notebook-only setup and how to work with the package
- [Possible open issues](docs/possible-open-issues.md): known problems and open questions
