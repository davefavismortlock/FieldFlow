from math import sqrt

from qgis.core import NULL, QgsGeometry, QgsFeatureRequest, QgsPointXY

import shared
from shared import INPUT_PATH_NETWORK, PATH_DESC, INPUT_ROAD_NETWORK, OS_VECTORMAP_FEAT_CODE, OS_VECTORMAP_FEAT_DESC, OS_VECTORMAP_ROAD_NAME, OS_VECTORMAP_ROAD_NUMBER, INPUT_WATERCOURSE_NETWORK, OS_WATER_NETWORK_LOCAL_ID, OS_WATER_NETWORK_NAME, TARGET_RIVER, TARGET_RIVER_NAME, MARKER_ENTER_RIVER, FLOW_VIA_WATERCOURSE, OS_WATER_NETWORK_LEVEL, MARKER_ENTER_CULVERT, MARKER_ENTER_WATERCOURSE, INPUT_DITCH_NETWORK, DITCH_NETWORK_LOCAL_ID, DITCH_NETWORK_DESC, FLOW_VIA_DITCH, MARKER_ENTER_DITCH, OUTPUT_FIELD_CODE
from utils import GetRasterElev, DisplayOS
from layers import AddFlowMarkerPoint, AddFlowLine


#======================================================================================================================
#
# Finds the adjacent grid cell to which water can flow, with the steepest downhill gradient, and to which this field's flow has not already travelled
#
#======================================================================================================================
def FindSteepestDownhillAdjacent(thisPoint, thisElev, geomPolygon = -1):
   # pylint: disable=too-many-locals
   # pylint: disable=too-many-branches
   # pylint: disable=too-many-statements

   newAdjX = -1
   newAdjY = -1
   newAdjElev = -1

   maxGradient = 0

   #shared.fpOut.write(n, DisplayOS(thisPoint.x(), thisPoint.y()), thisElev)

   # N
   adjX = thisPoint.x()
   adjY = thisPoint.y() + shared.resolutionOfDEM
   adjElev = GetRasterElev(adjX, adjY)

   #shared.fpOut.write(str(DisplayOS(adjX, adjY)) + " elev = " + str(adjElev) + "\n")

   gradient = (thisElev - adjElev) / shared.resolutionOfDEM
   #shared.fpOut.write("N " + str(gradient) + "\n")

   if gradient > maxGradient:
      adjPoint = QgsPointXY(adjX, adjY)
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
   adjElev = GetRasterElev(adjX, adjY)

   #shared.fpOut.write(str(DisplayOS(adjX, adjY)) + " elev = " + str(adjElev) + "\n")

   gradient = (thisElev  - adjElev) / shared.distDiag
   #shared.fpOut.write("NE " + str(gradient) + "\n")

   if gradient > maxGradient:
      adjPoint = QgsPointXY(adjX, adjY)
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
   adjElev = GetRasterElev(adjX, adjY)

   #shared.fpOut.write(str(DisplayOS(adjX, adjY)) + " elev = " + str(adjElev) + "\n")

   gradient = (thisElev  - adjElev) / shared.resolutionOfDEM
   #shared.fpOut.write("E " + str(gradient) + "\n")

   if gradient > maxGradient:
      adjPoint = QgsPointXY(adjX, adjY)
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
   adjElev = GetRasterElev(adjX, adjY)

   #shared.fpOut.write(str(DisplayOS(adjX, adjY)) + " elev = " + str(adjElev) + "\n")

   gradient = (thisElev  - adjElev) / shared.distDiag
   #shared.fpOut.write("SE " + str(gradient) + "\n")

   if gradient > maxGradient:
      adjPoint = QgsPointXY(adjX, adjY)
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
   adjElev = GetRasterElev(adjX, adjY)

   #shared.fpOut.write(str(DisplayOS(adjX, adjY)) + " elev = " + str(adjElev) + "\n")

   gradient = (thisElev  - adjElev) / shared.resolutionOfDEM
   #shared.fpOut.write("S " + str(gradient) + "\n")

   if gradient > maxGradient:
      adjPoint = QgsPointXY(adjX, adjY)
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
   adjElev = GetRasterElev(adjX, adjY)

   #shared.fpOut.write(str(DisplayOS(adjX, adjY)) + " elev = " + str(adjElev) + "\n")

   gradient = (thisElev  - adjElev) / shared.distDiag
   #shared.fpOut.write("SW " + str(gradient) + "\n")

   if gradient > maxGradient:
      adjPoint = QgsPointXY(adjX, adjY)
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
   adjElev = GetRasterElev(adjX, adjY)

   #shared.fpOut.write(str(DisplayOS(adjX, adjY)) + " elev = " + str(adjElev) + "\n")

   gradient = (thisElev  - adjElev) / shared.resolutionOfDEM
   #shared.fpOut.write("W " + str(gradient) + "\n")

   if gradient > maxGradient:
      adjPoint = QgsPointXY(adjX, adjY)
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
   adjElev = GetRasterElev(adjX, adjY)

   #shared.fpOut.write(str(DisplayOS(adjX, adjY)) + " elev = " + str(adjElev) + "\n")

   gradient = (thisElev  - adjElev) / shared.distDiag
   #shared.fpOut.write("NW " + str(gradient) + "\n")

   if gradient > maxGradient:
      adjPoint = QgsPointXY(adjX, adjY)
      if adjPoint not in shared.thisFieldFlowLine:
         if geomPolygon == -1 or (geomPolygon != -1 and geomPolygon.contains(adjPoint)):
            maxGradient = gradient
            newAdjX = adjX
            newAdjY = adjY
            newAdjElev = adjElev
            #shared.fpOut.write("New maxGradient = " + str(maxGradient) + " to " + DisplayOS(newAdjX, newAdjY) + "\n")

   return QgsPointXY(newAdjX, newAdjY), newAdjElev
#======================================================================================================================


