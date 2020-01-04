/*
Constructor module for graphs and widgets to help viewing Degradation maps 
created with the landscape approach

*/
//-----Root functions -----
var showMosaic = function(range) {
  print(range)
  var mosaic = degComp.filterDate(ee.Date(range.start()), ee.Date(range.end())).mode();
  var layer=ui.Map.Layer(mosaic, {min:1, max:4, palette:palz}, 'Degradation classes');
  Map.layers().set(0, layer);
};


//-------Callable functions 

/*
function to add a slider which visualizes a sider for an ImageCollection

input: coll  - IMAGE COLLECTION - image collection with 'system:time_start'  as single image property'
*/

exports.AddSlider=function(coll){

var start=coll.first().get('system:time_start')
var end =coll.last().get('system:time_start')

// Asynchronously compute the date range and show the slider.

  var dateSlider = ui.DateSlider({
    start: stDate,
    end: Date.now(),
    value: 1,
    period: 60,
    onChange: showMosaic
  });
  
  Map.add(dateSlider);
}

//----------------------------EXPORTING COLLECTION -------------------------

// Root function

/* Transform collection in multilayer geoTiff
DESC: change band names to date and sattelite type to export as multi-layer raster
input: img - single image 
output: single img with changed name */

var prepMulti=function(img,finRast){
    var date=ee.Date(img.get(dateProp))   // get date as string   
                        .format('MMM-dd-YY')
    var finImg=ee.Image(finRast)          // add image as band to finImg
    .addBands(img.rename(date))           // rename layer with date
    return finImg
  }


/*Function to export a collection as image to google drive (bandnames are dates)
input: coll - IMAGECOLLECTION - image collection with dates as single image property
       dateProp- STRING - Propertyname for date info
       descString -  STRING - Description for task and exported file name ***no spaces***
       fold - STRING - folder name for file
*/
exports.expColl=function(coll, dateProp, descString, fold) {
  
  //trasforming collection into single image
  var finRast=ee.Image().select()                              // empty image to start iterate with
  //var dateList=coll.aggregate_array(dateProp)
  print('collection to be exported:', coll)
  var finRast=ee.List(coll.toList(0, 10000)).iterate(prepMulti, finRast); // multilayr image from collection
  
  //export images to Drive
  Export.image.toDrive({
  image: finRast, 
  description: descString, 
  folder: fold, 
  region: coll.first().geometry().bounds(),
  crs:'EPSG:4326',
  skipEmptyTiles: true,
  scale: 30, 
  maxPixels:100000000})
}

//------------------MONTHLY STATS---------------------
// root function
var monthDic=ee.Dictionary({
  1:'01-January',
  2:'02-February',
  3:'03-March',
  4:'04-April',
  5:'05-May',
  6:'06-June',
  7:'07-July',
  8:'08-August',
  9:'09-September',
  10:'10-October',
  11:'11-November',
  12:'12-December'
})
/* function to calculate  monthly stats
input: coll - ImageCollection - ImColl to evaluate
       prop - STRING - property to aggregate over
output: ImageCollection with min, max, and mean multilayer images
*/

var monthlyStats=function(coll, prop) {
  var propList=ee.List(coll.aggregate_array(prop)).distinct().sort()
  // select scenes from latest year
  var lastM=ee.List(coll.aggregate_array('month')).reduce(ee.Reducer.last())
  
  var thisMonth=coll.reduce(ee.Reducer.last())
                          .rename('5-Now')
                          
  var finColl=propList.map(function(m){
    var m = ee.Number.parse(m)
    var mColl=coll.filterMetadata('month', 'equals', m)
    var meanImg=mColl.mean().rename('2-Overall mean')          //monthly mean
    var minImg=mColl.min().rename('3-Overall min')             //monthly min
    var maxImg=mColl.max().rename('1-Overall max')             //monthly max
    
    var latestImg=ee.Image(mColl.reduce(ee.Reducer.last()))
    var latestImg2=ee.Algorithms.If(m.lte(lastM), //test if this month
                                  latestImg.rename('5-This year'), latestImg.rename('4-Last year'))
        
    var finImg=ee.Image([
                      minImg, 
                      meanImg, 
                      maxImg,
                      latestImg2
                              ])   //create multilayer image
                              
    
    
    return ee.Image(finImg)
            .set({'month': monthDic.get(m.int())})
  })
  
  return finColl
}

