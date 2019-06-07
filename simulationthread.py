from PyQt5.QtCore import QThread, pyqtSignal

from qgis.core import QgsPointXY, QgsGeometry, QgsFeatureRequest

import shared
from shared import INPUT_FIELD_BOUNDARIES, CONNECTED_FIELD_ID, INPUT_RASTER_BACKGROUND, MARKER_FLOW_START_POINT_1, MARKER_FLOW_START_POINT_2, MERGED_WITH_ADJACENT_FLOWLINE, FLOW_ADJUSTMENT_DUMMY, MARKER_HIT_BLIND_PIT, MARKER_FORCE_FLOW, MARKER_ENTER_STREAM, FIELD_OBS_CATEGORY_BOUNDARY, FIELD_OBS_CATEGORY_ROAD, FIELD_OBS_CATEGORY_PATH, MARKER_HIT_ROAD, MARKER_HIT_PATH, FLOW_OUT_OF_BLIND_PIT, FLOW_TO_FIELD_BOUNDARY, FLOW_DOWN_STEEPEST, MARKER_HIGHEST_POINT, MARKER_LOWEST_POINT, MARKER_CENTROID, ROUTE_ROAD, ROUTE_PATH
from layers import AddFlowMarkerPoint, AddFlowLine, WriteVector
from simulate import GetHighestAndLowestPointsOnFieldBoundary, FlowViaFieldObservation, FlowHitFieldBoundary, FillBlindPit, FlowAlongVectorRoute
from searches import FindNearbyStream, FindNearbyFlowLine, FindNearbyFieldObservation, FindNearbyRoad, FindNearbyPath, FindSteepestAdjacent
from utils import GetRasterElev, GetCentroidOfContainingDEMCell, DisplayOS, IsPointInPolygon


