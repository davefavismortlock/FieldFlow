#!/usr/bin/python3

# TODO flow along road segments does not look for nearby pre-existing flow

from sys import argv

from qgis.core import QgsApplication

from readinput import readInput
from gui import MainWindow
from initialize import setUpSimulation


#======================================================================================================================
#
# The MainApp class
#
#======================================================================================================================
class MainApp(QgsApplication):
   def __init__(self, args):
      args2 = []
      for arg in args:
         args2.append(arg.encode('utf-8'))

      super(MainApp, self).__init__(args2, True)

      #print(self.showSettings())

      # Set the path to QGIS and initialize
      qgisPath = "/usr" # TODO Put in shared
      self.setPrefixPath(qgisPath, True)
      self.initQgis()

      # Get the input parameters
      rtn = readInput()
      if rtn == -1:
         print("ERROR: in input file")
         exit(rtn)

      # Initialise variables and read the GIS layers
      mapLayers, mapLayersCategory = setUpSimulation()
      if mapLayers == -1:
         print("ERROR: could not create map layer, see output file")
         exit(rtn)

      # Create the main window, and start the simulation thread
      appWindow = MainWindow(self, mapLayers, mapLayersCategory)

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

      exit (0)
#======================================================================================================================


if __name__ == "__main__":
   app = MainApp(argv)
