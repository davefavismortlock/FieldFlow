import sys

from PyQt4.QtGui import QAction, QMainWindow, QStatusBar, QProgressBar, QSizePolicy, QGridLayout             # , QMessageBox
from PyQt4.QtCore import Qt, QObject, pyqtSignal, QEvent, QSize

from qgis.core import *
from qgis.gui import QgsMapCanvas, QgsMapCanvasLayer, QgsMapToolPan, QgsMapToolZoom, QgsMapToolEmitPoint

import pyperclip

import shared
from shared import *
from simulationthread import SimulationThread


#======================================================================================================================
#
# Class for a map tool, which returns coordinates when the mouse is clicked
#
#======================================================================================================================
class PointTool(QgsMapToolEmitPoint):
   def __init__(self, canvas):
      QgsMapToolEmitPoint.__init__(self, canvas)
#======================================================================================================================


#======================================================================================================================
   def canvasReleaseEvent(self, mouseEvent):
      # Get the coords
      point = self.toMapCoordinates(mouseEvent.pos())
      #shared.fpOut.write(point.x(), point.y())
      
      # Show in the status bar
      coordStr = str("Coordinates: {" + str(point.x()) + ", " + str(point.y()) + "}")
      self.parent().parent().statusBar.showMessage(coordStr, shared.defaultMessageDisplayTime)
      
      # Copy to clipboard
      x = round(point.x() * 2) / 2
      y = round(point.y() * 2) / 2
      pyperclip.copy("{:08.1f}, {:08.1f}".format(x, y))
#======================================================================================================================
    
       
#======================================================================================================================
#
# The class which defines the main window
#
#======================================================================================================================
class MainWindow(QMainWindow):
   def __init__(self, app, canvasLayers, canvasLayersCategory): 
      QMainWindow.__init__(self)
      self.app = app
      self.canvasLayers = canvasLayers
      self.canvasLayersCategory = canvasLayersCategory
      
      self.resize(shared.windowWidth, shared.windowHeight)         
      self.setWindowTitle(shared.progName + ": " + shared.progVer)

      # Set up the map canvas
      self.canvas = QgsMapCanvas()
      self.setCentralWidget(self.canvas)      

      self.canvas.setCanvasColor(Qt.white)
      self.canvas.enableAntiAliasing(True)      
      
      self.canvas.setCachingEnabled(True)
      #self.canvas.setMapUpdateInterval(1000)
      self.canvas.setParallelRenderingEnabled(True)
      self.canvas.enableMapTileRendering(True)
      
      self.canvas.setLayerSet(self.canvasLayers)  
      self.canvas.setExtent(shared.extentRect)
      self.canvas.setMagnificationFactor(shared.windowMagnification)

      mapSet = self.canvas.mapSettings()
      #print(mapSet.flags())
      
      # Create some actions
      #self.actionExit = QAction(QIcon('exit.png'), '&Exit', self)        
      self.actionExit = QAction("&Exit", self)
      self.actionExit.setShortcut("Ctrl+Q")
      self.actionExit.setStatusTip("Exit " + shared.progName)
      
      self.actionZoomIn = QAction("Zoom in", self)
      self.actionZoomIn.setCheckable(True)
      #self.actionExit.setShortcut("Ctrl++")
      self.actionZoomIn.setStatusTip("Show more detail")
      
      self.actionZoomOut = QAction("Zoom out", self)
      self.actionZoomOut.setCheckable(True)
      #self.actionExit.setShortcut("Ctrl+-")
      self.actionZoomOut.setStatusTip("Show less detail")
      
      self.actionPan = QAction("Pan", self)
      self.actionPan.setCheckable(True)
      self.actionPan.setStatusTip("Move the map laterally")
      
      if shared.haveRasterBackground:
         self.actionChangeBackground = QAction("Change background", self)
         self.actionChangeBackground.setStatusTip("Change the raster background")

      self.actionCoords = QAction("Show coordinates", self)
      self.actionCoords.setCheckable(True)
      self.actionCoords.setStatusTip("Click to show coordinates")
      
      self.actionRun = QAction("Simulate", self)
      self.actionRun.setStatusTip("Route flow")

      # Connect the actions
      self.actionExit.triggered.connect(app.quit)
      self.actionZoomIn.triggered.connect(self.zoomIn)
      self.actionZoomOut.triggered.connect(self.zoomOut)
      self.actionPan.triggered.connect(self.pan)
      if shared.haveRasterBackground:
         self.actionChangeBackground.triggered.connect(self.changeBackground)
      self.actionCoords.triggered.connect(self.showCoords)
      self.actionRun.triggered.connect(self.doRun)
      

      # Create a menu bar and add menus
      self.menubar = self.menuBar()
      
      self.fileMenu = self.menubar.addMenu("&File")
      self.fileMenu.addAction(self.actionExit)
      
      self.editMenu = self.menubar.addMenu("&Edit")
      #self.editMenu.addAction(self.actionExit)
 
      self.viewMenu = self.menubar.addMenu("&View")
      self.viewMenu.addAction(self.actionZoomIn)
      self.viewMenu.addAction(self.actionZoomOut)
      self.viewMenu.addAction(self.actionPan)
      if shared.haveRasterBackground:
         self.viewMenu.addAction(self.actionChangeBackground)
      self.viewMenu.addAction(self.actionCoords)
      
      self.runMenu = self.menubar.addMenu("&Run")
      self.runMenu.addAction(self.actionRun)
      
      # Create a tool bar and add some actions
      self.toolbar = self.addToolBar("Default")
      self.toolbar.setFloatable(True)
      
      self.toolbar.addAction(self.actionRun)
      self.toolbar.addAction(self.actionZoomIn)
      self.toolbar.addAction(self.actionZoomOut)
      self.toolbar.addAction(self.actionPan)
      self.toolbar.addAction(self.actionCoords)

      # Create some map tools
      self.toolPan = QgsMapToolPan(self.canvas)
      self.toolPan.setAction(self.actionPan)
      self.toolZoomIn = QgsMapToolZoom(self.canvas, False)        # False = in
      self.toolZoomIn.setAction(self.actionZoomIn)
      self.toolZoomOut = QgsMapToolZoom(self.canvas, True)        # True = out
      self.toolZoomOut.setAction(self.actionZoomOut)
      self.toolCoords = PointTool(self.canvas)
      self.toolCoords.setAction(self.actionCoords)
      
      # Put into panning mode
      self.pan()
      
      # Add a status bar
      self.statusBar = QStatusBar(self.canvas)
      self.setStatusBar(self.statusBar)
        
      # And put a progress indicator on the status bar
      self.statusBar.progress = QProgressBar(self)
      self.statusBar.progress.setRange(0, 100)
      self.statusBar.progress.setMaximumWidth(500)
      self.statusBar.progress.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
      self.statusBar.addPermanentWidget(self.statusBar.progress)
      
      self.myThread = None
      
      return
