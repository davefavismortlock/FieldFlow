from math import sqrt

from qgis.core import NULL, QgsGeometry, QgsFeatureRequest, QgsPointXY

import shared
from shared import INPUT_PATH_NETWORK, PATH_DESC, INPUT_ROAD_NETWORK, OS_VECTORMAP_FEAT_CODE, OS_VECTORMAP_FEAT_DESC, OS_VECTORMAP_ROAD_NAME, OS_VECTORMAP_ROAD_NUMBER, INPUT_WATER_NETWORK, OS_WATER_NETWORK_LOCAL_ID, OS_WATER_NETWORK_NAME, TARGET_RIVER, MARKER_ENTER_RIVER, FLOW_VIA_STREAM, OS_WATER_NETWORK_LEVEL, MARKER_ENTER_CULVERT, MARKER_ENTER_STREAM, OUTPUT_FIELD_CODE
from utils import GetRasterElev, DisplayOS
from layers import AddFlowMarkerPoint, AddFlowLine


#======================================================================================================================
#
# Finds the adjacent grid cell with the steepest downhill gradient, to which this field's flow has not already travelled
#
#======================================================================================================================
def FindSteepestAdjacent(thisPoint, thisElev, geomPolygon = -1):
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
   geomThisPoint = QgsGeometry.fromPointXY(thisPoint)

   # TODO make this a user setting
   numberToSearchFor = 3

   # Now search for the nearest flowline segments
   nearestIDs = shared.outFlowLineLayerIndex.nearestNeighbor(thisPoint, numberToSearchFor)
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

   # OK we have some suitable flow line segments, sort the list of stream segments, shortest distance first
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

         # OK, the nearest point is an approximation: it is not necessarily a point in the line. So get the actual point in the line which is closest
         nearPoint, _numNearpoint, _beforeNearpoint, _afterNearpoint, sqrDist = geomFeat.closestVertex(flowLineSeg[1])

         #shared.fpOut.write("At " + DisplayOS(flowLineSeg[1].x(), flowLineSeg[1].y()) + ", flow line stream segment '" + str(featID) + "' was found with nearest point " + "{:0.1f}".format(sqrt(sqrDist)) + " m away\n")

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
# Is there a path near here?
#
#======================================================================================================================
def FindNearbyPath(point, flowFieldCode, alreadyAlongPath):
   # pylint: disable=too-many-locals

   #shared.fpOut.write("\tEntered FindNearbyPath at point " + DisplayOS(point.x(), point.y()))
   layerNum = -1
   geomPoint = QgsGeometry.fromPointXY(point)

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
   nearestIDs = shared.vectorInputLayerIndex[layerNum].nearestNeighbor(point, numberToSearchFor)
   #if len(nearestIDs) > 0:
      #print("Nearest path segment IDs (2) = " + str(nearestIDs))

   request = QgsFeatureRequest().setFilterFids(nearestIDs)
   features = shared.vectorInputLayers[layerNum].getFeatures(request)

   distToPoint = []
   geomPoint = QgsGeometry.fromPointXY(point)

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

         # OK, the nearest point is an approximation: it is not necessarily a point in the line. So get the actual point in the line which is closest
