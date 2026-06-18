"""Google Earth Engine landscape map creation for LandProductivity.

Server-side counterpart of ``landscape.py``.  Every function operates on
``ee.Image`` / ``ee.ImageCollection`` objects and requires an
authenticated Earth Engine session.

The public entry point is ``create_landscape_map``; it mirrors the
original ``createLandscapeMap.js`` GEE script and is imported in
``__init__.py`` as ``gee_create_landscape_map``.

Used by:
    * The GEE-based analysis notebook / dashboard.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

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


def create_mask_aoi(
    land_cover: Any,
    unwanted_categories: Optional[Iterable[int]] = None,
) -> Any:
    """Create an AOI mask from a land-cover image using Earth Engine.

    For each unwanted category, a binary "not-equal" mask is built; the
    masks are combined with ``min()`` so that a pixel is kept only when
    it passes every individual mask.

    Args:
        land_cover: ``ee.Image`` of integer land-cover categories.
        unwanted_categories: Category codes to exclude.  Defaults to
            ``[0]`` (background / no-data).

    Returns:
        ``ee.Image`` — binary mask clipped to the land-cover geometry.

    Used by ``create_landscape_map``.
    """
    _ensure_ee()
    unwanted = ee.List(list(unwanted_categories or [0]))

    def mask_for_cat(cat: Any) -> Any:
        return land_cover.neq(ee.Image.constant(cat)).And(land_cover.gt(0))

    mask = ee.ImageCollection(unwanted.map(mask_for_cat)).min()
    return mask.clip(land_cover.geometry())


def classify_image(image: Any, classification_dict: Any) -> Any:
    """Classify an image using GEE-side min/max range look-ups.

    For each key in *classification_dict* the image is tested against
    ``(min, max]`` and the matching pixels receive the key as value.
    Overlapping ranges are resolved by ``max()``.

    Args:
        image: ``ee.Image`` with continuous values (e.g. slope degrees).
        classification_dict: ``ee.Dictionary`` mapping string keys to
            ``[min, max]`` lists.

    Returns:
        ``ee.Image`` (Int32) with classified category codes.

    Used by ``create_landscape_map``.
    """
    _ensure_ee()
    classification_dict = ee.Dictionary(classification_dict)
    keys = classification_dict.keys()

    def classify_for_key(key: Any) -> Any:
        vals = ee.List(classification_dict.get(key))
        lo = ee.Number(vals.get(0))
        hi = ee.Number(vals.get(1))
        code = ee.Number.parse(key)
        return (
            ee.Image(image.gt(lo))
            .And(image.lte(hi))
            .toInt64()
            .multiply(code)
        )

    return ee.ImageCollection(keys.map(classify_for_key)).max().rename(["band"]).toInt32()


def simplify_landscape_map(img: Any, min_allowed_area: int) -> Any:
    """Smooth small landscape patches using a local-mode kernel.

    The kernel radius is derived from the image's nominal scale and
    *min_allowed_area* so that the window covers approximately one
    minimum-area patch.

    Args:
        img: ``ee.Image`` of landscape codes.
        min_allowed_area: Minimum patch area in square metres.

    Returns:
        ``ee.Image`` — smoothed landscape map, clipped to original extent.

    Used by ``create_landscape_map``.
    """
    _ensure_ee()
    pixel_area = ee.Number(img.projection().nominalScale()).pow(2)
    radius = ee.Number(min_allowed_area).divide(pixel_area).sqrt().ceil()
    kernel = ee.Kernel.square(radius)
    return (
        img.reduceNeighborhood(reducer=ee.Reducer.mode(), kernel=kernel)
        .clip(img.geometry())
    )


def create_landscape_map(
    land_cover_map: Any,
    dem: Any,
    slope_cat: Any,
    asp_cat: Any,
    unwanted_categories: Optional[Iterable[int]] = None,
    min_area: int = 20000,
) -> Any:
    """Create a homogeneous landscape-unit map on Earth Engine.

    Mirrors the original ``createLandscapeMap`` JavaScript function:

    1. Build an AOI mask from the land-cover image.
    2. Derive slope and aspect from the DEM.
    3. Classify slope and aspect into categories.
    4. Encode as a three-digit code: ``land_cover * 100 + slope * 10 +
       aspect``.
    5. Simplify with a mode filter.
    6. Attach metadata (category look-ups, value list, creation date).

    Args:
        land_cover_map: ``ee.Image`` of land-cover categories.
        dem: ``ee.Image`` digital elevation model (e.g. SRTM).
        slope_cat: ``ee.Dictionary`` of slope category ranges.
        asp_cat: ``ee.Dictionary`` of aspect category ranges.
        unwanted_categories: Land-cover codes to exclude.
        min_area: Minimum landscape-unit area in square metres.

    Returns:
        ``ee.Image`` — classified and simplified landscape map with
        metadata properties.
    """
    _ensure_ee()
    unwanted = ee.List(list(unwanted_categories or [0]))
    mask_aoi = create_mask_aoi(land_cover_map, unwanted).selfMask()

    clipped_dem = dem.clip(mask_aoi.geometry())
    raw_aspect = ee.Terrain.aspect(clipped_dem).toInt()
    raw_slope = (
        ee.Terrain.slope(clipped_dem)
        .unitScale(0, 90)
        .multiply(100)
        .toInt()
    )

    classified_slope = classify_image(raw_slope, slope_cat)
    classified_aspect = classify_image(raw_aspect, asp_cat).multiply(
        classified_slope.gt(ee.Image.constant(1))
    )

    raw_ls = (
        land_cover_map.mask(mask_aoi)
        .multiply(100)
        .add(classified_slope.multiply(10))
        .add(classified_aspect)
    )

    clean_ls = (
        simplify_landscape_map(raw_ls, min_area)
        .mask(mask_aoi)
        .short()
    )

    categories = ee.Dictionary({
        "landCover": slope_cat,
        "slope": slope_cat,
        "aspect": asp_cat,
    })

    ls_hist = clean_ls.reduceRegion(
        reducer=ee.Reducer.frequencyHistogram(),
        geometry=clean_ls.geometry(),
        scale=10,
        maxPixels=1e12,
    )
    ls_keys = ee.Dictionary(ls_hist.values().get(0)).keys()
    ls_value_list = (
        ee.List(ls_keys)
        .map(lambda v: ee.Number.parse(v))
        .filter(ee.Filter.gt("item", 0))
        .join(" , ")
    )

    return clean_ls.setMulti({
        "description": (
            "Map of homogenous landscape units. Each landscape class is "
            "coded as: landCover*100 + slope*10 + aspect."
        ),
        "date_created": ee.Date(ee.Date.now()).millis(),
        "categories": categories.serialize(),
        "lsValueList": ls_value_list,
    })
