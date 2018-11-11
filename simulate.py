from __future__ import print_function

from math import sqrt

from qgis.core import QgsRaster, QgsFeature, QgsFeatureRequest, QgsGeometry, QgsPoint, QgsRectangle     # NULL,
#from qgis.gui import QgsMapCanvasLayer    #, QgsMapToolPan, QgsMapToolZoom

import shared
from shared import INPUT_DIGITAL_ELEVATION_MODEL, FIELD_OBS_CATEGORY_ROAD, FIELD_OBS_BEHAVIOUR_ALONG, MARKER_ROAD, FIELD_OBS_CATEGORY_PATH, MARKER_PATH, FIELD_OBS_CATEGORY_BOUNDARY, MARKER_FIELD_BOUNDARY, FIELD_OBS_CATEGORY_CULVERT, MARKER_ENTER_CULVERT, INPUT_ROAD_NETWORK, OS_VECTORMAP_FEAT_CODE, OS_VECTORMAP_FEAT_DESC, OS_VECTORMAP_ROAD_NAME, OS_VECTORMAP_ROAD_NUMBER, NEAR_POINT, FIRST_POINT, LAST_POINT, MERGED_WITH_ADJACENT_FLOWLINE, FLOW_VIA_ROAD, INPUT_PATH_NETWORK, PATH_DESC, PREV_POINT, THIS_POINT, POST_POINT, FLOW_VIA_PATH, INPUT_FIELD_BOUNDARIES, CONNECTED_FIELD_ID, FLOW_VIA_BOUNDARY, FLOW_DOWN_STEEPEST, BLIND_PIT
from layers import addFlowMarkerPoint, addFlowLine
from searches import FindSteepestAdjacent, FindSegmentIntersectionWithStream, FindNearbyStream, FindSteepestSegment, FindNearbyFlowLine, FindNearbyFieldObservation, CanOverflowTo
from utils import pointsOnLine, centroidOfContainingDEMCell, displayOS, getRasterElev, calcZCrossProduct

# pylint: disable=too-many-lines


#======================================================================================================================
#
# Returns the coords (external CRS) of the centroid of the pixel containing the highest point on a field boundary
#
#======================================================================================================================
def getHighestPointOnFieldBoundary(fieldBoundary):
   # pylint: disable=too-many-locals
   # pylint: disable=too-many-nested-blocks

   maxElev = 0       # sys.float_info.min
   maxElevX = -1
   maxElevY = -1

   geom = fieldBoundary.constGeometry()
   #shared.fpOut.write(geom.wkbType())
   poly = geom.asPolygon()
   #shared.fpOut.write(poly)

   for i in range(len(poly)):
      for j in range(len(poly[i]) - 1):
         thisBoundaryPointX = poly[i][j][0]
         thisBoundaryPointY = poly[i][j][1]

         nextBoundaryPointX = poly[i][j+1][0]
         nextBoundaryPointY = poly[i][j+1][1]

         inBetweenPoints = pointsOnLine(QgsPoint(thisBoundaryPointX, thisBoundaryPointY), QgsPoint(nextBoundaryPointX, nextBoundaryPointY), shared.resolutionOfDEM)
         #shared.fpOut.write("From " + displayOS(thisBoundaryPointX, thisBoundaryPointY) + " to " + displayOS(nextBoundaryPointX, nextBoundaryPointY))
         #shared.fpOut.write("in-between points are " + str(inBetweenPoints))
         #shared.fpOut.write("")

         for boundaryPoint in inBetweenPoints:
            # Search all raster layers
            for layerNum in range(len(shared.rasterInputLayersCategory)):
               if shared.rasterInputLayersCategory[layerNum] == INPUT_DIGITAL_ELEVATION_MODEL:
                  # OK, this is our raster elevation data
                  provider = shared.rasterInputData[layerNum][1][0]
                  xSize = shared.rasterInputData[layerNum][1][1]
                  ySize = shared.rasterInputData[layerNum][1][2]
                  extent = shared.rasterInputData[layerNum][1][5]
                  dpi = shared.rasterInputData[layerNum][1][6]

                  # We have the point on the field boundary, but this almost certainly is not the same as the centroid of the containing pixel. So find the coords of this centroid
                  pixelCentroidPoint = centroidOfContainingDEMCell(boundaryPoint.x(), boundaryPoint.y())
                  #shared.fpOut.write("{", boundaryPoint.x(), ", ", boundaryPoint.y(), "} and {", pixelCentroidPoint.x(), ", ", pixelCentroidPoint.y(), "}")

                  # Now look up the elevation value at the centroid point
                  result = provider.identify(pixelCentroidPoint, QgsRaster.IdentifyFormatValue, extent, xSize, ySize, dpi)
                  error = result.error()
                  if not error.isEmpty() or not result.isValid():
                     shared.fpOut.write(error.summary())
                     return -1, -1, -1

                  # We have a valid result, so get the elevation (is the first in the list, since we have only a single band)
                  value = result.results()
                  elevPair = value.items()
                  elev = elevPair[0][1]

                  # However some results are from a 'wrong' sheet (i.e. a sheet which does not contain this point), so ignore these results
                  if elev != None:
                     if elev > maxElev:
                        maxElev = elev
                        maxElevX = pixelCentroidPoint.x()
                        maxElevY = pixelCentroidPoint.y()

   return maxElevX, maxElevY, maxElev
#======================================================================================================================


