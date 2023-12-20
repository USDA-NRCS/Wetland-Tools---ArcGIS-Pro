from getpass import getuser
from os import path
from sys import argv, exc_info
from time import ctime
from traceback import format_exception

from arcpy import AddError, AddMessage, AddWarning, CheckExtension, CheckOutExtension, Describe, env, Exists, \
    GetParameterAsText, ListDatasets, ListFields, SetParameterAsText, SetProgressorLabel
from arcpy.analysis import Buffer, Clip as Clip_a
from arcpy.management import AddField, Clip as Clip_m, Compact, CalculateField, CopyFeatures, CopyRaster, \
    Delete, DeleteField, MakeFeatureLayer, MosaicToNewRaster, Project, ProjectRaster, SelectLayerByAttribute
from arcpy.mp import ArcGISProject, LayerFile
from arcpy.da import Editor
from arcpy.sa import Con, Contour, ExtractByMask, Fill, FocalStatistics, Minus, Hillshade, Slope, Times


def AddMsgAndPrint(msg, severity=0, textFilePath=None):
    ''' Log messages to text file and ESRI tool messages dialog.'''
    if textFilePath:
        with open(textFilePath, 'a+') as f:
            f.write(f"{msg}\n")
    if severity == 0:
        AddMessage(msg)
    elif severity == 1:
        AddWarning(msg)
    elif severity == 2:
        AddError(msg)


def errorMsg(tool_name):
    ''' Return exception details for logging, ignore sys.exit exceptions.'''
    exc_type, exc_value, exc_traceback = exc_info()
    exc_message = f"\t{format_exception(exc_type, exc_value, exc_traceback)[1]}\n\t{format_exception(exc_type, exc_value, exc_traceback)[-1]}"
    if exc_message.find('sys.exit') > -1:
        pass
    else:
        return f"\n\t------------------------- {tool_name} Tool Error -------------------------\n{exc_message}"


def removeScratchLayers(scratchLayers):
    ''' Delete layers in a given list.'''
    for lyr in scratchLayers:
        try:
            Delete(lyr)
        except:
            continue


def logBasicSettings(textFilePath, userWorkspace, dataExtent, inputDEMs, zUnits, interval):
    with open(textFilePath,'a+') as f:
        f.write('\n######################################################################\n')
        f.write('Executing Tool: Create Elevation Derivatives\n')
        f.write(f"User Name: {getuser()}\n")
        f.write(f"Date Executed: {ctime()}\n")
        f.write('User Parameters:\n')
        f.write(f"\tWorkspace: {userWorkspace}\n")
        f.write(f"\tSelected Extent: {dataExtent}\n")
        f.write(f"\tInput DEMs: {str(inputDEMs)}\n")
        if len (zUnits) > 0:
            f.write(f"\tElevation Z-units: {zUnits}\n")
        else:
            f.write('\tElevation Z-units: NOT SPECIFIED\n')
        if len(interval) > 0:
            f.write(f"\tContour Interval: {str(interval)} ft.\n")
        else:
            f.write('\tContour Interval: NOT SPECIFIED\n')


### Initial Tool Validation ###
try:
    aprx = ArcGISProject('CURRENT')
    map = aprx.listMaps('Determinations')[0]
except:
    AddMsgAndPrint('This tool must be run from an ArcGIS Pro project that was developed from the template distributed with this toolbox. Exiting!', 2)
    exit()

if CheckExtension('Spatial') == 'Available':
    CheckOutExtension('Spatial')
else:
    AddMsgAndPrint('Spatial Analyst Extension not enabled. Please enable Spatial Analyst from Project, Licensing, Configure licensing options. Exiting...\n', 2)
    exit()


### ESRI Environment Settings ###
env.overwriteOutput = True
env.resamplingMethod = 'BILINEAR'
env.pyramid = 'PYRAMIDS -1 BILINEAR DEFAULT 75 NO_SKIP'

