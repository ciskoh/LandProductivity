"""Pure-Python vegetation time-series utilities for the LandProductivity pipeline.

Translates the original ``getVegTimeSeries.js`` GEE script into plain
Python / NumPy.  The module groups satellite scenes into regular time
steps, computes NDVI for each scene, and produces composite mosaics with
a simple quality band.

The public entry point is ``get_veg_time_series``; lower-level helpers
(``create_date_range_list``, ``filter_bounds_and_dates``, ``calc_ndvi``,
etc.) are exposed for unit testing and reuse.

Used by:
    * ``productivity`` (consumes the vegetation mosaics)
    * ``distance_to_potential`` (consumes the vegetation mosaics)
    * ``gee_time_series`` (mirrors the same logic on the GEE side)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

Scene = Dict[str, Any]
TimeRange = Tuple[datetime, datetime]


@dataclass(frozen=True)
class TimeStepGroup:
    """Container for scenes that fall within the same time step.

    Args:
        date: Midpoint datetime of the time step.
        images: List of scene dicts belonging to this step.
        size: Number of scenes (equals ``len(images)``).

    Created by ``make_time_step_coll`` and consumed by
    ``create_veg_and_quality_band``.
    """

    date: datetime
    images: List[Scene]
    size: int


def create_date_range_list(
    start_date: datetime,
    end_date: datetime,
    interval_days: int,
) -> List[TimeRange]:
    """Build a list of overlapping date windows for time-series aggregation.

    Each window is centred on a step date and extends
    ± ``interval_days // 2`` around it.

    Args:
        start_date: First step centre date.
        end_date: Last possible step centre date (inclusive).
        interval_days: Days between consecutive step centres.

    Returns:
        List of ``(window_start, window_end)`` tuples.

    Raises:
        ValueError: If *interval_days* is not positive.

    Used by ``get_veg_time_series``.
    """
    if interval_days <= 0:
        raise ValueError("interval_days must be positive")

    half = timedelta(days=interval_days // 2)
    ranges: List[TimeRange] = []
    current = start_date
    while current <= end_date:
        ranges.append((current - half, current + half))
        current += timedelta(days=interval_days)
    return ranges


def filter_bounds_and_dates(
    scenes: Sequence[Scene],
    date_range: TimeRange,
    geometry_filter: Optional[Callable[[Any], bool]] = None,
) -> List[Scene]:
    """Select scenes that fall within a date window and pass a geometry test.

    Args:
        scenes: Candidate scenes, each with a ``"date"`` key.
        date_range: ``(start, end)`` datetime window (inclusive).
        geometry_filter: Optional callable receiving the scene's
            ``"geometry"`` value; return ``True`` to keep the scene.

    Returns:
        Filtered list of scene dicts.

    Used by ``get_veg_time_series``.
    """
    start, end = date_range
    filtered: List[Scene] = []
    for scene in scenes:
        scene_date = scene.get("date")
        if not isinstance(scene_date, datetime):
            continue
        if start <= scene_date <= end:
            if geometry_filter is None or geometry_filter(scene.get("geometry")):
                filtered.append(scene)
    return filtered


def make_time_step_coll(
    date_ranges: Sequence[TimeRange],
    scenes: Sequence[Scene],
) -> List[TimeStepGroup]:
    """Group scenes into time steps and discard empty steps.

    Args:
        date_ranges: Time windows produced by ``create_date_range_list``.
        scenes: All available scenes (each must have a ``"date"`` key).

    Returns:
        List of ``TimeStepGroup`` instances, one per non-empty step.

    Used by ``get_veg_time_series``.
    """
    groups: List[TimeStepGroup] = []
    for start, end in date_ranges:
        matched = [s for s in scenes if start <= s.get("date") <= end]
        if matched:
            midpoint = start + (end - start) / 2
            groups.append(TimeStepGroup(date=midpoint, images=matched, size=len(matched)))
    return groups


def get_landsat_code(image_id: str) -> Optional[str]:
    """Extract the Landsat satellite code from a scene identifier.

    Recognised codes: ``LT05`` (Landsat 5), ``LE07`` (Landsat 7),
    ``LC08`` (Landsat 8).

    Args:
        image_id: Scene identifier string (e.g.
            ``"LANDSAT/LC08/C01/T1_SR/scene_id"``).

    Returns:
        The satellite code, or ``None`` if unrecognised.

    Used by ``calc_vegetation_index``.
    """
    if not image_id:
        return None
    for code in ("LT05", "LE07", "LC08"):
        if code in image_id:
            return code
    return None


def calc_ndvi(red: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """Compute NDVI from red and near-infrared reflectance arrays.

    Formula: ``(NIR − Red) / (NIR + Red)``.  Pixels where the
    denominator is zero are set to ``0.0``.

    Args:
        red: Red-band reflectance values.
        nir: Near-infrared-band reflectance values (same shape).

    Returns:
        NDVI array in the range ``[-1, 1]``.

    Used by ``calc_vegetation_index``.
    """
    red = np.asarray(red, dtype=float)
    nir = np.asarray(nir, dtype=float)
    denom = nir + red
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = np.where(denom == 0, 0.0, (nir - red) / denom)
    return ndvi


def calc_vegetation_index(scene: Scene) -> Scene:
    """Add NDVI and satellite metadata to a scene dict.

    Args:
        scene: Must contain ``"bands"`` with sub-keys ``"red"`` and
            ``"nir"``, and an ``"id"`` string.

    Returns:
        New dict with the original keys plus ``"ndvi"``,
        ``"vegetation_index"`` and ``"satellite_type"``.

    Raises:
        ValueError: If the scene is missing red or NIR bands.

    Used by ``create_veg_and_quality_band``.
    """
    image_id = scene.get("id", "")
    sat_code = get_landsat_code(image_id) or "UNKNOWN"
    bands = scene.get("bands", {})
    red = bands.get("red")
    nir = bands.get("nir")
    if red is None or nir is None:
        raise ValueError("Scene must contain red and nir bands")

    return {
        **scene,
        "ndvi": calc_ndvi(red, nir),
        "vegetation_index": "ndvi",
        "satellite_type": sat_code,
    }


def make_simple_quality_band(
    image_collection: Sequence[Scene],
    im_number: int,
) -> np.ndarray:
    """Compute a per-pixel quality score as valid-count / total-images.

    Args:
        image_collection: Scenes that contribute to the composite.
        im_number: Total number of images (denominator).

    Returns:
        Quality array in ``[0, 1]``.

    Raises:
        ValueError: If *im_number* is not positive or no QA band is found.

    Used by ``create_veg_and_quality_band``.
    """
    if im_number <= 0:
        raise ValueError("im_number must be positive")

    valid_counts = None
    for scene in image_collection:
        quality = scene.get("pixel_qa")
        if quality is None:
            quality = scene.get("bands", {}).get("pixel_qa")
        if quality is None:
            continue
        mask = ~np.isnan(np.asarray(quality, dtype=float))
        valid_counts = mask.astype(float) if valid_counts is None else valid_counts + mask.astype(float)

    if valid_counts is None:
        raise ValueError("No quality band found in image collection")
    return valid_counts / float(im_number)


def create_veg_and_quality_band(ts_group: TimeStepGroup) -> Scene:
    """Build a mean-NDVI mosaic and quality band for one time step.

    Args:
        ts_group: A ``TimeStepGroup`` containing at least one scene.

    Returns:
        Scene dict with keys ``"date"``, ``"ndvi"`` (mean composite),
        ``"simpleQA"`` (quality score), ``"vegetation_index"``,
        ``"satellite_type"`` and ``"size"``.

    Raises:
        ValueError: If the group has no scenes.

    Used by ``get_veg_time_series``.
    """
    scenes = ts_group.images
    if not scenes:
        raise ValueError("Time step group must have at least one scene")

    veg_scenes = [calc_vegetation_index(s) for s in scenes]
    ndvi_stack = np.stack([s["ndvi"] for s in veg_scenes], axis=0)
    ndvi_mean = ndvi_stack.mean(axis=0)
    quality_band = make_simple_quality_band(scenes, len(scenes))

    return {
        "date": ts_group.date,
        "ndvi": ndvi_mean,
        "simpleQA": quality_band,
        "vegetation_index": "ndvi",
        "satellite_type": scenes[0].get("satellite_type", "UNKNOWN"),
        "size": ts_group.size,
    }


def get_veg_time_series(
    scenes: Sequence[Scene],
    start_date: datetime,
    date_interval: int,
    geometry_filter: Optional[Callable[[Any], bool]] = None,
) -> List[Scene]:
    """Produce vegetation composite mosaics for regular time steps.

    This is the main entry point of the module.  It mirrors the original
    ``getVegTimeSeries`` GEE function:

    1. Generate date windows from *start_date* to now.
    2. Filter scenes into each window.
    3. Group into ``TimeStepGroup`` instances.
    4. Compute mean-NDVI and quality band per group.

    Args:
        scenes: Raw satellite scenes (each a dict with ``"date"``,
            ``"id"``, ``"bands"`` keys).
        start_date: Earliest date for the time series.
        date_interval: Days between consecutive time steps.
        geometry_filter: Optional spatial filter callable.

    Returns:
        List of composite scene dicts, one per non-empty time step.
    """
    end_date = datetime.now()
    date_ranges = create_date_range_list(start_date, end_date, date_interval)

    filtered: List[Scene] = []
    for dr in date_ranges:
        filtered.extend(filter_bounds_and_dates(scenes, dr, geometry_filter))

    time_groups = make_time_step_coll(date_ranges, filtered)
    return [create_veg_and_quality_band(group) for group in time_groups]
