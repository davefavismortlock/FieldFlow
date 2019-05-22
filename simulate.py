from math import sqrt, isclose
from operator import itemgetter

from qgis.core import QgsRaster, QgsFeature, QgsFeatureRequest, QgsGeometry, QgsPointXY, QgsRectangle, QgsPoint

import shared
from shared import INPUT_DIGITAL_ELEVATION_MODEL, FIELD_OBS_CATEGORY_ROAD, FIELD_OBS_BEHAVIOUR_ALONG, MARKER_ROAD, FIELD_OBS_CATEGORY_PATH, MARKER_PATH, FIELD_OBS_CATEGORY_BOUNDARY, MARKER_FIELD_BOUNDARY, FIELD_OBS_CATEGORY_CULVERT, MARKER_ENTER_CULVERT, INPUT_ROAD_NETWORK, OS_VECTORMAP_FEAT_CODE, OS_VECTORMAP_FEAT_DESC, OS_VECTORMAP_ROAD_NAME, OS_VECTORMAP_ROAD_NUMBER, MERGED_WITH_ADJACENT_FLOWLINE, FLOW_VIA_ROAD, INPUT_PATH_NETWORK, PATH_DESC, PREV_POINT, THIS_POINT, POST_POINT, FLOW_VIA_PATH, INPUT_FIELD_BOUNDARIES, CONNECTED_FIELD_ID, FLOW_VIA_BOUNDARY, FLOW_DOWN_STEEPEST, FLOW_INTO_BLIND_PIT, ROUTE_ROAD, ROUTE_PATH
from layers import AddFlowMarkerPoint, AddFlowLine
from searches import FindSteepestAdjacent, FindSegmentIntersectionWithWatercourse, FindSteepestSegment, FindNearbyFlowLine, FindNearbyFieldObservation, CanOverflowTo
from utils import GetPointsOnLine, GetCentroidOfContainingDEMCell, DisplayOS, GetRasterElev, CalcZCrossProduct, GetSteeperOfTwoLines, ToSentenceCase

# pylint: disable=too-many-lines


#======================================================================================================================
#
# Returns the coords (external CRS) of the centroid of the pixel containing the highest point and lowest point on a field boundary
#
#======================================================================================================================
def GetHighestAndLowestPointsOnFieldBoundary(fieldBoundary):
   # pylint: disable=too-many-locals
   # pylint: disable=too-many-nested-blocks

   maxElev = -9999
   maxElevX = -1
   maxElevY = -1
   minElev = 9999
   minElevX = -1
   minElevY = -1

   polyGeom = fieldBoundary.geometry()
   if polyGeom.isMultipart():
      polygons = polyGeom.asMultiPolygon()
   else:
      polygons = [polyGeom.asPolygon()]

   # If this is a multipolygon, we only consider the first polygon here
   polyBoundary = polygons[0]
   #print(len(polyBoundary))
   #print(str(polyBoundary))

   for point in polyBoundary:
      for j in range(len(point) - 1):
         thisBoundaryPointX = point[j][0]
         thisBoundaryPointY = point[j][1]

         nextBoundaryPointX = point[j+1][0]
         nextBoundaryPointY = point[j+1][1]

         inBetweenPoints = GetPointsOnLine(QgsPointXY(thisBoundaryPointX, thisBoundaryPointY), QgsPointXY(nextBoundaryPointX, nextBoundaryPointY), shared.resolutionOfDEM)
         #print("From " + DisplayOS(thisBoundaryPointX, thisBoundaryPointY) + " to " + DisplayOS(nextBoundaryPointX, nextBoundaryPointY))
         #print("in-between points are " + str(inBetweenPoints))
         #print("")

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
                  pixelCentroidPoint = GetCentroidOfContainingDEMCell(boundaryPoint.x(), boundaryPoint.y())
                  #print("{" + str(boundaryPoint.x()) + ", " + str(boundaryPoint.y()) + "} and {" + str(pixelCentroidPoint.x()) + ", " + str(pixelCentroidPoint.y()) + "}")

                  # Now look up the elevation value at the centroid point
                  result = provider.identify(pixelCentroidPoint, QgsRaster.IdentifyFormatValue, extent, xSize, ySize, dpi)
                  error = result.error()
                  if not error.isEmpty() or not result.isValid():
                     shared.fpOut.write(error.summary())
                     return -1, -1, -1

                  # We have a valid result, so get the elevation. First get this as a dict of key-value pairs
                  dictResults = result.results()

                  # Now get the first value from the dict (assume we only have a single band)
                  elevList = list(dictResults.values())
                  elev = elevList[0]
                  #print(elev)

                  # However some results are from a 'wrong' sheet (i.e. a sheet which does not contain this point), so ignore these results
                  if elev != None:
                     if elev > maxElev:
                        maxElev = elev
                        maxElevX = pixelCentroidPoint.x()
                        maxElevY = pixelCentroidPoint.y()

                     if elev < minElev:
                        minElev = elev
                        minElevX = pixelCentroidPoint.x()
                        minElevY = pixelCentroidPoint.y()

   #print("Returning " + str(maxElevX) + ", " + str(maxElevY) + ", " + str(maxElev))
   return maxElevX, maxElevY, maxElev, minElevX, minElevY, minElev
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
#  4 = flow along road, can continue to flow along roads
#  5 = flow along path, can continue to flow along paths/tracks
#
#======================================================================================================================
def FlowViaFieldObservation(indx, fieldCode, thisPoint, elev):
   # pylint: disable=too-many-statements
   # pylint: disable=too-many-return-statements
   # pylint: disable=too-many-branches

   #shared.fpOut.write("Entered FlowViaFieldObservation() at " + DisplayOS(thisPoint.x(), thisPoint.y(), False) + ", field observation for location " + DisplayOS(shared.fieldObservationFlowFrom[indx].x(), shared.fieldObservationFlowFrom[indx].y(), False) + "\n")
   #shared.fpOut.write(shared.fieldObservationFlowTo)
   if not shared.fieldObservationFlowTo[indx]:
      # The outflow location is not known, so we have flow along a road, or along a path, or along a field boundary
      if shared.fieldObservationCategory[indx] == FIELD_OBS_CATEGORY_ROAD:
         if shared.fieldObservationBehaviour[indx] == FIELD_OBS_BEHAVIOUR_ALONG:
            #shared.fpOut.write("Flow along road")
            AddFlowMarkerPoint(thisPoint, MARKER_ROAD, fieldCode, -1)

            rtn, point = FlowAlongVectorRoute(ROUTE_ROAD, indx, fieldCode, thisPoint)
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

            elif rtn == 4:
               # Flow has reached the beginning or end of the road, so carry on flowing along any other nearby roads
               shared.fpOut.write("\tFinished flow along road A at " + DisplayOS(point.x(), point.y()) + " called from FlowViaFieldObservation(), rtn = 4\n")
               return 4, point

            else:
               # Carry on with downhill flow from this point
               return 0, point

         elif shared.fieldObservationBehaviour[indx] == FIELD_OBS_BEHAVIOUR_LEAVE:
            # Carry on with downhill flow from this point
            return 0, point

      elif shared.fieldObservationCategory[indx] == FIELD_OBS_CATEGORY_PATH:
         if shared.fieldObservationBehaviour[indx] == FIELD_OBS_BEHAVIOUR_ALONG:
            #shared.fpOut.write("Flow along path\n")
            AddFlowMarkerPoint(thisPoint, MARKER_PATH, fieldCode, -1)

            rtn, point = FlowAlongVectorRoute(ROUTE_PATH, indx, fieldCode, thisPoint)
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

            elif rtn == 4:
               # Flow has reached the beginning or end of the path, so carry on flowing along any other nearby paths
               shared.fpOut.write("\tFinished flow along path A at " + DisplayOS(point.x(), point.y()) + " called from FlowViaFieldObservation(), rtn = 4\n")
               return 5, point

            else:
               # Carry on with downhill flow from this point
               return 0, point

         elif shared.fieldObservationBehaviour[indx] == FIELD_OBS_BEHAVIOUR_LEAVE:
            # Carry on with downhill flow from this point
            return 0, point

      elif shared.fieldObservationCategory[indx] == FIELD_OBS_CATEGORY_BOUNDARY:
         if shared.fieldObservationBehaviour[indx] == FIELD_OBS_BEHAVIOUR_ALONG:
            #shared.fpOut.write("Flow along field boundary\n")
            AddFlowMarkerPoint(thisPoint, MARKER_FIELD_BOUNDARY, fieldCode, -1)

            rtn, point = flowAlongVectorFieldBoundary(indx, fieldCode, thisPoint)
            #shared.fpOut.write("rtn = " + str(rtn) + ", point = " + DisplayOS(point.x(), point.y()) + "\n")
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
               # Carry on with downhill flow from this point
               return 0, point

         elif shared.fieldObservationBehaviour[indx] == FIELD_OBS_BEHAVIOUR_LEAVE:
            # Carry on with downhill flow from this point
            return 0, point

      else:
         printStr = "ERROR: must have a 'To' location for field observation " + str(indx) + " '" + shared.fieldObservationCategory[indx] + shared.fieldObservationBehaviour[indx] + "' '" + shared.fieldObservationDescription[indx] + "', in flow from field " + str(fieldCode) + " at "+ DisplayOS(shared.fieldObservationFlowFrom[indx].x(), shared.fieldObservationFlowFrom[indx].y()) + "\n"
         shared.fpOut.write(printStr)
         print(printStr)

         return -1, -1

   # We do have an outflow location: OK, show some marker points
   if shared.fieldObservationCategory[indx] == FIELD_OBS_CATEGORY_CULVERT:
      AddFlowMarkerPoint(QgsPointXY(shared.fieldObservationFlowFrom[indx].x(), shared.fieldObservationFlowFrom[indx].y()), MARKER_ENTER_CULVERT, fieldCode, -1)

   elif shared.fieldObservationCategory[indx] == FIELD_OBS_CATEGORY_PATH:
      AddFlowMarkerPoint(QgsPointXY(shared.fieldObservationFlowFrom[indx].x(), shared.fieldObservationFlowFrom[indx].y()), MARKER_PATH, fieldCode, -1)

   elif shared.fieldObservationCategory[indx] == FIELD_OBS_CATEGORY_ROAD:
      AddFlowMarkerPoint(QgsPointXY(shared.fieldObservationFlowFrom[indx].x(), shared.fieldObservationFlowFrom[indx].y()), MARKER_ROAD, fieldCode, -1)

   printStr = "\tFlow from field " + fieldCode + " routed '" + shared.fieldObservationBehaviour[indx] + " " + shared.fieldObservationCategory[indx] + " " + shared.fieldObservationDescription[indx] + "' from " + DisplayOS(thisPoint.x(), thisPoint.y())
   if thisPoint != shared.fieldObservationFlowFrom[indx]:
      printStr += " via " + DisplayOS(shared.fieldObservationFlowFrom[indx].x(), shared.fieldObservationFlowFrom[indx].y())
   printStr += " to " + DisplayOS(shared.fieldObservationFlowTo[indx].x(), shared.fieldObservationFlowTo[indx].y())
   printStr += "\n"
   shared.fpOut.write(printStr)

   shared.thisFieldFieldObsAlreadyFollowed.append(indx)

   if thisPoint != shared.fieldObservationFlowFrom[indx]:
      AddFlowLine(thisPoint, shared.fieldObservationFlowFrom[indx], " near to " + shared.fieldObservationDescription[indx], fieldCode, elev)
   AddFlowLine(shared.fieldObservationFlowFrom[indx], shared.fieldObservationFlowTo[indx], shared.fieldObservationDescription[indx], fieldCode, -1)

   ## TEST add intermediate points to thisFieldFlowLine and thisFieldFlowLineFieldCode, to prevent backtracking
   #tempPoints = []
   #if thisPoint != shared.fieldObservationFlowFrom[indx]:
      #tempPoints += GetPointsOnLine(thisPoint, shared.fieldObservationFlowFrom[indx], shared.resolutionOfDEM)
   #tempPoints += GetPointsOnLine(shared.fieldObservationFlowFrom[indx], shared.fieldObservationFlowTo[indx], shared.resolutionOfDEM)

   #inBetweenPoints = []
   #for point in tempPoints:
      #inBetweenPoints.append(GetCentroidOfContainingDEMCell(point.x(), point.y()))

   #inBetweenPointsFieldCode = [fieldCode] * len(inBetweenPoints)

   #shared.thisFieldFlowLine += inBetweenPoints
   #shared.thisFieldFlowLineFieldCode += inBetweenPointsFieldCode

   #printStr = ""
   #for i in shared.thisFieldFlowLine:
      #printStr += DisplayOS(i.x(), i.y())
      #printStr += " "
   #shared.fpOut.write(printStr)

   return 0, shared.fieldObservationFlowTo[indx]
