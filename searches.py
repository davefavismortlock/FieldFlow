import sys
from math import sqrt

from qgis.core import NULL, QgsGeometry, QgsFeatureRequest
from qgis.gui import QgsMapCanvasLayer    #, QgsMapToolPan, QgsMapToolZoom

import shared
from shared import *
from utils import getRasterElev, displayOS
from layers import addFlowMarkerPoint, addFlowLine


#======================================================================================================================
#
# Finds the adjacent grid cell with the steepest downhill gradient, to which this field's flow has not already travelled
#
#======================================================================================================================
def FindSteepestAdjacent(thisPoint, thisElev, geomPolygon = -1):   
   newAdjX = -1
   newAdjY = -1
   newAdjElev = -1
   
   maxGradient = 0
   
   #shared.fpOut.write(n, displayOS(thisPoint.x(), thisPoint.y()), thisElev)
   
   # N
   adjX = thisPoint.x()
   adjY = thisPoint.y() + shared.resolutionOfDEM
   adjElev = getRasterElev(adjX, adjY)

   #shared.fpOut.write(str(displayOS(adjX, adjY)) + " elev = " + str(adjElev) + "\n")
   
   gradient = (thisElev - adjElev) / shared.resolutionOfDEM
   #shared.fpOut.write("N " + str(gradient) + "\n")
   
   if gradient > maxGradient:
      adjPoint = QgsPoint(adjX, adjY)
      if adjPoint not in shared.thisFieldFlowLine:
         if geomPolygon == -1 or (geomPolygon != -1 and geomPolygon.contains(adjPoint)): 
            maxGradient = gradient
            newAdjX = adjX
            newAdjY = adjY
            newAdjElev = adjElev
            #shared.fpOut.write("N maxGradient = ", maxGradient, " to {", newAdjX, ", ", newAdjY, "}")
      
   # NE
   adjX = thisPoint.x() + shared.resolutionOfDEM
   adjY = thisPoint.y() + shared.resolutionOfDEM
   adjElev = getRasterElev(adjX, adjY)

   #shared.fpOut.write(str(displayOS(adjX, adjY)) + " elev = " + str(adjElev) + "\n")
   
   gradient = (thisElev  - adjElev) / shared.distDiag
   #shared.fpOut.write("NE " + str(gradient) + "\n")
   
   if gradient > maxGradient:
      adjPoint = QgsPoint(adjX, adjY)
      if adjPoint not in shared.thisFieldFlowLine:
         if geomPolygon == -1 or (geomPolygon != -1 and geomPolygon.contains(adjPoint)): 
            maxGradient = gradient
            newAdjX = adjX
            newAdjY = adjY
            newAdjElev = adjElev
            #shared.fpOut.write("NE maxGradient = ", maxGradient, " to {", newAdjX, ", ", newAdjY, "}")

   # E
   adjX = thisPoint.x() + shared.resolutionOfDEM
   adjY = thisPoint.y() 
   adjElev = getRasterElev(adjX, adjY)

   #shared.fpOut.write(str(displayOS(adjX, adjY)) + " elev = " + str(adjElev) + "\n")
   
   gradient = (thisElev  - adjElev) / shared.resolutionOfDEM
   #shared.fpOut.write("E " + str(gradient) + "\n")
   
   if gradient > maxGradient:
      adjPoint = QgsPoint(adjX, adjY)
      if adjPoint not in shared.thisFieldFlowLine:
         if geomPolygon == -1 or (geomPolygon != -1 and geomPolygon.contains(adjPoint)): 
            maxGradient = gradient
            newAdjX = adjX
            newAdjY = adjY
            newAdjElev = adjElev
            #shared.fpOut.write("E maxGradient = ", maxGradient, " to {", newAdjX, ", ", newAdjY, "}")

   # SE
   adjX = thisPoint.x() + shared.resolutionOfDEM
   adjY = thisPoint.y() - shared.resolutionOfDEM
   adjElev = getRasterElev(adjX, adjY)

   #shared.fpOut.write(str(displayOS(adjX, adjY)) + " elev = " + str(adjElev) + "\n")
   
   gradient = (thisElev  - adjElev) / shared.distDiag
   #shared.fpOut.write("SE " + str(gradient) + "\n")
   
   if gradient > maxGradient:
      adjPoint = QgsPoint(adjX, adjY)
      if adjPoint not in shared.thisFieldFlowLine:
         if geomPolygon == -1 or (geomPolygon != -1 and geomPolygon.contains(adjPoint)): 
            maxGradient = gradient
            newAdjX = adjX
            newAdjY = adjY
            newAdjElev = adjElev
            #shared.fpOut.write("SE maxGradient = ", maxGradient, " to {", newAdjX, ", ", newAdjY, "}")

   # S
   adjX = thisPoint.x()
   adjY = thisPoint.y() - shared.resolutionOfDEM
   adjElev = getRasterElev(adjX, adjY)

   #shared.fpOut.write(str(displayOS(adjX, adjY)) + " elev = " + str(adjElev) + "\n")
   
   gradient = (thisElev  - adjElev) / shared.resolutionOfDEM
   #shared.fpOut.write("S " + str(gradient) + "\n")
   
   if gradient > maxGradient:
      adjPoint = QgsPoint(adjX, adjY)
      if adjPoint not in shared.thisFieldFlowLine:
         if geomPolygon == -1 or (geomPolygon != -1 and geomPolygon.contains(adjPoint)): 
            maxGradient = gradient
            newAdjX = adjX
            newAdjY = adjY
            newAdjElev = adjElev
            #shared.fpOut.write("S maxGradient = ", maxGradient, " to {", newAdjX, ", ", newAdjY, "}")

   # SW
   adjX = thisPoint.x() - shared.resolutionOfDEM
   adjY = thisPoint.y() - shared.resolutionOfDEM
   adjElev = getRasterElev(adjX, adjY)

   #shared.fpOut.write(str(displayOS(adjX, adjY)) + " elev = " + str(adjElev) + "\n")
   
   gradient = (thisElev  - adjElev) / shared.distDiag
   #shared.fpOut.write("SW " + str(gradient) + "\n")
   
   if gradient > maxGradient:
      adjPoint = QgsPoint(adjX, adjY)
      if adjPoint not in shared.thisFieldFlowLine:
         if geomPolygon == -1 or (geomPolygon != -1 and geomPolygon.contains(adjPoint)): 
            maxGradient = gradient
            newAdjX = adjX
            newAdjY = adjY
            newAdjElev = adjElev
            #shared.fpOut.write("SW maxGradient = ", maxGradient, " to {", newAdjX, ", ", newAdjY, "}")

   # W
   adjX = thisPoint.x() - shared.resolutionOfDEM
   adjY = thisPoint.y()
   adjElev = getRasterElev(adjX, adjY)

   #shared.fpOut.write(str(displayOS(adjX, adjY)) + " elev = " + str(adjElev) + "\n")
   
   gradient = (thisElev  - adjElev) / shared.resolutionOfDEM
   #shared.fpOut.write("W " + str(gradient) + "\n")
   
   if gradient > maxGradient:
      adjPoint = QgsPoint(adjX, adjY)
      if adjPoint not in shared.thisFieldFlowLine:
         if geomPolygon == -1 or (geomPolygon != -1 and geomPolygon.contains(adjPoint)): 
            maxGradient = gradient
            newAdjX = adjX
            newAdjY = adjY
            newAdjElev = adjElev      
            #shared.fpOut.write("W maxGradient = ", maxGradient, " to {", newAdjX, ", ", newAdjY, "}")

   # NW
   adjX = thisPoint.x() - shared.resolutionOfDEM
   adjY = thisPoint.y() + shared.resolutionOfDEM
   adjElev = getRasterElev(adjX, adjY)

   #shared.fpOut.write(str(displayOS(adjX, adjY)) + " elev = " + str(adjElev) + "\n")
   
   gradient = (thisElev  - adjElev) / shared.distDiag
   #shared.fpOut.write("NW " + str(gradient) + "\n")
   
   if gradient > maxGradient:
      adjPoint = QgsPoint(adjX, adjY)
      if adjPoint not in shared.thisFieldFlowLine:
         if geomPolygon == -1 or (geomPolygon != -1 and geomPolygon.contains(adjPoint)): 
            maxGradient = gradient
            newAdjX = adjX
            newAdjY = adjY
            newAdjElev = adjElev
            #shared.fpOut.write("New maxGradient = " + str(maxGradient) + " to " + displayOS(newAdjX, newAdjY) + "\n")
      
   return QgsPoint(newAdjX, newAdjY), newAdjElev
