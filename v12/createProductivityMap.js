/** @description: module to calculate landscape based productivity map using ndvi and landscape Image


/* TODOS:
-improve filtering of landscape values line 148
-improve speed of script
-create dissemination page
*/

//------------------------INPUT & PARAMETERS----------------------------------
// 
//-------------------CODE

exports.createProductivityMap = function(landscape, veg) {
  /** @description function to convert veg image(s) in landscape-based productivity classes
   * @param { function } classification model, not actually used
   * @return image or imageCollection
   */
   
  //Input preparation
  // var landscapeCollection = imgToCollectionByValues(landscape);
  // print("landscapeCollection",landscapeCollection);
  
  // tsCheck is 0 if image is only one, is an integer >0 if veg is image collection
  var tsCheck = checkIfTimeSeries(veg);
  // print('CREATEPRODMAP: size of time series:', tsCheck);
  
  //tranform time series to multiband image, if needed
  var veg2 = ee.Image(ee.Algorithms.If(
        tsCheck, 
        timeSeriesToImage(ee.ImageCollection(veg).select(0)),
        veg.select(0)));
  // print("veg image", veg2);
  
// Start OF CLASSIFICATION
 print('CREATEPRODMAP: starting classification');
 var unLsVals=getUniqueValues(landscape)
 //print('ls values', unLsVals) 
  var completeImageList=unLsVals.map(function(lsValue) 
  {  
    var lsValue   = ee.Number(lsValue)
    var maskedVeg = veg2.mask(landscape.eq(ee.Image.constant(lsValue))); // for testing: ee.Image.constant(0).clip(landscape.geometry())
   // print('starting data', lsImg, maskedVeg, lsValue )
    var percentiles=makePercentileArray(maskedVeg);
    var formattedPerc=formatPercentiles(percentiles);
    //print('percentiles in correct format', formattedPerc)
    var imageNotNull = ee.Number(formattedPerc
    .values().flatten()
    .reduce(ee.Reducer.sum())).ceil()
    
    // print('image has values?', imageNotNull)
    
    var thresholdList=ee.Algorithms.If(
      imageNotNull,
      calcThresholdValues(formattedPerc, tsCheck)
      );
    // print('thresholds for', lsValue, thresholdList)
    
    var degImage=ee.Algorithms.If(
      imageNotNull,
      createDegImage(maskedVeg, thresholdList),
      ee.Image.constant(ee.List.repeat(0,tsCheck)).rename(veg2.bandNames()).clip(landscape.geometry())
      );
    return ee.Image(degImage).set({'cat': lsValue}).selfMask().toShort();
    
    // return(ee.Image.constant(1)).set({'cat':lsValue});
  });
  
  var classifiedImage=ee.ImageCollection(completeImageList).mosaic()
  var classifiedCollection= ee.ImageCollection(bandsToCollection(classifiedImage))
  // print("complete image", completeImageList, classifiedCollection);

  print("-------FINISHED MODULE CreateProductivityMap---------");
  return classifiedCollection;
}; //end of main function



//-------------------FUNCTIONS

var imgToCollectionByValues= function(raster) 
  /** divides image into collection based on unique Values of pixels
   */
{
  var allRasterValues= getUniqueValues(raster).filter(ee.Filter.gt('item', 0));
  // print(allRasterValues);
  
  var rasterCollection = ee.ImageCollection.fromImages(
    allRasterValues.map(function(lsValue)
    {
      var lsValue      = ee.Number.parse(lsValue);
      var singleCatImg = raster.eq(lsValue);
      return ee.Image(singleCatImg).set({'cat': lsValue}).toInt()
    }
    ));
  return rasterCollection
  // .filter(ee.Filter.gt('item', 0))
  .set({ 'cat_list': allRasterValues})
};

var getUniqueValues=function(raster)
/** 
 * @description get unique value from raster
 * @param {image} raster: ee.Image()
 * @return {array}
 */
{
  var unValDic=ee.Image(raster).reduceRegion(
  {
    reducer  : ee.Reducer.frequencyHistogram(), 
    scale    : raster.projection().nominalScale(), 
    tileScale: 4,
    maxPixels: 1e12
  } );
  var unVals = ee.Dictionary(unValDic.values().get(0)).keys();
  var unVals2= unVals.map(function(x) { return ee.Number.parse(x)});
  return(unVals2).filter(ee.Filter.gt('item', 0));
};


var checkIfTimeSeries= function(veg){
  if ( veg.name() !== "Image" || ee.List(ee.Image(veg).bandNames()).size() >1 ) 
  {
    print ("Input image is a time series, converting!");
    var check = ee.ImageCollection(veg).size();
    return check
  } else {
    var check = 0;
    return check;
  }
  return ee.Number(check);
};

var timeSeriesToImage = function(veg)
{
  var dateList   = ee.List(ee.ImageCollection(veg).aggregate_array("date"));
  var dateListString  = dateList.map(function(date) { return ee.Date(date).format("YYMMMdd")});
  var img        = ee.ImageCollection(veg).toBands();
  
  return img.rename(dateListString).set({'dates': dateList});
};

