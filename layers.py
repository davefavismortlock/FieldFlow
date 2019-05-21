from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer, QgsDataSourceUri, QgsFeatureRequest, QgsWkbTypes, QgsVectorFileWriter, QgsFeature, QgsGeometry, QgsRectangle, QgsCoordinateReferenceSystem, QgsPoint, QgsField

from PyQt5.QtCore import QFileInfo     #, QVariant

import shared
from shared import OUTPUT_TYPE, OUTPUT_FIELD_CODE, OUTPUT_ELEVATION
from utils import ToSentenceCase, DisplayOS


#======================================================================================================================
#
# Reads a raster layer from a file
#
#======================================================================================================================
def readRasterLayer(i, allBandData):
   # pylint: disable=too-many-locals

   fileInfo = QFileInfo(shared.rasterFileName[i])
   fileBaseName = fileInfo.baseName()

   layer = QgsRasterLayer(shared.rasterFileName[i], fileBaseName)
   if not layer.isValid():
      shared.fpOut.write("Raster layer '" + shared.rasterFileName[i] + "'failed to load")
      return -1

   # Store the title as the first list item
   allBandData.append(shared.rasterFileTitle[i])

   # Get more info
   xSize = layer.width()
   ySize = layer.height()

   cellWidth = layer.rasterUnitsPerPixelX()
   cellHeight = layer.rasterUnitsPerPixelY()

   provider = layer.dataProvider()
   extnt = provider.extent()
   dpi = provider.dpi()

   shared.fpOut.write("Raster layer '" + shared.rasterFileTitle[i] + "' loaded with X, Y resolution = " + str(cellWidth) + ", " + str(cellHeight) + " m\n")
   #shared.fpOut.write(layer.metadata())
   #shared.fpOut.write(layer.rasterType())

   # Store the above as the second list item
   allBandData.append([provider, xSize, ySize, cellWidth, cellHeight, extnt, dpi])

   # Now store the data for each band as a QgsRasterBlock
   nBands = layer.bandCount()
   for band in range(nBands):
      #shared.fpOut.write(layer.bandName(i))

      bandData = provider.block(band, extnt, xSize, ySize)

      # Store as a further list item
      allBandData.append(bandData)

   # Sort out style
   #shared.fpOut.write("Style file " + str(i) + " is " + shared.rasterFileStyle[i])
   if not shared.rasterFileStyle[i]:
      # No style file specified, so try the default style for this layer
      shared.rasterFileStyle[i] = layer.styleURI()
      #shared.fpOut.write("Trying default style file " + shared.rasterFileStyle[i])

      if not layer.loadDefaultStyle():
         shared.fpOut.write("Could not load default style '" + shared.rasterFileStyle[i] + "' for raster layer '" + shared.rasterFileTitle[i] + "'")

   else:
      # A style file was specified, so try to load it
      #shared.fpOut.write("Trying style file " + shared.rasterFileStyle[i])
      if not layer.loadNamedStyle(shared.rasterFileStyle[i]):
         shared.fpOut.write("Could not load style '" + shared.rasterFileStyle[i] + "' for raster layer '" + shared.rasterFileTitle[i] + "'")

   # Set opacity
   layer.renderer().setOpacity(shared.rasterFileOpacity[i])

   # Add this layer to the app's registry
   QgsProject.instance().addMapLayer(layer)

   return layer
#======================================================================================================================


#======================================================================================================================
#
# Reads a vector layer from a file
#
#======================================================================================================================
def ReadVectorLayer(i):
   if shared.vectorFileType[i] == "ogr":
      layer = QgsVectorLayer(shared.vectorFileName[i], shared.vectorFileTitle[i], "ogr")

   elif shared.vectorFileType[i] == "spatialite":
      uri = QgsDataSourceUri()
      uri.setDatabase(shared.vectorFileName[i])

      schema = ''
      geom_column = 'Geometry'
      uri.setDataSource(schema, shared.vectorFileTable[i], geom_column)

      layer = QgsVectorLayer(uri.uri(), shared.vectorFileTitle[i], shared.vectorFileType[i])

   elif shared.vectorFileType[i] == "xyz":
      uri = shared.vectorFileName[i] + "?type=csv&useHeader=No&xField=field_1&yField=field_2&spatialIndex=no&subsetIndex=no&watchFile=no"
      layer = QgsVectorLayer(uri, shared.vectorFileTitle[i], "delimitedtext")

   else:
      shared.fpOut.write("Cannot load vector file of type '" + shared.vectorFileType[i] + "'")
      return -1

   if not layer.isValid():
      shared.fpOut.write("Vector layer '" + shared.vectorFileTitle[i] + "' failed to load")
      return -1

   shared.fpOut.write("Vector layer '" + shared.vectorFileTitle[i] + "' loaded\n")

   # Sort out style
   if not shared.vectorFileStyle[i]:
      shared.vectorFileStyle[i] = layer.styleURI()
      #shared.fpOut.write(shared.vectorFileStyle[i])
      if not layer.loadDefaultStyle():
         shared.fpOut.write("Could not load default style '" + shared.vectorFileStyle[i] + "' for vector layer '" + shared.vectorFileTitle[i] + "'")
   else:
      if not layer.loadNamedStyle(shared.vectorFileStyle[i]):
         shared.fpOut.write("Could not load style '" + shared.vectorFileStyle[i] + "' for vector layer '" + shared.vectorFileTitle[i] + "'")

   # Set opacity
   layer.setOpacity(shared.vectorFileOpacity[i])

   # Add this layer to the app's registry
   QgsProject.instance().addMapLayer(layer)

   return layer