#======================================================================================================================
   

#======================================================================================================================
#
# Is there another flow line nearby?
#
#======================================================================================================================
def FindNearbyFlowLine(thisPoint):  
   #shared.fpOut.write("Entered FindNearbyFlowLine() at point " + displayOS(thisPoint.x(), thisPoint.y()) + "\n")
   layerNum = -1
   geomThisPoint = QgsGeometry.fromPoint(thisPoint)
   
   # TODO make this a user setting
   numberToSearchFor = 3
   
   # Now search for the nearest flow line segments
   nearestIDs = shared.outFlowLineLayerIndex.nearestNeighbor(thisPoint, numberToSearchFor) 
   
   # For the first flowline, there are no pre-existing flowlines
   if len(nearestIDs) == 0:
      #print("No flowlines")
      return -1, -1

   # OK we have some flowlines
   request = QgsFeatureRequest().setFilterFids(nearestIDs)
   features = shared.outFlowLineLayer.getFeatures(request) 
   
   distToPoint = []         
   for flowLineSeg in features:
      geom = flowLineSeg.geometry()
      #print("Geom: " + str(geom.wkbType()))
      #line = geom.asPolyline()
      #print("For point " + displayOS(thisPoint.x(), thisPoint.y()) + ", nearby line segment is from ")
      #for point in line:
         #print(displayOS(point.x(), point.y()))
      
      # Is this flow line segment close enough?
      geomSeg = flowLineSeg.geometry()
      nearPoint = geomSeg.nearestPoint(geomThisPoint)
      distanceToSeg = geomThisPoint.distance(nearPoint)
      flowLineSegID = flowLineSeg.id()
      #shared.fpOut.write("flowLineSegID = " + str(flowLineSegID) + " distanceToSeg = " + str(distanceToSeg) + "\n")
      
      if distanceToSeg > shared.searchDist:
         # Too far away so forget about this flow line segment
         continue

      # Is OK, so save the flow line segment feature, the nearest point, and the distance
      distToPoint.append([flowLineSeg, nearPoint.asPoint(), distanceToSeg])
   
   # Did we any find suitable flow line segments?
   if len(distToPoint) == 0:
      # Nope
      #print("Leaving loop")
      return -1, -1
   
   # OK we have some suitable flow line segments, sort the list of stream segments, shortest distance first         
   distToPoint.sort(key = lambda distPoint: distPoint[2])
   
   #for n in range(len(distToPoint)):
      #shared.fpOut.write("\tAfter sorting: " + str(n) + " " + str(distToPoint[n][0].id()) + " " + displayOS(distToPoint[n][1].x(), distToPoint[n][1].y()) + " " + str(distToPoint[n][2]) + " m")

   featIDTried = []
   for n in range(len(distToPoint)):
      # Go through this list of flow line segments
      feature = distToPoint[n][0]
      featID = feature.id()
      
      if featID not in featIDTried:
         #shared.fpOut.write("Trying feature ID " + str(featID) + "\n")
         featIDTried.append(featID)
         
         geomFeat = feature.geometry()
         linePoints = geomFeat.asPolyline()
         nPoints = len(linePoints)

         # OK, the nearest point is an approximation: it is not necessarily a point in the line. So get the actual point in the line which is closest
         nearPoint, numNearpoint, beforeNearpoint, afterNearpoint, sqrDist = geomFeat.closestVertex(distToPoint[n][1])
         
         shared.fpOut.write("At " + displayOS(distToPoint[n][1].x(), distToPoint[n][1].y()) + ", flow line stream segment '" + str(featID) + "' was found with nearest point " + "{:0.1f}".format(sqrt(sqrDist)) + " m away\n")
         
         return nearPoint.x(), nearPoint.y()
   
   
   #if len(shared.allFieldsFlowPath) == 0:
      #return -1, -1
      
   ## N
   #adjX = thisPoint.x()
   #adjY = thisPoint.y() + shared.resolutionOfDEM   
   #if QgsPoint(adjX, adjY) in shared.allFieldsFlowPath:
      #return(adjX, adjY)

   ## NE
   #adjX = thisPoint.x() + shared.resolutionOfDEM
   #adjY = thisPoint.y() + shared.resolutionOfDEM
   #if QgsPoint(adjX, adjY) in shared.allFieldsFlowPath:
      #return(adjX, adjY)

   ## E
   #adjX = thisPoint.x() + shared.resolutionOfDEM
   #adjY = thisPoint.y() 
   #if QgsPoint(adjX, adjY) in shared.allFieldsFlowPath:
      #return(adjX, adjY)

   ## SE
   #adjX = thisPoint.x() + shared.resolutionOfDEM
   #adjY = thisPoint.y() - shared.resolutionOfDEM
   #if QgsPoint(adjX, adjY) in shared.allFieldsFlowPath:
      #return(adjX, adjY)

   ## S
   #adjX = thisPoint.x()
   #adjY = thisPoint.y() - shared.resolutionOfDEM
   #if QgsPoint(adjX, adjY) in shared.allFieldsFlowPath:
      #return(adjX, adjY)

   ## SW
   #adjX = thisPoint.x() - shared.resolutionOfDEM
   #adjY = thisPoint.y() - shared.resolutionOfDEM
   #if QgsPoint(adjX, adjY) in shared.allFieldsFlowPath:
      #return(adjX, adjY)

   ## W
   #adjX = thisPoint.x() - shared.resolutionOfDEM
   #adjY = thisPoint.y()
   #if QgsPoint(adjX, adjY) in shared.allFieldsFlowPath:
      #return(adjX, adjY)

   ## NW
   #adjX = thisPoint.x() - shared.resolutionOfDEM
   #adjY = thisPoint.y() + shared.resolutionOfDEM
   #if QgsPoint(adjX, adjY) in shared.allFieldsFlowPath:
      #return(adjX, adjY)
      
   #print("At end of FindNearbyFlowLine()")
   
   return -1, -1
