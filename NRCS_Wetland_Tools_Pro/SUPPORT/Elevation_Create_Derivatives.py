## ===============================================================================================================
## Name:    Elevation - Create Derivatives
## Purpose: Create Project based DEM, Hillshade, Slope, Depth Grid, and Contours
##
## Authors: Chris Morse
##          GIS Specialist
##          Indianapolis State Office
##          USDA-NRCS
##          chris.morse@usda.gov
##          317.295.5849
##
## Created: 11/10/2020
##
## ===============================================================================================================
## Changes
## ===============================================================================================================
##
## rev. 11/10/2020
## -Start revisions of Create Reference Data ArcMap tool to National Wetlands Tool in ArcGIS Pro.
##
## rev. 08/24/2021
## -Updated to integrate DEM processing from Create Reference Data as part of a tool split of soils and elevation
## -Integrated the previous updates from Create Reference Data:
##
##      rev. 03/03/2021
##      -Adjust extent within which to generate reference data layers based on user specified input parameter for full
##      tract or request extent.
##
##      rev. 06/11/2021
##      -Fixed bug that was copying and processing entire input DEM when only one input DEM was specified.
##      -Update method to add Slope and Depth Grid to map so they load with the correct legend.
## 
##
## ===============================================================================================================
from getpass import getuser
from os import path
from sys import argv
from time import ctime

from arcpy import CheckExtension, CheckOutExtension, Describe, env, Exists, GetParameterAsText, ListDatasets, \
    ListFields, SetParameterAsText, SetProgressorLabel
from arcpy.analysis import Buffer, Clip as Clip_a
from arcpy.management import AddField, CalculateField, Clip, Compact, CopyFeatures, CopyRaster, Delete, DeleteField, \
    MakeFeatureLayer, MosaicToNewRaster, Project, ProjectRaster, SelectLayerByAttribute
from arcpy.mp import ArcGISProject
from arcpy.da import Editor
from arcpy.sa import Con, Contour, ExtractByMask, Fill, FocalStatistics, Hillshade, Minus, Slope, Times
from arcpy.mp import ArcGISProject, LayerFile

from wetland_utils import AddMsgAndPrint, deleteTempLayers, errorMsg


def logBasicSettings():    
    with open(textFilePath, 'a+') as f:
        f.write('\n######################################################################\n')
        f.write('Executing Elevation - Create Derivatives tool...\n')
        f.write(f"User Name: {getuser()}\n")
        f.write(f"Date Executed: {ctime()}\n")
        f.write('User Parameters:\n')
        f.write(f"\tWorkspace: {userWorkspace}\n")
        f.write(f"\tSelected Extent: {dataExtent}\n")
        f.write(f"\tInput DEMs: {str(inputDEMs)}\n")
        if len (zUnits) > 0:
            f.write(f"\tElevation Z-units: {zUnits}\n")
        else:
            f.write("\tElevation Z-units: NOT SPECIFIED\n")
        if len(interval) > 0:
            f.write(f"\tContour Interval: {str(interval)} ft.\n")
        else:
            f.write('\tContour Interval: NOT SPECIFIED\n')


#### Check out Spatial Analyst license
if CheckExtension('Spatial') == 'Available':
    CheckOutExtension('Spatial')
else:
    AddMsgAndPrint('Spatial Analyst Extension not enabled. Please enable Spatial Analyst from Project, Licensing, COnfigure licensing options. Exiting...\n', 2)
    exit()


### ESRI Environment Settings ###
env.overwriteOutput = True
env.resamplingMethod = 'BILINEAR'
env.pyramid = 'PYRAMIDS -1 BILINEAR DEFAULT 75 NO_SKIP'

# Test for Pro project.
try:
    aprx = ArcGISProject('CURRENT')
    m = aprx.listMaps('Determinations')[0]
except:
    AddMsgAndPrint('\nThis tool must be run from a active ArcGIS Pro project that was developed from the template distributed with this toolbox. Exiting...\n', 2)
    exit()