//DEPRECATED
var setImagesToSameProjection = function(landscape, veg) 
/** @description:  both inputs must be ee.Image
 *  @param { ee.Image } landscape: landscape Units map
 *  @param { ee.Image } veg: veg time series image e.g. ndvi
 *  @return: ee.Image
 */
{
  var newCrs = landscape.projection().crs();
  var newTransform = landscape.projection().transform();
  var newScale = ee.Algorithms.If(landscape.projection().nominalScale() >= veg.projection().nominalScale(), 
                                landscape.projection().nominalScale(), 
                                veg.projection().nominalScale()) ;
  return ee.List([
                landscape.setDefaultProjection(newCrs, newTransform, newScale), 
                veg.setDefaultProjection(newCrs, newTransform, newScale)
                ]);
};


//Classification below
// calculate percentiles
  var makePercentileArray = function(maskedVeg) 
  {
    var percentiles = maskedVeg.reduceRegion(
      {
        reducer   : ee.Reducer.percentile([0,10,90,100]), 
        geometry  : maskedVeg.geometry(), 
        scale     : 30, 
        bestEffort: true
      })
      .map(function(k,v) {return v});
      return percentiles;
  };

var formatPercentiles=function(percentiles)
  {
    var pKeys = ee.List(percentiles.keys());
    var perc0 = percentiles.values(
                    pKeys.filter(ee.Filter.stringEndsWith('item', 'p0'))
                    );
    var perc10  = percentiles.values(
                    pKeys.filter(ee.Filter.stringEndsWith('item','p10'))
                    );
    var perc90  = percentiles.values(
                    pKeys.filter(ee.Filter.stringEndsWith('item','p90'))
                    );
    var perc100 = percentiles.values(
                    pKeys.filter(ee.Filter.stringEndsWith('item','p100'))
                    );
    return ee.Dictionary.fromLists(['0','10', '90', '100'], [perc0, perc10, perc90, perc100])   
};

var model1090=function(percentiles)
  /** @description model uses 10 percentile and 
   * ..90th to classify very degraded and potential
   */ 
{
  var tVeryDeg = percentiles.get('10');
  var tPot     = ee.Number(percentiles.get('90'));
  var tHealthy = ee.Number(tPot).subtract(ee.Number(tVeryDeg)).divide(2).add(ee.Number(tVeryDeg));
  return ee.List([tVeryDeg, tHealthy, tPot]);
};

var calcThresholdValues= function(percentiles, tsCheck, model)
  /**Actual classification of images per landscape unit
   * @param {function} model: the model chosen to determine classes default is model1090
   * ..defined above
 */
{
  model = model1090; // in the future here we will choose which model to use
  var singleTimeStepPerc = ee.Array(percentiles.values())
                                    .transpose()
                                    .toList();
  var thresh=ee.Algorithms.If(tsCheck,
        singleTimeStepPerc.map(function(list)
        {
          var dic = ee.Dictionary.fromLists(percentiles.keys(), list);
          return model(dic);
        }),
        model1090(percentiles)
  );
  // print('threshold', thresh, ee.Array(thresh).transpose())
  return ee.Array(thresh).transpose().toList();
}; 




//DEPRECATED

var MultiModel1090=function(percentiles)
  /** @description model uses 10 percentile and 
   * ..90th to classify very degraded and potential
   */ 
  {
    var tVeryDeg = ee.List(percentiles.get('10'));
    var tPot     = ee.List(percentiles.get('90'))
    
    var joinedList = ee.List.sequence(0, tVeryDeg.length().subtract(1), 1)
                              .map(function(pos) {
                                return ee.List([tPot.get(pos), tVeryDeg.get(pos)])
    })
    var tHealthy = joinedList.map(function(ls){
      return ee.Number.expression(
          {
        expression: '(a - b)/2+b', 
        vars      : ee.Dictionary({
                  'a'       : ee.Number.parse(ee.List(ls).get(0)), 
                  'b'       : ee.Number.parse(ee.List(ls).get(1))
          
        })
          });
    });
    print('thealthy', joinedList, tHealthy);
      
    return ee.List([tVeryDeg, tHealthy, tPot]);
  }
    
var createDegImage= function(image, thresholdList)
{
    var degImg=ee.Image.constant(1)         
                        .add(image.gte(ee.Image.constant(ee.List(thresholdList).get(0))))
                        .add(image.gte(ee.Image.constant(ee.List(thresholdList).get(1))))
                        .add(image.gte(ee.Image.constant(ee.List(thresholdList).get(2))));
    return degImg;
};

var bandsToCollection = function(image){
  var collection = ee.ImageCollection.fromImages(ee.Image(image).bandNames().map(function(bandName){
    return image.select(ee.String(bandName))
                .rename('prodClass')
                .set({'date': ee.Date.parse('YYMMMdd', ee.String(bandName))});
  }));
  return collection;
};
