"""Unit tests for the LandProductivity distance-to-potential module."""

import unittest

import numpy as np

from landproductivity.distance_to_potential import (
    DistanceToPotentialResult,
    calc_distance_to_potential,
    create_dist_to_potential_map,
    get_unique_values,
    prep_distance_to_potential,
    remove_null_values,
    time_series_to_image,
)


class TestDistanceToPotential(unittest.TestCase):
    def test_get_unique_values(self):
        raster = np.array([[0, 100, 200], [100, 300, 0]])
        np.testing.assert_array_equal(get_unique_values(raster), np.array([100, 200, 300]))

    def test_remove_null_values(self):
        values = [0.1, None, np.nan, 0.4]
        self.assertEqual(remove_null_values(values), [0.1, 0.0, 0.0, 0.4])

    def test_time_series_to_image(self):
        veg_ts = [
            np.array([[0.1, 0.2], [0.3, 0.4]]),
            np.array([[0.5, 0.6], [0.7, 0.8]]),
        ]
        stack, dates = time_series_to_image(veg_ts, ["T0", "T1"])
        self.assertEqual(stack.shape, (2, 2, 2))
        self.assertEqual(dates, ["T0", "T1"])

    def test_create_dist_to_potential_map(self):
        ls_mask = np.array([[1, 0], [1, 1]], dtype=bool)
        veg_img = np.array([[[1.0, 2.0], [3.0, 4.0]], [[2.0, 4.0], [6.0, 8.0]]])
        ref_values = [2.0, 4.0]
        expected = np.array([[[50.0, 0.0], [150.0, 200.0]], [[50.0, 0.0], [150.0, 200.0]]])
        output = create_dist_to_potential_map(ls_mask, veg_img, ref_values)
        np.testing.assert_allclose(output, expected)

    def test_prep_distance_to_potential(self):
        ls = np.array([[100, 100], [200, 200]])
        lt_prod = np.array([[4, 4], [1, 4]])
        veg_ts = [
            np.array([[0.2, 0.4], [0.6, 0.8]]),
            np.array([[0.3, 0.6], [0.9, 1.2]]),
        ]
        result = prep_distance_to_potential(ls, lt_prod, veg_ts, dates=["T0", "T1"])
        self.assertIsInstance(result, DistanceToPotentialResult)
        self.assertEqual(result.image.shape, (2, 2, 2))
        self.assertEqual(result.date_list, ["T0", "T1"])

    def test_calc_distance_to_potential(self):
        ls = np.array([[100, 200], [100, 200]])
        lt_prod = np.array([[4, 4], [4, 4]])
        veg_ts = [
            np.array([[1.0, 2.0], [3.0, 4.0]]),
            np.array([[2.0, 4.0], [6.0, 8.0]]),
        ]
        result = prep_distance_to_potential(ls, lt_prod, veg_ts, dates=["T0", "T1"])
        geom_mask = np.array([[True, False], [True, True]])
        output = calc_distance_to_potential(result, geom_mask)
        self.assertIn("areaDist", output)
        self.assertIn("avgDist", output)
        self.assertEqual(output["dateList"], ["T0", "T1"])


if __name__ == "__main__":
    unittest.main()
