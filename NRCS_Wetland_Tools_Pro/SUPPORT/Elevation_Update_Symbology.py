## ===============================================================================================================
## Name:    Elevation - Update Symbology
## Purpose: Change the symbology for the slope and local depths layers to the standardized version.
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
#### Import system modules
import arcpy, os, sys


#### Update Environments
arcpy.AddMessage("Setting Environments...\n")

# Set overwrite flag
arcpy.env.overwriteOutput = True

# Test for Pro project.
try:
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    m = aprx.listMaps("Determinations")[0]
except:
    arcpy.AddError("\nThis tool must be run from a active ArcGIS Pro project that was developed from the template distributed with this toolbox. Exiting...\n")
    exit()


#### Main procedures
try:
    #### Inputs
    arcpy.AddMessage("Reading inputs...\n")
    slpLyr = arcpy.GetParameterAsText(0)
    depthsLyr = arcpy.GetParameterAsText(1)
    slpSym = arcpy.GetParameterAsText(2)
    depthsSym = arcpy.GetParameterAsText(3)
    #slpSym = r'C:\GIS_Tools\NRCS_Wetland_Tools_Pro\SUPPORT\layer_files\Slope_Pct.lyrx'
    #depthsSym = r'C:\GIS_Tools\NRCS_Wetland_Tools_Pro\SUPPORT\layer_files\Local_Depths.lyrx'
    #slpSym = arcpy.mp.LayerFile(os.path.join(os.path.dirname(sys.argv[0]), "layer_files") + os.sep + "Slope_Pct.lyrx").listLayers()[0]
    #depthsSym = arcpy.mp.LayerFile(os.path.join(os.path.dirname(sys.argv[0]), "layer_files") + os.sep + "Local_Depths.lyrx").listLayers()[0]

    #### Get the layers
    slopeLayer = m.listLayers(slpLyr)[0]
    depthsLayer = m.listLayers(depthsLyr)[0]

    
    #### Change the symbology
    arcpy.ApplySymbologyFromLayer_management(slopeLayer, slpSym, "VALUE_FIELD", "MAINTAIN")
    arcpy.ApplySymbologyFromLayer_management(depthsLayer, depthsSym, "VALUE_FIELD", "MAINTAIN")
    

except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested. Exiting...")

except:
    errorMsg()
