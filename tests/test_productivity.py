"""Unit tests for the productivity map translation."""

import unittest

import numpy as np

from landproductivity.productivity import (
    calc_threshold_values,
    create_deg_image,
    create_productivity_map,
    format_percentiles,
    get_unique_values,
    make_percentile_array,
)


class TestProductivityFunctions(unittest.TestCase):
    def test_get_unique_values(self):
        landscape = np.array([[0, 100, 200], [100, 300, 0]])
        expected = np.array([100, 200, 300])
        np.testing.assert_array_equal(get_unique_values(landscape), expected)

    def test_make_percentile_array(self):
        masked_veg = np.array([[[0.1, 0.2], [0.3, np.nan]], [[0.4, 0.5], [0.6, 0.7]]])
        percentiles = make_percentile_array(masked_veg)
        self.assertIn("10", percentiles)
        self.assertEqual(len(percentiles["10"]), 2)

    def test_format_percentiles(self):
        percentiles = {"0": [0.1], "10": [0.2], "90": [0.8], "100": [0.9]}
        formatted = format_percentiles(percentiles)
        self.assertEqual(formatted, percentiles)

    def test_calc_threshold_values(self):
        percentiles = {"0": [0.1], "10": [0.2], "90": [0.8], "100": [0.9]}
        thresholds = calc_threshold_values(percentiles)
        self.assertEqual(thresholds, [[0.2, 0.5, 0.8]])

    def test_create_deg_image(self):
        veg_stack = np.array([[[0.1, 0.2], [0.7, 0.9]], [[0.4, 0.5], [0.2, 0.3]]])
        thresholds = [[0.2, 0.5, 0.8], [0.3, 0.6, 0.9]]
        deg_image = create_deg_image(veg_stack, thresholds)
        self.assertEqual(deg_image.shape, veg_stack.shape)
        self.assertEqual(deg_image[0, 0, 0], 1)

    def test_create_productivity_map(self):
        landscape = np.array([[100, 100], [200, 200]])
        veg = [
            np.array([[0.1, 0.2], [0.3, 0.4]]),
            np.array([[0.5, 0.6], [0.7, 0.8]]),
        ]
        result = create_productivity_map(landscape, veg)
        self.assertEqual(result.classification.shape, (2, 2, 2))
        self.assertEqual(result.dates, ["T0", "T1"])


if __name__ == "__main__":
    unittest.main()
