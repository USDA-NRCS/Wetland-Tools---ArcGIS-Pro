## ===============================================================================================================
## Name:    Elevation - Download DEM from NRCS Service
## Purpose: Download a DEM from the NRCS 1m, 2m, or 3m service. Not intended to download from other services.
##
## Authors: Chris Morse
##          GIS Specialist
##          Indianapolis State Office
##          USDA-NRCS
##          chris.morse@usda.gov
##          317.295.5849
##
## Created: 11/16/2020
##
## ===============================================================================================================
## Changes
## ===============================================================================================================
##
## rev. 11/16/2020
## Start revisions of old versions of the tool to National Wetlands Tool in ArcGIS Pro.
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
    f.write("Executing Elevation - Download DEM from NRCS Service tool...\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("User Parameters:\n")
    f.write("\tWorkspace: " + userWorkspace + "\n")
    f.write("\tInput CLU: " + sourceCLU + "\n")
    f.write("\tInput Service: " + sourceService + "\n")
    f.write("\tInput Cell Size: " + str(sourceCellsize) + "\n")
    f.close
    del f

## ===============================================================================================================
def removeLayers(layer_list):
    # Remove the layers in the list
    try:
        for maps in aprx.listMaps():
            for lyr in maps.listLayers():
                if lyr.name in layer_list:
                    maps.removeLayer(lyr)
    except:
        pass
    
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
import arcpy, sys, os, traceback, re


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

# Environment Settings
arcpy.env.resamplingMethod = "BILINEAR"
arcpy.env.pyramid = "PYRAMIDS -1 BILINEAR DEFAULT 75 NO_SKIP"
arcpy.env.geographicTransformations = "WGS_1984_(ITRF00)_To_NAD_1983"

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
    sourceService = arcpy.GetParameterAsText(1)
    sourceCellsize = arcpy.GetParameterAsText(2)
    
    #### Set base path
    sourceCLU_path = arcpy.Describe(sourceCLU).CatalogPath
    if sourceCLU_path.find('.gdb') > 0 and sourceCLU_path.find('Determinations') > 0 and sourceCLU_path.find('Site_CLU') > 0:
        basedataGDB_path = sourceCLU_path[:sourceCLU_path.find('.gdb')+4]
    else:
        arcpy.AddError("\nSelected Site CLU layer is not from a Determinations project folder. Exiting...")
        exit()


    #### Variables
    userWorkspace = os.path.dirname(basedataGDB_path)
    basedataFD = basedataGDB_path + os.sep + "Layers"
    projectName = os.path.basename(userWorkspace).replace(" ","_")
    supportGDB = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb")
    scratchGDB = os.path.join(os.path.dirname(sys.argv[0]), "SCRATCH.gdb")
    dl_extent = scratchGDB + os.sep + "dl_extent"
    wgs_AOI = scratchGDB + os.sep + "AOI_WGS84"
    WGS84_DEM = scratchGDB + os.sep + "WGS84_DEM"
    final_DEM = basedataGDB_path + os.sep + "Downloaded_DEM"
    DEM_out = "Downloaded_DEM"
    

    #### Set up log file path and start logging
    arcpy.AddMessage("Commence logging...\n")
    textFilePath = userWorkspace + os.sep + projectName + "_log.txt"
    logBasicSettings()


    #### Delete temporary layers
    tempLayers = [dl_extent, wgs_AOI, WGS84_DEM]
    deleteTempLayers(tempLayers)


    #### Buffer the CLU
    bufferDistPlus = "550 Feet"
    arcpy.Buffer_analysis(sourceCLU, dl_extent, bufferDistPlus, "FULL", "", "ALL", "")
    if arcpy.Exists(dl_extent) == False:
        arcpy.AddError("\nCould not create download extent from Site CLU layer! Exiting...")
        exit()

        
    #### Remove the Source_DEM from the map and geodatabase if it already exists
    layers_to_remove = [DEM_out]
    removeLayers(layers_to_remove)
    
    if arcpy.Exists(final_DEM):
        try:
            arcpy.Delete_management(final_DEM)
        except:
            pass


    #### Re-project the AOI to WGS84 Geographic (EPSG WKID: 4326)
    AddMsgAndPrint("\nConverting AOI to WGS 1984...\n",0)
    wgs_CS = arcpy.SpatialReference(4326)
    arcpy.Project_management(dl_extent, wgs_AOI, wgs_CS)


    #### Use the WGS 1984 AOI to clip/extract the DEM from the service
    AddMsgAndPrint("\nDownloading Data...\n",0)
    aoi_ext = arcpy.Describe(wgs_AOI).extent
    xMin = aoi_ext.XMin
    yMin = aoi_ext.YMin
    xMax = aoi_ext.XMax
    yMax = aoi_ext.YMax
    clip_ext = str(xMin) + " " + str(yMin) + " " + str(xMax) + " " + str(yMax)
    arcpy.Clip_management(sourceService, clip_ext, WGS84_DEM, "", "", "", "NO_MAINTAIN_EXTENT")
    
    
    #### Project the WGS 1984 DEM to the coordinate system of the input CLU layer
    # We use the factory code to get it, so that it covers any UTM Zone.
    AddMsgAndPrint("\nProjecting data to match input CLU...\n",0)
    final_CS = arcpy.Describe(sourceCLU).spatialReference.factoryCode
    arcpy.ProjectRaster_management(WGS84_DEM, final_DEM, final_CS, "BILINEAR", sourceCellsize)


    #### Clean up and add to map
    try:
        AddMsgAndPrint("\nCompacting File Geodatabase...",0)
        arcpy.Compact_management(basedataGDB_path)
    except:
        pass
    
    AddMsgAndPrint("\nCleaning up temp files and adding DEM to map...\n",0)
    deleteTempLayers(tempLayers)

    arcpy.SetParameterAsText(3, final_DEM)
    
    
except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested. Exiting...",0)

except:
    errorMsg()
