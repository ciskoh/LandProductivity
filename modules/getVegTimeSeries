/**** Start of imports. If edited, may not auto-convert in the playground. ****/
var geometry = /* color: #d63000 */ee.Geometry.Point([-4.940674779161327, 32.57500115270216]);
/***** End of imports. If edited, may not auto-convert in the playground. *****/
/**
 * @description SCRIPT TO FILTER, CLIP, MASK CLOUDS AND VIDUALIZE LANDSAT IMAGES
 * the following parameters come from LandPro_settings
 * @params { ee.Geometry } aoiGeom : geometry for Area of interest 
 * @param { ee.Date } stDate :  Start Date for timeSeries in YYYY-MM-DD format
 * @params { Number  } dateInt : Number of days between each timestep of the final timeseries
 * @return { ee.imageCollection } with monthly NDVI images
NOTES:  
      - Cloud detection is based on automatic classification and external functions
      - Sentinel images ARE NOT surface reflectance
      
TODO: 
  
  -Add interpolation for missing data
  -Add resampling to specified resolution
  -Add offset correction to make NDVI values unifrm across satellite types
*/



//-----------------INPUT-----------------------
// _SOURCE OF SAT IMAGES
var ls5 = ee.ImageCollection('LANDSAT/LT05/C01/T1_SR'); //Load landsat 5
var ls7 = ee.ImageCollection('LANDSAT/LE07/C01/T1_SR'); //Load landsat 7
var ls8 = ee.ImageCollection('LANDSAT/LC08/C01/T1_SR'); //Load landsat 8

//load external functions
//cloud masks
var cloud_masks = require('users/fitoprincipe/geetools:cloud_masks');

//function to maks clouds from fitoprincipe/GEE
var landsatSRfunction = cloud_masks.landsatSR;

var params = require('users/matteojriva/LandscapeProductivity:LandPro_settings');

//----------------CODE---------------------

// megafunction to export 

exports.getVegTimeSeries=function(aoiGeom, stDate, dateInterval){
/**
 * @description function to get time series of vegetation index value for area of interest
 * @params { ee.Geometry } aoiGeom :  Geometry to use as study area
 * @params { stDate } stDate :  Start Date for timeSeries in YYYY-MM-DD format
 * @params { Number  } dateInt : Number of days between each timestep of the final timeseries
 * @return { ee.imageCollection } with n Vegetation index images
 */
 
// 0. Prepare dates
  var boundaryDateRange=ee.DateRange(stDate, ee.Date(Date.now()));        //list of start and end date
// 1. Filtering and preprocessing
  var filteredRawLs5= filterBoundsAndDates(ls5, boundaryDateRange, aoiGeom);  //Landsat 5
  var filteredRawLs7= filterBoundsAndDates(ls7, boundaryDateRange, aoiGeom);  //LandSat 7
  var filteredRawLs8= filterBoundsAndDates(ls8, boundaryDateRange, aoiGeom); //Landsat 8 
  
  var mergedRawColl=filteredRawLs5
                            .merge(filteredRawLs7)
                            .merge(filteredRawLs8);
                            

  //remove cloudy images 
  var filtMergedRawColl=mergedRawColl.filterMetadata('CLOUD_COVER', 'less_than', 50)
  print('filtered cloudy images', mergedRawColl.size(), filtMergedRawColl.size())

// 1.2 Exclude cloudy and noisy pixels 
  var noCloudsCollection = ee.ImageCollection(mergedRawColl.map(maskClouds));
  print(noCloudsCollection.size());
  var testImage = noCloudsCollection.first();
  
  
// build timestep mosaic images
  var dateRangeList = createDateRangeList(boundaryDateRange, dateInterval);
  var timeStepCollection = makeTimeStepColl(dateRangeList, noCloudsCollection); //exclude empty timeSteps
  var testColl = timeStepCollection.get(0);
  
  // var testImg = createVegAndQualityBand(testColl);
  // // print('testImg', testImg);
  
  var vegMosaicCollection = ee.ImageCollection.fromImages(timeStepCollection.map(createVegAndQualityBand));
  //print("timestep aggregation", timeStepCollection, timeStepCollection.get(0), vegMosaicCollection );
  //print("check for unmasked pixels", vegMosaicCollection.max().reduceRegion({reducer:ee.Reducer.max(), bestEffort: true, scale: vegMosaicCollection.first().projection().nominalScale(), geometry: aoiGeom}));

  
  return ee.ImageCollection(vegMosaicCollection
        .map(function(item){ return item.clip(aoiGeom)})
        .setMulti(
    {
      'date_limits' : boundaryDateRange,
      'vegetation_index' : vegMosaicCollection.first().get('vegetation_index')
    }));
};

//----------------FUNCTIONS---------------------

