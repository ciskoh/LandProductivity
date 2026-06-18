"""Pure-Python productivity classification for the LandProductivity pipeline.

Translates the original ``createProductivityMap.js`` GEE script into
NumPy.  For each landscape unit the module computes 10th/90th-percentile
thresholds from the vegetation values, then classifies every pixel into
one of four degradation classes (1 = very degraded … 4 = potential).

The public entry point is ``create_productivity_map``; lower-level helpers
are exposed for unit testing and reuse.

Used by:
    * ``distance_to_potential`` (consumes the long-term productivity map)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np


@dataclass
class ProductivityMap:
    """Result container for ``create_productivity_map``.

    Args:
        classification: 3-D integer array ``(bands, rows, cols)`` with
            degradation classes 1–4.
        dates: Band labels (one per time step).
    """

    classification: np.ndarray
    dates: List[str]


def get_unique_values(landscape: np.ndarray) -> np.ndarray:
    """Return sorted unique positive values from a landscape raster.

    Args:
        landscape: 2-D array of integer landscape codes.

    Returns:
        1-D array of values ``> 0``.

    Used by ``create_productivity_map`` to iterate over landscape units.
    """
    values = np.unique(landscape)
    return values[values > 0]


def is_time_series(veg: Any) -> bool:
    """Check whether *veg* represents a multi-step time series.

    Args:
        veg: Either a list of 2-D arrays or a single 2-D/3-D array.

    Returns:
        ``True`` when *veg* contains more than one time step.

    Used by callers that need to distinguish single images from stacks.
    """
    if isinstance(veg, list):
        return len(veg) > 1
    if isinstance(veg, np.ndarray):
        return veg.ndim == 3
    return False


def time_series_to_image(
    veg: Sequence[np.ndarray],
    dates: Optional[List[str]] = None,
) -> Tuple[np.ndarray, List[str]]:
    """Stack a list of 2-D vegetation images into a 3-D array.

    Args:
        veg: Non-empty sequence of 2-D arrays (one per time step).
        dates: Optional band labels.  Auto-generated as ``T0``, ``T1``,
            … when omitted.

    Returns:
        ``(image_stack, dates)`` where *image_stack* has shape
        ``(len(veg), rows, cols)``.

    Raises:
        ValueError: If *veg* is empty.

    Used by ``create_productivity_map``.
    """
    if not veg:
        raise ValueError("veg sequence must contain at least one image")
    image_stack = np.stack(veg, axis=0)
    if dates is None:
        dates = [f"T{i}" for i in range(image_stack.shape[0])]
    return image_stack, dates


def make_percentile_array(masked_veg: np.ndarray) -> Dict[str, List[float]]:
    """Compute 0th, 10th, 90th and 100th percentiles per band.

    Args:
        masked_veg: 2-D or 3-D array of vegetation values (``NaN`` for
            masked pixels).

    Returns:
        Dict mapping percentile keys ``"0"``, ``"10"``, ``"90"``,
        ``"100"`` to lists of per-band values.  Bands with no valid
        pixels get ``NaN``.

    Used by ``create_productivity_map``.
    """
    if masked_veg.ndim == 2:
        masked_veg = masked_veg[np.newaxis, ...]

    result: Dict[str, List[float]] = {"0": [], "10": [], "90": [], "100": []}
    for band in masked_veg:
        valid = band[np.isfinite(band)]
        if valid.size == 0:
            for key in result:
                result[key].append(float("nan"))
        else:
            for key in result:
                result[key].append(float(np.nanpercentile(valid, int(key))))
    return result


def format_percentiles(percentiles: Dict[str, List[float]]) -> Dict[str, List[float]]:
    """Return a shallow copy of *percentiles* with plain Python lists.

    This is a compatibility shim matching the original GEE workflow
    where the percentile dict needed reformatting.  In the Python
    translation the output of ``make_percentile_array`` is already in
    the right shape, so this function is effectively an identity.

    Args:
        percentiles: Dict produced by ``make_percentile_array``.

    Returns:
        Same structure with values copied into fresh lists.
    """
    return {k: list(v) for k, v in percentiles.items()}


def model_1090(percentiles: Dict[str, float]) -> List[float]:
    """Derive three thresholds from the 10th and 90th percentile.

    The "healthy" threshold sits halfway between the two::

        healthy = (p90 − p10) / 2 + p10

    Args:
        percentiles: Dict with at least keys ``"10"`` and ``"90"``,
            each a single float.

    Returns:
        ``[very_degraded, healthy, potential]`` thresholds.

    Used by ``calc_threshold_values``.
    """
    p10 = percentiles["10"]
    p90 = percentiles["90"]
    healthy = (p90 - p10) / 2.0 + p10
    return [p10, healthy, p90]


def calc_threshold_values(
    percentiles: Dict[str, List[float]],
) -> List[List[float]]:
    """Compute degradation thresholds for every time step.

    Args:
        percentiles: Dict from ``make_percentile_array`` /
            ``format_percentiles``.

    Returns:
        List of ``[very_degraded, healthy, potential]`` triples, one per
        band.

    Used by ``create_productivity_map``.
    """
    band_count = len(percentiles["0"])
    thresholds: List[List[float]] = []
    for i in range(band_count):
        band_pct = {k: percentiles[k][i] for k in percentiles}
        thresholds.append(model_1090(band_pct))
    return thresholds


def create_deg_image(
    veg_stack: np.ndarray,
    threshold_list: List[List[float]],
) -> np.ndarray:
    """Classify vegetation values into degradation classes 1–4.

    Class assignment: start at 1, add 1 for each threshold the pixel
    value meets or exceeds.

    Args:
        veg_stack: 2-D or 3-D array of vegetation values.
        threshold_list: One ``[t1, t2, t3]`` triple per band.

    Returns:
        Integer array of the same shape with values in ``{1, 2, 3, 4}``.

    Used by ``create_productivity_map``.
    """
    if veg_stack.ndim == 2:
        veg_stack = veg_stack[np.newaxis, ...]
    classification = np.ones_like(veg_stack, dtype=int)
    for band_idx, thresholds in enumerate(threshold_list):
        band = veg_stack[band_idx]
        for threshold in thresholds:
            classification[band_idx] += (band >= threshold).astype(int)
    return classification


def bands_to_collection(
    classification_stack: np.ndarray,
    dates: List[str],
) -> List[Dict[str, Any]]:
    """Convert a classification stack into a list of dicts with date metadata.

    Args:
        classification_stack: 3-D integer array ``(bands, rows, cols)``.
        dates: Band labels (same length as first axis).

    Returns:
        List of ``{"date": …, "prodClass": …}`` dicts, one per band.

    Useful for serialisation and downstream consumers that expect a
    collection format.
    """
    return [
        {"date": dates[i], "prodClass": classification_stack[i]}
        for i in range(classification_stack.shape[0])
    ]


def create_productivity_map(
    landscape: np.ndarray,
    veg: Any,
    dates: Optional[List[str]] = None,
) -> ProductivityMap:
    """Create a productivity classification map per landscape unit.

    This is the main entry point of the module.  It mirrors the original
    ``createProductivityMap`` GEE function:

    1. Convert *veg* into a 3-D stack ``(bands, rows, cols)``.
    2. For each unique landscape value, mask the vegetation stack and
       compute 10/90 percentile thresholds.
    3. Classify every pixel into degradation classes 1–4.

    Args:
        landscape: 2-D array of integer landscape codes (from
            ``landscape.create_landscape_map``).
        veg: Vegetation data — either a list of 2-D arrays, a 3-D array
            ``(bands, rows, cols)``, or a single 2-D array.
        dates: Optional band labels.  Auto-generated when omitted.

    Returns:
        A ``ProductivityMap`` with the classification array and dates.

    Raises:
        ValueError: If *veg* has an unsupported type or shape.
    """
    if isinstance(veg, list):
        veg_stack, band_dates = time_series_to_image(veg, dates)
    elif isinstance(veg, np.ndarray) and veg.ndim == 3:
        veg_stack = veg
        band_dates = dates or [f"T{i}" for i in range(veg.shape[0])]
    elif isinstance(veg, np.ndarray) and veg.ndim == 2:
        veg_stack = veg[np.newaxis, ...]
        band_dates = dates or ["T0"]
    else:
        raise ValueError("veg must be a numpy array or a list of numpy arrays")

    output_stack = np.zeros_like(veg_stack, dtype=int)

    for ls_value in get_unique_values(landscape):
        mask = landscape == ls_value
        masked_veg = np.where(mask[np.newaxis, ...], veg_stack, np.nan)

        if not any(np.isfinite(v).any() for v in masked_veg):
            continue

        percentiles = format_percentiles(make_percentile_array(masked_veg))
        threshold_list = calc_threshold_values(percentiles)
        deg_stack = create_deg_image(masked_veg, threshold_list)
        output_stack[:, mask] = deg_stack[:, mask]

    return ProductivityMap(classification=output_stack, dates=band_dates)