#======================================================================================================================
#
# Is there another flow line nearby?
#
#======================================================================================================================
def FindNearbyFlowLine(thisPoint):
   # pylint: disable=too-many-locals

   #shared.fpOut.write("Entered FindNearbyFlowLine() at point " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n")
   #layerNum = -1
   thisPointXY = QgsPointXY(thisPoint)
   geomThisPoint = QgsGeometry.fromPointXY(thisPointXY)

   # TODO make this a user setting
   numberToSearchFor = 3

   # Now search for the nearest flowline segments
   nearestIDs = shared.outFlowLineLayerIndex.nearestNeighbor(thisPointXY, numberToSearchFor)
   #if len(nearestIDs) > 0:
      #print("Nearest flowline segment IDs = " + str(nearestIDs))

   # For the first flowline, there are no pre-existing flowlines
   if not nearestIDs:
      #print("No flowlines")
      return -1, -1, -1

   # OK we have some flowlines
   request = QgsFeatureRequest().setFilterFids(nearestIDs)
   features = shared.outFlowLineLayer.getFeatures(request)

   distToPoint = []
   for flowLineSeg in features:
      #geom = flowLineSeg.geometry()
      #print("Geom: " + str(geom.wkbType()))
      #line = geom.asPolyline()
      #print("For point " + DisplayOS(thisPoint.x(), thisPoint.y()) + ", nearby line segment is from ")
      #for point in line:
         #print(DisplayOS(point.x(), point.y()))

      # Is this flow line segment close enough?
      geomSeg = flowLineSeg.geometry()
      nearPoint = geomSeg.nearestPoint(geomThisPoint)
      distanceToSeg = geomThisPoint.distance(nearPoint)
      #flowLineSegID = flowLineSeg.id()
      #shared.fpOut.write("flowLineSegID = " + str(flowLineSegID) + " distanceToSeg = " + str(distanceToSeg) + "\n")
      fieldCode = flowLineSeg[OUTPUT_FIELD_CODE]

      if distanceToSeg > shared.searchDist:
         # Too far away so forget about this flow line segment
         continue

      # Is OK, so save the flow line segment feature, the nearest point, the distance, and the field code
      distToPoint.append([flowLineSeg, nearPoint.asPoint(), distanceToSeg, fieldCode])

   # Did we any find suitable flow line segments?
   if not distToPoint:
      # Nope
      #print("Leaving loop")
      return -1, -1, -1

   # OK we have some suitable flow line segments, sort the list of watercourse segments, shortest distance first
   distToPoint.sort(key = lambda distPoint: distPoint[2])

   #for n in range(len(distToPoint)):
      #shared.fpOut.write("\tAfter sorting: " + str(n) + " " + str(distToPoint[n][0].id()) + " " + DisplayOS(distToPoint[n][1].x(), distToPoint[n][1].y()) + " " + str(distToPoint[n][2]) + " m")

   featIDTried = []
   for flowLineSeg in distToPoint:
      # Go through this list of flow line segments
      feature = flowLineSeg[0]
      featID = feature.id()

      if featID not in featIDTried:
         #shared.fpOut.write("Trying feature ID " + str(featID) + "\n")
         featIDTried.append(featID)
         geomFeat = feature.geometry()

         # The nearest point is an approximation: it is not necessarily a vertex of the line. So get the closest vertex of the line
         nearPoint, _numNearpoint, _beforeNearpoint, _afterNearpoint, sqrDist = geomFeat.closestVertex(flowLineSeg[1])

         #shared.fpOut.write("At " + DisplayOS(flowLineSeg[1].x(), flowLineSeg[1].y()) + ", flow line watercourse segment '" + str(featID) + "' was found with nearest vertex " + "{:0.1f}".format(sqrt(sqrDist)) + " m away\n")

         return nearPoint.x(), nearPoint.y(), flowLineSeg[3]


   #if len(shared.allFieldsFlowPath) == 0:
      #return -1, -1

   ## N
   #adjX = thisPoint.x()
   #adjY = thisPoint.y() + shared.resolutionOfDEM
   #if QgsPointXY(adjX, adjY) in shared.allFieldsFlowPath:
      #return(adjX, adjY)

   ## NE
   #adjX = thisPoint.x() + shared.resolutionOfDEM
   #adjY = thisPoint.y() + shared.resolutionOfDEM
   #if QgsPointXY(adjX, adjY) in shared.allFieldsFlowPath:
      #return(adjX, adjY)

   ## E
   #adjX = thisPoint.x() + shared.resolutionOfDEM
   #adjY = thisPoint.y()
   #if QgsPointXY(adjX, adjY) in shared.allFieldsFlowPath:
      #return(adjX, adjY)

   ## SE
   #adjX = thisPoint.x() + shared.resolutionOfDEM
   #adjY = thisPoint.y() - shared.resolutionOfDEM
   #if QgsPointXY(adjX, adjY) in shared.allFieldsFlowPath:
      #return(adjX, adjY)

   ## S
   #adjX = thisPoint.x()
   #adjY = thisPoint.y() - shared.resolutionOfDEM
   #if QgsPointXY(adjX, adjY) in shared.allFieldsFlowPath:
      #return(adjX, adjY)

   ## SW
   #adjX = thisPoint.x() - shared.resolutionOfDEM
   #adjY = thisPoint.y() - shared.resolutionOfDEM
   #if QgsPointXY(adjX, adjY) in shared.allFieldsFlowPath:
      #return(adjX, adjY)

   ## W
   #adjX = thisPoint.x() - shared.resolutionOfDEM
   #adjY = thisPoint.y()
   #if QgsPointXY(adjX, adjY) in shared.allFieldsFlowPath:
      #return(adjX, adjY)

   ## NW
   #adjX = thisPoint.x() - shared.resolutionOfDEM
   #adjY = thisPoint.y() + shared.resolutionOfDEM
   #if QgsPointXY(adjX, adjY) in shared.allFieldsFlowPath:
      #return(adjX, adjY)

   #print("At end of FindNearbyFlowLine()")

   return -1, -1, -1
#======================================================================================================================


#======================================================================================================================
#
# Is there a path near here? Returns -1 for a problem, 0 for no path found, 1 for path found, 2 for path found but need field observation
#
#======================================================================================================================
def FindNearbyPath(point, flowFieldCode, alreadyAlongPath):
   # pylint: disable=too-many-locals

   #shared.fpOut.write("\tEntered FindNearbyPath at point " + DisplayOS(point.x(), point.y()))
   layerNum = -1
   geomPoint = QgsGeometry.fromPointXY(QgsPointXY(point))

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
   nearestIDs = shared.vectorInputLayerIndex[layerNum].nearestNeighbor(QgsPointXY(point), numberToSearchFor)
   #if len(nearestIDs) > 0:
      #print("Nearest path segment IDs (2) = " + str(nearestIDs))

   request = QgsFeatureRequest().setFilterFids(nearestIDs)
   features = shared.vectorInputLayers[layerNum].getFeatures(request)

   distToPoint = []
   geomPoint = QgsGeometry.fromPointXY(QgsPointXY(point))

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
   if not distToPoint:
      # Nope
      #shared.fpOut.write("Leaving loop")
      return 0

   # OK we have some suitable path segments, sort the list of untravelled road segments, shortest distance first
   distToPoint.sort(key = lambda distPoint: distPoint[2])

   #for n in range(len(distToPoint)):
      #shared.fpOut.write("\tAfter sorting: " + str(n) + " " + str(distToPoint[n][0].id()) + " " + DisplayOS(distToPoint[n][1].x(), distToPoint[n][1].y()) + " " + str(distToPoint[n][2]) + " m\n")

   featIDTried = []
   for pathSeg in distToPoint:
      # Go through this list of untravelled path segments
      feature = pathSeg[0]
      featID = feature.id()

      if featID not in featIDTried:
         #shared.fpOut.write("Trying feature ID " + str(featID) + "\n")
         featIDTried.append(featID)

         featDesc = feature[PATH_DESC]

         #geomFeat = feature.geometry()
         #linePoints = geomFeat.asPolyline()
         #nPoints = len(linePoints)

         # The nearest point is an approximation: it is not necessarily a vertex of the line. So get the closest vertex of the line
