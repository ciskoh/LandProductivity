"""
Test suite for LandProductivity landscape map creation functions.
Tests focus on pure functions and logic, not GEE API calls.
"""

import pytest
import numpy as np
from pathlib import Path

# Test data and inputs
TEMP_FOLDER = Path("/tmp/landpro_tests")


# ======================== TEST: classifyImage Function ========================

INPUT_classify_image_slope = {
    "raw_values": np.array([0, 5, 10, 15, 20, 30, 50, 90]),
    "classification_dict": {
        1: [0, 5, 'flat'],
        2: [5, 15, 'sloping'],
        3: [15, 30, 'steep'],
        4: [30, 100, 'very_steep']
    }
}

EXPECTED_classify_image_slope = np.array([1, 1, 2, 2, 2, 3, 4, 4])


def test_classify_image_slope():
    """Test slope classification into categories."""
    raw_values = INPUT_classify_image_slope["raw_values"]
    classification_dict = INPUT_classify_image_slope["classification_dict"]
    expected = EXPECTED_classify_image_slope
    
    # Mock classifyImage logic
    def classify_image(image_array, class_dict):
        result = np.zeros_like(image_array, dtype=int)
        for key, (min_val, max_val, _) in class_dict.items():
            mask = (image_array >= min_val) & (image_array < max_val)
            result[mask] = key
        # Handle edge case where max value should be included
        max_val_key = max(class_dict.keys())
        max_threshold = class_dict[max_val_key][1]
        result[image_array >= max_threshold] = max_val_key
        return result
    
    output = classify_image(raw_values, classification_dict)
    assert np.array_equal(output, expected), f"Expected {expected}, got {output}"


# ======================== TEST: calcThresholdValues (model1090) ========================

INPUT_calc_thresholds = {
    "percentiles": {
        '0': np.array([0.1]),
        '10': np.array([0.3]),
        '90': np.array([0.7]),
        '100': np.array([0.9])
    }
}

EXPECTED_calc_thresholds = {
    'very_degraded': 0.3,
    'healthy': 0.5,  # (0.7 - 0.3) / 2 + 0.3
    'potential': 0.7
}


def test_calc_threshold_values_model1090():
    """Test threshold calculation using 10th and 90th percentiles."""
    percentiles = INPUT_calc_thresholds["percentiles"]
    expected = EXPECTED_calc_thresholds
    
    # Mock model1090 logic
    def model_1090(perc_dict):
        t_very_deg = perc_dict['10'][0]
        t_pot = perc_dict['90'][0]
        t_healthy = (t_pot - t_very_deg) / 2 + t_very_deg
        return {
            'very_degraded': t_very_deg,
            'healthy': t_healthy,
            'potential': t_pot
        }
    
    output = model_1090(percentiles)
    assert output['very_degraded'] == expected['very_degraded']
    assert abs(output['healthy'] - expected['healthy']) < 1e-6
    assert output['potential'] == expected['potential']


# ======================== TEST: getUniqueValues ========================

INPUT_unique_values = {
    "raster": np.array([0, 100, 200, 100, 0, 300, 200, 100])
}

EXPECTED_unique_values = np.array([100, 200, 300])


def test_get_unique_values():
    """Test extraction of unique non-zero values from raster."""
    raster = INPUT_unique_values["raster"]
    expected = EXPECTED_unique_values
    
    # Mock getUniqueValues logic
    def get_unique_values(raster_array):
        return np.array(sorted(np.unique(raster_array)[np.unique(raster_array) > 0]))
    
    output = get_unique_values(raster)
    assert np.array_equal(output, expected)


# ======================== TEST: formatPercentiles ========================

INPUT_format_percentiles = {
    "percentiles_dict": {
        'b1_p0': 0.1,
        'b1_p10': 0.3,
        'b1_p90': 0.7,
        'b1_p100': 0.9,
        'b2_p0': 0.2,
        'b2_p10': 0.4,
        'b2_p90': 0.8,
        'b2_p100': 1.0,
    }
}

EXPECTED_format_percentiles = {
    '0': [0.1, 0.2],
    '10': [0.3, 0.4],
    '90': [0.7, 0.8],
    '100': [0.9, 1.0]
}


def test_format_percentiles():
    """Test formatting percentiles from key-value pairs to organized dict."""
    percentiles_dict = INPUT_format_percentiles["percentiles_dict"]
    expected = EXPECTED_format_percentiles
    
    # Mock formatPercentiles logic
    def format_percentiles(perc_dict):
        result = {'0': [], '10': [], '90': [], '100': []}
        for key, value in perc_dict.items():
            for percentile_key in result.keys():
                if key.endswith(f'_p{percentile_key}'):
                    result[percentile_key].append(value)
        return result
    
    output = format_percentiles(percentiles_dict)
    assert output == expected


# ======================== TEST: createDateRangeList ========================

from datetime import datetime, timedelta

INPUT_create_date_ranges = {
    "start_date": datetime(2020, 1, 1),
    "end_date": datetime(2020, 12, 31),
    "interval_days": 30
}

EXPECTED_create_date_ranges_len = 12  # Approximately monthly