#======================================================================================================================


#======================================================================================================================
#
# Is there a path near here?
#
#======================================================================================================================
def FindNearbyPath(point, flowFieldCode): 
   #shared.fpOut.write("\tEntered FindNearbyPath at point " + displayOS(point.x(), point.y()))
   layerNum = -1
   geomPoint = QgsGeometry.fromPoint(point)
   
   # Find the path network layer
   pathLayerFound = False
   for layerNum in range(len(shared.vectorInputLayersCategory)):
      if shared.vectorInputLayersCategory[layerNum] == INPUT_PATH_NETWORK:
         pathLayerFound = True
         break
   
   # Safety check
   if not pathLayerFound:
      printStr = "ERROR: opening path network layer\n"
      shared.fpOut.write(printStr)
      print(printStr)
      
      return -1
   
   # TODO make this a user setting
   numberToSearchFor = 3
   
   # Now search for the nearest path segments
   nearestIDs = shared.vectorInputIndex[layerNum].nearestNeighbor(point, numberToSearchFor)    
   request = QgsFeatureRequest().setFilterFids(nearestIDs)
   features = shared.vectorInputLayers[layerNum].getFeatures(request)
      
   distToPoint = []      
   geomPoint = QgsGeometry.fromPoint(point)
   
   for pathSeg in features:
      # Is this path segment both close enough, and has not already been followed?
      geomSeg = pathSeg.geometry()
      nearPoint = geomSeg.nearestPoint(geomPoint)
      distanceToSeg = geomPoint.distance(nearPoint)
      segID = pathSeg.id()
      #shared.fpOut.write("segID = " + str(segID) + " distanceToSeg = " + str(distanceToSeg) + "\n")
      
      if distanceToSeg > shared.searchDist or segID in shared.thisFieldPathSegIDsTried:
         # Too far away or already travelled, so forget about this path segment
         #shared.fpOut.write("Too far for segID = " + str(segID) + "\n")
         continue

      # Is OK, so save the path segment feature, the nearest point, and the distance
      distToPoint.append([pathSeg, nearPoint.asPoint(), distanceToSeg])
            
   # Did we any find suitable path segments?
   if len(distToPoint) == 0:
      # Nope
      #shared.fpOut.write("Leaving loop")
      return 0 
   
   # OK we have some suitable path segments, sort the list of untravelled path segments, shortest distance first         
   distToPoint.sort(key = lambda distPoint: distPoint[2])
   
   #for n in range(len(distToPoint)):
      #shared.fpOut.write("\tAfter sorting: " + str(n) + " " + str(distToPoint[n][0].id()) + " " + displayOS(distToPoint[n][1].x(), distToPoint[n][1].y()) + " " + str(distToPoint[n][2]) + " m\n")

   featIDTried = []
   for n in range(len(distToPoint)):
      # Go through this list of untravelled path segments
      feature = distToPoint[n][0]
      featID = feature.id()
      
      if featID not in featIDTried:
         #shared.fpOut.write("Trying feature ID " + str(featID) + "\n")
         featIDTried.append(featID)
         
         featDesc = feature[PATH_DESC]
         
         geomFeat = feature.geometry()
         linePoints = geomFeat.asPolyline()
         nPoints = len(linePoints)

         # OK, the nearest point is an approximation: it is not necessarily a point in the line. So get the actual point in the line which is closest