#         nearPoint, numNearpoint, beforeNearpoint, afterNearpoint, sqrDist = geomFeat.closestVertex(pathSeg[1])

         #shared.fpOut.write("At " + DisplayOS(point.x(), point.y()) + ", an untravelled path segment '" + str(featDesc) + "' was found with nearest vertex " + "{:0.1f}".format(sqrt(sqrDist)) + " m away" + "\n*** Does flow go over, under or along this path? Please add a field observation\n")

         if not alreadyAlongPath:
            shared.fpOut.write("At " + DisplayOS(point.x(), point.y()) + ", an untravelled path segment '" + str(featDesc) + "' was found with nearest vertex " + "{:0.1f}".format(pathSeg[2]) + " m away" + "\n*** Does flow from field " + str(flowFieldCode) + " go over, under or along this path? Please add a field observation YYY\n")

            return 0

   return 1
#======================================================================================================================


#======================================================================================================================
#
# Searches for a field observation near to a given location, if found then returns the number of the field observation
#
#======================================================================================================================
def FindNearbyFieldObservation(foundPoint):
   numObs = len(shared.LEFlowInteractionFlowFrom)
   #shared.fpOut.write(shared.LEFlowInteractionFlowFrom)

   if numObs == 0:
      # No LE-flow interactions
      return -1

   # Construct the bounding box
   xMin = foundPoint.x() - shared.searchDist
   xMax = foundPoint.x() + shared.searchDist
   yMin = foundPoint.y() - shared.searchDist
   yMax = foundPoint.y() + shared.searchDist

   #shared.fpOut.write("Searching for LE-flow interactions between " + DisplayOS(xMin, yMin) + " and " + DisplayOS(xMax, yMax))

   for indx in range(numObs):
      if indx in shared.thisFieldFieldObsAlreadyFollowed:
         continue

      xObs = shared.LEFlowInteractionFlowFrom[indx].x()
      yObs = shared.LEFlowInteractionFlowFrom[indx].y()

      if xMin < xObs < xMax and yMin < yObs < yMax:
         shared.fpOut.write("\tLE-flow interaction found for location " + DisplayOS(shared.LEFlowInteractionFlowFrom[indx].x(), shared.LEFlowInteractionFlowFrom[indx].y()) + " '" + shared.fieldObservationBehaviour[indx] + " " + shared.fieldObservationCategory[indx] + ", " + shared.fieldObservationDescription[indx] + "'\n")

         return indx
   return -1
#======================================================================================================================


#======================================================================================================================
#
# Is there a road near here?
#
#======================================================================================================================
def FindNearbyRoad(point, flowFieldCode, alreadyAlongRoad):
   # pylint: disable=too-many-locals

   #shared.fpOut.write("\tEntered FindNearbyRoad at point " + DisplayOS(point.x(), point.y()))
   layerNum = -1
   geomPoint = QgsGeometry.fromPointXY(QgsPointXY(point))

   # Find the road network layer
   routeLayerFound = False
   for layerNum in range(len(shared.vectorInputLayersCategory)):
      if shared.vectorInputLayersCategory[layerNum] == INPUT_ROAD_NETWORK:
         routeLayerFound = True
         break

   # Safety check
   if not routeLayerFound:
      printStr = "ERROR: opening road network layer\n"
      shared.fpOut.write(printStr)
      print(printStr)

      return -1

   # TODO make this a user setting
   numberToSearchFor = 3

   # Now search for the nearest road segments
   nearestIDs = shared.vectorInputLayerIndex[layerNum].nearestNeighbor(QgsPointXY(point), numberToSearchFor)
   #if len(nearestIDs) > 0:
      #print("Nearest road segment IDs (2) = " + str(nearestIDs))

   request = QgsFeatureRequest().setFilterFids(nearestIDs)
   features = shared.vectorInputLayers[layerNum].getFeatures(request)

   distToPoint = []
   geomPoint = QgsGeometry.fromPointXY(QgsPointXY(point))

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
   if not distToPoint:
      # Nope
      #shared.fpOut.write("Leaving loop")
      return 0

   # OK we have some suitable road segments, sort the list of untravelled road segments, shortest distance first
   distToPoint.sort(key = lambda distPoint: distPoint[2])

   #for n in range(len(distToPoint)):
      #shared.fpOut.write("\tAfter sorting: " + str(n) + " " + str(distToPoint[n][0].id()) + " " + DisplayOS(distToPoint[n][1].x(), distToPoint[n][1].y()) + " " + str(distToPoint[n][2]) + " m\n")

   featIDTried = []
   for roadSeg in distToPoint:
      # Go through this list of untravelled road segments
      feature = roadSeg[0]
      featID = feature.id()

      if featID not in featIDTried:
         #shared.fpOut.write("Trying feature ID " + str(featID) + "\n")
         featIDTried.append(featID)

         featCode = feature[OS_VECTORMAP_FEAT_CODE]
         featDesc = feature[OS_VECTORMAP_FEAT_DESC]
         roadName = feature[OS_VECTORMAP_ROAD_NAME]
         roadNumber = feature[OS_VECTORMAP_ROAD_NUMBER]

         #geomFeat = feature.geometry()
         #linePoints = geomFeat.asPolyline()
         #nPoints = len(linePoints)

         # The nearest point is an approximation: it is not necessarily a vertex of the line. So get the closest vertex of the line
