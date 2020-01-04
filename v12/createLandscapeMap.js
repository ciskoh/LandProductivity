/**
 * @description SCRIPT TO CREATE A LANDSCAPE UNIT MAP BASED ON LAND USE, ASPECT AND SLOPE STEEPNESS CATEGORIES,
 * TO BE CALLED AS EXTERNAL FUNCTION.
 * following parameters all in LandPro_settings:
 * @params { ee.Dictionary } landCoverCat: categories of land cover Mapp
 * @params { ee.Dictionary } slopeCat: categories to use for slope codes
 * @params { ee.Dictionary } aspCat : catgeories to use for aspect codes
 * @params { ee.Image } dem : digital elevation model
 * @params { ee.Number } minArea : minimum landscape unit in sq.m.
 * for methodology see Jucker Riva et al., 2017, Applied Geography

TO DO:
- export landscape Map as imageCollection


NOTES:
- LandCover must be a raster
- Requires the following parameters :

*/
//----------------------------PARAMETERS-----------------------------------------------------
// Import parameters from main parameter module
var setModule    = require('users/matteojriva/LandscapeProductivity:LandPro_settings');
var settings     = setModule.Settings
var landCoverCat = settings.get(landCoverCat);
var slopeCat     = settings.get(slopeCat);
var aspCat       = settings.get(aspCat);
var dem          = settings.get(dem);


//----------------------------CODE----------------------------------------------------------
exports.doc=" description: Module to build landscape map using land use, aspect and slope."+
   "param { ee.Image } landCoverMap: raster land cover /land use map"+
   "param { ee.List } unwantedCat: Categories to exclude from landscapeMap"+
   "param { Number } minArea: minimum Area in sq m for landscape units"+
   "return { ee.ImageCollection } landscapeMap";

exports.createLandscapeMap=function(landCoverMap, unwantedCat, minArea ) {
  /**
   * @description Module to build landscape map using land use, aspect and slope.
   * @param { ee.Image } landCoverMap: raster land cover /land use map
   * @param { ee.List } unwantedCat: Categories to exclude from landscapeMap
   * @param { String } propertyName: name of property with landCover categories as dictionary
   * @param { Number } minArea: minimum Area in sq m for landscape units
   * @return { ee.ImageCollection } landscapeMap
   */

   //checks for missing variables
   var unwantedCat  = unwantedCat   || settings.get(unwantedCat) || ee.List([0]);
   var minArea      = minArea       || settings.get(minArea)     || ee.Number(1);


  var maskAoi=createMaskAoi(landCoverMap, unwantedCat).selfMask();

  //get terrain from dem
  var clippedDem      = dem.clip(maskAoi.geometry());

  var rawAspect       = ee.Terrain.aspect(clippedDem).toInt();    //calc aspect
  var rawSlope        = ee.Terrain.slope(clippedDem)              //slope calc
                        .unitScale(0,90).multiply(100).int();     //translate in percentage

  var classifiedSlope  = classifyImage(rawSlope, slopeCat) ;      //classify slope according to slope categories
  var classifiedAspect = classifyImage(rawAspect, aspCat)         //classify aspect
                         .multiply                                //make flat areas 0 aspect
                         (
                           classifiedSlope.gt
                           (
                            ee.Image.constant(1)
                           )
                         );
  var rawLandscapeMap=ee.Image(
          landCoverMap.mask(maskAoi).multiply(100) ) //land use is first digit
          .add(classifiedSlope.multiply(10))         //slope is second digit
          .add(classifiedAspect);                    //aspect is first digit


//simplify image
var cleanLandscapeMap=simplifyLandscapeMap(rawLandscapeMap, minArea)
                       .mask(maskAoi).short();
//Add properties to image

// get all values for property lsValueList
var lsValueDic = cleanLandscapeMap.reduceRegion(
  {
    reducer   : ee.Reducer.frequencyHistogram(),
    geometry  : cleanLandscapeMap.geometry() ,
    scale     : 10,
    maxPixels : 10e10
  }).values().get(0);

var lsValueString = ee.List(ee.Dictionary(lsValueDic).keys())
                          .map(function(x) { return ee.Number.parse(x)})
                          .filter(ee.Filter.gt('item', 0))
                          .join(" , ");
print(lsValueString);


//add properties to final Map
var completeLandscapeMap = cleanLandscapeMap.setMulti(
  {
    'description' : 'map of homogenous landscape units. Each landscape class is identified with a three digits code: first is land use, second is slope, third is aspect',
    'date_created': ee.Date(Date.now()).millis(),
    'categories'  : ee.Dictionary( { landCover : landCoverCat, slope: slopeCat, aspect: aspCat } ).serialize(),
    // 'aoiMask'     : maskAoi.serialize(),
    'lsValueList' : lsValueString
  });

// print("finished landscapeMap", completeLandscapeMap)
return ee.Image(completeLandscapeMap)
}

//----------------------------FUNCTIONS-----------------------------------------------------

 var createMaskAoi=function(landCover, unwantedCat)
  /**
   * @description create mask of area of interest
   */
  {
    var lcMaskColl=unwantedCat.map(function(cat)
    {
      return landCover.neq(ee.Image.constant(cat)).multiply(landCover.gt(ee.Image.constant(0)));
    });
    return ee.ImageCollection(lcMaskColl).min().clip(landCover.geometry());
  };

var classifyImage=function(image, classificationDic)
/**
 * @description function to classify slope and aspect using classificationDic
 * @param { ee.Image } image: image to be classified
 * @param { ee.Dictionary } classificationDic: dictionary with min and max values to use as classifier
 * @return { ee.Image } with values 1 to keyNumbers
 */
{
  var keyList=ee.Dictionary(classificationDic).keys();   //get all the categories
  var imgList=keyList.map(function(key)
  {
    var valueList= ee.List(classificationDic.get(key)); //first: min, second: max, third: category Description //fourth: correct keyValue if needed

    var keyValue = ee.Number.parse(key)

    var classifiedImg=ee.Image(image.gt(ee.Number(valueList.get(0))))
                          .and(image.lte(ee.Number(valueList.get(1))))
                          .toInt64();
    return classifiedImg.multiply(keyValue);
  });
  return ee.ImageCollection(imgList).max().rename(['band']).toInt32();
};


var simplifyLandscapeMap=function(img, minAllowedArea)
/**
* @description function to simplify map to obtain areas that below minAllowedArea
* @param { ee.Image } img: image to simplify
* @param { minAllowedArea } minAllowedArea: min area allowed in meters
* @return { ee.Image }
*/
{
 var pixelSize = ee.Number(img.projection().nominalScale()).pow(2)
 var minAreaInPixels= ee.Number(minAllowedArea)
                     .divide(pixelSize) //calculate nummber of pixels in minArea
 var simpImg=img            //simplify image using neighbourhood analysis
  .reduceNeighborhood({
    reducer : ee.Reducer.mode(), //mode as criteria
    kernel  : ee.Kernel.square(minAreaInPixels.sqrt().ceil())  //kernel defined by minArea
  });
  return(simpImg.clip(img.geometry()));
};