#======================================================================================================================
#
# Routes flow through a field observation of some landscape element
#
# Return values are:
# -1 = problem
#  0 = continue downhill
#  1 = hit blind pit
#  2 = hit stream
#  3 = merged with pre-existing flowline
#
#======================================================================================================================
def flowViaFieldObservation(indx, fieldCode, thisPoint, elev):
   # pylint: disable=too-many-return-statements
   # pylint: disable=too-many-branches

   #shared.fpOut.write(displayOS(thisPoint.x(), thisPoint.y()), displayOS(shared.fieldObservationFlowFrom[indx].x(), shared.fieldObservationFlowFrom[indx].y()))
   #shared.fpOut.write(shared.fieldObservationFlowTo)
   if not shared.fieldObservationFlowTo[indx]:
      # The outflow location is not known, so we have flow along a road or along a path
      if shared.fieldObservationCategory[indx] == FIELD_OBS_CATEGORY_ROAD and shared.fieldObservationBehaviour[indx] == FIELD_OBS_BEHAVIOUR_ALONG:
         #shared.fpOut.write("Flow along road")
         addFlowMarkerPoint(thisPoint, MARKER_ROAD, fieldCode, -1)

         rtn, point = flowAlongVectorRoad(indx, fieldCode, thisPoint)
         if rtn == -1:
            # A problem! Exit the program
            exit (-1)

         elif rtn == 1:
            # Flow has hit a blind pit
            return 1, point

         elif rtn == 2:
            # Flow has hit a stream
            return 2, point

         elif rtn == 3:
            # Flow has merged with pre-existing flow
            return 3, point

         else:
            # Carry on from this point
            return 0, point

      elif shared.fieldObservationCategory[indx] == FIELD_OBS_CATEGORY_PATH and shared.fieldObservationBehaviour[indx] == FIELD_OBS_BEHAVIOUR_ALONG:
         #shared.fpOut.write("Flow along path")
         addFlowMarkerPoint(thisPoint, MARKER_PATH, fieldCode, -1)

         rtn, point = flowAlongVectorPath(indx, fieldCode, thisPoint)
         #shared.fpOut.write("Returned from flowAlongVectorPath(), rtn = " + str(rtn) + "\n")
         if rtn == -1:
            # Either Problem! Exit the program
            exit (-1)

         elif rtn == 1:
            # Flow has hit a blind pit, or we have a problematic field observation
            return 1, point

         elif rtn == 2:
            # Flow has hit a stream
            return 2, point

         elif rtn == 3:
            # Flow has merged with pre-existing flow
            return 3, point

         else:
            # Carry on from this point
            return 0, point

      elif shared.fieldObservationCategory[indx] == FIELD_OBS_CATEGORY_BOUNDARY and shared.fieldObservationBehaviour[indx] == FIELD_OBS_BEHAVIOUR_ALONG:
         #shared.fpOut.write("Flow along boundary\n")
         addFlowMarkerPoint(thisPoint, MARKER_FIELD_BOUNDARY, fieldCode, -1)

         rtn, point = flowAlongVectorFieldBoundary(indx, fieldCode, thisPoint)
         if rtn == -1:
            # Problem! Exit the program
            exit (-1)

         elif rtn == 1:
            # Flow has hit a blind pit
            return 1, point

         elif rtn == 2:
            # Flow has hit a stream
            return 2, point

         elif rtn == 3:
            # Flow has merged with pre-existing flow
            return 3, point

         else:
            # Carry on from this point
            return 0, point

      else:
         printStr = "ERROR: must have a 'To' location for field observation " + str(indx) + " '" + shared.fieldObservationCategory[indx] + shared.fieldObservationBehaviour[indx] + "' '" + shared.fieldObservationDescription[indx] + "', in flow from field " + str(fieldCode) + " at "+ displayOS(shared.fieldObservationFlowFrom[indx].x(), shared.fieldObservationFlowFrom[indx].y()) + "\n"
         shared.fpOut.write(printStr)
         print(printStr)

         return -1, -1

   # Show some marker points
   if shared.fieldObservationCategory[indx] == FIELD_OBS_CATEGORY_CULVERT:
      addFlowMarkerPoint(QgsPoint(shared.fieldObservationFlowFrom[indx].x(), shared.fieldObservationFlowFrom[indx].y()), MARKER_ENTER_CULVERT, fieldCode, -1)
   elif shared.fieldObservationCategory[indx] == FIELD_OBS_CATEGORY_PATH:
      addFlowMarkerPoint(QgsPoint(shared.fieldObservationFlowFrom[indx].x(), shared.fieldObservationFlowFrom[indx].y()), MARKER_PATH, fieldCode, -1)
   elif shared.fieldObservationCategory[indx] == FIELD_OBS_CATEGORY_ROAD:
      addFlowMarkerPoint(QgsPoint(shared.fieldObservationFlowFrom[indx].x(), shared.fieldObservationFlowFrom[indx].y()), MARKER_ROAD, fieldCode, -1)

   printStr = "Flow from field " + fieldCode + " routed via '" + shared.fieldObservationBehaviour[indx] + " " + shared.fieldObservationCategory[indx] + " " + shared.fieldObservationDescription[indx] + "' from " + displayOS(thisPoint.x(), thisPoint.y())
   if thisPoint != shared.fieldObservationFlowFrom[indx]:
      printStr += " via " + displayOS(shared.fieldObservationFlowFrom[indx].x(), shared.fieldObservationFlowFrom[indx].y())
   printStr += " to " + displayOS(shared.fieldObservationFlowTo[indx].x(), shared.fieldObservationFlowTo[indx].y())
   printStr += "\n"
   shared.fpOut.write(printStr)

   shared.thisFieldFieldObsAlreadyFollowed.append(indx)

   if thisPoint != shared.fieldObservationFlowFrom[indx]:
      addFlowLine(thisPoint, shared.fieldObservationFlowFrom[indx], " near to " + shared.fieldObservationDescription[indx], fieldCode, elev)
   addFlowLine(shared.fieldObservationFlowFrom[indx], shared.fieldObservationFlowTo[indx], shared.fieldObservationDescription[indx], fieldCode, -1)

   ## TEST add intermediate points to thisFieldFlowLine and thisFieldFlowLineFieldCode, to prevent backtracking
   #tempPoints = []
   #if thisPoint != shared.fieldObservationFlowFrom[indx]:
      #tempPoints += pointsOnLine(thisPoint, shared.fieldObservationFlowFrom[indx], shared.resolutionOfDEM)
   #tempPoints += pointsOnLine(shared.fieldObservationFlowFrom[indx], shared.fieldObservationFlowTo[indx], shared.resolutionOfDEM)

   #inBetweenPoints = []
   #for point in tempPoints:
      #inBetweenPoints.append(centroidOfContainingDEMCell(point.x(), point.y()))

   #inBetweenPointsFieldCode = [fieldCode] * len(inBetweenPoints)

   #shared.thisFieldFlowLine += inBetweenPoints
   #shared.thisFieldFlowLineFieldCode += inBetweenPointsFieldCode

   #printStr = ""
   #for i in shared.thisFieldFlowLine:
      #printStr += displayOS(i.x(), i.y())
      #printStr += " "
   #shared.fpOut.write(printStr)

   return 0, shared.fieldObservationFlowTo[indx]
#======================================================================================================================