#         nearPoint, numNearpoint, beforeNearpoint, afterNearpoint, sqrDist = geomFeat.closestVertex(roadSeg[1])

         #shared.fpOut.write("At " + DisplayOS(point.x(), point.y()) + ", an untravelled road segment '" + str(featDesc) + "' '" + str(roadName) + "' '" + str(roadNumber) + "' was found with nearest vertex " + "{:0.1f}".format(sqrt(sqrDist)) + " m away" + "\n*** Does flow go over, under or along this road? Please add a field observation\n")

         #if not alreadyAlongRoad:
            #shared.fpOut.write("At " + DisplayOS(point.x(), point.y()) + ", an untravelled road segment '" + str(featCode) + "' '" + str(featDesc) + "' '" + str(roadName) + "' '" + str(roadNumber) + "' was found with nearest vertex " + "{:0.1f}".format(roadSeg[2]) + " m away" + "\n*** Does flow from field " + str(flowFieldCode) + " go over, under or along this road? Please add a field observation\n")

   return 1
#======================================================================================================================


#======================================================================================================================
#
# Checks to see if an object's geometry intersects a watercourse segment: if it does, then return the point(s) of intersection
#
#======================================================================================================================
def FindSegmentIntersectionWithWatercourse(featGeom):
   layerNum = -1

   # Find the water network layer
   watercourseLayerFound = False
   for layerNum in range(len(shared.vectorInputLayersCategory)):
      if shared.vectorInputLayersCategory[layerNum] == INPUT_WATERCOURSE_NETWORK:
         watercourseLayerFound = True
         break

   # Safety check
   if not watercourseLayerFound:
      printStr = "ERROR: opening stream flow network layer\n"
      shared.fpOut.write(printStr)
      print(printStr)

      return -1, -1

   # Does the object's geometry intersect any watercourse segments? First construct a bounding box around the road, then see if any streams intersect this
   roadBoundingBox = featGeom.boundingBox()
   #shared.fpOut.write("\t" + str(roadBoundingBox) + "\n")

   intersectingStreams = shared.vectorInputLayerIndex[layerNum].intersects(roadBoundingBox)

   if not intersectingStreams:
      # No intersections
      return 0, 0

   # OK we have at least one possible intersection
   request = QgsFeatureRequest().setFilterFids(intersectingStreams)
   features = shared.vectorInputLayers[layerNum].getFeatures(request)

   intersectPoints = []
   for watercourseSeg in features:
      # Get the point of intersection
      geomStreamSeg = watercourseSeg.geometry()
      if featGeom.intersects(geomStreamSeg):
         # Yes, they do intersect
         geomIntersect = featGeom.intersection(geomStreamSeg)

         intersectPoint = geomIntersect.asPoint()
         #shared.fpOut.write("intersectPoint = " + DisplayOS(intersectPoint.x(), intersectPoint.y()) + "\n")

         intersectPoints.append(intersectPoint)

   return 1, intersectPoints
#======================================================================================================================


