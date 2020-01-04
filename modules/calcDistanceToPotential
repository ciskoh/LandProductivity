// /** module to calculate distance to potential of selected areas
// * needs a long term productivityMap (values only 1-4)
// * a landscape map (values 100-999)
// * a vegetation time series e.g. NDVI
// * a feature or geometry,
// * time in years 
// */
 
 //------------------------INPUT & PARAMETERS----------------------------------
// calcEquivalentAreas?
// 
//-------------------CODE
exports.doc = "module to calculate Distance to potential for vegetation Time Series"+
"\n First function : "+
"\n           prepDistanceToPotential(ls, ltProd, vegTs)"+
"\n takes as input: "+
"\n a landscape Map (integer single band image )"+
"\n a long term productivity map (float single band image) amde with createProductivity module (reduced to Image with mode)"+
"\n a time series of vegetation ( float 2 band imageCollection) with dates"+
"\n outputs:  "+
"\n a multiband image with each band corresponding to a timepoint"+
"\n \n Second function : "+
"\n         calcDistanceToPotential(distanceToPotential, geom)"+
"\n takes as input: "+
"\n distance to Potential (multiband image) created with the function above"+
"\n geometry (polygon geometry or feature) with the area of interest"+
"\n output a feature with properties two lists, one for the area of interest (input geometry), one for the comparable average"+
"\n\n CAUTION: prepDistanceToPotential output cannot be stored as asset, some properties would be lost";


exports.prepDistanceToPotential= function(ls, ltProd, vegTs)

{
  
  //Input preparation
  var aoiGeom  = aoiGeom || ltProd.geometry();
  // calculate order of images
  var veg = ee.ImageCollection(addIdPropIfNeeded(vegTs));
  print('newVeg', veg)
  
  var vegImg = timeSeriesToImage(veg.select(0));
  var vegLen = vegImg.bandNames().size();
  
  var refAreas = ltProd.eq(ee.Image.constant(4));
  
  var lsValueList = getUniqueValues(ls);

    
  // start of cycle
  var distPotList = lsValueList.map(function(lsValue) 
  {
    var lsMask        = ls.eq(ee.Image.constant(lsValue)); 
    var maskedVegProd = vegImg.updateMask(lsMask).updateMask(refAreas);
    
    var refValue = maskedVegProd.reduceRegion(
      {
        reducer  : ee.Reducer.mean(), 
        geometry : aoiGeom, 
        scale    : 30, 
        maxPixels: 10e10, 
        tileScale: 2
        }).values();
  // print("ref value", refValue);
  
  //Avoid null values in reference
    var refValue =  ee.List(removeNullValues(refValue));
  // print("ref value", refValue);
    var checkValidValues = ee.Number(refValue.reduce(ee.Reducer.sum())).gt(0);
// print('check', checkValidValues);
    var distToPot = ee.Algorithms.If(                                   // distance to potential map
                            checkValidValues,
                            createDistToPotentialMap(lsMask, vegImg, refValue),
                            ee.Image.constant(ee.List.repeat(0, vegLen))
                            )
    var refValueNoNulls = refValue
    var avgValues = ee.Algorithms.If
                        (                                   //to add refValue as property
                            checkValidValues,
                            ee.Image(distToPot).reduceRegion(           // add landscape AVG value as property
                          {
                              reducer : ee.Reducer.mean(),
                             geometry : aoiGeom, 
                                scale : 30,
                            maxPixels : 10e10, 
                            tileScale : 4 
                          }),
                          ee.Dictionary.fromLists(ee.List(vegImg.bandNames()), ee.List.repeat(0, vegLen))
                        );
// print('avgValues', avgValues, avgValues.name() );
// print(ee.Dictionary(avgValues).values());
    var avgValueNoNulls = ee.List(removeNullValues(ee.Dictionary(avgValues).values()));
// print(avgValueNoNulls, ee.Dictionary.fromLists(ee.Dictionary(avgValues).keys(), avgValueNoNulls));
    
    return ee.Image(distToPot)
            .selfMask()
            .rename(vegImg.bandNames())
            .set(
              {
          'ls'       : ee.Number(lsValue),
          'refValues': refValueNoNulls,
          'avgDist'  : avgValueNoNulls
              });
  });
  
  var distPotColl     = ee.ImageCollection(distPotList);
  // print("finished cycle", distPotColl);
  //get Properties from images to add to final multiband image
  var allRefValues    = distPotColl.aggregate_array('refValues');
  var refArray        = ee.Array(allRefValues).transpose();
  // print('allRefValues', allRefValues, refArray);
  
  var allAvgValues    = distPotColl.aggregate_array('avgDist');
  // var arrayVals = ee.List(allAvgValues).map(function(dic) 
  // {
  //         return ee.Dictionary(dic).values();
  // });
  var avgDic = ee.Dictionary.fromLists(
                        lsValueList.map(function(x) { return ee.String(x) }), 
                        allAvgValues
                        );
  // print("arrayVals", avgDic);
  
  var distPotentialImg= ee.ImageCollection(distPotList).mosaic();
  
  return distPotentialImg.set(
            {
              'class4'    : refArray.toList(),
              'landscape' : ls,
              'ltProd'    : ltProd,
              'avgValueLs': avgDic,
              'dateList'  : ee.List(vegTs.aggregate_array('date')).map(function(x) {return ee.Date(x).millis()})
            });
};