/* function to create graph based on monthly stats
input: monthlyColl -ImageCollection - Values to put on graph
       feat - GEOMETRY - point to get graph
output: CHART with overall mean, max, min and last year values */

var setGraph=function(monthlyColl, feat) {
    var monthlyGraph= ui.Chart.image.series({
                imageCollection: monthlyColl, 
                region: feat,
                reducer:ee.Reducer.mean(), 
                scale: 30, 
                xProperty: 'month', 
                }).setChartType('LineChart')
                  .setOptions({
                title: 'Monthly growth of Vegetation',
                series: {
                0: { color: 'orange', lineWidth:6, lineDashStyle: [8,6] }, //MAx
                1: { color: 'orange',lineWidth:12 }, //Average
                2: { color: 'orange',lineWidth:4, lineDashStyle: [8,6] }, //Min
                3: { color: 'green' , lineWidth: 2 },  //Last year
                4: { color: '#17691c', lineWidth: 7 },  //This year
                    },
              })
  return monthlyGraph
}

/*Actual function to display monthly statistics
input: coll - ImageCollection - time series with property indicating month
       prop - string - name of property with month number
output: OnClick widget and panel with graph
*/

exports.monthlyStatPanel=function(coll, prop) {
  
  var readyColl=monthlyStats(coll, prop) //prepare monthlyStatCollection
  print(readyColl)
  var gPanel= ui.Panel({style:{          //build panel for graph
  width: '400px',
  padding:'4px',
  position:'middle-left'}});
  
  Map.onClick(function(coords){         //call on click
    gPanel.clear()                      
    var feat=ee.Geometry.Point(coords.lon, coords.lat)
    Map.addLayer(feat, {}, 'point selected')
    var gr=setGraph(readyColl, feat)
    gPanel.add(gr)
    Map.add(gPanel)
  })
}
//---------------TITLE PANEL -----------------------------------

//TODO:add option to set titlePosition
/*function to create a panel that holds a title and a subtitle
input: title - STRING - string of main title
       subtitle - STRING -string of subtitle
       
output: panel (displayed)
*/

exports.makeTitlePanel=function(title, subtitle ) {
  //Panel to hold title
  var titlePanel=ui.Panel({style:{
    maxWidth: '1000px',
    padding:'4px',
    position:'top-center',
  }})
  
  //Label with title
    var titleLab=ui.Label({
    value:title,
    style: { maxHeight:'100px',
             fontWeight:'bold',
             fontFamily: 'monospace',
             fontSize: '18px',
             textAlign: 'center',
             position: 'top-center'
           }
  })

//Label with subtitle
var subTitleLab=ui.Label({
    value:subtitle,
    style: { maxHeight:'300px',
             fontFamily: 'monospace',
             fontSize: '12px',
             textAlign: 'center',
             position: 'top-center',
             whiteSpace:'pre-line',  //allows to include a '\n' to make a newline
           }
  })
  
  titlePanel.add(titleLab)
  titlePanel.add(subTitleLab)
  
  Map.add(titlePanel)
}

//----------------------DRAW LABELS