#======================================================================================================================
#
# Is there a watercourse near this location? If so, route flow into this watercourse until it reaches the Rother
#
#======================================================================================================================
def FindNearbyWatercourse(point, flowFieldCode):
   # pylint: disable=too-many-locals
   # pylint: disable=too-many-branches
   # pylint: disable=too-many-statements

   #shared.fpOut.write("Entered FindNearbyWatercourse at point " + DisplayOS(point.x(), point.y()) + "\n")
   layerNum = -1
   geomPoint = QgsGeometry.fromPointXY(QgsPointXY(point))

   watercourseSegIDsFollowed = []

   # Find the watercourse network layer
   watercourseLayerFound = False
   for layerNum in range(len(shared.vectorInputLayersCategory)):
      if shared.vectorInputLayersCategory[layerNum] == INPUT_WATERCOURSE_NETWORK:
         watercourseLayerFound = True
         break

   # Safety check
   if not watercourseLayerFound:
      printStr = "ERROR: opening watercourse network layer\n"
      shared.fpOut.write(printStr)
      print(printStr)

      return -1

   # TODO make this a user setting
   numberToSearchFor = 3

   # Loop until we either hit the Rother, or cannot find a suitable nearby watercourse segment
   inWatercourse = False
   while True:
      # Find the nearest watercourse segments
      #shared.fpOut.write("At start of FindNearbyWatercourse loop: " + DisplayOS(point.x(), point.y()) + "\n")
      nearestIDs = shared.vectorInputLayerIndex[layerNum].nearestNeighbor(QgsPointXY(point), numberToSearchFor)
      #if len(nearestIDs) > 0:
         #shared.fpOut.write("Nearest watercourse segment IDs = " + str(nearestIDs) + "\n")
      request = QgsFeatureRequest().setFilterFids(nearestIDs)
      features = shared.vectorInputLayers[layerNum].getFeatures(request)

      distToPoint = []
      geomPoint = QgsGeometry.fromPointXY(QgsPointXY(point))

      for watercourseSeg in features:
         # Is this watercourse segment both close enough, and has not already been followed?
         geomSeg = watercourseSeg.geometry()
         nearPoint = geomSeg.nearestPoint(geomPoint)
         distanceToSeg = geomPoint.distance(nearPoint)
         segID = watercourseSeg.id()
         #shared.fpOut.write("Trying nearby watercourse segment with segID = " + str(segID) + " and distanceToSeg = " + "{:0.1f}".format(distanceToSeg) + " m\n")

         if distanceToSeg > shared.searchDist:
            # Too far away, so forget about this watercourse segment
            #shared.fpOut.write("Watercourse segment is too far away, max is " + "{:0.1f}".format(shared.searchDist) + " m, abandoning\n")
            continue

         if segID in watercourseSegIDsFollowed:
            # Already travelled, so forget about this watercourse segment
            #shared.fpOut.write("Already travelled, abandoning\n")
            continue

         # Is OK, so save the watercourse segment feature, the nearest point, and the distance
         distToPoint.append([watercourseSeg, nearPoint.asPoint(), distanceToSeg])

      # Did we find suitable a watercourse segments?
      if not distToPoint:
         # Nope
         #shared.fpOut.write("No suitable watercourse segments found\n")
         inWatercourse = False
         return 0

      # OK we have some possibly suitable watercourse segments
      #for n in range(len(distToPoint)):
         #shared.fpOut.write("Before " + str(n) + " " + str(distToPoint[n][0].id()) + " " + DisplayOS(distToPoint[n][1].x(), distToPoint[n][1].y()) + " " + str(distToPoint[n][2]) + " m\n")

      # Sort the list of untravelled watercourse segments, shortest distance first
      distToPoint.sort(key = lambda distPoint: distPoint[2])

      #for n in range(len(distToPoint)):
         #shared.fpOut.write("After " + (str(n) + " " + str(distToPoint[n][0].id()) + " " + DisplayOS(distToPoint[n][1].x(), distToPoint[n][1].y()) + " " + str(distToPoint[n][2]) + " m\n")

      flowRouted = False
      for thisWatercourseSeg in distToPoint:
         # Go through this list of untravelled watercourse segments till we find a suitable one
         feature = thisWatercourseSeg[0]
         featID = feature.id()
         #shared.fpOut.write("Trying nearby watercourse segment with feature ID " + str(featID) + "\n")

         localID = feature[OS_WATER_NETWORK_LOCAL_ID]
         #print(localID)
         #flds = feature.fields()
         #print(flds.names())
         #attrs = feature.attributes()
         #print(attrs)

         # Is this the Rother?
         watercourseName = feature[OS_WATER_NETWORK_NAME]

         watercourseName = str(watercourseName)  # Make sure that this is a string
         watercourseName = watercourseName.upper()
         #shared.fpOut.write("watercourseName = '" + watercourseName + "'\n")

         #if watercourseName.find(TARGET_RIVER) >= 0:
         # NOTE have no idea why some branches of the Rother are called "M" in the OS watercourse layer, maybe "M"  is "main channel"?
         #if watercourseName.find(TARGET_RIVER) >= 0 or watercourseName == "M":
         if watercourseName.find(TARGET_RIVER) >= 0:
            # Yes, flow has entered the Rother
            shared.fpOut.write("Flow from field " + flowFieldCode + " enters the " + TARGET_RIVER_NAME + " at " + DisplayOS(point.x(), point.y()) + " (" + str(watercourseName) + ")\n")
            AddFlowMarkerPoint(point, MARKER_ENTER_RIVER, flowFieldCode, -1)

            # We are done here
            return 1

         # This watercourse segment is not the Rother. Are we considering watercourses?
         if not shared.considerWatercourses:
            # We are not, so don't try to route flow along this watercourse segment
            #shared.fpOut.write("Watercourse not considered\n")
            continue

         # We are considering watercourses
         #geomFeat = feature.geometry()
         #linePoints = geomFeat.asPolyline()
         ##nPoints = len(linePoints)

         geomFeat = feature.geometry()
         if geomFeat.isMultipart():
            linePointsAll = geomFeat.asMultiPolyline()
         else:
            linePointsAll = [geomFeat.asPolyline()]

         linePoints = linePointsAll[0]

         firstPoint = linePoints[0]
         lastPoint = linePoints[-1]

         # The nearest point is an approximation: it is not necessarily a vertex of the line. So get the closest vertex of the line
         nearPoint, numNearpoint, _beforeNearpoint, _afterNearpoint, sqrDist = geomFeat.closestVertex(thisWatercourseSeg[1])

         #shared.fpOut.write("At " + DisplayOS(point.x(), point.y()) + ", an untravelled watercourse segment " + str(localID) + " found with nearest vertex " + "{:0.1f}".format(sqrt(sqrDist)) + " m away\n")

         #shared.fpOut.write("\tFirst vertex of watercourse segment is " + DisplayOS(firstPoint.x(), firstPoint.y()) + ", nearest vertex of watercourse segment is " + DisplayOS(nearPoint.x(), nearPoint.y()) + ", last vertex of watercourse segment is " + DisplayOS(lastPoint.x(), lastPoint.y()) + "\n")

         # Check the flow direction
         flowDirection = feature["flowDirection"]
         #shared.fpOut.write("\tFlow direction of this watercourse segment is " + flowDirection + "\n")

         if nearPoint == firstPoint and flowDirection != "inDirection":
            #shared.fpOut.write("Flow going wrong way in watercourse segment " + str(localID) + "\n")

            # Try the next watercourse segment
            continue

         elif nearPoint == lastPoint and flowDirection == "inDirection":
            #shared.fpOut.write("Flow going wrong way in watercourse segment " + str(localID) + "\n")

            # Try the next watercourse segment
            continue

         # We are flowing along at least part of this watercourse segment
         if flowDirection == "inDirection":
            for m in range(numNearpoint, len(linePoints)-1):
               thisPoint = linePoints[m]
               nextPoint = linePoints[m+1]

               AddFlowLine(thisPoint, nextPoint, FLOW_VIA_WATERCOURSE, flowFieldCode, -1)
               #shared.fpOut.write("AddFlowLine 1 from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to " + DisplayOS(nextPoint.x(), nextPoint.y()) + "\n")
         else:
            for m in range(numNearpoint, 1, -1):
               thisPoint = linePoints[m]
               nextPoint = linePoints[m-1]

               AddFlowLine(thisPoint, nextPoint, FLOW_VIA_WATERCOURSE, flowFieldCode, -1)
               #shared.fpOut.write("AddFlowLine 2 from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to " + DisplayOS(nextPoint.x(), nextPoint.y()) + "\n")

         # OK we have flow routed along this watercourse segment
         watercourseSegIDsFollowed.append(featID)
         flowRouted = True

         #shared.fpOut.write(feature.attributes())

         #fields = shared.vectorInputLayers[vectorNum].fields().toList()
         #for fld in fields:
            #shared.fpOut.write(fld.displayName())
         #shared.fpOut.write("")

         level = feature[OS_WATER_NETWORK_LEVEL]
         if level == "underground":
            typeName = MARKER_ENTER_CULVERT
            if watercourseName == NULL:
               watercourseName = "culvert"
         else:
            typeName = MARKER_ENTER_WATERCOURSE
            if watercourseName == NULL:
               watercourseName = "stream"

         #shared.fpOut.write("\tFlow from field " + flowFieldCode + " along watercourse segment with feature ID " + str(featID) + " '" + watercourseName + " " + str(localID) + "', from " + DisplayOS(point.x(), point.y()) + " to " + DisplayOS(lastPoint.x(), lastPoint.y()) + "\n")

         if not inWatercourse:
            AddFlowMarkerPoint(point, typeName, flowFieldCode, -1)

         # Set the end point of this watercourse segment to be the start point, ready for next time round the loop
         point = lastPoint

         # Don't bother looking at other watercourse segments since flow was routed along this watercourse segment
         inWatercourse = True
         break

      if not flowRouted:
         inWatercourse = False

         #printStr = "No suitable watercourse segment found"
         #shared.fpOut.write(printStr + "\n")
         #print(printStr)

         return 0

   return 0
#======================================================================================================================


