## ===============================================================================================================
## Name:    Create Reference Data
## Purpose: Download SSURGO layers and create DEM, Hillshade, Slope, Depth Grid, and Contours for the project
##
## Authors: Adolfo Diaz
##          GIS Specialist
##          National Soil Survey Center
##          USDA-NRCS
##          adolfo.diaz@usda.gov
##          608.662.4422 ext 216
##
##          Chris Morse
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
## rev. 02/04/2021
## -Integrate SSURGO data download and processing components
##
## rev. 03/03/2021
## -Adjust extent within which to generate reference data layers based on user specified input parameter for full
##  tract or request extent.
##
## rev. 06/11/2021
## -Fixed bug that was copying and processing entire input DEM when only one input DEM was specified.
## -Update method to add Slope and Depth Grid to map so they load with the correct legend.
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
    f.write("Executing Create Reference Data tool...\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("User Parameters:\n")
    f.write("\tWorkspace: " + userWorkspace + "\n")
    f.write("\tSelected Extent: " + dataExtent + "\n")
    if bSSURGO == True:
        f.write("\tSSURGO data download selected? Yes\n")
        f.write("\tSoil Properties Selected: " + str(propertyList) + "\n")
    else:
        f.write("\tSSURGO data download selected? No\n")
    if bElevation == True:
        f.write("\tElevation data processing selected? Yes\n")
        f.write("\tInput DEMs: " + str(inputDEMs) + "\n")
        if len (zUnits) > 0:
            f.write("\tElevation Z-units: " + zUnits + "\n")
        else:
            f.write("\tElevation Z-units: NOT SPECIFIED\n")
        if len(interval) > 0:
            f.write("\tContour Interval: " + str(interval) + " ft.\n")
        else:
            f.write("\tContour Interval: NOT SPECIFIED\n")
    else:
        f.write("\tElevation data processing selected? No\n")
    f.close
    del f

## ===============================================================================================================
def deleteTempLayers(lyrs):
    for lyr in lyrs:
        if arcpy.Exists(lyr):
            try:
                arcpy.Delete_management(lyr)
            except:
                pass

## ===============================================================================================================
#### Import system modules
import sys, os, time, urllib, json, traceback, socket
import arcpy
from importlib import reload
sys.dont_write_bytecode = True
scriptPath = os.path.dirname(sys.argv[0])
sys.path.append(scriptPath)

import getSSURGO_WCT_ArcGISpro
reload(getSSURGO_WCT_ArcGISpro)


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
    arcpy.AddError("\nThis tool must be run from an active ArcGIS Pro project that was developed from the template distributed with this toolbox. Exiting...\n")
    exit()


#### Main procedures
try:
    #### Inputs
    arcpy.AddMessage("Reading inputs...\n")
    sourceCLU = arcpy.GetParameterAsText(0)                     # User selected project CLU
    dataExtent = arcpy.GetParameterAsText(1)
    bSSURGO = arcpy.GetParameter(2)
    propertyList = arcpy.GetParameter(3)
    bElevation = arcpy.GetParameter(4)
    inputDEMs = arcpy.GetParameterAsText(5).split(";")          # user selected input DEMs
    DEMcount = len(inputDEMs)
    zUnits = arcpy.GetParameterAsText(6)                        # elevation z units of input DEM
    interval = arcpy.GetParameterAsText(7)                      # user defined contour interval (string)
    demSR = arcpy.GetParameterAsText(8)
    cluSR = arcpy.GetParameterAsText(9)
    transform = arcpy.GetParameterAsText(10)
##    if demSR == cluSR:
##        matchSR = True
##    else:
##        matchSR = False

    slpLyr = arcpy.mp.LayerFile(os.path.join(os.path.dirname(sys.argv[0]), "layer_files") + os.sep + "Slope_Pct.lyrx").listLayers()[0]
    dgLyr = arcpy.mp.LayerFile(os.path.join(os.path.dirname(sys.argv[0]), "layer_files") + os.sep + "Local_Depths.lyrx").listLayers()[0]

    #### Exit if neither data download option was selected to be run
    if bSSURGO == False and bElevation == False:
        arcpy.AddError("\nAt least one type of data download must be specified. Exiting...\n")
        exit()


##    if bElevation:
##        #### Manage spatial references
##        arcpy.env.outputCoordinateSystem = cluSR
##        if transform != '':
##            arcpy.env.geographicTransformations = transform
##        else:
##            arcpy.env.geographicTransformations = "WGS_1984_(ITRF00)_To_NAD_1983"
##        arcpy.env.resamplingMethod = "BILINEAR"
##        arcpy.env.pyramid = "PYRAMIDS -1 BILINEAR DEFAULT 75 NO_SKIP"

                
    #### Set base path
    sourceCLU_path = arcpy.Describe(sourceCLU).CatalogPath
    if sourceCLU_path.find('.gdb') > 0 and sourceCLU_path.find('Determinations') > 0 and sourceCLU_path.find('Site_CLU') > 0:
        basedataGDB_path = sourceCLU_path[:sourceCLU_path.find('.gdb')+4]
    else:
        arcpy.AddError("\nSelected Site CLU layer is not from a Determinations project folder. Exiting...")
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
    #demFD_name = "DEM_Vectors"
    #demFD = basedataGDB_path + os.sep + demFD_name
    userWorkspace = os.path.dirname(basedataGDB_path)
    projectName = os.path.basename(userWorkspace).replace(" ", "_")
    wetDir = userWorkspace + os.sep + "Wetlands"

    projectTract = basedataFD + os.sep + "Site_Tract"
    #projectTractB = basedataFD + os.sep + "Site_Tract_Buffer"
    projectAOI = basedataFD + os.sep + "project_AOI"
    pcsAOI = scratchGDB + os.sep + "pcsAOI"
    projectAOI_B = basedataFD + os.sep + "project_AOI_B"
    projectExtent = basedataFD + os.sep + "Request_Extent"
    bufferDist = "500 Feet"
    bufferDistPlus = "550 Feet"

    if bElevation:
        projectDEM = basedataGDB_path + os.sep + "Site_DEM"
        projectHillshade = basedataGDB_path + os.sep + "Site_Hillshade"
        dgName = "Site_Depth_Grid"
        projectDepths = basedataGDB_path + os.sep + dgName
        slpName = "Site_Slope_Pct"
        projectSlope = basedataGDB_path + os.sep + slpName
        projectContours = basedataGDB_path + os.sep + "Site_Contours"

        tempDEM = scratchGDB + os.sep + "tempDEM"
        tempDEM2 = scratchGDB + os.sep + "tempDEM2"
        DEMagg = scratchGDB + os.sep + "aggDEM"
        DEMsmooth = scratchGDB + os.sep + "DEMsmooth"
        ContoursTemp = scratchGDB + os.sep + "ContoursTemp"
        extendedContours = scratchGDB + os.sep + "extendedContours"
        Temp_DEMbase = scratchGDB + os.sep + "Temp_DEMbase"
        Fill_DEMaoi = scratchGDB + os.sep + "Fill_DEMaoi"
        FilMinus = scratchGDB + os.sep + "FilMinus"

        # ArcPro Map Layer Names
        contoursOut = "Site_Contours"
        demOut = "Site_DEM"
        depthOut = "Site_Depth_Grid"
        slopeOut = "Site_Slope_Pct"
        hillshadeOut = "Site_Hillshade"

        # Temp layers list for cleanup at the start and at the end
        tempLayers = [pcsAOI, tempDEM, tempDEM2, DEMagg, DEMsmooth, ContoursTemp, extendedContours, Temp_DEMbase, Fill_DEMaoi, FilMinus]
        deleteTempLayers(tempLayers)


    #### Set up log file path and start logging
    arcpy.AddMessage("Commence logging...\n")
    textFilePath = userWorkspace + os.sep + projectName + "_log.txt"
    logBasicSettings()


    #### Create the projectAOI and projectAOI_B layers based on the choice selected by user input
    AddMsgAndPrint("\nBuffering extent...",0)
    if dataExtent == "Request Extent":
        # Use the request extent to create buffers for use in data extraction
        arcpy.Buffer_analysis(projectExtent, projectAOI, bufferDist, "FULL", "", "ALL", "")
        arcpy.Buffer_analysis(projectExtent, projectAOI_B, bufferDistPlus, "FULL", "", "ALL", "")
    else:
        # Use the tract boundary to create the buffers for use in data extraction
        arcpy.Buffer_analysis(projectTract, projectAOI, bufferDist, "FULL", "", "ALL", "")
        arcpy.Buffer_analysis(projectTract, projectAOI_B, bufferDistPlus, "FULL", "", "ALL", "")


    #### Call SSURGO download script if it was selected
    if bSSURGO:
        AddMsgAndPrint("\nLaunching Soil Data Access download module...",0)
        getSSURGO_WCT_ArcGISpro.start(projectAOI, propertyList, basedataGDB_path)


    #### Call Elevation processing
    if bElevation:
        AddMsgAndPrint("\nProcessing elevation data...",0)

        #### Manage spatial references
        arcpy.env.outputCoordinateSystem = cluSR
        if transform != '':
            arcpy.env.geographicTransformations = transform
        else:
            arcpy.env.geographicTransformations = "WGS_1984_(ITRF00)_To_NAD_1983"
        arcpy.env.resamplingMethod = "BILINEAR"
        arcpy.env.pyramid = "PYRAMIDS -1 BILINEAR DEFAULT 75 NO_SKIP"
        
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
        AddMsgAndPrint("\nProcessing the input DEM file(s)...",0)

##        # Convert the projectAOI to a tempAOI that matches the input DEM PCS
##        if matchSR == False:
##            AddMsgAndPrint("\tConverting AOI to coordinate system of input DEM...",0)
##            arcpy.Project_management(projectAOI_B, pcsAOI, demSR, transform)
        
        # Clip out the DEMs that were entered
        AddMsgAndPrint("\tExtracting input DEM(s)...",0)
        x = 0
        DEMlist = []
        while x < DEMcount:
            raster = inputDEMs[x].replace("'", "")
            desc = arcpy.Describe(raster)
            raster_path = desc.CatalogPath
            sr = desc.SpatialReference
            units = sr.LinearUnitName
            if units == "Meter":
                units = "Meters"
            elif units == "Foot":
                units = "Feet"
            elif units == "Foot_US":
                units = "Feet"
            else:
                AddMsgAndPrint("\tHorizontal units of one or more input DEMs do not appear to be feet or meters! Exiting...",2)
                exit()
            outClip = tempDEM + "_" + str(x)
            try:
                #arcpy.Clip_management(raster, "", outClip, projectAOI, "", "ClippingGeometry")
##                if matchSR == False:
##                    extractedDEM = arcpy.sa.ExtractByMask(raster_path, pcsAOI)
##                else:
##                    extractedDEM = arcpy.sa.ExtractByMask(raster_path, projectAOI_B)
                extractedDEM = arcpy.sa.ExtractByMask(raster_path, projectAOI_B)
                extractedDEM.save(outClip)
            except:
                AddMsgAndPrint("\tOne or more input DEMs may have a problem! Please verify that the input DEMs cover the tract area and try to run again. Exiting...",2)
                sys.exit()
            if x == 0:
                mosaicInputs = "" + str(outClip) + ""
            else:
                mosaicInputs = mosaicInputs + ";" + str(outClip)
            DEMlist.append(str(outClip))
            x += 1
            del sr

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
            del sr
            
        # Merge the DEMs
        if DEMcount > 1:
            AddMsgAndPrint("\nMerging multiple input DEM(s)...",0)
            arcpy.MosaicToNewRaster_management(mosaicInputs, scratchGDB, "tempDEM", "#", "32_BIT_FLOAT", cellsize, "1", "MEAN", "#")

        # Else just convert the one input DEM to become the tempDEM
        else:
            AddMsgAndPrint("\nOnly one input DEM detected. Carrying extract forward for final DEM processing...",0)
            #firstDEM = scratchGDB + os.sep + "tempDEM_0"
            firstDEM = DEMlist[0]
            arcpy.CopyRaster_management(firstDEM, tempDEM)

        # Delete clippedDEM files
        AddMsgAndPrint("\nDeleting initial temp DEM file(s)...",0)
        for raster in DEMlist:
            arcpy.Delete_management(raster)

##        # Convert the input DEM to the target PCS, if necessary
##        if matchSR == False:
##            AddMsgAndPrint("\nProjecting new DEM back to local determination's coordinate system...",0)
##            arcpy.ProjectRaster_management(tempDEM2, tempDEM, cluSR, "BILINEAR", "", transform)
##        else:
##            AddMsgAndPrint("\nCopying temporary DEM for further processing...",0)
##            arcpy.CopyRaster_management(tempDEM2, tempDEM)
        

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

        # Clip out the tempDEM with the smaller buffer to get final projectDEM extent
        AddMsgAndPrint("\nClipping project DEM to buffered extent...",0)
        arcpy.Clip_management(tempDEM, "", projectDEM, projectAOI, "", "ClippingGeometry")

        # Create a temporary smoothed DEM to use for creating a slope layer and a contours layer
        AddMsgAndPrint("\tCreating a 3-meter pixel resolution version of the DEM for use in contours and slopes...",0)
        arcpy.ProjectRaster_management(tempDEM, DEMagg, cluSR, "BILINEAR", "3", "#", "#", "#")
        
        #outAggreg = arcpy.sa.Aggregate(tempDEM, smoothing, "MEAN", "TRUNCATE", "DATA")
        #outAggreg.save(DEMagg)
        AddMsgAndPrint("\tSmoothing the DEM with Focal Statistics...",0)
        outFocalStats = arcpy.sa.FocalStatistics(DEMagg, "RECTANGLE 3 3 CELL", "MEAN", "DATA")
        outFocalStats.save(DEMsmooth)
        AddMsgAndPrint("\tSuccessful",0)

        # Create Slope Layer
        # Use Zfactor to get accurate slope creation. Do not assume this Zfactor with contour processing later
        AddMsgAndPrint("\nCreating Slope...",0)
        outSlope = arcpy.sa.Slope(DEMsmooth, "PERCENT_RISE", Zfactor)
        arcpy.Clip_management(outSlope, "", projectSlope, projectAOI, "", "ClippingGeometry")
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
        arcpy.Clip_analysis(extendedContours, projectAOI, projectContours)

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


        #### Add layers to Pro Map
        AddMsgAndPrint("\nAdding Layers to Map...",0)
        lyr_list = m.listLayers()
        lyr_name_list = []
        for lyr in lyr_list:
            lyr_name_list.append(lyr.name)
        
        arcpy.SetParameterAsText(11, projectContours)

        if dgName not in lyr_name_list:
            dgLyr_cp = dgLyr.connectionProperties
            dgLyr_cp['connection_info']['database'] = basedataGDB_path
            dgLyr_cp['dataset'] = dgName
            dgLyr.updateConnectionProperties(dgLyr.connectionProperties, dgLyr_cp)
            m.addLayer(dgLyr)
            
        #arcpy.SetParameterAsText(12, projectSlope)
        arcpy.SetParameterAsText(13, projectDEM)
        arcpy.SetParameterAsText(14, projectHillshade)
        #arcpy.SetParameterAsText(15, projectDepths)
        
        if slpName not in lyr_name_list:
            slpLyr_cp = slpLyr.connectionProperties
            slpLyr_cp['connection_info']['database'] = basedataGDB_path
            slpLyr_cp['dataset'] = slpName
            slpLyr.updateConnectionProperties(slpLyr.connectionProperties, slpLyr_cp)
            m.addLayer(slpLyr)


    #### Clean up
    # Look for and delete anything else that may remain in the installed SCRATCH.gdb
    startWorkspace = arcpy.env.workspace
    arcpy.env.workspace = scratchGDB
    dss = []
    for ds in arcpy.ListDatasets('*'):
        dss.append(os.path.join(scratchGDB, ds))
    for ds in dss:
        if arcpy.Exists(ds):
            try:
                arcpy.Delete_management(ds)
            except:
                pass
    arcpy.env.workspace = startWorkspace
    del startWorkspace
    

    #### Compact FGDB
    try:
        AddMsgAndPrint("\nCompacting File Geodatabase..." ,0)
        arcpy.Compact_management(basedataGDB_path)
        AddMsgAndPrint("\tSuccessful",0)
    except:
        pass

    
except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested. Exiting...")

except:
    errorMsg()