// ---------------------------- calcDistanceToPotential --------------------------------------------------

exports.calcDistanceToPotential = function (distanceToPotential, geom)
/** Average array can be a dictionary of dictionaries or a 3d array made with .prepDistanceToPotential()
*
*/
{
  var area = geom;
  var aoiGeom=  aoiGeom || distanceToPotential.geometry();
  var ls = ee.Image(distanceToPotential.get('landscape'));
  
  // get weights from landscape
  var  clippedLsValues = ee.Dictionary(ls.reduceRegion(
  {
    reducer    : ee.Reducer.frequencyHistogram(), 
    geometry   : area, 
    scale      : ls.projection().nominalScale(),
    //bestEffort : true,
    maxPixels  : 10e10
  }).values().get(0));
  
//   print('clipped deg', clippedLsValues);
  
  var TotCount = ee.Number(clippedLsValues.values().reduce(ee.Reducer.sum())).round();
  
  var relWeights=clippedLsValues.map(function(k, v) { return ee.Number(v).round().divide(TotCount)});
  var relWeights2=ee.Dictionary.fromLists(relWeights.keys(),removeNullValues(ee.Dictionary(relWeights).values()));

  // print('real weights', relWeights, relWeights2, relWeights.values().reduce(ee.Reducer.sum()));
  // calc weighted avg value for time series
  var avgDic = ee.Dictionary(distanceToPotential.get('avgValueLs'));
// print('avgDic', avgDic);
 //check for missing values in avgDic
 var avgDicChek =avgDic.keys().containsAll(relWeights.keys())
 var str= ee.Algorithms.If(avgDicChek, "all ok with values","missing values")
// print(str, relWeights.keys(), avgDic.keys());
 
  var weightedValues = relWeights.keys().map(function(lsValue)
  {
        var lsValue   = ee.String(lsValue);
        var avgValues = ee.Dictionary(avgDic).get(lsValue); //TODO: Problem with null values here
        var weight    = ee.Number(relWeights.get(lsValue));
        var wValues   = ee.Array(avgValues).multiply(weight);
        return wValues.toList();
  });
  
  // print('weightedValues', weightedValues, weightedValues.length(), ee.Array(weightedValues).length());
  
  var avgComparableValues = ee.Array(weightedValues).reduce(
          {
                  reducer: ee.Reducer.sum(), 
                  axes   : ee.List([0])
          }).toList().get(0);
  print("avgComparableValues", avgComparableValues )
  
  
  // distance To potential Values per Area
  
  // Reduce region to get averages
  var aoiDist= distanceToPotential.reduceRegion(
  {
    reducer    : ee.Reducer.mean(), 
    geometry   : area, 
    scale      : 30,
    bestEffort : true,
    maxPixels  : 10e12
  }).values();
  
  print("aoiDist", aoiDist)
  //turn null values into 0s
  
  var aoiDist2 = ee.List.sequence(0, aoiDist.size().subtract(1), 1).map(function(x)
  {
    var refVal   = ee.Number(aoiDist.get(x));
    var refCheck = ee.List([refVal]).reduce(ee.Reducer.sum());
    return ee.Algorithms.If(
              refCheck, 
              ee.Number(aoiDist.get(x)),
              0.00);
  });
  
        return ee.Feature(null, {"areaDist": aoiDist2, 'avgDist': avgComparableValues, 'dateList': distanceToPotential.get('dateList')})
  
  
return ee.FeatureCollection(finalFeatureColl);
};
  

