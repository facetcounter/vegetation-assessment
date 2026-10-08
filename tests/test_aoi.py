from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Point, box

from veg_a.aoi import (estimate_point_count, find_intersecting_datasets, gcs_to_proj,
                     import_shapefile_to_shapely, proj_to_3857)

SAMPLE_AOI = Path(__file__).resolve().parent.parent / "examples" / "seward_sample_aoi.geojson"

# Length of one degree of longitude at the equator in Web Mercator meters.
DEG_3857 = 111_319.490793


def test_gcs_to_proj_known_point():
    p = gcs_to_proj(Point(1, 0))
    assert p.x == pytest.approx(DEG_3857)
    assert p.y == pytest.approx(0, abs=1e-6)


def test_proj_to_3857_from_utm():
    # A 1 km square in UTM 15N, near Minneapolis.
    utm = box(480_000, 4_980_000, 481_000, 4_981_000)
    gcs, wm = proj_to_3857(utm, "EPSG:32615")
    lon, lat = gcs.centroid.x, gcs.centroid.y
    assert -94 < lon < -93 and 44 < lat < 45
    # Web Mercator inflates area by ~1/cos(lat)^2 (about 2x at 45N).
    assert 1.8e6 < wm.area < 2.2e6


def test_import_shapefile(tmp_path):
    utm = box(480_000, 4_980_000, 481_000, 4_981_000)
    path = tmp_path / "aoi.shp"
    gpd.GeoDataFrame(geometry=[utm], crs="EPSG:32615").to_file(path)

    gcs, wm = import_shapefile_to_shapely(path)
    expected_gcs, expected_wm = proj_to_3857(utm, "EPSG:32615")
    # Shapefiles rewind rings clockwise, so compare with vertex order normalized.
    assert gcs.normalize().equals_exact(expected_gcs.normalize(), 1e-9)
    assert wm.normalize().equals_exact(expected_wm.normalize(), 1e-3)


def test_sample_aoi_loads():
    gcs, wm = import_shapefile_to_shapely(SAMPLE_AOI)
    assert gcs.is_valid
    assert -93.24 < gcs.centroid.x < -93.23 and 44.95 < gcs.centroid.y < 44.97
    # ~200 m square on the ground; Web Mercator inflates area ~2x at 45N.
    assert 0.6e5 < wm.area < 1.2e5


def test_import_shapefile_without_crs_raises(tmp_path):
    path = tmp_path / "aoi.shp"
    gpd.GeoDataFrame(geometry=[box(0, 0, 1, 1)]).to_file(path)
    with pytest.raises(ValueError):
        import_shapefile_to_shapely(path)


@pytest.fixture
def boundaries():
    return gpd.GeoDataFrame(
        {"name": ["west", "east", "far"], "url": ["w", "e", "f"], "count": [1000, 4000, 1]},
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1), box(50, 50, 51, 51)],
        crs="EPSG:4326",
    )


def test_find_intersecting_datasets(boundaries):
    aoi = gcs_to_proj(box(0.9, 0.4, 1.1, 0.6))  # straddles west/east
    hits = find_intersecting_datasets(boundaries, aoi)
    assert list(hits["name"]) == ["west", "east"]
    assert hits["geometry_3857"].iloc[0].equals_exact(gcs_to_proj(box(0, 0, 1, 1)), 1e-3)


def test_find_intersecting_datasets_none(boundaries):
    hits = find_intersecting_datasets(boundaries, gcs_to_proj(box(20, 20, 21, 21)))
    assert hits.empty


def test_estimate_point_count(boundaries):
    # AOI covers an eighth of 'west' (1000 pts) and an eighth of 'east' (4000 pts).
    aoi = gcs_to_proj(box(0.75, 0, 1.25, 0.5))
    hits = find_intersecting_datasets(boundaries, aoi)
    assert estimate_point_count(hits, aoi) == pytest.approx(125 + 500, rel=0.01)
