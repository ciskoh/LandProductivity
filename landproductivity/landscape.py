"""Pure-Python landscape map creation for the LandProductivity pipeline.

Translates the original ``createLandscapeMap.js`` GEE script into plain
Python operating on 2-D lists of integers.  The module builds a three-digit
landscape code ``[land_cover | slope_cat | aspect_cat]`` for every pixel,
then simplifies small patches with a local-mode filter.

The public entry point is ``create_landscape_map``; all other functions are
building blocks that can be tested and reused independently.

Used by:
    * ``gee_landscape`` (mirrors the same logic on the GEE side)
    * ``productivity`` and ``distance_to_potential`` (consume the output map)
"""

from collections import Counter
from math import ceil, sqrt
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

IntMatrix = List[List[int]]


def classify_image(
    values: Sequence[float],
    classification_dict: Dict[int, Tuple[float, float, str]],
) -> List[int]:
    """Assign each numeric value to a category using half-open ranges.

    Boundary rule:  ``min < value <= max``  (matches the original GEE
    ``gt / lte`` logic).

    Args:
        values: Raw numeric values to classify (e.g. slope in degrees).
        classification_dict: ``{code: (min, max, label), …}`` look-up.

    Returns:
        List of integer category codes, one per input value.  Values that
        fall outside every range get code ``0``.

    Used by ``classify_image_grid`` and, indirectly, by
    ``create_landscape_map``.
    """
    classified: List[int] = []
    for value in values:
        category = 0
        for key, (min_value, max_value, _) in classification_dict.items():
            if min_value < value <= max_value:
                category = key
                break
        classified.append(category)
    return classified


def create_mask_aoi(
    land_cover: IntMatrix,
    unwanted_categories: Optional[Iterable[int]] = None,
) -> List[List[bool]]:
    """Build a boolean AOI mask from a land-cover grid.

    A pixel is ``True`` when its land-cover value is positive **and** not
    in *unwanted_categories*.

    Args:
        land_cover: 2-D grid of integer land-cover codes.
        unwanted_categories: Codes to exclude (e.g. water, cloud shadow).

    Returns:
        Boolean grid of the same shape as *land_cover*.

    Used by ``create_landscape_map`` to exclude irrelevant pixels.
    """
    unwanted = set(unwanted_categories or [])
    return [
        [value > 0 and value not in unwanted for value in row]
        for row in land_cover
    ]


def create_landscape_code(
    land_cover_value: int,
    slope_category: int,
    aspect_category: int,
) -> int:
    """Encode land-cover, slope and aspect into a single three-digit integer.

    Format: ``land_cover * 100 + slope * 10 + aspect``.
    Returns ``0`` when *land_cover_value* is non-positive (masked pixel).

    Args:
        land_cover_value: Single-digit land-cover code (1–9).
        slope_category: Single-digit slope category (0–9).
        aspect_category: Single-digit aspect category (0–9).

    Returns:
        Three-digit landscape code, or ``0`` for masked pixels.

    Used by ``build_raw_landscape_map``.
    """
    if land_cover_value <= 0:
        return 0
    return land_cover_value * 100 + slope_category * 10 + aspect_category


def parse_landscape_code(code: int) -> Dict[str, int]:
    """Decompose a three-digit landscape code into its components.

    Args:
        code: Landscape code produced by ``create_landscape_code``.

    Returns:
        Dict with keys ``"land_cover"``, ``"slope"`` and ``"aspect"``.

    Used by reporting helpers and tests.
    """
    code_str = str(code).zfill(3)
    return {
        "land_cover": int(code_str[0]),
        "slope": int(code_str[1]),
        "aspect": int(code_str[2]),
    }


def classify_image_grid(
    values: IntMatrix,
    classification_dict: Dict[int, Tuple[float, float, str]],
) -> IntMatrix:
    """Apply ``classify_image`` to every row of a 2-D grid.

    Args:
        values: 2-D grid of raw numeric values.
        classification_dict: Category look-up (see ``classify_image``).

    Returns:
        Grid of integer category codes with the same shape.
    """
    return [classify_image(row, classification_dict) for row in values]


def suppress_flat_aspect(
    slope_grid: IntMatrix,
    aspect_grid: IntMatrix,
    minimum_slope_category: int = 2,
) -> IntMatrix:
    """Zero out aspect for flat pixels where slope direction is meaningless.

    Mirrors the GEE behaviour of multiplying aspect by
    ``slope > threshold``.

    Args:
        slope_grid: Grid of slope category codes.
        aspect_grid: Grid of aspect category codes (same shape).
        minimum_slope_category: Slope categories below this value are
            considered flat and get aspect set to ``0``.

    Returns:
        A new aspect grid with flat-pixel values zeroed.

    Used by ``create_landscape_map``.
    """
    return [
        [
            aspect if slope >= minimum_slope_category else 0
            for slope, aspect in zip(slope_row, aspect_row)
        ]
        for slope_row, aspect_row in zip(slope_grid, aspect_grid)
    ]


