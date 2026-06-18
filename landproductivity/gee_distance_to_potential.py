"""Google Earth Engine distance-to-potential analysis for LandProductivity.

Server-side counterpart of ``distance_to_potential.py``.  Every function
operates on ``ee.Image`` / ``ee.ImageCollection`` objects and requires an
authenticated Earth Engine session.

The public entry points are ``prep_distance_to_potential`` (builds the
image) and ``calc_distance_to_potential`` (summarises values for a
geometry).

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


def add_id_prop(collection: Any) -> Any:
    """Add a sequential ``"id"`` property to every image in a collection.

    Args:
        collection: ``ee.ImageCollection`` without ``"id"`` properties.

    Returns:
        ``ee.ImageCollection`` with zero-based ``"id"`` set on each image.

    Used by ``add_id_prop_if_needed``.
    """
    coll_list = collection.toList(10000)

    def set_id(img: Any) -> Any:
        img = ee.Image(img)
        return img.set({"id": ee.Number(coll_list.indexOf(img))})

    return ee.ImageCollection(coll_list.map(set_id))


def add_id_prop_if_needed(collection: Any) -> Any:
    """Ensure every image in *collection* carries an ``"id"`` property.

    If at least two distinct ``"id"`` values already exist, the
    collection is returned unchanged.

    Args:
        collection: ``ee.ImageCollection``.

    Returns:
        ``ee.ImageCollection`` with ``"id"`` properties guaranteed.

    Used by ``prep_distance_to_potential``.
    """
    _ensure_ee()
    has_ids = ee.Number(collection.aggregate_count_distinct("id")).gt(1)
    return ee.Algorithms.If(has_ids, collection, add_id_prop(collection))


def time_series_to_image(ts: Any) -> Any:
    """Convert a time-series collection into a multi-band image.

    Band names are formatted as ``GYYMMdd`` dates.

    Args:
        ts: ``ee.ImageCollection`` with a ``"date"`` property per image.

    Returns:
        ``ee.Image`` with one band per time step and a ``"dates"``
        property.

    Used by ``prep_distance_to_potential``.
    """
    _ensure_ee()
    dates = ee.List(ee.ImageCollection(ts).aggregate_array("date"))
    date_strings = dates.map(lambda d: ee.Date(d).format("GYYMMdd"))
    img = ee.ImageCollection(ts).toBands()
    return img.rename(date_strings).set({"dates": dates})


def get_unique_values(raster: Any) -> Any:
    """Return the unique positive values in a raster as an ``ee.List``.

    Args:
        raster: ``ee.Image`` with integer values.

    Returns:
        ``ee.List`` of ``ee.Number`` values ``> 0``.

    Used by ``prep_distance_to_potential``.
    """
    _ensure_ee()
    hist = ee.Image(raster).reduceRegion(
        reducer=ee.Reducer.frequencyHistogram(),
        scale=raster.projection().nominalScale(),
        tileScale=2,
        maxPixels=1e12,
    )
    keys = ee.Dictionary(hist.values().get(0)).keys()
    return (
        ee.List(keys.map(lambda x: ee.Number.parse(x)))
        .filter(ee.Filter.gt("item", 0))
    )


def remove_null_values(value_list: Any) -> Any:
    """Replace null / zero-sum entries with ``0`` in an ``ee.List``.

    Args:
        value_list: ``ee.List`` of numbers that may contain nulls.

    Returns:
        ``ee.List`` with nulls replaced by zero.

    Used by ``prep_distance_to_potential`` and
    ``calc_distance_to_potential``.
    """
    _ensure_ee()
    total = ee.Number(ee.List(value_list).reduce(ee.Reducer.sum())).gt(0)
    size = ee.List(value_list).size()
    indices = ee.List.sequence(0, ee.Number(size).subtract(1), 1)

    def safe_value(pos: Any) -> Any:
        val = ee.List(value_list).get(pos)
        valid = ee.Number(ee.List([val]).reduce(ee.Reducer.sum())).gt(0)
        return ee.Algorithms.If(valid, val, 0)

    return ee.Algorithms.If(total, indices.map(safe_value), ee.List.repeat(0, size))


def create_dist_to_potential_map(
    ls_mask: Any,
    veg_img: Any,
    ref_value: Any,
) -> Any:
    """Compute distance-to-potential for one landscape class (server-side).

    Distance = ``pixel / reference × 100`` (percent).

    Args:
        ls_mask: ``ee.Image`` — binary mask for the landscape class.
        veg_img: ``ee.Image`` — multi-band vegetation image.
        ref_value: ``ee.List`` of per-band reference means.

    Returns:
        ``ee.Image`` with distance-to-potential values.

    Used by ``prep_distance_to_potential``.
    """
    _ensure_ee()
    ref_img = ee.Image(ls_mask).multiply(ee.Image.constant(ref_value)).selfMask()
    return veg_img.divide(ref_img).multiply(ee.Image.constant(100))


def prep_distance_to_potential(ls: Any, lt_prod: Any, veg_ts: Any) -> Any:
    """Build a distance-to-potential image on Earth Engine.

    For every landscape unit:

    1. Identify reference pixels (long-term productivity == 4).
    2. Compute mean vegetation in reference pixels.
    3. Express each pixel as a percentage of the reference.

    Args:
        ls: ``ee.Image`` — landscape code raster.
        lt_prod: ``ee.Image`` — long-term productivity classification.
        veg_ts: ``ee.ImageCollection`` — vegetation time series.

    Returns:
        ``ee.Image`` with distance-to-potential bands and metadata
        properties ``"class4"``, ``"landscape"``, ``"ltProd"``,
        ``"avgValueLs"`` and ``"dateList"``.
    """
    _ensure_ee()
    aoi_geom = lt_prod.geometry()
    veg = ee.ImageCollection(add_id_prop_if_needed(veg_ts))
    veg_img = time_series_to_image(veg.select(0))
    veg_len = veg_img.bandNames().size()
    ref_areas = lt_prod.eq(ee.Image.constant(4))
    ls_values = get_unique_values(ls)

    def per_ls_value(ls_value: Any) -> Any:
        ls_mask = ls.eq(ee.Image.constant(ls_value))
        masked_ref = veg_img.updateMask(ls_mask).updateMask(ref_areas)

        ref_value = ee.List(remove_null_values(
            masked_ref.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=aoi_geom,
                scale=30,
                maxPixels=1e12,
                tileScale=2,
            ).values()
        ))
        has_valid = ee.Number(ref_value.reduce(ee.Reducer.sum())).gt(0)

        dist = ee.Algorithms.If(
            has_valid,
            create_dist_to_potential_map(ls_mask, veg_img, ref_value),
            ee.Image.constant(ee.List.repeat(0, veg_len)),
        )

        avg = ee.Algorithms.If(
            has_valid,
            ee.Image(dist).reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=aoi_geom,
                scale=30,
                maxPixels=1e12,
                tileScale=4,
            ),
            ee.Dictionary.fromLists(
                veg_img.bandNames(), ee.List.repeat(0, veg_len)
            ),
        )

        avg_clean = ee.List(remove_null_values(ee.Dictionary(avg).values()))

        return (
            ee.Image(dist)
            .selfMask()
            .rename(veg_img.bandNames())
            .set({
                "ls": ee.Number(ls_value),
                "refValues": ref_value,
                "avgDist": avg_clean,
            })
        )

    dist_list = ls_value_list = ls_values.map(per_ls_value)
    dist_coll = ee.ImageCollection(dist_list)

    ref_array = ee.Array(dist_coll.aggregate_array("refValues")).transpose()
    avg_dic = ee.Dictionary.fromLists(
        ls_values.map(lambda x: ee.String(x)),
        dist_coll.aggregate_array("avgDist"),
    )

    return ee.ImageCollection(dist_list).mosaic().set({
        "class4": ref_array.toList(),
        "landscape": ls,
        "ltProd": lt_prod,
        "avgValueLs": avg_dic,
        "dateList": ee.List(
            veg_ts.aggregate_array("date")
        ).map(lambda x: ee.Date(x).millis()),
    })


def calc_distance_to_potential(distance_to_potential: Any, geom: Any) -> Any:
    """Summarise distance-to-potential values for a sub-region.

    Computes:
        * ``areaDist`` — direct area mean per band.
        * ``avgDist`` — landscape-weighted comparable mean per band.

    Args:
        distance_to_potential: ``ee.Image`` from
            ``prep_distance_to_potential``.
        geom: ``ee.Geometry`` defining the sub-region.

    Returns:
        ``ee.Feature`` with properties ``"areaDist"``, ``"avgDist"``
        and ``"dateList"``.
    """
    _ensure_ee()
    ls = ee.Image(distance_to_potential.get("landscape"))

    ls_hist = ee.Dictionary(
        ls.reduceRegion(
            reducer=ee.Reducer.frequencyHistogram(),
            geometry=geom,
            scale=ls.projection().nominalScale(),
            maxPixels=1e12,
        ).values().get(0)
    )

    total = ee.Number(ls_hist.values().reduce(ee.Reducer.sum())).round()
    weights = ls_hist.map(lambda k, v: ee.Number(v).round().divide(total))
    weights_clean = ee.Dictionary.fromLists(
        weights.keys(),
        remove_null_values(ee.Dictionary(weights).values()),
    )

    def weighted_avg(ls_key: Any) -> Any:
        ls_str = ee.String(ls_key)
        avg = ee.Dictionary(distance_to_potential.get("avgValueLs")).get(ls_str)
        w = ee.Number(weights_clean.get(ls_str))
        return ee.Array(avg).multiply(w).toList()

    weighted = ee.List(weights_clean.keys()).map(weighted_avg)
    comparable = (
        ee.Array(weighted)
        .reduce(reducer=ee.Reducer.sum(), axes=ee.List([0]))
        .toList()
        .get(0)
    )

    raw_dist = distance_to_potential.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geom,
        scale=30,
        bestEffort=True,
        maxPixels=1e12,
    ).values()

    indices = ee.List.sequence(0, ee.Number(raw_dist.size()).subtract(1), 1)
    area_dist = indices.map(
        lambda i: ee.Algorithms.If(
            ee.Number(
                ee.List([ee.Number(raw_dist.get(i))]).reduce(ee.Reducer.sum())
            ).gt(0),
            ee.Number(raw_dist.get(i)),
            0.0,
        )
    )

    return ee.Feature(None, {
        "areaDist": area_dist,
        "avgDist": comparable,
        "dateList": distance_to_potential.get("dateList"),
    })