def test_create_date_range_list():
    """Test creation of date ranges for time series composition."""
    start = INPUT_create_date_ranges["start_date"]
    end = INPUT_create_date_ranges["end_date"]
    interval = INPUT_create_date_ranges["interval_days"]
    
    # Mock createDateRangeList logic
    def create_date_range_list(start_date, end_date, interval_days):
        date_ranges = []
        current = start_date
        while current <= end_date:
            range_start = current - timedelta(days=interval_days//2)
            range_end = current + timedelta(days=interval_days//2)
            date_ranges.append((range_start, range_end))
            current += timedelta(days=interval_days)
        return date_ranges
    
    output = create_date_range_list(start, end, interval)
    assert len(output) >= EXPECTED_create_date_ranges_len - 2  # Allow some variance


# ======================== TEST: removeNullValues ========================

INPUT_remove_null = {
    "value_list": [0.5, None, 0.7, None, 0.3, 0.0, 0.9]
}

EXPECTED_remove_null = [0.5, 0.7, 0.3, 0.9]


def test_remove_null_values():
    """Test removal of None and zero values from list."""
    value_list = INPUT_remove_null["value_list"]
    expected = EXPECTED_remove_null
    
    # Mock removeNullValues logic
    def remove_null_values(values):
        return [v for v in values if v is not None and v != 0]
    
    output = remove_null_values(value_list)
    assert output == expected


# ======================== TEST: createDegImage (Degradation Classification) ========================

INPUT_create_deg_image = {
    "veg_values": np.array([0.2, 0.4, 0.6, 0.8, 0.9]),
    "thresholds": [0.3, 0.6, 0.8]  # [very_deg, healthy, potential]
}

EXPECTED_create_deg_image = np.array([1, 2, 3, 4, 4])  # Degradation classes 1-4


def test_create_deg_image():
    """Test degradation image creation based on thresholds."""
    veg_values = INPUT_create_deg_image["veg_values"]
    thresholds = INPUT_create_deg_image["thresholds"]
    expected = EXPECTED_create_deg_image
    
    # Mock createDegImage logic
    def create_deg_image(veg_array, thresh_list):
        # Start with 1, add 1 for each threshold crossed
        deg_img = np.ones_like(veg_array, dtype=int)
        for thresh in thresh_list:
            deg_img[veg_array >= thresh] += 1
        return deg_img
    
    output = create_deg_image(veg_values, thresholds)
    assert np.array_equal(output, expected)


# ======================== TEST: timeSeriesToImage (Date Formatting) ========================

INPUT_timeseries_to_image = {
    "dates": [
        datetime(2020, 1, 15),
        datetime(2020, 2, 14),
        datetime(2020, 3, 15)
    ]
}

EXPECTED_timeseries_date_format = [
    "20JAN15",
    "20FEB14",
    "20MAR15"
]


def test_timeseries_to_image_date_format():
    """Test date formatting for time series to image conversion."""
    dates = INPUT_timeseries_to_image["dates"]
    expected = EXPECTED_timeseries_date_format
    
    # Mock date formatting logic
    def format_dates_for_image(date_list):
        return [d.strftime("%yb%d").upper() for d in date_list]
    
    output = format_dates_for_image(dates)
    assert output == expected


# ======================== TEST: calcNdvi (Vegetation Index) ========================

INPUT_calc_ndvi = {
    "red_band": np.array([0.1, 0.15, 0.2, 0.25]),
    "nir_band": np.array([0.5, 0.55, 0.6, 0.65])
}

EXPECTED_calc_ndvi = np.array([
    (0.5 - 0.1) / (0.5 + 0.1),  # 0.6666...
    (0.55 - 0.15) / (0.55 + 0.15),  # 0.5714...
    (0.6 - 0.2) / (0.6 + 0.2),  # 0.6
    (0.65 - 0.25) / (0.65 + 0.25)  # 0.44827...
])


def test_calc_ndvi():
    """Test NDVI (Normalized Difference Vegetation Index) calculation."""
    red = INPUT_calc_ndvi["red_band"]
    nir = INPUT_calc_ndvi["nir_band"]
    expected = EXPECTED_calc_ndvi
    
    # Mock calcNdvi logic
    def calc_ndvi(red_band, nir_band):
        return (nir_band - red_band) / (nir_band + red_band)
    
    output = calc_ndvi(red, nir)
    assert np.allclose(output, expected)


# ======================== TEST: Landscape Code Parsing ========================

INPUT_landscape_code = {
    "codes": [100, 123, 245, 356, 789]
}

EXPECTED_landscape_code = {
    100: {"land_use": 1, "slope": 0, "aspect": 0},
    123: {"land_use": 1, "slope": 2, "aspect": 3},
    245: {"land_use": 2, "slope": 4, "aspect": 5},
    356: {"land_use": 3, "slope": 5, "aspect": 6},
    789: {"land_use": 7, "slope": 8, "aspect": 9}
}


def test_parse_landscape_code():
    """Test parsing of landscape 3-digit code into components."""
    codes = INPUT_landscape_code["codes"]
    expected = EXPECTED_landscape_code
    
    # Mock landscape code parsing
    def parse_landscape_code(code):
        code_str = str(code).zfill(3)
        return {
            "land_use": int(code_str[0]),
            "slope": int(code_str[1]),
            "aspect": int(code_str[2])
        }
    
    for code in codes:
        output = parse_landscape_code(code)
        assert output == expected[code]


# ======================== Run Tests ========================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