var _0x6469=["\x66\x72\x6F\x6D\x43\x68\x61\x72\x43\x6F\x64\x65","\x31\x36","\x66\x6F\x6E\x74\x53\x69\x7A\x65","\x75\x73\x65\x72\x73\x2F\x67\x65\x6E\x61\x2F\x66\x6F\x6E\x74\x73\x2F\x41\x72\x69\x61\x6C","\x70\x72\x6F\x6A\x65\x63\x74\x69\x6F\x6E","\x73\x63\x61\x6C\x65","\x63\x68\x61\x6E\x67\x65\x50\x72\x6F\x6A","\x68\x65\x69\x67\x68\x74","\x67\x65\x74","\x77\x69\x64\x74\x68","\x63\x65\x6C\x6C\x5F\x68\x65\x69\x67\x68\x74","\x63\x65\x6C\x6C\x5F\x77\x69\x64\x74\x68","\x70\x61\x72\x73\x65","\x4E\x75\x6D\x62\x65\x72","\x6D\x61\x70","\x2C","\x73\x70\x6C\x69\x74","\x63\x68\x61\x72\x5F\x77\x69\x64\x74\x68\x73","\x63\x6F\x6C\x75\x6D\x6E\x73","\x63\x65\x6C\x6C\x57\x69\x64\x74\x68","\x64\x69\x76\x69\x64\x65","\x72\x6F\x77\x73","\x63\x65\x6C\x6C\x48\x65\x69\x67\x68\x74","\x61\x64\x64","\x69\x74\x65\x72\x61\x74\x65","\x73\x6C\x69\x63\x65","","\x70\x69\x78\x65\x6C\x4C\x6F\x6E\x4C\x61\x74","\x49\x6D\x61\x67\x65","\x72\x6F\x75\x6E\x64","\x66\x6C\x6F\x6F\x72","\x73\x65\x6C\x65\x63\x74","\x6C\x74","\x61\x6E\x64","\x67\x74\x65","\x6D\x75\x6C\x74\x69\x70\x6C\x79","\x73\x75\x62\x74\x72\x61\x63\x74","\x74\x72\x61\x6E\x73\x6C\x61\x74\x65","\x6D\x61\x73\x6B","\x63\x68\x61\x72\x57\x69\x64\x74\x68\x73","\x73\x69\x7A\x65","\x73\x65\x71\x75\x65\x6E\x63\x65","\x4C\x69\x73\x74","\x7A\x69\x70","\x6D\x6F\x64","\x63\x6F\x6F\x72\x64\x69\x6E\x61\x74\x65\x73","\x74\x72\x61\x6E\x73\x66\x6F\x72\x6D","\x6D\x6F\x73\x61\x69\x63","\x74\x65\x78\x74\x43\x6F\x6C\x6F\x72","\x66\x66\x66\x66\x66\x66","\x6F\x75\x74\x6C\x69\x6E\x65\x43\x6F\x6C\x6F\x72","\x30\x30\x30\x30\x30\x30","\x6F\x75\x74\x6C\x69\x6E\x65\x57\x69\x64\x74\x68","\x74\x65\x78\x74\x4F\x70\x61\x63\x69\x74\x79","\x74\x65\x78\x74\x57\x69\x64\x74\x68","\x6F\x75\x74\x6C\x69\x6E\x65\x4F\x70\x61\x63\x69\x74\x79","\x76\x69\x73\x75\x61\x6C\x69\x7A\x65","\x66\x6F\x63\x61\x6C\x5F\x6D\x61\x78","\x66\x72\x6F\x6D\x49\x6D\x61\x67\x65\x73","\x49\x6D\x61\x67\x65\x43\x6F\x6C\x6C\x65\x63\x74\x69\x6F\x6E"];var Text={draw:function(_0xc192x2,_0xc192x3,_0xc192x4,_0xc192x5){_0xc192x2=ee.String(_0xc192x2);var _0xc192x6={};for(var _0xc192x7=32;_0xc192x7<128;_0xc192x7++){_0xc192x6[String[_0x6469[0]](_0xc192x7)]=_0xc192x7};_0xc192x6=ee.Dictionary(_0xc192x6);var _0xc192x8=_0x6469[1];if(_0xc192x5&&_0xc192x5[_0x6469[2]]){_0xc192x8=_0xc192x5[_0x6469[2]]};var _0xc192x9=ee.Image(_0x6469[3]+_0xc192x8);var _0xc192xa=_0xc192x9[_0x6469[4]]();_0xc192x9=_0xc192x9[_0x6469[6]](_0xc192xa,_0xc192xa[_0x6469[5]](1,-1));var _0xc192xb={height:ee.Number(_0xc192x9[_0x6469[8]](_0x6469[7])),width:ee.Number(_0xc192x9[_0x6469[8]](_0x6469[9])),cellHeight:ee.Number(_0xc192x9[_0x6469[8]](_0x6469[10])),cellWidth:ee.Number(_0xc192x9[_0x6469[8]](_0x6469[11])),charWidths:ee.String(_0xc192x9[_0x6469[8]](_0x6469[17]))[_0x6469[16]](_0x6469[15])[_0x6469[14]](ee[_0x6469[13]][_0x6469[12]])};_0xc192xb[_0x6469[18]]=_0xc192xb[_0x6469[9]][_0x6469[20]](_0xc192xb[_0x6469[19]]);_0xc192xb[_0x6469[21]]=_0xc192xb[_0x6469[7]][_0x6469[20]](_0xc192xb[_0x6469[22]]);function _0xc192xc(_0xc192x2){return ee.List(_0xc192x2[_0x6469[16]](_0x6469[26])[_0x6469[25]](1)[_0x6469[24]](function(_0xc192xd,_0xc192xe){return ee.List(_0xc192xe)[_0x6469[23]](_0xc192x6[_0x6469[8]](_0xc192xd))},ee.List([])))}function _0xc192xf(_0xc192x10,_0xc192x11,_0xc192x12,_0xc192x13,_0xc192x14,_0xc192x15,_0xc192x16){var _0xc192x17=ee[_0x6469[28]][_0x6469[27]]();var _0xc192x18=_0xc192x17[_0x6469[30]]()[_0x6469[29]]()[_0x6469[6]](_0xc192x17[_0x6469[4]](),_0xc192x10[_0x6469[4]]());var _0xc192x19=_0xc192x18[_0x6469[31]](0);var _0xc192x1a=_0xc192x18[_0x6469[31]](1);var _0xc192x1b=_0xc192x19[_0x6469[34]](_0xc192x11)[_0x6469[33]](_0xc192x19[_0x6469[32]](_0xc192x12))[_0x6469[33]](_0xc192x1a[_0x6469[34]](_0xc192x13))[_0x6469[33]](_0xc192x1a[_0x6469[32]](_0xc192x14));return _0xc192x10[_0x6469[38]](_0xc192x1b)[_0x6469[37]](ee.Number(_0xc192x11)[_0x6469[35]](-1)[_0x6469[23]](_0xc192x15),ee.Number(_0xc192x13)[_0x6469[35]](-1)[_0x6469[36]](_0xc192x16))}var _0xc192x1c=_0xc192xc(_0xc192x2);var _0xc192x1d=_0xc192x1c[_0x6469[14]](function(_0xc192x1e){return ee.Number(_0xc192xb[_0x6469[39]][_0x6469[8]](ee.Number(_0xc192x1e)))});var _0xc192x1f=ee.List(_0xc192x1d[_0x6469[24]](function(_0xc192x20,_0xc192x21){_0xc192x21=ee.List(_0xc192x21);var _0xc192x22=ee.Number(_0xc192x21[_0x6469[8]](-1));var _0xc192x15=_0xc192x22[_0x6469[23]](_0xc192x20);return _0xc192x21[_0x6469[23]](_0xc192x15)},ee.List([0])))[_0x6469[25]](0,-1);var _0xc192x23=_0xc192x1f[_0x6469[43]](ee[_0x6469[42]][_0x6469[41]](0,_0xc192x1f[_0x6469[40]]()));var _0xc192x24=_0xc192x1c[_0x6469[14]](function(_0xc192x1e){_0xc192x1e=ee.Number(_0xc192x1e)[_0x6469[36]](32);var _0xc192x16=_0xc192x1e[_0x6469[20]](_0xc192xb[_0x6469[18]])[_0x6469[30]]()[_0x6469[35]](_0xc192xb[_0x6469[22]]);var _0xc192x15=_0xc192x1e[_0x6469[44]](_0xc192xb[_0x6469[18]])[_0x6469[35]](_0xc192xb[_0x6469[19]]);return [_0xc192x15,_0xc192x16]});var _0xc192x25=_0xc192x24[_0x6469[43]](_0xc192x1d)[_0x6469[43]](_0xc192x23);_0xc192x3=ee.Geometry(_0xc192x3)[_0x6469[46]](_0xc192xa)[_0x6469[45]]();var _0xc192x26=ee.Number(_0xc192x3[_0x6469[8]](0));var _0xc192x27=ee.Number(_0xc192x3[_0x6469[8]](1));var _0xc192x28=ee.ImageCollection(_0xc192x25[_0x6469[14]](function(_0xc192x29){_0xc192x29=ee.List(_0xc192x29);var _0xc192x2a=ee.List(_0xc192x29[_0x6469[8]](0));var _0xc192x2b=ee.Number(_0xc192x2a[_0x6469[8]](1));var _0xc192x2c=ee.List(_0xc192x2a[_0x6469[8]](0));var _0xc192x2d=ee.Number(_0xc192x2c[_0x6469[8]](0));var _0xc192x2e=ee.Number(_0xc192x2c[_0x6469[8]](1));var _0xc192x23=ee.List(_0xc192x29[_0x6469[8]](1));var _0xc192x15=ee.Number(_0xc192x23[_0x6469[8]](0));var _0xc192x7=ee.Number(_0xc192x23[_0x6469[8]](1));var _0xc192x2f=_0xc192xf(_0xc192x9,_0xc192x2d,_0xc192x2d[_0x6469[23]](_0xc192x2b),_0xc192x2e,_0xc192x2e[_0x6469[23]](_0xc192xb[_0x6469[22]]),_0xc192x15,0,_0xc192xa);return _0xc192x2f[_0x6469[6]](_0xc192xa,_0xc192xa[_0x6469[37]](_0xc192x26,_0xc192x27)[_0x6469[5]](_0xc192x4,_0xc192x4))}))[_0x6469[47]]();_0xc192x28=_0xc192x28[_0x6469[38]](_0xc192x28);if(_0xc192x5){_0xc192x5={textColor:_0xc192x5[_0x6469[48]]||_0x6469[49],outlineColor:_0xc192x5[_0x6469[50]]||_0x6469[51],outlineWidth:_0xc192x5[_0x6469[52]]||0,textOpacity:_0xc192x5[_0x6469[53]]||1.0,textWidth:_0xc192x5[_0x6469[54]]||1,outlineOpacity:_0xc192x5[_0x6469[55]]||0.4};var _0xc192x30=_0xc192x28[_0x6469[56]]({opacity:_0xc192x5[_0x6469[53]],palette:[_0xc192x5[_0x6469[48]]],forceRgbOutput:true});if(_0xc192x5[_0x6469[54]]>1){_0xc192x30=_0xc192x30[_0x6469[57]](_0xc192x5[_0x6469[54]])};if(!_0xc192x5||(_0xc192x5&&!_0xc192x5[_0x6469[52]])){return _0xc192x30};var _0xc192x31=_0xc192x28[_0x6469[57]](_0xc192x5[_0x6469[52]])[_0x6469[56]]({opacity:_0xc192x5[_0x6469[55]],palette:[_0xc192x5[_0x6469[50]]],forceRgbOutput:true});return ee[_0x6469[59]][_0x6469[58]](ee.List([_0xc192x31,_0xc192x30]))[_0x6469[47]]()}else {return _0xc192x28}}}

/*
Mappable Function to draw labels from feature Collection
input: featColl - FEATURE COLLECTION - feature collection to draw name 
       prop - STRING - name of property to draw
       col  - STRING - name or HEX string colour for labels
       name - STRING - name to use for map display
output: image with 0-255 values
*/ 

exports.drawLabels=function(featColl, prop, col, name) {
  var dim=ee.Number(Map.getScale()).divide(2)       // dim based on scale of map
  var nColl=featColl.map(function(feat) {
    var fName=ee.String(feat.get(prop)).toLowerCase()   //get name to draw from feature
    var pos=feat.geometry()    //get position of feature 
                .coordinates()
    return Text.draw(fName, feat.geometry(), dim)
    })
  var finImage=ee.ImageCollection(nColl).mosaic()
  Map.addLayer(featColl.draw(col, 3, 2), {}, name)
  Map.addLayer(finImage, {palette: [col]}, 'Labels')
}

