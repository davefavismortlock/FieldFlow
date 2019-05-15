   # Find the nearest field boundary polygon TODO could this be passed in as a parameter?
   nearestIDs = shared.vectorInputLayerIndex[layerNum].nearestNeighbor(thisPoint, 3)
   #if len(nearestIDs) > 0:
      #print("Nearest field boundary IDs = " + str(nearestIDs))

   request = QgsFeatureRequest().setFilterFids(nearestIDs)
   features = shared.vectorInputLayers[layerNum].getFeatures(request)

   distToPoint = []
   geomPoint = QgsGeometry.fromPointXY(thisPoint)

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
      featPoly = boundPoly[0]
      #featID = featPoly.id()
      #print("Trying feature ID " + str(featID))

      boundaryFieldCode = featPoly[CONNECTED_FIELD_ID]

      #geomPoly = featPoly.geometry()
      #polygon = geomPoly.asPolygon()
      #points = polygon[0]

      polyGeom = featPoly.geometry()
      if polyGeom.isMultipart():
         polygons = polyGeom.asMultiPolygon()
      else:
         polygons = [polyGeom.asPolygon()]

      # If this is a multipolygon, we only consider the first polygon here
      points = polygons[0]
      #print(len(polyBoundary))
      #print(str(polyBoundary))

      nPointsInPoly = len(points)
      #print("nPointsInPoly = " + str(nPointsInPoly))

      # If this polygon is too small, forget it
      if nPointsInPoly < 3:
         continue

      # OK, the nearest point is an approximation: it is not necessarily a point in the polygon's boundary. So get the actual point in the boundary which is closest
      nearPoint, numNearPoint, _beforeNearPoint, _afterNearPoint, sqrDist = polyGeom.closestVertex(boundPoly[1])
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

         geomThisPoint = QgsGeometry.fromPointXY(thisPoint)

         prevSlope = nextSlope = -1

         # Calculate the elevation difference for the previous point, if not already visited
         numPrevVertex = numThisVertex - 1
         if numPrevVertex < 0:
            numPrevVertex = nPointsInPoly - 2

         if numPrevVertex not in verticesTravelled:
            # This vertex has not already had flow through it
            print("numPrevVertex = " + str(numPrevVertex))
            print("nPointsInPoly = " + str(nPointsInPoly))
            prevPoint = points[numPrevVertex]

            elevPrevPoint = GetRasterElev(prevPoint.x(), prevPoint.y())

            elevDiffPrev = elevThisPoint - elevPrevPoint

            geomPrevPoint = QgsGeometry.fromPointXY(prevPoint)
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

            geomNextPoint = QgsGeometry.fromPointXY(nextPoint)
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
         geomLine = QgsGeometry.fromPolyline([QgsPoint(thisPoint), QgsPoint(flowToPoint)])
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
               #shared.fpOut.write("EEE Intersection with stream found, added flowline from " + DisplayOS(thisPoint.x(), thisPoint.y()) + " to " + DisplayOS(intPoint.x(), intPoint.y()) + "\n")
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
               adjPoint = QgsPointXY(adjX, adjY)
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
                  geomPoint1 = QgsGeometry.fromPointXY(point1)
                  adjPoint, _adjElev = FindSteepestAdjacent(point1, elev, geomPoint1)
                  #print(adjPoint, adjElev)
                  if adjPoint.x() != -1:
                     # There is a within-polygon cell with a steeper gradient
                     AddFlowLine(point1, adjPoint, FLOW_DOWN_STEEPEST, fieldCode, elev)

                     shared.fpOut.write("\tFlow from field " + str(fieldCode) + " has left the boundary of field " + str(boundaryFieldCode) + " at " + DisplayOS(point1.x(), point1.y()) + " and flows down the steepest within-field gradient, to " +  DisplayOS(adjPoint.x(), adjPoint.y()) + "\n")

                     return 0, adjPoint

            # Do we have a nearby field observation?
            indx = FindNearbyFieldObservation(point1)
            if indx != -1:
               # We have found a field observation near this point
               thisElev = GetRasterElev(point1.x(), point1.y())

               # So route flow accordingly
               rtn, adjPoint = FlowViaFieldObservation(indx, fieldCode, point1, thisElev)
               #shared.fpOut.write("Left FlowViaFieldObservation() called in flowAlongVectorFieldBoundary(), rtn = " + str(rtn) + "\n")
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