#         nearPoint, numNearpoint, beforeNearpoint, afterNearpoint, sqrDist = geomFeat.closestVertex(distToPoint[n][1])
         
         #shared.fpOut.write("At " + displayOS(point.x(), point.y()) + ", an untravelled path segment '" + str(featDesc) + "' was found with nearest point " + "{:0.1f}".format(sqrt(sqrDist)) + " m away" + "\n*** Does flow go over, under or along this path? Please add a field observation\n")
         
         shared.fpOut.write("At " + displayOS(point.x(), point.y()) + ", an untravelled path segment '" + str(featDesc) + "' was found with nearest point " + "{:0.1f}".format(distToPoint[n][2]) + " m away" + "\n*** Does flow go over, under or along this path? Please add a field observation\n")
         
         
   return 1
#======================================================================================================================


#======================================================================================================================
#
# Searches for a field observation near to a given location, if found then returns the number of the field observation
#
#======================================================================================================================
def FindNearbyFieldObservation(foundPoint):
   numObs = len(shared.fieldObservationFlowFrom)
   #shared.fpOut.write(shared.fieldObservationFlowFrom)
   
   if numObs == 0:
      # No field observations
      return -1
   
   # Construct the bounding box   
   xMin = foundPoint.x() - shared.searchDist
   xMax = foundPoint.x() + shared.searchDist
   yMin = foundPoint.y() - shared.searchDist
   yMax = foundPoint.y() + shared.searchDist

   #shared.fpOut.write("Searching for field observations between " + displayOS(xMin, yMin) + " and " + displayOS(xMax, yMax))
                 
   for indx in range(numObs):
      if indx in shared.thisFieldFieldObsAlreadyFollowed:
         continue
      
      xObs = shared.fieldObservationFlowFrom[indx].x()
      yObs = shared.fieldObservationFlowFrom[indx].y()
      
      if xMin < xObs < xMax and yMin < yObs < yMax:
         #shared.fpOut.write("Found " + str(indx))
         shared.fpOut.write("Field observation '" + shared.fieldObservationBehaviour[indx] + " " + shared.fieldObservationCategory[indx] + " " + shared.fieldObservationDescription[indx] + "' found at " + displayOS(shared.fieldObservationFlowFrom[indx].x(), shared.fieldObservationFlowFrom[indx].y()) + "\n")

         return indx
   return -1
#======================================================================================================================


#======================================================================================================================
#
# Is there a road near here? 
#
#======================================================================================================================
def FindNearbyRoad(point, flowFieldCode): 
   #shared.fpOut.write("\tEntered FindNearbyRoad at point " + displayOS(point.x(), point.y()))
   layerNum = -1
   geomPoint = QgsGeometry.fromPoint(point)
   
   # Find the road network layer
   roadLayerFound = False
   for layerNum in range(len(shared.vectorInputLayersCategory)):
      if shared.vectorInputLayersCategory[layerNum] == INPUT_ROAD_NETWORK:
         roadLayerFound = True
         break
   
   # Safety check
   if not roadLayerFound:
      printStr = "ERROR: opening road network layer\n"
      shared.fpOut.write(printStr)
      print(printStr)
      
      return -1
   
   # TODO make this a user setting
   numberToSearchFor = 3
   
   # Now search for the nearest road segments
   nearestIDs = shared.vectorInputIndex[layerNum].nearestNeighbor(point, numberToSearchFor)    
   request = QgsFeatureRequest().setFilterFids(nearestIDs)
   features = shared.vectorInputLayers[layerNum].getFeatures(request)
      
   distToPoint = []      
   geomPoint = QgsGeometry.fromPoint(point)
   
   for roadSeg in features:
      # Is this road segment both close enough, and has not already been followed?
      geomSeg = roadSeg.geometry()
      nearPoint = geomSeg.nearestPoint(geomPoint)
      distanceToSeg = geomPoint.distance(nearPoint)
      segID = roadSeg.id()
      #shared.fpOut.write("segID = " + str(segID) + " distanceToSeg = " + str(distanceToSeg) + "\n")
      
      if distanceToSeg > shared.searchDist or segID in shared.thisFieldRoadSegIDsTried:
         # Too far away or already travelled, so forget about this road segment
         #shared.fpOut.write("Too far for segID = " + str(segID) + "\n")
         continue

      # Is OK, so save the road segment feature, the nearest point, and the distance
      distToPoint.append([roadSeg, nearPoint.asPoint(), distanceToSeg])
            
   # Did we any find suitable road segments?
   if len(distToPoint) == 0:
      # Nope
      #shared.fpOut.write("Leaving loop")
      return 0 
   
   # OK we have some suitable road segments, sort the list of untravelled road segments, shortest distance first         
   distToPoint.sort(key = lambda distPoint: distPoint[2])
   
   #for n in range(len(distToPoint)):
      #shared.fpOut.write("\tAfter sorting: " + str(n) + " " + str(distToPoint[n][0].id()) + " " + displayOS(distToPoint[n][1].x(), distToPoint[n][1].y()) + " " + str(distToPoint[n][2]) + " m\n")

   featIDTried = []
   for n in range(len(distToPoint)):
      # Go through this list of untravelled road segments
      feature = distToPoint[n][0]
      featID = feature.id()
      
      if featID not in featIDTried:
         #shared.fpOut.write("Trying feature ID " + str(featID) + "\n")
         featIDTried.append(featID)
         
         featCode = feature[OS_VECTORMAP_FEAT_CODE]
         featDesc = feature[OS_VECTORMAP_FEAT_DESC]
         roadName = feature[OS_VECTORMAP_ROAD_NAME]
         roadNumber = feature[OS_VECTORMAP_ROAD_NUMBER]
         
         geomFeat = feature.geometry()
         linePoints = geomFeat.asPolyline()
         nPoints = len(linePoints)

         # OK, the nearest point is an approximation: it is not necessarily a point in the line. So get the actual point in the line which is closest
