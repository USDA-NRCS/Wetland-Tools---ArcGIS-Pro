## ===============================================================================================================
## Name:    Export Soil Table
## Purpose: Export Excel Table of the Soil Map unit layer from the project
##
##          Chris Morse
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
## rev. 09/07/2021
## - Added Excel Export to project folder.
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
    f.write("Executing Soils - Export to Excel tool...\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("User Parameters:\n")
    f.write("\tWorkspace: " + userWorkspace + "\n")
    f.close
    del f

## ===============================================================================================================
#### Import system modules
import arcpy, sys, os, traceback, re


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


#### Main procedures
try:
    #### Inputs
    arcpy.AddMessage("Reading inputs...")
    arcpy.SetProgressorLabel("Reading inputs...")
    
    sourceCLU = arcpy.GetParameterAsText(0)

    #### Set base path
    sourceCLU_path = arcpy.Describe(sourceCLU).CatalogPath
    if sourceCLU_path.find('.gdb') > 0 and sourceCLU_path.find('Determinations') > 0 and sourceCLU_path.find('Site_CLU') > 0:
        basedataGDB_path = sourceCLU_path[:sourceCLU_path.find('.gdb')+4]
    else:
        arcpy.AddError("\nSelected Site CLU layer is not from a Determinations project folder. Exiting...")
        exit()

    #### Define Variables
    arcpy.AddMessage("Setting variables...\n")
    arcpy.SetProgressorLabel("Setting variables...")

    userWorkspace = os.path.dirname(basedataGDB_path)
    projectName = os.path.basename(userWorkspace).replace(" ", "_")
    wetDir = userWorkspace + os.sep + "Wetlands"

    projectSoil = basedataGDB_path + os.sep + "SSURGO_Mapunits"
    soilTable = basedataGDB_path + os.sep + "summary_soils"
    soil_excel = wetDir + os.sep + "SSURGO_Table.xlsx"
    soil_excel_test = wetDir + os.sep + "SSURGO_Table_Test.xlsx"
    
    
    #### Set up log file path and start logging
    arcpy.AddMessage("Commence logging...\n")
    arcpy.SetProgressorLabel("Commence logging...")
    textFilePath = userWorkspace + os.sep + projectName + "_log.txt"
    logBasicSettings()


    #### Check for open excel file and exit if it is locked
    if os.path.exists(soil_excel):
        try:
            os.rename(soil_excel, soil_excel_test)
            # Rename worked, continue
            os.rename(soil_excel_test, soil_excel)
        except:
            # Rename failed, generate an error message and exit.
            AddMsgAndPrint("\nExcel table of soils may be open or locked. Please close the file and try again. Exiting...",2)
            exit()


    #### Export an excel table of the soil map units in the project extent
    AddMsgAndPrint("\nCreating Excel Table of soils...",0)
    arcpy.SetProgressorLabel("Creating Excel Table of soils...")
    
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

    # Convert results to Excel
    arcpy.conversion.TableToExcel(soilTable, soil_excel, "ALIAS")
    

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