#======================================================================================================================
#
# Class for the simulation thread
#
#======================================================================================================================
class SimulationThread(QThread):
   refresh = pyqtSignal()
   runDone = pyqtSignal()


   #======================================================================================================================
   #
   # Initialises the thread
   #
   #======================================================================================================================
   def __init__(self, app, appWindow):
      QThread.__init__(self)
      self.app = app
      self.appWindow = appWindow
   #======================================================================================================================


   #======================================================================================================================
   #
   # Runs the simulation
   #
   #======================================================================================================================
   def run(self):
      # pylint: disable=too-many-locals
      # pylint: disable=too-many-nested-blocks
      # pylint: disable=too-many-branches
      # pylint: disable=too-many-statements

      shared.flowStartPoints = []

      doAllFields = True
      if shared.sourceFields:
         doAllFields = False

      #===================================================================================================================
      # OK, off we go. First determine the flow start points
      #===================================================================================================================
      shared.fpOut.write("\n" + shared.dividerLen * shared.dividerChar + "\n\n")
      shared.fpOut.write("SIMULATED FLOW START POINTS, PER FIELD\n\n")

      fieldCodesStartPointFound = []
      for layerNum in range(len(shared.vectorInputLayersCategory)):
         #fields = shared.vectorInputLayers[layerNum].fields().toList()
         #for field in fields:
            #shared.fpOut.write(field.name())
         #shared.fpOut.write("\n")

         if shared.vectorInputLayersCategory[layerNum] == INPUT_FIELD_BOUNDARIES:
            request = QgsFeatureRequest(shared.extentRect)
            features = shared.vectorInputLayers[layerNum].getFeatures(request)
            for fieldBoundary in features:
               # Get the field code
               fieldCode = fieldBoundary[CONNECTED_FIELD_ID]

               # Is the centroid of this field within the coverage of one of the raster landscape element files which we have read in? TODO change to vector extent
               isWithinCoverage = False
               centroidPoint = fieldBoundary.geometry().centroid().asPoint()
               for n in range(len(shared.rasterInputLayersCategory)):
                  if shared.rasterInputLayersCategory[n] == INPUT_RASTER_BACKGROUND:
                     if shared.extentRect.contains(centroidPoint):
                        isWithinCoverage = True
                        break

               if not isWithinCoverage:
                  continue

               #print("fieldCode = " + str(fieldCode))
               #print("fieldCodesStartPointFound = " + str(fieldCodesStartPointFound))

               # Ignore any duplicate fields
               if fieldCode not in fieldCodesStartPointFound:
                  # Calculate the start-of-flow location only for fields which generate runoff
                  if not doAllFields and fieldCode not in shared.sourceFields:
                     shared.fpOut.write("Not calculating start of flow for field " + str(fieldCode) + ", this is not a source field\n")
                     continue

                  #print("Finding flow start point for field " + str(fieldCode))

                  # Get the coords of the centroid of the pixel which contains the highest point and lowest point on the boundary of this field (including in-between points), and also the elevation of these points
                  xMaxBoundary, yMaxBoundary, _maxBoundaryElev, xMinBoundary, yMinBoundary, _minBoundaryElev = GetHighestAndLowestPointsOnFieldBoundary(fieldBoundary)

                  # Are the results valid?
                  if (xMaxBoundary == -1) or (xMinBoundary == -1):
                     # No
                     continue

                  # Is valid, so show the highest and lowest points on the map
                  #AddFlowMarkerPoint(QgsPointXY(xMaxBoundary, yMaxBoundary), str(fieldCode) + MARKER_HIGHEST_POINT, fieldCode, _maxBoundaryElev)
                  #AddFlowMarkerPoint(QgsPointXY(xMinBoundary, yMinBoundary), str(fieldCode) + MARKER_LOWEST_POINT, fieldCode, _minBoundaryElev)

                  # OK, get the elevation of the field's centroid
                  xCentroid = centroidPoint.x()
                  yCentroid = centroidPoint.y()

                  # Show the centroid on the map
                  #AddFlowMarkerPoint(centroidPoint, str(fieldCode) + MARKER_CENTROID, fieldCode, GetRasterElev(xCentroid, yCentroid))

                  # Calculate the flow start point for this field, as a weighted average of the highest boundary point and the centroid point
                  weightCentroid = 1 - shared.weightBoundary
                  xFlowStart = (xMaxBoundary * shared.weightBoundary) + (xCentroid * weightCentroid)
                  yFlowStart = (yMaxBoundary * shared.weightBoundary) + (yCentroid * weightCentroid)

                  startPoint = QgsPointXY(xFlowStart, yFlowStart)

                  # In some cases, the flow start point may not be within the field polygon. if it isn't, then find the nearest within-polygon point
                  if not IsPointInPolygon(startPoint, fieldBoundary):
                     nearPointGeom = fieldBoundary.geometry().nearestPoint(QgsGeometry.fromPointXY(startPoint))
                     nearPoint = nearPointGeom.asPoint()

                     printStr = "For field " + str(fieldCode) +", the flow start point " + DisplayOS(xFlowStart, yFlowStart) + " is not within the field, so changing the flow start point to " + DisplayOS(nearPoint.x(), nearPoint.y()) + "\n"
                     shared.fpOut.write(printStr)

                     startPoint = nearPoint
                     xFlowStart = nearPoint.x()
                     yFlowStart = nearPoint.y()

                  # OK, we have an acceptable flow start point for this field, so get its elevation
                  flowStartElev = GetRasterElev(xFlowStart, yFlowStart)

                  # Save the flow start point for this field
                  shared.flowStartPoints.append([xFlowStart, yFlowStart, flowStartElev, fieldCode])
                  #print("ADDED FLOW START POINT")
                  fieldCodesStartPointFound.append(fieldCode)

                  # And show it on the map
                  AddFlowMarkerPoint(startPoint, MARKER_FLOW_START_POINT_1 + fieldCode + MARKER_FLOW_START_POINT_2, fieldCode, flowStartElev)
                  shared.fpOut.write("Flow from field " + fieldCode + " begins at " + DisplayOS(xFlowStart, yFlowStart) + "\n")

                  # Refresh the display
                  self.refresh.emit()

      # Have we missed any fields? If so, give an error message but carry on with the simulation
      nSourceFieldsFound = len(shared.flowStartPoints)
      nSourceFieldsSpecified = len(shared.sourceFields)
      if nSourceFieldsFound != nSourceFieldsSpecified:
         printStr = "ERROR: " + str(nSourceFieldsFound) + " fields found but " + str(nSourceFieldsSpecified) + " fields specified"
         print(printStr)
         shared.fpOut.write(printStr + "\n")

         startFldCode = []
         for startFld in shared.flowStartPoints:
            startFldCode.append(startFld[3])

         missingFlds = []
         for fld in shared.sourceFields:
            if fld not in startFldCode:
               missingFlds.append(fld)

         for missedFld in missingFlds:
            printStr = "\tField " + str(missedFld) + " omitted, is this field within the displayed extent?"
            print(printStr)
            shared.fpOut.write(printStr + "\n")

         print("\n")
         shared.fpOut.write("\n")

      # Next, sort the list of flow start points so that we first process the highest i.e. we work downhill
      shared.flowStartPoints.sort(key = lambda fieldPoint: fieldPoint[2], reverse = True)
      #for field in shared.flowStartPoints:
         #print(field)

      # Initialize ready for the simulation
      shared.allFieldsFlowPath = []
      shared.allFieldsFlowPathFieldCode = []
      shared.allFieldsFieldObsAlreadyFollowed = []

      shared.thisFieldFlowLine = []
      shared.thisFieldFlowLineFieldCode = []
      shared.thisFieldFieldObsAlreadyFollowed = []

      #===================================================================================================================
      # The main loop, go round this once for every field that generates runoff
      #===================================================================================================================
      for field in range(len(shared.flowStartPoints)):
         # Are we simulating flow from this field?
         fieldCode = shared.flowStartPoints[field][3]
         if not doAllFields:
            if fieldCode not in shared.sourceFields:
               # Nope
               continue

         # If this isn't the first field simulated, then save the last field's flow path and the last field's list of Field Observations used
         if shared.thisFieldFlowLine:
            shared.allFieldsFlowPath.extend(shared.thisFieldFlowLine)
            shared.allFieldsFlowPathFieldCode.extend(shared.thisFieldFlowLineFieldCode)

            for feature in shared.outFlowLineLayer.getFeatures():
               shared.outFlowLineLayerIndex.insertFeature(feature)

         # If we are considering LE-flow interactions, and flow for the last field travelled via at least one field observation, then save the last field's list of LE-flow interactions
         if shared.considerLEFlowInteractions and shared.thisFieldFieldObsAlreadyFollowed:
            shared.allFieldsFieldObsAlreadyFollowed.extend(shared.thisFieldFieldObsAlreadyFollowed)

         # OK, do some initialization
         shared.thisFieldFlowLine = []
         shared.thisFieldFlowLineFieldCode = []
         shared.thisFieldRoadSegIDsTried = []
         shared.thisFieldPathSegIDsTried = []
         shared.thisFieldFieldObsAlreadyFollowed = []

         x = shared.flowStartPoints[field][0]
         y = shared.flowStartPoints[field][1]
         thisPoint = QgsPointXY(x, y)
         elev = shared.flowStartPoints[field][2]
         fieldCode = shared.flowStartPoints[field][3]

         viaLEAndHitBlindPit = False
         viaLEAndHitStream = False
         viaLEAndAlongRoad = False
         viaLEAndAlongPath = False
         viaRoadAndHitStream = False
         viaPathAndHitStream = False

         shared.fpOut.write("\n" + shared.dividerLen * shared.dividerChar + "\n\n")
         shared.fpOut.write("SIMULATED FLOW FROM SOURCE FIELD " + str(fieldCode) + "\n\n")
         shared.fpOut.write("Flow from field " + str(fieldCode) + " starts at " + DisplayOS(x, y) + "\n")
         shared.thisStartPoint += 1

         nStepsAfterStart = 0

         inBlindPit = False
         hitBoundary = False
         hitRoadBehaviourUnknown = False
         hitPathBehaviourUnknown = False

         hitFieldCode = -1

         #================================================================================================================
         # The inner loop, keep going round this until flow from this field reaches the river, or can go no further
         #================================================================================================================
         while True:
            # Refresh the display
            self.refresh.emit()

            #shared.fpOut.write("At start of inner loop, thisPoint = " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n")

            # Safety check
            nStepsAfterStart += 1
            if nStepsAfterStart > 10000:
               # Flow line is excessively long
               shared.fpOut.write("ERROR: flow line too long")

               # So give up and move on to next field
               break

            #=============================================================================================================
            # First search for nearby streams and rivers
            #=============================================================================================================
            rtn = FindNearbyStream(thisPoint, fieldCode)
            if rtn == -1:
               # Problem! Exit the program
               exit (-1)
            elif rtn == 1:
               # Flow entered a stream and reached the Rother. We are done here, so move on to the next field
               #shared.fpOut.write("In stream\n")
               self.refresh.emit()
               break

            #=============================================================================================================
            # Flow did not enter a stream, so next search for nearby pre-existing flowlines
            #=============================================================================================================
            adjX, adjY, hitFieldFlowFrom = FindNearbyFlowLine(thisPoint)
            if adjX != -1:
               # There is an adjacent flow line, so merge the two and finish with this flow line
               AddFlowLine(thisPoint, QgsPointXY(adjX, adjY), MERGED_WITH_ADJACENT_FLOWLINE, fieldCode, elev)
               shared.fpOut.write("Flow from field " + fieldCode + " hit flow from field " + str(hitFieldFlowFrom) + " at " + DisplayOS(adjX, adjY) + ", so stopped tracing flow from this field\n")

               # Move on to the next field
               self.refresh.emit()
               break

            #=============================================================================================================
            # Flow did not merge with a pre-existing flowline. Make sure that this point is at the centroid of a DEM cell
            #=============================================================================================================
            #tempPoint = GetCentroidOfContainingDEMCell(thisPoint.x(), thisPoint.y())
            #if not (inBlindPit or viaLEAndHitBlindPit or viaLEAndHitStream) and tempPoint != thisPoint:
               ## We had to shift the location slightly, so show a connecting line
               #AddFlowLine(thisPoint, tempPoint, FLOW_ADJUSTMENT_DUMMY, fieldCode, -1)
               #thisPoint = tempPoint

            #=============================================================================================================
            #  OK, we are now considering LE-flow interactions
            #=============================================================================================================
            if shared.considerLEFlowInteractions:
               if viaLEAndAlongRoad:
                  #==========================================================================================================
                  # Was flowing along a road but reached the beginning or end of that road, so search for another nearby road
                  #==========================================================================================================
                  rtn = FindNearbyRoad(thisPoint, fieldCode, viaLEAndAlongRoad)
                  if rtn == -1:
                     # Problem! Exit the program
                     exit (-1)
                  elif rtn == 1:
                     # We have found a road, so mark it
                     AddFlowMarkerPoint(thisPoint, MARKER_HIT_ROAD, fieldCode, -1)

                     # And try to flow along this road
                     rtn, point = FlowAlongVectorRoute(ROUTE_ROAD, -1, fieldCode, thisPoint)
                     #shared.fpOut.write("\tFinished flow along road B at " + DisplayOS(point.x(), point.y()) + " with rtn = " + str(rtn) + "\n")
                     if rtn == -1:
                        # A problem! Exit the program
                        exit (-1)

                     elif rtn == 1:
                        # Flow has hit a blind pit
                        shared.fpOut.write("Flow from field " + str(fieldCode) + " hit a blind pit at " + DisplayOS(point.x(), point.y()) + " while flowing along a road\n*** Please add a field observation\n")

                        # Move on to next field
                        self.refresh.emit()
                        break

                     elif rtn == 2:
                        # Flow has hit a stream, so carry on and look for a field observation (or the Rother)
                        viaRoadAndHitStream = True
                        viaLEAndAlongRoad = False
                        thisPoint = point
                        #shared.fpOut.write("viaRoadAndHitStream = True, viaLEAndAlongRoad = False, looking for FO\n")
                        continue

                     elif rtn == 3:
                        # Flow has merged with pre-existing flow, so move on to next field
                        self.refresh.emit()
                        break

                     elif rtn == 4:
                        # Flow has reached the beginning or end of the road, so carry on flowing along any other nearby roads
                        viaLEAndAlongRoad = True
                        thisPoint = point

                        # Back to the start of the inner loop
                        continue

                     else:
                        # Carry on from this point
                        viaLEAndAlongRoad = False
                        thisPoint = point

                        # Back to the start of the inner loop
                        continue

               if viaLEAndAlongPath:
                  #==========================================================================================================
                  # Was flowing along a path but reached the beginning or end of that path, so search for another nearby path
                  #==========================================================================================================
                  rtn = FindNearbyPath(thisPoint, fieldCode, viaLEAndAlongPath)
                  if rtn == -1:
                     # Problem! Exit the program
                     exit (-1)
                  elif rtn == 1:
                     # We have found a path, so mark it
                     AddFlowMarkerPoint(thisPoint, MARKER_HIT_PATH, fieldCode, -1)

                     # And try to flow along this path
                     rtn, point = FlowAlongVectorRoute(ROUTE_PATH, -1, fieldCode, thisPoint)
                     #shared.fpOut.write("\tFinished flow along path B at " + DisplayOS(point.x(), point.y()) + " with rtn = " + str(rtn) + "\n")
                     if rtn == -1:
                        # A problem! Exit the program
                        exit (-1)

                     elif rtn == 1:
                        # Flow has hit a blind pit
                        shared.fpOut.write("Flow from field " + str(fieldCode) + " hit a blind pit at " + DisplayOS(thisPoint.x(), thisPoint.y()) + " while flowing along a path\n*** Please add a field observation\n")

                        # Move on to next field
                        self.refresh.emit()
                        break

                     elif rtn == 2:
                        # Flow has hit a stream, so carry on and look for a field observation (or the Rother)
                        viaPathAndHitStream = True
                        viaLEAndAlongPath = False
                        thisPoint = point
                        #shared.fpOut.write("viaPathAndHitStream = True\n")
                        continue

                     elif rtn == 3:
                        # Flow has merged with pre-existing flow, so move on to next field
                        self.refresh.emit()
                        break

                     elif rtn == 4:
                        # Flow has reached the beginning or end of the path, so carry on flowing along any other nearby paths
                        viaLEAndAlongPath = True
                        thisPoint = point

                        # Back to the start of the inner loop
                        continue

                     else:
                        # Carry on from this point
                        viaLEAndAlongPath = False
                        thisPoint = point

                        # Back to the start of the inner loop
                        continue

               #==========================================================================================================
               # Search for a field observation of a landscape element-flow interaction near this point
               #==========================================================================================================
               #shared.fpOut.write("Searching for LE-flow interactions for flow from field " + str(fieldCode) + " near " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n")
               indx = FindNearbyFieldObservation(thisPoint)
               if indx == -1:
                  # Did not find a field observation near this point
                  if viaLEAndHitBlindPit:
                     AddFlowMarkerPoint(thisPoint, MARKER_HIT_BLIND_PIT, fieldCode, -1)
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " ends at " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n*** Please add a field observation\n")

                     # Move on to next field
                     self.refresh.emit()
                     break

                  if viaRoadAndHitStream or viaPathAndHitStream or viaLEAndHitStream:
                     AddFlowMarkerPoint(thisPoint, MARKER_ENTER_STREAM, fieldCode, -1)
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " hits a stream at " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n*** Does flow enter the stream here?\n")

                     # Move on to next field
                     self.refresh.emit()
                     break

                  if hitRoadBehaviourUnknown:
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " hits a road at " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n*** Does flow go over, under, or along this road?\n")

                     # Move on to next field
                     self.refresh.emit()
                     break

                  if hitPathBehaviourUnknown:
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " hits a path at " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n*** Does flow go over, under, or along this path?\n")

                     # Move on to next field
                     self.refresh.emit()
                     break

               else:
                  # We have found a field observation near this point, so route flow accordingly
                  rtn, adjPoint = FlowViaFieldObservation(indx, fieldCode, thisPoint, elev)
                  #shared.fpOut.write("Left FlowViaFieldObservation() called in run(), rtn = " + str(rtn) + "\n")
                  if rtn == -1:
                     # Could not determine the outflow location, so move on to the next field's flow
                     self.refresh.emit()
                     break

                  elif rtn == 1:
                     # Flow has passed through the field observation and then hit a blind pit, so we need another field observation. Set a switch and go round the loop once more, since we may have a field observation which relates to this
                     AddFlowMarkerPoint(thisPoint, MARKER_HIT_BLIND_PIT, fieldCode, -1)
                     #shared.fpOut.write("XXXX " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n")
                     viaLEAndHitBlindPit = True

                  elif rtn == 2:
                     # Flow has hit a stream, so we need another field observation. Set a switch and go round the loop once more, since we may have a field observation which relates to this
                     viaLEAndHitStream = True

                     # Reset this switch
                     viaLEAndHitBlindPit = False

                  elif rtn == 3:
                     # Merged with pre-existing flow, so move on to the next field's flow
                     self.refresh.emit()
                     break

                  elif rtn == 4:
                     # Flow has passed through the field observation and is flowing along a road
                     #shared.fpOut.write("Returned with rtn = 4 and adjPoint = " + DisplayOS(adjPoint.x(), adjPoint.y()) + " from FlowViaFieldObservation()\n")
                     viaLEAndAlongRoad = True

                     # Reset this switch
                     viaLEAndHitBlindPit = False

                  elif rtn == 5:
                     # Flow has passed through the field observation and is flowing along a path
                     #shared.fpOut.write("Setting viaLEAndAlongPath to True\n")
                     viaLEAndAlongPath = True

                     # Reset this switch
                     viaLEAndHitBlindPit = False

                  # Turn off some switches
                  if hitBoundary and shared.fieldObservationCategory[indx] == FIELD_OBS_CATEGORY_BOUNDARY:
                     # We passed through the field boundary, so turn off the switch
                     hitBoundary = False

                  if hitRoadBehaviourUnknown:
                     #shared.fpOut.write("YYY")
                     if shared.fieldObservationCategory[indx] == FIELD_OBS_CATEGORY_ROAD:
                        # We passed across or along the road, so turn off the switch
                        hitRoadBehaviourUnknown = False

                  if hitPathBehaviourUnknown:
                     #shared.fpOut.write("ZZZ")
                     if shared.fieldObservationCategory[indx] == FIELD_OBS_CATEGORY_PATH:
                        # We passed across or along the path, so turn off the switch
                        hitPathBehaviourUnknown = False

                  # We have the outflow location, so go round the inner loop once more
                  thisPoint = adjPoint
                  continue

               #==========================================================================================================
               # Search for vector roads near this point
               #==========================================================================================================
               if shared.considerRoads:
                  rtn = FindNearbyRoad(thisPoint, fieldCode, viaLEAndAlongRoad)
                  if rtn == -1:
                     # Problem! Exit the program
                     exit (-1)
                  elif rtn == 1:
                     # We have found a road, so mark it and set a switch since we don't know whether flow goes under, over or along the road
                     AddFlowMarkerPoint(thisPoint, MARKER_HIT_ROAD, fieldCode, -1)
                     hitRoadBehaviourUnknown = True

                     # Back to the start of the inner loop
                     continue

                  # No road found

               #==========================================================================================================
               # Search for vector paths/tracks near this point
               #==========================================================================================================
               if shared.considerTracks:
                  rtn = FindNearbyPath(thisPoint, fieldCode, viaLEAndAlongPath)
                  if rtn == -1:
                     # Problem! Exit the program
                     exit (-1)
                  elif rtn == 1:
                     # We have found a path or track, so mark it and set a switch since we don't know whether flow goes under, over or along the path
                     AddFlowMarkerPoint(thisPoint, MARKER_HIT_PATH, fieldCode, -1)
                     hitPathBehaviourUnknown = True

                     # Back to the start of the inner loop
                     continue

                  # No path found

               #==========================================================================================================
               # Has flow hit a field boundary?
               #==========================================================================================================
               if hitBoundary:
                  shared.fpOut.write("Flow from field " + fieldCode + " hits the boundary of field " + hitFieldCode + " at " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n*** Does flow go through or along this boundary? Please add a field observation\n")

                  # Move to next field
                  self.refresh.emit()
                  break

            #=============================================================================================================
            # End of considering-field-observations section
            #=============================================================================================================
            if inBlindPit:
               if shared.FillBlindPits:
                  #AddFlowMarkerPoint(thisPoint, MARKER_HIT_BLIND_PIT, fieldCode, -1)

                  newPoint, flowDepth = FillBlindPit(thisPoint, fieldCode)
                  if newPoint == -1:
                     # Could not find and overflow point
                     print("Flow from field " + fieldCode + ", no overflow point found from blind pit at " + DisplayOS(thisPoint.x(), thisPoint.y()))
                     shared.fpOut.write("Flow from field " + fieldCode + ", no overflow point found from blind pit at " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n")

                     # Move on to next field
                     self.refresh.emit()
                     break

                  # We have an overflow point
                  #print("For flow from field " + fieldCode + ", filled blind pit at " + DisplayOS(thisPoint.x(), thisPoint.y()) + " with flow depth " + str(flowDepth) + " m")
                  #shared.fpOut.write("For flow from field " + fieldCode + ", filled blind pit at " + DisplayOS(thisPoint.x(), thisPoint.y()) + " with flow depth " + str(flowDepth) + " m\n")

                  if flowDepth > shared.blindPitFillMaxDepth:
                     shared.blindPitFillMaxDepth = flowDepth

                  shared.blindPitFillArea += 1

                  AddFlowLine(thisPoint, newPoint, FLOW_OUT_OF_BLIND_PIT, fieldCode, -1)

                  # Back to the start of the inner loop, change thisPoint
                  inBlindPit = False
                  thisPoint = newPoint

                  continue

               else:
                  AddFlowMarkerPoint(thisPoint, MARKER_HIT_BLIND_PIT, fieldCode, -1)

                  shared.fpOut.write("Flow from field " + fieldCode + " hits a blind pit at " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n")

                  if shared.considerLEFlowInteractions:
                     shared.fpOut.write("*** Please add a field observation\n")

                  # Move on to next field
                  self.refresh.emit()
                  break

            #=============================================================================================================
            # Route flow down the steepest slope
            #=============================================================================================================
            # Get this cell's elevation
            elev = GetRasterElev(thisPoint.x(), thisPoint.y())

            # Search for the adjacent raster cell with the steepest here-to-there slope, and get its centroid
            adjPoint, _adjElev = FindSteepestAdjacent(thisPoint, elev)
            #shared.fpOut.write("Steepest adjacent is " + DisplayOS(adjPoint.x(), adjPoint.y()) + "\n")

            # Is this adjacent point in a blind pit?
            if adjPoint.x() == -1:
               # Yes, we are in a blind pit, so set the switch
               inBlindPit = True

               # Back to the start of the inner loop, keep thisPoint unchanged
               continue

            if shared.considerLEFlowInteractions:
               # If we are considering LE-flow interactions: is there a field boundary between this point and the adjacent point?
               hitBoundary, hitPoint, hitFieldCode = FlowHitFieldBoundary(thisPoint, adjPoint, fieldCode)
               if hitBoundary:
                  # Yes, flow hits a field boundary, we have set a switch
                  shared.fpOut.write("Flow from field " + str(fieldCode) + " hits a field boundary at " + DisplayOS(hitPoint.x(), hitPoint.y()) + ", this is between vertices at " + DisplayOS(thisPoint.x(), thisPoint.y()) + " and " + DisplayOS(adjPoint.x(), adjPoint.y()) + "\n")

                  AddFlowLine(thisPoint, hitPoint, FLOW_TO_FIELD_BOUNDARY, fieldCode, -1)
                  thisPoint = hitPoint

                  # Back to the start of the inner loop
                  continue

            # No field boundary, or we are just considering topography-driven flow: so store the adjacent point and add a flow line to it
            AddFlowLine(thisPoint, adjPoint, FLOW_DOWN_STEEPEST, fieldCode, elev)

            # Update thisPoint ready for the next time round the inner loop
            thisPoint = adjPoint
            continue

      #===================================================================================================================
      # End of main and inner loops
      #===================================================================================================================

      # Deal with the last field simulated
      for feature in shared.outFlowLineLayer.getFeatures():
         shared.outFlowLineLayerIndex.insertFeature(feature)

      # If we are considering LE-flow interactions, and flow for the last field travelled via at least one field observation, then save the last field's list of LE-flow interactions
      if shared.considerLEFlowInteractions and shared.thisFieldFieldObsAlreadyFollowed:
         shared.allFieldsFieldObsAlreadyFollowed.extend(shared.thisFieldFieldObsAlreadyFollowed)

      # Simulation finished, so update the extents of the vector output files
      shared.outFlowMarkerPointLayer.updateExtents()
      shared.outFlowLineLayer.updateExtents()

      # If we've filled blind pits, show max flow depth to fill any pit
      if shared.FillBlindPits:
         shared.fpOut.write("\n" + shared.dividerLen * shared.dividerChar + "\n\n")
         shared.fpOut.write("Area of filled blind pits = " + "{:0.1f}".format(shared.blindPitFillArea * shared.resolutionOfDEM * shared.resolutionOfDEM) + " m2\n")
         shared.fpOut.write("Maximum flow depth to fill any blind pit = " + "{:0.3f}".format(shared.blindPitFillMaxDepth) + " m\n")

      # If we are considering LE-flow interactions, are they any still unused?
      if shared.considerLEFlowInteractions:
         shared.fpOut.write("\n" + shared.dividerLen * shared.dividerChar + "\n\n")
         shared.fpOut.write("UNUSED FIELD OBSERVATIONS\n\n")

         for obs in range(len(shared.LEFlowInteractionFlowFrom)):
            if not obs in shared.allFieldsFieldObsAlreadyFollowed:
               printStr = str(obs+1) + ": '" + shared.fieldObservationCategory[obs] + "' '" + shared.fieldObservationBehaviour[obs] + "' '" + shared.fieldObservationDescription[obs] + "' from " + DisplayOS(shared.LEFlowInteractionFlowFrom[obs].x(), shared.LEFlowInteractionFlowFrom[obs].y(), False)

               if shared.LEFlowInteractionFlowTo[obs]:
                  printStr += (" to " + DisplayOS(shared.LEFlowInteractionFlowTo[obs].x(), shared.LEFlowInteractionFlowTo[obs].y(), False))

               printStr += "\n"
               shared.fpOut.write(printStr)

      # Finally, write the results to shapefiles
      shared.fpOut.write("\n" + shared.dividerLen * shared.dividerChar + "\n\n")
      shared.fpOut.write("SAVING GIS FILES\n\n")

      WriteVector(shared.outFlowMarkerPointLayer, shared.outFileFlowMarkerPoints + ".shp", shared.externalCRS)
      WriteVector(shared.outFlowLineLayer, shared.outFileFlowLines + ".shp", shared.externalCRS)

      shared.fpOut.write("\n" + shared.dividerLen * shared.dividerChar + "\n\n")

      printStr = "Simulation finished"
      shared.fpOut.write(printStr + "\n")
      print(printStr)

      shared.fpOut.close()

      self.refresh.emit()
      self.runDone.emit()

      return
   #======================================================================================================================