#         nearPoint, numNearpoint, beforeNearpoint, afterNearpoint, sqrDist = geomFeat.closestVertex(distToPoint[n][1])
         
         #shared.fpOut.write("At " + displayOS(point.x(), point.y()) + ", an untravelled road segment '" + str(featDesc) + "' '" + str(roadName) + "' '" + str(roadNumber) + "' was found with nearest point " + "{:0.1f}".format(sqrt(sqrDist)) + " m away" + "\n*** Does flow go over, under or along this road? Please add a field observation\n")
         
         shared.fpOut.write("At " + displayOS(point.x(), point.y()) + ", an untravelled road segment '" + str(featDesc) + "' '" + str(roadName) + "' '" + str(roadNumber) + "' was found with nearest point " + "{:0.1f}".format(distToPoint[n][2]) + " m away" + "\n*** Does flow go over, under or along this road? Please add a field observation\n")
         
         
   return 1
#======================================================================================================================


#======================================================================================================================
#
# Finds the adjacent grid cell (previously untravelled by flow from this field) with the steepest downhill gradient which is on a road or path
#
#======================================================================================================================
def FindSteepestAdjacentRoadOrPath(thisPoint, thisElev):   
   #shared.fpOut.write(n, displayOS(thisPoint.x(), thisPoint.y()), thisElev)
   
   maxGradient = 0
   newAdjX = -1
   newAdjY = -1
   newAdjElev = -1

   # N
   adjX = thisPoint.x()
   adjY = thisPoint.y() + shared.resolutionOfDEM
   adjElev = getRasterElev(adjX, adjY)
   #shared.fpOut.write(adjX, adjY, adjElev)
   
   gradient = (thisElev - adjElev) / shared.resolutionOfDEM
   #shared.fpOut.write("N", gradient)
   
   if gradient > maxGradient and QgsPoint(adjX, adjY) not in shared.thisFieldFlowLine:
      val = getRasterCellValueAsInt(adjX, adjY)
      if val in OS_MASTERMAP_ROAD or val in OS_MASTERMAP_PATH:
         maxGradient = gradient
         newAdjX = adjX
         newAdjY = adjY
         newAdjElev = adjElev
         #shared.fpOut.write("N maxGradient = ", maxGradient, " to {", newAdjX, ", ", newAdjY, "}")
      
   # NE
   adjX = thisPoint.x() + shared.resolutionOfDEM
   adjY = thisPoint.y() + shared.resolutionOfDEM
   adjElev = getRasterElev(adjX, adjY)
   #shared.fpOut.write(adjX, adjY, adjElev)
   
   gradient = (thisElev - adjElev) / shared.distDiag
   #shared.fpOut.write("NE", gradient)
   
   if gradient > maxGradient and QgsPoint(adjX, adjY) not in shared.thisFieldFlowLine:
      val = getRasterCellValueAsInt(adjX, adjY)
      if val in OS_MASTERMAP_ROAD or val in OS_MASTERMAP_PATH:
         maxGradient = gradient
         newAdjX = adjX
         newAdjY = adjY
         newAdjElev = adjElev
         #shared.fpOut.write("NE maxGradient = ", maxGradient, " to {", newAdjX, ", ", newAdjY, "}")

   # E
   adjX = thisPoint.x() + shared.resolutionOfDEM
   adjY = thisPoint.y() 
   adjElev = getRasterElev(adjX, adjY)
   #shared.fpOut.write(adjX, adjY, adjElev)
   
   gradient = (thisElev - adjElev) / shared.resolutionOfDEM
   #shared.fpOut.write("E", gradient)
   
   if gradient > maxGradient and QgsPoint(adjX, adjY) not in shared.thisFieldFlowLine:
      val = getRasterCellValueAsInt(adjX, adjY)
      if val in OS_MASTERMAP_ROAD or val in OS_MASTERMAP_PATH:
         maxGradient = gradient
         newAdjX = adjX
         newAdjY = adjY
         newAdjElev = adjElev
         #shared.fpOut.write("E maxGradient = ", maxGradient, " to {", newAdjX, ", ", newAdjY, "}")

   # SE
   adjX = thisPoint.x() + shared.resolutionOfDEM
   adjY = thisPoint.y() - shared.resolutionOfDEM
   adjElev = getRasterElev(adjX, adjY)
   #shared.fpOut.write(adjX, adjY, adjElev)
   
   gradient = (thisElev - adjElev) / shared.distDiag
   #shared.fpOut.write("SE", gradient)
   
   if gradient > maxGradient and QgsPoint(adjX, adjY) not in shared.thisFieldFlowLine:
      val = getRasterCellValueAsInt(adjX, adjY)
      if val in OS_MASTERMAP_ROAD or val in OS_MASTERMAP_PATH:
         maxGradient = gradient
         newAdjX = adjX
         newAdjY = adjY
         newAdjElev = adjElev
         #shared.fpOut.write("SE maxGradient = ", maxGradient, " to {", newAdjX, ", ", newAdjY, "}")

   # S
   adjX = thisPoint.x()
   adjY = thisPoint.y() - shared.resolutionOfDEM
   adjElev = getRasterElev(adjX, adjY)
   #shared.fpOut.write(adjX, adjY, adjElev)
   
   gradient = (thisElev - adjElev) / shared.resolutionOfDEM
   #shared.fpOut.write("S", gradient)
   
   if gradient > maxGradient and QgsPoint(adjX, adjY) not in shared.thisFieldFlowLine:
      val = getRasterCellValueAsInt(adjX, adjY)
      if val in OS_MASTERMAP_ROAD or val in OS_MASTERMAP_PATH:
         maxGradient = gradient
         newAdjX = adjX
         newAdjY = adjY
         newAdjElev = adjElev
         #shared.fpOut.write("S maxGradient = ", maxGradient, " to {", newAdjX, ", ", newAdjY, "}")

   # SW
   adjX = thisPoint.x() - shared.resolutionOfDEM
   adjY = thisPoint.y() - shared.resolutionOfDEM
   adjElev = getRasterElev(adjX, adjY)
   #shared.fpOut.write(adjX, adjY, adjElev)
   
   gradient = (thisElev - adjElev) / shared.distDiag
   #shared.fpOut.write("SW", gradient)
   
   if gradient > maxGradient and QgsPoint(adjX, adjY) not in shared.thisFieldFlowLine:
      val = getRasterCellValueAsInt(adjX, adjY)
      if val in OS_MASTERMAP_ROAD or val in OS_MASTERMAP_PATH:
         maxGradient = gradient
         newAdjX = adjX
         newAdjY = adjY
         newAdjElev = adjElev
         #shared.fpOut.write("SW maxGradient = ", maxGradient, " to {", newAdjX, ", ", newAdjY, "}")

   # W
   adjX = thisPoint.x() - shared.resolutionOfDEM
   adjY = thisPoint.y()
   adjElev = getRasterElev(adjX, adjY)
   #shared.fpOut.write(adjX, adjY, adjElev)
   
   gradient = (thisElev - adjElev) / shared.resolutionOfDEM
   #shared.fpOut.write("W", gradient)
   
   if gradient > maxGradient and QgsPoint(adjX, adjY) not in shared.thisFieldFlowLine:
      val = getRasterCellValueAsInt(adjX, adjY)
      if val in OS_MASTERMAP_ROAD or val in OS_MASTERMAP_PATH:
         maxGradient = gradient
         newAdjX = adjX
         newAdjY = adjY
         newAdjElev = adjElev      
         #shared.fpOut.write("W maxGradient = ", maxGradient, " to {", newAdjX, ", ", newAdjY, "}")

   # NW
   adjX = thisPoint.x() - shared.resolutionOfDEM
   adjY = thisPoint.y() + shared.resolutionOfDEM
   adjElev = getRasterElev(adjX, adjY)
   #shared.fpOut.write(adjX, adjY, adjElev)
   
   gradient = (thisElev - adjElev) / shared.distDiag
   #shared.fpOut.write("NW", gradient)
   
   if gradient > maxGradient and QgsPoint(adjX, adjY) not in shared.thisFieldFlowLine:
      val = getRasterCellValueAsInt(adjX, adjY)
      if val in OS_MASTERMAP_ROAD or val in OS_MASTERMAP_PATH:
         maxGradient = gradient
         newAdjX = adjX
         newAdjY = adjY
         newAdjElev = adjElev
         #shared.fpOut.write("NW maxGradient = ", maxGradient, " to {", newAdjX, ", ", newAdjY, "}")
         
   return QgsPoint(newAdjX, newAdjY), newAdjElev, tolerance
