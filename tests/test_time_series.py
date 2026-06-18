"""Unit tests for the vegetation time series translation."""

import unittest
from datetime import datetime, timedelta

import numpy as np

from landproductivity.time_series import (
    TimeStepGroup,
    calc_ndvi,
    calc_vegetation_index,
    create_date_range_list,
    create_veg_and_quality_band,
    filter_bounds_and_dates,
    get_landsat_code,
    make_time_step_coll,
)


class TestTimeSeriesFunctions(unittest.TestCase):
    def test_get_landsat_code(self):
        self.assertEqual(get_landsat_code("LANDSAT/LC08/C01/T1_SR/scene"), "LC08")
        self.assertEqual(get_landsat_code("LANDSAT/LT05/C01/T1_SR/scene"), "LT05")
        self.assertIsNone(get_landsat_code("UNKNOWN_SCENE"))

    def test_calc_ndvi(self):
        red = np.array([0.1, 0.2, 0.0])
        nir = np.array([0.5, 0.3, 0.0])
        expected = np.array([0.66666667, 0.2, 0.0])
        output = calc_ndvi(red, nir)
        np.testing.assert_allclose(output, expected, atol=1e-6)

    def test_filter_bounds_and_dates(self):
        scenes = [
            {"id": "1", "date": datetime(2020, 1, 1), "geometry": None},
            {"id": "2", "date": datetime(2020, 6, 1), "geometry": None},
        ]
        date_range = (datetime(2020, 1, 1), datetime(2020, 3, 1))
        output = filter_bounds_and_dates(scenes, date_range)
        self.assertEqual(len(output), 1)
        self.assertEqual(output[0]["id"], "1")

    def test_create_date_range_list(self):
        start = datetime(2020, 1, 1)
        end = datetime(2020, 3, 1)
        output = create_date_range_list(start, end, 30)
        self.assertTrue(len(output) >= 2)
        self.assertEqual(output[0][0], datetime(2020, 1, 1) - timedelta(days=15))

    def test_make_time_step_coll(self):
        scenes = [
            {"id": "1", "date": datetime(2020, 1, 1)},
            {"id": "2", "date": datetime(2020, 1, 20)},
        ]
        date_ranges = [(datetime(2020, 1, 1), datetime(2020, 1, 15)), (datetime(2020, 1, 16), datetime(2020, 1, 31))]
        output = make_time_step_coll(date_ranges, scenes)
        self.assertEqual(len(output), 2)
        self.assertEqual(output[0].size, 1)
        self.assertEqual(output[1].size, 1)

    def test_create_veg_and_quality_band(self):
        scenes = [
            {"id": "LT05_scene", "date": datetime(2020, 1, 1), "bands": {"red": np.array([0.1]), "nir": np.array([0.5]), "pixel_qa": np.array([1])}},
            {"id": "LT05_scene2", "date": datetime(2020, 1, 2), "bands": {"red": np.array([0.2]), "nir": np.array([0.6]), "pixel_qa": np.array([1])}},
        ]
        group = TimeStepGroup(date=datetime(2020, 1, 15), images=scenes, size=2)
        output = create_veg_and_quality_band(group)
        self.assertEqual(output["vegetation_index"], "ndvi")
        self.assertEqual(output["size"], 2)
        np.testing.assert_allclose(output["ndvi"], np.array([0.58333333]), atol=1e-6)
        np.testing.assert_allclose(output["simpleQA"], np.array([1.0]), atol=1e-6)


if __name__ == "__main__":
    unittest.main()
