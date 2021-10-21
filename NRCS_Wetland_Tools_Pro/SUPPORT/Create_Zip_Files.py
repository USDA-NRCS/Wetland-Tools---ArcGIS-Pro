## ===============================================================================================================
## Name:    Create Zip Files
## Purpose: Create zip files in the project folder and load them with user selected files.
##
## Authors: Chris Morse
##          GIS Specialist
##          Indianapolis State Office
##          USDA-NRCS
##          chris.morse@usda.gov
##          317.295.5849
##
## Created: 10/14/2021
##
## ===============================================================================================================
## Changes
## ===============================================================================================================
##
## rev. 10/14/2021
## - Modify code from ArcMap Wetlands Tool for Create DMS Zipfile and update for new products to send to tracker.
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
    f.write("Executing Create Zip Files tool...\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.close
    del f

## ===============================================================================================================
#### Import system modules
import arcpy, sys, os, traceback, re, zipfile


#### Update Environments
arcpy.AddMessage("Setting Environments...\n")
arcpy.SetProgressorLabel("Setting Environments...")
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
    arcpy.SetProgressorLabel("Reading inputs...")
    sourceCWD = arcpy.GetParameterAsText(0)
    det_type = arcpy.GetParameterAsText(1)
    bCCPWC = arcpy.GetParameter(2)
    bSTDWC = arcpy.GetParameter(3)
    CCPWC_files = arcpy.GetParameterAsText(4).split(";")
    STDWC_files = arcpy.GetParameterAsText(5).split(";")

    # Multi value strings parameters that are optional always send a blank 1st item
    # Check the lengths of first items to set a boolean condition for whether to populate the respective zip
    if len(CCPWC_files[0]) > 0:
        CCPWC_exists = True
    else:
        CCPWC_exists = False

    if len(STDWC_files[0]) > 0:
        STDWC_exists = True
    else:
        STDWC_exists = False
        
    #### Initial Validations
    arcpy.AddMessage("Verifying inputs...\n")
    arcpy.SetProgressorLabel("Verifying inputs...")

    
    #### Set base path
    sourceCWD_path = arcpy.Describe(sourceCWD).CatalogPath
    if sourceCWD_path.find('.gdb') > 0 and sourceCWD_path.find('Determinations') > 0 and sourceCWD_path.find('Site_CWD') > 0:
        wcGDB_path = sourceCWD_path[:sourceCWD_path.find('.gdb')+4]
    else:
        arcpy.AddError("\nSelected CWD layer is not from a Determinations project folder. Exiting...")
        exit()


    #### Define Variables
    arcpy.AddMessage("Setting variables...\n")
    arcpy.SetProgressorLabel("Setting variables...")
    supportGDB = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb")
    scratchGDB = os.path.join(os.path.dirname(sys.argv[0]), "SCRATCH.gdb")

    wetDir = os.path.dirname(wcGDB_path)
    wcFD = wcGDB_path + os.sep + "WC_Data"
    userWorkspace = os.path.dirname(wetDir)
    projectName = os.path.basename(userWorkspace).replace(" ", "_")
    basedataGDB_path = userWorkspace + os.sep + projectName + "_BaseData.gdb"
    basedataFD_name = "Layers"
    basedataFD = basedataGDB_path + os.sep + basedataFD_name

    cwdName = "Site_CWD"
    projectCWD = wcFD + os.sep + cwdName

    if det_type == "Preliminary":
        ccpwc_zipout = wetDir + os.sep + "Combined_Client_Product_WC_Preliminary.zip"
        stdwc_zipout = wetDir + os.sep + "Supporting_Tech_Doc_WC_Preliminary.zip"
    else:
        ccpwc_zipout = wetDir + os.sep + "Combined_Client_Product_WC_Final.zip"
        stdwc_zipout = wetDir + os.sep + "Supporting_Tech_Doc_WC_Final.zip"

    shapeOut = projectName + "_Site_CWD.shp"
    shapePath = wetDir + os.sep + shapeOut

    #### Set up log file path and start logging
    arcpy.AddMessage("Commence logging...\n")
    arcpy.SetProgressorLabel("Commence logging...")
    textFilePath = userWorkspace + os.sep + projectName + "_log.txt"
    logBasicSettings()


    #### Replace zip files to prevent appending duplicate files
    AddMsgAndPrint("Creating initial zip files...",0)
    arcpy.SetProgressorLabel("Creating initial zip files...")
    if os.path.exists(ccpwc_zipout):
        try:
            os.remove(ccpwc_zipout)
        except:
            AddMsgAndPrint("The Combined Client Product zip file could not be deleted. Please move or rename the file and try again. Exiting...",2)
            exit()

    if os.path.exists(stdwc_zipout):
        try:
            os.remove(stdwc_zipout)
        except:
            AddMsgAndPrint("The Supporting Tech Doc zip file could not be deleted. Please move or rename the file and try again. Exiting...",2)
            exit()


    #### Export CWD shapefile
    AddMsgAndPrint("\nExporting CWD shapefile...",0)
    arcpy.SetProgressorLabel("Exporting CWD shapefile...")
    if arcpy.Exists(projectCWD):
        try:
            arcpy.FeatureClassToFeatureClass_conversion(projectCWD, wetDir, shapeOut)
            AddMsgAndPrint("\nCWD shapefile successfully exported!",0)
        except:
            AddMsgAndPrint("\nCould not export CWD shapefile. Shapefile may be locked. Continuing...",0)
    else:
        AddMsgAndPrint("\nDetermination spatial data files missing. Shapefiles not exported. Continuing...",0)
        

    #### Create zip files
    # Combined Client Products Zip File
    if bCCPWC:
        AddMsgAndPrint("\nUpdating Combined Client Product zip file...",0)
        arcpy.SetProgressorLabel("Updating Combined Client Product zip file...")
        zip = zipfile.ZipFile(ccpwc_zipout, 'a', zipfile.ZIP_DEFLATED)
        if CCPWC_exists:
            for item in (CCPWC_files):
                zip.write(item.replace("'",""), os.path.basename(item).replace("'",""))
                
        zip.close()
            
    # Supporting Docs Zip File
    if bSTDWC:
        AddMsgAndPrint("\nUpdating Supporting Tech Doc zip file...",0)
        arcpy.SetProgressorLabel("Updating Supporting Tech Doc zip file...")

        zip = zipfile.ZipFile(stdwc_zipout, 'a', zipfile.ZIP_DEFLATED)
        
        # Assemble CWD shapefile component files, if they exist, and zip them.
        if arcpy.Exists(shapePath):
            shape_list = []
            for (dirpath, dirname, filenames) in os.walk(wetDir):
                for file in filenames:
                    if (projectName + "_Site_CWD.") in file:
                        shape_list.append(file)
            for shape in shape_list:
                zip.write(os.path.join(wetDir, shape), shape)
        
        if STDWC_exists:
            for item in (STDWC_files):
                zip.write(item.replace("'",""), os.path.basename(item).replace("'",""))
                
        zip.close()
    

    #### Compact FGDB
    try:
        AddMsgAndPrint("\nCompacting File Geodatabases..." ,0)
        arcpy.SetProgressorLabel("Compacting File Geodatabases...")
        arcpy.Compact_management(wcGDB_path)
        AddMsgAndPrint("\tSuccessful",0)
    except:
        pass

except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested. Exiting...")

except:
    errorMsg()
