## ===============================================================================================================
## Name:    Download Soil Data
## Purpose: Download SSURGO layers for the project
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
## rev. 08/24/2021
## - Moved DEM and DEM derivative processing to a standalone tool.
##
## rev. 09/07/2021
## - Added Excel Export to project folder.
## - Added survey version to the output table (per the getSSURGO_WCT_ArcGISpro tool).
## - Changed SSURGO Date output on layout to Survey Area Version, per feedback and policy team
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
    f.write("\tSoil Properties Selected: " + str(propertyList) + "\n")
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


#### Update Environments
arcpy.AddMessage("Setting Environments...\n")
arcpy.SetProgressorLabel("Setting Environments...")

# Set overwrite flag
arcpy.env.overwriteOutput = True

# Test for Pro project.
try:
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    m = aprx.listMaps("Determinations")[0]
except:
    arcpy.AddError("\nThis tool must be run from an active ArcGIS Pro project that was developed from the template distributed with this toolbox. Exiting...\n")
    exit()

# Test for soil map layout (to update SSURGO Version)
try:
    soil_lyt = aprx.listLayouts("Soil Map")[0]
except:
    arcpy.AddError("\nCould not find soil map layout.")
    arcpy.AddError("\nThis tool must be run from an active ArcGIS Pro project that was developed from the template distributed with this toolbox. Exiting...\n")
    exit()


#### Main procedures
try:
    #### Inputs
    arcpy.AddMessage("Reading inputs...")
    arcpy.SetProgressorLabel("Reading inputs...")
    
    sourceCLU = arcpy.GetParameterAsText(0)
    dataExtent = arcpy.GetParameterAsText(1)
    propertyList = arcpy.GetParameter(2)



    #### Set base path
    sourceCLU_path = arcpy.Describe(sourceCLU).CatalogPath
    if sourceCLU_path.find('.gdb') > 0 and sourceCLU_path.find('Determinations') > 0 and sourceCLU_path.find('Site_CLU') > 0:
        basedataGDB_path = sourceCLU_path[:sourceCLU_path.find('.gdb')+4]
    else:
        arcpy.AddError("\nSelected Site CLU layer is not from a Determinations project folder. Exiting...")
        exit()


##    #### Do not run if an unsaved edits exist in the target workspace
##    # Pro opens an edit session when any edit has been made and stays open until edits are committed with Save Edits.
##    # Check for uncommitted edits and exit if found, giving the user a message directing them to Save or Discard them.
##    workspace = basedataGDB_path
##    edit = arcpy.da.Editor(workspace)
##    if edit.isEditing:
##        arcpy.AddError("\nYou have an active edit session. Please Save or Discard Edits and then run this tool again. Exiting...")
##        exit()
##    del workspace, edit


    #### Define Variables
    arcpy.AddMessage("Setting variables...\n")
    arcpy.SetProgressorLabel("Setting variables...")
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

    projectSoil = basedataGDB_path + os.sep + "SSURGO_Mapunits"
    soilTable = basedataGDB_path + os.sep + "summary_soils"
##    soil_excel = wetDir + os.sep + "SSURGO_Table.xlsx"
##    soil_excel_test = wetDir + os.sep + "SSURGO_Table_Test.xlsx"

    soil_csv_name = "SSURGO_Table.csv"
    soil_csv = wetDir + os.sep + soil_csv_name
    soil_test_name = "SSURGO_Table_Test.csv"
    soil_csv_test = wetDir + os.sep + soil_test_name
    
    
    #### Set up log file path and start logging
    arcpy.AddMessage("Commence logging...\n")
    arcpy.SetProgressorLabel("Commence logging...")
    textFilePath = userWorkspace + os.sep + projectName + "_log.txt"
    logBasicSettings()


