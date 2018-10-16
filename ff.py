#!/usr/bin/python2

# TODO
# paths!
# flow along road segments does not look for nearby pre-existing flow


from qgis.core import *

from PyQt4.QtGui import QApplication

import shared
from shared import *
from readinput import readInput
from gui import MainWindow
from initialize import setUpSimulation


#======================================================================================================================
#
# The MainApp class
#
#======================================================================================================================
class MainApp(QgsApplication):
   def __init__(self):
      QgsApplication.__init__(self, sys.argv, True)
   
      #print(self.showSettings())
      
      # Set the path to QGIS and initialize
      self.setPrefixPath("/usr", True)
      self.initQgis()     
      
      # Get the input parameters
      rtn = readInput()
      if rtn == -1:
         print("ERROR: see output file")
         exit(rtn)      
      
      # Initialise variables and read the GIS layers
      canvasLayers, canvasLayersCategory = setUpSimulation()
      if canvasLayers == -1:
         print("ERROR: see output file")
         exit(rtn)
      
      # Create the main window, and start the simulation thread
      appWindow = MainWindow(self, canvasLayers, canvasLayersCategory)

      # Show the window
      appWindow.show()
      #appWindow.canvas.refreshAllLayers()
      #self.processEvents()           
      
      # The main GUI loop
      self.exec_()        
      
      # Close the main window
      appWindow.close()
      self.exitQgis()
      
      print("\nEnd of run")
   
      #exit (0)
#======================================================================================================================


if __name__== "__main__":
   import sys
   app = MainApp()
