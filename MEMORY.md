# LandProductivity Project Memory

## Code Analysis Summary

### Module Breakdown

#### 1. LandPro_settings.js
**Purpose:** Configuration and settings module for the entire application
**Functions:** None (configuration only)
**Key variables:**
- landCoverMap (GEE Image)
- landCoverCat, slopeCat, aspCat (classifications)
- dem (SRTM Digital Elevation Model)
- aoiGeom (Area of Interest geometry)
- stDate (start date for time series)

**Technical Debt:**
- ❌ Hardcoded GEE asset paths (`users/matteojriva/...`)
- ❌ Not environment-specific (no dev/prod configs)
- ❌ Settings scattered (not all grouped in one place)

---

#### 2. createLandscapeMap.js
**Purpose:** Creates homogeneous landscape unit map based on land use, slope, and aspect
**Main Export:** `createLandscapeMap(landCoverMap, unwantedCat, minArea)`
**Internal Functions:**
- `createMaskAoi()` - Creates area of interest mask
- `classifyImage()` - Classifies images using min/max ranges
- `simplifyLandscapeMap()` - Simplifies map using neighborhood mode analysis

**Algorithm:**
1. Creates AOI mask from land cover
2. Calculates aspect and slope from DEM
3. Classifies slope and aspect into categories
4. Creates 3-digit code: [landUse|slope|aspect]
5. Simplifies using kernel mode filtering
6. Returns image with metadata

**Technical Debt:**
- ❌ Complex nested GEE operations hard to test
- ❌ No input validation
- ❌ Floating point slope calculations could lose precision
- ❌ `simplifyLandscapeMap` uses math on pixel counts that could be clearer
- ❌ Heavy dependence on GEE API chaining makes it hard to debug

---

#### 3. createProductivityMap.js
**Purpose:** Converts vegetation images to productivity classes based on landscape units
**Main Export:** `createProductivityMap(landscape, veg)`
**Internal Functions:**
- `imgToCollectionByValues()` - Divides image by unique values
- `checkIfTimeSeries()` - Checks if input is time series
- `timeSeriesToImage()` - Converts time series to multiband image
- `getUniqueValues()` - Gets unique pixel values
- `makePercentileArray()` - Creates percentile array
- `formatPercentiles()` - Formats percentile output
- `calcThresholdValues()` - Calculates threshold values
- `createDegImage()` - Creates degradation image
- `bandsToCollection()` - Converts bands to collection

**Technical Debt:**
- ⚠️ **SEVERE:** Function calls other functions that aren't defined in this file (missing dependencies)
- ❌ Complex conditional logic using `ee.Algorithms.If`
- ❌ Nested loops and map operations hard to trace
- ❌ Percentile calculation logic unclear (no documentation on algorithm)
- ❌ TODOs mention "improve filtering" and "improve speed"
- ❌ No null value handling shown in provided code

---

#### 4. calcDistanceToPotential.js
**Purpose:** Calculates ratio of vegetation value to reference potential areas
**Main Exports:**
- `prepDistanceToPotential(ls, ltProd, vegTs)` - Prepares distance to potential map
- `calcDistanceToPotential(distanceToPotential, geom)` - Calculates values for geometry

**Internal Functions:**
- `createDistToPotentialMap()` - Creates the distance map
- `removeNullValues()` - Removes null from arrays
- `addIdPropIfNeeded()` - Adds ID properties

**Technical Debt:**
- ❌ Code incomplete in provided excerpt (likely more functions below)
- ❌ Complex nested `ee.Algorithms.If` statements
- ❌ Multiple intermediate variables make logic hard to follow
- ❌ Reference area filtering (eq(4)) is magic number, not configurable
- ❌ Missing null value handling

---

#### 5. getVegTimeSeries.js
**Purpose:** Retrieves and processes vegetation time series from Landsat satellites
**Main Export:** `getVegTimeSeries(aoiGeom, stDate, dateInterval)`
**Internal Functions:**
- `createDateRangeList()` - Creates date ranges for composition
- `filterBoundsAndDates()` - Filters images by geometry and date
- `maskClouds()` - Cloud masking
- `makeTimeStepColl()` - Creates timestep collection
- `createVegAndQualityBand()` - Creates vegetation index band