#======================================================================================================================


#======================================================================================================================
#
# Routes flow downhill along a vector representation of a route (either a road or a path)
#
#======================================================================================================================
def FlowAlongVectorRoute(RoadOrPath, indx, fieldCode, thisPoint):
   # pylint: disable=too-many-locals
   # pylint: disable=too-many-nested-blocks
   # pylint: disable=too-many-return-statements
   # pylint: disable=too-many-branches
   # pylint: disable=too-many-statements

   if RoadOrPath == ROUTE_ROAD:
      inputNetwork = INPUT_ROAD_NETWORK
      routeType = "road"
      flowMarker = FLOW_VIA_ROAD

   elif RoadOrPath == ROUTE_PATH:
      inputNetwork = INPUT_PATH_NETWORK
      routeType = "path"
      flowMarker = FLOW_VIA_PATH

   DEPTH_TOLERANCE = 0.5   # Vertical (depth) tolerance in metres

   if indx >= 0:
      shared.thisFieldFieldObsAlreadyFollowed.append(indx)

   #shared.fpOut.write("Entered FlowAlongVectorRoute at point " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n")
   layerNum = -1

   # Find the route network layer
   routeLayerFound = False
   for layerNum in range(len(shared.vectorInputLayersCategory)):
         if shared.vectorInputLayersCategory[layerNum] == inputNetwork:
            routeLayerFound = True
            break
         # Safety check
   if not routeLayerFound:
      printStr = "ERROR: opening " + routeType + " network layer\n"
      shared.fpOut.write(printStr)
      print(printStr)

      return -1, -1

   numberToSearchFor = 4

   while True:
      # Find the nearest route segments
      #shared.fpOut.write("Start of FlowAlongVectorRoute loop at " + DisplayOS(thisPoint.x(), thisPoint.y()))
      nearestIDs = shared.vectorInputLayerIndex[layerNum].nearestNeighbor(QgsPointXY(thisPoint), numberToSearchFor)
      #if len(nearestIDs) > 0:
         #print("Nearest " + routeType + " segment IDs (1) = " + str(nearestIDs))

      request = QgsFeatureRequest().setFilterFids(nearestIDs)
      features = shared.vectorInputLayers[layerNum].getFeatures(request)

      routeSegData = []
      geomPoint = QgsGeometry.fromPointXY(QgsPointXY(thisPoint))

      for routeSeg in features:
         # Is this route segment both close enough, and has not already been tried?
         geomSeg = routeSeg.geometry()
         geomNearPoint = geomSeg.nearestPoint(geomPoint)
         nearPoint = geomNearPoint.asPoint()
         distanceToSeg = geomPoint.distance(geomNearPoint)
         segID = routeSeg.id()
         #shared.fpOut.write("\t" + routeType + " segID = " + str(segID) + ", nearest point = " + DisplayOS(nearPoint.x(), nearPoint.y()) + ", distanceToSeg = " + str(distanceToSeg) + "\n")

         if distanceToSeg > shared.searchDist:
            # Too far away, so forget about this route segment
            shared.fpOut.write("\t" + ToSentenceCase(routeType) + " segment " + str(segID) + " is too far away (" + "{:0.1f}".format(distanceToSeg) + " m)\n")

            continue

         if segID in shared.thisFieldRoadSegIDsTried:
            # Already travelled, so forget about this route segment
            shared.fpOut.write("\t" + ToSentenceCase(routeType) + " segment " + str(segID) + " has already had flow along it\n")

            continue

         # Is OK, so calculate the gradient that flow would take along this route segment
         nearPointElev = GetRasterElev(nearPoint.x(), nearPoint.y())

         if geomSeg.isMultipart():
            lineVertAll = geomSeg.asMultiPolyline()
         else:
            lineVertAll = [geomSeg.asPolyline()]

         # We only consider the first polyline here
         lineVert = lineVertAll[0]

         #shared.fpOut.write("Points in lineVert 1\n")
         #for pt in lineVert:
            #shared.fpOut.write(DisplayOS(pt.x(), pt.y()) + "\n")

         # Find the closest segment of the route polyline
         _sqrDist, _minDistPoint, afterVertex, _leftOf = geomSeg.closestSegmentWithContext(nearPoint)

         afterVertexPoint = geomSeg.vertexAt(afterVertex)
         afterVertexElev = GetRasterElev(afterVertexPoint.x(), afterVertexPoint.y())

         prevVertex = afterVertex - 1
         prevVertexPoint = geomSeg.vertexAt(prevVertex)
         prevVertexElev = GetRasterElev(prevVertexPoint.x(), prevVertexPoint.y())

         xDistPrevToNear = abs(prevVertexPoint.x() - nearPoint.x())
         yDistPrevToNear = abs(prevVertexPoint.y() - nearPoint.y())
         xDistAfterToNear = abs(afterVertexPoint.x() - nearPoint.x())
         yDistAfterToNear = abs(afterVertexPoint.y() - nearPoint.y())

         distPrevToNear = sqrt((xDistPrevToNear * xDistPrevToNear) + (yDistPrevToNear * yDistPrevToNear))
         distAfterToNear = sqrt((xDistAfterToNear * xDistAfterToNear) + (yDistAfterToNear * yDistAfterToNear))

         elevDiffPrevToNear = nearPointElev - prevVertexElev
         elevDiffAfterToNear = nearPointElev - afterVertexElev

         gradientPrevToNear = gradientAfterToNear = 0

         if distPrevToNear > 0:
            gradientPrevToNear = elevDiffPrevToNear / distPrevToNear

         if distAfterToNear > 0:
            gradientAfterToNear = elevDiffAfterToNear / distAfterToNear

         #shared.fpOut.write("\t" + ToSentenceCase(routeType) + " segment " + str(segID) + ", gradientPrevToNear = " + str(gradientPrevToNear) + ", gradientAfterToNear = " + str(gradientAfterToNear) + "\n")
         maxGradient = max(gradientPrevToNear, gradientAfterToNear)

         # save the route segment feature, the nearest point, the distance to the nearest point, and 1 - max gradient
         routeSegData.append([routeSeg, nearPoint, distanceToSeg, 1 - maxGradient, lineVert, prevVertex, prevVertexPoint, prevVertexElev, afterVertex, afterVertexPoint, afterVertexElev])
         #shared.fpOut.write("\t" + str(routeSegData[-1]) + "\n")

      # Did we any find suitable route segments?
      if not routeSegData:
         # Nope
         shared.fpOut.write("No untravelled " + routeType + " segments nearby: flow along " + routeType + " from field " + str(fieldCode) + " ends at " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n*** Please add a field observation\n")
         return 1, thisPoint

      # OK we have some possibly suitable route segments
      #for n in range(len(routeSegData)):
         #shared.fpOut.write("\tBefore " + str(n) + " " + str(routeSegData[n][0].id()) + " " + DisplayOS(routeSegData[n][1].x(), routeSegData[n][1].y()) + " " + str(routeSegData[n][2]) + " m " + str(routeSegData[n][3]) + "\n")

      # Sort the list of untravelled route segments, shortest distance first, then (1 - max gradient) first
      routeSegData.sort(key = itemgetter(2, 3))

      #for n in range(len(routeSegData)):
         #shared.fpOut.write("\tAfter " + str(n) + " " + str(routeSegData[n][0].id()) + " " + DisplayOS(routeSegData[n][1].x(), routeSegData[n][1].y()) + " " + str(routeSegData[n][2]) + " m " + str(routeSegData[n][3]) + "\n")

      flowRouted = False
      flowTowardsAfterVertex = None
      lineVert = None

      for routeSeg in routeSegData:
         # Go through this list of untravelled route segments till we find a suitable one
         feature = routeSeg[0]
         featID = feature.id()
         nearPoint = routeSeg[1]
         nearPointElev = GetRasterElev(nearPoint.x(), nearPoint.y())
         lineVert = routeSeg[4]

         #geomSeg = feature.geometry()
         #if geomSeg.isMultipart():
            #lineVertAll = geomSeg.asMultiPolyline()
         #else:
            #lineVertAll = [geomSeg.asPolyline()]

         ## We only consider the first polyline here
         #lineVert = lineVertAll[0]

         if RoadOrPath == ROUTE_ROAD:
            featCode = feature[OS_VECTORMAP_FEAT_CODE]
            featDesc = feature[OS_VECTORMAP_FEAT_DESC]
            roadName = feature[OS_VECTORMAP_ROAD_NAME]
            roadNumber = feature[OS_VECTORMAP_ROAD_NUMBER]

            fullDesc = "'" + str(featCode) + " " + str(featDesc) + " " + str(roadName) + " " + str(roadNumber) + "'"

         elif RoadOrPath == ROUTE_PATH:
            featDesc = feature[PATH_DESC]

            fullDesc = "'" + str(featDesc) + "'"

         shared.fpOut.write("\tTrying " + routeType + " segment " + str(featID) + " " + fullDesc + " with nearest point at " + DisplayOS(nearPoint.x(), nearPoint.y()) + " and distance to nearest point = " + "{:0.1f}".format(routeSeg[2]) + " m\n")

         #shared.fpOut.write("Points in lineVert 2\n")
         #for pt in lineVert:
            #shared.fpOut.write(DisplayOS(pt.x(), pt.y()) + "\n")

         prevVertex = routeSeg[5]
         prevVertexPoint = routeSeg[6]
         prevVertexElev = routeSeg[7]
         afterVertex = routeSeg[8]
         afterVertexPoint = routeSeg[9]
         afterVertexElev = routeSeg[10]

         #shared.fpOut.write("\t" + DisplayOS(prevVertexPoint.x(), prevVertexPoint.y(), False) + " " + DisplayOS(nearPoint.x(), nearPoint.y(), False) + " " + DisplayOS(afterVertexPoint.x(), afterVertexPoint.y(), False) + "\n")

         # Are the near and previous points co-incident?
         if isclose(prevVertexPoint.x(), nearPoint.x()) and isclose(prevVertexPoint.y(), nearPoint.y()):
            # The nearest point on the route segment is co-incident with the 'previous' vertex, so we only need check the elevation of the 'after' vertex
            if nearPointElev + DEPTH_TOLERANCE > afterVertexElev:
               # Flow towards 'after' vertex
               flowTowardsAfterVertex = True
               #shared.fpOut.write("\tFlow is towards ascending vertex numbers for this " + routeType + " (a)\n")

               printStr = "Flow from field " + fieldCode + " enters the " + routeType + " segment " + str(featID) + " " + fullDesc + " at " + DisplayOS(thisPoint.x(), thisPoint.y()) + " A "
               shared.fpOut.write("\t" + printStr + "\n")

               thisPointElev = GetRasterElev(thisPoint.x(), thisPoint.y())
               AddFlowMarkerPoint(thisPoint, flowMarker, fieldCode, thisPointElev)

               if not (isclose(thisPoint.x(), nearPoint.x()) and isclose(thisPoint.y(), nearPoint.y())):
                  shared.fpOut.write("\tFlow from field " + str(fieldCode) + " onto " + routeType + ", from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to " + DisplayOS(nearPoint.x(), nearPoint.y()) + " A\n")
                  AddFlowLine(thisPoint, nearPoint, flowMarker, fieldCode, thisPointElev)

               startVert = prevVertex
               firstPoint = prevVertexPoint
               secondPoint = afterVertexPoint
               flowRouted = True

               # Forget about the rest of the list of untravelled route segments since we have found a suitable route segment
               break

         # Are the near and after points co-incident?
         if isclose(afterVertexPoint.x(), nearPoint.x()) and isclose(afterVertexPoint.y(), nearPoint.y()):
            # The nearest point on the route segment is co-incident with the 'after' vertex, so we only need check the elevation of the 'previous' vertex
            if nearPointElev + DEPTH_TOLERANCE > prevVertexElev:
               # Flow towards 'previous' vertex
               flowTowardsAfterVertex = False
               #shared.fpOut.write("\tFlow is towards descending vertex numbers for this " + routeType + " (a)\n")

               printStr = "Flow from field " + fieldCode + " enters the " + routeType + " segment " + str(featID) + " " + fullDesc + " at " + DisplayOS(thisPoint.x(), thisPoint.y()) + " B "
               shared.fpOut.write("\t" + printStr + "\n")

               thisPointElev = GetRasterElev(thisPoint.x(), thisPoint.y())
               AddFlowMarkerPoint(thisPoint, flowMarker, fieldCode, thisPointElev)

               if not (isclose(thisPoint.x(), nearPoint.x()) and isclose(thisPoint.y(), nearPoint.y())):
                  shared.fpOut.write("\tFlow from field " + str(fieldCode) + " onto " + routeType + ", from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to " + DisplayOS(nearPoint.x(), nearPoint.y()) + " B\n")
                  AddFlowLine(thisPoint, nearPoint, flowMarker, fieldCode, thisPointElev)

               startVert = afterVertex
               firstPoint = afterVertexPoint
               secondPoint = prevVertexPoint
               flowRouted = True

               # Forget about the rest of the list of untravelled route segments since we have found a suitable route segment
               break

         # The nearest point is not co-incident with either the 'previous' or 'after' vertices, so determine the flow direction
         prevBelow = False
         afterBelow = False

         if nearPointElev + DEPTH_TOLERANCE > prevVertexElev:
            prevBelow = True

         if nearPointElev + DEPTH_TOLERANCE > afterVertexElev:
            afterBelow = True

         if afterBelow and not prevBelow:
            # Flow is towards the 'after' vertex
            flowTowardsAfterVertex = True
            #shared.fpOut.write("\tFlow is towards ascending vertex numbers for this road (a)\n")

            printStr = "Flow from field " + fieldCode + " enters the " + routeType + "  segment " + str(featID) + " " + fullDesc + " at " + DisplayOS(thisPoint.x(), thisPoint.y()) + " C "
            shared.fpOut.write("\t" + printStr + "\n")

            thisPointElev = GetRasterElev(thisPoint.x(), thisPoint.y())
            AddFlowMarkerPoint(thisPoint, flowMarker, fieldCode, thisPointElev)

            if not (isclose(thisPoint.x(), nearPoint.x()) and isclose(thisPoint.y(), nearPoint.y())):
               shared.fpOut.write("\tFlow from field " + str(fieldCode) + " onto " + routeType + ", from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to " + DisplayOS(nearPoint.x(), nearPoint.y()) + " C\n")
               AddFlowLine(thisPoint, nearPoint, flowMarker, fieldCode, thisPointElev)

            startVert = prevVertex
            firstPoint = nearPoint
            secondPoint = afterVertexPoint
            flowRouted = True

            # Forget about the rest of the list of untravelled route segments since we have found a suitable route segment
            break

         elif prevBelow and not afterBelow:
            # Flow is towards the 'previous' vertex
            flowTowardsAfterVertex = False
            #shared.fpOut.write("\tFlow is towards descending vertex numbers for this " + routeType + " (b)\n")

            printStr = "Flow from field " + fieldCode + " enters the " + routeType + "  segment " + str(featID) + " " + fullDesc + " at " + DisplayOS(thisPoint.x(), thisPoint.y()) + " D "
            shared.fpOut.write("\t" + printStr + "\n")

            thisPointElev = GetRasterElev(thisPoint.x(), thisPoint.y())
            AddFlowMarkerPoint(thisPoint, flowMarker, fieldCode, thisPointElev)

            if not (isclose(thisPoint.x(), nearPoint.x()) and isclose(thisPoint.y(), nearPoint.y())):
               shared.fpOut.write("\tFlow from field " + str(fieldCode) + " onto " + routeType + ", from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to " + DisplayOS(nearPoint.x(), nearPoint.y()) + " D\n")
               AddFlowLine(thisPoint, nearPoint, FlowMarker, fieldCode, thisPointElev)

            startVert = afterVertex
            firstPoint = nearPoint
            secondPoint = prevVertexPoint
            flowRouted = True

            # Forget about the rest of the list of untravelled route segments since we have found a suitable route segment
            break

         elif not prevBelow and not afterBelow:
            # We are in a blind pit, so try the next route segment in the list of untravelled route segments
            shared.fpOut.write("\tIn " + routeType + " blind pit for " + routeType + " segment " + str(featID) + " " + fullDesc + ", downhill flow ends at " + DisplayOS(nearPoint.x(), nearPoint.y()) + ", abandoning\n")
            shared.fpOut.write(str(prevVertexElev) + " " + str(nearPointElev) + " " + str(afterVertexElev) + "\n")

            if RoadOrPath == ROUTE_ROAD:
               shared.thisFieldRoadSegIDsTried.append(featID)
            elif RoadOrPath == ROUTE_PATH:
               shared.thisFieldPathSegIDsTried.append(featID)

            continue

         # Must be prevBelow and AfterBelow so find steepest
         previousIsSteepest = GetSteeperOfTwoLines(prevVertexPoint, prevVertexElev, nearPoint, nearPointElev, afterVertexPoint, afterVertexElev)
         #shared.fpOut.write("\tpreviousIsSteepest = " + str(previousIsSteepest) + "\n")

         if previousIsSteepest:
            #shared.fpOut.write("\tFlow is towards descending vertex numbers for this " + routeType + " (c)\n")
            flowTowardsAfterVertex = False

            printStr = "Flow from field " + fieldCode + " enters the " + routeType + " segment " + str(featID) + " " + fullDesc + " at " + DisplayOS(thisPoint.x(), thisPoint.y()) + " E "
            shared.fpOut.write("\t" + printStr + "\n")

            thisPointElev = GetRasterElev(thisPoint.x(), thisPoint.y())
            AddFlowMarkerPoint(thisPoint, flowMarker, fieldCode, thisPointElev)

            if not (isclose(thisPoint.x(), nearPoint.x()) and isclose(thisPoint.y(), nearPoint.y())):
               shared.fpOut.write("\tFlow from field " + str(fieldCode) + " onto " + routeType + ", from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to " + DisplayOS(nearPoint.x(), nearPoint.y()) + " E\n")
               AddFlowLine(thisPoint, nearPoint, flowMarker, fieldCode, thisPointElev)

            startVert = afterVertex
            firstPoint = nearPoint
            secondPoint = prevVertexPoint

         else:
            #shared.fpOut.write("\tFlow is towards ascending vertex numbers for this " + routeType + " (d)\n")
            flowTowardsAfterVertex = True

            printStr = "Flow from field " + fieldCode + " onto the " + routeType + " segment " + str(featID) + " " + fullDesc + " at " + DisplayOS(thisPoint.x(), thisPoint.y()) + " F "
            shared.fpOut.write("\t" + printStr + "\n")

            thisPointElev = GetRasterElev(thisPoint.x(), thisPoint.y())
            AddFlowMarkerPoint(thisPoint, flowMarker, fieldCode, thisPointElev)

            if not (isclose(thisPoint.x(), nearPoint.x()) and isclose(thisPoint.y(), nearPoint.y())):
               shared.fpOut.write("\tFlow from field " + str(fieldCode) + " along " + routeType + ", from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to " + DisplayOS(nearPoint.x(), nearPoint.y()) + " F\n")
               AddFlowLine(thisPoint, nearPoint, flowMarker, fieldCode, thisPointElev)

            startVert = prevVertex
            firstPoint = nearPoint
            secondPoint = afterVertexPoint

         # Forget about the rest of the list of untravelled route segments since we have found a suitable route segment
         flowRouted = True
         break

      # ===============================================================================================================
      if flowRouted:
         # OK we have found a suitable route segment: thisVertex is the start of flow along this segment, nextVertex is the end of flow along this segment. We know the initial direction of flow along this road, so keep going downhill till we reach a pre-existing flow line, a watercourse, a blind pit, or the end of the road
         if RoadOrPath == ROUTE_ROAD:
            shared.thisFieldRoadSegIDsTried.append(featID)
         elif RoadOrPath == ROUTE_PATH:
            shared.thisFieldPathSegIDsTried.append(featID)

         #printStr = "\tstartVert = " + str(startVert)
         #if flowTowardsAfterVertex:
            #printStr += ", flow towards 'after' vertex"
         #else:
            #printStr += ", flow towards 'previous' vertex"
         #shared.fpOut.write(printStr + "\n")

         #shared.fpOut.write("Points in lineVert 3\n")
         #for pt in lineVert:
            #shared.fpOut.write(DisplayOS(pt.x(), pt.y()) + "\n")

         nVert = len(lineVert)
         if flowTowardsAfterVertex:
            # Flow goes towards the last vertex of the route segment
            for nn in range(startVert, nVert-1):
               # Are we doing the first line, which joins nearPoint to the 'after' vertex?
               if nn == startVert:
                  thisVertex = firstPoint
                  nextVertex = secondPoint
               else:
                  thisVertex = lineVert[nn]
                  nextVertex = lineVert[nn+1]

               #shared.fpOut.write("\tthisVertex[" + str(nn) + "] = " + DisplayOS(thisVertex.x(), thisVertex.y()) + ", nextVertex[" + str(nn+1) + "] = " + DisplayOS(nextVertex.x(), nextVertex.y()) + "\n")

               # This can happen sometimes
               if isclose(thisVertex.x(), nextVertex.x()) and isclose(thisVertex.y(), nextVertex.y()):
                  continue

               thisVertexElev = GetRasterElev(thisVertex.x(), thisVertex.y())
               nextVertexElev = GetRasterElev(nextVertex.x(), nextVertex.y())

               # Is nextVertex lower than thisVertex?
               if nextVertexElev > thisVertexElev + DEPTH_TOLERANCE:
                  # The next vertex point is not downhill, so stop flowing along this route segment
                  AddFlowMarkerPoint(thisVertex, FLOW_INTO_BLIND_PIT, fieldCode, -1)
                  shared.fpOut.write("\tFlow from field " + fieldCode + " hit a blind pit in " + routeType + " segment " + str(featID) + " " + fullDesc + " at " + DisplayOS(thisVertex.x(), thisVertex.y()) + "\n")

                  return 1, thisPoint

               # OK, the route segment is, overall, downhill. Now get a list of the along-segment points, i.e. between thisVertex and nextVertex
               betweenPoints = GetPointsOnLine(thisVertex, nextVertex, shared.resolutionOfDEM)
               shared.fpOut.write(str(betweenPoints) + "\n")
               nBetween = len(betweenPoints) - 1
               for p in range(0, nBetween):
                  # Look at every pair of points
                  thisPoint = betweenPoints[p]
                  nextPoint = betweenPoints[p+1]
                  thisPointElev = GetRasterElev(thisPoint.x(), thisPoint.y())
                  nextPointElev = GetRasterElev(nextPoint.x(), nextPoint.y())

                  # Check to see whether this section of the route segment intersects a watercourse segment (note that we have not yet checked whether the next point is downhill from this point, but is a reasonable assumption that any intersect point must be downhill from this point)
                  #shared.fpOut.write("\tthisPoint = " + DisplayOS(thisPoint.x(), thisPoint.y()) + ", nextPoint = " + DisplayOS(nextPoint.x(), nextPoint.y()) + "\n")
                  geomLine = QgsGeometry.fromPolyline([QgsPoint(thisPoint), QgsPoint(nextPoint)])
                  rtn = -1
                  streamIntersectPoints = []
                  rtn, streamIntersectPoints = FindSegmentIntersectionWithWatercourse(geomLine)
                  if rtn == -1:
                     # Error
                     return -1, -1

                  elif rtn == 1:
                     # We have at least one intersection
                     #shared.fpOut.write("\tstreamIntersectPoints = " + str(streamIntersectPoints) + "\n")
                     for intPoint in streamIntersectPoints:
                        AddFlowLine(thisPoint, intPoint, flowMarker, fieldCode, -1)

                        # NOTE we are only considering the first intersection point
                        #shared.fpOut.write("AAA Intersection with stream found, added flowline from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to " + DisplayOS(intPoint.x(), intPoint.y()) + "\n")
                        return 2, intPoint

                  # Next check to see whether the next point is a blind pit
                  #if nextPointElev > thisPointElev + DEPTH_TOLERANCE:
                     ## The next point is not downhill, so stop flowing along this route segment
                     #AddFlowMarkerPoint(thisPoint, FLOW_INTO_BLIND_PIT, fieldCode, -1)
                     #shared.fpOut.write("\tFlow from field " + fieldCode + " hit a blind pit in " + routeType + " segment " + str(featID) + " " + fullDesc + " at " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n")

                     #return 1, thisPoint

                  # Check for pre-existing flow lines near the next point
                  adjX, adjY, hitFieldFlowFrom = FindNearbyFlowLine(nextPoint)
                  if adjX != -1:
                     # There is an adjacent flow line, so merge the two and finish with this flow line
                     adjPoint = QgsPointXY(adjX, adjY)
                     AddFlowLine(thisPoint, adjPoint, MERGED_WITH_ADJACENT_FLOWLINE, fieldCode, -1)

                     shared.fpOut.write("Flow from field " + fieldCode + " hit flow from field " + str(hitFieldFlowFrom) + " at " + DisplayOS(adjX, adjY) + " while moving along " + routeType + " segment " + str(featID) + " " + fullDesc + ", so stopped tracing flow from this field\n")

                     return 3, adjPoint

                  # Do we have a field observation near the next point?
                  indx = FindNearbyFieldObservation(nextPoint)
                  if indx != -1:
                     # We have found a field observation near the next point, so flow to the field observation
                     fieldObsStartPoint = shared.fieldObservationFlowFrom[indx]
                     AddFlowLine(thisPoint, fieldObsStartPoint, flowMarker, fieldCode, -1)

                     shared.fpOut.write("\tFlow from field " + str(fieldCode) + " along " + routeType + " segment " + str(featID) + " " + fullDesc + " from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to field observation at " + DisplayOS(fieldObsStartPoint.x(), fieldObsStartPoint.y()) + ", nn = " + str(nn) + " of " + str(nVert) + ", p = " + str(p) + " of " + str(nBetween) + "\n")

                     # Now route flow via the field observation
                     rtn, adjPoint = FlowViaFieldObservation(indx, fieldCode, nextPoint, nextPointElev)
                     if rtn == 0:
                        # Flow has passed through the field observation
                        #shared.fpOut.write("Left FlowViaFieldObservation() called in FlowAlongVectorRoute() 1, rtn = " + str(rtn) + "\n")
                        return rtn, adjPoint

                     elif rtn == -1:
                        # Could not determine the field observation's outflow location
                        shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(nextPoint.x(), nextPoint.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + ", could not determine outflow location\n")
                        return rtn, thisPoint

                     elif rtn == 1:
                        # Flow has passed through the field observation and then hit a blind pit
                        shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(nextPoint.x(), nextPoint.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + ", hit blind pit\n")
                        return rtn, thisPoint

                     elif rtn == 2:
                        # Flow has passed through the field observation and then  hit a stream
                        shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(nextPoint.x(), nextPoint.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + " stream\n")
                        return rtn, thisPoint

                     elif rtn == 3:
                        # Flow has passed through the field observation and then merged with pre-existing flow
                        shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(nextPoint.x(), nextPoint.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + ", merged with pre-existing flow\n")
                        return rtn, thisPoint

                     elif rtn == 4:
                        # Flow has passed through the field observation and is flowing along a road
                        shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(nextPoint.x(), nextPoint.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + ", flowed along " + routeType + " so looking for roads AAA\n")
                        return rtn, thisPoint

                  # So flow downhill along this part of thee route segment
                  AddFlowLine(thisPoint, nextPoint, flowMarker, fieldCode, -1)

                  shared.fpOut.write("\tFlow from field " + str(fieldCode) + " downhill along " + routeType + " segment " + str(featID) + " " + fullDesc + ", from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to " + DisplayOS(nextPoint.x(), nextPoint.y()) + ", nn = " + str(nn) + " of " + str(nVert) + ", p = " + str(p) + " of " + str(nBetween) + " A\n")

            # Have finished all segments of the route
            shared.fpOut.write("\tFlow from field " + str(fieldCode) + " at vertex[" + str(nVert-1) + "] of " + routeType + " segment " + str(featID) + " " + fullDesc + " " + DisplayOS(lineVert[nVert-1].x(), lineVert[nVert-1].y()) + "\n")

            return 4, lineVert[nVert-1]

         else:
            # Flow goes towards the first point of the route segment
            for nn in range(startVert, 0, -1):
               # Are we doing the first line, which joins nearPoint to the 'previous' vertex?
               if nn == startVert:
                  thisVertex = firstPoint
                  nextVertex = secondPoint
               else:
                  thisVertex = lineVert[nn]
                  nextVertex = lineVert[nn-1]

               #shared.fpOut.write("\tthisVertex[" + str(nn) + "] = " + DisplayOS(thisVertex.x(), thisVertex.y()) + ", nextVertex[" + str(nn-1) + "] = " + DisplayOS(nextVertex.x(), nextVertex.y()) + "\n")

               # This can happen sometimes
               if isclose(thisVertex.x(), nextVertex.x()) and isclose(thisVertex.y(), nextVertex.y()):
                  continue

               thisVertexElev = GetRasterElev(thisVertex.x(), thisVertex.y())
               nextVertexElev = GetRasterElev(nextVertex.x(), nextVertex.y())

               # Is nextVertex lower than thisVertex?
               if nextVertexElev > thisVertexElev + DEPTH_TOLERANCE:
                  # The next vertex point is not downhill, so stop flowing along this route segment
                  AddFlowMarkerPoint(thisVertex, FLOW_INTO_BLIND_PIT, fieldCode, -1)
                  shared.fpOut.write("\tFlow from field " + fieldCode + " hit a blind pit in " + routeType + " segment " + str(featID) + " " + fullDesc + " at " + DisplayOS(thisVertex.x(), thisVertex.y()) + "\n")

                  return 1, thisPoint

               # OK, the route segment is, overall, downhill. Now get a list of the along-segment points, i.e. between thisVertex and nextVertex
               betweenPoints = GetPointsOnLine(thisVertex, nextVertex, shared.resolutionOfDEM)
               nBetween = len(betweenPoints) - 1
               for p in range(0, nBetween):
                  # Look at every pair of points
                  thisPoint = betweenPoints[p]
                  nextPoint = betweenPoints[p+1]
                  thisPointElev = GetRasterElev(thisPoint.x(), thisPoint.y())
                  nextPointElev = GetRasterElev(nextPoint.x(), nextPoint.y())

                  # Check to see whether this route segment intersects a watercourse segment (note that we have not yet checked whether the next point is downhill from this point, but is a reasonable assumption that any intersect point must be downhill from this point)
                  #shared.fpOut.write("\tthisPoint = " + DisplayOS(thisPoint.x(), thisPoint.y()) + ", nextPoint = " + DisplayOS(nextPoint.x(), nextPoint.y()) + "\n")
                  geomLine = QgsGeometry.fromPolyline([QgsPoint(thisPoint), QgsPoint(nextPoint)])
                  rtn = -1
                  streamIntersectPoints = []
                  rtn, streamIntersectPoints = FindSegmentIntersectionWithWatercourse(geomLine)
                  if rtn == -1:
                     # Error
                     return -1, -1

                  elif rtn == 1:
                     # We have at least one intersection
                     #shared.fpOut.write("\tstreamIntersectPoints = " + str(streamIntersectPoints) + "\n")
                     for intPoint in streamIntersectPoints:
                        AddFlowLine(thisPoint, intPoint, flowMarker, fieldCode, -1)

                        # NOTE we are only considering the first intersection point
                        #shared.fpOut.write("BBB Intersection with stream found, added flowline from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to " + DisplayOS(intPoint.x(), intPoint.y()) + "\n")
                        return 2, intPoint

                  ## Next check to see whether the next point is a blind pit
                  #if nextPointElev > thisPointElev + DEPTH_TOLERANCE:
                     ## The next point is not downhill, so stop flowing along this route segment
                     #AddFlowMarkerPoint(thisPoint, FLOW_INTO_BLIND_PIT, fieldCode, -1)
                     #shared.fpOut.write("\tFlow from field " + fieldCode + " hit a blind pit in " + routeType + " segment " + str(featID) + " " + fullDesc + " at " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n")

                     #return 1, thisPoint

                  # Check for pre-existing flow lines near the next point
                  adjX, adjY, hitFieldFlowFrom = FindNearbyFlowLine(nextPoint)
                  if adjX != -1:
                     # There is an adjacent flow line, so merge the two and finish with this flow line
                     AddFlowLine(thisPoint, QgsPointXY(adjX, adjY), MERGED_WITH_ADJACENT_FLOWLINE, fieldCode, -1)

                     shared.fpOut.write("Flow from field " + fieldCode + " hit flow from field " + str(hitFieldFlowFrom) + " at " + DisplayOS(adjX, adjY) + " while moving along " + routeType + " segment " + str(featID) + " " + fullDesc + ", so stopped tracing flow from this field\n")

                     return 3, adjPoint

                  # Do we have a field observation near the next point?
                  indx = FindNearbyFieldObservation(nextPoint)
                  if indx != -1:
                     # We have found a field observation near this point, so flow to the field observation
                     fieldObsStartPoint = shared.fieldObservationFlowFrom[indx]
                     AddFlowLine(thisPoint, fieldObsStartPoint, flowMarker, fieldCode, -1)

                     shared.fpOut.write("\tFlow from field " + str(fieldCode) + " along " + routeType + " segment " + str(featID) + " " + fullDesc + " from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to field observation at " + DisplayOS(fieldObsStartPoint.x(), fieldObsStartPoint.y()) + ", nn = " + str(nn) + " of " + str(nVert) + ", p = " + str(p) + " of " + str(nBetween) + "\n")

                     # Now route flow via the field observation
                     rtn, adjPoint = FlowViaFieldObservation(indx, fieldCode, nextPoint, nextPointElev)
                     #shared.fpOut.write("Left FlowViaFieldObservation() called in FlowAlongVectorRoute() 2, rtn = " + str(rtn) + "\n")
                     if rtn == 0:
                        # Flow has passed through the field observation
                        return rtn, adjPoint

                     elif rtn == -1:
                        # Could not determine the Field observation's outflow location
                        shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(nextPoint.x(), nextPoint.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + ", could not determine outflow location\n")
                        return rtn, thisPoint

                     elif rtn == 1:
                        # Flow has passed through the field observation and then hit a blind pit
                        shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(nextPoint.x(), nextPoint.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + ", hit blind pit\n")
                        return rtn, thisPoint

                     elif rtn == 2:
                        # Flow has passed through the field observation and then hit a stream
                        shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(nextPoint.x(), nextPoint.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + " stream\n")
                        return rtn, thisPoint

                     elif rtn == 3:
                        # Flow has passed through the field observation and then merged with pre-existing flow
                        shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(nextPoint.x(), nextPoint.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + ", merged with pre-existing flow\n")
                        return rtn, thisPoint

                     elif rtn == 4:
                        # Flow has passed through the field observation and is flowing along a road
                        shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(nextPoint.x(), nextPoint.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + ", flowed along " + routeType + " so looking for roads BBB\n")
                        return rtn, thisPoint

                  # So flow downhill along the route segment
                  AddFlowLine(thisPoint, nextPoint, flowMarker, fieldCode, -1)

                  shared.fpOut.write("\tFlow from field " + str(fieldCode) + " downhill along " + routeType + " segment " + str(featID) + " " + fullDesc + ", from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to " + DisplayOS(nextPoint.x(), nextPoint.y()) + ", nn = " + str(nn) + " of " + str(nVert) + ", p = " + str(p) + " of " + str(nBetween) + " B\n")

            # Have finished the loop
            shared.fpOut.write("\tFlow from field " + str(fieldCode) + " at vertex[0] of " + routeType + " segment " + str(featID) + " " + fullDesc + " " + DisplayOS(lineVert[0].x(), lineVert[0].y()) + "\n")

            return 4, lineVert[0]

      else:
         # not flowRouted
         shared.fpOut.write("\tNo suitable " + routeType + " segment found at " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n")
         return 1, thisPoint

   return 0, thisPoint
#======================================================================================================================


#======================================================================================================================
#
# Returns True if flow between two points hits a field boundary
#
#======================================================================================================================
def FlowHitFieldBoundary(firstPoint, secondPoint, flowFieldCode):
   # pylint: disable=too-many-locals
   # pylint: disable=too-many-nested-blocks

   flowLineFeature = QgsFeature()
   flowLineFeature.setGeometry(QgsGeometry.fromPolyline([QgsPoint(firstPoint), QgsPoint(secondPoint)]))
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

            polyGeom = fieldBoundary.geometry()
            if polyGeom.isMultipart():
               polygons = polyGeom.asMultiPolygon()
            else:
               polygons = [polyGeom.asPolygon()]

            # If this is a multipolygon, we only consider the first polygon here
            polyBoundary = polygons[0]
            #print(len(polyBoundary))
            #print(str(polyBoundary))

            # Do this for every pair of points on this polygon's boundary i.e. for every line comprising the boundary
            for point in polyBoundary:
               for j in range(len(point) - 1):
                  thisBoundaryPointX = point[j][0]
                  thisBoundaryPointY = point[j][1]

                  nextBoundaryPointX = point[j+1][0]
                  nextBoundaryPointY = point[j+1][1]

                  boundaryLineFeature = QgsFeature()
                  boundaryLineFeature.setGeometry(QgsGeometry.fromPolyline([QgsPoint(thisBoundaryPointX, thisBoundaryPointY), QgsPoint(nextBoundaryPointX, nextBoundaryPointY)]))

                  geomBoundaryLine = boundaryLineFeature.geometry()

                  if geomFlowLine.intersects(geomBoundaryLine):
                     intersection = geomFlowLine.intersection(geomBoundaryLine)
                     intersectPoint = intersection.asPoint()

                     AddFlowMarkerPoint(intersectPoint, MARKER_FIELD_BOUNDARY, flowFieldCode, -1)

                     return True, intersectPoint, fieldCode

   return False, QgsPointXY(-1, -1), -1
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

   #obsCategory = shared.fieldObservationCategory[indx]
   #obsBehaviour = shared.fieldObservationBehaviour[indx]
   #obsDesc = shared.fieldObservationDescription[indx]

   shared.thisFieldFieldObsAlreadyFollowed.append(indx)

   #shared.fpOut.write("Entered flowAlongVectorFieldBoundary at point " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n")

   DEPTH_TOLERANCE = 0.5   # Vertical (depth) tolerance in metres
   CROSS_PRODUCT_TOLERANCE = 1.0

   if indx >= 0:
      shared.thisFieldFieldObsAlreadyFollowed.append(indx)

   layerNum = -1

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

   numberToSearchFor = 3

   while True:
      # Find the nearest field boundary polygons
      #shared.fpOut.write("Start of FlowAlongVectorFieldBoundary loop at " + DisplayOS(thisPoint.x(), thisPoint.y()) +"\n")
      nearestIDs = shared.vectorInputLayerIndex[layerNum].nearestNeighbor(QgsPointXY(thisPoint), numberToSearchFor)
      if len(nearestIDs) > 0:
         shared.fpOut.write("\tNearest field boundary polygon IDs are " + str(nearestIDs) + "\n")

      request = QgsFeatureRequest().setFilterFids(nearestIDs)
      features = shared.vectorInputLayers[layerNum].getFeatures(request)

      routeSegData = []
      geomPoint = QgsGeometry.fromPointXY(QgsPointXY(thisPoint))

      for boundaryPoly in features:
         # Is this field boundary polygon close enough?
         geomPoly = boundaryPoly.geometry()
         nearPoint = geomPoly.nearestPoint(geomPoint)
         distanceToPoly = geomPoint.distance(nearPoint)
         polyID = boundaryPoly.id()
         shared.fpOut.write("\tField boundary with polygon ID " + str(polyID) + " has nearest point = " + DisplayOS(nearPoint.asPoint().x(), nearPoint.asPoint().y()) + ", distance = {:6.1f}".format(distanceToPoly) + " m\n")

         if distanceToPoly > shared.searchDist:
            # Too far away, so forget about this field boundary polygon
            shared.fpOut.write("\tField boundary with polygon ID " + str(polyID) + " is too far away (" + "{:0.1f}".format(distanceToPoly) + " m)\n")

            continue

         # Is OK, so save the field boundary polygon feature, the nearest point, and the distance
         routeSegData.append([boundaryPoly, nearPoint.asPoint(), distanceToPoly])
         #shared.fpOut.write("\t" + str(routeSegData[-1]) + "\n")

      # Did we any find suitable field boundary polygons?
      if not routeSegData:
         # Nope
         shared.fpOut.write("No field boundary polygons nearby: flow along field boundary from field " + str(fieldCode) + " ends at " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n*** Please add a field observation\n")
         return 1, thisPoint

      # OK we have some possibly suitable field boundary polygons
      #for n in range(len(routeSegData)):
         #shared.fpOut.write("\tBefore " + str(n) + " " + str(routeSegData[n][0].id()) + " " + DisplayOS(routeSegData[n][1].x(), routeSegData[n][1].y()) + " " + str(routeSegData[n][2]) + " m\n")

      # Sort the list of field boundary polygons, shortest distance first
      routeSegData.sort(key = lambda distPoint: distPoint[2])

      #for n in range(len(routeSegData)):
         #shared.fpOut.write("\tAfter " + str(n) + " " + str(routeSegData[n][0].id()) + " " + DisplayOS(routeSegData[n][1].x(), routeSegData[n][1].y()) + " " + str(routeSegData[n][2]) + " m\n")

      flowRouted = False
      flowTowardsAfterVertex = None

      for boundaryPoly in routeSegData:
         # Go through this list of field boundary polygons till we find a suitable one
         feature = boundaryPoly[0]
         featID = feature.id()
         nearPoint = boundaryPoly[1]
         nearPointElev = GetRasterElev(nearPoint.x(), nearPoint.y())

         boundaryFieldCode = feature[CONNECTED_FIELD_ID]

         shared.fpOut.write("\tTrying field boundary polygon ID " + str(polyID) + ", for field " + str(boundaryFieldCode) + ", which has nearest point at " + DisplayOS(nearPoint.x(), nearPoint.y()) + ", distance to nearest point = " + "{:0.1f}".format(boundaryPoly[2]) + " m\n")

         geomFeat = feature.geometry()
         if geomFeat.isMultipart():
            lineVertAll = geomFeat.asMultiPolygon()
         else:
            lineVertAll = [geomFeat.asPolygon()]

         # We only consider the first polygon here
         lineVert = lineVertAll[0][0]

         #shared.fpOut.write("Points in lineVert\n")
         #for pt in lineVert:
            #shared.fpOut.write(DisplayOS(pt.x(), pt.y()) + "\n")

         nVert = len(lineVert)
         #shared.fpOut.write("nVert = " + str(nVert) + "\n")

         # If this polygon is too small, forget it
         if nVert < 3:
            continue

         # Find the closest segment of the field boundary polygon
         _sqrDist, _minDistPoint, afterVertex, _leftOf = geomFeat.closestSegmentWithContext(nearPoint)

         afterVertexPoint = geomFeat.vertexAt(afterVertex)
         afterVertexElev = GetRasterElev(afterVertexPoint.x(), afterVertexPoint.y())

         prevVertex = afterVertex - 1
         prevVertexPoint = geomFeat.vertexAt(prevVertex)
         prevVertexElev = GetRasterElev(prevVertexPoint.x(), prevVertexPoint.y())

         #shared.fpOut.write("\t" + DisplayOS(prevVertexPoint.x(), prevVertexPoint.y(), False) + " " + DisplayOS(nearPoint.x(), nearPoint.y(), False) + " " + DisplayOS(afterVertexPoint.x(), afterVertexPoint.y(), False) + "\n")

         # Are the two points co-incident?
         if isclose(prevVertexPoint.x(), nearPoint.x()) and isclose(prevVertexPoint.y(), nearPoint.y()):
            # The nearest point on the field boundary polygon is co-incident with the 'previous' vertex, so we only need check the elevation of the 'after' vertex
            if nearPointElev + DEPTH_TOLERANCE > afterVertexElev:
               # Flow towards 'after' vertex
               flowTowardsAfterVertex = True
               shared.fpOut.write("\tFlow is towards the 'after' vertex for field boundary (a)\n")

               printStr = "Flow from field " + fieldCode + " enters the field boundary  polygon " + boundaryFieldCode + " at " + DisplayOS(thisPoint.x(), thisPoint.y()) + " A "
               shared.fpOut.write("\t" + printStr + "\n")

               thisPointElev = GetRasterElev(thisPoint.x(), thisPoint.y())
               AddFlowMarkerPoint(thisPoint, FLOW_VIA_BOUNDARY, fieldCode, thisPointElev)

               if thisPoint != nearPoint:
                  shared.fpOut.write("\tAlong-boundary flowline added from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to " + DisplayOS(nearPoint.x(), nearPoint.y()) + "\n")
                  AddFlowLine(thisPoint, nearPoint, FLOW_VIA_BOUNDARY, fieldCode, -1)

               thisPoint = nearPoint
               nextPoint = afterVertexPoint
               startVert = afterVertex

               # Forget about this list of field boundary polygons since we have found a suitable one
               flowRouted = True
               break

         # Are the two points co-incident?
         if isclose(afterVertexPoint.x(), nearPoint.x()) and isclose(afterVertexPoint.y(), nearPoint.y()):
            # The nearest point on the field boundary polygon is co-incident with the 'after' vertex, so we only need check the elevation of the 'previous' vertex
            if nearPointElev + DEPTH_TOLERANCE > prevVertexElev:
               # Flow towards 'previous' vertex
               flowTowardsAfterVertex = False
               #shared.fpOut.write("\tFlow is towards descending vertex numbers for this field boundary (a)\n")

               printStr = "Flow from field " + fieldCode + " begins to flow along the boundary of field " + boundaryFieldCode + " at " + DisplayOS(thisPoint.x(), thisPoint.y()) + " B "
               shared.fpOut.write("\t" + printStr + "\n")

               thisPointElev = GetRasterElev(thisPoint.x(), thisPoint.y())
               AddFlowMarkerPoint(thisPoint, FLOW_VIA_BOUNDARY, fieldCode, thisPointElev)

               if thisPoint != nearPoint:
                  shared.fpOut.write("\tAlong-boundary flowline added from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to " + DisplayOS(nearPoint.x(), nearPoint.y()) + "\n")
                  AddFlowLine(thisPoint, nearPoint, FLOW_VIA_BOUNDARY, fieldCode, -1)

               thisPoint = nearPoint
               nextPoint = prevVertexPoint
               startVert = prevVertex

               # Forget about this list of field boundary polygons since we have found a suitable one
               flowRouted = True
               break

         # Now determine the flow direction
         prevBelow = False
         afterBelow = False

         if nearPointElev + DEPTH_TOLERANCE > prevVertexElev:
            prevBelow = True

         if nearPointElev + DEPTH_TOLERANCE > afterVertexElev:
            afterBelow = True

         if afterBelow and not prevBelow:
            # Flow is towards the 'after' vertex
            flowTowardsAfterVertex = True
            #shared.fpOut.write("\tFlow is towards ascending vertex numbers for this field boundary (a)\n")

            printStr = "Flow from field " + fieldCode + " begins to flow along the boundary of field " + boundaryFieldCode + " at " + DisplayOS(thisPoint.x(), thisPoint.y()) + " C "
            shared.fpOut.write("\t" + printStr + "\n")

            thisPointElev = GetRasterElev(thisPoint.x(), thisPoint.y())
            AddFlowMarkerPoint(thisPoint, FLOW_VIA_BOUNDARY, fieldCode, thisPointElev)

            if thisPoint != nearPoint:
               shared.fpOut.write("\tAlong-boundary flowline added from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to " + DisplayOS(nearPoint.x(), nearPoint.y()) + "\n")
               AddFlowLine(thisPoint, nearPoint, FLOW_VIA_BOUNDARY, fieldCode, -1)

            thisPoint = nearPoint
            nextPoint = afterVertexPoint
            startVert = afterVertex

            # Forget about this list of field boundary polygons since we have found a suitable one
            flowRouted = True
            break

         elif prevBelow and not afterBelow:
            # Flow is towards the 'previous' vertex
            flowTowardsAfterVertex = False
            #shared.fpOut.write("\tFlow is towards descending vertex numbers for this field boundary (b)\n")

            printStr = "Flow from field " + fieldCode + " begins to flow along the boundary of field " + boundaryFieldCode + " at " + DisplayOS(thisPoint.x(), thisPoint.y()) + " D "
            shared.fpOut.write("\t" + printStr + "\n")

            thisPointElev = GetRasterElev(thisPoint.x(), thisPoint.y())
            AddFlowMarkerPoint(thisPoint, FLOW_VIA_BOUNDARY, fieldCode, thisPointElev)

            if thisPoint != nearPoint:
               shared.fpOut.write("\tAlong-boundary flowline added from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to " + DisplayOS(nearPoint.x(), nearPoint.y()) + "\n")
               AddFlowLine(thisPoint, nearPoint, FLOW_VIA_BOUNDARY, fieldCode, -1)

            thisPoint = nearPoint
            nextPoint = prevVertexPoint
            startVert = prevVertex

            # Forget about this list of field boundary polygons since we have found a suitable one
            flowRouted = True
            break

         elif not prevBelow and not afterBelow:
            # We are in a blind pit, so try the next field boundary polygon in the list of field boundary polygons
            shared.fpOut.write("\tIn field boundary blind pit for field boundary polygon " + boundaryFieldCode + ", downhill flow ends at " + DisplayOS(nearPoint.x(), nearPoint.y()) + ", abandoning\n")
            shared.fpOut.write(str(prevVertexElev) + " " + str(nearPointElev) + " " + str(afterVertexElev) + "\n")

            continue

         # Must be prevBelow and AfterBelow so find steepest
         previousIsSteepest = GetSteeperOfTwoLines(prevVertexPoint, prevVertexElev, nearPoint, nearPointElev, afterVertexPoint, afterVertexElev)
         shared.fpOut.write("\tpreviousIsSteepest = " + str(previousIsSteepest) + "\n")

         if previousIsSteepest:
            #shared.fpOut.write("\tFlow is towards descending vertex numbers for this field boundary (c)\n")
            flowTowardsAfterVertex = False

            printStr = "Flow from field " + fieldCode + " begins to flow along the boundary of field " + boundaryFieldCode + " at " + DisplayOS(thisPoint.x(), thisPoint.y()) + " E "
            shared.fpOut.write("\t" + printStr + "\n")

            thisPointElev = GetRasterElev(thisPoint.x(), thisPoint.y())
            AddFlowMarkerPoint(thisPoint, FLOW_VIA_BOUNDARY, fieldCode, thisPointElev)

            if thisPoint != nearPoint:
               shared.fpOut.write("\tAlong-boundary flowline added from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to " + DisplayOS(nearPoint.x(), nearPoint.y()) + "\n")
               AddFlowLine(thisPoint, nearPoint, FLOW_VIA_BOUNDARY, fieldCode, -1)

            thisPoint = nearPoint
            nextPoint = prevVertexPoint
            startVert = prevVertex
         else:
            #shared.fpOut.write("\tFlow is towards ascending vertex numbers for this field boundary (d)\n")
            flowTowardsAfterVertex = True

            printStr = "Flow from field " + fieldCode + " begins to flow along the boundary of field " + boundaryFieldCode + " at " + DisplayOS(thisPoint.x(), thisPoint.y()) + " F "
            shared.fpOut.write("\t" + printStr + "\n")

            thisPointElev = GetRasterElev(thisPoint.x(), thisPoint.y())
            AddFlowMarkerPoint(thisPoint, FLOW_VIA_BOUNDARY, fieldCode, thisPointElev)

            if thisPoint != nearPoint:
               shared.fpOut.write("\tAlong-boundary flowline added from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to " + DisplayOS(nearPoint.x(), nearPoint.y()) + "\n")
               AddFlowLine(thisPoint, nearPoint, FLOW_VIA_BOUNDARY, fieldCode, -1)

            thisPoint = nearPoint
            nextPoint = afterVertexPoint
            startVert = afterVertex

         # Forget about this list of field boundary polygons since we have found a suitable one
         flowRouted = True
         break

      # ===============================================================================================================
      if flowRouted:
         # OK we have found a suitable field boundary polygon, thisPoint is the start of flow onto this polygon, nextPoint is the polygon vertex at which polygon-edge flow starts
         AddFlowLine(thisPoint, nextPoint, FLOW_VIA_BOUNDARY, fieldCode, -1)

         #shared.fpOut.write("\tflowTowardsAfterVertex = " + str(flowTowardsAfterVertex) + "\n")

         # OK we know the initial direction of flow along this field boundary, so keep going downhill till we reach a pre-existing flow line, a watercourse, a blind pit, or the end of the field boundary
         thisPointElev = GetRasterElev(thisPoint.x(), thisPoint.y())

         nVert = len(lineVert)
         #shared.fpOut.write("\tnVert = " + str(nVert) + "\n")

         if flowTowardsAfterVertex:
            # Flow goes in the direction of ascending numbered vertices of the field boundary polygon
            nnBefore = startVert-2
            nn = startVert-1
            nnNext = startVert

            while True:
               nnBefore += 1
               nn += 1
               nnNext += 1

               # Have we come back to the start vertex i.e. gone all the way round the field boundary?
               if nn == startVert-1:
                  shared.fpOut.write("\tFlow has made a complete circuit of the field boundary polygon\n")
                  return 4, lineVert[nn]

               # When we go past the final point in the polygon, then continue from the first point
               if nnNext == nVert:
                  shared.fpOut.write("\tPast last vertex of field boundary polygon, continuing from first vertex\n")
                  nnNext = 0

               if nn == nVert:
                  nn = 0

               if nnBefore == nVert:
                  nnBefore = 0

               thisPoint = lineVert[nn]
               nextPoint = lineVert[nnNext]
               thisPointElev = GetRasterElev(thisPoint.x(), thisPoint.y())
               nextPointElev = GetRasterElev(nextPoint.x(), nextPoint.y())

               # Check to see whether this field boundary polygon segment intersects a watercourse segment (note that we have not yet checked whether the next point is downhill from this point, but is a reasonable assumption that any intersect point must be downhill from this point)
               geomLine = QgsGeometry.fromPolyline([QgsPoint(thisPoint), QgsPoint(nextPoint)])
               rtn = -1
               streamIntersectPoints = []
               rtn, streamIntersectPoints = FindSegmentIntersectionWithWatercourse(geomLine)
               if rtn == -1:
                  # Error
                  return -1, -1

               elif rtn == 1:
                  # We have at least one intersection
                  for intPoint in streamIntersectPoints:
                     AddFlowLine(thisPoint, intPoint, FLOW_VIA_BOUNDARY, fieldCode, -1)

                     # NOTE we are only considering the first intersection point
                     shared.fpOut.write("AAA Intersection with stream found, added flowline from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to " + DisplayOS(intPoint.x(), intPoint.y()) + "\n")
                     return 2, intPoint

               # Next check to see whether the next point is downhill from this point
               if nextPointElev > thisPointElev + DEPTH_TOLERANCE:
                  # The next point is not downhill, so stop flowing along this field boundary segment
                  AddFlowMarkerPoint(thisPoint, FLOW_INTO_BLIND_PIT, fieldCode, -1)
                  shared.fpOut.write("\tFlow from field " + fieldCode + " hit a blind pit on the boundary of field " + boundaryFieldCode + " at " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n")

                  return 1, thisPoint

               # Check for pre-existing flow lines near the next point
               adjX, adjY, hitFieldFlowFrom = FindNearbyFlowLine(nextPoint)
               if adjX != -1:
                  # There is an adjacent flow line, so merge the two and finish with this flow line
                  adjPoint = QgsPointXY(adjX, adjY)
                  AddFlowLine(thisPoint, adjPoint, MERGED_WITH_ADJACENT_FLOWLINE, fieldCode, -1)

                  shared.fpOut.write("Flow from field " + fieldCode + " hit flow from field " + str(hitFieldFlowFrom) + " at " + DisplayOS(adjX, adjY) + " while moving along the boundary of field " + boundaryFieldCode + ", so stopped tracing flow from field " + fieldCode + "\n")

                  return 3, adjPoint

               # If the field boundary is convex at this vertex (i.e. bulges inward) then find out whether flow leaves the boundary because an adjacent within-polygon cell has a steeper gradient
               # TODO make a user option
               beforePoint = lineVert[nnBefore]
               z = CalcZCrossProduct(beforePoint, thisPoint, nextPoint)

               if (z > CROSS_PRODUCT_TOLERANCE):
                  shared.fpOut.write("\tcross product = " + str(z) + "\n")

                  # Search for the adjacent raster cell with the steepest here-to-there slope, and get its centroid
                  adjPoint, adjElev = FindSteepestAdjacent(thisPoint, thisPointElev, geomFeat)
                  #shared.fpOut.write("\tadjPoint = " + DisplayOS(adjPoint.x(), adjPoint.y()) + ", adjElev = " + str(adjElev) + "\n")
                  if adjPoint.x() != -1:
                     # There is a within-polygon cell with a steeper gradient
                     AddFlowLine(thisPoint, adjPoint, FLOW_DOWN_STEEPEST, fieldCode, thisPointElev)

                     shared.fpOut.write("\tFlow from field " + str(fieldCode) + " leaves the boundary of field " + str(boundaryFieldCode) + " at " + DisplayOS(thisPoint.x(), thisPoint.y()) + " and flows down the steepest within-field gradient, to " +  DisplayOS(adjPoint.x(), adjPoint.y()) + "\n")

                     return 0, adjPoint

               # Do we have a nearby field observation?
               indx = FindNearbyFieldObservation(nextPoint)
               if indx != -1:
                  # We have found a field observation near this point, so flow to the field observation
                  fieldObsStartPoint = shared.fieldObservationFlowFrom[indx]
                  AddFlowLine(thisPoint, fieldObsStartPoint, FLOW_VIA_BOUNDARY, fieldCode, -1)

                  shared.fpOut.write("\tFlow from field " + str(fieldCode) + " along the boundary of field " + str(boundaryFieldCode) + " from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to field observation at " + DisplayOS(fieldObsStartPoint.x(), fieldObsStartPoint.y()) + ", nn = " + str(nn) + ", nVert = " + str(nVert) + "\n")

                  # Now route flow via the field observation
                  rtn, adjPoint = FlowViaFieldObservation(indx, fieldCode, nextPoint, nextPointElev)
                  if rtn == 0:
                     # Flow has passed through the field observation
                     #shared.fpOut.write("Left FlowViaFieldObservation() called in FlowAlongVectorFieldBoundary() 1, rtn = " + str(rtn) + "\n")
                     return rtn, adjPoint

                  elif rtn == -1:
                     # Could not determine the field observation's outflow location
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(nextPoint.x(), nextPoint.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + ", could not determine outflow location\n")
                     return rtn, thisPoint

                  elif rtn == 1:
                     # Flow has passed through the field observation and then hit a blind pit
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(nextPoint.x(), nextPoint.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + ", hit blind pit\n")
                     return rtn, thisPoint

                  elif rtn == 2:
                     # Flow has passed through the field observation and then  hit a stream
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(nextPoint.x(), nextPoint.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + " stream\n")
                     return rtn, thisPoint

                  elif rtn == 3:
                     # Flow has passed through the field observation and then merged with pre-existing flow
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(nextPoint.x(), nextPoint.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + ", merged with pre-existing flow\n")
                     return rtn, thisPoint

                  elif rtn == 4:
                     # Flow has passed through the field observation and is flowing along a field boundary
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(nextPoint.x(), nextPoint.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + ", flowed along field boundary so looking for other field boundaries AAA\n")
                     return rtn, thisPoint


               # OK, we are flowing downhill along this field boundary segment
               AddFlowLine(thisPoint, nextPoint, FLOW_VIA_BOUNDARY, fieldCode, -1)

               shared.fpOut.write("\tFlow from field " + str(fieldCode) + " along the boundary of field " + boundaryFieldCode + " from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to " + DisplayOS(nextPoint.x(), nextPoint.y()) + ", nn = " + str(nn) + ", nnNext = " + str(nnNext) + ", nVert = " + str(nVert) + "\n")

         else:
            # Flow goes in the direction of descending numbered vertices of the field boundary polygon
            nnBefore = startVert+2
            nn = startVert+1
            nnNext = startVert

            while True:
               nnBefore -= 1
               nn -= 1
               nnNext -= 1

               # Have we come back to the start vertex i.e. gone all the way round the field boundary?
               if nn == startVert+1:
                  shared.fpOut.write("\tFlow has made a complete circuit of the field boundary polygon\n")
                  return 4, lineVert[nn]

               # When we go past the first point in the polygon, then continue from the last point
               if nnNext == -1:
                  shared.fpOut.write("\tPast first vertex of field boundary polygon, continue from last vertex\n")
                  nnNext = nVert-1

               if nn == -1:
                  nn = nVert-1

               if nnBefore == -1:
                  nnBefore = nVert-1

               thisPoint = lineVert[nn]
               nextPoint = lineVert[nnNext]
               thisPointElev = GetRasterElev(thisPoint.x(), thisPoint.y())
               nextPointElev = GetRasterElev(nextPoint.x(), nextPoint.y())

               # Check to see whether this field boundary segment intersects a watercourse segment (note that we have not yet checked whether the next point is downhill from this point, but is a reasonable assumption that any intersect point must be downhill from this point)
               geomLine = QgsGeometry.fromPolyline([QgsPoint(thisPoint), QgsPoint(nextPoint)])
               rtn = -1
               streamIntersectPoints = []
               rtn, streamIntersectPoints = FindSegmentIntersectionWithWatercourse(geomLine)
               if rtn == -1:
                  # Error
                  return -1, -1

               elif rtn == 1:
                  # We have at least one intersection
                  for intPoint in streamIntersectPoints:
                     AddFlowLine(thisPoint, intPoint, FLOW_VIA_BOUNDARY, fieldCode, -1)

                     # NOTE we are only considering the first intersection point
                     #shared.fpOut.write("BBB Intersection with stream found, added flowline from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to " + DisplayOS(intPoint.x(), intPoint.y()) + "\n")
                     return 2, intPoint

               # Next check to see whether the next point is downhill from this point
               if nextPointElev > thisPointElev + DEPTH_TOLERANCE:
                  # The next point is not downhill, so stop flowing along this route segment
                  AddFlowMarkerPoint(thisPoint, FLOW_INTO_BLIND_PIT, fieldCode, -1)
                  shared.fpOut.write("\tFlow from field " + fieldCode + " hit a blind pit in field boundary segment " + boundaryFieldCode + " at " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n")

                  return 1, thisPoint

               # Check for pre-existing flow lines near the next point
               adjX, adjY, hitFieldFlowFrom = FindNearbyFlowLine(nextPoint)
               if adjX != -1:
                  # There is an adjacent flow line, so merge the two and finish with this flow line
                  AddFlowLine(thisPoint, QgsPointXY(adjX, adjY), MERGED_WITH_ADJACENT_FLOWLINE, fieldCode, -1)

                  shared.fpOut.write("Flow from field " + fieldCode + " hit flow from field " + str(hitFieldFlowFrom) + " at " + DisplayOS(adjX, adjY) + " while moving along field boundary segment " + boundaryFieldCode + ", so stopped tracing flow from field " + fieldCode + "\n")

                  return 3, adjPoint

               # If the field boundary is convex at this vertex (i.e. bulges inward) then find out whether flow leaves the boundary because an adjacent within-polygon cell has a steeper gradient
               # TODO make a user option
               beforePoint = lineVert[nnBefore]
               z = CalcZCrossProduct(beforePoint, thisPoint, nextPoint)


               if (z < -CROSS_PRODUCT_TOLERANCE):
                  shared.fpOut.write("\tcross product = " + str(z) + "\n")

                  # Search for the adjacent raster cell with the steepest here-to-there slope, and get its centroid
                  adjPoint, adjElev = FindSteepestAdjacent(thisPoint, thisPointElev, geomFeat)
                  #shared.fpOut.write("\tadjPoint = " + DisplayOS(adjPoint.x(), adjPoint.y()) + ", adjElev = " + str(adjElev) + "\n")
                  if adjPoint.x() != -1:
                     # There is a within-polygon cell with a steeper gradient
                     AddFlowLine(thisPoint, adjPoint, FLOW_DOWN_STEEPEST, fieldCode, thisPointElev)

                     shared.fpOut.write("\tFlow from field " + str(fieldCode) + " leaves the boundary of field " + str(boundaryFieldCode) + " at " + DisplayOS(thisPoint.x(), thisPoint.y()) + " and flows down the steepest within-field gradient, to " +  DisplayOS(adjPoint.x(), adjPoint.y()) + "\n")

                     return 0, adjPoint

               # Do we have a nearby field observation?
               indx = FindNearbyFieldObservation(nextPoint)
               if indx != -1:
                  # We have found a field observation near this point, so flow to the field observation
                  fieldObsStartPoint = shared.fieldObservationFlowFrom[indx]
                  AddFlowLine(thisPoint, fieldObsStartPoint, FLOW_VIA_BOUNDARY, fieldCode, -1)

                  shared.fpOut.write("\tFlow from field " + str(fieldCode) + " along the boundary of field " + str(boundaryFieldCode) + " from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to field observation at " + DisplayOS(fieldObsStartPoint.x(), fieldObsStartPoint.y()) + ", nn = " + str(nn) + ", nVert = " + str(nVert) + "\n")

                  # Now route flow via the field observation
                  rtn, adjPoint = FlowViaFieldObservation(indx, fieldCode, nextPoint, nextPointElev)
                  #shared.fpOut.write("Left FlowViaFieldObservation() called in FlowAlongVectorFieldBoundary() 1, rtn = " + str(rtn) + "\n")
                  if rtn == 0:
                     # Flow has passed through the field observation
                     return rtn, adjPoint

                  elif rtn == -1:
                     # Could not determine the Field observation's outflow location
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(nextPoint.x(), nextPoint.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + ", could not determine outflow location\n")
                     return rtn, thisPoint

                  elif rtn == 1:
                     # Flow has passed through the field observation and then hit a blind pit
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(nextPoint.x(), nextPoint.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + ", hit blind pit\n")
                     return rtn, thisPoint

                  elif rtn == 2:
                     # Flow has passed through the field observation and then hit a stream
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(nextPoint.x(), nextPoint.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + " stream\n")
                     return rtn, thisPoint

                  elif rtn == 3:
                     # Flow has passed through the field observation and then merged with pre-existing flow
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(nextPoint.x(), nextPoint.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + ", merged with pre-existing flow\n")
                     return rtn, thisPoint

                  elif rtn == 4:
                     # Flow has passed through the field observation and is flowing along a field boundaries
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(nextPoint.x(), nextPoint.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + ", flowed along field boundary so looking for other field boundaries BBB\n")
                     return rtn, thisPoint

               # OK, we are flowing downhill along this field boundary segment
               AddFlowLine(thisPoint, nextPoint, FLOW_VIA_BOUNDARY, fieldCode, -1)

               shared.fpOut.write("\tFlow from field " + str(fieldCode) + " along the boundary of field " + boundaryFieldCode + " from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to " + DisplayOS(nextPoint.x(), nextPoint.y()) + ", nn = " + str(nn) + ", nnNext = " + str(nnNext) + ", nVert = " + str(nVert) + "\n")

      else:
         # not flowRouted
         shared.fpOut.write("\tNo suitable field boundary polygon found at " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n")
         return 1, thisPoint

   return 0, thisPoint
#======================================================================================================================


#======================================================================================================================
#
# Fills a blind pit, returning the overflow point and flow depth needed to create this overflow point
#
#======================================================================================================================
def FillBlindPit(thisPoint, fieldCode):

   startElev = GetRasterElev(thisPoint.x(), thisPoint.y())
   pondedCells = [thisPoint]
   increment = 0.1
   topElev = startElev

   while True:
      topElev += increment
      #print("Start of FillBlindPit loop at " + DisplayOS(thisPoint.x(), thisPoint.y()) + " startElev = " +str(startElev) + " topElev = " + str(topElev))
      for cell in pondedCells:
         #print("pondedCell " + DisplayOS(cell.x(), cell.y()))
         AddFlowLine(thisPoint, cell, FLOW_INTO_BLIND_PIT, fieldCode, -1)

      newOverflowCells = []
      for point in pondedCells:
         adjPoint, _adjElev = FindSteepestAdjacent(point, topElev)

         if adjPoint.x() != -1:
            # We have found a new overflow point to which we have not travelled before
            #print("Overflow cell found at " + DisplayOS(adjPoint.x(), adjPoint.y()) + " startElev = " +str(startElev)  + " topElev = " + str(topElev))
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
