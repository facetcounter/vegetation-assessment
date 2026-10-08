import json

import pytest
from shapely.geometry import box

from veg_a.pipelines import EPT_URL, build_pdal_pipeline, make_DEM_pipeline

AOI = box(-10_000_000, 5_000_000, -9_999_000, 5_001_000)


def stage_types(pipeline):
    return [stage["type"] for stage in pipeline["pipeline"]]


def test_one_reader_per_dataset():
    p = build_pdal_pipeline(AOI, ["DS_A", "DS_B"], 2.0, savePointCloud=False)
    readers = [s for s in p["pipeline"] if s["type"] == "readers.ept"]
    assert [r["filename"] for r in readers] == [EPT_URL.format("DS_A"), EPT_URL.format("DS_B")]
    assert all(r["polygon"] == AOI.wkt for r in readers)
    assert all(r["resolution"] == 2.0 for r in readers)


def test_minimal_pipeline_reads_then_reprojects():
    p = build_pdal_pipeline(AOI, ["DS"], 1.0, savePointCloud=False, outCRS=32615)
    assert stage_types(p) == ["readers.ept", "filters.reprojection"]
    assert p["pipeline"][-1]["out_srs"] == "EPSG:32615"


def test_accepts_wkt_string_extent():
    p = build_pdal_pipeline(AOI.wkt, ["DS"], 1.0, savePointCloud=False)
    assert p["pipeline"][0]["polygon"] == AOI.wkt


def test_filter_noise_removes_classes_7_and_18():
    p = build_pdal_pipeline(AOI, ["DS"], 1.0, filterNoise=True, savePointCloud=False)
    limits = [s["limits"] for s in p["pipeline"] if s["type"] == "filters.range"]
    assert limits == ["Classification![7:7]", "Classification![18:18]"]


def test_reclassify_runs_smrf_and_keeps_ground():
    p = build_pdal_pipeline(AOI, ["DS"], 1.0, reclassify=True, savePointCloud=False)
    assert stage_types(p) == ["readers.ept", "filters.assign", "filters.smrf",
                              "filters.range", "filters.reprojection"]
    assert p["pipeline"][3]["limits"] == "Classification[2:2]"


@pytest.mark.parametrize("ext, compressed", [("las", False), ("laz", True)])
def test_point_cloud_writer(ext, compressed):
    p = build_pdal_pipeline(AOI, ["DS"], 1.0, pc_outName="out", pc_outType=ext)
    writer = p["pipeline"][-1]
    assert writer["type"] == "writers.las"
    assert writer["filename"] == f"out.{ext}"
    assert ("compression" in writer) == compressed


def test_bad_point_cloud_type_raises():
    with pytest.raises(ValueError):
        build_pdal_pipeline(AOI, ["DS"], 1.0, pc_outType="ply")


def test_bad_point_cloud_type_ignored_when_not_saving():
    p = build_pdal_pipeline(AOI, ["DS"], 1.0, savePointCloud=False, pc_outType="ply")
    assert "writers.las" not in stage_types(p)


def test_dtm_filters_ground_before_gridding():
    p = make_DEM_pipeline(AOI, ["DS"], 1.0, 2, demType="dtm", dem_outName="dtm")
    assert stage_types(p)[-2:] == ["filters.range", "writers.gdal"]
    assert p["pipeline"][-2]["limits"] == "Classification[2:2]"
    writer = p["pipeline"][-1]
    assert writer["filename"] == "dtm.tif"
    assert writer["resolution"] == 2.0
    assert writer["nodata"] == -9999


def test_dsm_uses_all_returns():
    p = make_DEM_pipeline(AOI, ["DS"], 1.0, 2.0, filterNoise=False, demType="dsm", gridMethod="max")
    assert stage_types(p) == ["readers.ept", "filters.reprojection", "writers.gdal"]
    assert p["pipeline"][-1]["output_type"] == "max"


def test_bad_dem_type_raises():
    with pytest.raises(ValueError):
        make_DEM_pipeline(AOI, ["DS"], 1.0, 2.0, demType="chm")


def test_pipeline_is_json_serializable():
    p = make_DEM_pipeline(AOI, ["DS"], 1.0, 2.0, reclassify=True, savePointCloud=True)
    assert json.loads(json.dumps(p)) == p