#======================================================================================================================
#
# Routes flow downhill along a vector representation of a road
#
#======================================================================================================================
def flowAlongVectorRoad(indx, fieldCode, thisPoint):
   # pylint: disable=too-many-locals
   # pylint: disable=too-many-nested-blocks
   # pylint: disable=too-many-return-statements
   # pylint: disable=too-many-branches
   # pylint: disable=too-many-statements

   obsCategory = shared.fieldObservationCategory[indx]
   obsBehaviour = shared.fieldObservationBehaviour[indx]
   obsDesc = shared.fieldObservationDescription[indx]

   shared.thisFieldFieldObsAlreadyFollowed.append(indx)

   #shared.fpOut.write("Entered flowAlongVectorRoad at point " + displayOS(thisPoint.x(), thisPoint.y()))
   layerNum = -1
   #geomPoint = QgsGeometry.fromPoint(thisPoint)

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

      return -1, -1

   # TODO make this a user setting
   numberToSearchFor = 4

   while True:
      # Find the nearest road segments
      firstTime = True

      #shared.fpOut.write("Start of flowAlongVectorRoad loop at " + displayOS(thisPoint.x(), thisPoint.y()))
      nearestIDs = shared.vectorInputIndex[layerNum].nearestNeighbor(thisPoint, 3)
      request = QgsFeatureRequest().setFilterFids(nearestIDs)
      features = shared.vectorInputLayers[layerNum].getFeatures(request)

      distToPoint = []
      geomPoint = QgsGeometry.fromPoint(thisPoint)

      for roadSeg in features:
         # Is this road segment both close enough, and has not already been tried?
         geomSeg = roadSeg.geometry()
         nearPoint = geomSeg.nearestPoint(geomPoint)
         distanceToSeg = geomPoint.distance(nearPoint)
         segID = roadSeg.id()
         #shared.fpOut.write("\troad segID = " + str(segID) + ", distanceToSeg = " + str(distanceToSeg) + "\n")

         if distanceToSeg > shared.searchDist:
            # Too far away, so forget about this road segment
            shared.fpOut.write("\tToo far away (" + str(distanceToSeg) + " m) for road segID = " + str(segID) + "\n")

            continue

         if segID in shared.thisFieldRoadSegIDsTried:
            # Aready travelled, so forget about this road segment
            #shared.fpOut.write("\tAlready travelled for road segID = " + str(segID) + "\n")

            continue

         # Is OK, so save the road segment feature, the nearest point, and the distance
         distToPoint.append([roadSeg, nearPoint.asPoint(), distanceToSeg])

      # Did we any find suitable road segments?
      if not distToPoint:
         # Nope
         #shared.fpOut.write("Flow along road from field " + str(fieldCode) + " ends at " + displayOS(thisPoint.x(), thisPoint.y()) + "\n*** Please add a field observation\n")
         return 1, thisPoint

      # OK we have some possibly suitable road segments
      #for n in range(len(distToPoint)):
         #shared.fpOut.write("\tBefore " + str(n) + " " + str(distToPoint[n][0].id()) + " " + displayOS(distToPoint[n][1].x(), distToPoint[n][1].y()) + " " + str(distToPoint[n][2]) + " m\n")

      # Sort the list of untravelled road segments, shortest distance first
      distToPoint.sort(key = lambda distPoint: distPoint[2])

      #for n in range(len(distToPoint)):
         #shared.fpOut.write("\tAfter " + str(n) + " " + str(distToPoint[n][0].id()) + " " + displayOS(distToPoint[n][1].x(), distToPoint[n][1].y()) + " " + str(distToPoint[n][2]) + " m\n")

      flowRouted = False
      for n in range(len(distToPoint)):
         # Go through this list of untravelled road segments till we find a suitable one
         feature = distToPoint[n][0]
         nearPoint = distToPoint[n][1]
         distToNearPoint = distToPoint[n][2]
         featID = feature.id()
         #shared.fpOut.write("\tTrying road seg ID " + str(featID) + "\n")

         featCode = feature[OS_VECTORMAP_FEAT_CODE]
         featDesc = feature[OS_VECTORMAP_FEAT_DESC]
         roadName = feature[OS_VECTORMAP_ROAD_NAME]
         roadNumber = feature[OS_VECTORMAP_ROAD_NUMBER]

         geomFeat = feature.geometry()
         linePoints = geomFeat.asPolyline()
         nPoints = len(linePoints)

         firstPoint = linePoints[0]
         lastPoint = linePoints[-1]

         #shared.fpOut.write("\tAt " + displayOS(thisPoint.x(), thisPoint.y()) +", trying untravelled road segment " + str(featID) + " '" + str(featDesc) + "' '" + str(roadName) + "' '" + str(roadNumber) + "', which has nearest point " + "{:0.1f}".format(distToNearPoint) + " m away at " + displayOS(nearPoint.x(), nearPoint.y()) + "\n")

         #shared.fpOut.write("\tFirst point of road segment is " + displayOS(firstPoint.x(), firstPoint.y()) + "\n")
         #shared.fpOut.write("\tNearest point of road segment is " + displayOS(nearPoint.x(), nearPoint.y()) + "\n")
         #shared.fpOut.write("\tLast point of road segment is " + displayOS(lastPoint.x(), lastPoint.y()) + "\n")

         # If there is a choice, then find out which direction along the road has the steepest downhill slope
         flowToFirstPoint = False
         flowToLastPoint = False
         if nearPoint == firstPoint:
            # The nearest point is the same as the first point
            numNearPoint = 0

            elevFirstPoint = getRasterElev(firstPoint.x(), firstPoint.y())
            elevLastPoint = getRasterElev(lastPoint.x(), lastPoint.y())

            #shared.fpOut.write("A " + str(elevFirstPoint) + " " + str(elevLastPoint) + "\n")

            if elevFirstPoint > elevLastPoint:
               # Flow to last point
               flowToLastPoint = True
               #shared.fpOut.write("Flow to last point\n")

         elif nearPoint == lastPoint:
            # The nearest point is the same as the last point
            numNearPoint = len(linePoints) - 1

            elevFirstPoint = getRasterElev(firstPoint.x(), firstPoint.y())
            elevLastPoint = getRasterElev(lastPoint.x(), lastPoint.y())

            #shared.fpOut.write("B " + str(elevFirstPoint) + " " + str(elevFirstPoint) + "\n")

            if elevLastPoint > elevFirstPoint:
               # Flow to first point
               flowToFirstPoint = True
               #shared.fpOut.write("Flow to first point\n")
         else:
            # The nearest point is not a point in the line, so we need to insert it. First get the closest vertex
            linePoints = geomFeat.asPolyline()
            nPoints = len(linePoints)
            #for n in range(nPoints):
               #shared.fpOut.write(str(n) + " " + displayOS(linePoints[n].x(), linePoints[n].y()) + "\n")
            #shared.fpOut.write("\n")

            dist, p2, numPt = geomFeat.closestSegmentWithContext(nearPoint)
            if not geomFeat.insertVertex(nearPoint.x(), nearPoint.y(), numPt):
               # Error, could not insert vertex
               return -1, -1

            linePoints = geomFeat.asPolyline()
            nPoints = len(linePoints)
            #for n in range(nPoints):
               #shared.fpOut.write(str(n) + " " + displayOS(linePoints[n].x(), linePoints[n].y()) + "\n")
            #shared.fpOut.write("\n")

            numNearPoint = numPt
            #shared.fpOut.write("numNearPoint = " + str(numNearPoint) + "\n")

            elevFirstPoint = getRasterElev(firstPoint.x(), firstPoint.y())
            elevNearPoint = getRasterElev(nearPoint.x(), nearPoint.y())
            elevLastPoint = getRasterElev(lastPoint.x(), lastPoint.y())

            #shared.fpOut.write("C " + str(elevFirstPoint) + " " + str(elevNearPoint) + " " + str(elevLastPoint) + "\n")

            pts = [[NEAR_POINT, elevNearPoint], [FIRST_POINT, elevFirstPoint], [LAST_POINT, elevLastPoint]]
            pts.sort(key = lambda pt: pt[1])

            #for m in range(3):
               #shared.fpOut.write("\tpts[" + str(m) + "][0] = " + str(pts[m][0]) + ", pts[" + str(m) + "][1] = " + str(pts[m][1]) + "\n")

            if pts[0][0] == NEAR_POINT:
               # Near point is lowest: we are in a blind pit, so try the next road segment
               #shared.fpOut.write("\tIn road blind pit: with this road segment, downhill flow ends at " + displayOS(thisPoint.x(), thisPoint.y()) + ", abandoning\n")

               shared.thisFieldRoadSegIDsTried.append(featID)
               continue

            elif pts[1][0] == NEAR_POINT:
               if pts[0][0] == FIRST_POINT:
                  # First point is lower than near point, so flow goes to first point
                  shared.fpOut.write("Flow to first point d\n")
                  flowToFirstPoint = True

               else:
                  # Last point is lower than near point, so flow goes to last point
                  #shared.fpOut.write("Flow to last point a\n")
                  flowToLastPoint = True

            else:
               # Both first and last points are lower, so we need to compare gradients
               shared.fpOut.write("firstPoint = " + displayOS(firstPoint.x(), firstPoint.y()) + " nearPoint = " + displayOS(nearPoint.x(), nearPoint.y()) + " lastPoint = " + displayOS(lastPoint.x(), lastPoint.y()) + "\n")

               flowToLast = FindSteepestSegment(firstPoint, nearPoint, lastPoint, elevNearPoint - elevFirstPoint, elevNearPoint - elevLastPoint)
               shared.fpOut.write(str(flowToLast) + " \n")

               if flowToLast:
                  flowToLastPoint = True
                  #shared.fpOut.write("Flow to last point b\n")
               else:
                  flowToFirstPoint = True
                  shared.fpOut.write("Flow to first point c\n")


         # We are flowing along at least part of this road segment
         #if firstTime:
            #shared.fpOut.write("FIRST " + displayOS(prevPoint.x(), prevPoint.y()) + " " + displayOS(nearPoint.x(), nearPoint.y()))
            #if prevPoint != nearPoint:
               #addFlowLine(prevPoint, nearPoint, FLOW_VIA_ROAD, fieldCode, -1)
               #firstTime = False

         # Now check for nearby pre-existing flow lines
         adjX, adjY = FindNearbyFlowLine(thisPoint)
         if adjX != -1:
            # There is an adjacent flow line, so merge the two and finish with this flow line
            adjPoint = QgsPoint(adjX, adjY)

            indx = shared.allFieldsFlowPath.index(adjPoint)
            hitFieldFlowFrom = shared.allFieldsFlowPathFieldCode[indx]

            addFlowLine(thisPoint, adjPoint, MERGED_WITH_ADJACENT_FLOWLINE, fieldCode, -1)
            shared.fpOut.write("Flow from field " + fieldCode + " hit flow from field " + str(hitFieldFlowFrom) + " at " + displayOS(adjPoint.x(), adjPoint.y(), False) + ", so stopped tracing flow from this field\n")

            return 3, adjPoint

         # Next check if this road segment intersects a stream segment
         rtn = -1
         streamIntersectPoints = []
         streamIntersectFound = False
         rtn, streamIntersectPoints = FindSegmentIntersectionWithStream(feature.geometry())
         if rtn == -1:
            # Error
            return -1, -1

         elif rtn == 1:
            # We have at least one road-stream intersection
            streamIntersectFound = True
            for point in streamIntersectPoints:
               #shared.fpOut.write("This road segment intersects a stream segment at " + displayOS(point.x(), point.y()))

               # The intersection point is not necessarily a point in the line. So get the actual point in the line which is closest
               intersectPoint = -1
               numIntersectPoint = -1
               beforeIntersectPoint = -1
               afterIntersectPoint = -1
               sqrDist = -1
               intersectPoint, numIntersectpoint, beforeIntersectpoint, afterIntersectpoint, sqrDist = geomFeat.closestVertex(point)

               # And insert the intersection point in the road polyline
               linePoints.insert(numIntersectpoint, point)

         # OK now do the along-road routing
         if flowToLastPoint:
            # Flow is towards the last point of this road segment
            flowRouted = True
            shared.thisFieldRoadSegIDsTried.append(featID)

            printStr = "Flow from field " + fieldCode + " enters the OS road segment '" + str(featCode) + "' '" + str(featDesc) + "' '" + str(roadName) + "' '" + str(roadNumber) + "' at " + displayOS(thisPoint.x(), thisPoint.y()) + " "

            for m in range(numNearPoint, len(linePoints)-1):
               if not firstTime:
                  thisPoint = linePoints[m]
               nextPoint = linePoints[m+1]

               addFlowLine(thisPoint, nextPoint, FLOW_VIA_ROAD, fieldCode, -1)
               #shared.fpOut.write("addFlowLine 1 " + displayOS(thisPoint.x(), thisPoint.y()))

               firstTime = False

               if streamIntersectFound:
                  if nextPoint in streamIntersectPoints:
                     printStr += ("and hits a stream at " + displayOS(nextPoint.x(), nextPoint.y()) + "\n")
                     shared.fpOut.write(printStr)
                     #shared.fpOut.write("======")

                     return 2, nextPoint

            printStr += ("and leaves it at " + displayOS(lastPoint.x(), lastPoint.y()) + "\n")
            shared.fpOut.write(printStr)
            #shared.fpOut.write("======")

         else:
            # Flow is towards the first point of this road segment
            flowRouted = True
            shared.thisFieldRoadSegIDsTried.append(featID)

            printStr = "Flow from field " + fieldCode + " enters the OS road segment '" + str(featCode) + "' '" + str(featDesc) + "' '" + str(roadName) + "' '" + str(roadNumber) + "' at " + displayOS(thisPoint.x(), thisPoint.y()) + " "

            for m in range(numNearPoint, 1, -1):
               if not firstTime:
                  thisPoint = linePoints[m]
               nextPoint = linePoints[m-1]

               addFlowLine(thisPoint, nextPoint, FLOW_VIA_ROAD, fieldCode, -1)
               #shared.fpOut.write("addFlowLine 2 " + displayOS(thisPoint.x(), thisPoint.y()))

               firstTime = False

               if streamIntersectFound:
                  if nextPoint in streamIntersectPoints:
                     printStr += ("and hits a stream at " + displayOS(nextPoint.x(), nextPoint.y()) + "\n*** Does it enter the stream here?\n")
                     shared.fpOut.write(printStr)
                     #shared.fpOut.write("======")

                     return 2, nextPoint

            printStr += ("and leaves it at " + displayOS(lastPoint.x(), lastPoint.y()) + "\n")
            shared.fpOut.write(printStr)
            #shared.fpOut.write("======")

         # Set the end point of this road segment to be the start point, ready for next time round the loop
         thisPoint = lastPoint

         # Don't bother with any more possible road segments since we have routed flow via this one
         break

      if not flowRouted:
         shared.fpOut.write("\tNo suitable road segment found at " + displayOS(thisPoint.x(), thisPoint.y()) + "\n")
         return 1, thisPoint

   return 0, thisPoint
