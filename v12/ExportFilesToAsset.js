/**** Start of imports. If edited, may not auto-convert in the playground. ****/
var ls4 = ee.Image("users/matteojriva/Midelt/outputLandscapeMap4");
/***** End of imports. If edited, may not auto-convert in the playground. *****/
var lsModule = require('users/matteojriva/LandscapeProductivity:modules/createLandscapeMap');
var vegModule = require('users/matteojriva/LandscapeProductivity:modules/getVegTimeSeries');
var prodModule = require('users/matteojriva/LandscapeProductivity:modules/createProductivityMap');
var distModule = require('users/matteojriva/LandscapeProductivity:modules/calcDistanceToPotential');
 
// ---------------------- createLandscapeMap---------------------------
//clipped good image: 
var goodInputImage = ee.Image("users/matteojriva/Midelt/landCoverMap092019");
Map.addLayer(goodInputImage.randomVisualizer());
var unwantedCategories=[6,7];

var prepareLsForExport = function(landCover, unwantedCategories){
  
  var outputLs = lsModule.createLandscapeMap(goodInputImage, unwantedCategories, 20000);
  //change properties to jSon string
  var serOutput= ee.Image(outputLs.select(0))
  .setMulti(
    {
    date_created: ee.Date(outputLs.get('date_created')).millis(),
    });
    
  return serOutput;  
};


// print("landscape map", serOutput);
// var newStr= ee.String(serOutput.get('categories'));
// var newStr2= ee.String(outputLs.get('aoiMask').serialize());
// print(newStr2);
// var newDic=ee.Deserializer.fromJSON(newStr2.getInfo());
// print("deserialised property", newDic);
// Map.addLayer(outputLs.randomVisualizer(),{}, 'ls display');
Map.addLayer(ls4,{}, 'landscapeMap', 0);

Export.image.toAsset({
  image:lsModule.createLandscapeMap(goodInputImage, unwantedCategories, "2000"), 
  description: 'landscapeMap',
  assetId: 'LandscapeProductivity_test/outputLandscapeMap4',
  scale: 10,
  maxPixels: 10000000000000,
  });     
  print("landscape  exported to asset:  okay?")

// --------------- get NdviTimeSeries-----------------------------------------
// var outputVeg = vegModule.getVegTimeSeries(ls4.geometry(), "2010-01-01", 30);
// // var firstImage=ee.ImageCollection(outputVeg).first()
// // var serOut = firstImage.set({date: ee.Date(firstImage.get('date')).millis()})
// print('veg time series', outputVeg)
// Map.addLayer(outputVeg.first(), { min:0, max:1, palette : ['red', 'yellow', 'green']}, 'vegIndex');
// // Export.image.toAsset(
// //   {
// //     image : serOut,
// //     description : 'vegIndex',
// //     assetId: 'LandscapeProductivity_test/outputVegTs',
// //     scale: 30,
// //     maxPixels: 10000000000
  
// //     });

// //-------------------------------ProductivityMap ----------------------------------------
// var outputProd = prodModule.createProductivityMap(ls4, outputVeg)
// print('productivity image Collection', outputProd)
// Map.addLayer(outputProd.mode(), {min: 1, max:4, palette:['red', 'yellow', 'green']}, 'productivityMap')
// Export.image.toAsset(
//   {
//     image : prodModule.createProductivityMap(ls4, outputVeg).mode(),
//     description : 'ProdMap',
//     assetId: 'LandscapeProductivity_test/outputProdMap-10y',
//     scale: 30,
//     maxPixels: 10000000000
//     });

// // //DistanceTOPotential
// // var distPot = distModule.prepDistanceToPotential(outputLs, outputProd.mode(), outputVeg )
