/**** Start of imports. If edited, may not auto-convert in the playground. ****/
var ls = ee.Image("users/matteojriva/LandscapeProductivity_test/outputLandscapeMap3"),
    ltProd = ee.Image("users/matteojriva/RS2RPM/DegTimeS_10YearsMODE"),
    testGeom = /* color: #d63000 */ee.Geometry.Point([-4.803638744693785, 32.59626878507704]),
    protAreas = ee.FeatureCollection("users/matteojriva/Midelt/intervention2409");
/***** End of imports. If edited, may not auto-convert in the playground. *****/

//-------PARAMETERS---------
//import modules

var calcDistModule= require('users/matteojriva/LandscapeProductivity:modules/calcDistanceToPotential')
var graphModule= require('users/matteojriva/LandscapeProductivity:modules/graphicExportConstructors')
var vegModule = require('users/matteojriva/LandscapeProductivity:modules/getVegTimeSeries');
//----Visualisation----
Map.centerObject(ltProd);
Map.addLayer(ltProd, {min:1, max:4, palette:['red', 'yellow', 'green']}, 'Productivité à longue terme (10 ans)')
Map.addLayer(protAreas, {}, "zones d'intervention", 1, 0.5)
//-----------FUNCTIONS--------
var bandsToCollection = function(image)
{
    var collection = ee.ImageCollection.fromImages(ee.Image(image).bandNames().map(function(bandName){
    return image.select(ee.String(bandName))
                .rename('prodClass')
                .set({'system:time_start': ee.Date.parse('GYYMMdd', ee.String(bandName)).millis()});
  }));
  return collection;
};

var plotDistPotentialMonthly=function(coll, geom)
{
  print('geom', geom, ee.Feature(geom).geometry());
  var plot= ui.Chart.image.doySeries(
    {
      imageCollection: coll, 
      region: ee.Feature(geom), 
      scale: 30, 
    });
};

//get info from protected areas
var getAreaInfo = function (geom)
{
  //output is a string
  
    
  var line1 = ee.String("description : ").cat( geom.getString("desc"));
  var line2 = ee.String("commune : ").cat( geom.getString("LO_Commune"));
  var line3 = ee.String("Douar : ").cat( geom.getString("LO_Douar"));
  var line4 = ee.String("intervention : ").cat( geom.getString("GE_TypeInt"));
  var line5 = ee.String("Premiere année d'intervention : ").cat( geom.get("GE_AnInter"));
  var line6 = ee.String("\n Type de sol : ").cat( ee.String(geom.get("BP_Sol")));
  var line7 = ee.String(" Altitude : ").cat( ee.String(geom.get("BP_Altitud")));
  var line8 = ee.String(" Surface : ").cat( ee.String(geom.get("BP_Surface")).cat(""));
  
 print('line 1', geom.getString("desc"),line1)
  var compStr = ee.List([line1, line2, line3, line4, line5, line6, line7, line8 ]).join("\n");
  print(compStr)
  return compStr;
};


// ----Widgets------
// make title
graphModule.makeTitlePanel('Outil de suivi des interventions dans la Zone de Midelt', "Toutes les informations sont issues des satellites LandSat et Sentinel, et élaborées par Dr. Matteo jucker Riva, BFH-HAFL");


var Panel1=ui.Panel({style:{          //build panel for graph
  width: '300px',
  padding:'4px',
  position:'top-left'}});

var title1 = ui.Label(
  {
    value     :"Informations sur la zone sélectionnée",
    style     : {
                fontFamily: 'monospace',
                  fontSize: '12px',
                 textAlign: 'left',
                fontWeight: 'bold',
                  position: 'top-center'
                }
  });
var Panel1Lab=ui.Label(
  {
  value     :"Cliquer sur la carte pour plus d'informations....",
  
  style     : {
          fontFamily: 'monospace',
          fontSize  : '12px',
          textAlign : 'left',
          fontWeight: 'normal',
          position  : 'top-center',
          whiteSpace:'pre-line'  //allows to include a '\n' to make a newline
              }
  });
  
Panel1.add(title1);
Panel1.add(Panel1Lab);
Map.add(Panel1);

var Panel2=ui.Panel({style:{          //build panel for graph
  width: '400px',
  padding:'4px',
  position:'bottom-left'}});
var title2 = ui.Label(
  {
    value     :"Productivité (long terme) dans la zone sélectionnée ",
    style     : {
                fontFamily: 'monospace',
                  fontSize: '12px',
                 textAlign: 'left',
                fontWeight: 'bold',
                  position: 'top-center'
                }
  });
var tempLab2=ui.Label(" Cliquer sur la carte pour plus d'informations....");
Panel2.add(title2);
Panel2.add(tempLab2);
Map.add(Panel2);
  
var Panel3=ui.Panel({style:{          //build panel for graph
  width: '600px',
  padding:'4px',
  position:'top-right'}});
var title3 = ui.Label(
  {
    value     :"Indicateur de gestion (Différence d’avec le Potentiel)",
    style     : {
                fontFamily: 'monospace',
                  fontSize: '12px',
                 textAlign: 'left',
                fontWeight: 'bold',
                  position: 'top-center'
                }
  });
var tempLab3=ui.Label(" Cliquer sur la carte pour plus d'informations....");
Panel3.add(title3);
Panel3.add(tempLab3);
Map.add(Panel3);

