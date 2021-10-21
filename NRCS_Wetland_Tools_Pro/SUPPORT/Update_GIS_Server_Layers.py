## ===============================================================================================================
## Name:    Update GIS Server Layers
## Purpose: Updates layers on GeoPortal with results from the current determination project, including all support
##          layers and all layers needed for running the dashboards.
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
## - Replaces the Upload to State Office tool from previous ArcMap based tools.
##
## rev. 08/27/2021
## - Updated all functions and test against GIS States.
## - Updated processing for all layers
## - Incorporated Field Mapping to manage the mismatched GlobalID to globalid field names from local to web
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
    f.write("Executing Update GIS Server Layers tool...\n")
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
    #AddMsgAndPrint("\nChecking Job_ID of " + in_lyr + "layer...",0)
    where_clause = "job_id = '" + job_id + "'"
    arcpy.MakeFeatureLayer_management(hfs_lyr, "temp_lyr", where_clause)
    result = int(arcpy.GetCount_management("temp_lyr").getOutput(0))
    if result > 0:
        arcpy.SelectLayerByAttribute_management("temp_lyr", "NEW_SELECTION", where_clause)
        selections = int(arcpy.GetCount_management("temp_lyr").getOutput(0))
        try:
            arcpy.DeleteRows_management("temp_lyr")
        except:
            AddMsgAndPrint("\nOne or more feature services is returning a general function failure and may be offline or inaccessible.",2)
            AddMsgAndPrint("\nContact your State GIS Specialist for assistance. Exiting...",2)
            arcpy.Delete_management("temp_lyr")
            #deleteTempLayers(tempLayers)
            exit()
    # Delete was successful. Delete the temp layer and return to the script
    arcpy.Delete_management("temp_lyr")

## ===============================================================================================================
def update_polys(proj_lyr, target_hfs, local_temp, fldmapping=''):
    #AddMsgAndPrint("\nProcessing data from " + proj_lyr + " layer...",0)
    # Manage the local_temp in case this was previously run and crashed
    if arcpy.Exists(local_temp):
        # Check whether the existing temp layer CONTAINS anything on the server.
        # If not, append it to the server to restore lost features on the server
        temp_lyr1 = arcpy.SelectLayerByLocation_management(target_hfs, 'CONTAINS', local_temp, "", "NEW_SELECTION")
        result = int(arcpy.GetCount_management(temp_lyr1).getOutput(0))
        if result == 0:
            # fldmapping not needed on this append because local_temp was created from the server layer's schema
            arcpy.SelectLayerByAttribute_management(target_hfs, "CLEAR_SELECTION")
            arcpy.Append_management(local_temp, target_hfs, "NO_TEST")
            arcpy.Delete_management(local_temp)
            del temp_lyr1
        else:
            # The server features take precedence and will be re-acquired.
            arcpy.Delete_management(local_temp)
            del temp_lyr1
        del result

    # Do a select by location with INTERSECT type to see if there is any overlap between proj_lyr and the target_hfs
    temp_lyr2 = arcpy.SelectLayerByLocation_management(target_hfs, 'INTERSECT', proj_lyr, "", "NEW_SELECTION")
    result = int(arcpy.GetCount_management(temp_lyr2).getOutput(0))
    if result > 0:
        # Intersecting features were found. Copy the current selections to the local layer
        arcpy.CopyFeatures_management(temp_lyr2, local_temp)
        # Delete the selected features on the server.
        arcpy.DeleteRows_management(temp_lyr2)
        # Erase the part of the local_temp layer that overlaps with the project layer
        arcpy.Erase_analysis(local_temp, proj_lyr, server_multi)
        result = int(arcpy.GetCount_management(server_multi).getOutput(0))
        if result > 0:
            # The Erase attempt left additional features outside of the current project extent, update their integrity and measurments
            arcpy.MultipartToSinglepart_management(server_multi, server_single)
            expression = "round(!Shape.Area@acres!,2)"
            arcpy.CalculateField_management(server_single, "acres", expression, "PYTHON_9.3")
            del expression
            # Copy the residual server intersected features to the local temp layer as a backup step before upload
            arcpy.CopyFeatures_management(server_single, local_temp)
            # Append the residual server intersected features back to the server; fldmapping should not be needed
            arcpy.Append_management(server_single, target_hfs, "NO_TEST")
            # Now Append the proj_lyr features to the server, including the fldmapping
            if fldmapping != '':
                arcpy.Append_management(proj_lyr, target_hfs, "NO_TEST", fldmapping)
            else:
                arcpy.Append_management(proj_lyr, target_hfs, "NO_TEST")
            arcpy.Delete_management(server_multi)
            arcpy.Delete_management(server_single)
        else:
            # The new features completely replace the old features. Append the new features.
            arcpy.Append_management(proj_lyr, target_hfs, "NO_TEST", fldmapping)
            arcpy.Delete_management(server_multi)

    else:
        # The project features don't intersect any server features. Append the new features.
        arcpy.Append_management(proj_lyr, target_hfs, "NO_TEST", fldmapping)

    # Clean up the select by location object
    del temp_lyr2

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
    arcpy.AddError("\nThis tool must be run from an active ArcGIS Pro project that was developed from the template distributed with this toolbox. Exiting...\n")
    exit()


