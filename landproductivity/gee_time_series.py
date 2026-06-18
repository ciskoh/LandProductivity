"""Google Earth Engine vegetation time-series retrieval for LandProductivity.

Server-side counterpart of ``time_series.py``.  Every function operates on
``ee.ImageCollection`` / ``ee.Image`` objects and requires an authenticated
Earth Engine session.

The public entry point is ``get_veg_time_series``; it mirrors the
original ``getVegTimeSeries.js`` GEE script and is imported in
``__init__.py`` as ``gee_get_veg_time_series``.

Used by:
    * The GEE-based analysis notebook / dashboard.
"""

from __future__ import annotations

from typing import Any

try:
    import ee
except ImportError:  # pragma: no cover
    ee = None  # type: ignore[assignment]


def _ensure_ee() -> None:
    """Raise ``ImportError`` if the ``ee`` package is not available."""
    if ee is None:
        raise ImportError(
            "Google Earth Engine Python API is required to use this module"
        )


def create_date_range_list(start_date: Any, date_interval: int) -> Any:
    """Build a server-side list of date ranges for regular time steps.

    Each range is centred on a step date and extends
    ± ``date_interval / 2`` days.

    Args:
        start_date: ``ee.Date`` or date string for the first step.
        date_interval: Days between consecutive step centres.

    Returns:
        ``ee.List`` of ``ee.DateRange`` objects.

    Used by ``get_veg_time_series``.
    """
    _ensure_ee()
    day_diff = ee.Date(ee.Date.now()).difference(start_date, "day").ceil()
    step_list = ee.List.sequence(0, day_diff, ee.Number(date_interval))
    half = ee.Number(date_interval).divide(2).floor()

    def make_range(n: Any) -> Any:
        centre = ee.Date(start_date).advance(n, "day")
        return ee.DateRange(
            centre.advance(half.multiply(-1), "day"),
            centre.advance(half, "day"),
        )

    return step_list.map(make_range)


def filter_bounds_and_dates(collection: Any, aoi_geom: Any) -> Any:
    """Filter an image collection to an area of interest.

    Args:
        collection: ``ee.ImageCollection`` to filter.
        aoi_geom: ``ee.Geometry`` bounding box / polygon.

    Returns:
        Spatially filtered ``ee.ImageCollection``.

    Used by ``get_veg_time_series``.
    """
    _ensure_ee()
    return collection.filterBounds(aoi_geom)


def mask_clouds(img: Any) -> Any:
    """Apply the standard Landsat SR cloud mask.

    Relies on the external ``users/fitoprincipe/geetools:cloud_masks``
    module hosted on Earth Engine.

    Args:
        img: ``ee.Image`` — a Landsat Surface Reflectance scene.

    Returns:
        Cloud-masked ``ee.Image``.

    Used by ``get_veg_time_series`` (mapped over the merged collection).
    """
    _ensure_ee()
    cloud_masks = ee.FeatureCollection("users/fitoprincipe/geetools:cloud_masks")
    return cloud_masks.landsatSR()(img)


def get_landsat_code(image_id: str) -> str:
    """Extract the Landsat satellite code from an image identifier.

    Args:
        image_id: Scene identifier (e.g. ``"LANDSAT/LC08/…"``).

    Returns:
        One of ``"LT05"``, ``"LE07"`` or ``"LC08"``.  Defaults to
        ``"LC08"`` when none is recognised.

    Used by ``calc_ndvi`` and ``calc_vegetation_index``.
    """
    for code in ("LT05", "LE07", "LC08"):
        if code in image_id:
            return code
    return "LC08"


def calc_ndvi(img: Any) -> Any:
    """Compute NDVI for a Landsat scene using the correct band pair.

    Band mapping:
        * LT05 / LE07 → B4 (NIR), B3 (Red)
        * LC08 → B5 (NIR), B4 (Red)

    Args:
        img: ``ee.Image`` — a Landsat scene.

    Returns:
        ``ee.Image`` with bands ``["ndvi", "pixel_qa"]``.

    Used by ``calc_vegetation_index``.
    """
    _ensure_ee()
    sat = get_landsat_code(img.id())
    bands = {
        "LT05": ["B4", "B3"],
        "LE07": ["B4", "B3"],
        "LC08": ["B5", "B4"],
    }
    nir_red = bands.get(sat, ["B5", "B4"])
    ndvi_img = img.normalizedDifference(nir_red)
    return (
        ee.Image([ndvi_img, img.select(["pixel_qa"])])
        .rename(["ndvi", "pixel_qa"])
        .set({"vegetation_index": "ndvi"})
    )


def make_simple_quality_band(img_collection: Any, im_number: Any) -> Any:
    """Create a simple quality band as valid-pixel count / total images.

    Args:
        img_collection: ``ee.ImageCollection`` of NDVI images.
        im_number: Total number of images (``ee.Number``).

    Returns:
        ``ee.Image`` with a single ``"simpleQA"`` band in ``[0, 1]``.

    Used by ``create_veg_and_quality_band``.
    """
    _ensure_ee()
    return (
        ee.ImageCollection(img_collection.select(0))
        .count()
        .divide(ee.Image.constant(im_number))
        .rename(["simpleQA"])
    )


