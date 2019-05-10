# SHARED CONSTANTS ====================================================================================================
COMMENT1                      = '#'
COMMENT2                      = ';'

TARGET_RIVER                  = "ROTHER"

EOF_VECTOR_DATA               = "END OF VECTOR LAYERS"
EOF_RASTER_DATA               = "END OF RASTER LAYERS"
EOF_FIELD_OBSERVATIONS        = "END OF FIELD OBSERVATIONS"

PREV_POINT                    = 0
THIS_POINT                    = 1
POST_POINT                    = 2

# Input datasets ======================================================================================================
INPUT_OBSERVED_FLOW_LINES     = 1
INPUT_FIELD_BOUNDARIES        = 2
INPUT_DIGITAL_ELEVATION_MODEL = 3
INPUT_WATER_NETWORK           = 4
INPUT_ROAD_NETWORK            = 5
INPUT_PATH_NETWORK            = 6
INPUT_RASTER_BACKGROUND       = 7

# OS TERRAIN 5 XYZ FIELD NAME
OS_TERRAIN_5_XYZ_ELEVATION    = "field_3"

# OS MASTERMAP WATER NETWORK FIELD NAMES
OS_WATER_NETWORK_LEVEL        = "level"
OS_WATER_NETWORK_NAME         = "watercourseName"
OS_WATER_NETWORK_LOCAL_ID     = "localId"

# OS VECTORMAP LOCAL ROAD CENTRELINE FIELD NAMES
OS_VECTORMAP_FEAT_CODE        = "FeatCode"
OS_VECTORMAP_FEAT_DESC        = "FeatDesc"
OS_VECTORMAP_ROAD_NAME        = "roadName"
OS_VECTORMAP_ROAD_NUMBER      = "roadNumber"

# Paths and tracks
PATH_DESC                     = "desc"

# Connected field boundaries
CONNECTED_FIELD_ID            = "field_ID"

# Field observation valid categories
FIELD_OBS_CATEGORY_BOUNDARY   = "boundary"
FIELD_OBS_CATEGORY_CULVERT    = "culvert"
FIELD_OBS_CATEGORY_PATH       = "path"
FIELD_OBS_CATEGORY_ROAD       = "road"
FIELD_OBS_CATEGORY_STREAM     = "stream"
FIELD_OBS_CATEGORY_BLIND_PIT  = "blindpit"

# Field observation valid behaviours
FIELD_OBS_BEHAVIOUR_ALONG    = "along"
FIELD_OBS_BEHAVIOUR_UNDER    = "under"
FIELD_OBS_BEHAVIOUR_ACROSS   = "across"
FIELD_OBS_BEHAVIOUR_THROUGH  = "through"
FIELD_OBS_BEHAVIOUR_ENTER    = "enter"
FIELD_OBS_BEHAVIOUR_LEAVE    = "leave"
FIELD_OBS_BEHAVIOUR_OVERTOP  = "overtop"

# Output datasets =====================================================================================================
OUTPUT_FLOW_MARKERS           = 0
OUTPUT_FLOW_LINES             = 1

# Names of output vector layers
FLOW_MARKERS                  = "FlowMarker"
FLOW_LINES                    = "FlowLine"

# Field names used in all output vector layers
OUTPUT_TYPE                   = "Type"
OUTPUT_FIELD_CODE             = "FieldCode"
OUTPUT_ELEVATION              = "Elev"

# Values used for OUTPUT_TYPE field
# Flow lines
FLOW_DOWN_STEEPEST            = "Steepest"
MERGED_WITH_ADJACENT_FLOWLINE = "Merged"
#FLOW_VIA_LANDSCAPE_ELEMENT    = "LE"
FLOW_VIA_STREAM               = "Stream"
FLOW_VIA_ROAD                 = "Road"
FLOW_VIA_PATH                 = "Path"
FLOW_VIA_BOUNDARY             = "Boundary"
FLOW_ADJUSTMENT_DUMMY         = "Dummy"
FLOW_TO_FIELD_BOUNDARY        = "ToBoundary"
FLOW_OUT_OF_BLIND_PIT         = "OutBlindPit"
BLIND_PIT                     = "BlindPit"

# Markers
MARKER_HIGHEST_POINT          = " highest point"
MARKER_LOWEST_POINT           = " lowest point"
MARKER_CENTROID               = " centroid"
MARKER_FLOW_START_POINT_1     = "Field "
MARKER_FLOW_START_POINT_2     = " flow start"
MARKER_BLIND_PIT              = "Blind pit"
MARKER_FIELD_BOUNDARY         = "Field boundary"
MARKER_ENTER_STREAM           = "Stream"
MARKER_ENTER_CULVERT          = "Culvert"
MARKER_ENTER_RIVER            = "Enter River Rother"
MARKER_ROAD                   = "Road"
MARKER_PATH                   = "Path"
MARKER_AT_STREAM              = "Enter stream"


# SHARED VARIABLES ======================================================================================================
progName = "FieldFlow"
progVer = "10 May 2019 QGIS3 version"
runTitle = ""

considerFieldObservations = ""
FillBlindPits = ""
considerStreams = ""
considerFieldBoundaries = ""
considerRoads = ""
considerTracks = ""

externalCRS = ""
GISPath = ""
dataInputFile = ""
textOutputFile = ""
fpOut = 0
haveRasterBackground = False

outFileFlowMarkerPoints = ""
outFileFlowMarkerPointsStyle = ""
outFileFlowMarkerPointsOpacity = 100
outFileFlowLines = ""
outFileFlowLinesStyle = ""
outFileFlowLinesOpacity = 100

windowWidth = 0
windowHeight = 0
windowMagnification = 0

fieldsWithFlow = 0
weightBoundary = 0
flowStartPoints = 0
thisStartPoint = 0

extentRect = 0

resolutionOfDEM = 0
distDiag = 0

searchDist = 0

cellWidthDEM = 0
cellHeightDEM = 0
xMinExtentDEM = 0
yMinExtentDEM = 0

blindPitFillMaxDepth = 0
blindPitFillArea = 0

vectorFileName = 0
vectorFileTitle = 0
vectorFileType = 0
vectorFileStyle = 0
vectorFileOpacity = 0
vectorFileCategory = 0

rasterFileName = 0
rasterFileTitle = 0
rasterFileStyle = 0
rasterFileOpacity = 0
rasterFileCategory = 0

outFlowMarkerPointLayer = 0
outFlowLineLayer = 0
outFlowLineLayerIndex = 0

vectorInputLayers = 0
vectorInputLayersCategory = 0
vectorInputLayerIndex = 0
rasterInputLayers = 0
rasterInputLayersCategory = 0
rasterInputData = 0

fieldObservationFlowFrom = 0
fieldObservationCategory = 0
fieldObservationValidCategories = 0
fieldObservationBehaviour = 0
fieldObservationValidBehaviours = 0
fieldObservationDescription = 0
fieldObservationFlowTo = 0

rasterPathCodes = 0

allFieldsFlowPath = 0
allFieldsFlowPathFieldCode = 0
allFieldsFieldObsAlreadyFollowed = 0

thisFieldFlowLine = 0
thisFieldFlowLineFieldCode = 0
thisFieldFieldObsAlreadyFollowed = 0
thisFieldRoadSegIDsTried = 0
thisFieldPathSegIDsTried = 0
thisFieldBoundarySegIDsTried = 0

defaultMessageDisplayTime = 5000
dividerLen = 150
dividerChar = '*'
#======================================================================================================================
