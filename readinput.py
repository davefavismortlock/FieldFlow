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
      
   shared.observedLEFlowFrom = []
   shared.observedLECategory = []
   shared.observedLEValidCategories = [FIELD_OBS_CATEGORY_BOUNDARY, FIELD_OBS_CATEGORY_CULVERT, FIELD_OBS_CATEGORY_PATH, FIELD_OBS_CATEGORY_ROAD, FIELD_OBS_CATEGORY_STREAM, FIELD_OBS_CATEGORY_DUMMY]
   shared.observedLEBehaviour = []
   shared.observedLEValidBehaviours = [FIELD_OBS_BEHAVIOUR_ALONG, FIELD_OBS_BEHAVIOUR_UNDER, FIELD_OBS_BEHAVIOUR_ACROSS, FIELD_OBS_BEHAVIOUR_ENTER, FIELD_OBS_BEHAVIOUR_DUMMY]
   shared.observedLEDescription = []
   shared.observedLEFlowTo = []
   
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
      
      if dataLine == 0:
         # For flow down the steepest slope, are we considering only topography (T), or considering both topography and anthropogenic elements (A)?
         shared.runType = data
         if shared.runType != "T" and shared.runType != "A":
            printStr = "ERROR: run type = " + shared.runType + ", it must be T or A\n"
            print(printStr)
            
            return -1            
         dataLine += 1
   
      elif dataLine == 1:
         shared.runTitle = data
         dataLine += 1
         
      elif dataLine == 2:
         if data:
            dataSplit = data.split(',')
            for fld in dataSplit:
               shared.fieldsWithFlow.append(fld.strip())
         dataLine += 1
         
      elif dataLine == 3:
         shared.weightBoundary = float(data)
         if shared.weightBoundary > 1:
            printStr = "ERROR: flow start weighting must be less than or equal to 1.0\n"
            print(printStr)
            
            return -1
         dataLine += 1
         
      elif dataLine == 4:
         # Consider ditches?
         tempStr = data.upper().strip()
         if tempStr == "Y":
            shared.considerDitches = True
         elif tempStr == "N":
            shared.considerDitches = False
         else:
            printStr = "ERROR: consider ditches = " + tempStr + ", it must be Y or N\n"
            print(printStr)
            
            return -1            
         dataLine += 1        
 
      elif dataLine == 5:
         # Fill blind pits?
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
 
      elif dataLine == 6:
         # The resolution of the DEM layer or the mean spacing of spot heights (m) 
         shared.resElevData = float(data)
         dataLine += 1
    
      elif dataLine == 7:
         # Distance to search (metres)
         shared.searchDist = float(data)
         dataLine += 1
         
      elif dataLine == 8:
         # Path to all GIS data
         shared.GISPath = data
         dataLine += 1
         
      elif dataLine == 9:
         # Output shapefile for flow marker points
         shared.outFileFlowMarkerPoints = shared.GISPath + data
         dataLine += 1
         
      elif dataLine == 10:
         # Style for Output shapefile for flow marker points
         shared.outFileFlowMarkerPointsStyle = shared.GISPath + data
         dataLine += 1
                  
      elif dataLine == 11:
         shared.outFileFlowMarkerPointsTransparency = int(data)
         dataLine += 1
   
      elif dataLine == 12:   
          # Output shapefile for flow lines
         shared.outFileFlowLines = shared.GISPath + data
         dataLine += 1
         
      elif dataLine == 13:   
          # Style for output shapefile for flow lines
         shared.outFileFlowLinesStyle = shared.GISPath + data
         dataLine += 1
         
      elif dataLine == 14:
         shared.outFileFlowLinesTransparency = int(data)
         dataLine += 1
         
      elif dataLine == 15:
         shared.windowWidth = int(data)
         dataLine += 1
          
      elif dataLine == 16:    
         shared.windowHeight = int(data)
         dataLine += 1
         
      elif dataLine == 17:
         shared.windowMagnification = float(data)
         dataLine += 1
        
      elif dataLine == 18:
         # External coordinate reference system
         shared.externalCRS = data  
         dataLine += 1
         
      elif dataLine == 19:
         # Coordinates of SW corner of area displayed
         coords = data.split(',')
         shared.extentRect.setXMinimum(int(coords[0]))
         shared.extentRect.setYMinimum(int(coords[1]))
         dataLine += 1
         
      elif dataLine == 20:
         # Coordinates of NE corner of area displayed 
         coords = data.split(',')
         shared.extentRect.setXMaximum(int(coords[0]))
         shared.extentRect.setYMaximum(int(coords[1]))
         dataLine += 1
             
      elif dataLine == 21:
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
               
      elif dataLine == 22:
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
            
      elif dataLine == 23:
         # Field observations, don't bother reading them if this is a topography-only run
         if shared.runType == "T":
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
               
               shared.observedLEFlowFrom.append(QgsPoint(float(xCoord), float(yCoord)))
               
            elif obsLine == 1:
               # Category
               if data not in shared.observedLEValidCategories:
                  printStr = "ERROR: unknown field observation category '" + str(data) + "' in field observation at " + displayOS(shared.observedLEFlowFrom[-1].x(), shared.observedLEFlowFrom[-1].y()) 
                  print(printStr)
                  
                  return -1
               
               shared.observedLECategory.append(data)

            elif obsLine == 2:
               # Behaviour
               if data not in shared.observedLEValidBehaviours:
                  printStr = "ERROR: unknown field observation behaviour behaviour '" + str(data) + "' in field observation at " + displayOS(shared.observedLEFlowFrom[-1].x(), shared.observedLEFlowFrom[-1].y())
                  print(printStr)
                  
                  return -1
               
               shared.observedLEBehaviour.append(data)
               
            elif obsLine == 3:
               # Description
               shared.observedLEDescription.append(data)                  
               
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

                  shared.observedLEFlowTo.append(QgsPoint(float(xCoord), float(yCoord)))
               else:
                  # We do not have an outflow location. This is only allowable if the category is "along road", "along path", or "boundary blocked"
                  if not ((shared.observedLECategory[-1] == FIELD_OBS_CATEGORY_ROAD and shared.observedLEBehaviour[-1] == FIELD_OBS_BEHAVIOUR_ALONG) or (shared.observedLECategory[-1] == FIELD_OBS_CATEGORY_PATH and shared.observedLEBehaviour[-1] == FIELD_OBS_BEHAVIOUR_ALONG) or (shared.observedLECategory[-1] == FIELD_OBS_CATEGORY_BOUNDARY and shared.observedLEBehaviour[-1] == FIELD_OBS_BEHAVIOUR_ALONG)):
                     printStr = "ERROR: for field observation '" + shared.observedLECategory[-1] + "' '" + shared.observedLEBehaviour[-1] + "' '" + shared.observedLEDescription[-1] + "', the outflow location must be specified"                        
                     print(printStr)
                     
                     return -1
                  
                  shared.observedLEFlowTo.append(None)                  
               
            obsLine += 1
            if obsLine == 5:
               obsLine = 0
            
         dataLine += 1               

   return 0
   #====================================================================================================================