def build_raw_landscape_map(
    land_cover: IntMatrix,
    slope_category_map: IntMatrix,
    aspect_category_map: IntMatrix,
    mask: List[List[bool]],
) -> IntMatrix:
    """Combine land-cover, slope and aspect grids into landscape codes.

    Masked pixels (``mask[r][c] == False``) are set to ``0``.

    Args:
        land_cover: Grid of land-cover codes.
        slope_category_map: Grid of slope category codes.
        aspect_category_map: Grid of aspect category codes.
        mask: Boolean AOI mask (same shape).

    Returns:
        Grid of three-digit landscape codes.

    Used by ``create_landscape_map``.
    """
    height = len(land_cover)
    width = len(land_cover[0]) if height else 0
    raw_map: IntMatrix = []
    for r in range(height):
        raw_row: List[int] = []
        for c in range(width):
            if not mask[r][c]:
                raw_row.append(0)
            else:
                raw_row.append(create_landscape_code(
                    land_cover[r][c],
                    slope_category_map[r][c],
                    aspect_category_map[r][c],
                ))
        raw_map.append(raw_row)
    return raw_map


def simplify_landscape_map(
    image: IntMatrix,
    min_allowed_area: int,
    pixel_area: int = 1,
) -> IntMatrix:
    """Replace small patches with the local mode value.

    Derives the kernel radius from ``ceil(sqrt(min_allowed_area /
    pixel_area))`` and slides a square window across the grid, assigning
    each pixel the most common value in the window.

    Args:
        image: Grid of landscape codes.
        min_allowed_area: Minimum patch area (same units as *pixel_area*).
        pixel_area: Area represented by a single pixel.

    Returns:
        Simplified grid of the same shape.

    Raises:
        ValueError: If *min_allowed_area* or *pixel_area* are not positive,
            or if row lengths are inconsistent.

    Used by ``create_landscape_map`` as the final smoothing step.
    """
    if min_allowed_area <= 0:
        raise ValueError("min_allowed_area must be positive")
    if pixel_area <= 0:
        raise ValueError("pixel_area must be positive")

    height = len(image)
    if height == 0:
        return []
    width = len(image[0])
    if any(len(row) != width for row in image):
        raise ValueError("All rows in image must have the same width")

    kernel_size = max(1, int(ceil(sqrt(min_allowed_area / pixel_area))))
    radius = kernel_size // 2

    simplified: IntMatrix = [[image[r][c] for c in range(width)] for r in range(height)]
    for r in range(height):
        for c in range(width):
            window: List[int] = []
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < height and 0 <= nc < width:
                        window.append(image[nr][nc])
            if window:
                most_common, _ = Counter(window).most_common(1)[0]
                simplified[r][c] = most_common
    return simplified


def create_landscape_map(
    land_cover: IntMatrix,
    slope_map: IntMatrix,
    aspect_map: IntMatrix,
    unwanted_categories: Optional[Iterable[int]] = None,
    min_area: int = 20000,
    pixel_area: int = 1,
    slope_classification: Optional[Dict[int, Tuple[float, float, str]]] = None,
    aspect_classification: Optional[Dict[int, Tuple[float, float, str]]] = None,
) -> IntMatrix:
    """Create a simplified landscape map from land-cover, slope and aspect.

    This is the main entry point of the module.  It mirrors the original
    ``createLandscapeMap`` GEE function:

    1. Build an AOI mask from *land_cover* and *unwanted_categories*.
    2. Optionally classify raw slope/aspect values into categories.
    3. Suppress aspect for flat pixels.
    4. Encode every pixel as a three-digit landscape code.
    5. Smooth small patches with a local-mode filter.

    Args:
        land_cover: 2-D grid of integer land-cover codes.
        slope_map: 2-D grid of slope values (raw or pre-classified).
        aspect_map: 2-D grid of aspect values (raw or pre-classified).
        unwanted_categories: Land-cover codes to mask out.
        min_area: Minimum landscape-unit area for simplification.
        pixel_area: Area per pixel (same units as *min_area*).
        slope_classification: If given, raw slope values are classified
            through ``classify_image`` before encoding.
        aspect_classification: Same, for aspect values.

    Returns:
        Simplified grid of three-digit landscape codes.

    Raises:
        ValueError: If input grids have mismatched dimensions.
    """
    if not land_cover:
        return []
    if not (len(land_cover) == len(slope_map) == len(aspect_map)):
        raise ValueError("land_cover, slope_map, and aspect_map must have the same dimensions")

    mask = create_mask_aoi(land_cover, unwanted_categories)

    slope_cats = (
        classify_image_grid(slope_map, slope_classification)
        if slope_classification is not None
        else slope_map
    )
    aspect_cats = (
        classify_image_grid(aspect_map, aspect_classification)
        if aspect_classification is not None
        else aspect_map
    )

    suppressed_aspect = suppress_flat_aspect(slope_cats, aspect_cats)
    raw_map = build_raw_landscape_map(land_cover, slope_cats, suppressed_aspect, mask)
    return simplify_landscape_map(raw_map, min_area, pixel_area)