#### Check GeoPortal Connection
#nrcsPortal = 'https://gis-states.sc.egov.usda.gov/portal/'     # GeoPortal States Production 10.8.1
#if not portalToken:
#arcpy.AddError("Could not generate Portal token! Please login or switch active portal to GeoPortal States 10.8.1! Exiting...")
#exit()

nrcsPortal = 'https://gis-testing.usda.net/portal/'     # GeoPortal Sandbox Testing 10.8.1
portalToken = extract_CLU_by_Tract.getPortalTokenInfo(nrcsPortal)
if not portalToken:
    arcpy.AddError("Could not generate Portal token! Please login or switch active portal to GIS-Testing 10.8.1! Exiting...")
    exit()
    

#### Main procedures
try:
    #### Inputs
    arcpy.AddMessage("Reading inputs...\n")
    sourceCWD = arcpy.GetParameterAsText(0)
    ext_HFS = arcpy.GetParameterAsText(1)
    extA_HFS = arcpy.GetParameterAsText(2)
    su_HFS = arcpy.GetParameterAsText(3)
    suA_HFS = arcpy.GetParameterAsText(4)
    rop_HFS = arcpy.GetParameterAsText(5)
    ropA_HFS = arcpy.GetParameterAsText(6)
    rp_HFS = arcpy.GetParameterAsText(7)
    rpA_HFS = arcpy.GetParameterAsText(8)
    drains_HFS = arcpy.GetParameterAsText(9)
    drainsA_HFS = arcpy.GetParameterAsText(10)
    cwd_HFS = arcpy.GetParameterAsText(11)
    cwdA_HFS = arcpy.GetParameterAsText(12)
    pjw_HFS = arcpy.GetParameterAsText(13)
    pjwA_HFS = arcpy.GetParameterAsText(14)
    clucwd_HFS = arcpy.GetParameterAsText(15)
    clucwdA_HFS = arcpy.GetParameterAsText(16)


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
    arcpy.SetProgressorLabel("VSetting variables...")
    supportGDB = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb")
    scratchGDB = os.path.join(os.path.dirname(sys.argv[0]), "SCRATCH.gdb")

    wetDir = os.path.dirname(wcGDB_path)
    userWorkspace = os.path.dirname(wetDir)
    projectName = os.path.basename(userWorkspace).replace(" ", "_")
    
    wcGDB_name = os.path.basename(userWorkspace).replace(" ", "_") + "_WC.gdb"
    wcGDB_path = wetDir + os.sep + wcGDB_name
    wcFD_name = "WC_Data"
    wcFD = wcGDB_path + os.sep + wcFD_name
    
    basedataGDB_path = userWorkspace + os.sep + projectName + "_BaseData.gdb"
    basedataGDB_name = os.path.basename(basedataGDB_path)
    basedataFD_name = "Layers"
    basedataFD = basedataGDB_path + os.sep + basedataFD_name

    projectTable = basedataGDB_path + os.sep + "Table_" + projectName
    wetDetTableName = "Admin_Table"
    wetDetTable = wcGDB_path + os.sep + wetDetTableName
    
    extentName = "Request_Extent"
    projectExtent = basedataFD + os.sep + extentName
    ext_server_copy = wcFD + os.sep + "Ext_Server"
    
    suName = "Site_Sampling_Units"
    projectSU = wcFD + os.sep + suName
    su_server_copy = wcFD + os.sep + "SU_Server"

    drainName = "Site_Drainage_Lines"
    projectLines = wcFD + os.sep + drainName

    ropName = "Site_ROPs"
    projectROP = wcFD + os.sep + ropName

    refName = "Site_Reference_Points"
    projectREF = wcFD + os.sep + refName
    
    cwdName = "Site_CWD"
    projectCWD = wcFD + os.sep + cwdName
    #projectCWD_pts = wcFD + os.sep + "Site_CWD_Points"
    #cwd_pub_name = "Publish_CWD"
    #publishCWD = wcFD + os.sep + cwd_pub_name
    cwd_server_copy = wcFD + os.sep + "CWD_Server"

    pjwName = "Site_PJW"
    projectPJW = wcFD + os.sep + pjwName

    cluCwdName = "Site_CLU_CWD"
    projectCLUCWD = wcFD + os.sep + cluCwdName
    clucwd_server_copy = wcFD + os.sep + "CLUCWD_Server"
    
    prevCert = wcFD + os.sep + "Previous_CWD"
    pcs_name = "Site_Previous_CWD"
    prevCertSite = wcFD + os.sep + pcs_name
    pccsName = "Site_Previous_CLU_CWD"
    prevCluCertSite = wcFD + os.sep + pccsName

    prevAdmin = wcFD + os.sep + "Previous_Admin"
    prevAdminSite = wcFD + os.sep + "Site_Previous_Admin"
    updatedCert = wcFD + os.sep + "Updated_Cert"
    updatedAdmin = wcFD + os.sep + "Updated_Admin"

    server_multi = scratchGDB + os.sep + "server_multi"
    server_single = scratchGDB + os.sep + "server_single"

    # Temp layers list for cleanup at the start and at the end
    tempLayers = [server_multi, server_single]
    #deleteTempLayers(tempLayers)


    #### Set up log file path and start logging
    arcpy.AddMessage("Commence logging...\n")
    textFilePath = userWorkspace + os.sep + projectName + "_log.txt"
    logBasicSettings()

        
    #### Check Project Integrity
    AddMsgAndPrint("\nChecking project integrity...",0)
    arcpy.SetProgressorLabel("Checking project integrity...")

    # If project wetlands geodatabase and feature dataset do not exist, exit.
    if not arcpy.Exists(wcGDB_path):
        AddMsgAndPrint("\tInput Site CWD layer is not part of a wetlands tool project folder. Exiting...",2)
        exit()

    if not arcpy.Exists(wcFD):
        AddMsgAndPrint("\tInput Site CWD layer is not part of a wetlands tool project folder. Exiting...",2)
        exit()


    #### Count the features of the input layers.
    # Extent, SU, ROP, CWD, and CLUCWD must have at least 1 feature, else exit.
    if not arcpy.Exists(projectExtent):
        AddMsgAndPrint("\tRequest Extent layer does not exist. Exiting...",2)
        exit()
    else:
        ext_count = int(arcpy.management.GetCount(projectExtent)[0])

    if not arcpy.Exists(projectSU):
        AddMsgAndPrint("\tSampling Units layer does not exist. Exiting...",2)
        exit()
    else:
        su_count = int(arcpy.management.GetCount(projectSU)[0])
        
    if not arcpy.Exists(projectROP):
        AddMsgAndPrint("\tROPs layer does not exist. Exiting...",2)
        exit()
    else:
        rop_count = int(arcpy.management.GetCount(projectROP)[0])

    if not arcpy.Exists(projectLines):
        AddMsgAndPrint("\tDrainage Lines layer does not exist. Exiting...",2)
        exit()
    else:
        dl_count = int(arcpy.management.GetCount(projectLines)[0])

    if not arcpy.Exists(projectREF):
        AddMsgAndPrint("\tReference Points layer does not exist. Exiting...",2)
        exit()
    else:
        ref_count = int(arcpy.management.GetCount(projectREF)[0])

    if not arcpy.Exists(projectPJW):
        AddMsgAndPrint("\tPJW layer does not exist. Exiting...",2)
        exit()
    else:
        pjw_count = int(arcpy.management.GetCount(projectPJW)[0])

    if not arcpy.Exists(projectCWD):
        AddMsgAndPrint("\tCWD layer does not exist. Exiting...",2)
        exit()
    else:
        cwd_count = int(arcpy.management.GetCount(projectCWD)[0])

    if not arcpy.Exists(projectCLUCWD):
        AddMsgAndPrint("\tCLU CWD layer does not exist. Exiting...",2)
        exit()
    else:
        clucwd_count = int(arcpy.management.GetCount(projectCLUCWD)[0])

    if ext_count == 0 or su_count == 0 or rop_count == 0 or cwd_count == 0 or clucwd_count == 0:
        AddMsgAndPrint("\tOne or more critical business layers contains no feature data. Please complete the entire workflow prior to upload.",2)
        AddMsgAndPrint("\tRequest Extent: " + str(ext_count) + " features.",2)
        AddMsgAndPrint("\tSampling Units: " + str(su_count) + " features.",2)
        AddMsgAndPrint("\tROPs: " + str(rop_count) + " features.",2)
        AddMsgAndPrint("\tCWD: " + str(cwd_count) + " features.",2)
        AddMsgAndPrint("\tCLU CWD: " + str(clucwd_count) + " features.",2)
        AddMsgAndPrint("\tExiting...",2)
        exit()

    
    #### Get the current job_id for use in processing
    cur_id = ''
    fields = ['job_id']
    cursor = arcpy.da.SearchCursor(wetDetTable, fields)
    for row in cursor:
        cur_id = row[0]
        break
    del cursor, fields

    if cur_id == '':
        AddMsgAndPrint("\tJob_ID could not be retrieved from admin table. Exiting...",2)
        exit()


    #### Build field mapping objects that will be needed
    AddMsgAndPrint("\nBuilding field mappings...",0)
    arcpy.SetProgressorLabel("Building field mappings...")
    field_mapping_cwd_to_hfs="globalid \"GlobalID\" false false true 38 GlobalID 0 0,First,#,Site_CWD,GlobalID,-1,-1;job_id \"Job ID\" true true false 128 Text 0 0,First,#,Site_CWD,job_id,0,128;admin_state \"Admin State\" true true false 2 Text 0 0,First,#,Site_CWD,admin_state,0,2;admin_state_name \"Admin State Name\" true true false 64 Text 0 0,First,#,Site_CWD,admin_state_name,0,64;admin_county \"Admin County\" true true false 3 Text 0 0,First,#,Site_CWD,admin_county,0,3;admin_county_name \"Admin County Name\" true true false 64 Text 0 0,First,#,Site_CWD,admin_county_name,0,64;state_code \"State Code\" true true false 2 Text 0 0,First,#,Site_CWD,state_code,0,2;state_name \"State Name\" true true false 64 Text 0 0,First,#,Site_CWD,state_name,0,64;county_code \"County Code\" true true false 3 Text 0 0,First,#,Site_CWD,county_code,0,3;county_name \"County Name\" true true false 64 Text 0 0,First,#,Site_CWD,county_name,0,64;farm_number \"Farm Number\" true true false 7 Text 0 0,First,#,Site_CWD,farm_number,0,7;tract_number \"Tract Number\" true true false 7 Text 0 0,First,#,Site_CWD,tract_number,0,7;eval_status \"Evaluation Status\" true true false 24 Text 0 0,First,#,Site_CWD,eval_status,0,24;wetland_label \"Wetland Label\" true true false 12 Text 0 0,First,#,Site_CWD,wetland_label,0,12;occur_year \"Occurrence Year\" true true false 4 Text 0 0,First,#,Site_CWD,occur_year,0,4;acres \"Acres\" true true false 0 Double 0 0,First,#,Site_CWD,acres,-1,-1;three_factors \"3-Factors\" true true false 1 Text 0 0,First,#,Site_CWD,three_factors,0,1;request_date \"Request Date\" true true false 29 Date 0 0,First,#,Site_CWD,request_date,-1,-1;request_type \"Request Type\" true true false 12 Text 0 0,First,#,Site_CWD,request_type,0,12;deter_method \"Determination Method\" true true false 24 Text 0 0,First,#,Site_CWD,deter_method,0,24;deter_staff \"Determination Staff\" true true false 100 Text 0 0,First,#,Site_CWD,deter_staff,0,100;dig_staff \"Digitizing Staff\" true true false 100 Text 0 0,First,#,Site_CWD,dig_staff,0,100;dig_date \"Digitizing Date\" true true false 29 Date 0 0,First,#,Site_CWD,dig_date,-1,-1;cwd_comments \"Comments\" true true false 255 Text 0 0,First,#,Site_CWD,cwd_comments,0,255;cert_date \"Certification Date\" true true false 0 Double 0 0,First,#,Site_CWD,cert_date,-1,-1"
    field_mapping_su_to_hfs="globalid \"GlobalID\" false false false 38 GlobalID 0 0,First,#,Site_Sampling_Units,GlobalID,-1,-1;job_id \"Job ID\" true true false 128 Text 0 0,First,#,Site_Sampling_Units,job_id,0,128;admin_state \"Admin State\" true true false 2 Text 0 0,First,#,Site_Sampling_Units,admin_state,0,2;admin_state_name \"Admin State Name\" true true false 64 Text 0 0,First,#,Site_Sampling_Units,admin_state_name,0,64;admin_county \"Admin County\" true true false 3 Text 0 0,First,#,Site_Sampling_Units,admin_county,0,3;admin_county_name \"Admin County Name\" true true false 64 Text 0 0,First,#,Site_Sampling_Units,admin_county_name,0,64;state_code \"State Code\" true true false 2 Text 0 0,First,#,Site_Sampling_Units,state_code,0,2;state_name \"State Name\" true true false 64 Text 0 0,First,#,Site_Sampling_Units,state_name,0,64;county_code \"County Code\" true true false 3 Text 0 0,First,#,Site_Sampling_Units,county_code,0,3;county_name \"County Name\" true true false 64 Text 0 0,First,#,Site_Sampling_Units,county_name,0,64;farm_number \"Farm Number\" true true false 7 Text 0 0,First,#,Site_Sampling_Units,farm_number,0,7;tract_number \"Tract Number\" true true false 7 Text 0 0,First,#,Site_Sampling_Units,tract_number,0,7;eval_status \"Evaluation Status\" true true false 24 Text 0 0,First,#,Site_Sampling_Units,eval_status,0,24;su_number \"Sampling Unit Number\" true true false 0 Long 0 0,First,#,Site_Sampling_Units,su_number,-1,-1;su_letter \"Sampling Unit Letter\" true true false 3 Text 0 0,First,#,Site_Sampling_Units,su_letter,0,3;acres \"Acres\" true true false 0 Double 0 0,First,#,Site_Sampling_Units,acres,-1,-1;associated_rop \"Associated ROP\" true true false 0 Long 0 0,First,#,Site_Sampling_Units,associated_rop,-1,-1;associated_ref \"Associated Reference Points\" true true false 255 Text 0 0,First,#,Site_Sampling_Units,associated_ref,0,255;three_factors \"3-Factors?\" true true false 1 Text 0 0,First,#,Site_Sampling_Units,three_factors,0,1;request_date \"Request_Date\" true true false 29 Date 0 0,First,#,Site_Sampling_Units,request_date,-1,-1;request_type \"Request Type\" true true false 24 Text 0 0,First,#,Site_Sampling_Units,request_type,0,24;deter_method \"Determination Method\" true true false 24 Text 0 0,First,#,Site_Sampling_Units,deter_method,0,24;deter_staff \"Determination Staff\" true true false 100 Text 0 0,First,#,Site_Sampling_Units,deter_staff,0,100;dig_staff \"Digitizing Staff\" true true false 100 Text 0 0,First,#,Site_Sampling_Units,dig_staff,0,100;dig_date \"Digitizing Date\" true true false 29 Date 0 0,First,#,Site_Sampling_Units,dig_date,-1,-1;su_comments \"Comments\" true true false 255 Text 0 0,First,#,Site_Sampling_Units,su_comments,0,255"
    field_mapping_rop_to_hfs="globalid \"GlobalID\" false false false 38 GlobalID 0 0,First,#,Site_ROPs,GlobalID,-1,-1;job_id \"Job ID\" true true false 128 Text 0 0,First,#,Site_ROPs,job_id,0,128;admin_state \"Admin State\" true true false 2 Text 0 0,First,#,Site_ROPs,admin_state,0,2;admin_state_name \"Admin State Name\" true true false 64 Text 0 0,First,#,Site_ROPs,admin_state_name,0,64;admin_county \"Admin County\" true true false 3 Text 0 0,First,#,Site_ROPs,admin_county,0,3;admin_county_name \"Admin County Name\" true true false 64 Text 0 0,First,#,Site_ROPs,admin_county_name,0,64;state_code \"State Code\" true true false 2 Text 0 0,First,#,Site_ROPs,state_code,0,2;state_name \"State Name\" true true false 64 Text 0 0,First,#,Site_ROPs,state_name,0,64;county_code \"County Code\" true true false 3 Text 0 0,First,#,Site_ROPs,county_code,0,3;county_name \"County Name\" true true false 64 Text 0 0,First,#,Site_ROPs,county_name,0,64;farm_number \"Farm Number\" true true false 7 Text 0 0,First,#,Site_ROPs,farm_number,0,7;tract_number \"Tract Number\" true true false 7 Text 0 0,First,#,Site_ROPs,tract_number,0,7;rop_number \"ROP Number\" true true false 0 Long 0 0,First,#,Site_ROPs,rop_number,-1,-1;associated_su \"Associated Sampling Units\" true true false 255 Text 0 0,First,#,Site_ROPs,associated_su,0,255;rop_comments \"Comments\" true true false 255 Text 0 0,First,#,Site_ROPs,rop_comments,0,255"
    field_mapping_ref_to_hfs="globalid \"GlobalID\" false false false 38 GlobalID 0 0,First,#,Site_Reference_Points,GlobalID,-1,-1;job_id \"Job ID\" true true false 128 Text 0 0,First,#,Site_Reference_Points,job_id,0,128;admin_state \"Admin State\" true true false 2 Text 0 0,First,#,Site_Reference_Points,admin_state,0,2;admin_state_name \"Admin State Name\" true true false 64 Text 0 0,First,#,Site_Reference_Points,admin_state_name,0,64;admin_county \"Admin County\" true true false 3 Text 0 0,First,#,Site_Reference_Points,admin_county,0,3;admin_county_name \"Admin County Name\" true true false 64 Text 0 0,First,#,Site_Reference_Points,admin_county_name,0,64;state_code \"State Code\" true true false 2 Text 0 0,First,#,Site_Reference_Points,state_code,0,2;state_name \"State Name\" true true false 64 Text 0 0,First,#,Site_Reference_Points,state_name,0,64;county_code \"County Code\" true true false 3 Text 0 0,First,#,Site_Reference_Points,county_code,0,3;county_name \"County Name\" true true false 64 Text 0 0,First,#,Site_Reference_Points,county_name,0,64;farm_number \"Farm Number\" true true false 7 Text 0 0,First,#,Site_Reference_Points,farm_number,0,7;tract_number \"Tract Number\" true true false 7 Text 0 0,First,#,Site_Reference_Points,tract_number,0,7;ref_number \"Reference Point Number\" true true false 0 Long 0 0,First,#,Site_Reference_Points,ref_number,-1,-1;parent_rop \"Parent ROP\" true true false 0 Long 0 0,First,#,Site_Reference_Points,parent_rop,-1,-1;hydro \"Documents Hydrology?\" true true false 3 Text 0 0,First,#,Site_Reference_Points,hydro,0,3;veg \"Documents Vegetation?\" true true false 3 Text 0 0,First,#,Site_Reference_Points,veg,0,3;soil \"Documents Soil?\" true true false 3 Text 0 0,First,#,Site_Reference_Points,soil,0,3;ref_comments \"Comments\" true true false 255 Text 0 0,First,#,Site_Reference_Points,ref_comments,0,255"
    field_mapping_dl_to_hfs="globalid \"GlobalID\" false false false 38 GlobalID 0 0,First,#,Site_Drainage_Lines,GlobalID,-1,-1;job_id \"Job ID\" true true false 128 Text 0 0,First,#,Site_Drainage_Lines,job_id,0,128;admin_state \"Admin State\" true true false 2 Text 0 0,First,#,Site_Drainage_Lines,admin_state,0,2;admin_state_name \"Admin State Name\" true true false 64 Text 0 0,First,#,Site_Drainage_Lines,admin_state_name,0,64;admin_county \"Admin County\" true true false 3 Text 0 0,First,#,Site_Drainage_Lines,admin_county,0,3;admin_county_name \"Admin County Name\" true true false 64 Text 0 0,First,#,Site_Drainage_Lines,admin_county_name,0,64;state_code \"State Code\" true true false 2 Text 0 0,First,#,Site_Drainage_Lines,state_code,0,2;state_name \"State Name\" true true false 64 Text 0 0,First,#,Site_Drainage_Lines,state_name,0,64;county_code \"County Code\" true true false 3 Text 0 0,First,#,Site_Drainage_Lines,county_code,0,3;county_name \"County Name\" true true false 64 Text 0 0,First,#,Site_Drainage_Lines,county_name,0,64;farm_number \"Farm Number\" true true false 7 Text 0 0,First,#,Site_Drainage_Lines,farm_number,0,7;tract_number \"Tract Number\" true true false 7 Text 0 0,First,#,Site_Drainage_Lines,tract_number,0,7;line_type \"Line Type\" true true false 50 Text 0 0,First,#,Site_Drainage_Lines,line_type,0,50;manip_era \"Era\" true true false 12 Text 0 0,First,#,Site_Drainage_Lines,manip_era,0,12;manip_year \"Manipulation Year\" true true false 4 Text 0 0,First,#,Site_Drainage_Lines,manip_year,0,4;line_length \"Length (ft)\" true true false 0 Double 0 0,First,#,Site_Drainage_Lines,line_length,-1,-1;depth \"Depth (ft)\" true true false 0 Double 0 0,First,#,Site_Drainage_Lines,depth,-1,-1;width \"Width (ft)\" true true false 0 Double 0 0,First,#,Site_Drainage_Lines,width,-1,-1;drain_comments \"Comments\" true true false 255 Text 0 0,First,#,Site_Drainage_Lines,drain_comments,0,255"
    field_mapping_clucwd_to_hfs="globalid \"GlobalID\" false false false 38 GlobalID 0 0,First,#,Site_CLU_CWD,GlobalID,-1,-1;job_id \"Job ID\" true true false 128 Text 0 0,First,#,Site_CLU_CWD,job_id,0,128;admin_state \"Admin State\" true true false 2 Text 0 0,First,#,Site_CLU_CWD,admin_state,0,2;admin_state_name \"Admin State Name\" true true false 64 Text 0 0,First,#,Site_CLU_CWD,admin_state_name,0,64;admin_county \"Admin County\" true true false 3 Text 0 0,First,#,Site_CLU_CWD,admin_county,0,3;admin_county_name \"Admin County Name\" true true false 64 Text 0 0,First,#,Site_CLU_CWD,admin_county_name,0,64;state_code \"State Code\" true true false 2 Text 0 0,First,#,Site_CLU_CWD,state_code,0,2;state_name \"State Name\" true true false 64 Text 0 0,First,#,Site_CLU_CWD,state_name,0,64;county_code \"County Code\" true true false 3 Text 0 0,First,#,Site_CLU_CWD,county_code,0,3;county_name \"County Name\" true true false 64 Text 0 0,First,#,Site_CLU_CWD,county_name,0,64;farm_number \"Farm Number\" true true false 7 Text 0 0,First,#,Site_CLU_CWD,farm_number,0,7;tract_number \"Tract Number\" true true false 7 Text 0 0,First,#,Site_CLU_CWD,tract_number,0,7;clu_number \"CLU Number\" true true false 7 Text 0 0,First,#,Site_CLU_CWD,clu_number,0,7;eval_status \"Evaluation Status\" true true false 24 Text 0 0,First,#,Site_CLU_CWD,eval_status,0,24;wetland_label \"Wetland Label\" true true false 12 Text 0 0,First,#,Site_CLU_CWD,wetland_label,0,12;occur_year \"Occurrence Year\" true true false 4 Text 0 0,First,#,Site_CLU_CWD,occur_year,0,4;acres \"Acres\" true true false 0 Double 0 0,First,#,Site_CLU_CWD,acres,-1,-1;three_factors \"3-Factors\" true true false 1 Text 0 0,First,#,Site_CLU_CWD,three_factors,0,1;request_date \"Request Date\" true true false 29 Date 0 0,First,#,Site_CLU_CWD,request_date,-1,-1;request_type \"Request Type\" true true false 12 Text 0 0,First,#,Site_CLU_CWD,request_type,0,12;deter_method \"Determination Method\" true true false 24 Text 0 0,First,#,Site_CLU_CWD,deter_method,0,24;deter_staff \"Determination Staff\" true true false 100 Text 0 0,First,#,Site_CLU_CWD,deter_staff,0,100;dig_staff \"Digitizing Staff\" true true false 100 Text 0 0,First,#,Site_CLU_CWD,dig_staff,0,100;dig_date \"Digitizing Date\" true true false 29 Date 0 0,First,#,Site_CLU_CWD,dig_date,-1,-1;clucwd_comments \"Comments\" true true false 255 Text 0 0,First,#,Site_CLU_CWD,clucwd_comments,0,255;cert_date \"Certification Date\" true true false 29 Date 0 0,First,#,Site_CLU_CWD,cert_date,-1,-1"


    #### Process the Archive Layers first with check_id and then just append features
    AddMsgAndPrint("\nProcessing Archive Layers...",0)
    arcpy.SetProgressorLabel("Processing Archive Layers...")

    # Request Extent Archive
    AddMsgAndPrint("\tArchiving the Request Extent Layer...",0)
    arcpy.SetProgressorLabel("Archiving the Reqeust Extent Layer...")
    check_id(projectExtent, extA_HFS, cur_id)
    arcpy.Append_management(projectExtent, extA_HFS, "NO_TEST")

    # Sampling Units Archive
    AddMsgAndPrint("\tArchiving the Sampling Units Layer...",0)
    arcpy.SetProgressorLabel("Archiving the Sampling Units Layer...")
    check_id(projectSU, suA_HFS, cur_id)
    arcpy.Append_management(projectSU, suA_HFS, "NO_TEST", field_mapping_su_to_hfs)

    # ROPs Archive
    AddMsgAndPrint("\tArchiving the ROPs Layer...",0)
    arcpy.SetProgressorLabel("Archiving the ROPs Layer...")
    check_id(projectROP, ropA_HFS, cur_id)
    arcpy.Append_management(projectROP, ropA_HFS, "NO_TEST", field_mapping_rop_to_hfs)
    
    # Reference Points Archive
    if ref_count > 0:
        AddMsgAndPrint("\tArchiving the Reference Points Layer...",0)
        arcpy.SetProgressorLabel("Archiving the Reference Points Layer...")
        check_id(projectREF, rpA_HFS, cur_id)
        arcpy.Append_management(projectREF, rpA_HFS, "NO_TEST", field_mapping_ref_to_hfs)

    # Drainage Lines Archive
    if dl_count > 0:
        AddMsgAndPrint("\tArchiving the Drainage Lines Layer...",0)
        arcpy.SetProgressorLabel("Archiving the Drainage Lines Layer...")
        check_id(projectLines, drainsA_HFS, cur_id)
        arcpy.Append_management(projectLines, drainsA_HFS, "NO_TEST", field_mapping_dl_to_hfs)

    # PJW Archive
    if pjw_count > 0:
        AddMsgAndPrint("\tArchiving the PJW Layer...",0)
        arcpy.SetProgressorLabel("Archiving the PJW Layer...")
        check_id(projectPJW, pjwA_HFS, cur_id)
        arcpy.Append_management(projectPJW, pjwA_HFS, "NO_TEST")

    # CWD Archive
    AddMsgAndPrint("\tArchiving the CWD Layer...",0)
    arcpy.SetProgressorLabel("Archiving the CWD Layer...")
    check_id(projectCWD, cwdA_HFS, cur_id)
    arcpy.Append_management(projectCWD, cwdA_HFS, "NO_TEST", field_mapping_cwd_to_hfs)

    # CLU_CWD Archive
    AddMsgAndPrint("\tArchiving the CLU CWD Layer...",0)
    arcpy.SetProgressorLabel("Archiving the CLU CWD Layer...")
    check_id(projectCLUCWD, clucwdA_HFS, cur_id)
    arcpy.Append_management(projectCLUCWD, clucwdA_HFS, "NO_TEST", field_mapping_clucwd_to_hfs)
    
    
    #### Process the Active Data Layers
    AddMsgAndPrint("\nProcessing Active Data Layers...",0)
    arcpy.SetProgressorLabel("Processing Active Layers...")

    # Request Extent Layer
    AddMsgAndPrint("\tUploading the Request Extent Layer...",0)
    arcpy.SetProgressorLabel("Uploading the Request Extent Layer...")
    check_id(projectExtent, ext_HFS, cur_id)
    update_polys(projectExtent, ext_HFS, ext_server_copy)

    # Sampling Units Layer
    AddMsgAndPrint("\tUploading the Sampling Units Layer...",0)
    arcpy.SetProgressorLabel("Uploading the Sampling Units Layer...")
    check_id(projectSU, su_HFS, cur_id)
    update_polys(projectSU, su_HFS, su_server_copy, field_mapping_su_to_hfs)

    # CWD Layer
    AddMsgAndPrint("\tUploading the CWD Layer...",0)
    arcpy.SetProgressorLabel("Uploading the CWD Layer...")
    check_id(projectCWD, cwd_HFS, cur_id)
    update_polys(projectCWD, cwd_HFS, cwd_server_copy, field_mapping_cwd_to_hfs)

    # CLU CWD Layer
    AddMsgAndPrint("\tUploading the CLU CWD Layer...",0)
    arcpy.SetProgressorLabel("Uploading the CLU CWD Layer...")
    check_id(projectCLUCWD, clucwd_HFS, cur_id)
    update_polys(projectCLUCWD, clucwd_HFS, clucwd_server_copy, field_mapping_clucwd_to_hfs)

    # ROPs Layer
    AddMsgAndPrint("\tUploading the ROPs Layer...",0)
    arcpy.SetProgressorLabel("Uploading the ROPs Layer...")
    check_id(projectROP, rop_HFS, cur_id)
    arcpy.Append_management(projectROP, rop_HFS, "NO_TEST", field_mapping_rop_to_hfs)

    # REF Layer
    if ref_count > 0:
        AddMsgAndPrint("\tUploading the Reference Points Layer...",0)
        arcpy.SetProgressorLabel("Uploading the Reference Points Layer...")
        check_id(projectREF, rp_HFS, cur_id)
        arcpy.Append_management(projectREF, rp_HFS, "NO_TEST", field_mapping_ref_to_hfs)

    # Drainage Lines Layer
    if dl_count > 0:
        AddMsgAndPrint("\tUploading the Drainage Lines Layer...",0)
        arcpy.SetProgressorLabel("Uploading the Drainage Lines Layer...")
        check_id(projectLines, drains_HFS, cur_id)
        arcpy.Append_management(projectLines, drains_HFS, "NO_TEST", field_mapping_dl_to_hfs)

    # PJW Layer
    if pjw_count > 0:
        AddMsgAndPrint("\tUploading the PJW Layer...",0)
        arcpy.SetProgressorLabel("Uploading the PJW Layer...")
        check_id(projectPJW, pjw_HFS, cur_id)
        arcpy.Append_management(projectPJW, pjw_HFS, "NO_TEST")
        

    #### Clean up Temporary Datasets
    # Temporary datasets specifically from this tool
    AddMsgAndPrint("\nCleaning up temporary data...",0)
    arcpy.SetProgressorLabel("Cleaning up temporary data...")
    deleteTempLayers(tempLayers)

    # Look for and delete anything else that may remain in the installed SCRATCH.gdb
    startWorkspace = arcpy.env.workspace
    arcpy.env.workspace = scratchGDB
    # Feature Classes
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
        arcpy.SetProgressorLabel("Compacting File Geodatabases...")
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
