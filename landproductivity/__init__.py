"""LandProductivity — land degradation analysis pipeline.

This package provides both pure-Python (NumPy) and Google Earth Engine
implementations for:

* **Landscape mapping** — classifying terrain into homogeneous units
  based on land cover, slope and aspect.
* **Vegetation time series** — retrieving, compositing and computing NDVI
  from satellite imagery.
* **Productivity classification** — assigning degradation classes to
  landscape units using percentile-based thresholds.
* **Distance to potential** — measuring how far each pixel's vegetation
  is from the reference (potential) productivity.

Pure-Python modules (``landscape``, ``time_series``, ``productivity``,
``distance_to_potential``) operate on lists / NumPy arrays and are fully
testable without Earth Engine credentials.  GEE modules
(``gee_landscape``, ``gee_time_series``, ``gee_distance_to_potential``)
mirror the same logic server-side.
"""

from .landscape import (
    classify_image,
    create_mask_aoi,
    create_landscape_code,
    create_landscape_map,
    parse_landscape_code,
    simplify_landscape_map,
)
from .gee_landscape import (
    create_landscape_map as gee_create_landscape_map,
    create_mask_aoi as gee_create_mask_aoi,
    classify_image as gee_classify_image,
    simplify_landscape_map as gee_simplify_landscape_map,
)
from .gee_time_series import get_veg_time_series as gee_get_veg_time_series
from .distance_to_potential import (
    calc_distance_to_potential,
    create_dist_to_potential_map,
    get_unique_values as dtp_get_unique_values,
    prep_distance_to_potential,
)

__all__ = [
    "classify_image",
    "create_mask_aoi",
    "create_landscape_code",
    "create_landscape_map",
    "parse_landscape_code",
    "simplify_landscape_map",
    "gee_create_landscape_map",
    "gee_create_mask_aoi",
    "gee_classify_image",
    "gee_simplify_landscape_map",
    "gee_get_veg_time_series",
    "calc_distance_to_potential",
    "create_dist_to_potential_map",
    "dtp_get_unique_values",
    "prep_distance_to_potential",
]