#======================================================================================================================


#======================================================================================================================
#
# Checks to see if an object's geometry intersects a stream segment: if it does, then return the point(s) of intersection
#
#======================================================================================================================
def FindSegmentIntersectionWithStream(featGeom):
   layerNum = -1
   
   # Find the water network layer
   waterLayerFound = False
   for layerNum in range(len(shared.vectorInputLayersCategory)):
      if shared.vectorInputLayersCategory[layerNum] == INPUT_WATER_NETWORK:
         waterLayerFound = True
         break
   
   # Safety check
   if not waterLayerFound:
      printStr = "ERROR: opening stream flow network layer\n"
      shared.fpOut.write(printStr)
      print(printStr)
      
      return -1, -1

   # Does the object's geometry intersect any stream segments? First construct a bounding box around the road, then see if any streams intersect this
   roadBoundingBox = featGeom.boundingBox()
   intersectingStreams = shared.vectorInputIndex[layerNum].intersects(roadBoundingBox)
   
   if len(intersectingStreams) == 0:
      # No intersections
      return 0, 0
   
   # OK we have at least one possible intersection
   request = QgsFeatureRequest().setFilterFids(intersectingStreams)
   features = shared.vectorInputLayers[layerNum].getFeatures(request)
   
   intersectPoints = []
   for streamSeg in features:
      # Get the point of intersection
      geomStreamSeg = streamSeg.geometry()
      if featGeom.intersects(geomStreamSeg):
         # Yes, they do intersect
         geomIntersect = featGeom.intersection(geomStreamSeg)
         
         intersectPoint = geomIntersect.asPoint()
         #print("intersectPoint = " + displayOS(intersectPoint.x(), intersectPoint.y()))
         
         intersectPoints.append(intersectPoint)
      
   return 1, intersectPoints
#======================================================================================================================
   