##    #### Check for open excel file and exit if it is locked
##    if os.path.exists(soil_excel):
##        try:
##            os.rename(soil_excel, soil_excel_test)
##            # Rename worked, continue
##            os.rename(soil_excel_test, soil_excel)
##        except:
##            # Rename failed, generate an error message and exit.
##            AddMsgAndPrint("\nExcel table of soils may be open or locked. Please close the file and try again. Exiting...",2)
##            exit()


    #### Check for open CSV file and exit if it is locked
    if os.path.exists(soil_csv):
        try:
            os.rename(soil_csv, soil_csv_test)
            # Rename worked, continue
            os.rename(soil_csv_test, soil_csv)
        except:
            # Rename failed, generate an error message and exit.
            AddMsgAndPrint("\nCSV table of soils may be open or locked. Please close the file and try again. Exiting...",2)
            exit()


    #### Create the projectAOI and projectAOI_B layers based on the choice selected by user input
    AddMsgAndPrint("\nBuffering extent...",0)
    arcpy.SetProgressorLabel("Buffering extent...")
    if dataExtent == "Request Extent":
        # Use the request extent to create buffers for use in data extraction
        arcpy.Buffer_analysis(projectExtent, projectAOI, bufferDist, "FULL", "", "ALL", "")
        arcpy.Buffer_analysis(projectExtent, projectAOI_B, bufferDistPlus, "FULL", "", "ALL", "")
    else:
        # Use the tract boundary to create the buffers for use in data extraction
        arcpy.Buffer_analysis(projectTract, projectAOI, bufferDist, "FULL", "", "ALL", "")
        arcpy.Buffer_analysis(projectTract, projectAOI_B, bufferDistPlus, "FULL", "", "ALL", "")


    #### Call SSURGO download script if it was selected
    AddMsgAndPrint("\nDownloading soils from SDA......",0)
    arcpy.SetProgressorLabel("Downloading soils from SDA...")
    getSSURGO_WCT_ArcGISpro.start(projectAOI, propertyList, basedataGDB_path)

    # Update SSURGO version on Soil Map Layout
    AddMsgAndPrint("\nUpdating Survey Version on Soil Map layout...",0)
    arcpy.SetProgressorLabel("Updating Survey Version on Soil Map layout...")

    fields = ['saversion','surveyareadate']
    with arcpy.da.SearchCursor(projectSoil, fields) as cursor:
        for row in cursor:
            saver = str(row[0])
            sadate = row[1]
            break
    del fields

    sadate_formatted = sadate[5:7] + "/" + sadate[8:] + "/" + sadate[0:4]
    
    SSURGO_Ver = saver + ", " + sadate_formatted
    
    #rundate = datetime.date.today().strftime('%m/%d/%Y')
    
    elm_list = []
    for elm in soil_lyt.listElements():
        elm_list.append(elm.name)

    if "SSURGO Date" not in elm_list:
        AddMsgAndPrint("\n" + soil_lyt.name + " layout does not contain the 'SSURGO Date' layout element.",2)
        AddMsgAndPrint("\n Project needs to be started from an installed and configured template or soil layout needs to be imported. Exiting...",2)
        exit()
    else:
        for elm in soil_lyt.listElements():
            if elm.name == "SSURGO Date":
                sdate_elm = elm

        sdate_elm.text = "Survey Version: " + SSURGO_Ver
        #sdate_elm.text = "SSURGO Version: " + rundate


    #### Export a CSV table of the soil map units in the project extent
    AddMsgAndPrint("\nCreating CSV Table of soils...",0)
    arcpy.SetProgressorLabel("Creating CSV Table of soils...")
    
    # Find and clean up the list of fields in the soils layer
    soil_fields = arcpy.ListFields(projectSoil)
    remove_fields = ["OBJECTID", "Shape", "Shape_Length", "Shape_Area"]
    for bad_fld in remove_fields:
        for fld in soil_fields:
            if bad_fld == fld.name:
                soil_fields.remove(fld)
    soil_fld_names = []
    for fld in soil_fields:
        soil_fld_names.append(fld.name)
        
    # Run frequency to clean up matching records
    arcpy.analysis.Frequency(projectSoil, soilTable, soil_fld_names)

##    # Convert results to Excel
##    arcpy.conversion.TableToExcel(soilTable, soil_excel, "ALIAS")

    # Convert results to CSV
    if arcpy.Exists(soil_csv):
        arcpy.management.Delete(soil_csv)
    arcpy.conversion.TableToTable(soilTable, wetDir, soil_csv_name)

    
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