#======================================================================================================================


#======================================================================================================================
#
# Routes flow downhill along a vector representation of a path
#
#======================================================================================================================
def flowAlongVectorPath(indx, fieldCode, thisPoint):
   # pylint: disable=too-many-locals
   # pylint: disable=too-many-nested-blocks
   # pylint: disable=too-many-return-statements
   # pylint: disable=too-many-branches
   # pylint: disable=too-many-statements

   obsCategory = shared.fieldObservationCategory[indx]
   obsBehaviour = shared.fieldObservationBehaviour[indx]
   obsDesc = shared.fieldObservationDescription[indx]

   shared.thisFieldFieldObsAlreadyFollowed.append(indx)

   #shared.fpOut.write("Entered flowAlongVectorPath at point " + displayOS(thisPoint.x(), thisPoint.y()))
   layerNum = -1
   #geomPoint = QgsGeometry.fromPoint(thisPoint)

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

      return -1, -1

   # TODO make this a user setting
   numberToSearchFor = 4

   while True:
      # Find the nearest path segments
      #shared.fpOut.write("Start of flowAlongVectorPath loop at " + displayOS(thisPoint.x(), thisPoint.y()))
      nearestIDs = shared.vectorInputIndex[layerNum].nearestNeighbor(thisPoint, 3)
      request = QgsFeatureRequest().setFilterFids(nearestIDs)
      features = shared.vectorInputLayers[layerNum].getFeatures(request)

      distToPoint = []
      geomPoint = QgsGeometry.fromPoint(thisPoint)

      for pathSeg in features:
         # Is this path segment both close enough, and has not already been tried?
         geomSeg = pathSeg.geometry()
         nearPoint = geomSeg.nearestPoint(geomPoint)
         distanceToSeg = geomPoint.distance(nearPoint)
         segID = pathSeg.id()
         #shared.fpOut.write("\tpath segID = " + str(segID) + ", distanceToSeg = " + str(distanceToSeg) + "\n")

         if distanceToSeg > shared.searchDist:
            # Too far away, so forget about this path segment
            #shared.fpOut.write("\tToo far away (" + str(distanceToSeg) + " m) for path segID = " + str(segID) + "\n")

            continue

         if segID in shared.thisFieldPathSegIDsTried:
            # Aready travelled, so forget about this path segment
            #shared.fpOut.write("\tAlready travelled for path segID = " + str(segID) + "\n")

            continue

         # Is OK, so save the path segment feature, the nearest point, and the distance
         distToPoint.append([pathSeg, nearPoint.asPoint(), distanceToSeg])

      # Did we any find suitable path segments?
      if not distToPoint:
         # Nope
         #shared.fpOut.write("Flow along path from field " + str(fieldCode) + " ends at " + displayOS(thisPoint.x(), thisPoint.y()) + "\n*** Please add a field observation\n")
         return 1, thisPoint

      # OK we have some possibly suitable path segments
      #for n in range(len(distToPoint)):
         #shared.fpOut.write("\tBefore " + str(n) + " " + str(distToPoint[n][0].id()) + " " + displayOS(distToPoint[n][1].x(), distToPoint[n][1].y()) + " " + str(distToPoint[n][2]) + " m\n")

      # Sort the list of untravelled path segments, shortest distance first
      distToPoint.sort(key = lambda distPoint: distPoint[2])

      #for n in range(len(distToPoint)):
         #shared.fpOut.write("\tAfter " + str(n) + " " + str(distToPoint[n][0].id()) + " " + displayOS(distToPoint[n][1].x(), distToPoint[n][1].y()) + " " + str(distToPoint[n][2]) + " m\n")

      flowRouted = False
      for n in range(len(distToPoint)):
         # Go through this list of untravelled path segments till we find a suitable one
         feature = distToPoint[n][0]
         nearPoint = distToPoint[n][1]
         distToNearPoint = distToPoint[n][2]
         featID = feature.id()
         #shared.fpOut.write("\tTrying path seg ID " + str(featID) + "\n")

         featDesc = feature[PATH_DESC]

         geomFeat = feature.geometry()
         linePoints = geomFeat.asPolyline()
         nPoints = len(linePoints)

         firstPoint = linePoints[0]
         lastPoint = linePoints[-1]

         #shared.fpOut.write("\tAt " + displayOS(thisPoint.x(), thisPoint.y()) +", trying untravelled path segment " + str(featID) + " '" + str(featDesc) + "', which has nearest point " + "{:0.1f}".format(distToNearPoint) + " m away at " + displayOS(nearPoint.x(), nearPoint.y()) + "\n")

         #shared.fpOut.write("\tFirst point of path segment is " + displayOS(firstPoint.x(), firstPoint.y()) + "\n")
         #shared.fpOut.write("\tNearest point of path segment is " + displayOS(nearPoint.x(), nearPoint.y()) + "\n")
         #shared.fpOut.write("\tLast point of path segment is " + displayOS(lastPoint.x(), lastPoint.y()) + "\n")

         # If there is a choice, then find out which direction along the path has the steepest downhill slope
         flowTowardsFirstPoint = False
         flowTowardsLastPoint = False
         if nearPoint == firstPoint:
            # The nearest point is the same as the first point
            thisPoint = linePoints[0]
            thisPointNum = 0
            nextPoint = linePoints[1]

            elevThisPoint = getRasterElev(thisPoint.x(), thisPoint.y())
            elevNextPoint = getRasterElev(nextPoint.x(), nextPoint.y())

            #shared.fpOut.write("A " + str(elevThisPoint) + " " + str(elevNextPoint) + "\n")

            if elevThisPoint >= elevNextPoint:
               # Flow towards last point of path segment
               flowTowardsLastPoint = True
               #shared.fpOut.write("Flow is towards last point of path segment\n")
            else:
               # This point is lower: we are in a blind pit, so try the next path segment
               #shared.fpOut.write("\tIn path blind pit: with this path segment, downhill flow ends at " + displayOS(thisPoint.x(), thisPoint.y()) + ", abandoning\n")

               shared.thisFieldPathSegIDsTried.append(featID)
               continue

         elif nearPoint == lastPoint:
            # The nearest point is the same as the last point
            thisPointNum = len(linePoints) - 1
            thisPoint = linePoints[thisPointNum]
            nextPoint = linePoints[thisPointNum-1]

            elevThisPoint = getRasterElev(thisPoint.x(), thisPoint.y())
            elevNextPoint = getRasterElev(nextPoint.x(), nextPoint.y())

            #shared.fpOut.write("B " + str(elevThisPoint) + " " + str(elevNextPoint) + "\n")

            if elevThisPoint >= elevNextPoint:
               # Flow towards first point of path segment
               flowTowardsFirstPoint = True
               #shared.fpOut.write("Flow is towards first point of path segment\n")
            else:
               # This point is lower: we are in a blind pit, so try the next path segment
               shared.fpOut.write("\tIn path blind pit: with this path segment, downhill flow ends at " + displayOS(thisPoint.x(), thisPoint.y()) + ", abandoning\n")

               shared.thisFieldPathSegIDsTried.append(featID)
               continue

         else:
            # The nearest point is not a point in the line, so we need to insert it. First get the closest vertex
            linePoints = geomFeat.asPolyline()
            nPoints = len(linePoints)
            #for n in range(nPoints):
               #shared.fpOut.write(str(n) + " " + displayOS(linePoints[n].x(), linePoints[n].y()) + "\n")
            #shared.fpOut.write("\n")

            dist, p2, numPt = geomFeat.closestSegmentWithContext(nearPoint)
            if not geomFeat.insertVertex(nearPoint.x(), nearPoint.y(), numPt):
               # Error, could not insert vertex
               return -1, -1

            linePoints = geomFeat.asPolyline()
            nPoints = len(linePoints)
            #for n in range(nPoints):
               #shared.fpOut.write(str(n) + " " + displayOS(linePoints[n].x(), linePoints[n].y()) + "\n")
            #shared.fpOut.write("\n")

            thisPointNum = numPt      # Because insertVertex inserts BEFORE numPt, so the new point is numPt
            #shared.fpOut.write("\tthisPointNum = " + str(thisPointNum) + "\n")

            prevPoint = linePoints[thisPointNum-1]
            thisPoint = linePoints[thisPointNum]
            postPoint = linePoints[thisPointNum+1]

            elevPrevPoint = getRasterElev(prevPoint.x(), prevPoint.y())
            elevThisPoint = getRasterElev(thisPoint.x(), thisPoint.y())
            elevPostPoint = getRasterElev(postPoint.x(), postPoint.y())

            #shared.fpOut.write("\tC prev: " + str(elevPrevPoint) + " this: " + str(elevThisPoint) + " post: " + str(elevPostPoint) + "\n")

            pts = [[PREV_POINT, elevPrevPoint], [THIS_POINT, elevThisPoint], [POST_POINT, elevPostPoint]]
            pts.sort(key = lambda pt: pt[1])

            #for m in range(3):
               #shared.fpOut.write("\tpts[" + str(m) + "][0] = " + str(pts[m][0]) + ", pts[" + str(m) + "][1] = " + str(pts[m][1]) + "\n")

            if pts[0][0] == THIS_POINT:
               # This point (the newly-inserted point) is lowest: we are in a blind pit, so try the next path segment
               shared.fpOut.write("\tIn path blind pit: with this path segment, downhill flow ends at " + displayOS(thisPoint.x(), thisPoint.y()) + ", abandoning\n")

               shared.thisFieldPathSegIDsTried.append(featID)
               continue

            elif pts[1][0] == THIS_POINT:
               if pts[0][0] == PREV_POINT:
                  # The previous point is lower than this point, so flow goes towards the first point of the path segment
                  #shared.fpOut.write("Flow towards first point of path segment a1\n")
                  flowTowardsFirstPoint = True

               else:
                  # The post point is lower than this point, so flow goes towards the last point of the path segment
                  #shared.fpOut.write("Flow towards last point of path segment a2\n")
                  flowTowardsLastPoint = True

            else:
               # Both previous and post points are lower than this , so we need to compare gradients
               #shared.fpOut.write("prevPoint = " + displayOS(prevPoint.x(), prevPoint.y()) + " thisPoint = " + displayOS(thisPoint.x(), thisPoint.y()) + " postPoint = " + displayOS(postPoint.x(), postPoint.y()) + "\n")

               flowLastwards = FindSteepestSegment(prevPoint, thisPoint, postPoint, elevThisPoint - elevPrevPoint, elevThisPoint - elevPostPoint)

               if flowLastwards:
                  flowTowardsLastPoint = True
                  #shared.fpOut.write("Flow towards last point of path segment b\n")
               else:
                  flowTowardsFirstPoint = True
                  #shared.fpOut.write("Flow towards first point of path segment c\n")

         # OK we know the initial direction of flow along this path/track, so keep going till we reach a pre-existing flow line, a ditch/stream, a blind pit, or the end of the path/track
         shared.thisFieldPathSegIDsTried.append(featID)
         printStr = "Flow from field " + fieldCode + " enters the path segment '" + str(featDesc) + "' at " + displayOS(thisPoint.x(), thisPoint.y()) + " "
         addFlowMarkerPoint(thisPoint, FLOW_VIA_PATH, fieldCode, elevThisPoint)

         if flowTowardsLastPoint:
            # Flow goes towards the last point of the path segment
            for nn in range(thisPointNum, len(linePoints) - 2):
               thisPoint = linePoints[nn]
               nextPoint = linePoints[nn+1]
               elevThisPoint = getRasterElev(thisPoint.x(), thisPoint.y())
               elevNextPoint = getRasterElev(nextPoint.x(), nextPoint.y())

               addFlowLine(thisPoint, nextPoint, FLOW_VIA_PATH, fieldCode, -1)

               # Check for nearby pre-existing flow lines
               adjX, adjY = FindNearbyFlowLine(nextPoint)
               if adjX != -1:
                  # There is an adjacent flow line, so merge the two and finish with this flow line
                  adjPoint = QgsPoint(adjX, adjY)

                  indx = shared.allFieldsFlowPath.index(adjPoint)
                  hitFieldFlowFrom = shared.allFieldsFlowPathFieldCode[indx]

                  addFlowLine(thisPoint, adjPoint, MERGED_WITH_ADJACENT_FLOWLINE, fieldCode, -1)
                  shared.fpOut.write("Flow from field " + fieldCode + " hit flow from field " + str(hitFieldFlowFrom) + " at " + displayOS(adjPoint.x(), adjPoint.y(), False) + ", so stopped tracing flow from this field\n")

                  return 3, adjPoint

               # Next check if we are near a stream segment
               rtn = FindNearbyStream(nextPoint, fieldCode)
               if rtn == -1:
                  # Problem! Exit the program
                  exit (-1)
               elif rtn == 1:
                  # Flow entered a ditch or stream and reached the Rother. We are done here, so move on to the next field
                  shared.fpOut.write("Hit ditch/stream\n")
                  return 2, nextPoint

               # Do we have a nearby field observation?
               indx = FindNearbyFieldObservation(nextPoint)
               if indx != -1:
                  # We have found a field observation near this point, so route flow accordingly
                  rtn, adjPoint = flowViaFieldObservation(indx, fieldCode, nextPoint, elevNextPoint)
                  if rtn == 0:
                     # Flow has passed through the field observation
                     #shared.fpOut.write("Left flowViaFieldObservation() called in flowAlongVectorPath() 1, rtn = " + str(rtn) + "\n")
                     return rtn, adjPoint

                  elif rtn == -1:
                     # Could not determine the Field observation's outflow location
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + displayOS(nextPoint.x(), nextPoint.y()) + " to " + displayOS(adjPoint.x(), adjPoint.y()) + ", could not determine outflow location\n")
                     return rtn, thisPoint

                  elif rtn == 1:
                     # Flow has passed through the field observation and then hit a blind pit
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + displayOS(nextPoint.x(), nextPoint.y()) + " to " + displayOS(adjPoint.x(), adjPoint.y()) + ", hit blind pit\n")
                     return rtn, thisPoint

                  elif rtn == 2:
                     # Flow has passed through the field observation and then  hit a stream
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + displayOS(nextPoint.x(), nextPoint.y()) + " to " + displayOS(adjPoint.x(), adjPoint.y()) + " stream\n")
                     return rtn, thisPoint

                  elif rtn == 3:
                     # Flow has passed through the field observation and then merged with pre-existing flow
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + displayOS(nextPoint.x(), nextPoint.y()) + " to " + displayOS(adjPoint.x(), adjPoint.y()) + ", merged with pre-existing flow\n")
                     return rtn, thisPoint

         else:
            # Flow goes towards the first point of the path segment
            for nn in range(thisPointNum, 1, -1):
               thisPoint = linePoints[nn]
               nextPoint = linePoints[nn-1]
               elevThisPoint = getRasterElev(thisPoint.x(), thisPoint.y())
               elevNextPoint = getRasterElev(nextPoint.x(), nextPoint.y())

               addFlowLine(thisPoint, nextPoint, FLOW_VIA_PATH, fieldCode, -1)

               # Check for nearby pre-existing flow lines
               adjX, adjY = FindNearbyFlowLine(nextPoint)
               if adjX != -1:
                  # There is an adjacent flow line, so merge the two and finish with this flow line
                  adjPoint = QgsPoint(adjX, adjY)

                  indx = shared.allFieldsFlowPath.index(adjPoint)
                  hitFieldFlowFrom = shared.allFieldsFlowPathFieldCode[indx]

                  addFlowLine(thisPoint, adjPoint, MERGED_WITH_ADJACENT_FLOWLINE, fieldCode, -1)
                  shared.fpOut.write("Flow from field " + fieldCode + " hit flow from field " + str(hitFieldFlowFrom) + " at " + displayOS(adjPoint.x(), adjPoint.y(), False) + ", so stopped tracing flow from this field\n")

                  return 3, adjPoint

               # Next check if we are near a stream segment
               rtn = FindNearbyStream(nextPoint, fieldCode)
               if rtn == -1:
                  # Problem! Exit the program
                  exit (-1)
               elif rtn == 1:
                  # Flow entered a ditch or stream and reached the Rother. We are done here, so move on to the next field
                  shared.fpOut.write("Hit ditch/stream\n")
                  return 2, nextPoint

               # Do we have a nearby field observation?
               indx = FindNearbyFieldObservation(nextPoint)
               if indx != -1:
                  # We have found a field observation near this point, so route flow accordingly
                  rtn, adjPoint = flowViaFieldObservation(indx, fieldCode, nextPoint, elevNextPoint)
                  #shared.fpOut.write("Left flowViaFieldObservation() called in flowAlongVectorPath() 2, rtn = " + str(rtn) + "\n")
                  if rtn == 0:
                     # Flow has passed through the field observation
                     return rtn, adjPoint

                  elif rtn == -1:
                     # Could not determine the Field observation's outflow location
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + displayOS(nextPoint.x(), nextPoint.y()) + " to " + displayOS(adjPoint.x(), adjPoint.y()) + ", could not determine outflow location\n")
                     return rtn, thisPoint

                  elif rtn == 1:
                     # Flow has passed through the field observation and then hit a blind pit
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + displayOS(nextPoint.x(), nextPoint.y()) + " to " + displayOS(adjPoint.x(), adjPoint.y()) + ", hit blind pit\n")
                     return rtn, thisPoint

                  elif rtn == 2:
                     # Flow has passed through the field observation and then hit a stream
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + displayOS(nextPoint.x(), nextPoint.y()) + " to " + displayOS(adjPoint.x(), adjPoint.y()) + " stream\n")
                     return rtn, thisPoint

                  elif rtn == 3:
                     # Flow has passed through the field observation and then merged with pre-existing flow
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + displayOS(nextPoint.x(), nextPoint.y()) + " to " + displayOS(adjPoint.x(), adjPoint.y()) + ", merged with pre-existing flow\n")
                     return rtn, thisPoint


         ## OK now do the along-path routing
         #if flowToLastPoint:
            ## Flow is towards the last point of this path segment
            #flowRouted = True

            #for m in range(numNearPoint, len(linePoints)-1):
               #if not firstTime:
                  #thisPoint = linePoints[m]
               #nextPoint = linePoints[m+1]

               ##shared.fpOut.write("addFlowLine 1 " + displayOS(thisPoint.x(), thisPoint.y()))

               #firstTime = False

               #if streamIntersectFound:
                  #if nextPoint in streamIntersectPoints:
                     #printStr += ("and hits a stream at " + displayOS(nextPoint.x(), nextPoint.y()) + "\n")
                     #shared.fpOut.write(printStr)
                     ##shared.fpOut.write("======")

                     #return 2, nextPoint

            #printStr += ("and leaves it at " + displayOS(lastPoint.x(), lastPoint.y()) + "\n")
            #shared.fpOut.write(printStr)
            ##shared.fpOut.write("======")

         #else:
            ## Flow is towards the first point of this path segment
            #flowRouted = True
            #shared.thisFieldPathSegIDsTried.append(featID)

            #printStr = "Flow from field " + fieldCode + " enters the path segment '" + str(featDesc) + "' at " + displayOS(thisPoint.x(), thisPoint.y()) + " "

            #for m in range(numNearPoint, 1, -1):
               #if not firstTime:
                  #thisPoint = linePoints[m]
               #nextPoint = linePoints[m-1]

               #addFlowLine(thisPoint, nextPoint, FLOW_VIA_ROAD, fieldCode, -1)
               ##shared.fpOut.write("addFlowLine 2 " + displayOS(thisPoint.x(), thisPoint.y()))

               #firstTime = False

               #if streamIntersectFound:
                  #if nextPoint in streamIntersectPoints:
                     #printStr += ("and hits a stream at " + displayOS(nextPoint.x(), nextPoint.y()) + "\n*** Does it enter the stream here?\n")
                     #shared.fpOut.write(printStr)
                     ##shared.fpOut.write("======")

                     #return 2, nextPoint

            #printStr += ("and leaves it at " + displayOS(lastPoint.x(), lastPoint.y()) + "\n")
            #shared.fpOut.write(printStr)
            ##shared.fpOut.write("======")

         ## Set the end point of this path segment to be the start point, ready for next time round the loop
         #thisPoint = lastPoint

         ## Don't bother with any more possible path segments since we have routed flow via this one
         #break

      if not flowRouted:
         shared.fpOut.write("\tNo suitable path segment found at " + displayOS(thisPoint.x(), thisPoint.y()) + "\n")
         return 1, thisPoint

   return 0, thisPoint
