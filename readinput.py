import shared
from shared import *
from utils import displayOS


#======================================================================================================================
#
# Processes a single line from a text file, ignoring comments. Each valid data line must contain a colon
#
#======================================================================================================================
def checkDataLine(inData, fileName):
   # Ignore blank or wholly-comment lines (beginning with a comment character)
   if len(inData) == 0 or inData[0] == COMMENT1 or inData[0] == COMMENT2:
      return -1

   # Trim off trailing comments
   indx = inData.find(COMMENT1)
   if indx > 0:
      inData = inData[:indx]
      inData = inData.strip()
      
   indx = inData.find(COMMENT2)
   if indx > 0:
      inData = inData[:indx]
      inData = inData.strip()
   
   indx = inData.find(':')
   if indx == -1:
      print("ERROR: invalid line in " + fileName + "'" + inData +"'")
      return -1
   
   data = inData[indx+1:]
   data = data.strip()
   
   return data
#======================================================================================================================


#======================================================================================================================
#
# Reads the initialisation file and the input data file
#
#======================================================================================================================
def readInput():
   # First open and read the .ini file to get the name of the data file
   iniFile = "./ff.ini"
   
   # TODO test for file opening
   fpIni = open(iniFile, "r")

   dataLine = 0
   for inData in fpIni:
      inData = inData.strip()
      
      data = checkDataLine(inData, iniFile)
      if data == -1:
         continue
      
      if dataLine == 0:
         shared.dataInputFile = data
         
      elif dataLine == 1:
         shared.textOutputFile = data
         
      dataLine += 1      

   fpIni.close()
   
   # Before reading the data file, do some initialisation
   shared.extentRect = QgsRectangle()
   
   shared.fieldsWithFlow = []
   
   shared.outFlowMarkerPointLayer = QgsVector()
   shared.outFlowLineLayer = QgsVector()
   
   shared.vectorFileName = []
   shared.vectorFileTable = []
   shared.vectorFileTitle = []
   shared.vectorFileType = []
   shared.vectorFileStyle = []
   shared.vectorFileTransparency = []
   shared.vectorFileCategory = []
   
   shared.rasterFileName = []
   shared.rasterFileTitle = []
   shared.rasterFileStyle = []
   shared.rasterFileTransparency = []
   shared.rasterFileCategory = []
   
   shared.vectorInputLayers = []
   shared.vectorInputLayersCategory = []
   shared.vectorInputIndex = []
   shared.rasterInputLayers = []
   shared.rasterInputLayersCategory = []
   shared.rasterInputData = []
      
   shared.fieldObservationFlowFrom = []
   shared.fieldObservationCategory = []
   shared.fieldObservationValidCategories = [FIELD_OBS_CATEGORY_BOUNDARY, FIELD_OBS_CATEGORY_CULVERT, FIELD_OBS_CATEGORY_PATH, FIELD_OBS_CATEGORY_ROAD, FIELD_OBS_CATEGORY_STREAM, FIELD_OBS_CATEGORY_DUMMY]
   shared.fieldObservationBehaviour = []
   shared.fieldObservationValidBehaviours = [FIELD_OBS_BEHAVIOUR_ALONG, FIELD_OBS_BEHAVIOUR_UNDER, FIELD_OBS_BEHAVIOUR_ACROSS, FIELD_OBS_BEHAVIOUR_ENTER, FIELD_OBS_BEHAVIOUR_THROUGH, FIELD_OBS_BEHAVIOUR_DUMMY]
   shared.fieldObservationDescription = []
   shared.fieldObservationFlowTo = []
   
   # Now open and read the data file TODO test for file opening
   fpData = open(shared.dataInputFile, "r")
   
   dataLine = 0
   while True:
      inData = fpData.readline()
      if not inData:
         break
      
      inData = inData.strip()
      #print(str(dataLine) + " '" + inData + "'")
      
      if inData.find(EOF_FIELD_OBSERVATIONS) >= 0:
         break          
      
      data = checkDataLine(inData, shared.dataInputFile)
      if data == -1:
         continue
      
      elif dataLine == 0:
         shared.runTitle = data
         dataLine += 1
         
      elif dataLine == 1:
         if data:
            dataSplit = data.split(',')
            for fld in dataSplit:
               shared.fieldsWithFlow.append(fld.strip())
         dataLine += 1
         
      elif dataLine == 2:
         shared.weightBoundary = float(data)
         if shared.weightBoundary > 1:
            printStr = "ERROR: flow start weighting must be less than or equal to 1.0\n"
            print(printStr)
            
            return -1
         dataLine += 1
         
      elif dataLine == 3:
         # Consider field observations?
         tempStr = data.upper().strip()
         if tempStr == "Y":
            shared.considerFieldObservations = True
         elif tempStr == "N":
            shared.considerFieldObservations = False
         else:
            printStr = "ERROR: consider field observations = " + tempStr + ", it must be Y or N\n"
            print(printStr)
            
            return -1            
         dataLine += 1
   
      elif dataLine == 4:
         # Fill blind pits?
         if shared.considerFieldObservations:
            shared.fillBlindPits = False
         else:
            tempStr = data.upper().strip()
            if tempStr == "Y":
               shared.fillBlindPits = True
            elif tempStr == "N":
               shared.fillBlindPits = False
            else:
               printStr = "ERROR: fill blind pits = " + tempStr + ", it must be Y or N\n"
               print(printStr)
               
               return -1            
         dataLine += 1        
         
      elif dataLine == 5:
         # Consider ditches and streams?
         if shared.considerFieldObservations:
            shared.considerDitches = True
         else:
            tempStr = data.upper().strip()
            if tempStr == "Y":
               shared.considerDitches = True
            elif tempStr == "N":
               shared.considerDitches = False
            else:
               printStr = "ERROR: consider ditches and streams = " + tempStr + ", it must be Y or N\n"
               print(printStr)
               
               return -1            
         dataLine += 1        
         
      elif dataLine == 6:
         # Consider roads?
         if not shared.considerFieldObservations:
            shared.considerRoads = False
         else:
            tempStr = data.upper().strip()
            if tempStr == "Y":
               shared.considerRoads = True
            elif tempStr == "N":
               shared.considerRoads = False
            else:
               printStr = "ERROR: consider roads = " + tempStr + ", it must be Y or N\n"
               print(printStr)
               
               return -1            
         dataLine += 1        
         
      elif dataLine == 7:
         # Consider tracks and paths?
         if not shared.considerFieldObservations:
            shared.considerTracks = False
         else:
            tempStr = data.upper().strip()
            if tempStr == "Y":
               shared.considerTracks = True
            elif tempStr == "N":
               shared.considerTracks = False
            else:
               printStr = "ERROR: consider tracks and paths = " + tempStr + ", it must be Y or N\n"
               print(printStr)
               
               return -1            
         dataLine += 1        
 
      elif dataLine == 8:
         # Consider field boundaries?
         if not shared.considerFieldObservations:
            shared.considerFieldBoundaries = False
         else:
            tempStr = data.upper().strip()
            if tempStr == "Y":
               shared.considerFieldBoundaries = True
            elif tempStr == "N":
               shared.considerFieldBoundaries = False
            else:
               printStr = "ERROR: consider field boundaries = " + tempStr + ", it must be Y or N\n"
               print(printStr)
               
               return -1            
         dataLine += 1        
         
      elif dataLine == 9:
         # The resolution of the DEM layer (m) 
         shared.resolutionOfDEM = float(data)
         dataLine += 1
    
      elif dataLine == 10:
         # Distance to search (metres)
         shared.searchDist = float(data)
         dataLine += 1
         
      elif dataLine == 11:
         # Path to all GIS data
         shared.GISPath = data
         dataLine += 1
         
      elif dataLine == 12:
         # Output shapefile for flow marker points
         shared.outFileFlowMarkerPoints = shared.GISPath + data
         dataLine += 1
         
      elif dataLine == 13:
         # Style for Output shapefile for flow marker points
         shared.outFileFlowMarkerPointsStyle = shared.GISPath + data
         dataLine += 1
                  
      elif dataLine == 14:
         shared.outFileFlowMarkerPointsTransparency = int(data)
         dataLine += 1
   
      elif dataLine == 15:   
          # Output shapefile for flow lines
         shared.outFileFlowLines = shared.GISPath + data
         dataLine += 1
         
      elif dataLine == 16:   
          # Style for output shapefile for flow lines
         shared.outFileFlowLinesStyle = shared.GISPath + data
         dataLine += 1
         
      elif dataLine == 17:
         shared.outFileFlowLinesTransparency = int(data)
         dataLine += 1
         
      elif dataLine == 18:
         shared.windowWidth = int(data)
         dataLine += 1
          
      elif dataLine == 19:    
         shared.windowHeight = int(data)
         dataLine += 1
         
      elif dataLine == 20:
         shared.windowMagnification = float(data)
         dataLine += 1
        
      elif dataLine == 21:
         # External coordinate reference system
         shared.externalCRS = data  
         dataLine += 1
         
      elif dataLine == 22:
         # Coordinates of SW corner of area displayed
         coords = data.split(',')
         shared.extentRect.setXMinimum(int(coords[0]))
         shared.extentRect.setYMinimum(int(coords[1]))
         dataLine += 1
         
      elif dataLine == 23:
         # Coordinates of NE corner of area displayed 
         coords = data.split(',')
         shared.extentRect.setXMaximum(int(coords[0]))
         shared.extentRect.setYMaximum(int(coords[1]))
         dataLine += 1
             
      elif dataLine == 24:
         # Vector files
         first = True
         vecLine = 0

         while True:
            if first:
               inVecData = inData
               first = False
            else:
               inVecData = fpData.readline()
               
            if not inVecData:
               break
            
            if inVecData.find(EOF_VECTOR_DATA) >= 0:
               break
            
            inVecData = inVecData.strip()
            #print(str(dataLine) + " " + str(vecLine) + " '" + inVecData + "'")

            data = checkDataLine(inVecData, shared.dataInputFile)
            if data == -1:
               continue
   
            if vecLine == 0:
               shared.vectorFileName.append(shared.GISPath + data)
            elif vecLine == 1:
               shared.vectorFileTable.append(data)
            elif vecLine == 2:
               shared.vectorFileTitle.append(data)
            elif vecLine == 3:
               shared.vectorFileType.append(data)
            elif vecLine == 4:
               shared.vectorFileStyle.append(shared.GISPath + data)
            elif vecLine == 5:
               shared.vectorFileTransparency.append(int(data))
            elif vecLine == 6:
               shared.vectorFileCategory.append(eval(data))

            vecLine += 1
            if vecLine == 7:
               vecLine = 0
               
         dataLine += 1
               
      elif dataLine == 25:
         # Raster files
         first = True
         rasLine = 0

         while True:  
            if first:
               inRasData = inData
               first = False
            else:
               inRasData = fpData.readline()
               
            if not inRasData:
               break
            
            if inRasData.find(EOF_RASTER_DATA) >= 0:
               break

            inRasData = inRasData.strip()
            #print("Raster " + str(dataLine) + " " + str(rasLine) + " '" + inRasData + "'")

            data = checkDataLine(inRasData, shared.dataInputFile)
            if data == -1:
               continue
   
            if rasLine == 0:
               shared.rasterFileName.append(shared.GISPath + data)
            elif rasLine == 1:
               shared.rasterFileTitle.append(data)
            elif rasLine == 2:
               shared.rasterFileStyle.append(shared.GISPath + data)
            elif rasLine == 3:
               shared.rasterFileTransparency.append(int(data))
            elif rasLine == 4:
               shared.rasterFileCategory.append(eval(data))

            rasLine += 1
            if rasLine == 5:
               rasLine = 0
               
         dataLine += 1
            
      elif dataLine == 26:
         # Field observations, don't bother reading them if this is a topography-only run
         if shared.considerFieldObservations == "T":
            break
         
         first = True
         obsLine = 0

         while True:
            if first:
               inObsData = inData
               first = False
            else:
               inObsData = fpData.readline()
               
            if not inObsData:
               break
            
            if inObsData.find(EOF_FIELD_OBSERVATIONS) >= 0:
               break

            inObsData = inObsData.strip()
            #print("Field obs " + str(dataLine) + " " + str(obsLine) + " '" + inObsData + "'")

            data = checkDataLine(inObsData, shared.dataInputFile)
            if data == -1:
               continue
            
            if obsLine == 0:
               # Inflow location: check for six digits in co-ord
               isOK = False
               coords = data.split(',')
               xCoord = coords[0].strip()
               yCoord = coords[1].strip()
               
               indx = xCoord.find(".")
               if indx == -1 or indx == 6:
                  isOK = True
                  
               indx = yCoord.find(".")
               if indx == -1 or indx == 6:
                  isOK = True
                  
               if not isOK:
                  printStr = "ERROR: '" + data + "' is not a six-figure OS grid reference"
                  print(printStr)
                  
                  return -1
               
               shared.fieldObservationFlowFrom.append(QgsPoint(float(xCoord), float(yCoord)))
               
            elif obsLine == 1:
               # Category
               if data not in shared.fieldObservationValidCategories:
                  printStr = "ERROR: unknown field observation category '" + str(data) + "' in field observation at " + displayOS(shared.fieldObservationFlowFrom[-1].x(), shared.fieldObservationFlowFrom[-1].y()) 
                  print(printStr)
                  
                  return -1
               
               shared.fieldObservationCategory.append(data)

            elif obsLine == 2:
               # Behaviour
               if data not in shared.fieldObservationValidBehaviours:
                  printStr = "ERROR: unknown field observation behaviour behaviour '" + str(data) + "' in field observation at " + displayOS(shared.fieldObservationFlowFrom[-1].x(), shared.fieldObservationFlowFrom[-1].y())
                  print(printStr)
                  
                  return -1
               
               shared.fieldObservationBehaviour.append(data)
               
            elif obsLine == 3:
               # Description
               shared.fieldObservationDescription.append(data)                  
               
            elif obsLine == 4:
               # Outflow location
               if data:
                  # We have an outflow location, check for six digits in co-ord
                  isOK = False
                  coords = data.split(',')
                  xCoord = coords[0].strip()
                  yCoord = coords[1].strip()
                  
                  indx = xCoord.find(".")
                  if indx == -1 or indx == 6:
                     isOK = True
                     
                  indx = yCoord.find(".")
                  if indx == -1 or indx == 6:
                     isOK = True
                     
                  if not isOK:
                     printStr = "ERROR: '" + data + "' is not a six-figure OS grid reference"
                     print(printStr)
                     
                     return -1

                  shared.fieldObservationFlowTo.append(QgsPoint(float(xCoord), float(yCoord)))
               else:
                  # We do not have an outflow location. This is only allowable if the category is "along road", "along path", or "boundary blocked"
                  if not ((shared.fieldObservationCategory[-1] == FIELD_OBS_CATEGORY_ROAD and shared.fieldObservationBehaviour[-1] == FIELD_OBS_BEHAVIOUR_ALONG) or (shared.fieldObservationCategory[-1] == FIELD_OBS_CATEGORY_PATH and shared.fieldObservationBehaviour[-1] == FIELD_OBS_BEHAVIOUR_ALONG) or (shared.fieldObservationCategory[-1] == FIELD_OBS_CATEGORY_BOUNDARY and shared.fieldObservationBehaviour[-1] == FIELD_OBS_BEHAVIOUR_ALONG)):
                     printStr = "ERROR: for field observation '" + shared.fieldObservationCategory[-1] + "' '" + shared.fieldObservationBehaviour[-1] + "' '" + shared.fieldObservationDescription[-1] + "', the outflow location must be specified"                        
                     print(printStr)
                     
                     return -1
                  
                  shared.fieldObservationFlowTo.append(None)                  
               
            obsLine += 1
            if obsLine == 5:
               obsLine = 0
            
         dataLine += 1               

   return 0
   #====================================================================================================================
