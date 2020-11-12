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
## Start revisions of Create Reference Data ArcMap tool to National Wetlands Tool in ArcGIS Pro.
##
## ===============================================================================================================
## ===============================================================================================================    
def AddMsgAndPrint(msg, severity=0):
    # Adds tool message to the geoprocessor and text file log.
    
    print(msg)
    
    try:
        f = open(textFilePath,'a+')
        f.write(msg + " \n")
        f.close
        del f

        if severity == 0:
            arcpy.AddMessage(msg)
        elif severity == 1:
            arcpy.AddWarning(msg)
        elif severity == 2:
            arcpy.AddError(msg)
        
    except:
        pass

## ===============================================================================================================
def errorMsg():
    # Error message handling
    try:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        theMsg = "\t" + traceback.format_exception(exc_type, exc_value, exc_traceback)[1] + "\n\t" + traceback.format_exception(exc_type, exc_value, exc_traceback)[-1]

        if theMsg.find("exit") > -1:
            AddMsgAndPrint("\n\n")
            pass
        else:
            AddMsgAndPrint(theMsg,2)

    except:
        AddMsgAndPrint("Unhandled error in unHandledException method", 2)
        pass
        
## ===============================================================================================================
def logBasicSettings():    
    # record basic user inputs and settings to log file for future purposes
    import getpass, time
    f = open(textFilePath,'a+')
    f.write("\n######################################################################\n")
    f.write("Executing Elevation - Create Derivatives tool...\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("User Parameters:\n")
    f.write("\tWorkspace: " + userWorkspace + "\n")
    f.write("\tInput DEMs: " + str(inputDEMs) + "\n")
    if len (zUnits) > 0:
        f.write("\tElevation Z-units: " + zUnits + "\n")
    else:
        f.write("\tElevation Z-units: NOT SPECIFIED\n")
    if len(interval) > 0:
        f.write("\tContour Interval: " + str(interval) + " ft.\n")
    else:
        f.write("\tContour Interval: NOT SPECIFIED\n")
    f.close
    del f

## ===============================================================================================================
def changeSource(cur_lyr, new_ws='', new_fd='', new_fc=''):
    # This function will update the input layer through the CIM to change connection properties for the layer
    # utilizing the provided new workspace path, new feature dataset name, or new feature class name if they were
    # provided to the function.
    # Requires a layer object from a map within an APRX.
    # cur_lyr:  A layer in a map in the current APRX.
    # new_ws:   A path to a folder or workspace (e.g. file geodatabase) that contains the desired feature class.
    # new_fd:   A string that specifies an existing feature dataset name in the specified workspace.
    # new_fc:   A string that represents an existing feature class name in the specified workspace.
    
    lyrCIM = cur_lyr.getDefinition('V2')
    dc = lyrCIM.featureTable.dataConnection

    if new_ws != '':
        if arcpy.Exists(new_ws):
            dc.workspaceConnectionString = 'DATABASE=' + new_ws

    if new_fd != '':
        if new_ws != '':
            fd_path = new_ws + os.sep + new_fd
        else:
            fd_path = dc.workspaceConnectionString[:9] + os.sep + new_fd

        if arcpy.Exists(fd_path):
            dc.featureDataset = new_fd

    if new_fc != '':
        if new_ws!= '':
            if new_fd != '':
                fc_path = new_ws + os.sep + new_fd + os.sep + new_fc
            else:
                fc_path = new_ws + os.sep + dc.featureDataset + os.sep + new_fc
        else:
            if new_fd != '':
                fc_path = dc.workspaceConnectionString[:9] + os.sep + new_fd + os.sep + new_fc
            else:
                fc_path = dc.workspaceConnectionString[:9] + os.sep + dc.featureDataset + os.sep + new_fc

        if arcpy.Exists(fc_path):
            dc.dataset = new_fc

    if new_ws != '' or new_fd != '' or new_fc != '':
        cur_lyr.setDefinition(lyrCIM)

## ===============================================================================================================
def deleteTempLayers(lyrs):
    for lyr in lyrs:
        if arcpy.Exists(lyr)
            try:
                arcpy.Delete_management(lyr)
            except:
                pass
            
## ===============================================================================================================
#### Import system modules
import arcpy, sys, os, traceback


#### Check out Spatial Analyst license
if arcpy.CheckExtension("Spatial") == "Available":
    arcpy.CheckOutExtension("Spatial")
else:
    arcpy.AddError("Spatial Analyst Extension not enabled. Please enable Spatial Analyst from Project, Licensing, COnfigure licensing options. Exiting...\n")
    exit()


#### Update Environments
arcpy.AddMessage("Setting Environments...\n")

# Set overwrite flag
arcpy.env.overwriteOutput = True

# Test for Pro project.
try:
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    m = aprx.listMaps("Determinations")[0]
except:
    arcpy.AddError("\nThis tool must be from an active ArcGIS Pro project. Exiting...\n")
    exit()


#### Main procedures
try:
    #### Inputs
    arcpy.AddMessage("Reading inputs...\n")
    sourceCLU = arcpy.GetParameterAsText(0)                     # User selected project CLU
    inputDEMs = arcpy.GetParameterAsText(1).split(";")          # user selected input DEMs
    DEMcount = len(inputDEMs)
    zUnits = arcpy.GetParameterAsText(2)                        # elevation z units of input DEM
    interval = arcpy.GetParameterAsText(3)                      # user defined contour interval (string)
    demSR = arcpy.GetParameterAsText(4)
    cluSR = arcpy.GetParameterAsText(5)
    transform = arcpy.GetParameterAsText(6)
    
    #suLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(8))
    #ropLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(9))
    #drainLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(10))
    #extentLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(11))


    #### Manage spatial references
    arcpy.env.outputCoordinateSystem = cluSR
    if transform != '':
        arcpy.env.geographicTransformations = transform
    else:
        arcpy.env.geographicTransformations = "WGS_1984_(ITRF00)_To_NAD_1983"
    arcpy.env.resamplingMethod = "BILINEAR"
    arcpy.env.pyramid = "PYRAMIDS -1 BILINEAR DEFAULT 75 NO_SKIP"

                
    #### Set base path
    sourceCLU_path = arcpy.Describe(sourceDefine).CatalogPath
    if sourceCLU_path.find('.gdb') > 0 and sourceCLU_path.find('Determinations') > 0 and sourceCLU_path.find('CLU_') > 0:
        basedataGDB_path = sourceCLU_path[:sourceCLU_path.find('.gdb')+4]
    else:
        arcpy.AddError("\nSelected project CLU layer is not from a Determinations project folder. Exiting...")
        exit()


    #### Do not run if an unsaved edits exist in the target workspace
    # Pro opens an edit session when any edit has been made and stays open until edits are committed with Save Edits.
    # Check for uncommitted edits and exit if found, giving the user a message directing them to Save or Discard them.
    workspace = basedataGDB_path
    edit = arcpy.da.Editor(workspace)
    if edit.isEditing:
        arcpy.AddError("\nYou have an active edit session. Please Save or Discard Edits and then run this tool again. Exiting...")
        exit()
    del workspace, edit


    #### Define Variables
    arcpy.AddMessage("Setting variables...\n")
    supportGDB = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb")
    scratchGDB = os.path.join(os.path.dirname(sys.argv[0]), "SCRATCH.gdb")

    basedataGDB_name = os.path.basename(basedataGDB_path)
    basedataFD_name = "Layers"
    basedataFD = basedataGDB_path + os.sep + basedataFD_name
    demFD_name = "DEM_Vectors"
    demFD = basedataGDB_path + os.sep + demFD_name
    userWorkspace = os.path.dirname(basedataGDB_path)
    projectName = os.path.basename(userWorkspace).replace(" ", "_")
    wetDir = userWorkspace + os.sep + "Wetlands"

    projectTract = basedataFD + os.sep + "Tract_" + projectName
    projectTractB = basedataFD + os.sep + "Tract_Buffer_" + projectName
    projectAOI = basedataFD + os.sep + "AOI_" + projectName
    extentName = "Extent_" + projectName
    projectExtent = basedataFD + os.sep + extentName

    projectDEM = basedataGDB_path + os.sep + "DEM_" + projectName
    projectHillshade = basedataGDB_path + os.sep + "Hillshade_" + projectName
    projectDepths = basedataGDB_path + os.sep + "Local_Depths_" + projectName
    projectSlope = basedataGDB_path + os.sep + "Slope_Pct_" + projectName
    projectContours = demFD + os.sep + "Contours_" + projectName

    tempDEM = scratchGDB + os.sep + "tempDEM"
    DEMagg = scratchGDB + os.sep + "aggDEM"
    DEMsmooth = scratchGDB + os.sep + "DEMsmooth"
    ContoursTemp = scratchGDB + os.sep + "ContoursTemp"
    extendedContours = scratchGDB + os.sep + "extendedContours"
    Temp_DEMbase = scratchGDB + os.sep + "Temp_DEMbase"
    Fill_DEMaoi = scratchGDB + os.sep + "Fill_DEMaoi"
    FilMinus = scratchGDB + os.sep + "FilMinus"

    # ArcPro Map Layer Names
    contoursOut = "Contours_" + projectName
    demOut = "DEM_" + projectName
    depthOut = "Local_Depths_" + projectName
    slopeOut = "Slope_Pct_" + projectName
    hillshadeOut = "Hillshade_" + projectName

    # Temp layers list for cleanup at the start and at the end
    tempLayers = [tempDEM, DEMsmooth, ContoursTemp, extendedContours, Temp_DEMbase, Fill_DEMaoi, FilMinus]
    deleteTempLayers(tempLayers)


    #### Set up log file path and start logging
    arcpy.AddMessage("Commence logging...\n")
    textFilePath = userWorkspace + os.sep + projectName + "_log.txt"
    logBasicSettings()
    

    #### Remove existing project DEM related layers from the Pro maps
    AddMsgAndPrint("\nRemoving layers from project maps, if present...\n",0)
    
    # Set starting layers to be removed
    mapLayersToRemove = [contoursOut, demOut, depthOut, slopeOut, hillshadeOut]
    
    # Remove the layers in the list
    try:
        for maps in aprx.listMaps():
            for lyr in maps.listLayers():
                if lyr.name in mapLayersToRemove:
                    maps.removeLayer(lyr)
    except:
        pass


    #### Remove existing DEM related layers from the geodatabase
    AddMsgAndPrint("\nRemoving layers from project database, if present...\n",0)

    # Set starting datasets to remove
    datasetsToRemove = [projectDEM, projectHillshade, projectDepths, projectSlope, projectContours]

    # Remove the datasets in the list
    for dataset in datasetsToRemove:
        if arcpy.Exists(dataset):
            try:
                arcpy.Delete_management(dataset)
            except:
                pass


    #### Process the input DEMs
    AddMsgAndPrint("\nProcessing the DEM...",0)
    # Clip out the DEMs that were entered
    x = 0
    DEMlist = []
    while x < DEMcount:
        raster = inputDEMs[x].replace("'", "")
        desc = arcpy.Describe(raster)
        sr = desc.SpatialReference
        units = sr.LinearUnitName
        if units == "Meter":
            units = "Meters"
        elif units == "Foot":
            units = "Feet"
        elif units == "Foot_US":
            units = "Feet"
        else:
            AddMsgAndPrint("\nHorizontal units of one or more input DEMs do not appear to be feet or meters! Exiting...",2)
            exit()
        outClip = tempDEM + "_" + str(x)
        try:
            #arcpy.Clip_management(raster, "", outClip, projectAOI, "", "ClippingGeometry")
            extractedDEM = arcpy.sa.ExtractByMask(raster, projectAOI)
            extractedDEM.save(outClip)
        except:
            AddMsgAndPrint("\nOne or more input DEMs may have a problem! Please verify that the input DEMs cover the tract area and try to run again. Exiting...",2)
            sys.exit()
        if x == 0:
            mosaicInputs = "" + str(outClip) + ""
        else:
            mosaicInputs = mosaicInputs + ";" + str(outClip)
        DEMlist.append(str(outClip))
        x += 1

    cellsize = 0
    # Determine largest cell size
    for raster in DEMlist:
        desc = arcpy.Describe(raster)
        sr = desc.SpatialReference
        cellwidth = desc.MeanCellWidth
        if cellwidth > cellsize:
            cellsize = cellwidth
##        #Exit if any DEM is greater than 5m cell size
##        if units == "Meters":
##            if cellsize > 3:
##                AddMsgAndPrint("\nOne or more input DEMs has a cell size greater than 3 meters or 9.84252 feet! Please verify input DEM data and try again. Exiting...",2)
##                exit()
##        if units == "Feet":
##            if cellsize > 9.84252:
##                AddMsgAndPrint("\nOne or more input DEMs has a cell size greater than 3 meters or 9.84252 feet! Please verify input DEM data and try again. Exiting...",2)
##                exit()

    # Merge the DEMs
    if DEMcount > 1:
        arcpy.MosaicToNewRaster_management(mosaicInputs, scratchGDB, "tempDEM", "#", "32_BIT_FLOAT", cellsize, "1", "MEAN", "#")

    # Else just convert the one input DEM to become the tempDEM
    else:
        firstDEM = scratchGDB + os.sep + "tempDEM_0"
        arcpy.CopyRaster_management(firstDEM, tempDEM)

    # Delete clippedDEM files
    for raster in DEMlist:
        arcpy.Delete_management(raster)

    # Gather info on the final temp DEM
    desc = arcpy.Describe(tempDEM)
    sr = desc.SpatialReference
    # linear units should now be meters, since outputs were UTM zone specified
    units = sr.LinearUnitName

    if sr.Type == "Projected":
        if zUnits == "Meters":
            Zfactor = 1
        elif zUnits == "Meter":
            Zfactor = 1
        elif zUnits == "Feet":
            Zfactor = 0.3048
        elif zUnits == "Inches":
            Zfactor = 0.0254
        elif zUnits == "Centimeters":
            Zfactor = 0.01
        else:
            AddMsgAndPrint("\nZunits were not selected at runtime....Exiting!",2)
            exit()

        AddMsgAndPrint("\tDEM Projection Name: " + sr.Name,0)
        AddMsgAndPrint("\tDEM XY Linear Units: " + units,0)
        AddMsgAndPrint("\tDEM Elevation Values (Z): " + zUnits,0)
        AddMsgAndPrint("\tZ-factor for Slope Modeling: " + str(Zfactor),0)
        AddMsgAndPrint("\tDEM Cell Size: " + str(desc.MeanCellWidth) + " x " + str(desc.MeanCellHeight) + " " + units,0)

    else:
        AddMsgAndPrint("\n\n\t" + os.path.basename(tempDEM) + " is not in a projected Coordinate System! Exiting...",2)
        exit()

    # Clip out the DEM with extended buffer for temp processing and standard buffer for final DEM display
    arcpy.Clip_management(tempDEM, "", projectDEM, projectTractB, "", "ClippingGeometry")

    # Create a temporary smoothed DEM to use for creating a slope layer and a contours layer
    AddMsgAndPrint("\tCreating a 3-meter pixel resolution version of the DEM for use in contours and slopes...",0)
    arcpy.ProjectRaster_management(tempDEM, DEMagg, cluSR, "BILINEAR", "3", "#", "#", "#")
    
    #outAggreg = arcpy.sa.Aggregate(tempDEM, smoothing, "MEAN", "TRUNCATE", "DATA")
    #outAggreg.save(DEMagg)

    outFocalStats = arcpy.sa.FocalStatistics(DEMagg, "RECTANGLE 3 3 CELL", "MEAN", "DATA")
    outFocalStats.save(DEMsmooth)
    AddMsgAndPrint("\tSuccessful",0)

    # Create Slope Layer
    # Use Zfactor to get accurate slope creation. Do not assume this Zfactor with contour processing later
    AddMsgAndPrint("\nCreating Slope...",0)
    outSlope = arcpy.sa.Slope(DEMsmooth, "PERCENT_RISE", Zfactor)
    arcpy.Clip_management(outSlope, "", projectSlope, projectTractB, "", "ClippingGeometry")
    AddMsgAndPrint("\tSuccessful",0)


    #### Create contours
    # Use an appropriate z factor to always get contour results in feet.
    # Use a new variable, cZfactor (contours Z factor) to distinguish from Zfactor used for slope above
    cZfactor = 0
    if zUnits == "Meters":
        cZfactor = 3.28084
    elif zUnits == "Centimeters":
        cZfactor = 0.0328084
    elif zUnits == "Inches":
        cZfactor = 0.0833333
    else:
        cZfactor = 1

    # Create Contours
    AddMsgAndPrint("\nCreating " + str(interval) + " foot Contours from DEM using a Z-factor of " + str(cZfactor) + "...",0)
    arcpy.sa.Contour(DEMsmooth, ContoursTemp, interval, "", cZfactor)
    arcpy.AddField_management(ContoursTemp, "Index", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

    # Delete temporary feature layer of contours if it exists from previous runs
    if arcpy.Exists("ContourLYR"):
        try:
            arcpy.Delete_management("ContourLYR")
        except:
            pass
        
    # Make the temporary contours feature layer for indexing calculations
    arcpy.MakeFeatureLayer_management(ContoursTemp,"ContourLYR","","","")

    # every 5th contour will be indexed to 1
    expression = "MOD( \"CONTOUR\"," + str(float(interval) * 5) + ") = 0"
    arcpy.SelectLayerByAttribute_management("ContourLYR", "NEW_SELECTION", expression)
    indexValue = 1
    #arcpy.CalculateField_management("ContourLYR", "Index", indexValue, "VB","")
    arcpy.CalculateField_management("ContourLYR", "Index", indexValue, "PYTHON_9.3")
    del indexValue
    del expression

    # All other contours will be indexed to 0
    arcpy.SelectLayerByAttribute_management("ContourLYR", "SWITCH_SELECTION", "")
    indexValue = 0
    #arcpy.CalculateField_management("ContourLYR", "Index", indexValue, "VB","")
    arcpy.CalculateField_management("ContourLYR", "Index", indexValue, "PYTHON_9.3")
    del indexValue

    # Clear selection and write all contours to final feature class via a clip
    arcpy.SelectLayerByAttribute_management("ContourLYR","CLEAR_SELECTION","")
    arcpy.CopyFeatures_management("ContourLYR", extendedContours)
    arcpy.Clip_analysis(extendedContours, projectTractB, projectContours)

    # Delete unwanted "ID" remnant field
    if len(arcpy.ListFields(projectContours,"Id")) > 0:
        try:
            arcpy.DeleteField_management(Contours,"Id")
        except:
            pass

    arcpy.Delete_management("ContourLYR")
    
    AddMsgAndPrint("\tSuccessful",0)


    #### Create Hillshade and Depth Grid
    AddMsgAndPrint("\nCreating Hillshade...",0)
    outHillshade = arcpy.sa.Hillshade(projectDEM, "315", "45", "#", Zfactor)
    outHillshade.save(projectHillshade)
    AddMsgAndPrint("\tSuccessful",0)

    AddMsgAndPrint("\nCreating Local Depths...",0)
    fill = False
    try:
        # Fills sinks in projectDEM to remove small imperfections in the data.
        # Convert the projectDEM to a raster with z units in feet to create this layer
        Temp_DEMbase = arcpy.sa.Times(projectDEM, cZfactor)
        Fill_DEMaoi = arcpy.sa.Fill(Temp_DEMbase, "")
        fill = True
    except:
        pass
    
    if fill:
        FilMinus = arcpy.sa.Minus(Fill_DEMaoi, Temp_DEMbase)

        # Create a Depth Grid whereby any pixel with a difference is written to a new raster
        tempDepths = arcpy.sa.Con(FilMinus, FilMinus, "", "VALUE > 0")
        tempDepths.save(projectDepths)

        # Delete temp data
        del tempDepths

        AddMsgAndPrint("\tSuccessful",0)


    #### Delete temp data
    AddMsgAndPrint("\nDeleting temp data..." ,0)
    deleteTempLayers(tempLayers)
    
    
    #### Compact FGDB
    try:
        AddMsgAndPrint("\nCompacting File Geodatabase..." ,0)
        arcpy.Compact_management(basedataGDB_path)
        AddMsgAndPrint("\tSuccessful",0)
    except:
        pass


    #### Add layers to Pro Map
    AddMsgAndPrint("\nAdding Layers to Map...",0)
    arcpy.SetParameterAsText(7, projectContours)
    arcpy.SetParameterAsText(8, projectDEM)
    arcpy.SetParameterAsText(9, projectDepths)
    arcpy.SetParameterAsText(10, projectSlope)
    

except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested. Exiting...")

except:
    errorMsg()
