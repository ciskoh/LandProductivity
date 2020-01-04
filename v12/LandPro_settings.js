//----------------------------PARAMETERS-----------------------------------------------------
// ----- Settings for createLandscapeMap module

exports.doc="Main settings to run landscape Productivity app. packaged as dictionary named settings"

var settings  = {}
//Land Cover Map
settings["landCoverMap"] = ee.Image('users/matteojriva/Midelt/landCoverMap092019');

//Land Cover Categories
settings["landCoverCat"] = ee.Dictionary(
{
  1: 'Urban',
  2: 'Rangeland',
  3: 'Forest',
  4: 'dense Forest',
  5: 'dense shrubland',
  6: 'agriculture'
});

//DTM
settings["dem"] = ee.Image('USGS/SRTMGL1_003');

//slope steepness categories for classification based on FAO soil categories in (%)
//last value is the category code
settings["slopeCat"]=ee.Dictionary(
{
  1: [0,5, 'flat'],
  2: [5,15,'sloping'],
  3: [15,30, 'steep'],
  4: [30, 100, 'very_steep']
});

//Aspect categoriesfor classification
//last value is the category code
settings["aspCat"]=ee.Dictionary(
{
  1: [0,90, 'north'],
  2: [270,400, 'north'],
  3: [90,270, 'south'],
});


// Minimum area of land use unit in sq. m.
settings["minArea"]=20000;

settings["aoiGeom"]= ee.FeatureCollection("users/matteojriva/pastures/bb").union().geometry()
// ------ Settings for the creation of NDVI timeSeries

settings["stDate"] = ee.Date("2009-01-01");

settings["dateInt"] = 30;

export.settings = ee.Dictionary(settings)

//---------------Settings for Productivity Map

//Choose statistical model for the analysis between the following
var model=model1090

// Possible choices:

var model1090=function(percentiles)
  /** @description model uses 10 percentile and
   * ..90th to classify very degraded and potential
   */
  {
    var tVeryDeg = ee.Number.parse(percentiles.get('10'))
    var tPot     = ee.Number.parse(percentiles.get('90'))
    var tHealthy = tPot.subtract(tVeryDeg).divide(2).add(tVeryDeg)
    return ee.List([tVeryDeg, tHealthy, tPot])
  }

//----------------------FUNCTIONS-----------------

//  create module specific settings #TODO
var createModuleSettings(settingsDic, keyList, addedVariables)