### Input Parameters ###
sourceCLU = GetParameterAsText(0)                     # User selected project CLU
dataExtent = GetParameterAsText(1)
demFormat = GetParameterAsText(2)
inputDEMs = GetParameterAsText(3).split(';')          # user selected input DEMs
DEMcount = len(inputDEMs)
sourceService = GetParameterAsText(4)
sourceCellsize = GetParameterAsText(5)
zUnits = GetParameterAsText(6)                        # elevation z units of input DEM
interval = GetParameterAsText(7)                      # user defined contour interval (string)
demSR = GetParameterAsText(8)
cluSR = GetParameterAsText(9)
transform = GetParameterAsText(10)

try:
    slpLyr = LayerFile(path.join(path.join(path.dirname(argv[0]), 'layer_files'), 'Slope_Pct.lyrx')).listLayers()[0]
    dgLyr = LayerFile(path.join(path.join(path.dirname(argv[0]), 'layer_files'), 'Local_Depths.lyrx')).listLayers()[0]
    
    #### Set base path
    sourceCLU_path = Describe(sourceCLU).CatalogPath
    if sourceCLU_path.find('.gdb') > 0 and sourceCLU_path.find('Determinations') > 0 and sourceCLU_path.find('Site_CLU') > 0:
        basedataGDB_path = sourceCLU_path[:sourceCLU_path.find('.gdb')+4]
    else:
        AddMsgAndPrint('\nSelected Site CLU layer is not from a Determinations project folder. Exiting...', 2)
        exit()


    #### Do not run if an unsaved edits exist in the target workspace
    # Pro opens an edit session when any edit has been made and stays open until edits are committed with Save Edits.
    # Check for uncommitted edits and exit if found, giving the user a message directing them to Save or Discard them.
    workspace = basedataGDB_path
    edit = Editor(workspace)
    if edit.isEditing:
        AddMsgAndPrint('\nYou have an active edit session. Please Save or Discard edits and run this tool again. Exiting...', 2)
        exit()
    del workspace, edit


    #### Define Variables
    supportGDB = path.join(path.dirname(argv[0]), 'SUPPORT.gdb')
    scratchGDB = path.join(path.dirname(argv[0]), 'SCRATCH.gdb')

    basedataGDB_name = path.basename(basedataGDB_path)
    basedataFD_name = 'Layers'
    basedataFD = path.join(basedataGDB_path, basedataFD_name)
    userWorkspace = path.dirname(basedataGDB_path)
    projectName = path.basename(userWorkspace).replace(' ', '_')
    wetDir = path.join(userWorkspace, 'Wetlands')

    projectTract = path.join(basedataFD, 'Site_Tract')
    projectAOI = path.join(basedataFD, 'Site_AOI')
    projectAOI_B = path.join(basedataFD, 'project_AOI_B')
    projectExtent = path.join(basedataFD, 'Request_Extent')
    bufferDist = '500 Feet'
    bufferDistPlus = '550 Feet'
    
    projectDEM = path.join(basedataGDB_path, 'Site_DEM')
    projectHillshade = path.join(basedataGDB_path, 'Site_Hillshade')
    dgName = 'Site_Depth_Grid'
    projectDepths = path.join(basedataGDB_path, dgName)
    slpName = 'Site_Slope_Pct'
    projectSlope = path.join(basedataGDB_path, slpName)
    projectContours = path.join(basedataGDB_path, 'Site_Contours')

    pcsAOI = path.join(scratchGDB, 'pcsAOI')
    wgs_AOI = path.join(scratchGDB, 'AOI_WGS84')
    WGS84_DEM = path.join(scratchGDB, 'WGS84_DEM')
    tempDEM = path.join(scratchGDB, 'tempDEM')
    tempDEM2 = path.join(scratchGDB, 'tempDEM2')
    DEMagg = path.join(scratchGDB, 'aggDEM')
    DEMsmooth = path.join(scratchGDB, 'DEMsmooth')
    ContoursTemp = path.join(scratchGDB, 'ContoursTemp')
    extendedContours = path.join(scratchGDB, 'extendedContours')
    Temp_DEMbase = path.join(scratchGDB, 'Temp_DEMbase')
    Fill_DEMaoi = path.join(scratchGDB, 'Fill_DEMaoi')
    FilMinus = path.join(scratchGDB, 'FilMinus')

    # ArcPro Map Layer Names
    contoursOut = 'Site_Contours'
    demOut = 'Site_DEM'
    depthOut = 'Site_Depth_Grid'
    slopeOut = 'Site_Slope_Pct'
    hillshadeOut = 'Site_Hillshade'
    
    # Temp layers list for cleanup at the start and at the end
    tempLayers = [pcsAOI, wgs_AOI, WGS84_DEM, tempDEM, tempDEM2, DEMagg, DEMsmooth, ContoursTemp, extendedContours, Temp_DEMbase, Fill_DEMaoi, FilMinus]
    AddMsgAndPrint('Deleting Temp layers...')
    SetProgressorLabel('Deleting Temp layers...')
    removeScratchLayers(tempLayers)


    #### Set up log file path and start logging
    textFilePath = path.join(userWorkspace, f"{projectName}_log.txt")
    logBasicSettings(textFilePath, userWorkspace, dataExtent, inputDEMs, zUnits, interval)
    

    #### Create the projectAOI and projectAOI_B layers based on the choice selected by user input
    AddMsgAndPrint('\nBuffering selected extent...',0)
    SetProgressorLabel('Buffering selected extent...')
    if dataExtent == 'Request Extent':
        # Use the request extent to create buffers for use in data extraction
        Buffer(projectExtent, projectAOI, bufferDist, 'FULL', '', 'ALL', '')
        Buffer(projectExtent, projectAOI_B, bufferDistPlus, 'FULL', '', 'ALL', '')
    else:
        # Use the tract boundary to create the buffers for use in data extraction
        Buffer(projectTract, projectAOI, bufferDist, 'FULL', '', 'ALL', '')
        Buffer(projectTract, projectAOI_B, bufferDistPlus, 'FULL', '', 'ALL', '')


    #### Remove existing project DEM related layers from the Pro maps
    AddMsgAndPrint('\nRemoving layers from project maps, if present...\n',0)
    SetProgressorLabel('Removing layers from project maps, if present...')
    
    # Set starting layers to be removed
    mapLayersToRemove = [contoursOut, demOut, depthOut, slopeOut, hillshadeOut]
    
    # Remove the layers in the list
    try:
        for maps in aprx.listMaps():
            for lyr in maps.listLayers():
                if lyr.longName in mapLayersToRemove:
                    maps.removeLayer(lyr)
    except:
        pass


    #### Remove existing DEM related layers from the geodatabase
    AddMsgAndPrint('\nRemoving layers from project database, if present...\n',0)
    SetProgressorLabel('Removing layers from project database, if present...')

    # Set starting datasets to remove
    datasetsToRemove = [projectDEM, projectHillshade, projectDepths, projectSlope, projectContours]

    # Remove the datasets in the list
    for dataset in datasetsToRemove:
        if Exists(dataset):
            try:
                Delete(dataset)
            except:
                pass


    #### Process the input DEMs
    AddMsgAndPrint('\nProcessing the input DEM(s)...',0)
    SetProgressorLabel('Processing the input DEM(s)...')

    # Extract and process the DEM if it's an image service
    if demFormat == 'NRCS Image Service':
        if sourceCellsize == '':
            AddMsgAndPrint('\nAn output DEM cell size was not specified. Exiting...',2)
            exit()
        else:
            AddMsgAndPrint('\nProjecting AOI to match input DEM...',0)
            SetProgressorLabel('Projecting AOI to match input DEM...')
            wgs_CS = demSR
            Project(projectAOI_B, wgs_AOI, wgs_CS)
            
            AddMsgAndPrint('\nDownloading DEM data...',0)
            SetProgressorLabel('Downloading DEM data...')
            aoi_ext = Describe(wgs_AOI).extent
            xMin = aoi_ext.XMin
            yMin = aoi_ext.YMin
            xMax = aoi_ext.XMax
            yMax = aoi_ext.YMax
            clip_ext = str(xMin) + ' ' + str(yMin) + ' ' + str(xMax) + ' ' + str(yMax)
            Clip_m(sourceService, clip_ext, WGS84_DEM, '', '', '', 'NO_MAINTAIN_EXTENT')

            AddMsgAndPrint('\nProjecting downloaded DEM...',0)
            SetProgressorLabel('Projecting downloaded DEM...')
            ProjectRaster(WGS84_DEM, tempDEM, cluSR, 'BILINEAR', sourceCellsize)

    # Else, extract the local file DEMs
    else:
        # Manage spatial references
        env.outputCoordinateSystem = cluSR
        if transform != '':
            env.geographicTransformations = transform
        else:
            env.geographicTransformations = 'WGS_1984_(ITRF00)_To_NAD_1983'
        
        # Clip out the DEMs that were entered
        AddMsgAndPrint('\tExtracting input DEM(s)...',0)
        SetProgressorLabel('Extracting input DEM(s)...')
        x = 0
        DEMlist = []
        while x < DEMcount:
            raster = inputDEMs[x].replace("'", '')
            desc = Describe(raster)
            raster_path = desc.CatalogPath
            sr = desc.SpatialReference
            units = sr.LinearUnitName
            if units == 'Meter':
                units = 'Meters'
            elif units == 'Foot':
                units = 'Feet'
            elif units == 'Foot_US':
                units = 'Feet'
            else:
                AddMsgAndPrint('\nHorizontal units of one or more input DEMs do not appear to be feet or meters! Exiting...',2)
                exit()
            outClip = tempDEM + '_' + str(x)
            try:
                extractedDEM = ExtractByMask(raster_path, projectAOI_B)
                extractedDEM.save(outClip)
            except:
                AddMsgAndPrint('\nOne or more input DEMs may have a problem! Please verify that the input DEMs cover the tract area and try to run again. Exiting...',2)
                exit()
            if x == 0:
                mosaicInputs = '' + str(outClip) + ''
            else:
                mosaicInputs = mosaicInputs + ';' + str(outClip)
            DEMlist.append(str(outClip))
            x += 1
            del sr

        cellsize = 0
        # Determine largest cell size
        for raster in DEMlist:
            desc = Describe(raster)
            sr = desc.SpatialReference
            cellwidth = desc.MeanCellWidth
            if cellwidth > cellsize:
                cellsize = cellwidth
            del sr

        # Merge the DEMs
        if DEMcount > 1:
            AddMsgAndPrint('\nMerging multiple input DEM(s)...',0)
            SetProgressorLabel('Merging multiple input DEM(s)...')
            MosaicToNewRaster(mosaicInputs, scratchGDB, 'tempDEM', '#', '32_BIT_FLOAT', cellsize, '1', 'MEAN', '#')

        # Else just convert the one input DEM to become the tempDEM
        else:
            AddMsgAndPrint('\nOnly one input DEM detected. Carrying extract forward for final DEM processing...',0)
            firstDEM = DEMlist[0]
            CopyRaster(firstDEM, tempDEM)

        # Delete clippedDEM files
        AddMsgAndPrint('\nDeleting temp DEM file(s)...',0)
        SetProgressorLabel('Deleting temp DEM file(s)...')
        for raster in DEMlist:
            Delete(raster)

        
    # Gather info on the final temp DEM
    desc = Describe(tempDEM)
    sr = desc.SpatialReference
    # linear units should now be meters, since outputs were UTM zone specified
    units = sr.LinearUnitName

    if sr.Type == 'Projected':
        if zUnits == 'Meters':
            Zfactor = 1
        elif zUnits == 'Meter':
            Zfactor = 1
        elif zUnits == 'Feet':
            Zfactor = 0.3048
        elif zUnits == 'Inches':
            Zfactor = 0.0254
        elif zUnits == 'Centimeters':
            Zfactor = 0.01
        else:
            AddMsgAndPrint('\nZunits were not selected at runtime....Exiting!',2)
            exit()

        AddMsgAndPrint('\tDEM Projection Name: ' + sr.Name,0)
        AddMsgAndPrint('\tDEM XY Linear Units: ' + units,0)
        AddMsgAndPrint('\tDEM Elevation Values (Z): ' + zUnits,0)
        AddMsgAndPrint('\tZ-factor for Slope Modeling: ' + str(Zfactor),0)
        AddMsgAndPrint('\tDEM Cell Size: ' + str(desc.MeanCellWidth) + ' x ' + str(desc.MeanCellHeight) + ' ' + units,0)

    else:
        AddMsgAndPrint('\n\n\t' + path.basename(tempDEM) + ' is not in a projected Coordinate System! Exiting...',2)
        exit()

    # Clip out the DEM with extended buffer for temp processing and standard buffer for final DEM display
    AddMsgAndPrint('\nClipping project DEM to buffered extent...',0)
    SetProgressorLabel('Clipping project DEM to buffered extent...')
    Clip_m(tempDEM, '', projectDEM, projectAOI, '', 'ClippingGeometry')

    # Create a temporary smoothed DEM to use for creating a slope layer and a contours layer
    AddMsgAndPrint('\tCreating a 3-meter pixel resolution version of the DEM for use in contours and slopes...',0)
    SetProgressorLabel('Creating 3-meter resolution DEM...')
    ProjectRaster(tempDEM, DEMagg, cluSR, 'BILINEAR', '3', '#', '#', '#')

    AddMsgAndPrint('\tSmoothing the DEM with Focal Statistics...',0)
    SetProgressorLabel('Smoothing DEM with Focal Stats...')
    outFocalStats = FocalStatistics(DEMagg, 'RECTANGLE 3 3 CELL', 'MEAN', 'DATA')
    outFocalStats.save(DEMsmooth)
    AddMsgAndPrint('\tSuccessful',0)

    # Create Slope Layer
    # Use Zfactor to get accurate slope creation. Do not assume this Zfactor with contour processing later
    AddMsgAndPrint('\nCreating Slope...',0)
    SetProgressorLabel('Creating Slope...')
    outSlope = Slope(DEMsmooth, 'PERCENT_RISE', Zfactor)
    Clip_m(outSlope, '', projectSlope, projectAOI, '', 'ClippingGeometry')
    AddMsgAndPrint('\tSuccessful',0)


    #### Create contours
    # Use an appropriate z factor to always get contour results in feet.
    # Use a new variable, cZfactor (contours Z factor) to distinguish from Zfactor used for slope above
    cZfactor = 0
    if zUnits == 'Meters':
        cZfactor = 3.28084
    elif zUnits == 'Centimeters':
        cZfactor = 0.0328084
    elif zUnits == 'Inches':
        cZfactor = 0.0833333
    else:
        cZfactor = 1

    # Create Contours
    AddMsgAndPrint('\nCreating ' + str(interval) + ' foot Contours from DEM using a Z-factor of ' + str(cZfactor) + '...',0)
    SetProgressorLabel('Creating contours...')
    Contour(DEMsmooth, ContoursTemp, interval, '', cZfactor)
    AddField(ContoursTemp, 'Index', 'DOUBLE', '', '', '', '', 'NULLABLE', 'NON_REQUIRED', '')

    # Delete temporary feature layer of contours if it exists from previous runs
    if Exists('ContourLYR'):
        try:
            Delete('ContourLYR')
        except:
            pass
        
    # Make the temporary contours feature layer for indexing calculations
    MakeFeatureLayer(ContoursTemp,'ContourLYR','','','')

    # every 5th contour will be indexed to 1
    expression = "MOD( \"CONTOUR\"," + str(float(interval) * 5) + ") = 0"
    SelectLayerByAttribute('ContourLYR', 'NEW_SELECTION', expression)
    indexValue = 1
    CalculateField('ContourLYR', 'Index', indexValue, 'PYTHON_9.3')

    # All other contours will be indexed to 0
    SelectLayerByAttribute('ContourLYR', 'SWITCH_SELECTION', '')
    indexValue = 0
    CalculateField('ContourLYR', 'Index', indexValue, 'PYTHON_9.3')

    # Clear selection and write all contours to final feature class via a clip
    SelectLayerByAttribute('ContourLYR','CLEAR_SELECTION','')
    CopyFeatures('ContourLYR', extendedContours)
    Clip_a(extendedContours, projectAOI, projectContours)

    # Delete unwanted 'ID' remnant field
    if len(ListFields(projectContours,'Id')) > 0:
        try:
            DeleteField(Contours,'Id')
        except:
            pass

    Delete('ContourLYR')
    
    AddMsgAndPrint('\tSuccessful',0)


    #### Create Hillshade and Depth Grid
    AddMsgAndPrint('\nCreating Hillshade...',0)
    SetProgressorLabel('Creating Hillshade...')
    outHillshade = Hillshade(projectDEM, '315', '45', '#', Zfactor)
    outHillshade.save(projectHillshade)
    AddMsgAndPrint('\tSuccessful',0)

    AddMsgAndPrint('\nCreating Depth Grid...',0)
    SetProgressorLabel('Creating Depth Grid...')
    fill = False
    try:
        # Fills sinks in projectDEM to remove small imperfections in the data.
        # Convert the projectDEM to a raster with z units in feet to create this layer
        Temp_DEMbase = Times(projectDEM, cZfactor)
        Fill_DEMaoi = Fill(Temp_DEMbase, '')
        fill = True
    except:
        pass
    
    if fill:
        FilMinus = Minus(Fill_DEMaoi, Temp_DEMbase)

        # Create a Depth Grid whereby any pixel with a difference is written to a new raster
        tempDepths = Con(FilMinus, FilMinus, '', 'VALUE > 0')
        tempDepths.save(projectDepths)

        # Delete temp data
        del tempDepths

        AddMsgAndPrint('\tSuccessful',0)


    #### Delete temp data
    AddMsgAndPrint('\nDeleting temp data...' ,0)
    SetProgressorLabel('Deleting temp data...')
    removeScratchLayers(tempLayers)


    #### Add layers to Pro Map
    AddMsgAndPrint('\nAdding layers to map...',0)
    SetProgressorLabel('Adding layers to map...')
    lyr_list = map.listLayers()
    lyr_name_list = []
    for lyr in lyr_list:
        lyr_name_list.append(lyr.longName)

    SetParameterAsText(11, projectContours)

    if dgName not in lyr_name_list:
        dgLyr_cp = dgLyr.connectionProperties
        dgLyr_cp['connection_info']['database'] = basedataGDB_path
        dgLyr_cp['dataset'] = dgName
        dgLyr.updateConnectionProperties(dgLyr.connectionProperties, dgLyr_cp)
        map.addLayer(dgLyr)

    SetParameterAsText(13, projectDEM)
    SetParameterAsText(14, projectHillshade)

    if slpName not in lyr_name_list:
        slpLyr_cp = slpLyr.connectionProperties
        slpLyr_cp['connection_info']['database'] = basedataGDB_path
        slpLyr_cp['dataset'] = slpName
        slpLyr.updateConnectionProperties(slpLyr.connectionProperties, slpLyr_cp)
        map.addLayer(slpLyr)


    #### Clean up
    # Look for and delete anything else that may remain in the installed SCRATCH.gdb
    startWorkspace = env.workspace
    env.workspace = scratchGDB
    dss = []
    for ds in ListDatasets('*'):
        dss.append(path.join(scratchGDB, ds))
    for ds in dss:
        if Exists(ds):
            try:
                Delete(ds)
            except:
                pass
    env.workspace = startWorkspace
    del startWorkspace

    
    #### Compact FGDB
    try:
        AddMsgAndPrint('\nCompacting File Geodatabase...' ,0)
        SetProgressorLabel('Compacting File Geodatabase...')
        Compact(basedataGDB_path)
        AddMsgAndPrint('\tSuccessful',0)
    except:
        pass


except SystemExit:
    pass

except:
    errorMsg('Create Elevation Derivatives')