#======================================================================================================================


#======================================================================================================================
#
# Reads multiple vector layers from files and merges them
#
#======================================================================================================================
def ReadAndMergeVectorLayers(vectorLayers):
   # pylint: disable=too-many-locals
   # pylint: disable=too-many-branches
   # pylint: disable=too-many-statements

   category = ""
   feats = []

   for i in vectorLayers:
      if shared.vectorFileType[i] == "ogr":
         thisLayer = QgsVectorLayer(shared.vectorFileName[i], shared.vectorFileTitle[i], "ogr")

      elif shared.vectorFileType[i] == "spatialite":
         uri = QgsDataSourceUri()
         uri.setDatabase(shared.vectorFileName[i])

         schema = ''
         geom_column = 'Geometry'
         uri.setDataSource(schema, shared.vectorFileTable[i], geom_column)

         thisLayer = QgsVectorLayer(uri.uri(), shared.vectorFileTitle[i], shared.vectorFileType[i])

      elif shared.vectorFileType[i] == "xyz":
         uri = shared.vectorFileName[i] + "?type=csv&useHeader=No&xField=field_1&yField=field_2&spatialIndex=no&subsetIndex=no&watchFile=no"
         thisLayer = QgsVectorLayer(uri, shared.vectorFileTitle[i], "delimitedtext")

      else:
         shared.fpOut.write("Cannot load vector file of type '" + shared.vectorFileType[i] + "'")
         return -1, -1

      if not thisLayer.isValid():
         shared.fpOut.write("Vector layer '" + shared.vectorFileTitle[i] + "' failed to load")
         return -1, -1

      shared.fpOut.write("Vector layer '" + shared.vectorFileTitle[i] + "' loaded\n")

      # Copy the features from this layer that are within the displayed extent, to a new list
      extentRectWithBorder = QgsRectangle()
      borderSize = 100
      extentRectWithBorder.setXMinimum(shared.extentRect.xMinimum() - borderSize)
      extentRectWithBorder.setYMinimum(shared.extentRect.yMinimum() - borderSize)
      extentRectWithBorder.setXMaximum(shared.extentRect.xMaximum() + borderSize)
      extentRectWithBorder.setYMaximum(shared.extentRect.yMaximum() + borderSize)

      request = QgsFeatureRequest(extentRectWithBorder)
      features = thisLayer.getFeatures(request)
      #features = thisLayer.getFeatures()

      print("Copying features from vector layer '" + shared.vectorFileTitle[i] + "'")
      feats += features
      #for feat in features:
         #newFeature = QgsFeature()
         #newFeature.setGeometry(feat.geometry())

         #fields = feat.fields()
         #newFeature.setFields(fields)

         #attrs = feat.attributes()
         #newFeature.setAttributes(attrs)

         #feats.append(newFeature)

         ##print(feat)

         ##feats.append(feat)

      category = shared.vectorFileCategory[i]

   # Get the Coordinate Reference System and the list of fields from the last input file
   thisLayerCRS = thisLayer.crs().toWkt()
   thisLayerFieldList = thisLayer.dataProvider().fields().toList()

   # Create the merged layer by checking the geometry type of the input files
   layerGeom = thisLayer.geometryType()
   layerWkb = thisLayer.wkbType()
   isMulti = QgsWkbTypes.isMultiType(layerWkb)
   if layerGeom == QgsWkbTypes.PointGeometry:
      if isMulti:
         mergedLayer = QgsVectorLayer('MultiPoint?crs=' + thisLayerCRS, 'merged', "memory")
      else:
         mergedLayer = QgsVectorLayer('Point?crs=' + thisLayerCRS, 'merged', "memory")

   elif layerGeom == QgsWkbTypes.LineGeometry:
      if isMulti:
         mergedLayer = QgsVectorLayer('MultiLineString?crs=' + thisLayerCRS, 'merged', "memory")
      else:
         mergedLayer = QgsVectorLayer('LineString?crs=' + thisLayerCRS, 'merged', "memory")

   elif layerGeom == QgsWkbTypes.PolygonGeometry:
      if isMulti:
         mergedLayer = QgsVectorLayer('MultiPolygon?crs=' + thisLayerCRS, 'merged', "memory")
      else:
         mergedLayer = QgsVectorLayer('Polygon?crs=' + thisLayerCRS, 'merged', "memory")

   else:
      geomTypeString = QgsWkbTypes.displayString(int(layerWkb))
      errStr = "ERROR: layer type " + geomTypeString + " could not be merged"
      print(errStr)
      shared.fpOut.write(errStr + "\n")
      return -1, -1

   # Is the new (but still empty) merged layer OK?
   if not mergedLayer.isValid():
      titleStr = ""
      for i in vectorLayers:
         titleStr += shared.vectorFileTitle[i]
         if i < len(vectorLayers):
            titleStr += "' '"
      errStr = "ERROR: could not create new vector layer for merge of '" + titleStr + "'"
      print(errStr)
      shared.fpOut.write(errStr + "\n")
      return -1, -1

   # Sort the list of features by identifier
   #for i in range(10):
      #shared.fpOut.write(feats[i].attributes())

   feats.sort(key = lambda feat : feat.attributes()[1])

   #for i in range(10):
      #print("BEFORE MERGE " + str(feats[i].attributes()))
   #print("=================")

   # BODGE
   # This is needed because QGIS 3 handles Boolean layers incorrectly
   #print("*********************")
   #print("*** ORIGINAL: " + str(thisLayerFieldList))
   #for fld in thisLayerFieldList:
      #print(fld.type())
   #print("*********************")

   for fld in thisLayerFieldList:
      fldName = fld.typeName()
      if fldName == "Boolean":
         fld.setTypeName("Integer64")
         fld.setType(4)

   #print("**** CHANGED : " + str(thisLayerFieldList))
   #for fld in thisLayerFieldList:
      #print(fld.type())
   #print("*********************")

   # Add the field attributes to the merged layer
   provider = mergedLayer.dataProvider()
   #print(provider)
   #print("Number of attribute fields = " + str(len(thisLayerFieldList)))
   if not provider.addAttributes(thisLayerFieldList):
      errStr = "ERROR: could not add attributes to merged layer"
      print(errStr)
      shared.fpOut.write(errStr + "\n")
      return -1, -1

   mergedLayer.updateFields()

   flds = mergedLayer.fields()
   #print(flds.names())
   #print("Number of attribute fields = " + str(len(flds.names())))


   if not mergedLayer.startEditing():
      errStr = "ERROR: could not edit merged layer"
      print(errStr)
      shared.fpOut.write(errStr + "\n")
      return -1, -1

   if not provider.addFeatures(feats):
      errStr = "ERROR: could not add features to merged layer"
      print(errStr)
      shared.fpOut.write(errStr + "\n")
      return -1, -1

   mergedLayer.commitChanges()

   #testFeats = mergedLayer.getFeatures()
   #print("testFeats = " + str(list(testFeats)))

   #features = mergedLayer.getFeatures()
   #for feat in features:
      #shared.fpOut.write(str(feat.attributes()))

   #for field in mergedLayer.fields().toList():
      #shared.fpOut.write(str(field.name()))


   # Sort out style
   i = vectorLayers[-1]
   if not shared.vectorFileStyle[i]:
      shared.vectorFileStyle[i] = mergedLayer.styleURI()
      #shared.fpOut.write(shared.vectorFileStyle[i])
      if not mergedLayer.loadDefaultStyle():
         errStr = "ERROR: could not load default style '" + shared.vectorFileStyle[i] + "' for vector layer '" + shared.vectorFileTitle[i] + "'"
         print(errStr)
         shared.fpOut.write(errStr + "\n")
   else:
      if not mergedLayer.loadNamedStyle(shared.vectorFileStyle[i]):
         errStr = "ERROR: could not load style '" + shared.vectorFileStyle[i] + "' for vector layer '" + shared.vectorFileTitle[i] + "'"
         print(errStr)
         shared.fpOut.write(errStr + "\n")

   # Set transparency
   mergedLayer.setOpacity(shared.vectorFileOpacity[i])

   # Add this layer to the app's registry
   QgsProject.instance().addMapLayer(mergedLayer)

   mergedNames = ""
   for i in vectorLayers:
      mergedNames += "'"
      mergedNames += shared.vectorFileTitle[i]
      mergedNames += "' "

   shared.fpOut.write("\tMerged layers " + mergedNames + "\n")
   print("Merged layers " + mergedNames)

   return mergedLayer, category