var createDateRangeList=function(boundaryDateRange, dateInterval)
/** 
 * @description function to create a list of dateRanges to use for imageComposition
 * @param { ee.DateRange } boundaryDateRange: limits of the date range series
 * @param { ee.Number } dateInterval : timestep in days between on range and the other
 * @return  { ee.List } of DateRanges
 */
{
  var intInDays=ee.Number(dateInterval)
  var day_diff = boundaryDateRange.end().difference(boundaryDateRange.start(), 'day').ceil()
  var stepList=ee.List.sequence(0, day_diff, intInDays)
  var dateRangeList=stepList.map(function(n) 
  {
    var currentDate= boundaryDateRange.start().advance(n, 'day')
    var currentRange=ee.DateRange(
    {
      start:currentDate.advance( intInDays.divide(2).floor().multiply(-1), 'day'), 
      end:currentDate.advance( intInDays.divide(2).floor(), 'day')
    })
    return currentRange
  }); 
  
  return dateRangeList;
}

var filterBoundsAndDates = function(imC, boundaryDateRange, aoiGeom) 
/**
 * @description function to filter boundaries and Dates
 * @param { ee.imageCollection } imC : imageCollection to Filter
 * @param { ee.DateRange } dateRange : dateRange to use as filter
 * @param { ee.Geometry } aoi : Area of interest to  use as filter
 */
{
  var newC=imC.filterBounds(aoiGeom)
  //.filterDate(boundaryDateRange.start(), boundaryDateRange.end());
  var newC2 = newC.set({"system:time_start": imC.get("system:time_start"), "system:index": imC.get("system:index")});
  return(newC2);
};

var maskClouds=function(img) 
  /**
   * @description mask cloudy pixels using Landsat QA info and fitoPrincipe cloudMask
   */
{
  var nImg = landsatSRfunction()(img); //if landsat use landsat cloud filtering; //if sentinel use sentinel cloud filtering
  return(nImg);
};


//Actual function


var makeTimeStepColl = function(dateRangeList, imgCollection)
/**
 * @description make small collection based on timeste
 * @param { ee.List } dateRangeList : dateRange for each timeStep
 * @return List of ee.ImageCollection
 */
{
  var timeStepColl = dateRangeList.map(function(dr)
  {
    var dRange = ee.DateRange(dr);
    var timeInterval = ee.Number(dRange.end().difference(dRange.start(), 'day'));
    var smallColl = imgCollection.filterDate
                      (
                        dRange.start(), 
                        dRange.end()
                      );
    return smallColl.set(
                          {
                            'date' : dRange.start().advance(
                            timeInterval.divide(2).floor(), 'day'),
                            'size' : ee.Algorithms.If(ee.ImageCollection(smallColl).size().gt(0), ee.ImageCollection(smallColl).size(), 0)
                          });
  });
  return ee.List(timeStepColl)
  .filter(ee.Filter.gt('size', 0));
};

var createVegAndQualityBand = function(tsColl) 
{
  var tsColl = ee.ImageCollection(tsColl);
  var imNumber = tsColl.size();
  var vegColl = tsColl.map(calcVegetationIndex);
  var qualityBand = makeSimpleQualityBand(vegColl, imNumber);
  var vegMosaic = ee.Image([ee.ImageCollection(vegColl).qualityMosaic('pixel_qa').select(0), qualityBand]);
  return vegMosaic.set(
                      { 
                      'date' : tsColl.get('date'),
                      'size' : tsColl.get('size'),
                      'vegetation_index' : vegColl.first().get('vegetation_index'),
                      'satellite_type' : ee.List(vegColl.aggregate_array('satellite_type')).get(0)
                      });
};

var calcVegetationIndex = function(img) 
/**
 * @description function to calc vegetationindex and add properties
 * @param { ee.Image } img : raw satellite scene
 * @return single band ee.Image
 */
{
  var imageId = img.id();
  var satCode = getLandsatCode(img);
  var vegIndexImage = calcNdvi(img, satCode);
  var vegIndType = vegIndexImage.bandNames().get(0);
  return vegIndexImage.float()
            .set(
              {
              'vegetation_index' : vegIndType,
              'satellite_type' : satCode
              });
};

var getLandsatCode = function(img)
{
  var imageId=img.id();
  var satCode=imageId.slice(imageId.index('L'), imageId.index('L').add(4));
  return ee.String(satCode);
};  

var calcNdvi = function (img, satCode)
/** 
 * @description function to calculate ndvi using correct bands for each satellite
 * @params { ee.String } satCode : code identifying satellite
 * @params { ee.Dictionary } allSatBands : dictionary with band information for calculating NDVI
 * @return single band image
 */
{
  var allSatBands = ee.Dictionary( { 
    'LT05': [ 'B4', 'B3' ],
    'LE07': [ 'B4', 'B3' ],
    'LC08': [ 'B5', 'B4' ]
  } );
  var bandsName = allSatBands.get(satCode);
  var ndviImg = ee.Image(img.normalizedDifference(bandsName));
  var finNdvi = ee.Image([ndviImg, img.select(['pixel_qa'])]);
                    
  return finNdvi.rename(["ndvi", "pixel_qa"]).set({ "vegetation_index" : 'ndvi' });
};

var makeSimpleQualityBand = function(imgCollection, imNumber) {
  return ee.ImageCollection(imgCollection.select(0))
                                .count()
                                .divide(ee.Image.constant(imNumber))
                                .rename(['simpleQA']);
};



