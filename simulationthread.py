from __future__ import print_function

from PyQt4.QtCore import QThread, pyqtSignal

from qgis.core import QgsPoint, QgsFeatureRequest

import shared
from shared import INPUT_FIELD_BOUNDARIES, CONNECTED_FIELD_ID, INPUT_RASTER_BACKGROUND, MARKER_FLOW_START_POINT, MERGED_WITH_ADJACENT_FLOWLINE, FLOW_ADJUSTMENT_DUMMY, MARKER_BLIND_PIT, MARKER_AT_STREAM, FIELD_OBS_CATEGORY_BOUNDARY, FIELD_OBS_CATEGORY_ROAD, FIELD_OBS_CATEGORY_PATH, MARKER_ROAD, MARKER_PATH, FLOW_OUT_OF_BLIND_PIT, FLOW_TO_FIELD_BOUNDARY, FLOW_DOWN_STEEPEST
from layers import AddFlowMarkerPoint, AddFlowLine, WriteVector
from simulate import GetHighestPointOnFieldBoundary, FlowViaFieldObservation, FlowHitFieldBoundary, FillBlindPit, FlowAlongVectorRoad, FlowAlongVectorPath
from searches import FindNearbyStream, FindNearbyFlowLine, FindNearbyFieldObservation, FindNearbyRoad, FindNearbyPath, FindSteepestAdjacent
from utils import GetRasterElev, GetCentroidOfContainingDEMCell, DisplayOS


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
      if shared.fieldsWithFlow:
         doAllFields = False

      #===================================================================================================================
      # OK, off we go. First determine the flow start points
      #===================================================================================================================
      #shared.fpOut.write("\n" + shared.dividerLen * shared.dividerChar + "\n\n")
      #shared.fpOut.write("FLOW START POINTS\n\n")

      fieldCodes = []
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
               #shared.fpOut.write(str(fieldCode) + "\n")

               # Is the centroid of this field within the coverage of one of the raster landscape element files which we have read in? TODO change to vector extent
               isWithin = False
               centroidPoint = fieldBoundary.geometry().centroid().asPoint()
               for n in range(len(shared.rasterInputLayersCategory)):
                  if shared.rasterInputLayersCategory[n] == INPUT_RASTER_BACKGROUND:
                     if shared.extentRect.contains(centroidPoint):
                        isWithin = True
                        break

               if not isWithin:
                  continue

               # Ignore duplicate fields
               if fieldCode not in fieldCodes:
                  #shared.fpOut.write(str(fieldCode) + "\n")

                  # Get the coords of the centroid of the pixel which contains the highest point on the boundary of this field (including in-between points), and also the elevation of this point
                  xBoundary, yBoundary, _boundaryElev = GetHighestPointOnFieldBoundary(fieldBoundary)

                  # Is it valid?
                  if (xBoundary == -1) and (yBoundary == -1):
                     # No
                     continue

                  # Is valid, so show on the map
                  #AddFlowMarkerPoint(QgsPoint(xBoundary, yBoundary), MARKER_HIGHEST_POINT, fieldCode, boundaryElev)

                  # Calculate the start-of-flow location only for fields which generate runoff
                  if not doAllFields and fieldCode not in shared.fieldsWithFlow:
                     continue

                  # OK, get the elevation of the field's centroid
                  xCentroid = centroidPoint.x()
                  yCentroid = centroidPoint.y()
                  #centroidElev = GetRasterElev(xCentroid, yCentroid)

                  # Show the centroid on the map
                  #AddFlowMarkerPoint(centroidPoint, MARKER_CENTROID, fieldCode, centroidElev)

                  # Calculate the flow start point for this field, as a weighted average of the highest boundary point and the centroid point
                  weightCentroid = 1 - shared.weightBoundary
                  xFlowStart = (xBoundary * shared.weightBoundary) + (xCentroid * weightCentroid)
                  yFlowStart = (yBoundary * shared.weightBoundary) + (yCentroid * weightCentroid)

                  flowStartElev = GetRasterElev(xFlowStart, yFlowStart)

                  # Save the flow start point for this field
                  shared.flowStartPoints.append([xFlowStart, yFlowStart, flowStartElev, fieldCode])
                  fieldCodes.append(fieldCode)

                  # And show it on the map
                  AddFlowMarkerPoint(QgsPoint(xFlowStart, yFlowStart), fieldCode + MARKER_FLOW_START_POINT, fieldCode, flowStartElev)
                  #shared.fpOut.write("Flow from field " + fieldCode + " begins at " + DisplayOS(xFlowStart, yFlowStart) + "\n")

                  # Refresh the display
                  self.refresh.emit()

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
            if fieldCode not in shared.fieldsWithFlow:
               # Nope
               continue

         # If this isn't the first field simulated, then save the last field's flow path and the last field's list of Field Observations used
         if shared.thisFieldFlowLine:
            shared.allFieldsFlowPath.extend(shared.thisFieldFlowLine)
            shared.allFieldsFlowPathFieldCode.extend(shared.thisFieldFlowLineFieldCode)

            for feature in shared.outFlowLineLayer.getFeatures():
               shared.outFlowLineLayerIndex.insertFeature(feature)

         # If we are considering field observations, and flow for the last field travelled via at least one field observation, then save the last field's list of field observations
         if shared.considerFieldObservations and shared.thisFieldFieldObsAlreadyFollowed:
            shared.allFieldsFieldObsAlreadyFollowed.extend(shared.thisFieldFieldObsAlreadyFollowed)

         # OK, do some initialization
         shared.thisFieldFlowLine = []
         shared.thisFieldFlowLineFieldCode = []
         shared.thisFieldRoadSegIDsTried = []
         shared.thisFieldPathSegIDsTried = []
         shared.thisFieldBoundarySegIDsTried = []
         shared.thisFieldFieldObsAlreadyFollowed = []

         x = shared.flowStartPoints[field][0]
         y = shared.flowStartPoints[field][1]
         thisPoint = QgsPoint(x, y)
         elev = shared.flowStartPoints[field][2]
         fieldCode = shared.flowStartPoints[field][3]

         viaLEAndHitBlindPit = False
         viaLEAndHitStream = False
         viaLEAndAlongRoad = False
         viaLEAndAlongPath = False
         viaRoadAndHitStream = False
         viaPathAndHitStream = False

         shared.fpOut.write("\n" + shared.dividerLen * shared.dividerChar + "\n\n")
         shared.fpOut.write("SIMULATED FLOW FROM FIELD " + str(fieldCode) + "\n\n")
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

            #print("thisPoint = " + DisplayOS(thisPoint.x(), thisPoint.y()))

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
               AddFlowLine(thisPoint, QgsPoint(adjX, adjY), MERGED_WITH_ADJACENT_FLOWLINE, fieldCode, elev)
               shared.fpOut.write("Flow from field " + fieldCode + " hit flow from field " + str(hitFieldFlowFrom) + " at " + DisplayOS(adjX, adjY) + ", so stopped tracing flow from this field\n")

               # Move on to the next field
               self.refresh.emit()
               break

            #=============================================================================================================
            # Flow did not merge with a pre-existing flowline. Make sure that this point is at the centroid of a DEM cell
            #=============================================================================================================
            tempPoint = GetCentroidOfContainingDEMCell(thisPoint.x(), thisPoint.y())
            if not (inBlindPit or viaLEAndHitBlindPit or viaLEAndHitStream) and tempPoint != thisPoint:
               # We had to shift the location slightly, so show a connecting line
               AddFlowLine(thisPoint, tempPoint, FLOW_ADJUSTMENT_DUMMY, fieldCode, -1)
               thisPoint = tempPoint

            #=============================================================================================================
            #  OK, we are now considering field observations
            #=============================================================================================================
            if shared.considerFieldObservations:
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
                     AddFlowMarkerPoint(thisPoint, MARKER_ROAD, fieldCode, -1)

                     # And try to flow along this road
                     rtn, point = FlowAlongVectorRoad(-1, fieldCode, thisPoint)
                     shared.fpOut.write("\tFinished flow along road at " + DisplayOS(point.x(), point.y()) + " with rtn = " + str(rtn) + "\n")
                     if rtn == -1:
                        # A problem! Exit the program
                        exit (-1)

                     elif rtn == 1:
                        # Flow has hit a blind pit
                        shared.fpOut.write("Flow from field " + str(fieldCode) + " hit a blind pit at " + DisplayOS(thisPoint.x(), thisPoint.y()) + " while flowing along a road\n*** Please add a field observation\n")

                        # Move on to next field
                        self.refresh.emit()
                        break

                     elif rtn == 2:
                        # Flow has hit a stream, so carry on and look for a field observation
                        viaRoadAndHitStream = True
                        viaLEAndAlongRoad = False
                        #shared.fpOut.write("viaRoadAndHitStream = True\n")
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
                  # Was flowing along a path/track but reached the beginning or end of that path/track, so search for another nearby path/track
                  #==========================================================================================================
                  rtn = FindNearbyPath(thisPoint, fieldCode, viaLEAndAlongPath)
                  if rtn == -1:
                     # Problem! Exit the program
                     exit (-1)
                  elif rtn == 1:
                     # We have found a path, so mark it
                     AddFlowMarkerPoint(thisPoint, MARKER_PATH, fieldCode, -1)

                     # And try to flow along this path
                     rtn, point = FlowAlongVectorPath(-1, fieldCode, thisPoint)
                     shared.fpOut.write("\tFinished flow along path/track at " + DisplayOS(point.x(), point.y()) + " with rtn = " + str(rtn) + "\n")
                     if rtn == -1:
                        # A problem! Exit the program
                        exit (-1)

                     elif rtn == 1:
                        # Flow has hit a blind pit
                        shared.fpOut.write("Flow from field " + str(fieldCode) + " hit a blind pit at " + DisplayOS(thisPoint.x(), thisPoint.y()) + " while flowing along a path/track\n*** Please add a field observation\n")

                        # Move on to next field
                        self.refresh.emit()
                        break

                     elif rtn == 2:
                        # Flow has hit a stream, so carry on and look for a field observation
                        viaPathAndHitStream = True
                        viaLEAndAlongPath = False
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
               # Search for a field observation of a landscape element near this point
               #==========================================================================================================
               #shared.fpOut.write("Searching for field observations for flow from field " + str(fieldCode) + " near " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n")
               indx = FindNearbyFieldObservation(thisPoint)
               if indx == -1:
                  # Did not find a field observation near this point
                  if viaLEAndHitBlindPit:
                     AddFlowMarkerPoint(thisPoint, MARKER_BLIND_PIT, fieldCode, -1)
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " ends at " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n*** Please add a field observation\n")

                     # Move on to next field
                     self.refresh.emit()
                     break

                  if viaRoadAndHitStream or viaPathAndHitStream or viaLEAndHitStream:
                     AddFlowMarkerPoint(thisPoint, MARKER_AT_STREAM, fieldCode, -1)
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " hits a stream at " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n*** Does flow enter the stream here?\n")

                     # Move on to next field
                     self.refresh.emit()
                     break

                  if hitRoadBehaviourUnknown or hitPathBehaviourUnknown:
                     # Move on to next field
                     self.refresh.emit()
                     break

               else:
                  # We have found a field observation near this point, so route flow accordingly
                  rtn, adjPoint = FlowViaFieldObservation(indx, fieldCode, thisPoint, elev)
                  shared.fpOut.write("Left FlowViaFieldObservation() called in run(), rtn = " + str(rtn) + "\n")
                  if rtn == -1:
                     # Could not determine the outflow location, so move on to the next field's flow
                     self.refresh.emit()
                     break

                  elif rtn == 1:
                     # Flow has passed through the field observation and then hit a blind pit, so we need another field observation. Set a switch and go round the loop once more, since we may have a field observation which relates to this
                     #AddFlowMarkerPoint(thisPoint, MARKER_BLIND_PIT, fieldCode, -1)
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
                     #shared.fpOut.write("Setting viaLEAndAlongRoad to True\n")
                     viaLEAndAlongRoad = True

                     # Reset this switch
                     viaLEAndHitBlindPit = False

                  elif rtn == 5:
                     # Flow has passed through the field observation and is flowing along a path/track
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
                     AddFlowMarkerPoint(thisPoint, MARKER_ROAD, fieldCode, -1)
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
                     AddFlowMarkerPoint(thisPoint, MARKER_PATH, fieldCode, -1)
                     hitPathBehaviourUnknown = True

                     # Back to the start of the inner loop
                     continue

                  # No path/track found

               #==========================================================================================================
               # Has flow hit a field boundary?
               #==========================================================================================================
               if hitBoundary:
                  shared.fpOut.write("Flow from field " + fieldCode + " hits the boundary of field " + hitFieldCode + " at " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n*** Does flow go through this boundary? Please add a field observation\n")

                  # Move to next field
                  self.refresh.emit()
                  break

            #=============================================================================================================
            # End of considering-field-observations section
            #=============================================================================================================
            if inBlindPit:
               if shared.FillBlindPits:
                  AddFlowMarkerPoint(thisPoint, MARKER_BLIND_PIT, fieldCode, -1)

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
                  AddFlowMarkerPoint(thisPoint, MARKER_BLIND_PIT, fieldCode, -1)

                  shared.fpOut.write("Flow from field " + fieldCode + " hits a blind pit at " + DisplayOS(thisPoint.x(), thisPoint.y()) + "\n")

                  if shared.considerFieldObservations:
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

            if shared.considerFieldObservations:
               # If we are considering field observations: is there a field boundary between this point and the adjacent point?
               hitBoundary, hitPoint, hitFieldCode = FlowHitFieldBoundary(thisPoint, adjPoint, fieldCode)
               if hitBoundary:
                  # Yes, flow hits a field boundary, we have set a switch
                  shared.fpOut.write("Hit boundary at " + DisplayOS(hitPoint.x(), hitPoint.y()) + " which is between " + DisplayOS(thisPoint.x(), thisPoint.y()) + " and " + DisplayOS(adjPoint.x(), adjPoint.y()) + "\n")

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

      # If we are considering field observations, and flow for the last field travelled via at least one field observation, then save the last field's list of field observations
      if shared.considerFieldObservations and shared.thisFieldFieldObsAlreadyFollowed:
         shared.allFieldsFieldObsAlreadyFollowed.extend(shared.thisFieldFieldObsAlreadyFollowed)

      # Simulation finished, so update the extents of the vector output files
      shared.outFlowMarkerPointLayer.updateExtents()
      shared.outFlowLineLayer.updateExtents()

      # If we've filled blind pits, show max flow depth to fill any pit
      if shared.FillBlindPits:
         shared.fpOut.write("\n" + shared.dividerLen * shared.dividerChar + "\n\n")
         shared.fpOut.write("Area of filled blind pits = " + str(shared.blindPitFillArea * shared.resolutionOfDEM * shared.resolutionOfDEM) + " m2\n")
         shared.fpOut.write("Maximum flow depth to fill any blind pit = " + str(shared.blindPitFillMaxDepth) + " m\n")

      # If we are considering field observations, are they any still unused?
      if shared.considerFieldObservations:
         shared.fpOut.write("\n" + shared.dividerLen * shared.dividerChar + "\n\n")
         shared.fpOut.write("UNUSED FIELD OBSERVATIONS\n\n")

         for i in range(len(shared.fieldObservationFlowFrom)):
            if not i in shared.allFieldsFieldObsAlreadyFollowed:
               printStr = str(i+1) + " " + shared.fieldObservationBehaviour[i] + " " + shared.fieldObservationCategory[i] + " " + shared.fieldObservationDescription[i] + " from " + DisplayOS(shared.fieldObservationFlowFrom[i].x(), shared.fieldObservationFlowFrom[i].y())
               if shared.fieldObservationFlowTo[i]:
                  printStr += " to "
                  printStr += DisplayOS(shared.fieldObservationFlowTo[i].x(), shared.fieldObservationFlowTo[i].y())
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