//------------------------------FUNCTIONS----------------------------

 var addIdPropIfNeeded = function(collection)
 {
  
    var checkIfIdPropExists= ee.Number(collection.aggregate_count_distinct('id')).gt(1)
  
    return ee.Algorithms.If(
            checkIfIdPropExists,
            collection,
            addIdProp(collection)
            );
 }
  
var addIdProp= function(collection) 
{
  var collAsList=collection.toList(10000)
  var newColl = collAsList.map(function(img)
  {
    var img=ee.Image(img)
    var id = ee.Number(collAsList.indexOf(img))
    var newImg = img.set({ 'id' : id })
    return newImg
  })
  return ee.ImageCollection.fromImages(newColl)
}  
  
var timeSeriesToImage = function(ts)
{
  var dateList   = ee.List(ee.ImageCollection(ts).aggregate_array('date'));
  var dateListString  = dateList.map(function(date) { return ee.Date(date).format("GYYMMdd")});
  var img        = ee.ImageCollection(ts).toBands();
  
  return img.rename(dateListString).set({'dates': dateList});
};
  
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
    tileScale: 2,
    maxPixels: 1e12
  } );
  var unVals = ee.Dictionary(unValDic.values().get(0)).keys();
  var unVals2= unVals.map(function(x) { return ee.Number.parse(x)});
  return(unVals2).filter(ee.Filter.gt('item', 0));
};


   var createDistToPotentialMap = function(lsMask, vegImg, refValue)
    {
    // print( 'ref value is ', refValue, ee.List(refValue));
      
      var refImage= lsMask.multiply(ee.Image.constant(refValue)).selfMask();
    
      var distToPot=vegImg.divide(refImage).multiply(ee.Image.constant(100));
    
    // print('distanceToPotentialImage', distToPot);
    // Map.addLayer(distToPot.select(0), {min:0, max:100, palette:['blue', 'yellow']}, 'distance To Potential');
    
    return distToPot;
    };
    
var getAvgValuesPerClass = function(ltProd, distPotentialImg, aoiGeom)
  {
  var mask1 = ltProd.eq(ee.Image.constant(1));
  var mask2 = ltProd.eq(ee.Image.constant(2));
  var mask3 = ltProd.eq(ee.Image.constant(3));
  
  var maskList=ee.List([mask1, mask2, mask3]);
  
  var averageCatValues = maskList.map(function(mask) 
  {
    var averageCatValues = distPotentialImg.mask(mask).reduceRegion(
      {
        reducer  : ee.Reducer.mean(),
        geometry : aoiGeom, 
        scale    : 30, 
        maxPixels: 10e08, 
        tileScale: 4
      })
      .values().get(0);
      
    return averageCatValues;
  });
  return (averageCatValues)
  };

var bandsToCollection = function(image){
  var collection = ee.ImageCollection.fromImages(ee.Image(image).bandNames().map(function(bandName){
    return image.select(ee.String(bandName))
                .rename('prodClass')
                .set({'date': ee.Date.parse('GYYMMdd', ee.String(bandName))});
  }));
  return collection;
};

var removeNullValues = function(valueList){
  var check = ee.Number(ee.List(valueList).reduce(ee.Reducer.sum())).gt(0);
  
  var size  = ee.List(valueList).size();
  var seq   = ee.List.sequence(0, ee.Number(ee.List(valueList).size()).subtract(1), 1);
  var noNullValues = ee.Algorithms.If(
                                  check, 
                                  seq.map(function(pos) 
                                      {
                                        var val =ee.List(valueList).get(pos);
                                        var check=ee.Number(ee.List([val]).reduce(ee.Reducer.sum())).gt(0);
                                        return ee.Algorithms.If(check, val, 0);
                                      }),
                                  ee.List.repeat(0,size)
                                  );
  return noNullValues;
};