**Technical Debt:**
- ⚠️ **BLOCKING:** Imports external cloud_masks module (`users/fitoprincipe/geetools`)
- ❌ Multiple hardcoded Landsat collections (LS5, LS7, LS8)
- ❌ Hardcoded cloud cover threshold (50%)
- ❌ No offset correction between satellite types mentioned in TODO
- ❌ TODOs: interpolation, resampling, offset correction not implemented

---

#### 6-8. Other Modules (graphicExportConstructors, ExportFilesToAsset, OutilDeSuivi-2019)
- **graphicExportConstructors.js**: UI functions, not core logic
- **ExportFilesToAsset.js**: Workflow orchestration, not core logic
- **OutilDeSuivi-2019.js**: Specific monitoring tool, not reusable module

---

## Technical Debt Summary

### Critical Issues (Must fix for translation):
1. **Missing function definitions** in createProductivityMap.js
2. **External dependencies** from fitoprincipe/geetools
3. **Hardcoded asset paths** that won't work in Python
4. **Magic numbers** (e.g., landscape 3-digit code system unclear)

### High Priority Issues:
1. **Complex nested GEE operations** - Need to be broken down into testable functions
2. **No input validation** - Functions assume correct input
3. **No error handling** - Silent failures possible with null data
4. **Incomplete functions** - TODOs not implemented
5. **Unclear algorithms** - Percentile calculation, threshold logic needs documentation

### Medium Priority Issues:
1. **Multiple Landsat versions** - Need unified approach
2. **Hardcoded thresholds** - Cloud cover 50%, reference category 4, etc.
3. **Date handling** - Complex and could have edge cases
4. **Performance concerns** - Author noted "improve speed of script"

### Code Quality Issues:
1. **Inconsistent naming** - Sometimes camelCase, sometimes snake_case
2. **Mixed variable declaration** - `var` used inconsistently
3. **No docstring standards** - JSDoc not consistently applied
4. **Test coverage** - Zero tests

---

## Translation Strategy (Python)

### Step 1: Understand & Test Phase (CURRENT)
- ✅ Analyzed all modules
- ⏳ Document complete code structure
- ⏳ Find missing function definitions
- ⏳ Create simple unit tests for each module
- ⏳ Note which functions depend on each other

### Step 2: Python Translation
- Replace GEE JavaScript API with `ee` Python client
- Replace nested chains with intermediate variables
- Add input validation
- Add comprehensive docstrings
- Reorganize imports (no more GEE hardcoded paths)
- Create configuration system

### Step 3: Refactoring & Testing
- Simplify complex functions
- Ensure PEP8 compliance
- Add logging instead of print()
- Create integration tests

---

## Next Steps
1. Find all missing function definitions
2. Request user input on core assumptions
3. Create test data structure
4. Create first test cases
5. Begin Python translation
## Recent Progress
- Added `landproductivity/distance_to_potential.py` based on `v12/calcDistanceToPotential.js`
- Added `tests/test_distance_to_potential.py` with coverage for helper functions and complete workflow
- Exported distance-to-potential functions through `landproductivity/__init__.py`

### 2026-06-18: Code Simplifier + Sphinx Docs
- Ran code simplifier on all 9 Python modules (`settings`, `landscape`, `time_series`, `productivity`, `distance_to_potential`, `gee_landscape`, `gee_time_series`, `gee_distance_to_potential`, `__init__`)
- Added Google-style docstrings to every function, class and module
- Added module-level docstrings explaining purpose, dependencies and consumers
- Streamlined code: list comprehensions, cleaner variable names, PEP8 compliance
- All 28 tests pass unchanged
- Created full Sphinx documentation with autodoc, Napoleon, RTD theme, viewcode, intersphinx
- Added `.gitignore`
- Two atomic commits: `2260c62` (refactoring) and `bb81319` (docs)
