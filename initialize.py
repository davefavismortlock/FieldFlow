from math import hypot
import sys

from PyQt5.QtCore import QVariant

from qgis.core import QgsField, QgsSpatialIndex, QgsRectangle, QgsVectorLayer, QgsRasterLayer

import shared
from shared import FLOW_MARKERS, OUTPUT_TYPE, FLOW_LINES, OUTPUT_FIELD_CODE, OUTPUT_ELEVATION, INPUT_FIELD_BOUNDARIES, INPUT_WATER_NETWORK, INPUT_ROAD_NETWORK, INPUT_PATH_NETWORK, INPUT_DIGITAL_ELEVATION_MODEL, INPUT_RASTER_BACKGROUND, OUTPUT_FLOW_MARKERS, OUTPUT_FLOW_LINES
from layers import createVector, ReadVectorLayer, readRasterLayer, ReadAndMergeVectorLayers
from utils import GetCentroidOfContainingDEMCell, DisplayOS


#======================================================================================================================
#
# Create the GIS output layers, reads in the GIS input layers, and sets everything up ready for the simulation
#
#======================================================================================================================
def setUpSimulation():
   # pylint: disable=too-many-locals
   # pylint: disable=too-many-return-statements
   # pylint: disable=too-many-branches
   # pylint: disable=too-many-statements

   # Open the text output file
   shared.fpOut = open(shared.textOutputFile, "w")

   # Hello world!
   printStr = shared.progName + " (" + shared.progVer + ")\n"
   l = len(printStr)
   shared.fpOut.write(printStr)
   print(printStr)

   shared.fpOut.write("-" * l)
   shared.fpOut.write("\n\n")

      # Write to the text ouput file: first show run details
   shared.fpOut.write("RUN DETAILS\n\n")

   printStr = shared.runTitle + "\n" + "Input data read from " + shared.dataInputFile + "\n"

   n = len(shared.sourceFields)
   if n > 0:
      printStr += "Flow from source fields "
      for m in range(n):
         printStr += shared.sourceFields[m]
         if m < n-1:
            printStr += ", "
   else:
      printStr += "Flow from all fields"
   shared.fpOut.write(printStr + "\n")

   if shared.considerLEFlowInteractions:
      printStr = "LE-flow interactions considered\n"
   else:
      printStr = "LE-flow interactions not considered\n"
   shared.fpOut.write(printStr)

   if shared.FillBlindPits:
      printStr = "Blind pits filled\n"
   else:
      printStr = "Blind pits not filled\n"
   shared.fpOut.write(printStr)

   if shared.considerFieldBoundaries:
      printStr = "Field boundaries considered\n"
   else:
      printStr = "Field boundaries not considered\n"
   shared.fpOut.write(printStr)

   if shared.considerRoads:
      printStr = "Roads considered\n"
   else:
      printStr = "Roads not considered\n"
   shared.fpOut.write(printStr)

   if shared.considerTracks:
      printStr = "Paths/tracks considered\n"
   else:
      printStr = "Paths/tracks not considered\n"
   shared.fpOut.write(printStr)

   shared.fpOut.write("DEM resolution = " + str(shared.resolutionOfDEM) + " m\n")
   shared.fpOut.write("Distance to search = " + str(shared.searchDist) + " m\n\n")


   # OK, now do some initialization
   shared.distDiag = hypot(shared.resolutionOfDEM, shared.resolutionOfDEM)

   # Create a Point vector layer to store the flow marker points
   initString = "Point?crs="
   initString += shared.externalCRS
   title = FLOW_MARKERS
   fieldDefn = [QgsField(OUTPUT_TYPE, QVariant.String, "char", 10), QgsField(OUTPUT_FIELD_CODE, QVariant.String, "char", 10), QgsField(OUTPUT_ELEVATION, QVariant.Double, "float", 12, 4)]
   shared.outFlowMarkerPointLayer = createVector(initString, title, fieldDefn, shared.outFileFlowMarkerPointsStyle, shared.outFileFlowMarkerPointsOpacity)
   if shared.outFlowMarkerPointLayer == -1:
      return (-1, -1)

   # Now create a MultiLineString vector layer to store the flow path
   initString = "MultiLineString?crs="
   initString += shared.externalCRS
   title = FLOW_LINES
   fieldDefn = [QgsField(OUTPUT_TYPE, QVariant.String, "char", 10), QgsField(OUTPUT_FIELD_CODE, QVariant.String, "char", 10), QgsField(OUTPUT_ELEVATION, QVariant.Double, "float", 12, 4)]
   shared.outFlowLineLayer = createVector(initString, title, fieldDefn, shared.outFileFlowLinesStyle, shared.outFileFlowLinesOpacity)
   if shared.outFlowLineLayer == -1:
      return (-1, -1)

   # Create an empty spatial index for this layer
   shared.outFlowLineLayerIndex = QgsSpatialIndex()

   # Now go through all input vector files: is there more than one with the same category? If so, we need to merge these
   vectorLayersToMerge = []
   vectorLayersUnmerged = []
   dups = []
   for i in range(len(shared.vectorFileCategory)):
      if i in dups:
         continue

      thisCat = shared.vectorFileCategory[i]
      sharedVectorCats = [i]

      for j in range(len(shared.vectorFileCategory)):
         if j == i or j in dups:
            continue

         if shared.vectorFileCategory[j] == thisCat:
            sharedVectorCats.append(j)
            dups.append(j)

      if len(sharedVectorCats) > 1:
         # We have some vector layers with the same category
         vectorLayersToMerge.append(sharedVectorCats)
      else:
         vectorLayersUnmerged.append(i)

   #shared.fpOut.write(vectorLayersToMerge)
   #shared.fpOut.write(vectorLayersUnmerged)
   #shared.fpOut.write("")

   # Read in and merge the vector layers with duplicated categories
   for i in vectorLayersToMerge:
      layer, category = ReadAndMergeVectorLayers(i)
      if layer == -1:
         return (-1, -1)

      shared.vectorInputLayers.append(layer)
      shared.vectorInputLayersCategory.append(category)

      #feats = layer.getFeatures()
      #n = 0
      #for feat in feats:
         #print("AFTER MERGE " + str(feat.attributes()))
         #n += 1
         #if n == 10:
            #break
      #print("=================")

      # Create a spatial index for each merged vector layer
      index = QgsSpatialIndex(layer)
      shared.vectorInputLayerIndex.append(index)

   #for i in range(len(shared.vectorInputLayers)):
      #fields = shared.vectorInputLayers[i].fields().toList()
      #for field in fields:
         #shared.fpOut.write(i, field.name())
      #shared.fpOut.write(shared.vectorInputLayersCategory)
      #shared.fpOut.write("")

   # Read in the rest of the vector layers
   for i in vectorLayersUnmerged:
      layer = ReadVectorLayer(i)
      if layer == -1:
         return (-1, -1)

      shared.vectorInputLayers.append(layer)
      shared.vectorInputLayersCategory.append(shared.vectorFileCategory[i])

      # Create a spatial index
      index = QgsSpatialIndex(layer)
      shared.vectorInputLayerIndex.append(index)

   #for i in range(len(shared.vectorInputLayers)):
      #fields = shared.vectorInputLayers[i].fields().toList()
      #for field in fields:
         #shared.fpOut.write(i, field.name())
      #shared.fpOut.write(shared.vectorInputLayersCategory)
      #shared.fpOut.write("")

   # Put the raster background files at the front of the list
   for i in range(len(shared.rasterFileName)):
      if shared.rasterFileCategory[i] == INPUT_RASTER_BACKGROUND:
         shared.rasterFileName.insert(0, shared.rasterFileName.pop(i))
         shared.rasterFileTitle.insert(0, shared.rasterFileTitle.pop(i))
         shared.rasterFileStyle.insert(0, shared.rasterFileStyle.pop(i))
         shared.rasterFileOpacity.insert(0, shared.rasterFileOpacity.pop(i))
         shared.rasterFileCategory.insert(0, shared.rasterFileCategory.pop(i))

   # Now read the raster files
   for i in range(len(shared.rasterFileName)):
      rasterData = []
      layer = readRasterLayer(i, rasterData)
      if layer == -1:
         return (-1, -1)

      shared.rasterInputLayers.append(layer)
      shared.rasterInputLayersCategory.append(shared.rasterFileCategory[i])
      shared.rasterInputData.append(rasterData)

   shared.fpOut.write("")

   #for ind in shared.vectorInputLayerIndex:
      #print(ind)

   # OK, check what we have read in
   haveFieldBoundaries = False
   haveWaterNetwork = False
   haveRoadNetwork = False
   havePathNetwork = False
   haveDEM = False
   shared.haveRasterBackground = False    # Optional

   for layer in range(len(shared.vectorInputLayersCategory)):
      if shared.vectorInputLayersCategory[layer] == INPUT_FIELD_BOUNDARIES:
         haveFieldBoundaries = True
         continue

      if shared.vectorInputLayersCategory[layer] == INPUT_WATER_NETWORK:
         haveWaterNetwork = True
         continue

      if shared.vectorInputLayersCategory[layer] == INPUT_ROAD_NETWORK:
         haveRoadNetwork = True
         continue

      if shared.vectorInputLayersCategory[layer] == INPUT_PATH_NETWORK:
         havePathNetwork = True
         continue

   for layer in range(len(shared.rasterInputLayersCategory)):
      if shared.rasterInputLayersCategory[layer] == INPUT_DIGITAL_ELEVATION_MODEL:
         haveDEM = True
         continue

      if shared.rasterInputLayersCategory[layer] == INPUT_RASTER_BACKGROUND:
         shared.haveRasterBackground = True
         continue

   # Now make sure that we have all we need
   if not haveFieldBoundaries:
      printStr = "ERROR: did not read in a vector layer for field boundaries\n"
      shared.fpOut.write(printStr)
      print(printStr)

      return (-1, -1)

   if not haveWaterNetwork:
      printStr = "ERROR: did not read in a vector layer for the water network\n"
      shared.fpOut.write(printStr)
      print(printStr)

      return (-1, -1)

   if not haveRoadNetwork:
      printStr = "ERROR: did not read in a vector layer for the road network\n"
      shared.fpOut.write(printStr)
      print(printStr)

      return (-1, -1)

   if not havePathNetwork:
      printStr = "ERROR: did not read in a vector layer for the path network\n"
      shared.fpOut.write(printStr)
      print(printStr)

      return (-1, -1)

   if not haveDEM:
      printStr = "ERROR: did not read in a raster layer for the DEM\n"
      shared.fpOut.write(printStr)
      print(printStr)

      return (-1, -1)

   # All OK so far, so do some more initialization
   xMin = yMin = sys.float_info.max
   xMax = yMax = sys.float_info.min

   allLayers = [[shared.outFlowMarkerPointLayer, OUTPUT_FLOW_MARKERS], [shared.outFlowLineLayer, OUTPUT_FLOW_LINES]]
   for i in range(len(shared.vectorInputLayers)):
      allLayers.append([shared.vectorInputLayers[i], shared.vectorInputLayersCategory[i]])
   for i in range(len(shared.rasterInputLayers)):
      allLayers.append([shared.rasterInputLayers[i], shared.rasterInputLayersCategory[i]])

   mapLayers = []
   mapLayersCategory = []
   for layer in allLayers:
      mapLayers.append(layer[0])
      mapLayersCategory.append(layer[1])

      layerExtent = layer[0].extent()
      if not layerExtent.isEmpty():
         xMin = min(xMin, layerExtent.xMinimum())
         yMin = min(yMin, layerExtent.yMinimum())
         xMax = max(xMax, layerExtent.xMaximum())
         yMax = max(yMax, layerExtent.yMaximum())

   #for i in range(len(listLayers)):
      #print i, listLayers[i].crs().authid()

   #for i in range(len(mapLayers)):
      #shared.fpOut.write(i, mapLayers[i].isVisible())

   # Set up the extent of the main window
   if shared.extentRect.isEmpty():
      shared.extentRect = QgsRectangle(xMin, yMin, xMax, yMax)

   # Some more initialization
   for layerNum in range(len(shared.rasterInputLayersCategory)):
      if shared.rasterInputLayersCategory[layerNum] == INPUT_DIGITAL_ELEVATION_MODEL:
         # OK, this is our raster elevation data
         shared.cellWidthDEM = shared.rasterInputData[layerNum][1][3]
         shared.cellHeightDEM = shared.rasterInputData[layerNum][1][4]
         extent = shared.rasterInputData[layerNum][1][5]
         shared.xMinExtentDEM = extent.xMinimum()
         shared.yMinExtentDEM = extent.yMinimum()

         break

   shared.fpOut.write("\n" + shared.dividerLen * shared.dividerChar + "\n\n")

   if shared.considerLEFlowInteractions:
      for obs in range(len(shared.LEFlowInteractionFlowTo)):
         centroidFromPoint = shared.LEFlowInteractionFlowFrom[obs]
         if shared.LEFlowInteractionFlowTo[obs]:
            centroidToPoint = shared.LEFlowInteractionFlowTo[obs]

            #shared.LEFlowInteractionFlowFrom[obs] = centroidFromPoint
            #shared.LEFlowInteractionFlowTo[obs] = centroidToPoint

      # Print out the revised LE-flow interactions
      shared.fpOut.write("FIELD OBSERVATIONS\n\n")

      for obs in range(len(shared.LEFlowInteractionFlowTo)):
         printStr = str(obs+1) + ": '" + shared.fieldObservationBehaviour[obs] + " " + shared.fieldObservationCategory[obs] + ", " + shared.fieldObservationDescription[obs] + "' from " + DisplayOS(shared.LEFlowInteractionFlowFrom[obs].x(), shared.LEFlowInteractionFlowFrom[obs].y())

         if shared.LEFlowInteractionFlowTo[obs]:
            printStr += (" to " + DisplayOS(shared.LEFlowInteractionFlowTo[obs].x(), shared.LEFlowInteractionFlowTo[obs].y()))

         printStr += "\n"
         shared.fpOut.write(printStr)

   #shared.fpOut.write("\n" + shared.dividerLen * shared.dividerChar + "\n\n")

   return mapLayers, mapLayersCategory
#======================================================================================================================
