"""Default configuration for the LandProductivity analysis pipeline.

Centralises land-cover, slope and aspect classification look-ups together
with global analysis parameters (minimum landscape-unit area, start date,
area of interest).  Every other module in the package reads these defaults
when the caller does not supply its own values.

Typical usage::

    from landproductivity.settings import LandProSettings
    cfg = LandProSettings()
    slope_cats = cfg.slope_categories
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class LandProSettings:
    """Immutable container for the analysis configuration.

    Args:
        land_cover_categories: Mapping of integer codes to land-cover
            names (e.g. ``{1: "Urban", 2: "Rangeland", …}``).
        slope_categories: Mapping of integer codes to
            ``(min_deg, max_deg, label)`` tuples used by
            ``landscape.classify_image``.
        aspect_categories: Same structure as *slope_categories* but for
            aspect ranges (degrees from north).
        min_area: Minimum landscape-unit area in square metres.  Used by
            ``landscape.simplify_landscape_map`` to set the kernel size.
        st_date: Start date for vegetation time-series retrieval.
        aoi_geom: Optional GeoJSON-like geometry dict for the area of
            interest.  ``None`` means "use the full extent".
    """

    land_cover_categories: Dict[int, str] = field(default_factory=lambda: {
        1: "Urban",
        2: "Rangeland",
        3: "Forest",
        4: "Dense Forest",
        5: "Dense Shrubland",
        6: "Agriculture",
    })
    slope_categories: Dict[int, Tuple[float, float, str]] = field(default_factory=lambda: {
        1: (0.0, 5.0, "flat"),
        2: (5.0, 15.0, "sloping"),
        3: (15.0, 30.0, "steep"),
        4: (30.0, 100.0, "very_steep"),
    })
    aspect_categories: Dict[int, Tuple[float, float, str]] = field(default_factory=lambda: {
        1: (0.0, 90.0, "north"),
        2: (270.0, 400.0, "north"),
        3: (90.0, 270.0, "south"),
    })
    min_area: int = 20000
    st_date: date = date(2009, 1, 1)
    aoi_geom: Optional[dict] = None

    def get_category_names(self) -> Dict[str, Dict[int, str]]:
        """Return human-readable category names grouped by dimension.

        Returns:
            A dict with keys ``"land_cover"``, ``"slope"`` and
            ``"aspect"``, each mapping integer codes to label strings.
            Used by reporting and visualisation helpers.
        """
        return {
            "land_cover": self.land_cover_categories,
            "slope": {k: v[2] for k, v in self.slope_categories.items()},
            "aspect": {k: v[2] for k, v in self.aspect_categories.items()},
        }