#======================================================================================================================
#
# Finds the steeper of two road segments
#
#======================================================================================================================
#def FindSteepestSegment(firstPoint, nearPoint, lastPoint, elevDiffNearToFirst, elevDiffNearToLast):
   #geomFirstPoint = QgsGeometry.fromPointXY(QgsPointXY(firstPoint))
   #geomNearPoint = QgsGeometry.fromPointXY(QgsPointXY(nearPoint))
   #geomLastPoint = QgsGeometry.fromPointXY(QgsPointXY(lastPoint))

   ## Note that this calculates the straight-line distance, which will not be appropriate if the roads are very twisty
   #distAlongRoadNearToFirst = geomNearPoint.distance(geomFirstPoint)
   #distAlongRoadNearToLast = geomNearPoint.distance(geomLastPoint)

   #gradientNearToFirst = elevDiffNearToFirst / distAlongRoadNearToFirst
   #gradientNearToLast = elevDiffNearToLast / distAlongRoadNearToLast

   #if gradientNearToLast > gradientNearToFirst:
      #return True

   #return False
#======================================================================================================================


#======================================================================================================================
#
# Finds all adjacent grid cells which are lower than the supplied elevation, and adds them to a list (if not already present)
#
#======================================================================================================================
def CanOverflowTo(thisPoint, topElev, overflowCells):
   # pylint: disable=too-many-branches
   # pylint: disable=too-many-statements

   newOverflowCells = []

   # N
   adjX = thisPoint.x()
   adjY = thisPoint.y() + shared.resolutionOfDEM
   adjElev = GetRasterElev(adjX, adjY)

   if adjElev <= topElev:
      newPoint = QgsPointXY(adjX, adjY)
      if newPoint not in overflowCells:
         newOverflowCells.append(newPoint)

   # NE
   adjX = thisPoint.x() + shared.resolutionOfDEM
   adjY = thisPoint.y() + shared.resolutionOfDEM
   adjElev = GetRasterElev(adjX, adjY)

   if adjElev <= topElev:
      newPoint = QgsPointXY(adjX, adjY)
      if newPoint not in overflowCells:
         newOverflowCells.append(newPoint)

   # E
   adjX = thisPoint.x() + shared.resolutionOfDEM
   adjY = thisPoint.y()
   adjElev = GetRasterElev(adjX, adjY)

   if adjElev <= topElev:
      newPoint = QgsPointXY(adjX, adjY)
      if newPoint not in overflowCells:
         newOverflowCells.append(newPoint)

   # SE
   adjX = thisPoint.x() + shared.resolutionOfDEM
   adjY = thisPoint.y() - shared.resolutionOfDEM
   adjElev = GetRasterElev(adjX, adjY)

   if adjElev <= topElev:
      newPoint = QgsPointXY(adjX, adjY)
      if newPoint not in overflowCells:
         newOverflowCells.append(newPoint)

   # S
   adjX = thisPoint.x()
   adjY = thisPoint.y() - shared.resolutionOfDEM
   adjElev = GetRasterElev(adjX, adjY)

   if adjElev <= topElev:
      newPoint = QgsPointXY(adjX, adjY)
      if newPoint not in overflowCells:
         newOverflowCells.append(newPoint)

   # SW
   adjX = thisPoint.x() - shared.resolutionOfDEM
   adjY = thisPoint.y() - shared.resolutionOfDEM
   adjElev = GetRasterElev(adjX, adjY)

   if adjElev <= topElev:
      newPoint = QgsPointXY(adjX, adjY)
      if newPoint not in overflowCells:
         newOverflowCells.append(newPoint)

   # W
   adjX = thisPoint.x() - shared.resolutionOfDEM
   adjY = thisPoint.y()
   adjElev = GetRasterElev(adjX, adjY)

   if adjElev <= topElev:
      newPoint = QgsPointXY(adjX, adjY)
      if newPoint not in overflowCells:
         newOverflowCells.append(newPoint)

   # NW
   adjX = thisPoint.x() - shared.resolutionOfDEM
   adjY = thisPoint.y() + shared.resolutionOfDEM
   adjElev = GetRasterElev(adjX, adjY)

   if adjElev <= topElev:
      newPoint = QgsPointXY(adjX, adjY)
      if newPoint not in overflowCells:
         newOverflowCells.append(newPoint)

   return newOverflowCells
#======================================================================================================================


