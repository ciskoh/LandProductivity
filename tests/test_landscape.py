"""Unit tests for the LandProductivity Python landscape module."""

import unittest
from landproductivity.landscape import (
    build_raw_landscape_map,
    classify_image,
    classify_image_grid,
    create_landscape_code,
    create_landscape_map,
    create_mask_aoi,
    parse_landscape_code,
    simplify_landscape_map,
    suppress_flat_aspect,
)
from landproductivity.settings import LandProSettings


class TestLandscapeFunctions(unittest.TestCase):
    def test_classify_image_slope(self):
        values = [0.0, 5.0, 10.0, 15.0, 20.0, 30.0, 50.0, 90.0]
        classification_dict = {
            1: (0.0, 5.0, "flat"),
            2: (5.0, 15.0, "sloping"),
            3: (15.0, 30.0, "steep"),
            4: (30.0, 100.0, "very_steep"),
        }
        expected = [0, 1, 2, 2, 3, 3, 4, 4]
        self.assertEqual(classify_image(values, classification_dict), expected)

    def test_create_mask_aoi(self):
        land_cover = [
            [1, 2, 3],
            [0, 4, 5],
        ]
        expected = [
            [True, True, True],
            [False, True, False],
        ]
        self.assertEqual(create_mask_aoi(land_cover, [5, 6]), expected)

    def test_create_landscape_code(self):
        self.assertEqual(create_landscape_code(2, 3, 1), 231)
        self.assertEqual(create_landscape_code(0, 2, 1), 0)

    def test_parse_landscape_code(self):
        self.assertEqual(parse_landscape_code(231), {"land_cover": 2, "slope": 3, "aspect": 1})
        self.assertEqual(parse_landscape_code(5), {"land_cover": 0, "slope": 0, "aspect": 5})

    def test_simplify_landscape_map(self):
        image = [
            [100, 100, 200],
            [100, 200, 200],
            [300, 200, 200],
        ]
        simplified = simplify_landscape_map(image, min_allowed_area=4, pixel_area=1)
        self.assertEqual(simplified[0][0], 100)
        self.assertEqual(simplified[1][1], 200)

    def test_create_landscape_map(self):
        land_cover = [
            [1, 2],
            [3, 0],
        ]
        slope_map = [
            [2, 3],
            [1, 4],
        ]
        aspect_map = [
            [1, 2],
            [3, 1],
        ]
        output = create_landscape_map(land_cover, slope_map, aspect_map, unwanted_categories=[0], min_area=1, pixel_area=1)
        self.assertEqual(output, [[121, 232], [310, 0]])

    def test_suppress_flat_aspect(self):
        slope_grid = [
            [1, 2],
            [1, 3],
        ]
        aspect_grid = [
            [2, 3],
            [1, 4],
        ]
        expected = [
            [0, 3],
            [0, 4],
        ]
        self.assertEqual(suppress_flat_aspect(slope_grid, aspect_grid), expected)

    def test_build_raw_landscape_map(self):
        land_cover = [
            [1, 2],
            [3, 4],
        ]
        slope_map = [
            [2, 2],
            [1, 4],
        ]
        aspect_map = [
            [1, 2],
            [3, 4],
        ]
        mask = [
            [True, False],
            [True, True],
        ]
        expected = [
            [121, 0],
            [313, 444],
        ]
        self.assertEqual(build_raw_landscape_map(land_cover, slope_map, aspect_map, mask), expected)

    def test_create_landscape_map_with_classification(self):
        land_cover = [
            [1, 1],
            [0, 2],
        ]
        raw_slope = [
            [0.0, 7.0],
            [3.0, 40.0],
        ]
        raw_aspect = [
            [45.0, 180.0],
            [0.0, 315.0],
        ]
        slope_categories = {
            1: (0.0, 5.0, "flat"),
            2: (5.0, 15.0, "sloping"),
            3: (15.0, 30.0, "steep"),
            4: (30.0, 100.0, "very_steep"),
        }
        aspect_categories = {
            1: (0.0, 90.0, "north"),
            2: (90.0, 270.0, "south"),
            3: (270.0, 360.0, "north"),
        }
        output = create_landscape_map(
            land_cover,
            raw_slope,
            raw_aspect,
            unwanted_categories=[0],
            min_area=1,
            pixel_area=1,
            slope_classification=slope_categories,
            aspect_classification=aspect_categories,
        )
        self.assertEqual(output, [[100, 122], [0, 243]])

    def test_settings_categories(self):
        config = LandProSettings()
        categories = config.get_category_names()
        self.assertIn("land_cover", categories)
        self.assertEqual(categories["land_cover"][2], "Rangeland")


if __name__ == "__main__":
    unittest.main()
