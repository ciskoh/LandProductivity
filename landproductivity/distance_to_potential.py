"""Pure-Python distance-to-potential analysis for the LandProductivity pipeline.

Translates the original ``calcDistanceToPotential.js`` GEE script into
NumPy.  For each landscape unit the module identifies reference areas
(long-term productivity class 4) and expresses every pixel's vegetation
value as a percentage of the reference mean.  The result quantifies how
far each pixel is from its potential productivity.

The public entry points are ``prep_distance_to_potential`` (builds the
full image) and ``calc_distance_to_potential`` (summarises values for a
sub-region).

Used by:
    * ``gee_distance_to_potential`` (mirrors the same logic on the GEE side)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

Array3D = np.ndarray
Array2D = np.ndarray


@dataclass(frozen=True)
class DistanceToPotentialResult:
    """Container for the output of ``prep_distance_to_potential``.

    Args:
        image: 3-D distance-to-potential image ``(bands, rows, cols)``,
            values in percent.
        class4: Reference values matrix ``(bands, landscape_units)``.
        landscape: Original landscape raster.
        lt_prod: Long-term productivity raster (class 4 = reference).
        avg_value_ls: Per-landscape-unit mean distance values.
        date_list: Band labels (one per time step).
    """

    image: Array3D
    class4: np.ndarray
    landscape: Array2D
    lt_prod: Array2D
    avg_value_ls: Dict[int, List[float]]
    date_list: List[str]


def get_unique_values(raster: Array2D) -> np.ndarray:
    """Return sorted unique positive values from a raster.

    Args:
        raster: 2-D integer array (e.g. landscape codes).

    Returns:
        1-D array of values ``> 0``.

    Used by ``prep_distance_to_potential`` and
    ``calc_distance_to_potential``.
    """
    values = np.unique(raster)
    return values[values > 0]


def remove_null_values(values: Sequence[Optional[float]]) -> List[float]:
    """Replace ``None`` and ``NaN`` entries with ``0.0``.

    Args:
        values: Sequence that may contain ``None`` or ``NaN``.

    Returns:
        List of floats with nulls replaced by zero.

    Used by ``prep_distance_to_potential`` to sanitise reducer output.
    """
    result: List[float] = []
    for v in values:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            result.append(0.0)
        else:
            result.append(float(v))
    return result


def time_series_to_image(
    veg_ts: Union[Sequence[Array2D], Array3D],
    dates: Optional[Sequence[str]] = None,
) -> Tuple[Array3D, List[str]]:
    """Convert a vegetation time series into a 3-D image stack.

    Accepts either a list of 2-D arrays or an already-stacked 3-D array.

    Args:
        veg_ts: Vegetation images (one per time step).
        dates: Optional band labels.  Auto-generated when omitted.

    Returns:
        ``(image_stack, dates)`` where *image_stack* has shape
        ``(bands, rows, cols)``.

    Raises:
        ValueError: If *veg_ts* is empty or *dates* length mismatches.

    Used by ``prep_distance_to_potential``.
    """
    if isinstance(veg_ts, np.ndarray):
        if veg_ts.ndim == 2:
            stack = veg_ts[np.newaxis, ...]
        elif veg_ts.ndim == 3:
            stack = veg_ts
        else:
            raise ValueError("veg_ts must be a 2D or 3D numpy array")
    else:
        if not veg_ts:
            raise ValueError("veg_ts sequence must contain at least one image")
        stack = np.stack([np.asarray(img, dtype=float) for img in veg_ts], axis=0)

    band_count = stack.shape[0]
    if dates is None:
        dates = [f"T{i}" for i in range(band_count)]
    if len(dates) != band_count:
        raise ValueError("dates length must match number of vegetation time steps")
    return stack, list(dates)


def create_dist_to_potential_map(
    ls_mask: Array2D,
    veg_img: Array3D,
    ref_values: Sequence[float],
) -> Array3D:
    """Compute distance-to-potential for a single landscape unit.

    Distance is expressed as a percentage: ``pixel / reference × 100``.

    Args:
        ls_mask: Boolean mask for the landscape unit.
        veg_img: Full vegetation stack ``(bands, rows, cols)``.
        ref_values: Per-band mean reference values (from class-4 pixels).

    Returns:
        3-D array with distance percentages; masked-out pixels are ``0.0``.

    Raises:
        ValueError: If *ref_values* shape is inconsistent with *veg_img*.

    Used by ``prep_distance_to_potential``.
    """
    ref_arr = np.asarray(ref_values, dtype=float)
    if ref_arr.ndim != 1:
        raise ValueError("ref_values must be a 1D sequence")
    if ref_arr.size != veg_img.shape[0]:
        raise ValueError("ref_values length must match number of vegetation bands")

    denom = ref_arr[:, np.newaxis, np.newaxis]
    denom = np.where(denom == 0.0, np.nan, denom)

    dist = veg_img.astype(float) / denom * 100.0
    dist = np.where(np.isfinite(dist), dist, 0.0)
    return np.where(ls_mask[np.newaxis, ...], dist, 0.0)


def prep_distance_to_potential(
    ls: Array2D,
    lt_prod: Array2D,
    veg_ts: Union[Sequence[Array2D], Array3D],
    dates: Optional[Sequence[str]] = None,
    aoi_mask: Optional[Array2D] = None,
) -> DistanceToPotentialResult:
    """Build a full distance-to-potential image from landscape and vegetation data.

    This is the main preparation step.  For every landscape unit it:

    1. Identifies reference pixels (long-term productivity == 4).
    2. Computes mean vegetation in reference pixels.
    3. Divides every pixel's value by the reference mean (× 100).

    Args:
        ls: 2-D landscape code raster.
        lt_prod: 2-D long-term productivity raster (class 4 = reference).
        veg_ts: Vegetation time series (list of 2-D arrays or 3-D stack).
        dates: Optional band labels.
        aoi_mask: Optional boolean mask; defaults to all-``True``.

    Returns:
        A ``DistanceToPotentialResult`` containing the distance image,
        reference values, and summary statistics.

    Raises:
        ValueError: If *ls* and *lt_prod* shapes differ.
    """
    veg_img, date_list = time_series_to_image(veg_ts, dates)
    band_count = veg_img.shape[0]

    if ls.shape != lt_prod.shape:
        raise ValueError("ls and lt_prod must have the same shape")
    if aoi_mask is None:
        aoi_mask = np.ones_like(ls, dtype=bool)
    if aoi_mask.shape != ls.shape:
        raise ValueError("aoi_mask must have the same shape as ls")

    ref_areas = (lt_prod == 4) & aoi_mask
    ls_values = get_unique_values(ls)

    dist_potential_img = np.zeros(veg_img.shape, dtype=float)
    all_ref_values: List[List[float]] = []
    avg_value_ls: Dict[int, List[float]] = {}

    for ls_value in ls_values:
        mask = (ls == ls_value) & aoi_mask
        if not np.any(mask):
            continue

        masked_ref = np.where(ref_areas & mask, veg_img, np.nan)
        ref_values = remove_null_values(np.nanmean(masked_ref, axis=(1, 2)).tolist())
        has_valid_ref = any(v != 0.0 for v in ref_values)

        if has_valid_ref:
            dist = create_dist_to_potential_map(mask, veg_img, ref_values)
        else:
            dist = np.zeros(veg_img.shape, dtype=float)

        masked_dist = np.where(mask[np.newaxis, ...], dist, 0.0)
        dist_potential_img += masked_dist

        avg = np.nanmean(
            np.where(mask[np.newaxis, ...], masked_dist, np.nan),
            axis=(1, 2),
        )
        avg_value_ls[int(ls_value)] = remove_null_values(avg.tolist())
        all_ref_values.append(ref_values)

    class4 = (
        np.array(all_ref_values, dtype=float).T
        if all_ref_values
        else np.zeros((band_count, 0), dtype=float)
    )

    return DistanceToPotentialResult(
        image=dist_potential_img,
        class4=class4,
        landscape=ls,
        lt_prod=lt_prod,
        avg_value_ls=avg_value_ls,
        date_list=date_list,
    )


def calc_distance_to_potential(
    distance_to_potential: DistanceToPotentialResult,
    geom_mask: Array2D,
) -> Dict[str, Any]:
    """Summarise distance-to-potential values for a sub-region.

    Computes both the direct area mean and a landscape-weighted
    comparable mean.

    Args:
        distance_to_potential: Result from ``prep_distance_to_potential``.
        geom_mask: Boolean mask defining the sub-region.

    Returns:
        Dict with keys ``"areaDist"`` (area mean per band),
        ``"avgDist"`` (weighted comparable mean per band) and
        ``"dateList"``.

    Raises:
        ValueError: If *geom_mask* shape doesn't match or has no overlap.
    """
    if geom_mask.shape != distance_to_potential.landscape.shape:
        raise ValueError("geom_mask must have the same shape as the landscape")

    ls = distance_to_potential.landscape
    unique_values = get_unique_values(np.where(geom_mask, ls, 0))
    total_count = float(np.sum(np.isin(ls, unique_values) & geom_mask))
    if total_count == 0:
        raise ValueError("Geometry mask does not overlap the landscape")

    weighted_values = []
    for ls_value in unique_values:
        weight = float(np.sum((ls == ls_value) & geom_mask)) / total_count
        avg = distance_to_potential.avg_value_ls.get(int(ls_value), [])
        weighted_values.append(np.array(avg, dtype=float) * weight)

    avg_comparable = (
        np.sum(weighted_values, axis=0).tolist()
        if weighted_values
        else []
    )

    aoi_dist = np.nanmean(
        np.where(geom_mask[np.newaxis, ...], distance_to_potential.image, np.nan),
        axis=(1, 2),
    )

    return {
        "areaDist": remove_null_values(aoi_dist.tolist()),
        "avgDist": avg_comparable,
        "dateList": distance_to_potential.date_list,
    }