def calc_vegetation_index(img: Any) -> Any:
    """Compute NDVI and attach satellite metadata to a scene.

    Args:
        img: ``ee.Image`` — a Landsat scene.

    Returns:
        ``ee.Image`` with NDVI band and ``"satellite_type"`` property.

    Used by ``create_veg_and_quality_band``.
    """
    _ensure_ee()
    return calc_ndvi(img).set({"satellite_type": get_landsat_code(img.id())})


def create_veg_and_quality_band(ts_coll: Any) -> Any:
    """Build a vegetation mosaic and quality band for one time step.

    Uses a quality-mosaic approach: the pixel with the highest QA value
    is selected, then a simple quality band is appended.

    Args:
        ts_coll: ``ee.ImageCollection`` for a single time step (with
            ``"date"`` and ``"size"`` properties).

    Returns:
        ``ee.Image`` with NDVI + simpleQA bands and metadata.

    Used by ``get_veg_time_series``.
    """
    _ensure_ee()
    veg_coll = ee.ImageCollection(ts_coll).map(calc_vegetation_index)
    qa = make_simple_quality_band(veg_coll, ee.ImageCollection(veg_coll).size())
    mosaic = ee.Image([veg_coll.qualityMosaic("pixel_qa").select(0), qa])
    return mosaic.set({
        "date": ts_coll.get("date"),
        "size": ts_coll.get("size"),
        "vegetation_index": veg_coll.first().get("vegetation_index"),
        "satellite_type": ee.List(
            veg_coll.aggregate_array("satellite_type")
        ).get(0),
    })


def make_time_step_coll(date_range_list: Any, img_collection: Any) -> Any:
    """Group images into time steps and discard empty steps.

    Args:
        date_range_list: ``ee.List`` of ``ee.DateRange`` objects.
        img_collection: ``ee.ImageCollection`` of cloud-masked scenes.

    Returns:
        ``ee.List`` of sub-collections with ``"date"`` and ``"size"``
        properties, filtered to non-empty steps.

    Used by ``get_veg_time_series``.
    """
    _ensure_ee()

    def make_step(dr: Any) -> Any:
        d_range = ee.DateRange(dr)
        sub = img_collection.filterDate(d_range.start(), d_range.end())
        midpoint = d_range.start().advance(
            d_range.end().difference(d_range.start(), "day").divide(2).floor(),
            "day",
        )
        size = ee.Algorithms.If(
            ee.ImageCollection(sub).size().gt(0),
            ee.ImageCollection(sub).size(),
            0,
        )
        return sub.set({"date": midpoint, "size": size})

    return ee.List(date_range_list.map(make_step)).filter(
        ee.Filter.gt("size", 0)
    )


def get_veg_time_series(
    aoi_geom: Any,
    st_date: Any,
    date_interval: int,
) -> Any:
    """Build a vegetation time-series collection on Earth Engine.

    This is the main entry point of the module.  It mirrors the original
    ``getVegTimeSeries`` JavaScript function:

    1. Merge Landsat 5 / 7 / 8 SR collections filtered to the AOI.
    2. Apply cloud masking.
    3. Group into regular time steps.
    4. Compute NDVI + quality mosaic per step.

    Args:
        aoi_geom: ``ee.Geometry`` area of interest.
        st_date: ``ee.Date`` or date string — start of the series.
        date_interval: Days between consecutive time steps.

    Returns:
        ``ee.ImageCollection`` of NDVI mosaics clipped to the AOI,
        with ``"date_limits"`` and ``"vegetation_index"`` metadata.
    """
    _ensure_ee()
    boundary = ee.DateRange(st_date, ee.Date(ee.Date.now()))

    ls5 = ee.ImageCollection("LANDSAT/LT05/C01/T1_SR")
    ls7 = ee.ImageCollection("LANDSAT/LE07/C01/T1_SR")
    ls8 = ee.ImageCollection("LANDSAT/LC08/C01/T1_SR")

    merged = (
        filter_bounds_and_dates(ls5, aoi_geom)
        .merge(filter_bounds_and_dates(ls7, aoi_geom))
        .merge(filter_bounds_and_dates(ls8, aoi_geom))
    )
    no_clouds = ee.ImageCollection(merged.map(mask_clouds))

    date_ranges = create_date_range_list(st_date, date_interval)
    time_steps = make_time_step_coll(date_ranges, no_clouds)
    mosaics = ee.ImageCollection.fromImages(
        time_steps.map(create_veg_and_quality_band)
    )

    return mosaics.map(lambda img: img.clip(aoi_geom)).setMulti({
        "date_limits": boundary,
        "vegetation_index": mosaics.first().get("vegetation_index"),
    })