//-----------CODE--------------
//build distancetoPotentialMap
var veg2= vegModule.getVegTimeSeries(ls.geometry(), "2013-06-01", 30);
var distImage = calcDistModule.prepDistanceToPotential(ls, ltProd, veg2);
var distColl = ee.ImageCollection(bandsToCollection(distImage));

//onClickFunction 
// panel 1 is information
// panel 2 is degradation
// panel 3 is distance to potential
// panel 4 is dist TO potential by year
Map.onClick(function(coords)
{
  Panel1.remove(Panel1Lab)
  Panel2.remove(Panel2.widgets().get(1))
  Panel3.remove(Panel3.widgets().get(1))
  Panel3.add(ui.Label('Patientez...'))
  
  var pointFromCoords =ee.Geometry.Point(coords.lon, coords.lat);
  var selectFromProtectedAreas=ee.FeatureCollection(protAreas).filterBounds(pointFromCoords);
  var checkIfProtected = selectFromProtectedAreas.size();
  // print("check If protected", checkIfProtected, selectFromProtectedAreas)
  // print('geom', ee.Feature(pointFromCoords.buffer(1000)))
  var geom = ee.Feature(ee.Algorithms.If(checkIfProtected, 
                                    selectFromProtectedAreas.first(), 
                                      ee.Feature(pointFromCoords.buffer(1000))));
  Map.addLayer(ee.Feature(geom), {color: 'red'});
  
  //PANEL 1 INFOs
  var Panel1Str = ee.Algorithms.If(
    checkIfProtected, 
    getAreaInfo(geom),
    "Pas d'informations!  Sélectionnez une zone d'intervention"
  );
  Panel1Str.evaluate(function(val){Panel1Lab.setValue(val)})
  Panel1.add(Panel1Lab);
  print("panel1 updated")
  
  
  // PANEL2 degradation
  var dic = ltProd.reduceRegion(
  {
    reducer: ee.Reducer.frequencyHistogram(), 
    geometry: geom.geometry(),
    scale:30, 
    maxPixels:10e10,
    bestEffort: true,
  }).values().get(0);
  
  var nameList    = ee.List(["1-très peu productive", "2-peu productive", "3-productive", "4-très productive"]);
  var filtNameList=ee.Dictionary(dic).keys().map(function(k) 
  {
    var pos    = ee.Number.parse(k).subtract(1)
    var name   = nameList.get(pos)
    return name
  })
print("PANEL2: ", filtNameList)
  var ls      = ee.Dictionary(dic).rename(ee.Dictionary(dic).keys(), filtNameList , true);
  print("ls", ls)
  var feat    = ee.Feature(geom.geometry(), ls);
  print(feat)
  //Chart building
  var colorList= ee.List(["red", "orange", "#77c700", "green"])
  var filtColorList=ee.Dictionary(dic).keys().map(function(k) 
  {
    var pos    = ee.Number.parse(k).subtract(1)
    var name   = colorList.get(pos)
    return name
  })
  print("color", filtColorList, filtColorList.name())
  var chart2  =ui.Chart.feature.byProperty(feat);
  // print('chart', chart2)
  chart2.setChartType('PieChart');
   chart2.setOptions(
 {
    colors: filtColorList.getInfo(),
    title: "Classification de la productivité à long terme dans la zone sélectionnée",
    pieHole: 0.2,
    legend: { position : 'left'},
    chartArea: {width: '70%', } 
  });
  
  Panel2.add(chart2);
  print("panel 2 updated");
  
  
  //PANEL 3
  // var aTime = ee.Date(Date.Now())
  var distFeat = calcDistModule.calcDistanceToPotential(distImage, geom.geometry());
  var arList= ee.Dictionary(distFeat.get('distToPot'));
  var arValues = ee.Array([distFeat.get("areaDist"), distFeat.get('avgDist')]);
  var chart3 = ui.Chart.array.values(arValues, 1, distFeat.get("dateList"));
  
  chart3.setOptions(
  {
    title     : " ",
    legend    : {position: 'top', alignment : 'start', maxLines:4},
    chartArea : { left:40,top:20},
    hAxis     : { title: 'Date'},
    vAxis     : { title : "% de biomasse", minValue: 0, maxValue: 100, textPosition: 'in'},
    series    : { 
         0         : {labelInLegend: "Zone séléctionnée", color: "red", opacity: 0.5} ,
         1         : {labelInLegend: "moyenne des zones comparables", color:"#91a3d6", pointSize: 2}
    },
    trendlines: {
      0:{ type: 'linear',
      lineWidth: 3,
      opacity: 0.7,
      showR2: true,
      visibleInLegend: false},
      
      1:{ type: 'linear',
      lineWidth: 3,
      opacity: 0.3,
      showR2: true,
      visibleInLegend: false}
    }
  })
  Panel3.add(chart3);
  Panel3.remove(Panel3.widgets().get(1))
  // var bTime=ee.Date(Date.Now())
  
  // print("time for Panel 3 calc", bTime.difference(aTime,'second'))
  // Panel 4
  
  // Panel4.add(plotDistPotentialMonthly(distImage, geom));
  // var chart =ui.Chart.image.doySeriesByYear(
  // {
  //     imageCollection: ee.ImageCollection(distColl), 
  //     region: ee.Feature(geom), 
  //     scale:30 ,
  //     bandName: 'prodClass'
  // });
      

  
});