#         nearPoint, numNearpoint, beforeNearpoint, afterNearpoint, sqrDist = geomFeat.closestVertex(pathSeg[1])

         #shared.fpOut.write("At " + DisplayOS(point.x(), point.y()) + ", an untravelled path segment '" + str(featDesc) + "' was found with nearest point " + "{:0.1f}".format(sqrt(sqrDist)) + " m away" + "\n*** Does flow go over, under or along this path? Please add a field observation\n")

         if not alreadyAlongPath:
            shared.fpOut.write("At " + DisplayOS(point.x(), point.y()) + ", an untravelled path/track segment '" + str(featDesc) + "' was found with nearest point " + "{:0.1f}".format(pathSeg[2]) + " m away" + "\n*** Does flow from field " + str(flowFieldCode) + " go over, under or along this path/track? Please add a field observation\n")

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

   #shared.fpOut.write("Searching for field observations between " + DisplayOS(xMin, yMin) + " and " + DisplayOS(xMax, yMax))

   for indx in range(numObs):
      if indx in shared.thisFieldFieldObsAlreadyFollowed:
         continue

      xObs = shared.fieldObservationFlowFrom[indx].x()
      yObs = shared.fieldObservationFlowFrom[indx].y()

      if xMin < xObs < xMax and yMin < yObs < yMax:
         shared.fpOut.write("Field observation found for location " + DisplayOS(shared.fieldObservationFlowFrom[indx].x(), shared.fieldObservationFlowFrom[indx].y()) + " '" + shared.fieldObservationBehaviour[indx] + " " + shared.fieldObservationCategory[indx] + ", " + shared.fieldObservationDescription[indx] + "'\n")

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
   geomPoint = QgsGeometry.fromPointXY(point)

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
   nearestIDs = shared.vectorInputLayerIndex[layerNum].nearestNeighbor(point, numberToSearchFor)
   #if len(nearestIDs) > 0:
      #print("Nearest road segment IDs (2) = " + str(nearestIDs))

   request = QgsFeatureRequest().setFilterFids(nearestIDs)
   features = shared.vectorInputLayers[layerNum].getFeatures(request)

   distToPoint = []
   geomPoint = QgsGeometry.fromPointXY(point)

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

         # The nearest point may or may not be a vertex of the line. So get the closest vertex in the line
#         nearPoint, numNearpoint, beforeNearpoint, afterNearpoint, sqrDist = geomFeat.closestVertex(roadSeg[1])

         #shared.fpOut.write("At " + DisplayOS(point.x(), point.y()) + ", an untravelled road segment '" + str(featDesc) + "' '" + str(roadName) + "' '" + str(roadNumber) + "' was found with nearest point " + "{:0.1f}".format(sqrt(sqrDist)) + " m away" + "\n*** Does flow go over, under or along this road? Please add a field observation\n")

         #if not alreadyAlongRoad:
            #shared.fpOut.write("At " + DisplayOS(point.x(), point.y()) + ", an untravelled road segment '" + str(featCode) + "' '" + str(featDesc) + "' '" + str(roadName) + "' '" + str(roadNumber) + "' was found with nearest point " + "{:0.1f}".format(roadSeg[2]) + " m away" + "\n*** Does flow from field " + str(flowFieldCode) + " go over, under or along this road? Please add a field observation\n")

   return 1
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
   shared.fpOut.write("\t" + str(roadBoundingBox) + "\n")

   intersectingStreams = shared.vectorInputLayerIndex[layerNum].intersects(roadBoundingBox)

   if not intersectingStreams:
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
         shared.fpOut.write("intersectPoint = " + DisplayOS(intersectPoint.x(), intersectPoint.y()) + "\n")

         intersectPoints.append(intersectPoint)

   return 1, intersectPoints
#======================================================================================================================