#======================================================================================================================


#======================================================================================================================
#
# Returns True if flow between two points hits a field boundary
#
#======================================================================================================================
def flowHitFieldBoundary(firstPoint, secondPoint, flowFieldCode):
   # pylint: disable=too-many-locals
   # pylint: disable=too-many-nested-blocks

   flowLineFeature = QgsFeature()
   flowLineFeature.setGeometry(QgsGeometry.fromPolyline([firstPoint, secondPoint]))
   geomFlowLine = flowLineFeature.geometry()

   # Construct a bounding box
   if firstPoint.x() < secondPoint.x():
      xMin = firstPoint.x()
      xMax = secondPoint.x()
   else:
      xMin = secondPoint.x()
      xMax = firstPoint.x()

   if firstPoint.y() < secondPoint.y():
      yMin = firstPoint.y()
      yMax = secondPoint.y()
   else:
      yMin = secondPoint.y()
      yMax = firstPoint.y()

   boundingBox = QgsRectangle(xMin, yMin, xMax, yMax)
   request = QgsFeatureRequest(boundingBox)

   for layerNum in range(len(shared.vectorInputLayersCategory)):
      if shared.vectorInputLayersCategory[layerNum] == INPUT_FIELD_BOUNDARIES:
         features = shared.vectorInputLayers[layerNum].getFeatures(request)
         for fieldBoundary in features:
            # Get the field code
            fieldCode = fieldBoundary[CONNECTED_FIELD_ID]

            geomFieldBoundary = fieldBoundary.constGeometry()
            poly = geomFieldBoundary.asPolygon()

            # Do this for every pair of points on this polygon's boundary i.e. for every line comprising the boundary
            for i in range(len(poly)):
               for j in range(len(poly[i]) - 1):
                  thisBoundaryPointX = poly[i][j][0]
                  thisBoundaryPointY = poly[i][j][1]

                  nextBoundaryPointX = poly[i][j+1][0]
                  nextBoundaryPointY = poly[i][j+1][1]

                  boundaryLineFeature = QgsFeature()
                  boundaryLineFeature.setGeometry(QgsGeometry.fromPolyline([QgsPoint(thisBoundaryPointX, thisBoundaryPointY), QgsPoint(nextBoundaryPointX, nextBoundaryPointY)]))

                  geomBoundaryLine = boundaryLineFeature.geometry()

                  if geomFlowLine.intersects(geomBoundaryLine):
                     intersection = geomFlowLine.intersection(geomBoundaryLine)
                     intersectPoint = intersection.asPoint()

                     addFlowMarkerPoint(intersectPoint, MARKER_FIELD_BOUNDARY, flowFieldCode, -1)

                     return True, intersectPoint, fieldCode

   return False, QgsPoint(-1, -1), -1
