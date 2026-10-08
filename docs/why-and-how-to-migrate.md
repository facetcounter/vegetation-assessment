# Why and how to migrate

This repo started as notebooks with all the logic defined in cells. The reusable code now
lives in a Python package, `veg_a` (`src/veg_a/`), with tests, and the notebooks import it.
This doc explains why, what changes day to day, and how to get comfortable with it.

## Why

- **The code is tested.** `tests/` checks the AOI handling, the PDAL pipeline builders, and
  the canopy height math on small synthetic data in a couple of seconds. Writing those tests
  turned up real bugs from the original notebook (for example, the downsampling swapped
  height and width, and the CHM was saved without its -9999 NoData value).
- **One copy of each function.** Both notebooks import the same code instead of each
  keeping its own copy that drifts apart.
- **Reproducible setup.** `environment.yml` creates the whole environment, including PDAL,
  with one command.
- **Notebooks get shorter.** They read as the workflow: pick an AOI, build pipelines, make
  the CHM, plot it.

## What changed

| Before | Now |
|---|---|
| Functions defined in notebook cells | Functions in `src/veg_a/` (`aoi.py`, `pipelines.py`, `chm.py`), imported by the notebooks |
| `OT-requirements.txt`, environment by hand | `environment.yml` (conda), which also installs `veg_a` |
| No tests | `tests/`, run with `pytest` |

## How to migrate

1. Install [Miniforge](https://github.com/conda-forge/miniforge) if you don't have conda.
2. From the repo root, create the environment:
   ```
   conda env create -f environment.yml
   ```
   If you created `veg` before the `veg_a` package existed, update it instead:
   ```
   conda env update -n veg -f environment.yml --prune
   ```
3. Check that it works:
   ```
   conda run -n veg pytest
   ```
4. Open a notebook (`conda run -n veg jupyter lab`, or VS Code with the `veg` kernel).

Run the update command from step 2 whenever you pull changes to `environment.yml`.

## What will feel different, and how to handle it

### Editing code doesn't show up in a running notebook

A running Jupyter kernel keeps the first version of `veg_a` it imported. If you edit
`src/veg_a/chm.py`, the notebook keeps using the old code until you either:

- restart the kernel, or
- turn on autoreload once at the top of the notebook:
  ```
  %load_ext autoreload
  %autoreload 2
  ```

This is the most common "my change isn't working" moment.

### Why `import veg_a` works is invisible

Creating the environment runs `pip install -e .`, which uses `pyproject.toml` to install
`veg_a` in editable mode: Python loads it straight from `src/veg_a/`, so edits take effect
without reinstalling. If you see `ModuleNotFoundError: No module named 'veg_a'`, check:

- **The kernel.** The notebook must use the `veg` environment, not base or another Python.
- **The environment is current.** Run the update command from step 2.
- **Where the file is.** New modules must go in `src/veg_a/` to be importable as
  `veg_a.<name>`.

### Environments are their own thing

Each conda environment is a separate Python with its own packages. `veg` is this project's.

- `conda run -n veg <command>` runs one command in it, with no setup.
- `conda activate veg` switches your terminal to it, but needs `conda init` once first.
- In VS Code and Jupyter, the kernel you pick decides the environment. Pick `veg`.

### Debugging inside functions

In a notebook, every variable stays around to inspect. Inside a `veg_a` function they
disappear when it returns. Some options:

- Copy the function body into a cell temporarily and run it step by step.
- Add `breakpoint()` in the function to pause there (works in Jupyter and VS Code).
- Use the VS Code debugger on a notebook cell or a test.

### Writing tests

See [testing.md](testing.md) for commands and conventions. To get started, copy an existing
test, change its inputs and expected result, and run it with
`conda run -n veg pytest -k <name>`. Tests should build small inputs themselves (the
`make_raster` helper in `tests/test_chm.py` makes rasters) rather than download data.

### Deciding where code goes

- **In `veg_a`:** logic you'll reuse or want tested, such as reprojection, pipeline building
  and raster math.
- **In the notebook:** interactive maps, plotting, one-off exploration, and the order the
  steps run in.

When you change a function's arguments, search the notebooks and `tests/` for its uses and
update them too.

### Git with notebooks

- Notebook files are JSON, so diffs are noisy. Clearing outputs before committing
  (*Edit → Clear Outputs of All Cells* in JupyterLab) keeps diffs small and readable.
- Generated files (`.tif`, `.las`, `.laz`, `resources.geojson`) are written next to the
  notebooks. They're gitignored, but still check `git status` before committing.
