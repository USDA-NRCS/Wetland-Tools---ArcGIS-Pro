## ===============================================================================================================
## Name:    Update GeoPortal Layers
## Purpose: Updates layers on GeoPortal with results from the current determination project, including all support
##          layers and all layers needed for running the dashboards. Target Hosted Feature Services from input
##          parameters should be state base hosted feature service views for a group of users defined by state.
##
## Authors: Chris Morse
##          GIS Specialist
##          Indianapolis State Office
##          USDA-NRCS
##          chris.morse@usda.gov
##          317.295.5849
##
## Created: 04/12/2021
##
## ===============================================================================================================
## Changes
## ===============================================================================================================
##
## rev. 04/12/2021
## -Replaces the Upload to State Office tool from previous ArcMap based tools.
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
    f.write("Executing Create CWD Mapping Layers tool...\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("User Parameters:\n")
    f.write("\tInput CWD Layer: " + str(sourceCWD) + "\n")
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
def check_id(in_lyr, hfs_lyr, job_id):
    # Search the HFS layer for features with the current job_id and delete those features if found
    where_clause = "job_id = '" + job_id + "'"
    arcpy.MakeFeatureLayer_management(hfs_lyr, "temp_lyr", where_clause)
    result = int(arcpy.GetCount_management("temp_lyr").getOutput(0))
    if result > 0:
        arcpy.SelectLayerByAttribute_management("temp_lyr", "NEW_SELECTION", where_clause)
        selections = int(arcpy.GetCount_management("temp_lyr").getOutput(0))
        try:
            arcpy.DeleteRows("temp_lyr")
        except:
            AddMsgAndPrint("\nOne or more feature services is returning a general function failure.",2)
            AddMsgAndPrint("\nContact your State GIS Specialist for assistance. Exiting...",2)
            arcpy.Delete_management("temp_lyr")
            deleteTempLayers(tempLayers)
            exit()
    # Delete was successful. Delete the temp layer and return to the script
    arcpy.Delete_management("temp_lyr")

## ===============================================================================================================
def update_server_polys(proj_lyr, target_hfs, local_temp):
##    # Manage the local_temp in case this was previously run and crashed
    if arcpy.Exists(local_temp):
        # Check wheter the existing temp layer CONTAINS anything on the server.
        # If not, append it to the server to restore lost features on the server
        temp_lyr1 = arcpy.SelectLayerByLocation_management(target_hfs, 'CONTAINS', local_temp, "", "NEW_SELECTION")
        result = int(arcpy.GetCount_management(temp_lyr1).getOutput(0))
        if result == 0:
            arcpy.Append_management(local_temp, target_hfs, 'NO_TEST')
            arcpy.Delete_management(local_temp)
            arcpy.Delete_management(temp_lyr1)
        else:
            # The server features take precedence and will be re-acquired.
            arcpy.Delete_management(local_temp)
            arcpy.Delete_management(temp_lyr1)
        del result

    # Do a select by location with INTERSECT type to see if there is any overlap between proj_lyr and the target_hfs
    temp_lyr2 = arcpy.SelectLayerByLocation_management(target_hfs, 'INTERSECT', proj_lyr, "", "NEW_SELECTION")
    result = int(arcpy.GetCount_management(temp_lyr2).getOutput(0))
    if result > 0:
        # Intersecting features were found. Copy the current selections to the local layer
        arcpy.CopyFeatures_management(temp_lyr2, local_temp)
        # Delete the selected features on the server.
        arcpy.DeleteRows(temp_lyr2)
        # Erase the overlapping part of the local_temp layer
        arcpy.Erase_analysis(local_temp, proj_lyr, server_multi)
        result = int(arcpy.GetCount_management(server_multi).getOutput(0))
        if result > 0:
            # Erase left features outside of the current project extent
            arcpy.MultipartToSinglepart_management(server_multi, server_single)
            expression = "!Shape.Area@acres!"
            arcpy.CalculateField_management(server_single, "acres", expression, "PYTHON_9.3")
            del expression
            # Copy the finished layer ready for appending back to the local temp layer, prior to upload, in case of a fail
            arcpy.CopyFeatures_management(server_single, local_temp)
            # Append the singlepart back to the server
            arcpy.Append_management(server_single, target_hfs, "NO_TEST")
            # Append the proj_lyr features to the server
            arcpy.Append_management(proj_lyr, target_hfs, "NO_TEST")
            arcpy.Delete_management(server_multi)
            arcpy.Delete_management(server_single)
        else:
            # The new features completely replace the old features. Append the new features.
            arcpy.Append_management(proj_lyr, target_hfs, "NO_TEST")
            arcpy.Delete_management(server_multi)
    # Clean up the select by location layer
    arcpy.Delete_management(temp_lyr2)

## ===============================================================================================================
#### Import system modules
import arcpy, sys, os, traceback, re, shutil, csv
from importlib import reload
sys.dont_write_bytecode=True
scriptPath = os.path.dirname(sys.argv[0])
sys.path.append(scriptPath)

import extract_CLU_by_Tract
reload(extract_CLU_by_Tract)


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


#### Check GeoPortal Connection
#nrcsPortal = 'https://gis.sc.egov.usda.gov/portal/'     # GeoPortal Production
#if not portalToken:
#arcpy.AddError("Could not generate Portal token! Please login or switch active portal to GeoPortal! Exiting...")
#exit()

nrcsPortal = 'https://gis-staging.usda.net/portal/'     # Staging/Training
portalToken = extract_CLU_by_Tract.getPortalTokenInfo(nrcsPortal)
if not portalToken:
    arcpy.AddError("Could not generate Portal token! Please login or switch active portal to GIS-Staging! Exiting...")
    exit()
    

#### Main procedures
try:
    #### Inputs
    arcpy.AddMessage("Reading inputs...\n")
    sourceCWD = arcpy.GetParameterAsText(0)
    ext_HFS = arcpy.GetParameterAsText(1)
    extp_HFS = arcpy.GetParameterAsText(2)
    su_HFS = arcpy.GetParameterAsText(3)
    sua_HFS = arcpy.GetParameterAsText(4)
    rop_HFS = arcpy.GetParameterAsText(5)
    rp_HFS = arcpy.GetParameterAsText(6)
    drains_HFS = arcpy.GetParameterAsText(7)
    cwd_HFS = arcpy.GetParameterAsText(8)
    cwda_HFS = arcpy.GetParameterAsText(9)
    cwdp_HFS = arcpy.GetParameterAsText(10)
    pjw_HFS = arcpy.GetParameterAsText(11)

    #### Initial Validations
    arcpy.AddMessage("Verifying inputs...\n")
    
                
    #### Set base path
    sourceCWD_path = arcpy.Describe(sourceCWD).CatalogPath
    if sourceCWD_path.find('.gdb') > 0 and sourceCWD_path.find('Determinations') > 0 and sourceCWD_path.find('Site_CWD') > 0:
        wcGDB_path = sourceCWD_path[:sourceCWD_path.find('.gdb')+4]
    else:
        arcpy.AddError("\nSelected CWD layer is not from a Determinations project folder. Exiting...")
        exit()


    #### Define Variables
    arcpy.AddMessage("Setting variables...\n")
    supportGDB = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb")
    scratchGDB = os.path.join(os.path.dirname(sys.argv[0]), "SCRATCH.gdb")

    wetDir = os.path.dirname(wcGDB_path)
    userWorkspace = os.path.dirname(wetDir)
    projectName = os.path.basename(userWorkspace).replace(" ", "_")

    arcpy.AddMessage("Debugging...")
    
    wcGDB_name = os.path.basename(userWorkspace).replace(" ", "_") + "_WC.gdb"
    wcGDB_path = wetDir + os.sep + wcGDB_name
    wcFD_name = "WC_Data"
    wcFD = wcGDB_path + os.sep + wcFD_name
    
    basedataGDB_path = userWorkspace + os.sep + projectName + "_BaseData.gdb"
    basedataGDB_name = os.path.basename(basedataGDB_path)
    basedataFD_name = "Layers"
    basedataFD = basedataGDB_path + os.sep + basedataFD_name

    extentName = "Request_Extent"
    projectExtent = basedataFD + os.sep + extentName
    
    suName = "Site_Sampling_Units"
    projectSU = wcFD + os.sep + suName

    drainName = "Site_Drainage_Lines"
    projectLines = wcFD + os.sep + drainName

    ropName = "Site_ROPs"
    projectROP = wcFD + os.sep + ropName

    refName = "Site_Reference_Points"
    projectREF = wcFD + os.sep + refName
    
    cwdName = "Site_CWD"
    projectCWD = wcFD + os.sep + cwdName
    projectCWD_pts = wcFD + os.sep + "Site_CWD_Points"
    cwd_pub_name = "Publish_CWD"
    publishCWD = wcFD + os.sep + cwd_pub_name
    cwd_server_copy = wcFD + os.sep + "CWD_Server"

    pjwName = "Site_PJW"
    projectPJW = wcFD + os.sep + pjwName

    cluCwdName = "Site_CLU_CWD"
    cluCWD = wcFD + os.sep + cluCwdName
    
    prevCert = wcFD + os.sep + "Previous_CWD"
    psc_name = "Site_Previous_CWD"
    prevCertSite = wcFD + os.sep + psc_name
    pccsName = "Site_Previous_CLU_CWD"
    prevCluCertSite = wcFD + os.sep + pccsName

    prevAdmin = wcFD + os.sep + "Previous_Admin"
    prevAdminSite = wcFD + os.sep + "Site_Previous_Admin"
    updatedCert = wcFD + os.sep + "Updated_Cert"
    updatedAdmin = wcFD + os.sep + "Updated_Admin"

    cwd_temp1 = scratchGDB + os.sep + "cwd_temp1"
    cwd_temp2 = scratchGDB + os.sep + "cwd_temp2"
    server_multi = scracthGDB + os.sep + "server_multi"
    server_single = scratchGDB + os.sep + "server_single"

    # Temp layers list for cleanup at the start and at the end
    tempLayers = [cwd_temp1, cwd_temp2, server_multi, server_single]
    deleteTempLayers(tempLayers)


    #### Set up log file path and start logging
    arcpy.AddMessage("Commence logging...\n")
    textFilePath = userWorkspace + os.sep + projectName + "_log.txt"
    logBasicSettings()

        
    #### Check Project Integrity
    AddMsgAndPrint("\nChecking project integrity...",0)

    # If project wetlands geodatabase and feature dataset do not exist, exit.
    if not arcpy.Exists(wcGDB_path):
        AddMsgAndPrint("\tInput Site CWD layer is not part of a wetlands tool project folder. Exiting...",2)
        exit()

    if not arcpy.Exists(wcFD):
        AddMsgAndPrint("\tInput Site CWD layer is not part of a wetlands tool project folder. Exiting...",2)
        exit()


    #### Get the current job_id for use in processing
    fields = ['job_id']
    cursor = arcpy.da.SearchCursor(wetDetTable, fields)
    for row in cursor:
        cur_id = row[0]
        break
    del cursor, fields
    
    
    #### Process the CWD layer
    AddMsgAndPrint("\nPreparing the CWD layer for uploading...",0)
    # Update a copy to add more attributes needed for dashboard linking and summarizing
    # Intersect with the SCA Teams layer to pick up teams (output is cwd_temp1)
    # Intersect with the SCA Areas layer to pick up areas (output is cwd_temp2)
    # Create the publishCWD layer from a template layer and append features to it.
    arcpy.CreateFeatureClass_management()
    arcpy.AddField_management(publishCWD, "FIPSTRACT", "TEXT", "", "", 24)
    arcpy.AddField_management(publishCWD, "FIPSNUM", "LONG")

    expression = "!admin_state! + !admin_county! + !tract_number!"
    arcpy.CacluateField_management(publishCWD, "FIPSTRACT", expression, "PYTHON_9.3")
    del expression

    expression = "int(!admin_state! + !admin_county!)"
    arcpy.CacluateField_management(publishCWD, "FIPSNUM", expression, "PYTHON_9.3")
    del expression
    
    
    check_id(projectCWD, cwd_HFS, cur_id)
    update_server_polys(projectCWD, cwd_HFS, cwd_server_copy)

    # Update the CWD archive layer with the current projectCWD work
    check_id(projectCWD, cwda_HFS, cur_id)
    arcpy.Append_management(projectCWD, cwda_HFS, 'NO_TEST')
    
    # Convert the projectCWD layer to a points version to prep the points for upload
    arcpy.FeatureToPoint_management(projectCWD, projectCWD_pts, 'INSIDE')
    #### ADD MORE CODE TO CREATE ADDITIONAL FIPSTRACT, ETC... FIELDS FOR DAHSBOARDS ####
    #### NOTE: May need to add FIPSTRACT and other such fields to the standard data model for Request Extent & CWD layers ####
    #### ADD MORE CODE TO INTERSECT/JOIN IT WITH THE GEOPORTAL SCA LAYER TO PICK UP ####

    # Create a job extent by dissolving the project CWD layer to update the extent related hosted feature services
    
    
    


    #### Clean up Temporary Datasets
    # Temporary datasets specifically from this tool
    AddMsgAndPrint("\nCleaning up temporary data...",0)
    deleteTempLayers(tempLayers)

    # Look for and delete anything else that may remain in the installed SCRATCH.gdb
    startWorkspace = arcpy.env.workspace
    arcpy.env.workspace = scratchGDB
    fcs = []
    for fc in arcpy.ListFeatureClasses('*'):
        fcs.append(os.path.join(scratchGDB, fc))
    for fc in fcs:
        if arcpy.Exists(fc):
            try:
                arcpy.Delete_management(fc)
            except:
                pass
    arcpy.env.workspace = startWorkspace
    del startWorkspace

    
    #### Compact FGDB
    try:
        AddMsgAndPrint("\nCompacting File Geodatabases..." ,0)
        arcpy.Compact_management(basedataGDB_path)
        arcpy.Compact_management(wcGDB_path)
        arcpy.Compact_management(scratchGDB)
        AddMsgAndPrint("\tSuccessful",0)
    except:
        pass


except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested. Exiting...")

except:
    errorMsg()