#======================================================================================================================


#======================================================================================================================
#
# Routes flow along a vector representation of a field boundary
#
#======================================================================================================================
def flowAlongVectorFieldBoundary(indx, fieldCode, thisPoint):
   # pylint: disable=too-many-locals
   # pylint: disable=too-many-nested-blocks
   # pylint: disable=too-many-return-statements
   # pylint: disable=too-many-branches
   # pylint: disable=too-many-statements

   obsCategory = shared.fieldObservationCategory[indx]
   obsBehaviour = shared.fieldObservationBehaviour[indx]
   obsDesc = shared.fieldObservationDescription[indx]

   shared.thisFieldFieldObsAlreadyFollowed.append(indx)

   #print("Entered flowAlongVectorFieldBoundary at point " + displayOS(thisPoint.x(), thisPoint.y()))
   layerNum = -1
   #geomPoint = QgsGeometry.fromPoint(thisPoint)

   # Find the field boundary layer
   boundaryLayerFound = False
   for layerNum in range(len(shared.vectorInputLayersCategory)):
      if shared.vectorInputLayersCategory[layerNum] == INPUT_FIELD_BOUNDARIES:
         boundaryLayerFound = True
         break

   # Safety check
   if not boundaryLayerFound:
      printStr = "ERROR: opening field boundary layer\n"
      shared.fpOut.write(printStr)
      print(printStr)

      return -1, -1

   # TODO make this a user setting
   numberToSearchFor = 3

   # Find the nearest field boundary polygon TODO could this be passed in as a parameter?
   nearestIDs = shared.vectorInputIndex[layerNum].nearestNeighbor(thisPoint, 3)
   request = QgsFeatureRequest().setFilterFids(nearestIDs)
   features = shared.vectorInputLayers[layerNum].getFeatures(request)

   distToPoint = []
   geomPoint = QgsGeometry.fromPoint(thisPoint)

   for boundaryPoly in features:
      # Is this boundary polygon both close enough, and has not already been tried?
      geomPoly = boundaryPoly.geometry()
      nearPoint = geomPoly.nearestPoint(geomPoint)
      distanceToPoly = geomPoint.distance(nearPoint)
      polyID = boundaryPoly.id()
      #print("polyID = " + str(polyID) + " distanceToPoly = " + str(distanceToPoly))

      if distanceToPoly > shared.searchDist or polyID in shared.thisFieldFieldObsAlreadyFollowed:
         # Too far away or already travelled, so forget about this road segment
         continue

      # Is OK, so save the boundary polygon feature, the nearest point, and the distance
      distToPoint.append([boundaryPoly, nearPoint.asPoint(), distanceToPoly])

   # Did we any find suitable boundary polygons?
   if not distToPoint:
      # Nope
      shared.fpOut.write("Flow along boundary from field " + str(fieldCode) + " ends at " + displayOS(thisPoint.x(), thisPoint.y()) + "\n*** Please add a field observation\n")
      return 1, thisPoint

   # OK we have some possibly suitable boundary polygons
   #for n in range(len(distToPoint)):
      #shared.fpOut.write("Before " + str(n) + " " + str(distToPoint[n][0].id()) + " " + displayOS(distToPoint[n][1].x(), distToPoint[n][1].y()) + " " + str(distToPoint[n][2]) + " m")

   # Sort the list of untravelled boundary polygons, closest first
   distToPoint.sort(key = lambda distPoint: distPoint[2])

   #for n in range(len(distToPoint)):
      #print"After " + (str(n) + " " + str(distToPoint[n][0].id()) + " " + displayOS(distToPoint[n][1].x(), distToPoint[n][1].y()) + " " + str(distToPoint[n][2]) + " m")

   flowRouted = False
   for n in range(len(distToPoint)):
      # Go through this list of untravelled boundary polygons till we find a suitable one
      feature = distToPoint[n][0]
      featID = feature.id()
      #print("Trying feature ID " + str(featID))

      boundaryFieldCode = feature[CONNECTED_FIELD_ID]

      geomFeat = feature.geometry()
      polygon = geomFeat.asPolygon()
      points = polygon[0]
      nPointsInPoly = len(points)

      # OK, the nearest point is an approximation: it is not necessarily a point in the polygon's boundary. So get the actual point in the bopundary which is closest
      nearPoint, numNearPoint, beforeNearPoint, afterNearPoint, sqrDist = geomFeat.closestVertex(distToPoint[n][1])
      #print(nearPoint, numNearPoint, beforeNearPoint, afterNearPoint, sqrDist)
      #print(nearPoint, points[numNearPoint])

      shared.fpOut.write("\tAt " + displayOS(thisPoint.x(), thisPoint.y()) +", trying untravelled boundary of field " + str(boundaryFieldCode) + "  which has nearest point " + "{:0.1f}".format(sqrt(sqrDist)) + " m away at " + displayOS(nearPoint.x(), nearPoint.y()) + "\n")

      #shared.fpOut.write("\tNearest point of boundary polygon is " + displayOS(nearPoint.x(), nearPoint.y()) + "\n")

      # May need to flow to this nearest vertex
      if thisPoint != nearPoint:
         addFlowLine(thisPoint, nearPoint, FLOW_VIA_BOUNDARY, fieldCode, -1)

         thisPoint = nearPoint

      numThisVertex = numNearPoint

      # OK, so we know which field boundary polygon we are dealing with: now loop until we either hit a blind pit, a stream, or a field observation
      verticesTravelled = [numThisVertex]

      while True:
         #print("Start of flowAlongVectorFieldBoundary loop at " + displayOS(thisPoint.x(), thisPoint.y()) + " vertex " + str(numThisVertex))

         # Find out which direction along the polygon's edge has the steepest downhill slope
         flowRouted = False

         elevThisPoint = getRasterElev(thisPoint.x(), thisPoint.y())

         geomThisPoint = QgsGeometry.fromPoint(thisPoint)

         prevSlope = nextSlope = -1

         # Calculate the elevation difference for the previous point, if not already visited
         numPrevVertex = numThisVertex - 1
         if numPrevVertex < 0:
            numPrevVertex = nPointsInPoly - 2

         if numPrevVertex not in verticesTravelled:
            # This vertex has not already had flow through it
            prevPoint = points[numPrevVertex]

            elevPrevPoint = getRasterElev(prevPoint.x(), prevPoint.y())

            elevDiffPrev = elevThisPoint - elevPrevPoint

            geomPrevPoint = QgsGeometry.fromPoint(prevPoint)
            prevDist = geomThisPoint.distance(geomPrevPoint)

            #print(numPrevVertex, prevPoint, elevDiffPrev, prevDist)
            prevSlope = elevDiffPrev / prevDist

         # Calculate the elevation difference for the next point, if not already visited
         numNextVertex = numThisVertex + 1
         if numNextVertex >= nPointsInPoly - 1:
            numNextVertex = numNextVertex - nPointsInPoly + 1

         if numNextVertex not in verticesTravelled:
            # This vertex has not already had flow through it
            nextPoint = points[numNextVertex]

            elevNextPoint = getRasterElev(nextPoint.x(), nextPoint.y())

            elevDiffNext = elevThisPoint - elevNextPoint

            geomNextPoint = QgsGeometry.fromPoint(nextPoint)
            nextDist = geomThisPoint.distance(geomNextPoint)

            #print(numNextVertex, nextPoint, elevDiffNext, nextDist)
            nextSlope = elevDiffNext / nextDist

         #print(prevSlope, nextSlope, verticesTravelled)

         if prevSlope <= 0 and nextSlope <= 0:
            # We are in a blind pit
            shared.fpOut.write("\tIn blind pit on boundary of field " + str(boundaryFieldCode) + ": downhill flow ends at " + displayOS(thisPoint.x(), thisPoint.y()) + ", abandoning\n")

            return 1, thisPoint

         # We are flowing along a segment of this polygon's edge
         if prevSlope > nextSlope:
            forward = True
            flowToPoint = prevPoint
            numFlowToPoint = numPrevVertex
         else:
            forward = False
            flowToPoint = nextPoint
            numFlowToPoint = numNextVertex

         # Check for intersection with a stream segment
         geomLine = QgsGeometry.fromPolyline([thisPoint, flowToPoint])
         rtn = -1
         streamIntersectPoints = []
         streamIntersectFound = False
         rtn, streamIntersectPoints = FindSegmentIntersectionWithStream(geomLine)
         if rtn == -1:
            # Error
            return -1, -1

         elif rtn == 1:
            # We have at least one intersection
            streamIntersectFound = True
            for intPoint in streamIntersectPoints:
               shared.fpOut.write("The boundary of field " + str(boundaryFieldCode) + " intersects a stream at " + displayOS(intPoint.x(), intPoint.y()) + "\n*** Does flow enter the stream here?\n")

               addFlowLine(thisPoint, intPoint, FLOW_VIA_BOUNDARY, fieldCode, -1)

               # NOTE we are only considering the first intersection point
               return 2, intPoint

         # OK, now find the in-between points
         inBetweenPoints = pointsOnLine(thisPoint, flowToPoint, shared.searchDist)
         for nPoint in range(len(inBetweenPoints)-1):
            # Do this for every in-between point
            point1 = inBetweenPoints[nPoint]
            point2 = inBetweenPoints[nPoint+1]

            # Check for nearby flow lines
            adjX, adjY = FindNearbyFlowLine(point1)
            if adjX != -1:
               # There is an adjacent flow line, so merge the two and finish with this flow line
               adjPoint = QgsPoint(adjX, adjY)

               indx = shared.allFieldsFlowPath.index(adjPoint)
               hitFieldFlowFrom = shared.allFieldsFlowPathFieldCode[indx]

               addFlowLine(point1, adjPoint, MERGED_WITH_ADJACENT_FLOWLINE, fieldCode, -1)
               shared.fpOut.write("Flow from field " + fieldCode + " hit flow from field " + str(hitFieldFlowFrom) + " at " + displayOS(adjPoint.x(), adjPoint.y(), False) + ", so stopped tracing flow from this field\n")

               return 3, adjPoint

            # If the field boundary is convex at this vertex (i.e. bulges inward) then find out whether flow leaves the boundary because an adjacent within-polygon cell has a steeper gradient
            # TODO make a user option
            flowAwayFromBoundary = True
            if flowAwayFromBoundary and nPoint > 0:
               point0 = inBetweenPoints[nPoint-1]
               z = calcZCrossProduct(point0, point1, point2)

               if (forward and z > 0) or (not forward and z < 0):
                  #print(point1, z)

                  elev = getRasterElev(point1.x(), point1.y())

                  # Search for the adjacent raster cell with the steepest here-to-there slope, and get its centroid
                  geomPoint1 = QgsGeometry.fromPoint(point1)
                  adjPoint, adjElev = FindSteepestAdjacent(point1, elev, geomPoint1)
                  #print(adjPoint, adjElev)
                  if adjPoint.x() != -1:
                     # There is a within-polygon cell with a steeper gradient
                     addFlowLine(point1, adjPoint, FLOW_DOWN_STEEPEST, fieldCode, elev)

                     shared.fpOut.write("\tFlow from field " + str(fieldCode) + " has left the boundary of field " + str(boundaryFieldCode) + " at " + displayOS(point1.x(), point1.y(), False) + " and flows down the steepest with-in field gradient, to " +  displayOS(adjPoint.x(), adjPoint.y(), False) + "\n")

                     return 0, adjPoint

            # Do we have a nearby field observation?
            indx = FindNearbyFieldObservation(point1)
            if indx != -1:
               # We have found a field observation near this point
               thisElev = getRasterElev(point1.x(), point1.y())

               # So route flow accordingly
               rtn, adjPoint = flowViaFieldObservation(indx, fieldCode, point1, thisElev)
               #shared.fpOut.write("Left flowViaFieldObservation() called in flowAlongVectorFieldBoundary(), rtn = " + str(rtn) + "\n")
               if rtn == 0:
                  # Flow has passed through the LE
                  return rtn, adjPoint

               elif rtn == -1:
                  # Could not determine the outflow location
                  shared.fpOut.write("Along-boundary flow from field " + str(fieldCode) + " via field observation from " + displayOS(point1.x(), point1.y()) + " to " + displayOS(adjPoint.x(), adjPoint.y()) + ", could not determine outflow location\n")
                  return rtn, thisPoint

               elif rtn == 1:
                  # Flow has passed through the field observation and then hit a blind pit
                  shared.fpOut.write("Along-boundary flow from field " + str(fieldCode) + " via field observation from " + displayOS(point1.x(), point1.y()) + " to " + displayOS(adjPoint.x(), adjPoint.y()) + ", hit blind pit\n")
                  return rtn, thisPoint

               elif rtn == 2:
                  # Flow has hit a stream
                  shared.fpOut.write("Along-boundary flow from field " + str(fieldCode) + " via field observation from " + displayOS(point1.x(), point1.y()) + " to " + displayOS(adjPoint.x(), adjPoint.y()) + " stream\n")
                  return rtn, thisPoint

               elif rtn == 3:
                  # Merged with pre-existing flow
                  shared.fpOut.write("Along-boundary flow from field " + str(fieldCode) + " via field observation from " + displayOS(point1.x(), point1.y()) + " to " + displayOS(adjPoint.x(), adjPoint.y()) + ", merged with pre-existing flow\n")
                  return rtn, thisPoint

            # No nearby field observation

         # OK we have flow routed between these two vertices of the field boundary
         flowRouted = True

         printStr = "\tFlow from field " + fieldCode + " flows along the boundary of field " + str(boundaryFieldCode) + " from " + displayOS(thisPoint.x(), thisPoint.y()) + " to " + displayOS(flowToPoint.x(), flowToPoint.y())  + "\n"
         shared.fpOut.write(printStr)

         addFlowLine(thisPoint, flowToPoint, FLOW_VIA_BOUNDARY, fieldCode, -1)

         verticesTravelled.append(numFlowToPoint)

         # Go round the loop again
         thisPoint = flowToPoint
         numThisVertex = numFlowToPoint


      if flowRouted:
         # Don't bother looking at more distant polygon(s)
         break

   return 0, thisPoint