#======================================================================================================================
#
# Is there a stream near this location? If so, route flow into this stream until it reaches the Rother
#
#======================================================================================================================
def FindNearbyStream(point, flowFieldCode): 
   #shared.fpOut.write("Entered FindNearbyStream at point " + displayOS(point.x(), point.y()))
   layerNum = -1
   geomPoint = QgsGeometry.fromPoint(point)
   
   streamSegIDsFollowed = []
   
   # Find the water network layer
   waterLayerFound = False
   for layerNum in range(len(shared.vectorInputLayersCategory)):
      if shared.vectorInputLayersCategory[layerNum] == INPUT_WATER_NETWORK:
         waterLayerFound = True
         break
   
   # Safety check
   if not waterLayerFound:
      printStr = "ERROR: opening stream flow network layer\n"
      shared.fpOut.write(printStr)
      print(printStr)
      
      return -1

   # TODO make this a user setting
   numberToSearchFor = 3
   
   # Loop until we either hit the Rother, or cannot find a suitable nearby stream segment
   inStream = False
   while (True):
      # Find the nearest stream segments
      #shared.fpOut.write("Start of loop: " + displayOS(point.x(), point.y()))
      nearestIDs = shared.vectorInputIndex[layerNum].nearestNeighbor(point, numberToSearchFor)    
      request = QgsFeatureRequest().setFilterFids(nearestIDs)
      features = shared.vectorInputLayers[layerNum].getFeatures(request)
      
      distToPoint = []      
      geomPoint = QgsGeometry.fromPoint(point)

      for streamSeg in features:
         # Is this stream segment both close enough, and has not already been followed?
         geomSeg = streamSeg.geometry()
         nearPoint = geomSeg.nearestPoint(geomPoint)
         distanceToSeg = geomPoint.distance(nearPoint)
         segID = streamSeg.id()
         #shared.fpOut.write("segID = " + str(segID) + " distanceToSeg = " + str(distanceToSeg))
         
         if distanceToSeg > shared.searchDist or segID in streamSegIDsFollowed:
            # Too far away or already travelled, so forget about this stream segment
            continue

         # Is OK, so save the stream segment feature, the nearest point, and the distance
         distToPoint.append([streamSeg, nearPoint.asPoint(), distanceToSeg])
            
      # Did we find suitable stream segments?
      if len(distToPoint) == 0:
         # Nope
         #shared.fpOut.write("Leaving loop")
         return 0 
      
      # OK we have some suitable stream segments
      #for n in range(len(distToPoint)):
         #shared.fpOut.write("Before " + str(n) + " " + str(distToPoint[n][0].id()) + " " + displayOS(distToPoint[n][1].x(), distToPoint[n][1].y()) + " " + str(distToPoint[n][2]) + " m")

      # Sort the list of untravelled stream segments, shortest distance first         
      distToPoint.sort(key = lambda distPoint: distPoint[2])

      #for n in range(len(distToPoint)):
         #print"After " + (str(n) + " " + str(distToPoint[n][0].id()) + " " + displayOS(distToPoint[n][1].x(), distToPoint[n][1].y()) + " " + str(distToPoint[n][2]) + " m")
      
      flowRouted = False
      for n in range(len(distToPoint)):
         # Go through this list of untravelled stream segments till we find a suitable one
         feature = distToPoint[n][0]
         featID = feature.id()
         #shared.fpOut.write("Trying feature ID " + str(featID))
         
         localID = feature[OS_WATER_NETWORK_LOCAL_ID]
         
         # Is this the Rother?
         streamName = feature[OS_WATER_NETWORK_NAME]
         if streamName != NULL and streamName.upper().find(TARGET_RIVER) >= 0:
            # Yes, flow has entered the Rother
            shared.fpOut.write("Flow from field " + flowFieldCode + " enters the River Rother at " + displayOS(point.x(), point.y()) + "\n")                  
            addFlowMarkerPoint(point, MARKER_ENTER_RIVER, flowFieldCode, -1)
            
            # We are done here
            return 1
         
         # This stream segment is not the Rother. Are we considering ditches?
         if not shared.considerDitches:
            # We are not, so don't try to route flow along this stream segment
            continue
         
         # We are considering ditches
         geomFeat = feature.geometry()
         linePoints = geomFeat.asPolyline()
         nPoints = len(linePoints)

         firstPoint = linePoints[0]         
         lastPoint = linePoints[-1]
         
         # OK, the nearest point is an approximation: it is not necessarily a point in the line. So get the actual point in the line which is closest
         nearPoint, numNearpoint, beforeNearpoint, afterNearpoint, sqrDist = geomFeat.closestVertex(distToPoint[n][1])
                  
         #shared.fpOut.write("At " + displayOS(point.x(), point.y() + ", an untravelled stream segment " + str(localID) + " found with nearest point " + "{:0.1f}".format(sqrt(sqrDist)) + " m away"))
         
         #shared.fpOut.write("\tFirst point of stream segment is " + displayOS(firstPoint.x(), firstPoint.y()))
         #shared.fpOut.write("\tNearest point of stream segment is " + displayOS(nearPoint.x(), nearPoint.y()))
         #shared.fpOut.write("\tLast point of stream segment is " + displayOS(lastPoint.x(), lastPoint.y()))
         
         # Check the flow direction
         flowDirection = feature["flowDirection"]
         #shared.fpOut.write("\tFlow direction of this stream segment is " + flowDirection)
         
         if nearPoint == firstPoint and flowDirection != "inDirection":
            #shared.fpOut.write("Flow going wrong way in stream segment " + str(localID))
               
            # Try the next stream segment
            continue
            
         elif nearPoint == lastPoint and flowDirection == "inDirection":
            #shared.fpOut.write("Flow going wrong way in stream segment " + str(localID))
               
            # Try the next stream segment
            continue
         
         # We are flowing along at least part of this stream segment
         if flowDirection == "inDirection":
            for m in range(numNearpoint, len(linePoints)-1):
               thisPoint = linePoints[m]
               nextPoint = linePoints[m+1]
         
               addFlowLine(thisPoint, nextPoint, FLOW_VIA_STREAM, flowFieldCode, -1)
               #shared.fpOut.write("addFlowLine 1", thisPoint.x(), thisPoint.y())
         else:
            for m in range(numNearpoint, 1, -1):
               thisPoint = linePoints[m]
               nextPoint = linePoints[m-1]
         
               addFlowLine(thisPoint, nextPoint, FLOW_VIA_STREAM, flowFieldCode, -1)
               #shared.fpOut.write("addFlowLine 2", thisPoint.x(), thisPoint.y())
            
         # OK we have flow routed along this stream segment
         streamSegIDsFollowed.append(featID)
         flowRouted = True
         inStream = True         
         
         #shared.fpOut.write(feature.attributes())
         
         #fields = shared.vectorInputLayers[vectorNum].fields().toList()
         #for fld in fields:
            #shared.fpOut.write(fld.displayName())
         #shared.fpOut.write("")
         
         level = feature[OS_WATER_NETWORK_LEVEL]
         if level == "underground":
            typeName = MARKER_ENTER_CULVERT
            if streamName == NULL:
               streamName = "culvert"
         else:
            typeName = MARKER_ENTER_STREAM
            if streamName == NULL:
               streamName = "stream"
         
         shared.fpOut.write("Flow from field " + flowFieldCode + " enters the OS " + streamName + " segment " + str(localID) + " at " + displayOS(point.x(), point.y()) + " and leaves it at " + displayOS(lastPoint.x(), lastPoint.y()) + "\n")
         #shared.fpOut.write("======")            
      
         # Set the end point of this stream segment to be the start point, ready for next time round the loop
         point = lastPoint
         
         # Don't bother looking at other stream segments since flow was routed along this stream segment
         break
            
      if not flowRouted:
         #printStr = "No suitable stream segment found"
         #shared.fpOut.write(printStr)
         #print(printStr)
         
         return 0
      
   return 0