#======================================================================================================================
#
# Is there a stream near this location? If so, route flow into this stream until it reaches the Rother
#
#======================================================================================================================
def FindNearbyStream(point, flowFieldCode):
   # pylint: disable=too-many-locals
   # pylint: disable=too-many-branches
   # pylint: disable=too-many-statements

   #shared.fpOut.write("Entered FindNearbyStream at point " + DisplayOS(point.x(), point.y()) + "\n")
   layerNum = -1
   geomPoint = QgsGeometry.fromPointXY(point)

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
   #inStream = False
   while True:
      # Find the nearest stream segments
      #shared.fpOut.write("At start of FindNearbyStream loop: " + DisplayOS(point.x(), point.y()) + "\n")
      nearestIDs = shared.vectorInputLayerIndex[layerNum].nearestNeighbor(point, numberToSearchFor)
      #if len(nearestIDs) > 0:
         #shared.fpOut.write("Nearest stream segment IDs = " + str(nearestIDs) + "\n")
      request = QgsFeatureRequest().setFilterFids(nearestIDs)
      features = shared.vectorInputLayers[layerNum].getFeatures(request)

      distToPoint = []
      geomPoint = QgsGeometry.fromPointXY(point)

      for streamSeg in features:
         # Is this stream segment both close enough, and has not already been followed?
         geomSeg = streamSeg.geometry()
         nearPoint = geomSeg.nearestPoint(geomPoint)
         distanceToSeg = geomPoint.distance(nearPoint)
         segID = streamSeg.id()
         #shared.fpOut.write("Trying nearby stream segment with segID = " + str(segID) + " and distanceToSeg = " + "{:0.1f}".format(distanceToSeg) + " m\n")

         if distanceToSeg > shared.searchDist:
            # Too far away, so forget about this stream segment
            #shared.fpOut.write("Too far away, max is " + "{:0.1f}".format(shared.searchDist) + " m, abandoning\n")
            continue

         if segID in streamSegIDsFollowed:
            # Already travelled, so forget about this stream segment
            #shared.fpOut.write("Already travelled, abandoning\n")
            continue

         # Is OK, so save the stream segment feature, the nearest point, and the distance
         distToPoint.append([streamSeg, nearPoint.asPoint(), distanceToSeg])

      # Did we find suitable stream segments?
      if not distToPoint:
         # Nope
         #shared.fpOut.write("No suitable stream segments found\n")
         return 0

      # OK we have some possibly suitable stream segments
      #for n in range(len(distToPoint)):
         #shared.fpOut.write("Before " + str(n) + " " + str(distToPoint[n][0].id()) + " " + DisplayOS(distToPoint[n][1].x(), distToPoint[n][1].y()) + " " + str(distToPoint[n][2]) + " m\n")

      # Sort the list of untravelled stream segments, shortest distance first
      distToPoint.sort(key = lambda distPoint: distPoint[2])

      #for n in range(len(distToPoint)):
         #shared.fpOut.write("After " + (str(n) + " " + str(distToPoint[n][0].id()) + " " + DisplayOS(distToPoint[n][1].x(), distToPoint[n][1].y()) + " " + str(distToPoint[n][2]) + " m\n")

      flowRouted = False
      for thisStreamSeg in distToPoint:
         # Go through this list of untravelled stream segments till we find a suitable one
         feature = thisStreamSeg[0]
         featID = feature.id()
         shared.fpOut.write("Trying nearby stream segment with feature ID " + str(featID) + "\n")

         localID = feature[OS_WATER_NETWORK_LOCAL_ID]
         #print(localID)
         #flds = feature.fields()
         #print(flds.names())
         #attrs = feature.attributes()
         #print(attrs)

         # Is this the Rother?
         streamName = feature[OS_WATER_NETWORK_NAME]

         streamName = str(streamName)  # Make sure that this is a string
         streamName = streamName.upper()
         shared.fpOut.write("streamName = '" + streamName + "'\n")