try:
    #### Inputs
    sourceCLU = GetParameterAsText(0)                     # User selected project CLU
    dataExtent = GetParameterAsText(1)
    demFormat = GetParameterAsText(2)
    inputDEMs = GetParameterAsText(3).split(';')          # user selected input DEMs
    DEMcount = len(inputDEMs)
    nrcsService = GetParameterAsText(4)
    externalService = GetParameterAsText(5)
    sourceCellsize = GetParameterAsText(6)
    zUnits = GetParameterAsText(7)                        # elevation z units of input DEM
    interval = GetParameterAsText(8)                      # user defined contour interval (string)
    demSR = GetParameterAsText(9)
    cluSR = GetParameterAsText(10)
    transform = GetParameterAsText(11)
    depthGrid = GetParameterAsText(12)

    slpLyr = LayerFile(path.join(path.dirname(argv[0]), 'layer_files', 'Slope_Pct.lyrx')).listLayers()[0]
    dgLyr = LayerFile(path.join(path.dirname(argv[0]), 'layer_files', 'Local_Depths.lyrx')).listLayers()[0]

                
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
        AddMsgAndPrint('\nYou have an active edit session. Please Save or Discard Edits and then run this tool again. Exiting...', 2)
        exit()
    del workspace, edit


    #### Define Variables
    supportGDB = path.join(path.dirname(argv[0]), 'SUPPORT.gdb')
    scratchGDB = path.join(path.dirname(argv[0]), 'SCRATCH.gdb')
    referenceLayers = path.join(path.dirname(path.dirname(argv[0])), 'Reference_Layers')

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

    # If NRCS Image Service selected, set path to lyrx file
    if '0.5m' in nrcsService:
        sourceService = path.join(referenceLayers, 'NRCS Bare Earth 0.5m.lyrx')
    elif '1m' in nrcsService:
        sourceService = path.join(referenceLayers, 'NRCS Bare Earth 1m.lyrx')
    elif '2m' in nrcsService:
        sourceService = path.join(referenceLayers, 'NRCS Bare Earth 2m.lyrx')
    elif '3m' in nrcsService:
        sourceService = path.join(referenceLayers, 'NRCS Bare Earth 3m.lyrx')
    elif externalService != '':
        sourceService = externalService

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
    deleteTempLayers(tempLayers)


    #### Set up log file path and start logging
    textFilePath = path.join(userWorkspace, f"{projectName}_log.txt")
    logBasicSettings()
    

    #### Create the projectAOI and projectAOI_B layers based on the choice selected by user input
    AddMsgAndPrint('\nBuffering selected extent...')
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
    AddMsgAndPrint('\nRemoving layers from project maps, if present...\n')
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
    AddMsgAndPrint('\nRemoving layers from project database, if present...\n')
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
    AddMsgAndPrint('\nProcessing the input DEM(s)...')
    SetProgressorLabel('Processing the input DEM(s)...')

    # Extract and process the DEM if it's an image service
    if demFormat in ['NRCS Image Service', 'External Image Service']:
        if sourceCellsize == '':
            AddMsgAndPrint('\nAn output DEM cell size was not specified. Exiting...', 2)
            exit()
        else:
            AddMsgAndPrint('\nProjecting AOI to match input DEM...')
            SetProgressorLabel('Projecting AOI to match input DEM...')
            #wgs_CS = SpatialReference(4326)  # WGS 1984 Geographic
            #wgs_CS = SpatialReference(3857)   # Web Mercator Auxilliary Sphere
            wgs_CS = demSR
            Project(projectAOI_B, wgs_AOI, wgs_CS)
            
            AddMsgAndPrint('\nDownloading DEM data...')
            SetProgressorLabel('Downloading DEM data...')
            aoi_ext = Describe(wgs_AOI).extent
            xMin = aoi_ext.XMin
            yMin = aoi_ext.YMin
            xMax = aoi_ext.XMax
            yMax = aoi_ext.YMax
            clip_ext = f"{str(xMin)} {str(yMin)} {str(xMax)} {str(yMax)}"
            Clip(sourceService, clip_ext, WGS84_DEM, '', '', '', 'NO_MAINTAIN_EXTENT')

            AddMsgAndPrint('\nProjecting downloaded DEM...')
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
        AddMsgAndPrint('\tExtracting input DEM(s)...')
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
                AddMsgAndPrint('\nHorizontal units of one or more input DEMs do not appear to be feet or meters! Exiting...', 2)
                exit()
            outClip = f"{tempDEM}_{str(x)}"
            try:
                extractedDEM = ExtractByMask(raster_path, projectAOI_B)
                extractedDEM.save(outClip)
            except:
                AddMsgAndPrint('\nOne or more input DEMs may have a problem! Please verify that the input DEMs cover the tract area and try to run again. Exiting...', 2)
                exit()
            if x == 0:
                mosaicInputs = str(outClip)
            else:
                mosaicInputs = f"{mosaicInputs};{str(outClip)}"
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
            AddMsgAndPrint('\nMerging multiple input DEM(s)...')
            SetProgressorLabel('Merging multiple input DEM(s)...')
            MosaicToNewRaster(mosaicInputs, scratchGDB, 'tempDEM', '#', '32_BIT_FLOAT', cellsize, '1', 'MEAN', '#')

        # Else just convert the one input DEM to become the tempDEM
        else:
            AddMsgAndPrint('\nOnly one input DEM detected. Carrying extract forward for final DEM processing...')
            firstDEM = DEMlist[0]
            CopyRaster(firstDEM, tempDEM)

        # Delete clippedDEM files
        AddMsgAndPrint('\nDeleting temp DEM file(s)...')
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
            AddMsgAndPrint('\nZunits were not selected at runtime....Exiting!', 2)
            exit()

        AddMsgAndPrint(f"\tDEM Projection Name: {sr.Name}")
        AddMsgAndPrint(f"\tDEM XY Linear Units: {units}")
        AddMsgAndPrint(f"\tDEM Elevation Values (Z): {zUnits}")
        AddMsgAndPrint(f"\tZ-factor for Slope Modeling: {str(Zfactor)}")
        AddMsgAndPrint(f"\tDEM Cell Size: {str(desc.MeanCellWidth)} x {str(desc.MeanCellHeight)} units")

    else:
        AddMsgAndPrint(f"\n\n\t{path.basename(tempDEM)} is not in a projected Coordinate System! Exiting...", 2)
        exit()

    # Clip out the DEM with extended buffer for temp processing and standard buffer for final DEM display
    AddMsgAndPrint('\nClipping project DEM to buffered extent...')
    SetProgressorLabel('Clipping project DEM to buffered extent...')
    Clip(tempDEM, '', projectDEM, projectAOI, '', 'ClippingGeometry')

    # Create a temporary smoothed DEM to use for creating a slope layer and a contours layer
    AddMsgAndPrint('\tCreating a 3-meter pixel resolution version of the DEM for use in contours and slopes...')
    SetProgressorLabel('Creating 3-meter resolution DEM...')
    ProjectRaster(tempDEM, DEMagg, cluSR, 'BILINEAR', '3', '#', '#', '#')

    AddMsgAndPrint('\tSmoothing the DEM with Focal Statistics...')
    SetProgressorLabel('Smoothing DEM with Focal Stats...')
    outFocalStats = FocalStatistics(DEMagg, 'RECTANGLE 3 3 CELL', 'MEAN', 'DATA')
    outFocalStats.save(DEMsmooth)
    AddMsgAndPrint('\tSuccessful')

    # Create Slope Layer
    # Use Zfactor to get accurate slope creation. Do not assume this Zfactor with contour processing later
    AddMsgAndPrint('\nCreating Slope...')
    SetProgressorLabel('Creating Slope...')
    outSlope = Slope(DEMsmooth, 'PERCENT_RISE', Zfactor)
    Clip(outSlope, '', projectSlope, projectAOI, '', 'ClippingGeometry')
    AddMsgAndPrint('\tSuccessful')

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
    AddMsgAndPrint(f"\nCreating {str(interval)} foot Contours from DEM using a Z-factor of {str(cZfactor)}...")
    SetProgressorLabel('Creating contours...')
    Contour(DEMsmooth, ContoursTemp, interval, '', cZfactor)
    AddField(ContoursTemp, 'Index', 'DOUBLE', '', '', '', '', 'NULLABLE', 'NON_REQUIRED')

    # Delete temporary feature layer of contours if it exists from previous runs
    if Exists('ContourLYR'):
        try:
            Delete('ContourLYR')
        except:
            pass
        
    # Make the temporary contours feature layer for indexing calculations
    MakeFeatureLayer(ContoursTemp, 'ContourLYR')

    # every 5th contour will be indexed to 1
    expression = "MOD( \"CONTOUR\"," + str(float(interval) * 5) + ") = 0"
    SelectLayerByAttribute('ContourLYR', 'NEW_SELECTION', expression)
    indexValue = 1
    CalculateField('ContourLYR', 'Index', indexValue, 'PYTHON_9.3')
    del indexValue
    del expression

    # All other contours will be indexed to 0
    SelectLayerByAttribute('ContourLYR', 'SWITCH_SELECTION')
    indexValue = 0
    CalculateField('ContourLYR', 'Index', indexValue, 'PYTHON_9.3')
    del indexValue

    # Clear selection and write all contours to final feature class via a clip
    SelectLayerByAttribute('ContourLYR', 'CLEAR_SELECTION')
    CopyFeatures('ContourLYR', extendedContours)
    Clip_a(extendedContours, projectAOI, projectContours)

    # Delete unwanted 'ID' remnant field
    if len(ListFields(projectContours, 'Id')) > 0:
        try:
            DeleteField(Contours, 'Id') #Undefined variable here??
        except:
            pass

    Delete('ContourLYR')
    
    AddMsgAndPrint('\tSuccessful')


    #### Create Hillshade and Depth Grid
    AddMsgAndPrint('\nCreating Hillshade...')
    SetProgressorLabel('Creating Hillshade...')
    outHillshade = Hillshade(projectDEM, '315', '45', '#', Zfactor)
    outHillshade.save(projectHillshade)
    AddMsgAndPrint('\tSuccessful')

    if depthGrid == 'true':
        AddMsgAndPrint('\nCreating Depth Grid...')
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

            AddMsgAndPrint('\tSuccessful')


    #### Delete temp data
    AddMsgAndPrint('\nDeleting temp data...' )
    SetProgressorLabel('Deleting temp data...')
    deleteTempLayers(tempLayers)


    #### Add layers to Pro Map
    AddMsgAndPrint('\nAdding layers to map...')
    SetProgressorLabel('Adding layers to map...')
    lyr_list = m.listLayers()
    lyr_name_list = []
    for lyr in lyr_list:
        lyr_name_list.append(lyr.longName)

    SetParameterAsText(13, projectContours)

    if depthGrid == 'true':
        if dgName not in lyr_name_list:
            dgLyr_cp = dgLyr.connectionProperties
            dgLyr_cp['connection_info']['database'] = basedataGDB_path
            dgLyr_cp['dataset'] = dgName
            dgLyr.updateConnectionProperties(dgLyr.connectionProperties, dgLyr_cp)
            m.addLayer(dgLyr)

    SetParameterAsText(14, projectDEM)
    SetParameterAsText(15, projectHillshade)

    if slpName not in lyr_name_list:
        slpLyr_cp = slpLyr.connectionProperties
        slpLyr_cp['connection_info']['database'] = basedataGDB_path
        slpLyr_cp['dataset'] = slpName
        slpLyr.updateConnectionProperties(slpLyr.connectionProperties, slpLyr_cp)
        m.addLayer(slpLyr)


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
        AddMsgAndPrint('\nCompacting File Geodatabase...' )
        SetProgressorLabel('Compacting File Geodatabase...')
        Compact(basedataGDB_path)
        AddMsgAndPrint('\tSuccessful')
    except:
        pass


except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint('Interruption requested. Exiting...')

except:
    errorMsg()
