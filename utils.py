from math import isclose

from qgis.core import QgsPointXY, QgsRaster

import shared
from shared import INPUT_DIGITAL_ELEVATION_MODEL

# pylint: disable=too-many-arguments


#======================================================================================================================
#
# Checks whether the supplied argument is a number. From https://stackoverflow.com/questions/354038/how-do-i-check-if-a-string-is-a-number-float
#
#======================================================================================================================
def is_number(s):
   try:
      float(s)
      return True
   except ValueError:
      return False
#======================================================================================================================


#======================================================================================================================
#
# Converts coords in the raster grid CRS to coords in the external CRS
#
#======================================================================================================================
def gridCRSToExtCRS(x, y, cellWidth, cellHeight, originX, originY):
   xExt = (cellWidth * x) + originX + (cellWidth / 2)
   yExt = (cellHeight * y) + originY + (cellHeight / 2)

   return QgsPointXY(xExt, yExt)
#======================================================================================================================


#======================================================================================================================
#
# Converts coords in the external CRS to coords in the raster grid CRS
#
#======================================================================================================================
def extCRSToGridCRS(x, y, cellWidth, cellHeight, originX, originY):
   xGrid = (x - originX - (cellWidth / 2)) / cellWidth
   yGrid = (y - originY - (cellHeight / 2)) / cellHeight

   return QgsPointXY(xGrid, yGrid)
#======================================================================================================================


#======================================================================================================================
#
# Given a coord, calculates the coord of the centroid of the DEM cell which contains this coord (all ext CRS)
#
#======================================================================================================================
def GetCentroidOfContainingDEMCell(x, y):
   diffX = x - shared.xMinExtentDEM
   diffY = y - shared.yMinExtentDEM
   numXPixels = diffX // shared.cellWidthDEM       # Integer division
   numYPixels = diffY // shared.cellHeightDEM      # Integer division

   centroidX = shared.xMinExtentDEM + (numXPixels * shared.cellWidthDEM) + (shared.cellWidthDEM / 2)
   centroidY = shared.yMinExtentDEM + (numYPixels * shared.cellHeightDEM) + (shared.cellHeightDEM / 2)

   return QgsPointXY(centroidX, centroidY)
#======================================================================================================================


#======================================================================================================================
#
# Displays an OS grid reference neatly
#
#======================================================================================================================
def DisplayOS(x, y, rounding = True):
   if rounding:
      x = round(x * 2) / 2
      y = round(y * 2) / 2
      #return "{" + "{:08.1f}, {:08.1f}".format(x, y) + "}"
      return "{" + "{:06.0f}, {:06.0f}".format(x, y) + "}"

   return "{" + str(x) + ", " + str(y) + "}"
#======================================================================================================================


#======================================================================================================================
#
# Capitalizes the first character of a string, leaves the rest untouched (from https://stackoverflow.com/questions/40454141/capitalize-first-letter-only-of-a-string-in-python)
#
#======================================================================================================================
def ToSentenceCase(s):
   return s[:1].upper() + s[1:]
#======================================================================================================================


#======================================================================================================================
#
# Given two points and a spacing, returns a list with all points (with the given spacing) on the straight line which joins the points. The list includes both start and finish points
#
#======================================================================================================================
def GetPointsOnLine(startPoint, endPoint, spacing):
   # Safety check, in case the two points are identical (could happen due to rounding errors)
   if isclose(startPoint.x(), endPoint.x()) and isclose(startPoint.y(), endPoint.y()):
      return []

   # Interpolate between cells by a simple DDA line algorithm, see http://en.wikipedia.org/wiki/Digital_differential_analyzer_(graphics_algorithm) Note that Bresenham's algorithm gave occasional gaps
   XInc = float(endPoint.x() - startPoint.x())
   YInc = float(endPoint.y() - startPoint.y())
   length = max(abs(XInc), abs(YInc))

   XInc = XInc / length
   YInc = YInc / length

   x = startPoint.x()
   y = startPoint.y()

   spacing = max(1, int(round(spacing)))

   points = []
   # Process each interpolated point
   for _ in range(0, int(length), int(spacing)):
      points.append(QgsPointXY(x, y))

      x += XInc
      y += YInc

   points.append(endPoint)

   return points
#======================================================================================================================


#======================================================================================================================
#
# Returns the elevation of a point from a raster layer
#
#======================================================================================================================
def GetRasterElev(x, y):
   # pylint: disable=too-many-locals

   # Search all layers
   for layerNum in range(len(shared.rasterInputLayersCategory)):
      if shared.rasterInputLayersCategory[layerNum] == INPUT_DIGITAL_ELEVATION_MODEL:
         # OK, this is our raster elevation data
         provider = shared.rasterInputData[layerNum][1][0]
         xSize = shared.rasterInputData[layerNum][1][1]
         ySize = shared.rasterInputData[layerNum][1][2]
         #cellWidth = shared.rasterInputData[layerNum][1][3]
         #cellHeight = shared.rasterInputData[layerNum][1][4]
         extent = shared.rasterInputData[layerNum][1][5]
         dpi = shared.rasterInputData[layerNum][1][6]

         # Now look up the elevation value at this point
         point = QgsPointXY(x, y)
         result = provider.identify(point, QgsRaster.IdentifyFormatValue, extent, xSize, ySize, dpi)
         error = result.error()
         if not error.isEmpty() or not result.isValid():
            shared.fpOut.write(error.summary())
            return -1, -1, -1

         # We have a valid result, so get the elevation. First get this as a dict of key-value pairs
         dictResults = result.results()

         # Now get the first value from the dict (assume we only have a single band)
         elevList = list(dictResults.values())
         elev = elevList[0]

         # However some results are from a 'wrong' sheet (i.e. a sheet which does not contain this point), so ignore these results
         if elev != None:
            return elev

   return -1
#======================================================================================================================


#======================================================================================================================
#
# Returns the z cross-product of the angle at two intersecting lines: is +ve for one direction, -ve for the other
#
#======================================================================================================================
def CalcZCrossProduct(prevPoint, thisPoint, nextPoint):
   dx1 = thisPoint.x() - prevPoint.x()
   dy1 = thisPoint.y() - prevPoint.y()
   dx2 = nextPoint.x() - thisPoint.x()
   dy2 = nextPoint.y() - thisPoint.y()

   zCrossProduct = dx1*dy2 - dy1*dx2

   return zCrossProduct
#======================================================================================================================


#======================================================================================================================
#
# Given three non-coincident points A, B, and C with their elevations, elevA < elevB and elevC < elevB, determines which of the two downhill paths A-B or B-C is steeper
#
#======================================================================================================================
def GetSteeperOfTwoLines(pointA, elevA, pointB, elevB, pointC, elevC):
   ABDistX = abs(pointA.x() - pointB.x())
   ABDistY = abs(pointA.y() - pointB.y())
   BCDistX = abs(pointB.x() - pointC.x())
   BCDistY = abs(pointB.y() - pointC.y())

   sqrDistAB = (ABDistX * ABDistX) + (ABDistY * ABDistY)
   sqrDistBC = (BCDistX * BCDistX) + (BCDistY * BCDistY)

   elevDiffAB = elevB - elevA
   elevDiffBC = elevB - elevC

   gradientSqrAB = elevDiffAB / sqrDistAB
   gradientSqrBC = elevDiffBC / sqrDistBC

   if gradientSqrAB > gradientSqrBC:
      return True
   else:
      return False
#======================================================================================================================