#         if streamName.find(TARGET_RIVER) >= 0:
         if streamName.find(TARGET_RIVER) >= 0 or streamName == "M":
            # Yes, flow has entered the Rother
            shared.fpOut.write("Flow from field " + flowFieldCode + " enters the River Rother at " + DisplayOS(point.x(), point.y()) + "\n")
            AddFlowMarkerPoint(point, MARKER_ENTER_RIVER, flowFieldCode, -1)

            # We are done here
            return 1

         # This stream segment is not the Rother. Are we considering streams?
         if not shared.considerStreams:
            # We are not, so don't try to route flow along this stream segment
            #shared.fpOut.write("Stream not considered\n")
            continue

         # We are considering streams
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

         # OK, the nearest point is an approximation: it is not necessarily a point in the line. So get the actual point in the line which is closest
         nearPoint, numNearpoint, _beforeNearpoint, _afterNearpoint, sqrDist = geomFeat.closestVertex(thisStreamSeg[1])

         #shared.fpOut.write("At " + DisplayOS(point.x(), point.y()) + ", an untravelled stream segment " + str(localID) + " found with nearest point " + "{:0.1f}".format(sqrt(sqrDist)) + " m away\n")

         #shared.fpOut.write("\tFirst point of stream segment is " + DisplayOS(firstPoint.x(), firstPoint.y()) + "\n")
         #shared.fpOut.write("\tNearest point of stream segment is " + DisplayOS(nearPoint.x(), nearPoint.y()) + "\n")
         #shared.fpOut.write("\tLast point of stream segment is " + DisplayOS(lastPoint.x(), lastPoint.y()) + "\n")

         # Check the flow direction
         flowDirection = feature["flowDirection"]
         shared.fpOut.write("\tFlow direction of this stream segment is " + flowDirection + "\n")

         if nearPoint == firstPoint and flowDirection != "inDirection":
            #shared.fpOut.write("Flow going wrong way in stream segment " + str(localID) + "\n")

            # Try the next stream segment
            continue

         elif nearPoint == lastPoint and flowDirection == "inDirection":
            #shared.fpOut.write("Flow going wrong way in stream segment " + str(localID) + "\n")

            # Try the next stream segment
            continue

         # We are flowing along at least part of this stream segment
         if flowDirection == "inDirection":
            for m in range(numNearpoint, len(linePoints)-1):
               thisPoint = linePoints[m]
               nextPoint = linePoints[m+1]

               AddFlowLine(thisPoint, nextPoint, FLOW_VIA_STREAM, flowFieldCode, -1)
               #shared.fpOut.write("AddFlowLine 1 from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to " + DisplayOS(nextPoint.x(), nextPoint.y()) + "\n")
         else:
            for m in range(numNearpoint, 1, -1):
               thisPoint = linePoints[m]
               nextPoint = linePoints[m-1]

               AddFlowLine(thisPoint, nextPoint, FLOW_VIA_STREAM, flowFieldCode, -1)
               #shared.fpOut.write("AddFlowLine 2 from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to " + DisplayOS(nextPoint.x(), nextPoint.y()) + "\n")

         # OK we have flow routed along this stream segment
         streamSegIDsFollowed.append(featID)
         flowRouted = True
         #inStream = True

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

         shared.fpOut.write("Flow from field " + flowFieldCode + " enters the OS " + streamName + " segment " + str(localID) + " at " + DisplayOS(point.x(), point.y()) + " and leaves it at " + DisplayOS(lastPoint.x(), lastPoint.y()) + "\n")
         #shared.fpOut.write("======")

         AddFlowMarkerPoint(point, typeName, flowFieldCode, -1)

         # Set the end point of this stream segment to be the start point, ready for next time round the loop
         point = lastPoint

         # Don't bother looking at other stream segments since flow was routed along this stream segment
         break

      if not flowRouted:
         printStr = "No suitable stream segment found"
         shared.fpOut.write(printStr)
         print(printStr)

         return 0

   return 0
#======================================================================================================================


#======================================================================================================================
#
# Finds the steeper of two road segments
#
#======================================================================================================================
def FindSteepestSegment(firstPoint, nearPoint, lastPoint, elevDiffNearToFirst, elevDiffNearToLast):
   geomFirstPoint = QgsGeometry.fromPointXY(firstPoint)
   geomNearPoint = QgsGeometry.fromPointXY(nearPoint)
   geomLastPoint = QgsGeometry.fromPointXY(lastPoint)

   # Note that this calculates the straight-line distance, which will not be appropriate if the roads are very twisty
   distAlongRoadNearToFirst = geomNearPoint.distance(geomFirstPoint)
   distAlongRoadNearToLast = geomNearPoint.distance(geomLastPoint)

   gradientNearToFirst = elevDiffNearToFirst / distAlongRoadNearToFirst
   gradientNearToLast = elevDiffNearToLast / distAlongRoadNearToLast

   if gradientNearToLast > gradientNearToFirst:
      return True

   return False
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
