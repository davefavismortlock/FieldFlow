from PyQt4.QtCore import QThread, pyqtSignal

from qgis.core import QgsPoint, QgsFeatureRequest

import shared
from shared import *
from layers import addFlowMarkerPoint, addFlowLine, writeVector
from simulate import getHighestPointOnFieldBoundary, flowViaLandscapeElement, flowHitFieldBoundary, fillBlindPit
from searches import FindNearbyStream, FindNearbyFlowLine, FindNearbyFieldObservation, FindNearbyRoad, FindNearbyPath, FindSteepestAdjacent
from utils import getRasterElev, centroidOfContainingDEMCell, displayOS


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
      shared.flowStartPoints = []
      
      doAllFields = True
      if len(shared.fieldsWithFlow) > 0:
         doAllFields = False
         
      #===================================================================================================================
      # OK, off we go. First determine the flow start points
      #===================================================================================================================
      shared.fpOut.write("\n" + shared.dividerLen * shared.dividerChar + "\n\n")   
      shared.fpOut.write("FLOW START POINTS\n\n")

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
                  xBoundary, yBoundary, boundaryElev = getHighestPointOnFieldBoundary(fieldBoundary)
                  
                  # Is it valid?
                  if (xBoundary == -1) and (yBoundary == -1):
                     # No
                     continue
                  
                  # Is valid, so show on the map
                  #addFlowMarkerPoint(QgsPoint(xBoundary, yBoundary), MARKER_HIGHEST_POINT, fieldCode, boundaryElev)
                  
                  # Calculate the start-of-flow location only for fields which generate runoff              
                  if not doAllFields and fieldCode not in shared.fieldsWithFlow:
                     continue                     
                  
                  # OK, get the elevation of the field's centroid
                  xCentroid = centroidPoint.x()
                  yCentroid = centroidPoint.y()
                  centroidElev = getRasterElev(xCentroid, yCentroid)
                  
                  # Show the centroid on the map
                  #addFlowMarkerPoint(centroidPoint, MARKER_CENTROID, fieldCode, centroidElev)
               
                  # Calculate the flow start point for this field, as a weighted average of the highest boundary point and the centroid point
                  weightCentroid = 1 - shared.weightBoundary
                  xFlowStart = (xBoundary * shared.weightBoundary) + (xCentroid * weightCentroid)
                  yFlowStart = (yBoundary * shared.weightBoundary) + (yCentroid * weightCentroid)
                  
                  flowStartElev = getRasterElev(xFlowStart, yFlowStart)
                  
                  # Save the flow start point for this field
                  shared.flowStartPoints.append([xFlowStart, yFlowStart, flowStartElev, fieldCode])
                  fieldCodes.append(fieldCode)
                  
                  # And show it on the map
                  addFlowMarkerPoint(QgsPoint(xFlowStart, yFlowStart), fieldCode + MARKER_FLOW_START_POINT, fieldCode, flowStartElev)
                  shared.fpOut.write("Flow from field " + fieldCode + " begins at " + displayOS(xFlowStart, yFlowStart) + "\n")

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
         if len(shared.thisFieldFlowLine) > 0:
            shared.allFieldsFlowPath.extend(shared.thisFieldFlowLine)
            shared.allFieldsFlowPathFieldCode.extend(shared.thisFieldFlowLineFieldCode)
            
            for feature in shared.outFlowLineLayer.getFeatures():
               shared.outFlowLineLayerIndex.insertFeature(feature)
         
         # If we are considering field observations, and flow for the last field travelled via at least one field observation, then save the last field's list of field observations
         if shared.considerFieldObservations and len(shared.thisFieldFieldObsAlreadyFollowed) > 0:
            shared.allFieldsFieldObsAlreadyFollowed.extend(shared.thisFieldFieldObsAlreadyFollowed)         
            
         # OK, do some initialization
         shared.thisFieldFlowLine = []
         shared.thisFieldFlowLineFieldCode = []
         shared.thisFieldRoadSegIDsTried = []
         shared.thisFieldPathSegIDsTried = []
         thisFieldBoundarySegIDsTried = []
         shared.thisFieldFieldObsAlreadyFollowed = []
            
         x = shared.flowStartPoints[field][0]
         y = shared.flowStartPoints[field][1]
         thisPoint = QgsPoint(x, y)
         elev = shared.flowStartPoints[field][2]
         fieldCode = shared.flowStartPoints[field][3]
         
         viaLEAndHitBlindPit = False
         viaLEAndHitStream = False
         
         shared.fpOut.write("\n" + shared.dividerLen * shared.dividerChar + "\n\n")
         shared.fpOut.write("SIMULATING FLOW FROM FIELD " + str(fieldCode) + "\n\n")
         shared.fpOut.write("Flow from field " + str(fieldCode) + " starts at " + displayOS(x, y) + "\n")
         shared.thisStartPoint += 1

         nStepsAfterStart = 0
         
         inBlindPit = False
         hitBoundary = False
         hitRoad = False
         hitPath = False
         
         hitFieldCode = -1
         
         #================================================================================================================
         # The inner loop, keep going round this until flow from this field reaches the river, or can go no further
         #================================================================================================================
         while True:
            # Refresh the display
            self.refresh.emit()   
            
            #print("thisPoint = " + displayOS(thisPoint.x(), thisPoint.y()))
            
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
               self.refresh.emit()               
               break
            
            #=============================================================================================================
            # Flow did not enter a stream, so next search for nearby pre-existing flowlines
            #=============================================================================================================
            adjX, adjY = FindNearbyFlowLine(thisPoint)
            if adjX != -1:
               # There is an adjacent flow line, so merge the two and finish with this flow line
               indx = shared.allFieldsFlowPath.index(QgsPoint(adjX, adjY))
               hitFieldFlowFrom = shared.allFieldsFlowPathFieldCode[indx]
               
               addFlowLine(thisPoint, QgsPoint(adjX, adjY), MERGED_WITH_ADJACENT_FLOWLINE, fieldCode, elev)
               shared.fpOut.write("Flow from field " + fieldCode + " hit flow from field " + str(hitFieldFlowFrom) + " at " + displayOS(adjPoint.x(), adjPoint.y(), False) + ", so stopped tracing flow from this field\n")
                  
               # Move on to the next field
               self.refresh.emit()                
               break
            
            #=============================================================================================================
            # Flow did not merge with a pre-existing flowline. Make sure that this point is at the centroid of a DEM cell
            #=============================================================================================================
            tempPoint = centroidOfContainingDEMCell(thisPoint.x(), thisPoint.y())
            if not (inBlindPit or viaLEAndHitBlindPit or viaLEAndHitStream) and tempPoint != thisPoint:
               # We had to shift the location slightly, so show a connecting line
               addFlowLine(thisPoint, tempPoint, FLOW_ADJUSTMENT_DUMMY, fieldCode, -1)
               thisPoint = tempPoint            
               
            #=============================================================================================================
            #  OK, we are now considering field observations
            #=============================================================================================================
            if shared.considerFieldObservations: 
               #==========================================================================================================
               # Search for a field observation of a landscape element near this point
               #==========================================================================================================
               #shared.fpOut.write("Searching for field observations for flow from field " + str(fieldCode) + " near " + displayOS(thisPoint.x(), thisPoint.y()) + "\n")
               indx = FindNearbyFieldObservation(thisPoint)
               if indx == -1:
                  # Did not find a field observation near this point
                  if viaLEAndHitBlindPit:
                     addFlowMarkerPoint(thisPoint, MARKER_BLIND_PIT, fieldCode, -1)
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " ends at " + displayOS(thisPoint.x(), thisPoint.y()) + "\n*** Please add a field observation\n")
                     
                     # Move on to next field
                     self.refresh.emit() 
                     break
                  
                  if viaLEAndHitStream:                                          
                     addFlowMarkerPoint(thisPoint, MARKER_AT_STREAM, fieldCode, -1)
                     shared.fpOut.write("Flow from field " + str(fieldCode) + " hits a stream at " + displayOS(thisPoint.x(), thisPoint.y()) + + "\n*** Does flow enter the stream here?\n")
                     
                     # Move on to next field
                     self.refresh.emit() 
                     break         
                  
                  if hitRoad or hitPath:
                     # Move on to next field
                     self.refresh.emit() 
                     break 
               
               else:
                  # We have found a field observation near this point, so route flow accordingly
                  rtn, adjPoint = flowViaLandscapeElement(indx, fieldCode, thisPoint, elev)
                  if rtn == -1:
                     # Could not determine the outflow location, so move on to the next field's flow
                     self.refresh.emit() 
                     break
                  
                  elif rtn == 1:
                     # Flow has passed through the LE and then hit a blind pit, so we need another field observation. Set a switch and go round the loop once more, since we may have a field observation which relates to this
                     addFlowMarkerPoint(thisPoint, MARKER_BLIND_PIT, fieldCode, -1)
                     viaLEAndHitBlindPit = True                     
                  
                  elif rtn == 2:
                     # Flow has hit a stream, so we need another field observation. Set a switch and go round the loop once more, since we may have a field observation which relates to this
                     viaLEAndHitStream = True                     
                  
                  elif rtn == 3:
                     # Merged with pre-existing flow, so move on to the next field's flow
                     self.refresh.emit() 
                     break
                     
                  # Turn off some switches
                  if hitBoundary and shared.fieldObservationCategory[indx] == FIELD_OBS_CATEGORY_BOUNDARY:
                     # We passed through the field boundary, so turn off the switch
                     hitBoundary = False
                  
                  if hitRoad:
                     #shared.fpOut.write("YYY")
                     if shared.fieldObservationCategory[indx] == FIELD_OBS_CATEGORY_ROAD:
                        # We passed across or along the road, so turn off the switch
                        hitRoad = False

                  if hitPath:
                     #shared.fpOut.write("ZZZ")
                     if shared.fieldObservationCategory[indx] == FIELD_OBS_CATEGORY_PATH:
                        # We passed across or along the path, so turn off the switch
                        hitPath = False

                  # We have the outflow location, so go round the inner loop once more
                  thisPoint = adjPoint                  
                  continue
               
               #==========================================================================================================
               # Search for vector roads near this point
               #==========================================================================================================
               if shared.considerRoads:
                  rtn = FindNearbyRoad(thisPoint, fieldCode)
                  if rtn == -1:
                     # Problem! Exit the program
                     exit (-1)
                  elif rtn == 1:
                     # We have found a road, so mark it and set a switch since we don't know whether flow goes under, over or along the road
                     addFlowMarkerPoint(thisPoint, MARKER_ROAD, fieldCode, -1)
                     hitRoad = True
                     
                     # Back to the start of the inner loop
                     #shared.fpOut.write("XXX\n")
                     continue
                     
                  # No road found
               
               #==========================================================================================================
               # Search for raster paths/tracks near this point        
               #==========================================================================================================
               if shared.considerTracks:
                  rtn = FindNearbyPath(thisPoint, fieldCode)
                  if rtn == -1:
                     # Problem! Exit the program
                     exit (-1)
                  elif rtn == 1:
                     # We have found a path or track, so mark it and set a switch since we don't know whether flow goes under, over or along the path
                     addFlowMarkerPoint(thisPoint, MARKER_PATH, fieldCode, -1)
                     hitPath = True
                     
                     # Back to the start of the inner loop
                     #shared.fpOut.write("AAA\n")
                     continue
                     
                  # No path found


               if hitBoundary:
                  shared.fpOut.write("Flow from field " + fieldCode + " hits the boundary of field " + hitFieldCode + " at " + displayOS(thisPoint.x(), thisPoint.y()) + "\n*** Does flow go through this boundary? Please add a field observation\n")  
                        
                  # Move to next field
                  self.refresh.emit() 
                  break               
            
            #=============================================================================================================
            # End of considering-field-observations section
            #=============================================================================================================                        
            if inBlindPit:
               if shared.fillBlindPits:
                  addFlowMarkerPoint(thisPoint, MARKER_BLIND_PIT, fieldCode, -1)
                  
                  newPoint, flowDepth = fillBlindPit(thisPoint, fieldCode)
                  if newPoint == -1:
                     # Could not find and overflow point
                     print("Flow from field " + fieldCode + ", no overflow point found from blind pit at " + displayOS(thisPoint.x(), thisPoint.y()))
                     shared.fpOut.write("Flow from field " + fieldCode + ", no overflow point found from blind pit at " + displayOS(thisPoint.x(), thisPoint.y()) + "\n")

                     # Move on to next field
                     self.refresh.emit() 
                     break
                     
                  # We have an overflow point
                  #print("For flow from field " + fieldCode + ", filled blind pit at " + displayOS(thisPoint.x(), thisPoint.y()) + " with flow depth " + str(flowDepth) + " m")
                  #shared.fpOut.write("For flow from field " + fieldCode + ", filled blind pit at " + displayOS(thisPoint.x(), thisPoint.y()) + " with flow depth " + str(flowDepth) + " m\n")
                  
                  if flowDepth > shared.blindPitFillMaxDepth:
                     shared.blindPitFillMaxDepth = flowDepth
                  
                  shared.blindPitFillArea += 1
                  
                  addFlowLine(thisPoint, newPoint, FLOW_OUT_OF_BLIND_PIT, fieldCode, -1)
                  
                  # Back to the start of the inner loop, change thisPoint
                  inBlindPit = False
                  thisPoint = newPoint
                  
                  continue
               
               else:               
                  addFlowMarkerPoint(thisPoint, MARKER_BLIND_PIT, fieldCode, -1)

                  shared.fpOut.write("Flow from field " + fieldCode + " hits a blind pit at " + displayOS(thisPoint.x(), thisPoint.y()) + "\n") 
                  
                  if shared.considerFieldObservations:
                     shared.fpOut.write("*** Please add a field observation\n")
               
                  # Move on to next field
                  self.refresh.emit() 
                  break
            
            #=============================================================================================================
            # Route flow down the steepest slope
            #=============================================================================================================
            # Get this cell's elevation
            elev = getRasterElev(thisPoint.x(), thisPoint.y())
            
            # Search for the adjacent raster cell with the steepest here-to-there slope, and get its centroid
            adjPoint, adjElev = FindSteepestAdjacent(thisPoint, elev)
            #shared.fpOut.write("Steepest adjacent is " + displayOS(adjPoint.x(), adjPoint.y()) + "\n")
            
            # Is this adjacent point in a blind pit?
            if adjPoint.x() == -1:
               # Yes, we are in a blind pit, so set the switch
               inBlindPit = True
               
               # Back to the start of the inner loop, keep thisPoint unchanged
               continue
               
            if shared.considerFieldObservations:
               # If we are considering field observations: is there a field boundary between this point and the adjacent point?
               hitBoundary, hitPoint, hitFieldCode = flowHitFieldBoundary(thisPoint, adjPoint, fieldCode)
               if hitBoundary:
                  # Yes, flow hits a field boundary, we have set a switch
                  addFlowLine(thisPoint, hitPoint, FLOW_TO_FIELD_BOUNDARY, fieldCode, -1)
                  thisPoint = hitPoint
                  
                  # Back to the start of the inner loop
                  continue               
               
            # No field boundary, or we are just considering topography-driven flow: so store the adjacent point and add a flow line to it
            addFlowLine(thisPoint, adjPoint, FLOW_DOWN_STEEPEST, fieldCode, elev)
            
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
      if shared.considerFieldObservations and len(shared.thisFieldFieldObsAlreadyFollowed) > 0:
         shared.allFieldsFieldObsAlreadyFollowed.extend(shared.thisFieldFieldObsAlreadyFollowed)   
      
      # Simulation finished, so update the extents of the vector output files
      shared.outFlowMarkerPointLayer.updateExtents()
      shared.outFlowLineLayer.updateExtents()
      
      # If we've filled blind pits, show max flow depth to fill any pit
      if shared.fillBlindPits:
         shared.fpOut.write("\n" + shared.dividerLen * shared.dividerChar + "\n\n")
         shared.fpOut.write("Area of filled blind pits = " + str(shared.blindPitFillArea * shared.resolutionOfDEM * shared.resolutionOfDEM) + " m2\n")
         shared.fpOut.write("Maximum flow depth to fill any blind pit = " + str(shared.blindPitFillMaxDepth) + " m\n")
      
      # If we are considering field observations, are they any still unused?
      if shared.considerFieldObservations:
         shared.fpOut.write("\n" + shared.dividerLen * shared.dividerChar + "\n\n")
         shared.fpOut.write("UNUSED FIELD OBSERVATIONS\n\n")
         
         for i in range(len(shared.fieldObservationFlowFrom)):
            if not i in shared.allFieldsFieldObsAlreadyFollowed:
               printStr = str(i+1) + " " + shared.fieldObservationBehaviour[i] + " " + shared.fieldObservationCategory[i] + " " + shared.fieldObservationDescription[i] + " from " + displayOS(shared.fieldObservationFlowFrom[i].x(), shared.fieldObservationFlowFrom[i].y())
               if shared.fieldObservationFlowTo[i]:
                  printStr += " to "
                  printStr += displayOS(shared.fieldObservationFlowTo[i].x(), shared.fieldObservationFlowTo[i].y())
               printStr += "\n"
               shared.fpOut.write(printStr)
      
      # Finally, write the results to shapefiles
      shared.fpOut.write("\n" + shared.dividerLen * shared.dividerChar + "\n\n")
      shared.fpOut.write("SAVING GIS FILES\n\n")

      writeVector(shared.outFlowMarkerPointLayer, shared.outFileFlowMarkerPoints + ".shp", shared.externalCRS)
      writeVector(shared.outFlowLineLayer, shared.outFileFlowLines + ".shp", shared.externalCRS)
      
      shared.fpOut.write("\n" + shared.dividerLen * shared.dividerChar + "\n\n")

      printStr = "Simulation finished\n"
      shared.fpOut.write(printStr)
      
      print(printStr)
      
      shared.fpOut.close()
      
      self.refresh.emit()   
      self.runDone.emit()
      
      return
   #======================================================================================================================  