#======================================================================================================================


#======================================================================================================================
#
# Creates a new vector layer
#
#======================================================================================================================
def createVector(initString, title, fieldDefn, style, opacity):
   layer = QgsVectorLayer(initString, title, "memory")
   if not layer.isValid():
      shared.fpOut.write("Could not create vector layer '" + title + "'")
      return -1

   shared.fpOut.write("Vector layer '" + title + "' created\n")

   # OK now add the fields
   layer.dataProvider().addAttributes(fieldDefn)
   layer.updateFields()

   # Sort out style and opacity
   layer.loadNamedStyle(style)
   layer.setOpacity(opacity)

   # Add this layer to the app's registry
   QgsProject.instance().addMapLayer(layer)

   return layer
#======================================================================================================================


#======================================================================================================================
#
# Writes a vector layer as a shapefile
#
#======================================================================================================================
def WriteVector(layer, fileName, CRS):
   error, errorString  = QgsVectorFileWriter.writeAsVectorFormat(layer, fileName, "UTF-8", driverName = "ESRI Shapefile")
   if error != QgsVectorFileWriter.NoError:
      printStr = "ERROR: could not create '" + fileName + "' '" + errorString + "'\n"
      shared.fpOut.write(printStr)
      print(printStr)

   else:
      shared.fpOut.write("Vector layer '" + fileName + "' saved\n")

   return