#======================================================================================================================
#
# Is there a ditch near this location? If so, route flow into this ditch until it can't go any further, or it reaches a stream
#
#======================================================================================================================
def FindNearbyDitch(point, flowFieldCode):
   # pylint: disable=too-many-locals
   # pylint: disable=too-many-branches
   # pylint: disable=too-many-statements

   #shared.fpOut.write("\tEntered FindNearbyDitch at point " + DisplayOS(point.x(), point.y()) + "\n")
   layerNum = -1
   geomPoint = QgsGeometry.fromPointXY(QgsPointXY(point))

   ditchSegIDsFollowed = []

   # Find the ditch network layer
   ditchLayerFound = False
   for layerNum in range(len(shared.vectorInputLayersCategory)):
      if shared.vectorInputLayersCategory[layerNum] == INPUT_DITCH_NETWORK:
         ditchLayerFound = True
         break

   # Safety check
   if not ditchLayerFound:
      printStr = "ERROR: opening ditch network layer\n"
      shared.fpOut.write(printStr)
      print(printStr)

      return -1

   # TODO make this a user setting
   numberToSearchFor = 3

   inDitch = False
   while True:
      # Find the nearest ditch segments
      #shared.fpOut.write("\tAt start of FindNearbyWatercourse loop: " + DisplayOS(point.x(), point.y()) + "\n")
      nearestIDs = shared.vectorInputLayerIndex[layerNum].nearestNeighbor(QgsPointXY(point), numberToSearchFor)

      #if len(nearestIDs) > 0:
         #shared.fpOut.write("\tNearest ditch segment IDs = " + str(nearestIDs) + "\n")

      request = QgsFeatureRequest().setFilterFids(nearestIDs)
      features = shared.vectorInputLayers[layerNum].getFeatures(request)

      distToPoint = []
      geomPoint = QgsGeometry.fromPointXY(QgsPointXY(point))

      for ditchSeg in features:
         # Is this ditch segment both close enough, and has not already been followed?
         geomSeg = ditchSeg.geometry()
         nearPoint = geomSeg.nearestPoint(geomPoint)
         distanceToSeg = geomPoint.distance(nearPoint)
         segID = ditchSeg.id()
         #shared.fpOut.write("\tTrying nearby ditch segment with segID = " + str(segID) + " and distanceToSeg = " + "{:0.1f}".format(distanceToSeg) + " m\n")

         if distanceToSeg > shared.searchDist:
            # Too far away, so forget about this ditch segment
            #shared.fpOut.write("\tDitch segment is too far away, max is " + "{:0.1f}".format(shared.searchDist) + " m, abandoning\n")
            continue

         if segID in ditchSegIDsFollowed:
            # Already travelled, so forget about this ditch segment
            #shared.fpOut.write("Already travelled, abandoning\n")
            continue

         # Is OK, so save the ditch segment feature, the nearest point, and the distance
         distToPoint.append([ditchSeg, nearPoint.asPoint(), distanceToSeg])

      # Did we find a suitable ditch segment?
      if not distToPoint:
         # Nope
         #shared.fpOut.write("\tNo suitable ditch segments found\n")
         inDitch = False
         return 0

      # OK we have some possibly suitable ditch segments
      #for n in range(len(distToPoint)):
         #shared.fpOut.write("Before " + str(n) + " " + str(distToPoint[n][0].id()) + " " + DisplayOS(distToPoint[n][1].x(), distToPoint[n][1].y()) + " " + str(distToPoint[n][2]) + " m\n")

      # Sort the list of untravelled ditch segments, shortest distance first
      distToPoint.sort(key = lambda distPoint: distPoint[2])

      #for n in range(len(distToPoint)):
         #shared.fpOut.write("After " + (str(n) + " " + str(distToPoint[n][0].id()) + " " + DisplayOS(distToPoint[n][1].x(), distToPoint[n][1].y()) + " " + str(distToPoint[n][2]) + " m\n")

      flowRouted = False
      for thisDitchSeg in distToPoint:
         # Go through this list of untravelled ditch segments till we find a suitable one
         feature = thisDitchSeg[0]
         featID = feature.id()
         localID = feature[DITCH_NETWORK_LOCAL_ID]
         desc = feature[DITCH_NETWORK_DESC]
         #shared.fpOut.write("\tTrying nearby ditch segment with feature ID " + str(featID) + " '" + str(localID) + "' '" + str(desc) + "'\n")

         #geomFeat = feature.geometry()
         #linePoints = geomFeat.asPolyline()
         ##nPoints = len(linePoints)

         geomFeat = feature.geometry()
         if geomFeat.isMultipart():
            linePointsAll = geomFeat.asMultiPolyline()
         else:
            linePointsAll = [geomFeat.asPolyline()]

         linePoints = linePointsAll[0]

         firstPoint = linePoints[0]
         lastPoint = linePoints[-1]

         # The nearest point is an approximation: it is not necessarily a vertex of the line. So get the closest vertex of the line
         nearPoint, numNearpoint, _numBeforeNearpoint, _numAfterNearpoint, sqrDist = geomFeat.closestVertex(thisDitchSeg[1])

         #shared.fpOut.write("At " + DisplayOS(point.x(), point.y()) + ", untravelled ditch segment with feature ID " + str(featID) + " '" + str(localID) + "' '" + str(desc) + "' found with nearest vertex " + "{:0.1f}".format(sqrt(sqrDist)) + " m away\n")

         #shared.fpOut.write("\tFirst vertex of ditch segment is " + DisplayOS(firstPoint.x(), firstPoint.y()) + ", nearest vertex of ditch segment is " + DisplayOS(nearPoint.x(), nearPoint.y()) + ", last vertex of ditch segment is " + DisplayOS(lastPoint.x(), lastPoint.y()) + "\n")

         # Get the flow direction
         firstPointElev = GetRasterElev(firstPoint.x(), firstPoint.y())
         lastPointElev = GetRasterElev(lastPoint.x(), lastPoint.y())

         flowFirstToLast = None
         if lastPointElev < firstPointElev:
            flowFirstToLast = True
            #shared.fpOut.write("\tFlow direction in this ditch segment is first to last\n")

         elif firstPointElev < lastPointElev:
            flowFirstToLast = False
            #shared.fpOut.write("\tFlow direction in this ditch segment is last to first\n")

         else:
            #shared.fpOut.write("\tThis ditch segment is level\n")
            return 0

         # Is the flow direction OK?
         if nearPoint == firstPoint and not flowFirstToLast:
            #shared.fpOut.write("\tFlow going wrong way in ditch segment " + str(localID) + "\n")

            # Try the next ditch segment
            continue

         elif nearPoint == lastPoint and flowFirstToLast:
            #shared.fpOut.write("\tFlow going wrong way in ditch segment " + str(localID) + "\n")

            # Try the next ditch segment
            continue

         # We are flowing along at least part of this ditch segment
         if flowFirstToLast:
            startPoint = linePoints[numNearpoint+1]
            AddFlowLine(point, startPoint, FLOW_VIA_DITCH, flowFieldCode, -1)
            #shared.fpOut.write("\tAddFlowLine from " + DisplayOS(point.x(), point.y()) + " to " + DisplayOS(startPoint.x(), startPoint.y()) + "\n")

            for m in range(numNearpoint+1, len(linePoints)-1):
               thisPoint = linePoints[m]
               nextPoint = linePoints[m+1]

               AddFlowLine(thisPoint, nextPoint, FLOW_VIA_DITCH, flowFieldCode, -1)
               #shared.fpOut.write("\tAddFlowLine 1 from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to " + DisplayOS(nextPoint.x(), nextPoint.y()) + "\n")

            lastPoint = linePoints[-1]
         else:
            startPoint = linePoints[numNearpoint-1]
            AddFlowLine(point, startPoint, FLOW_VIA_DITCH, flowFieldCode, -1)
            #shared.fpOut.write("\tAddFlowLine from " + DisplayOS(point.x(), point.y()) + " to " + DisplayOS(startPoint.x(), startPoint.y()) + "\n")

            for m in range(numNearpoint-1, 1, -1):
               thisPoint = linePoints[m]
               nextPoint = linePoints[m-1]

               AddFlowLine(thisPoint, nextPoint, FLOW_VIA_DITCH, flowFieldCode, -1)
               #shared.fpOut.write("\tAddFlowLine 2 from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to " + DisplayOS(nextPoint.x(), nextPoint.y()) + "\n")

            lastPoint = linePoints[0]

         # OK we have flow routed along this ditch segment
         ditchSegIDsFollowed.append(featID)
         flowRouted = True

         #shared.fpOut.write(feature.attributes())

         shared.fpOut.write("\tFlow from field " + flowFieldCode + " along ditch segment with feature ID " + str(featID) + " '" + str(localID) + "' '" + str(desc) + "', from " + DisplayOS(point.x(), point.y()) + " to " + DisplayOS(lastPoint.x(), lastPoint.y()) + "\n")

         if not inDitch:
            AddFlowMarkerPoint(point, MARKER_ENTER_DITCH, flowFieldCode, -1)

         # Set the end point of this ditch segment to be the start point, ready for next time round the loop
         point = lastPoint

         # Don't bother looking at other ditch segments since flow was routed along this ditch segment
         inDitch = True

         # Now look for a watercourse near here
         rtn = FindNearbyWatercourse(point, flowFieldCode)
         if rtn == -1:
            # Problem! Exit the program
            exit(-1)
         elif rtn == 1:
            # Flow entered a watercourse and reached the Rother. We are done here, so move on to the next field
            #shared.fpOut.write("Hit a watercourse and reached the Rother\n")

            return 1

         # Did not find a watercourse, so continue round the loop, look for another ditch segment
         break

      # Have left the main loop
      if not flowRouted:
         inDitch = False

         printStr = "\tNo suitable ditch segment found"
         shared.fpOut.write(printStr + "\n")

         return 0

   shared.fpOut.write("\treturn 1\n")
   return 1
