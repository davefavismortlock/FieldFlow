from __future__ import print_function

from math import sqrt

from qgis.core import QgsRaster, QgsFeature, QgsFeatureRequest, QgsGeometry, QgsPoint, QgsRectangle     # NULL,
#from qgis.gui import QgsMapCanvasLayer    #, QgsMapToolPan, QgsMapToolZoom

import shared
from shared import INPUT_DIGITAL_ELEVATION_MODEL, FIELD_OBS_CATEGORY_ROAD, FIELD_OBS_BEHAVIOUR_ALONG, MARKER_ROAD, FIELD_OBS_CATEGORY_PATH, MARKER_PATH, FIELD_OBS_CATEGORY_BOUNDARY, MARKER_FIELD_BOUNDARY, FIELD_OBS_CATEGORY_CULVERT, MARKER_ENTER_CULVERT, INPUT_ROAD_NETWORK, OS_VECTORMAP_FEAT_CODE, OS_VECTORMAP_FEAT_DESC, OS_VECTORMAP_ROAD_NAME, OS_VECTORMAP_ROAD_NUMBER, MERGED_WITH_ADJACENT_FLOWLINE, FLOW_VIA_ROAD, INPUT_PATH_NETWORK, PATH_DESC, PREV_POINT, THIS_POINT, POST_POINT, FLOW_VIA_PATH, INPUT_FIELD_BOUNDARIES, CONNECTED_FIELD_ID, FLOW_VIA_BOUNDARY, FLOW_DOWN_STEEPEST, BLIND_PIT
from layers import AddFlowMarkerPoint, AddFlowLine
from searches import FindSteepestAdjacent, FindSegmentIntersectionWithStream, FindSteepestSegment, FindNearbyFlowLine, FindNearbyFieldObservation, CanOverflowTo
from utils import GetPointsOnLine, GetCentroidOfContainingDEMCell, DisplayOS, GetRasterElev, CalcZCrossProduct

# pylint: disable=too-many-lines