#======================================================================================================================


#======================================================================================================================
#
# Adds a point to the flow marker points vector layer
#
#======================================================================================================================
def AddFlowMarkerPoint(thisPoint, desc, fieldCode, elev):
   #print("In AddFlowMarkerPoint " + desc + " " + DisplayOS(thisPoint.x(), thisPoint.y()) + " for field " + str(fieldCode))
   feature = QgsFeature()
   feature.setGeometry(QgsGeometry.fromPointXY(thisPoint))

   fields = shared.outFlowMarkerPointLayer.fields()
   feature.setFields(fields)

   feature[OUTPUT_TYPE] = ToSentenceCase(desc)
   feature[OUTPUT_FIELD_CODE] = fieldCode
   feature[OUTPUT_ELEVATION] = elev

   provider = shared.outFlowMarkerPointLayer.dataProvider()
   if not provider.addFeatures([feature]):
      shared.fpOut.write("Could not add flow marker point (coord = {" + str(thisPoint.x()) + ", " + str(thisPoint.y()) + "}, '" + desc + "', field code = " + fieldCode + ", elev = " + str(elev) + ")")

   return
#======================================================================================================================


#======================================================================================================================
#
# Adds a line to the flow lines vector layer
#
#======================================================================================================================
def AddFlowLine(lineStartPoint, lineEndPoint, desc, fieldCode, elev):
   feature = QgsFeature()
   feature.setGeometry(QgsGeometry.fromPolyline([QgsPoint(lineStartPoint), QgsPoint(lineEndPoint)]))

   fields = shared.outFlowLineLayer.fields()
   feature.setFields(fields)

   feature[OUTPUT_TYPE] = ToSentenceCase(desc)
   feature[OUTPUT_FIELD_CODE] = fieldCode
   feature[OUTPUT_ELEVATION] = elev

   provider = shared.outFlowLineLayer.dataProvider()
   if not provider.addFeatures([feature]):
      shared.fpOut.write("Could not add flow line from {" + str(lineStartPoint.x()) + ", " + str(lineStartPoint.y()) + "} to {" + str(lineEndPoint.x()) + ", " + str(lineEndPoint.y()) + "}, '" + desc + "', field code = " + fieldCode + ", elev = " + str(elev) + ")")

      return

   shared.thisFieldFlowLine.append(lineStartPoint)
   shared.thisFieldFlowLineFieldCode.append(fieldCode)

   return
#======================================================================================================================