#======================================================================================================================


#======================================================================================================================      
   def doRun(self):
      # Delete all output features (in case we have some from a previous run)
      listIDs = [feat.id() for feat in shared.outFlowMarkerPointLayer.getFeatures()]
      prov = shared.outFlowMarkerPointLayer.dataProvider() 
      prov.deleteFeatures([featID for featID in listIDs])
      shared.outFlowMarkerPointLayer.updateExtents()
      shared.outFlowMarkerPointLayer.triggerRepaint()      
    
      listIDs = [feat.id() for feat in shared.outFlowLineLayer.getFeatures()]
      prov = shared.outFlowLineLayer.dataProvider() 
      prov.deleteFeatures([featID for featID in listIDs])
      shared.outFlowLineLayer.updateExtents()
      shared.outFlowLineLayer.triggerRepaint()
         
      self.canvas.repaint()
      self.statusBar.progress.setValue(0)
   
      # All is now ready, so run the simulation as a separate thread
      self.myThread = SimulationThread(self.app, self)
      
      self.myThread.refresh.connect(self.doRefresh)
      self.myThread.runDone.connect(self.runDone)

      self.canvas.freeze(True)
      #self.canvas.refreshAllLayers()
      #self.app.processEvents()     
      
      self.myThread.start()
      
      print("\nThread started")
            
      return
#======================================================================================================================      

      
#======================================================================================================================      
   def doRefresh(self):
      self.canvas.freeze(False)
      
      if not self.canvas.isDrawing():
         shared.outFlowMarkerPointLayer.triggerRepaint()
         shared.outFlowLineLayer.triggerRepaint()
         self.canvas.repaint()
         
      self.canvas.freeze(True)   
         
      doneSoFar = (float(shared.thisStartPoint) / float(len(shared.flowStartPoints) + 1)) * 100.0
      #shared.fpOut.write(doneSoFar)
      self.statusBar.progress.setValue(doneSoFar)
        
      return
#======================================================================================================================
     

#======================================================================================================================
   def zoomIn(self):
      self.canvas.freeze(False)
      self.canvas.setMapTool(self.toolZoomIn)
      return
#======================================================================================================================


#======================================================================================================================
   def zoomOut(self):
      self.canvas.freeze(False)
      self.canvas.setMapTool(self.toolZoomOut)
      return
#======================================================================================================================


#======================================================================================================================
   def pan(self):
      self.canvas.freeze(False)
      self.canvas.setMapTool(self.toolPan)
      return
#======================================================================================================================
      

#======================================================================================================================
   def showCoords(self):
      self.canvas.setMapTool(self.toolCoords)
      
      return
#======================================================================================================================


#======================================================================================================================
   def close(self):
      if self.myThread: 
         self.myThread.terminate()
         
      self.app.quit
      
      return
#======================================================================================================================


#======================================================================================================================
   def runDone(self):
      self.canvas.freeze(False)
      shared.outFlowMarkerPointLayer.triggerRepaint()
      shared.outFlowLineLayer.triggerRepaint()
      self.canvas.repaint()
      
      print("Thread done")
      self.myThread.quit()
      
      self.statusBar.progress.setValue(100)
      
      #QMessageBox.information(self, "End of run", shared.progName + ": flow routed")
      self.statusBar.showMessage("End of run: flow routed", shared.defaultMessageDisplayTime)
      
      # To prevent subsequent re-runs      
      self.actionRun.setEnabled(False)   
      
      return
#======================================================================================================================


#======================================================================================================================
   def changeBackground(self):
      for n in range(len(self.canvasLayers)):
         if self.canvasLayersCategory[n] == INPUT_RASTER_BACKGROUND:
            self.canvasLayers[n].setVisible(not self.canvasLayers[n].isVisible())
         
      self.canvas.setLayerSet(self.canvasLayers)  
      self.canvas.repaint()
      
      return      
#======================================================================================================================

      
