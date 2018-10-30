from math import hypot
import sys

from PyQt4.QtCore import QFileInfo, QVariant

from qgis.core import NULL, QgsField, QgsSpatialIndex
from qgis.gui import QgsMapCanvasLayer     #, QgsMapToolPan, QgsMapToolZoom

import shared
from shared import *
from layers import createVector, ReadVectorLayer, readRasterLayer, ReadAndMergeVectorLayers
from utils import centroidOfContainingDEMCell, displayOS


#======================================================================================================================
#
# Create the GIS output layers, reads in the GIS input layers, and sets everything up ready for the simulation
#
#======================================================================================================================
def setUpSimulation(): 
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
   
   n = len(shared.fieldsWithFlow)
   if n > 0:
      printStr += "Flow from fields "
      for m in range(n):
         printStr += shared.fieldsWithFlow[m]
         if m < n-1:
            printStr += ", "            
   else:
      printStr += "Flow from all fields"      
   shared.fpOut.write(printStr + "\n")   

   if shared.considerFieldObservations:
      printStr = "Field observations considered\n"
   else:
      printStr = "Field observations not considered\n"      
   shared.fpOut.write(printStr)   

   if shared.fillBlindPits:
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

   shared.fpOut.write("DEM resolution (metres) : " + str(shared.resolutionOfDEM) + "\n")
   shared.fpOut.write("Distance to search (metres) : " + str(shared.searchDist) + "\n\n")


   # OK, now do some initialization
   shared.distDiag = hypot(shared.resolutionOfDEM, shared.resolutionOfDEM)
   
   # May add other landscape elements (e.g. woodland) later
   #shared.rasterPathCodes = OS_MASTERMAP_PATH
   
   # Create a Point vector layer to store the flow marker points
   initString = "Point?crs="
   initString += shared.externalCRS
   title = FLOW_MARKERS
   fieldDefn = [QgsField(OUTPUT_TYPE, QVariant.String, "char", 10), QgsField(OUTPUT_FIELD_CODE, QVariant.String, "char", 10), QgsField(OUTPUT_ELEVATION, QVariant.Double, "float", 12, 4)]
   shared.outFlowMarkerPointLayer = createVector(initString, title, fieldDefn, shared.outFileFlowMarkerPointsStyle, shared.outFileFlowMarkerPointsTransparency)
   if shared.outFlowMarkerPointLayer == -1:
      return (-1, -1)
   
   # Now create a MultiLineString vector layer to store the flow path
   initString = "MultiLineString?crs="
   initString += shared.externalCRS
   title = FLOW_LINES
   fieldDefn = [QgsField(OUTPUT_TYPE, QVariant.String, "char", 10), QgsField(OUTPUT_FIELD_CODE, QVariant.String, "char", 10), QgsField(OUTPUT_ELEVATION, QVariant.Double, "float", 12, 4)]
   shared.outFlowLineLayer = createVector(initString, title, fieldDefn, shared.outFileFlowLinesStyle, shared.outFileFlowLinesTransparency)
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

      # Create a spatial index
      index = QgsSpatialIndex(layer.getFeatures())
      shared.vectorInputIndex.append(index)

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
      index = QgsSpatialIndex(layer.getFeatures())   
      shared.vectorInputIndex.append(index)
   
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
         shared.rasterFileTransparency.insert(0, shared.rasterFileTransparency.pop(i))
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
   
   canvasLayers = []
   canvasLayersCategory = []
   for layer in allLayers:         
      canvasLayers.append(QgsMapCanvasLayer(layer[0]))
      canvasLayersCategory.append(layer[1])
      
      layerExtent = layer[0].extent()
      if not layerExtent.isEmpty():         
         xMin = min(xMin, layerExtent.xMinimum())
         yMin = min(yMin, layerExtent.yMinimum())
         xMax = max(xMax, layerExtent.xMaximum())
         yMax = max(yMax, layerExtent.yMaximum())         

   #for i in range(len(listLayers)):
      #print i, listLayers[i].crs().authid()
      
   #for i in range(len(canvasLayers)):
      #shared.fpOut.write(i, canvasLayers[i].isVisible())
   
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
   
   shared.fpOut.write("FIELD OBSERVATIONS\n\n")
   
   if shared.considerFieldObservations:
      # The user-supplied OS coords for field observations are unlikely to be the coords of the raster DEM centroids. This is a problem for flow routing, after flow has passed through a landscape element which has an associated field observation. So we need to modify the 'To' coord of all field observations: check all field observations and adjust if necessary
      #shared.fpOut.write("\n" + shared.dividerLen * shared.dividerChar + "\n\n")
      
      for obs in range(len(shared.fieldObservationFlowTo)):
         centroidFromPoint = centroidOfContainingDEMCell(shared.fieldObservationFlowFrom[obs].x(), shared.fieldObservationFlowFrom[obs].y())  
         if not shared.fieldObservationFlowTo[obs]:
            # 'To' location is blank
            if centroidFromPoint != shared.fieldObservationFlowFrom[obs]:         
               shared.fpOut.write("Field observation " + str(obs) + " '" + shared.fieldObservationCategory[obs] + "' '" + shared.fieldObservationBehaviour[obs] + "' '" + shared.fieldObservationDescription[obs] + "' changed to align with DEM centroids:\n\tinflow location (was " + displayOS(shared.fieldObservationFlowFrom[obs].x(), shared.fieldObservationFlowFrom[obs].y(), False) + ", now " + displayOS(centroidFromPoint.x(), centroidFromPoint.y(), False) + "\n\toutflow location is unknown\n")
            
            shared.fieldObservationFlowFrom[obs] = centroidFromPoint
            
         else:
            # We have a 'To' location, so check it
            centroidToPoint = centroidOfContainingDEMCell(shared.fieldObservationFlowTo[obs].x(), shared.fieldObservationFlowTo[obs].y())  
         
            #if centroidFromPoint == centroidToPoint:
               #if not (shared.fieldObservationCategory[obs] == FIELD_OBS_CATEGORY_STREAM and shared.fieldObservationBehaviour[obs] == FIELD_OBS_BEHAVIOUR_ENTER):
                  #printStr = "ERROR: after adjustment, we have identical inflow and outflow locations " + displayOS(centroidFromPoint.x(), centroidFromPoint.y()) + " for field observation '" +  shared.fieldObservationCategory[obs] + "' '" + shared.fieldObservationBehaviour[obs] + "' '" + shared.fieldObservationDescription[obs] + "'. The adjusted inflow location is " + displayOS(shared.fieldObservationFlowFrom[obs].x(), shared.fieldObservationFlowFrom[obs].y()) + " and the adjusted outflow location is " + displayOS(shared.fieldObservationFlowTo[obs].x(), shared.fieldObservationFlowTo[obs].y()) + "\n*** Please change inflow and/or outflow coordinates\n"               
                  #shared.fpOut.write(printStr)
                  #print(printStr)
                     
                  #return (-1, -1)
            
            changedFrom = False
            changedTo = False
            if centroidFromPoint != shared.fieldObservationFlowFrom[obs]:
               changedFrom = True
            if centroidToPoint != shared.fieldObservationFlowTo[obs]:
               changedTo = True
               
            if changedFrom or changedTo:
               printStr = "Field observation " + str(obs) + " '" + shared.fieldObservationCategory[obs] + "' '" + shared.fieldObservationBehaviour[obs] + "' '" + shared.fieldObservationDescription[obs] + "' changed to align with DEM centroids:\n"
               
               if changedFrom:
                  printStr += "\tinflow location was "
                  printStr += displayOS(shared.fieldObservationFlowFrom[obs].x(), shared.fieldObservationFlowFrom[obs].y(), False)
                  printStr += ", now "
                  printStr += displayOS(centroidFromPoint.x(), centroidFromPoint.y(), False)
                  printStr += "\n"
                  
               if changedTo:
                  printStr += "\toutflow location was "
                  printStr += displayOS(shared.fieldObservationFlowTo[obs].x(), shared.fieldObservationFlowTo[obs].y(), False)
                  printStr += ", now " + displayOS(centroidToPoint.x(), centroidToPoint.y(), False)
                  printStr += "\n"
                  
               shared.fpOut.write(printStr)   
         
            shared.fieldObservationFlowFrom[obs] = centroidFromPoint
            shared.fieldObservationFlowTo[obs] = centroidToPoint      
               
      # Print out the revised field observations
      shared.fpOut.write("\nREVISED FIELD OBSERVATIONS\n\n")
      
      for obs in range(len(shared.fieldObservationFlowTo)):
         printStr = str(obs) + ": '" + shared.fieldObservationCategory[obs] + "' '" + shared.fieldObservationBehaviour[obs] + "' '" + shared.fieldObservationDescription[obs] + "' from " + displayOS(shared.fieldObservationFlowFrom[obs].x(), shared.fieldObservationFlowFrom[obs].y(), False)
         
         if shared.fieldObservationFlowTo[obs]:
            printStr += (" to " + displayOS(shared.fieldObservationFlowTo[obs].x(), shared.fieldObservationFlowTo[obs].y(), False)) 
            
         printStr += "\n"
         shared.fpOut.write(printStr)
               
   #shared.fpOut.write("\n" + shared.dividerLen * shared.dividerChar + "\n\n")
   
   return canvasLayers, canvasLayersCategory
#======================================================================================================================