#======================================================================================================================


#======================================================================================================================
#
# Finds the steeper of two road segments
#
#======================================================================================================================
def FindSteepestSegment(firstPoint, nearPoint, lastPoint, elevDiffNearToFirst, elevDiffNearToLast):
   geomFirstPoint = QgsGeometry.fromPoint(firstPoint)
   geomNearPoint = QgsGeometry.fromPoint(nearPoint)
   geomLastPoint = QgsGeometry.fromPoint(lastPoint)

   # Note that this calculates the straight-line distance, which will not be appropriate if the roads are very twisty
   distAlongRoadNearToFirst = geomNearPoint.distance(geomFirstPoint) 
   distAlongRoadNearToLast = geomNearPoint.distance(geomLastPoint) 
            
   gradientNearToFirst = elevDiffNearToFirst / distAlongRoadNearToFirst
   gradientNearToLast = elevDiffNearToLast / distAlongRoadNearToLast
   
   if gradientNearToLast > gradientNearToFirst:
      return True
   else:
      return False
#======================================================================================================================
   

#======================================================================================================================
#
# Finds all adjacent grid cells which are lower than the supplied elevation, and adds them to a list (if not already present)
#
#======================================================================================================================
def CanOverflowTo(thisPoint, topElev, overflowCells):  
   newOverflowCells = []
   
   # N
   adjX = thisPoint.x()
   adjY = thisPoint.y() + shared.resolutionOfDEM
   adjElev = getRasterElev(adjX, adjY)
   
   if adjElev <= topElev:
      newPoint = QgsPoint(adjX, adjY)
      if newPoint not in overflowCells:
         newOverflowCells.append(newPoint)
      
   # NE
   adjX = thisPoint.x() + shared.resolutionOfDEM
   adjY = thisPoint.y() + shared.resolutionOfDEM
   adjElev = getRasterElev(adjX, adjY)

   if adjElev <= topElev:
      newPoint = QgsPoint(adjX, adjY)
      if newPoint not in overflowCells:
         newOverflowCells.append(newPoint)

   # E
   adjX = thisPoint.x() + shared.resolutionOfDEM
   adjY = thisPoint.y() 
   adjElev = getRasterElev(adjX, adjY)

   if adjElev <= topElev:
      newPoint = QgsPoint(adjX, adjY)
      if newPoint not in overflowCells:
         newOverflowCells.append(newPoint)

   # SE
   adjX = thisPoint.x() + shared.resolutionOfDEM
   adjY = thisPoint.y() - shared.resolutionOfDEM
   adjElev = getRasterElev(adjX, adjY)

   if adjElev <= topElev:
      newPoint = QgsPoint(adjX, adjY)
      if newPoint not in overflowCells:
         newOverflowCells.append(newPoint)

   # S
   adjX = thisPoint.x()
   adjY = thisPoint.y() - shared.resolutionOfDEM
   adjElev = getRasterElev(adjX, adjY)

   if adjElev <= topElev:
      newPoint = QgsPoint(adjX, adjY)
      if newPoint not in overflowCells:
         newOverflowCells.append(newPoint)

   # SW
   adjX = thisPoint.x() - shared.resolutionOfDEM
   adjY = thisPoint.y() - shared.resolutionOfDEM
   adjElev = getRasterElev(adjX, adjY)

   if adjElev <= topElev:
      newPoint = QgsPoint(adjX, adjY)
      if newPoint not in overflowCells:
         newOverflowCells.append(newPoint)

   # W
   adjX = thisPoint.x() - shared.resolutionOfDEM
   adjY = thisPoint.y()
   adjElev = getRasterElev(adjX, adjY)

   if adjElev <= topElev:
      newPoint = QgsPoint(adjX, adjY)
      if newPoint not in overflowCells:
         newOverflowCells.append(newPoint)

   # NW
   adjX = thisPoint.x() - shared.resolutionOfDEM
   adjY = thisPoint.y() + shared.resolutionOfDEM
   adjElev = getRasterElev(adjX, adjY)

   if adjElev <= topElev:
      newPoint = QgsPoint(adjX, adjY)
      if newPoint not in overflowCells:
         newOverflowCells.append(newPoint)
      
   return newOverflowCells
#======================================================================================================================
   