#======================================================================================================================


#======================================================================================================================
#
# Finds the adjacent grid which is lowest and to which this field's flow has not already travelled
#
#======================================================================================================================
def FindLowestAdjacent(thisPoint):
   # pylint: disable=too-many-locals
   # pylint: disable=too-many-branches
   # pylint: disable=too-many-statements

   lowElev = float("inf")
   found = False
   newAdjX = -1
   newAdjY = -1
   
   # N
   adjX = thisPoint.x()
   adjY = thisPoint.y() + shared.resolutionOfDEM
   adjElev = GetRasterElev(adjX, adjY)

   #print("thispoint = " + str(DisplayOS(thisPoint.x(), thisPoint.y())) + ", trying N " + str(DisplayOS(adjX, adjY)) + " adjElev = " + str(adjElev))
   if adjElev < lowElev:
      adjPoint = QgsPointXY(adjX, adjY)
      if adjPoint not in shared.thisFieldFlowLine:
         found = True
         newAdjX = adjX
         newAdjY = adjY
         lowElev = adjElev

   # NE
   adjX = thisPoint.x() + shared.resolutionOfDEM
   adjY = thisPoint.y() + shared.resolutionOfDEM
   adjElev = GetRasterElev(adjX, adjY)

   #print("thispoint = " + str(DisplayOS(thisPoint.x(), thisPoint.y())) + ", trying NE " + str(DisplayOS(adjX, adjY)) + " adjElev = " + str(adjElev))
   if adjElev < lowElev:
      adjPoint = QgsPointXY(adjX, adjY)
      if adjPoint not in shared.thisFieldFlowLine:
         found = True
         newAdjX = adjX
         newAdjY = adjY
         lowElev = adjElev

   # E
   adjX = thisPoint.x() + shared.resolutionOfDEM
   adjY = thisPoint.y()
   adjElev = GetRasterElev(adjX, adjY)

   #print("thispoint = " + str(DisplayOS(thisPoint.x(), thisPoint.y())) + ", trying E " + str(DisplayOS(adjX, adjY)) + " adjElev = " + str(adjElev))
   if adjElev < lowElev:
      adjPoint = QgsPointXY(adjX, adjY)
      if adjPoint not in shared.thisFieldFlowLine:
         found = True
         newAdjX = adjX
         newAdjY = adjY
         lowElev = adjElev

   # SE
   adjX = thisPoint.x() + shared.resolutionOfDEM
   adjY = thisPoint.y() - shared.resolutionOfDEM
   adjElev = GetRasterElev(adjX, adjY)

   #print("thispoint = " + str(DisplayOS(thisPoint.x(), thisPoint.y())) + ", trying SE " + str(DisplayOS(adjX, adjY)) + " adjElev = " + str(adjElev))
   if adjElev < lowElev:
      adjPoint = QgsPointXY(adjX, adjY)
      if adjPoint not in shared.thisFieldFlowLine:
         found = True
         newAdjX = adjX
         newAdjY = adjY
         lowElev = adjElev

   # S
   adjX = thisPoint.x()
   adjY = thisPoint.y() - shared.resolutionOfDEM
   adjElev = GetRasterElev(adjX, adjY)

   #print("thispoint = " + str(DisplayOS(thisPoint.x(), thisPoint.y())) + ", trying S " + str(DisplayOS(adjX, adjY)) + " adjElev = " + str(adjElev))
   if adjElev < lowElev:
      adjPoint = QgsPointXY(adjX, adjY)
      if adjPoint not in shared.thisFieldFlowLine:
         found = True
         newAdjX = adjX
         newAdjY = adjY
         lowElev = adjElev

   # SW
   adjX = thisPoint.x() - shared.resolutionOfDEM
   adjY = thisPoint.y() - shared.resolutionOfDEM
   adjElev = GetRasterElev(adjX, adjY)

   #print("thispoint = " + str(DisplayOS(thisPoint.x(), thisPoint.y())) + ", trying SW " + str(DisplayOS(adjX, adjY)) + " adjElev = " + str(adjElev))
   if adjElev < lowElev:
      adjPoint = QgsPointXY(adjX, adjY)
      if adjPoint not in shared.thisFieldFlowLine:
         found = True
         newAdjX = adjX
         newAdjY = adjY
         lowElev = adjElev

   # W
   adjX = thisPoint.x() - shared.resolutionOfDEM
   adjY = thisPoint.y()
   adjElev = GetRasterElev(adjX, adjY)

   #print("thispoint = " + str(DisplayOS(thisPoint.x(), thisPoint.y())) + ", trying W " + str(DisplayOS(adjX, adjY)) + " adjElev = " + str(adjElev))
   if adjElev < lowElev:
      adjPoint = QgsPointXY(adjX, adjY)
      if adjPoint not in shared.thisFieldFlowLine:
         found = True
         newAdjX = adjX
         newAdjY = adjY
         lowElev = adjElev

   # NW
   adjX = thisPoint.x() - shared.resolutionOfDEM
   adjY = thisPoint.y() + shared.resolutionOfDEM
   adjElev = GetRasterElev(adjX, adjY)

   #print("thispoint = " + str(DisplayOS(thisPoint.x(), thisPoint.y())) + ", trying NW " + str(DisplayOS(adjX, adjY)) + " adjElev = " + str(adjElev))
   if adjElev < lowElev:
      adjPoint = QgsPointXY(adjX, adjY)
      if adjPoint not in shared.thisFieldFlowLine:
         found = True
         newAdjX = adjX
         newAdjY = adjY
         lowElev = adjElev
      
   return found, QgsPointXY(newAdjX, newAdjY), lowElev
#======================================================================================================================