#======================================================================================================================
#
# Returns the coords (external CRS) of the centroid of the pixel containing the highest point on a field boundary
#
#======================================================================================================================
def GetHighestPointOnFieldBoundary(fieldBoundary):
   # pylint: disable=too-many-locals
   # pylint: disable=too-many-nested-blocks

   maxElev = 0       # sys.float_info.min
   maxElevX = -1
   maxElevY = -1

   polyBoundary = fieldBoundary.constGeometry().asPolygon()
   for point in polyBoundary:
      for j in range(len(point) - 1):
         thisBoundaryPointX = point[j][0]
         thisBoundaryPointY = point[j][1]

         nextBoundaryPointX = point[j+1][0]
         nextBoundaryPointY = point[j+1][1]

         inBetweenPoints = GetPointsOnLine(QgsPoint(thisBoundaryPointX, thisBoundaryPointY), QgsPoint(nextBoundaryPointX, nextBoundaryPointY), shared.resolutionOfDEM)
         #shared.fpOut.write("From " + DisplayOS(thisBoundaryPointX, thisBoundaryPointY) + " to " + DisplayOS(nextBoundaryPointX, nextBoundaryPointY))
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
                  pixelCentroidPoint = GetCentroidOfContainingDEMCell(boundaryPoint.x(), boundaryPoint.y())
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
#  4 = flow along road, can continue to flow along roads
#  5 = flow along path/track, can continue to flow along paths/tracks
#
#======================================================================================================================
def FlowViaFieldObservation(indx, fieldCode, thisPoint, elev):
   # pylint: disable=too-many-statements
   # pylint: disable=too-many-return-statements
   # pylint: disable=too-many-branches

   shared.fpOut.write("Entered FlowViaFieldObservation() at " + DisplayOS(thisPoint.x(), thisPoint.y(), False) + ", field observation found at " + DisplayOS(shared.fieldObservationFlowFrom[indx].x(), shared.fieldObservationFlowFrom[indx].y(), False) + "\n")
   #shared.fpOut.write(shared.fieldObservationFlowTo)
   if not shared.fieldObservationFlowTo[indx]:
      # The outflow location is not known, so we have flow along a road or along a path
      if shared.fieldObservationCategory[indx] == FIELD_OBS_CATEGORY_ROAD and shared.fieldObservationBehaviour[indx] == FIELD_OBS_BEHAVIOUR_ALONG:
         #shared.fpOut.write("Flow along road")
         AddFlowMarkerPoint(thisPoint, MARKER_ROAD, fieldCode, -1)

         rtn, point = FlowAlongVectorRoad(indx, fieldCode, thisPoint)
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
            shared.fpOut.write("\tFinished flow along road at " + DisplayOS(point.x(), point.y()) + " called from FlowViaFieldObservation(), rtn = 4\n")
            return 4, point

         else:
            # Carry on from this point
            return 0, point

      elif shared.fieldObservationCategory[indx] == FIELD_OBS_CATEGORY_PATH and shared.fieldObservationBehaviour[indx] == FIELD_OBS_BEHAVIOUR_ALONG:
         #shared.fpOut.write("Flow along path")
         AddFlowMarkerPoint(thisPoint, MARKER_PATH, fieldCode, -1)

         rtn, point = FlowAlongVectorPath(indx, fieldCode, thisPoint)
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
            shared.fpOut.write("\tFinished flow along path at " + DisplayOS(point.x(), point.y()) + " called from FlowViaFieldObservation(), rtn = 4\n")
            return 5, point

         else:
            # Carry on from this point
            return 0, point

      elif shared.fieldObservationCategory[indx] == FIELD_OBS_CATEGORY_BOUNDARY and shared.fieldObservationBehaviour[indx] == FIELD_OBS_BEHAVIOUR_ALONG:
         #shared.fpOut.write("Flow along boundary\n")
         AddFlowMarkerPoint(thisPoint, MARKER_FIELD_BOUNDARY, fieldCode, -1)

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
         printStr = "ERROR: must have a 'To' location for field observation " + str(indx) + " '" + shared.fieldObservationCategory[indx] + shared.fieldObservationBehaviour[indx] + "' '" + shared.fieldObservationDescription[indx] + "', in flow from field " + str(fieldCode) + " at "+ DisplayOS(shared.fieldObservationFlowFrom[indx].x(), shared.fieldObservationFlowFrom[indx].y()) + "\n"
         shared.fpOut.write(printStr)
         print(printStr)

         return -1, -1

   # We do have an outflow location: OK, show some marker points
   if shared.fieldObservationCategory[indx] == FIELD_OBS_CATEGORY_CULVERT:
      AddFlowMarkerPoint(QgsPoint(shared.fieldObservationFlowFrom[indx].x(), shared.fieldObservationFlowFrom[indx].y()), MARKER_ENTER_CULVERT, fieldCode, -1)

   elif shared.fieldObservationCategory[indx] == FIELD_OBS_CATEGORY_PATH:
      AddFlowMarkerPoint(QgsPoint(shared.fieldObservationFlowFrom[indx].x(), shared.fieldObservationFlowFrom[indx].y()), MARKER_PATH, fieldCode, -1)

   elif shared.fieldObservationCategory[indx] == FIELD_OBS_CATEGORY_ROAD:
      AddFlowMarkerPoint(QgsPoint(shared.fieldObservationFlowFrom[indx].x(), shared.fieldObservationFlowFrom[indx].y()), MARKER_ROAD, fieldCode, -1)

   printStr = "Flow from field " + fieldCode + " routed via '" + shared.fieldObservationBehaviour[indx] + " " + shared.fieldObservationCategory[indx] + " " + shared.fieldObservationDescription[indx] + "' from " + DisplayOS(thisPoint.x(), thisPoint.y())
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
# Routes flow downhill along a vector representation of a road
#
#======================================================================================================================
def FlowAlongVectorRoad(indx, fieldCode, thisPoint):
   # pylint: disable=too-many-locals
   # pylint: disable=too-many-nested-blocks
   # pylint: disable=too-many-return-statements
   # pylint: disable=too-many-branches
   # pylint: disable=too-many-statements

   TOLERANCE = 0.1

   if indx >= 0:
      shared.thisFieldFieldObsAlreadyFollowed.append(indx)

   #shared.fpOut.write("Entered FlowAlongVectorRoad at point " + DisplayOS(thisPoint.x(), thisPoint.y()))
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

   #numberToSearchFor = 4

   while True:
      # Find the nearest road segments
      #shared.fpOut.write("Start of FlowAlongVectorRoad loop at " + DisplayOS(thisPoint.x(), thisPoint.y()))
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
         #shared.fpOut.write("\tRoad segID = " + str(segID) + ", nearest point = " + DisplayOS(nearPoint.asPoint().x(), nearPoint.asPoint().y()) + ", distanceToSeg = " + str(distanceToSeg) + "\n")

         if distanceToSeg > shared.searchDist:
            # Too far away, so forget about this road segment
            #shared.fpOut.write("\tToo far away (" + str(distanceToSeg) + " m) for road segID = " + str(segID) + "\n")

            continue

         if segID in shared.thisFieldRoadSegIDsTried:
            # Already travelled, so forget about this road segment
            #shared.fpOut.write("\tAlready travelled for road segID = " + str(segID) + "\n")

            continue

         # Is OK, so save the road segment feature, the nearest point, and the distance
         distToPoint.append([roadSeg, nearPoint.asPoint(), distanceToSeg])
         #shared.fpOut.write("\t" + str(distToPoint[-1]) + "\n")

      # Did we any find suitable road segments?
      if not distToPoint:
         # Nope
         shared.fpOut.write("No untravelled road segments nearby: flow along road from field " + str(fieldCode) + " ends at " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n*** Please add a field observation\n")
         return 1, thisPoint

      # OK we have some possibly suitable road segments
      #for n in range(len(distToPoint)):
         #shared.fpOut.write("\tBefore " + str(n) + " " + str(distToPoint[n][0].id()) + " " + DisplayOS(distToPoint[n][1].x(), distToPoint[n][1].y()) + " " + str(distToPoint[n][2]) + " m\n")

      # Sort the list of untravelled road segments, shortest distance first
      distToPoint.sort(key = lambda distPoint: distPoint[2])

      #for n in range(len(distToPoint)):
         #shared.fpOut.write("\tAfter " + str(n) + " " + str(distToPoint[n][0].id()) + " " + DisplayOS(distToPoint[n][1].x(), distToPoint[n][1].y()) + " " + str(distToPoint[n][2]) + " m\n")

      flowRouted = False
      for roadSeg in distToPoint:
         # Go through this list of untravelled road segments till we find a suitable one
         feature = roadSeg[0]
         featID = feature.id()
         nearPoint = roadSeg[1]

         featCode = feature[OS_VECTORMAP_FEAT_CODE]
         featDesc = feature[OS_VECTORMAP_FEAT_DESC]
         roadName = feature[OS_VECTORMAP_ROAD_NAME]
         roadNumber = feature[OS_VECTORMAP_ROAD_NUMBER]

         fullDesc = "'" + str(featCode) + " " + str(featDesc) + " " + str(roadName) + " " + str(roadNumber) + "'"

         shared.fpOut.write("\tTrying untravelled road segment " + fullDesc + " with distance to nearest point = " + str(roadSeg[2]) + " m\n")

         geomFeat = feature.geometry()
         linePoints = geomFeat.asPolyline()

         shared.fpOut.write("\tAt " + DisplayOS(thisPoint.x(), thisPoint.y()) +", trying untravelled road segment " + fullDesc + ", which has nearest point " + "{:0.1f}".format(roadSeg[2]) + " m away at " + DisplayOS(nearPoint.x(), nearPoint.y()) + "\n")

         # Find the nearest point in the road polyline
         nearPoint, numNearPoint, _beforeNearpoint, _afterNearpoint, _sqrDist = geomFeat.closestVertex(thisPoint)

         # If there is a choice, then find out which direction along the road has the steepest downhill slope
         flowTowardsLastPoint = None
         elevNearPoint = GetRasterElev(nearPoint.x(), nearPoint.y())
         if numNearPoint == 0:
            # The nearest point is the same as the first point, so compare elevations with the next point (the second point in the line)
            nextPoint = linePoints[1]
            elevNextPoint = GetRasterElev(nextPoint.x(), nextPoint.y())

            shared.fpOut.write("\tA: near point elev = " + str(elevNearPoint) + ", next point elev = " + str(elevNextPoint) + "\n")

            if elevNearPoint + TOLERANCE > elevNextPoint:
               # Flow towards next point
               flowTowardsLastPoint = True
               shared.fpOut.write("\tFlow towards last point in road (a)\n")

               # Forget about this list of untravelled road segments since we have found a suitable one
               flowRouted = True
               break

            else:
               # This point is lower: we are in a blind pit, so try the next road segment in the list of untravelled road segments
               shared.fpOut.write("\tIn road blind pit: for road segment " + fullDesc + ", downhill flow ends at " + DisplayOS(nearPoint.x(), nearPoint.y()) + ", abandoning\n")

               shared.thisFieldRoadSegIDsTried.append(featID)
               continue

         elif numNearPoint == len(linePoints)-1:
            # The nearest point is the same as the last point, so compare elevations with the previous point (the penultimate point in the line)
            prevPoint = linePoints[numNearPoint-1]
            elevPrevPoint = GetRasterElev(prevPoint.x(), prevPoint.y())

            shared.fpOut.write("\tB: near point elev = " + str(elevNearPoint) + ", prev point elev = " + str(elevPrevPoint) + "\n")

            if elevNearPoint + TOLERANCE > elevPrevPoint:
               # Flow towards first point
               flowTowardsLastPoint = False
               shared.fpOut.write("\tFlow towards first point in road (b)\n")

               # Forget about this list of untravelled road segments since we have found a suitable one
               flowRouted = True
               break

            else:
               # This point is lower: we are in a blind pit, so try the next road segment
               shared.fpOut.write("\tIn road blind pit: for road segment " + fullDesc + ", downhill flow ends at " + DisplayOS(nearPoint.x(), nearPoint.y()) + ", abandoning\n")

               shared.thisFieldRoadSegIDsTried.append(featID)
               continue

         else:
            # The nearest point is neither the first or last point in the road polyline
            prevPoint = linePoints[numNearPoint-1]
            elevPrevPoint = GetRasterElev(prevPoint.x(), prevPoint.y())

            postPoint = linePoints[numNearPoint+1]
            elevPostPoint = GetRasterElev(postPoint.x(), postPoint.y())

            shared.fpOut.write("\tC: prev point elev = " + str(elevPrevPoint) + ", nearest point elev = " + str(elevNearPoint) + ", post point elev = " + str(elevPostPoint) + "\n")

            pts = [[PREV_POINT, elevPrevPoint], [THIS_POINT, elevNearPoint], [POST_POINT, elevPostPoint]]
            pts.sort(key = lambda pt: pt[1])

            for m in range(3):
               shared.fpOut.write("\tpts[" + str(m) + "][0] = " + str(pts[m][0]) + ", pts[" + str(m) + "][1] = " + str(pts[m][1]) + "\n")

            if pts[0][0] == THIS_POINT:
               # Near point is lowest: we are in a blind pit, so try the next road segment in the list of untravelled road segments
               shared.fpOut.write("\tIn road blind pit: for road segment " + fullDesc + ", downhill flow ends at " + DisplayOS(nearPoint.x(), nearPoint.y()) + ", abandoning\n")

               shared.thisFieldRoadSegIDsTried.append(featID)
               continue

            elif pts[1][0] == THIS_POINT:
               if pts[0][0] == PREV_POINT:
                  # The previous point is lower than the near point, so flow goes towards the first point
                  shared.fpOut.write("\tFlow towards first point in road (c)\n")
                  flowTowardsLastPoint = False

                  # Forget about this list of untravelled road segments since we have found a suitable one
                  flowRouted = True
                  break

               else:
                  # The post point is lower than the near point, so flow goes towards the last point
                  shared.fpOut.write("\tFlow towards last point in road (d)\n")
                  flowTowardsLastPoint = True

                  # Forget about this list of untravelled road segments since we have found a suitable one
                  flowRouted = True
                  break

            else:
               # Both first and last points are lower, so we need to compare gradients
               shared.fpOut.write("\tprevPoint = " + DisplayOS(prevPoint.x(), prevPoint.y()) + " nearPoint = " + DisplayOS(nearPoint.x(), nearPoint.y()) + " postPoint = " + DisplayOS(postPoint.x(), postPoint.y()) + "\n")

               flowToLast = FindSteepestSegment(prevPoint, nearPoint, postPoint, elevNearPoint - elevPrevPoint, elevNearPoint - elevPostPoint)
               shared.fpOut.write("\t" + str(flowToLast) + " \n")

               if flowToLast:
                  flowTowardsLastPoint = True
                  shared.fpOut.write("\tFlow towards last point in road (e)\n")

                  # Forget about this list of untravelled road segments since we have found a suitable one
                  flowRouted = True
                  break

               else:
                  flowTowardsLastPoint = False
                  shared.fpOut.write("\tFlow towards first point in road (f)\n")

                  # Forget about this list of untravelled road segments since we have found a suitable one
                  flowRouted = True
                  break

      if flowRouted:
         # OK we know the initial direction of flow along this road, so keep going downhill till we reach a pre-existing flow line, a ditch/stream, a blind pit, or the end of the road
         shared.thisFieldRoadSegIDsTried.append(featID)

         elevThisPoint = GetRasterElev(thisPoint.x(), thisPoint.y())

         printStr = "Flow from field " + fieldCode + " enters the road segment " + fullDesc + " at " + DisplayOS(thisPoint.x(), thisPoint.y()) + " "
         shared.fpOut.write("\t" + printStr + "\n")

         AddFlowMarkerPoint(thisPoint, FLOW_VIA_ROAD, fieldCode, elevThisPoint)

         nPoints = len(linePoints)

         if flowTowardsLastPoint:
            # Flow goes towards the last point of the road segment
            for nn in range(numNearPoint, len(linePoints)+1):
               shared.fpOut.write("\tTowards last point of road segment " + fullDesc + " at " + DisplayOS(linePoints[nn].x(), linePoints[nn].y()) + ", nn = " + str(nn) + ", nPoints = " + str(nPoints) + "\n")

               # Are we at the final point in the line?
               if nn == nPoints-1:
                  shared.fpOut.write("\tAt last point of road segment " + fullDesc + " " + DisplayOS(linePoints[nn].x(), linePoints[nn].y()) + "\n")
                  return 4, linePoints[nn]

               # Not at the last point on the line
               thisPoint = linePoints[nn]
               nextPoint = linePoints[nn+1]
               elevThisPoint = GetRasterElev(thisPoint.x(), thisPoint.y())
               elevNextPoint = GetRasterElev(nextPoint.x(), nextPoint.y())

               # Check to see whether this road segment intersects a ditch/stream segment (note that we have not yet checked whether the next point is downhill from this point, but is a reasonable assumption that any intersect point must be downhill from this point)
               geomLine = QgsGeometry.fromPolyline([thisPoint, nextPoint])
               rtn = -1
               streamIntersectPoints = []
               rtn, streamIntersectPoints = FindSegmentIntersectionWithStream(geomLine)
               if rtn == -1:
                  # Error
                  return -1, -1

               elif rtn == 1:
                  # We have at least one intersection
                  for intPoint in streamIntersectPoints:
                     AddFlowLine(thisPoint, intPoint, FLOW_VIA_ROAD, fieldCode, -1)

                     # NOTE we are only considering the first intersection point
                     return 2, intPoint

               # Next check to see whether the next point is downhill from this point
               if elevNextPoint > elevThisPoint + TOLERANCE:
                  # The next point is not downhill, so stop flowing along this road segment
                  shared.fpOut.write("\tFlow from field " + fieldCode + " hit a blind pit in road segment " + fullDesc + " at " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n")

                  return 1, thisPoint

               # OK, we are flowing downhill along the road segment
               AddFlowLine(thisPoint, nextPoint, FLOW_VIA_ROAD, fieldCode, -1)

               # Check for pre-existing flow lines near the next point
               adjX, adjY, hitFieldFlowFrom = FindNearbyFlowLine(nextPoint)
               if adjX != -1:
                  # There is an adjacent flow line, so merge the two and finish with this flow line
                  adjPoint = QgsPoint(adjX, adjY)
                  AddFlowLine(thisPoint, adjPoint, MERGED_WITH_ADJACENT_FLOWLINE, fieldCode, -1)

                  shared.fpOut.write("Flow from field " + fieldCode + " hit flow from field " + str(hitFieldFlowFrom) + " at " + DisplayOS(adjX, adjY) + " while moving along road segment " + fullDesc + ", so stopped tracing flow from this field\n")

                  return 3, adjPoint

               # Do we have a field observation near the next point?
               indx = FindNearbyFieldObservation(nextPoint)
               if indx != -1:
                  # We have found a field observation near this point, so route flow accordingly
                  rtn, adjPoint = FlowViaFieldObservation(indx, fieldCode, nextPoint, elevNextPoint)
                  if rtn == 0:
                     # Flow has passed through the field observation
                     shared.fpOut.write("Left FlowViaFieldObservation() called in FlowAlongVectorPath() 1, rtn = " + str(rtn) + "\n")
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
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(nextPoint.x(), nextPoint.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + ", flowed along road so looking for other roads AAA\n")
                     return rtn, thisPoint

         else:
            # Flow goes towards the first point of the road segment
            for nn in range(numNearPoint, -1, -1):
               shared.fpOut.write("\tTowards first point of road segment " + fullDesc + " at " + DisplayOS(linePoints[nn].x(), linePoints[nn].y()) + ", nn = " + str(nn) + ", nPoints = " + str(nPoints) + "\n")

               # Are we at the first point in the line?
               if nn == 0:
                  shared.fpOut.write("\tAt first point of road segment " + fullDesc + " " + DisplayOS(linePoints[0].x(), linePoints[0].y()) + "\n")
                  return 4, linePoints[0]

               # Not at the first point on the line
               thisPoint = linePoints[nn]
               nextPoint = linePoints[nn-1]
               elevThisPoint = GetRasterElev(thisPoint.x(), thisPoint.y())
               elevNextPoint = GetRasterElev(nextPoint.x(), nextPoint.y())

               # Check to see whether this road segment intersects a ditch/stream segment (note that we have not yet checked whether the next point is downhill from this point, but is a reasonable assumption that any intersect point must be downhill from this point)
               geomLine = QgsGeometry.fromPolyline([thisPoint, nextPoint])
               rtn = -1
               streamIntersectPoints = []
               rtn, streamIntersectPoints = FindSegmentIntersectionWithStream(geomLine)
               if rtn == -1:
                  # Error
                  return -1, -1

               elif rtn == 1:
                  # We have at least one intersection
                  for intPoint in streamIntersectPoints:
                     AddFlowLine(thisPoint, intPoint, FLOW_VIA_ROAD, fieldCode, -1)

                     # NOTE we are only considering the first intersection point
                     return 2, intPoint

               # Next check to see whether the next point is downhill from this point
               if elevNextPoint > elevThisPoint + TOLERANCE:
                  # The next point is not downhill, so stop flowing along this road segment
                  shared.fpOut.write("\tFlow from field " + fieldCode + " hit a blind pit in road segment " + fullDesc + " at " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n")

                  return 1, thisPoint

               # OK, we are flowing downhill along the road segment
               AddFlowLine(thisPoint, nextPoint, FLOW_VIA_ROAD, fieldCode, -1)

               # Check for pre-existing flow lines near the next point
               adjX, adjY, hitFieldFlowFrom = FindNearbyFlowLine(nextPoint)
               if adjX != -1:
                  # There is an adjacent flow line, so merge the two and finish with this flow line
                  AddFlowLine(thisPoint, QgsPoint(adjX, adjY), MERGED_WITH_ADJACENT_FLOWLINE, fieldCode, -1)

                  shared.fpOut.write("Flow from field " + fieldCode + " hit flow from field " + str(hitFieldFlowFrom) + " at " + DisplayOS(adjX, adjY) + " while moving along road segment " + fullDesc + ", so stopped tracing flow from this field\n")

                  return 3, adjPoint

               # Do we have a field observation near the next point?
               indx = FindNearbyFieldObservation(nextPoint)
               if indx != -1:
                  # We have found a field observation near this point, so route flow accordingly
                  rtn, adjPoint = FlowViaFieldObservation(indx, fieldCode, nextPoint, elevNextPoint)
                  shared.fpOut.write("Left FlowViaFieldObservation() called in FlowAlongVectorPath() 2, rtn = " + str(rtn) + "\n")
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
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(nextPoint.x(), nextPoint.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + ", flowed along road so looking for other roads BBB\n")
                     return rtn, thisPoint


      if not flowRouted:
         shared.fpOut.write("\tNo suitable road segment found at " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n")
         return 1, thisPoint

   return 0, thisPoint
#======================================================================================================================


#======================================================================================================================
#
# Routes flow downhill along a vector representation of a path
#
#======================================================================================================================
def FlowAlongVectorPath(indx, fieldCode, thisPoint):
   # pylint: disable=too-many-locals
   # pylint: disable=too-many-nested-blocks
   # pylint: disable=too-many-return-statements
   # pylint: disable=too-many-branches
   # pylint: disable=too-many-statements

   TOLERANCE = 0.1

   if indx >= 0:
      shared.thisFieldFieldObsAlreadyFollowed.append(indx)

   #shared.fpOut.write("Entered FlowAlongVectorPath at point " + DisplayOS(thisPoint.x(), thisPoint.y()))
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

   #numberToSearchFor = 4

   while True:
      # Find the nearest path segments
      #shared.fpOut.write("Start of FlowAlongVectorPath loop at " + DisplayOS(thisPoint.x(), thisPoint.y()))
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
         #shared.fpOut.write("\tPath segID = " + str(segID) + ", nearest point = " + DisplayOS(nearPoint.asPoint().x(), nearPoint.asPoint().y()) + ", distanceToSeg = " + str(distanceToSeg) + "\n")

         if distanceToSeg > shared.searchDist:
            # Too far away, so forget about this path segment
            #shared.fpOut.write("\tToo far away (" + str(distanceToSeg) + " m) for path segID = " + str(segID) + "\n")

            continue

         if segID in shared.thisFieldPathSegIDsTried:
            # Already travelled, so forget about this path segment
            #shared.fpOut.write("\tAlready travelled for path segID = " + str(segID) + "\n")

            continue

         # Is OK, so save the path segment feature, the nearest point, and the distance
         distToPoint.append([pathSeg, nearPoint.asPoint(), distanceToSeg])
         #shared.fpOut.write("\t" + str(distToPoint[-1]) + "\n")

      # Did we any find suitable path segments?
      if not distToPoint:
         # Nope
         shared.fpOut.write("No untravelled path segments nearby: flow along path from field " + str(fieldCode) + " ends at " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n*** Please add a field observation\n")
         return 1, thisPoint

      # OK we have some possibly suitable path segments
      #for n in range(len(distToPoint)):
         #shared.fpOut.write("\tBefore " + str(n) + " " + str(distToPoint[n][0].id()) + " " + DisplayOS(distToPoint[n][1].x(), distToPoint[n][1].y()) + " " + str(distToPoint[n][2]) + " m\n")

      # Sort the list of untravelled path segments, shortest distance first
      distToPoint.sort(key = lambda distPoint: distPoint[2])

      #for n in range(len(distToPoint)):
         #shared.fpOut.write("\tAfter " + str(n) + " " + str(distToPoint[n][0].id()) + " " + DisplayOS(distToPoint[n][1].x(), distToPoint[n][1].y()) + " " + str(distToPoint[n][2]) + " m\n")

      flowRouted = False
      for pathSeg in distToPoint:
         # Go through this list of untravelled path segments till we find a suitable one
         feature = pathSeg[0]
         featID = feature.id()
         nearPoint = pathSeg[1]

         featDesc = feature[PATH_DESC]

         fullDesc = "'" + str(featDesc) + "'"

         shared.fpOut.write("\tTrying untravelled path segment " + fullDesc + " with distance to nearest point = " + str(pathSeg[2]) + " m\n")

         geomFeat = feature.geometry()
         linePoints = geomFeat.asPolyline()

         shared.fpOut.write("\tAt " + DisplayOS(thisPoint.x(), thisPoint.y()) +", trying untravelled path segment " + fullDesc + ", which has nearest point " + "{:0.1f}".format(pathSeg[2]) + " m away at " + DisplayOS(nearPoint.x(), nearPoint.y(), False) + "\n")

         # Find the nearest point in the path polyline
         nearPoint, numNearPoint, _beforeNearpoint, _afterNearpoint, _sqrDist = geomFeat.closestVertex(thisPoint)

         # If there is a choice, then find out which direction along the path has the steepest downhill slope
         flowTowardsLastPoint = None
         elevNearPoint = GetRasterElev(nearPoint.x(), nearPoint.y())
         if numNearPoint == 0:
            # The nearest point is the same as the first point, so compare elevations with the next point (the second point in the line)
            nextPoint = linePoints[1]
            elevNextPoint = GetRasterElev(nextPoint.x(), nextPoint.y())

            shared.fpOut.write("\tA: near point elev = " + str(elevNearPoint) + ", next point elev = " + str(elevNextPoint) + "\n")

            if elevNearPoint + TOLERANCE > elevNextPoint:
               # Flow towards next point
               flowTowardsLastPoint = True
               shared.fpOut.write("\tFlow towards last point in path (a)\n")

               # Forget about this list of untravelled path segments since we have found a suitable one
               flowRouted = True
               break

            else:
               # This point is lower: we are in a blind pit, so try the next path segment in the list of untravelled path segments
               shared.fpOut.write("\tIn path blind pit: for path segment " + fullDesc + ", downhill flow ends at " + DisplayOS(nearPoint.x(), nearPoint.y()) + ", abandoning\n")

               shared.thisFieldPathSegIDsTried.append(featID)
               continue

         elif numNearPoint == len(linePoints)-1:
            # The nearest point is the same as the last point, so compare elevations with the previous point (the penultimate point in the line)
            prevPoint = linePoints[numNearPoint-1]
            elevPrevPoint = GetRasterElev(prevPoint.x(), prevPoint.y())

            shared.fpOut.write("\tB: near point elev = " + str(elevNearPoint) + ", prev point elev = " + str(elevPrevPoint) + "\n")

            if elevNearPoint + TOLERANCE > elevPrevPoint:
               # Flow towards first point
               flowTowardsLastPoint = False
               shared.fpOut.write("\tFlow towards first point in path (b)\n")

               # Forget about this list of untravelled path segments since we have found a suitable one
               flowRouted = True
               break

            else:
               # This point is lower: we are in a blind pit, so try the next path segment
               shared.fpOut.write("\tIn path blind pit: for path segment " + fullDesc + ", downhill flow ends at " + DisplayOS(nearPoint.x(), nearPoint.y()) + ", abandoning\n")

               shared.thisFieldPathSegIDsTried.append(featID)
               continue

         else:
            # The nearest point is neither the first or last point in the path polyline
            prevPoint = linePoints[numNearPoint-1]
            elevPrevPoint = GetRasterElev(prevPoint.x(), prevPoint.y())

            postPoint = linePoints[numNearPoint+1]
            elevPostPoint = GetRasterElev(postPoint.x(), postPoint.y())

            shared.fpOut.write("\tC: prev point elev = " + str(elevPrevPoint) + ", nearest point elev = " + str(elevNearPoint) + ", post point elev = " + str(elevPostPoint) + "\n")

            pts = [[PREV_POINT, elevPrevPoint], [THIS_POINT, elevNearPoint], [POST_POINT, elevPostPoint]]
            pts.sort(key = lambda pt: pt[1])

            for m in range(3):
               shared.fpOut.write("\tpts[" + str(m) + "][0] = " + str(pts[m][0]) + ", pts[" + str(m) + "][1] = " + str(pts[m][1]) + "\n")

            if pts[0][0] == THIS_POINT:
               # Near point is lowest: we are in a blind pit, so try the next path segment in the list of untravelled path segments
               shared.fpOut.write("\tIn path blind pit: for path segment " + fullDesc + ", downhill flow ends at " + DisplayOS(nearPoint.x(), nearPoint.y()) + ", abandoning\n")

               shared.thisFieldPathSegIDsTried.append(featID)
               continue

            elif pts[1][0] == THIS_POINT:
               if pts[0][0] == PREV_POINT:
                  # The previous point is lower than the near point, so flow goes towards the first point
                  shared.fpOut.write("\tFlow towards first point in path (c)\n")
                  flowTowardsLastPoint = False

                  # Forget about this list of untravelled path segments since we have found a suitable one
                  flowRouted = True
                  break

               else:
                  # The post point is lower than the near point, so flow goes towards the last point
                  shared.fpOut.write("\tFlow towards last point in path (d)\n")
                  flowTowardsLastPoint = True

                  # Forget about this list of untravelled path segments since we have found a suitable one
                  flowRouted = True
                  break

            else:
               # Both first and last points are lower, so we need to compare gradients
               shared.fpOut.write("\tprevPoint = " + DisplayOS(prevPoint.x(), prevPoint.y()) + " nearPoint = " + DisplayOS(nearPoint.x(), nearPoint.y()) + " postPoint = " + DisplayOS(postPoint.x(), postPoint.y()) + "\n")

               flowToLast = FindSteepestSegment(prevPoint, nearPoint, postPoint, elevNearPoint - elevPrevPoint, elevNearPoint - elevPostPoint)
               shared.fpOut.write("\t" + str(flowToLast) + " \n")

               if flowToLast:
                  flowTowardsLastPoint = True
                  shared.fpOut.write("\tFlow towards last point in path (e)\n")

                  # Forget about this list of untravelled path segments since we have found a suitable one
                  flowRouted = True
                  break

               else:
                  flowTowardsLastPoint = False
                  shared.fpOut.write("\tFlow towards first point in path (f)\n")

                  # Forget about this list of untravelled path segments since we have found a suitable one
                  flowRouted = True
                  break

      if flowRouted:
         # OK we know the initial direction of flow along this path, so keep going downhill till we reach a pre-existing flow line, a ditch/stream, a blind pit, or the end of the path
         shared.thisFieldPathSegIDsTried.append(featID)

         elevThisPoint = GetRasterElev(thisPoint.x(), thisPoint.y())

         printStr = "Flow from field " + fieldCode + " enters the path segment " + fullDesc + " at " + DisplayOS(thisPoint.x(), thisPoint.y()) + " "
         shared.fpOut.write("\t" + printStr + "\n")

         AddFlowMarkerPoint(thisPoint, FLOW_VIA_PATH, fieldCode, elevThisPoint)

         nPoints = len(linePoints)

         if flowTowardsLastPoint:
            # Flow goes towards the last point of the path segment
            for nn in range(numNearPoint, len(linePoints)+1):
               shared.fpOut.write("\tTowards last point of path segment " + fullDesc + " at " + DisplayOS(linePoints[nn].x(), linePoints[nn].y()) + ", nn = " + str(nn) + ", nPoints = " + str(nPoints) + "\n")

               # Are we at the final point in the line?
               if nn == nPoints-1:
                  shared.fpOut.write("\tAt last point of path segment " + fullDesc + " " + DisplayOS(linePoints[nn].x(), linePoints[nn].y()) + "\n")
                  return 4, linePoints[nn]

               # Not at the last point on the line
               thisPoint = linePoints[nn]
               nextPoint = linePoints[nn+1]
               elevThisPoint = GetRasterElev(thisPoint.x(), thisPoint.y())
               elevNextPoint = GetRasterElev(nextPoint.x(), nextPoint.y())

               # Check to see whether this path segment intersects a ditch/stream segment (note that we have not yet checked whether the next point is downhill from this point, but is a reasonable assumption that any intersect point must be downhill from this point)
               geomLine = QgsGeometry.fromPolyline([thisPoint, nextPoint])
               rtn = -1
               streamIntersectPoints = []
               rtn, streamIntersectPoints = FindSegmentIntersectionWithStream(geomLine)
               if rtn == -1:
                  # Error
                  return -1, -1

               elif rtn == 1:
                  # We have at least one intersection
                  for intPoint in streamIntersectPoints:
                     AddFlowLine(thisPoint, intPoint, FLOW_VIA_PATH, fieldCode, -1)

                     # NOTE we are only considering the first intersection point
                     return 2, intPoint

               # Next check to see whether the next point is downhill from this point
               if elevNextPoint > elevThisPoint + TOLERANCE:
                  # The next point is not downhill, so stop flowing along this path segment
                  shared.fpOut.write("\tFlow from field " + fieldCode + " hit a blind pit in path segment " + fullDesc + " at " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n")

                  return 1, thisPoint

               # OK, we are flowing downhill along the path segment
               AddFlowLine(thisPoint, nextPoint, FLOW_VIA_PATH, fieldCode, -1)

               # Check for pre-existing flow lines near the next point
               adjX, adjY, hitFieldFlowFrom = FindNearbyFlowLine(nextPoint)
               if adjX != -1:
                  # There is an adjacent flow line, so merge the two and finish with this flow line
                  adjPoint = QgsPoint(adjX, adjY)
                  AddFlowLine(thisPoint, adjPoint, MERGED_WITH_ADJACENT_FLOWLINE, fieldCode, -1)

                  shared.fpOut.write("Flow from field " + fieldCode + " hit flow from field " + str(hitFieldFlowFrom) + " at " + DisplayOS(adjX, adjY) + " while moving along path segment " + fullDesc + ", so stopped tracing flow from this field\n")

                  return 3, adjPoint

               # Do we have a field observation near the next point?
               indx = FindNearbyFieldObservation(nextPoint)
               if indx != -1:
                  # We have found a field observation near this point, so route flow accordingly
                  rtn, adjPoint = FlowViaFieldObservation(indx, fieldCode, nextPoint, elevNextPoint)
                  if rtn == 0:
                     # Flow has passed through the field observation
                     shared.fpOut.write("Left FlowViaFieldObservation() called in FlowAlongVectorPath() 1, rtn = " + str(rtn) + "\n")
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
                     # Flow has passed through the field observation and is flowing along a path
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(nextPoint.x(), nextPoint.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + ", flowed along path so looking for other paths AAA\n")
                     return rtn, thisPoint

         else:
            # Flow goes towards the first point of the path segment
            for nn in range(numNearPoint, -1, -1):
               shared.fpOut.write("\tTowards first point of path segment " + fullDesc + " at " + DisplayOS(linePoints[nn].x(), linePoints[nn].y()) + ", nn = " + str(nn) + ", nPoints = " + str(nPoints) + "\n")

               # Are we at the first point in the line?
               if nn == 0:
                  shared.fpOut.write("\tAt first point of path segment " + fullDesc + " " + DisplayOS(linePoints[0].x(), linePoints[0].y()) + "\n")
                  return 4, linePoints[0]

               # Not at the first point on the line
               thisPoint = linePoints[nn]
               nextPoint = linePoints[nn-1]
               elevThisPoint = GetRasterElev(thisPoint.x(), thisPoint.y())
               elevNextPoint = GetRasterElev(nextPoint.x(), nextPoint.y())

               # Check to see whether this path segment intersects a ditch/stream segment (note that we have not yet checked whether the next point is downhill from this point, but is a reasonable assumption that any intersect point must be downhill from this point)
               geomLine = QgsGeometry.fromPolyline([thisPoint, nextPoint])
               rtn = -1
               streamIntersectPoints = []
               rtn, streamIntersectPoints = FindSegmentIntersectionWithStream(geomLine)
               if rtn == -1:
                  # Error
                  return -1, -1

               elif rtn == 1:
                  # We have at least one intersection
                  for intPoint in streamIntersectPoints:
                     AddFlowLine(thisPoint, intPoint, FLOW_VIA_ROAD, fieldCode, -1)

                     # NOTE we are only considering the first intersection point
                     return 2, intPoint

               # Next check to see whether the next point is downhill from this point
               if elevNextPoint > elevThisPoint + TOLERANCE:
                  # The next point is not downhill, so stop flowing along this path segment
                  shared.fpOut.write("\tFlow from field " + fieldCode + " hit a blind pit in path segment " + fullDesc + " at " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n")

                  return 1, thisPoint

               # OK, we are flowing downhill along the path segment
               AddFlowLine(thisPoint, nextPoint, FLOW_VIA_ROAD, fieldCode, -1)

               # Check for pre-existing flow lines near the next point
               adjX, adjY, hitFieldFlowFrom = FindNearbyFlowLine(nextPoint)
               if adjX != -1:
                  # There is an adjacent flow line, so merge the two and finish with this flow line
                  AddFlowLine(thisPoint, QgsPoint(adjX, adjY), MERGED_WITH_ADJACENT_FLOWLINE, fieldCode, -1)

                  shared.fpOut.write("Flow from field " + fieldCode + " hit flow from field " + str(hitFieldFlowFrom) + " at " + DisplayOS(adjX, adjY) + " while moving along path segment " + fullDesc + ", so stopped tracing flow from this field\n")

                  return 3, adjPoint

               # Do we have a field observation near the next point?
               indx = FindNearbyFieldObservation(nextPoint)
               if indx != -1:
                  # We have found a field observation near this point, so route flow accordingly
                  rtn, adjPoint = FlowViaFieldObservation(indx, fieldCode, nextPoint, elevNextPoint)
                  shared.fpOut.write("Left FlowViaFieldObservation() called in FlowAlongVectorPath() 2, rtn = " + str(rtn) + "\n")
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
                     # Flow has passed through the field observation and is flowing along a path
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(nextPoint.x(), nextPoint.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + ", flowed along path so looking for other paths BBB\n")
                     return rtn, thisPoint


      if not flowRouted:
         shared.fpOut.write("\tNo suitable path/track segment found at " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n")
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

            polyBoundary = fieldBoundary.constGeometry().asPolygon()

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

   #obsCategory = shared.fieldObservationCategory[indx]
   #obsBehaviour = shared.fieldObservationBehaviour[indx]
   #obsDesc = shared.fieldObservationDescription[indx]

   shared.thisFieldFieldObsAlreadyFollowed.append(indx)

   #print("Entered flowAlongVectorFieldBoundary at point " + DisplayOS(thisPoint.x(), thisPoint.y()))
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

   #numberToSearchFor = 3

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
      shared.fpOut.write("Flow along boundary from field " + str(fieldCode) + " ends at " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n*** Please add a field observation\n")
      return 1, thisPoint

   # OK we have some possibly suitable boundary polygons
   #for n in range(len(distToPoint)):
      #shared.fpOut.write("Before " + str(n) + " " + str(distToPoint[n][0].id()) + " " + DisplayOS(distToPoint[n][1].x(), distToPoint[n][1].y()) + " " + str(distToPoint[n][2]) + " m")

   # Sort the list of untravelled boundary polygons, closest first
   distToPoint.sort(key = lambda distPoint: distPoint[2])

   #for n in range(len(distToPoint)):
      #print"After " + (str(n) + " " + str(distToPoint[n][0].id()) + " " + DisplayOS(distToPoint[n][1].x(), distToPoint[n][1].y()) + " " + str(distToPoint[n][2]) + " m")

   flowRouted = False
   for boundPoly in distToPoint:
      # Go through this list of untravelled boundary polygons till we find a suitable one
      feature = boundPoly[0]
      #featID = feature.id()
      #print("Trying feature ID " + str(featID))

      boundaryFieldCode = feature[CONNECTED_FIELD_ID]

      geomFeat = feature.geometry()
      polygon = geomFeat.asPolygon()
      points = polygon[0]
      nPointsInPoly = len(points)

      # OK, the nearest point is an approximation: it is not necessarily a point in the polygon's boundary. So get the actual point in the boundary which is closest
      nearPoint, numNearPoint, _beforeNearPoint, _afterNearPoint, sqrDist = geomFeat.closestVertex(boundPoly[1])
      #print(nearPoint, numNearPoint, beforeNearPoint, afterNearPoint, sqrDist)
      #print(nearPoint, points[numNearPoint])

      shared.fpOut.write("\tAt " + DisplayOS(thisPoint.x(), thisPoint.y()) +", trying untravelled boundary of field " + str(boundaryFieldCode) + "  which has nearest point " + "{:0.1f}".format(sqrt(sqrDist)) + " m away at " + DisplayOS(nearPoint.x(), nearPoint.y()) + "\n")

      #shared.fpOut.write("\tNearest point of boundary polygon is " + DisplayOS(nearPoint.x(), nearPoint.y()) + "\n")

      # May need to flow to this nearest vertex
      if thisPoint != nearPoint:
         AddFlowLine(thisPoint, nearPoint, FLOW_VIA_BOUNDARY, fieldCode, -1)

         thisPoint = nearPoint

      numThisVertex = numNearPoint

      # OK, so we know which field boundary polygon we are dealing with: now loop until we either hit a blind pit, a stream, or a field observation
      verticesTravelled = [numThisVertex]

      while True:
         #print("Start of flowAlongVectorFieldBoundary loop at " + DisplayOS(thisPoint.x(), thisPoint.y()) + " vertex " + str(numThisVertex))

         # Find out which direction along the polygon's edge has the steepest downhill slope
         flowRouted = False

         elevThisPoint = GetRasterElev(thisPoint.x(), thisPoint.y())

         geomThisPoint = QgsGeometry.fromPoint(thisPoint)

         prevSlope = nextSlope = -1

         # Calculate the elevation difference for the previous point, if not already visited
         numPrevVertex = numThisVertex - 1
         if numPrevVertex < 0:
            numPrevVertex = nPointsInPoly - 2

         if numPrevVertex not in verticesTravelled:
            # This vertex has not already had flow through it
            prevPoint = points[numPrevVertex]

            elevPrevPoint = GetRasterElev(prevPoint.x(), prevPoint.y())

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

            elevNextPoint = GetRasterElev(nextPoint.x(), nextPoint.y())

            elevDiffNext = elevThisPoint - elevNextPoint

            geomNextPoint = QgsGeometry.fromPoint(nextPoint)
            nextDist = geomThisPoint.distance(geomNextPoint)

            #print(numNextVertex, nextPoint, elevDiffNext, nextDist)
            nextSlope = elevDiffNext / nextDist

         #print(prevSlope, nextSlope, verticesTravelled)

         if prevSlope <= 0 and nextSlope <= 0:
            # We are in a blind pit
            shared.fpOut.write("\tIn blind pit on boundary of field " + str(boundaryFieldCode) + ": downhill flow ends at " + DisplayOS(thisPoint.x(), thisPoint.y()) + ", abandoning\n")

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

         # Check to see whether this field boundary intersects a stream segment
         geomLine = QgsGeometry.fromPolyline([thisPoint, flowToPoint])
         rtn = -1
         streamIntersectPoints = []
         #streamIntersectFound = False
         rtn, streamIntersectPoints = FindSegmentIntersectionWithStream(geomLine)
         if rtn == -1:
            # Error
            return -1, -1

         elif rtn == 1:
            # We have at least one intersection
            #streamIntersectFound = True
            for intPoint in streamIntersectPoints:
               shared.fpOut.write("The boundary of field " + str(boundaryFieldCode) + " intersects a stream at " + DisplayOS(intPoint.x(), intPoint.y()) + "\n*** Does flow enter the stream here?\n")

               AddFlowLine(thisPoint, intPoint, FLOW_VIA_BOUNDARY, fieldCode, -1)

               # NOTE we are only considering the first intersection point
               return 2, intPoint

         # OK, now find the in-between points
         inBetweenPoints = GetPointsOnLine(thisPoint, flowToPoint, shared.searchDist)
         for nPoint in range(len(inBetweenPoints)-1):
            # Do this for every in-between point
            point1 = inBetweenPoints[nPoint]
            point2 = inBetweenPoints[nPoint+1]

            # Check for nearby flow lines
            adjX, adjY, hitFieldFlowFrom = FindNearbyFlowLine(point1)
            if adjX != -1:
               # There is an adjacent flow line, so merge the two and finish with this flow line
               adjPoint = QgsPoint(adjX, adjY)
               AddFlowLine(point1, adjPoint, MERGED_WITH_ADJACENT_FLOWLINE, fieldCode, -1)

               shared.fpOut.write("Flow from field " + fieldCode + " hit flow from field " + str(hitFieldFlowFrom) + " at " + DisplayOS(adjX, adjY) + ", so stopped tracing flow from this field\n")

               return 3, adjPoint

            # If the field boundary is convex at this vertex (i.e. bulges inward) then find out whether flow leaves the boundary because an adjacent within-polygon cell has a steeper gradient
            # TODO make a user option
            flowAwayFromBoundary = True
            if flowAwayFromBoundary and nPoint > 0:
               point0 = inBetweenPoints[nPoint-1]
               z = CalcZCrossProduct(point0, point1, point2)

               if (forward and z > 0) or (not forward and z < 0):
                  #print(point1, z)

                  elev = GetRasterElev(point1.x(), point1.y())

                  # Search for the adjacent raster cell with the steepest here-to-there slope, and get its centroid
                  geomPoint1 = QgsGeometry.fromPoint(point1)
                  adjPoint, _adjElev = FindSteepestAdjacent(point1, elev, geomPoint1)
                  #print(adjPoint, adjElev)
                  if adjPoint.x() != -1:
                     # There is a within-polygon cell with a steeper gradient
                     AddFlowLine(point1, adjPoint, FLOW_DOWN_STEEPEST, fieldCode, elev)

                     shared.fpOut.write("\tFlow from field " + str(fieldCode) + " has left the boundary of field " + str(boundaryFieldCode) + " at " + DisplayOS(point1.x(), point1.y()) + " and flows down the steepest with-in field gradient, to " +  DisplayOS(adjPoint.x(), adjPoint.y()) + "\n")

                     return 0, adjPoint

            # Do we have a nearby field observation?
            indx = FindNearbyFieldObservation(point1)
            if indx != -1:
               # We have found a field observation near this point
               thisElev = GetRasterElev(point1.x(), point1.y())

               # So route flow accordingly
               rtn, adjPoint = FlowViaFieldObservation(indx, fieldCode, point1, thisElev)
               shared.fpOut.write("Left FlowViaFieldObservation() called in flowAlongVectorFieldBoundary(), rtn = " + str(rtn) + "\n")
               if rtn == 0:
                  # Flow has passed through the LE
                  return rtn, adjPoint

               elif rtn == -1:
                  # Could not determine the outflow location
                  shared.fpOut.write("Along-boundary flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(point1.x(), point1.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + ", could not determine outflow location\n")
                  return rtn, thisPoint

               elif rtn == 1:
                  # Flow has passed through the field observation and then hit a blind pit
                  shared.fpOut.write("Along-boundary flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(point1.x(), point1.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + ", hit blind pit\n")
                  return rtn, thisPoint

               elif rtn == 2:
                  # Flow has hit a stream
                  shared.fpOut.write("Along-boundary flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(point1.x(), point1.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + " stream\n")
                  return rtn, thisPoint

               elif rtn == 3:
                  # Merged with pre-existing flow
                  shared.fpOut.write("Along-boundary flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(point1.x(), point1.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + ", merged with pre-existing flow\n")
                  return rtn, thisPoint

               elif rtn == 4:
                  # Flow has passed through the field observation and is flowing along a road
                  shared.fpOut.write("Flow from field " + str(fieldCode) + " via field observation from " + DisplayOS(nextPoint.x(), nextPoint.y()) + " to " + DisplayOS(adjPoint.x(), adjPoint.y()) + ", flowed along road so looking for other roads EEE\n")
                  return rtn, thisPoint

            # No nearby field observation

         # OK we have flow routed between these two vertices of the field boundary
         flowRouted = True

         printStr = "\tFlow from field " + fieldCode + " flows along the boundary of field " + str(boundaryFieldCode) + " from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to " + DisplayOS(flowToPoint.x(), flowToPoint.y())  + "\n"
         shared.fpOut.write(printStr)

         AddFlowLine(thisPoint, flowToPoint, FLOW_VIA_BOUNDARY, fieldCode, -1)

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
         AddFlowLine(thisPoint, cell, BLIND_PIT, fieldCode, -1)

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