#======================================================================================================================


#======================================================================================================================
#
# Fills a blind pit, returning the overflow point and flow depth needed to create this overflow point
#
#======================================================================================================================
def fillBlindPit(thisPoint, fieldCode):

   startElev = getRasterElev(thisPoint.x(), thisPoint.y())
   pondedCells = [thisPoint]
   increment = 0.1
   topElev = startElev

   while True:
      topElev += increment
      #print("Start of fillBlindPit loop at " + displayOS(thisPoint.x(), thisPoint.y()) + " startElev = " +str(startElev) + " topElev = " + str(topElev))
      for cell in pondedCells:
         #print("pondedCell " + displayOS(cell.x(), cell.y()))
         addFlowLine(thisPoint, cell, BLIND_PIT, fieldCode, -1)

      newOverflowCells = []
      for point in pondedCells:
         adjPoint, adjElev = FindSteepestAdjacent(point, topElev)

         if adjPoint.x() != -1:
            # We have found a new overflow point to which we have not travelled before
            #print("Overflow cell found at " + displayOS(adjPoint.x(), adjPoint.y()) + " startElev = " +str(startElev)  + " topElev = " + str(topElev))
            return adjPoint, topElev - startElev

         # No new overflow point, so just add to list of ponded cells
         tempCells = CanOverflowTo(thisPoint, topElev, pondedCells)
         newOverflowCells.extend(tempCells)
         #print("newOverflowCells = " + str(newOverflowCells))

      pondedCells.extend(newOverflowCells)
      #print("pondedCells = " + str(pondedCells))

   # No overflow point
   return -1, -1
#======================================================================================================================
