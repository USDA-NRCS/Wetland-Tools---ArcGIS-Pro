## ===============================================================================================================
## Name:    Define Request Extent
## Purpose: Define the request extent from user input. Create the extent layer and all layers needed to start
##          delineating sampling units, including import of previously certified data where applicable.
##
## Authors: Chris Morse
##          GIS Specialist
##          Indianapolis State Office
##          USDA-NRCS
##          chris.morse@usda.gov
##          317.295.5849
##
## Created: 10/06/2020
##
## ===============================================================================================================
## Changes
## ===============================================================================================================
##
## rev. 10/06/2020
## - Start revisions of Create SU Layer ArcMap tool to National Wetlands Tool in ArcGIS Pro.
## - CLU and derived layers now use GeoPortal based web service extract attribute schema.
##
## rev. 10/14/2020
## - Incorporate download of previously certified determination areas; used later to restrict request extent
##      - Added check for GeoPortal login using getPortalTokenInfo call to the extract_CLU_by_Tract tool
##      - Added creation of prevCert feature class
##      - Added creation of prevAdmin feature class
##
## rev. 11/17/2020
## - Added a check for the input extent to make sure it is within the FSA Tract for the project.
## - Revised the methodology for developing the sampling unit layer to not include previously certified append step.
##
## rev. 03/02/2021
## - Updated tool to focus on creating the Request Extent layer and display New Request vs Certified-Digital areas
##   within the user entered AOI parameter(s).
## - Removed Sampling Unit and ROP data creation from this tool and moved it to the Create Base Map Layers tool.
##
## rev. 02/02/2022
## - Added functions and code to handle querying existing CWD data from server to update request extent and
##   protect existing determination extents.
##
## rev. 02/18/2022
## - Updated and debugged query server functions that were added on 2/2/2022
##
## rev. 02/22/2022
## - Replaced intersects with overlaps in server query function.
##
## rev. 02/25/2022
## - Debugged query/download function and related file cleanup
##
## rev. 05/02/2022
## - Updated Previously Certified data processing steps
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
    f.write("Executing Define Request Extent tool...\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("User Parameters:\n")
    f.write("\tWhole Tract?: " + str(wholeTract) + "\n")
    f.write("\tSelected Fields or Subfields?: " + str(selectFields) + "\n")
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

##  ===============================================================================================================
def queryIntersect(ws,temp_dir,fc,RESTurl,outFC):
##  This function uses a REST API query to retrieve geometry from that overlap an input feature class from a
##  hosted feature service.
##  Relies on a global variable of portalToken to exist and be active (checked before running this function)
##  ws is a file geodatabase workspace to store temp files for processing
##  fc is the input feature class. Should be a polygon feature class, but technically shouldn't fail if other types
##  RESTurl is the url for the query where the target hosted data resides
##  Example: """https://gis-testing.usda.net/server/rest/services/Hosted/CWD_Training/FeatureServer/0/query"""
##  outFC is the output feature class path/name that is return if the function succeeds AND finds data
##  Otherwise False is returned

    # Run the query
##    try:
    
    # Set variables
    query_url = RESTurl + "/query"
    jfile = temp_dir + os.sep + "jsonFile.json"
    wmas_fc = ws + os.sep + "wmas_fc"
    wmas_dis = ws + os.sep + "wmas_dis_fc"
    wmas_sr = arcpy.SpatialReference(3857)

    # Convert the input feature class to Web Mercator and to JSON
    arcpy.management.Project(fc, wmas_fc, wmas_sr)
    arcpy.management.Dissolve(wmas_fc, wmas_dis, "", "", "MULTI_PART", "")
    jsonPolygon = [row[0] for row in arcpy.da.SearchCursor(wmas_dis, ['SHAPE@JSON'])][0]

    # Setup parameters for query
    params = urllibEncode({'f': 'json',
                           'geometry':jsonPolygon,
                           'geometryType':'esriGeometryPolygon',
                           'spatialRelationship':'esriSpatialRelOverlaps',
                           'returnGeometry':'true',
                           'outFields':'*',
                           'token': portalToken['token']})


    INparams = params.encode('ascii')
    resp = urllib.request.urlopen(query_url,INparams)

    responseStatus = resp.getcode()
    responseMsg = resp.msg
    jsonString = resp.read()

    # json --> Python; dictionary containing 1 key with a list of lists
    results = json.loads(jsonString)

    # Check for error in results and exit with message if found.
    if 'error' in results.keys():
        if results['error']['message'] == 'Invalid Token':
            AddMsgAndPrint("\nSign-in token expired. Sign-out and sign-in to the portal again and then re-run. Exiting...",2)
            exit()
        else:
            AddMsgAndPrint("\nUnknown error encountered. Make sure you are online and signed in and that the portal is online. Exiting...",2)
            AddMsgAndPrint("\nResponse status code: " + str(responseStatus),2)
            exit()
    else:
        # Convert results to a feature class
        if not len(results['features']):
            return False
        else:
            with open(jfile, 'w') as outfile:
                json.dump(results, outfile)

            arcpy.conversion.JSONToFeatures(jfile, outFC)
            arcpy.management.Delete(jfile)
            arcpy.management.Delete(wmas_fc)
            arcpy.management.Delete(wmas_dis)
            return outFC

##        # Cleanup temp stuff from this function
##        files_to_del = [jfile, wmas_fc, wmas_dis]
##        for item in files_to_del:
##            try:
##                arcpy.management.Delete(item)
##            except:
##                pass

##    except httpErrors as e:
##        if int(e.code) >= 400:
##            AddMsgAndPrint("\nUnknown error encountered. Exiting...",2)
##            AddMsgAndPrint("\nHTTP Error = " + str(e.code),2)
##            errorMsg()
##            exit()
##        else:
##            errorMsg()
##            return False
            
## ===============================================================================================================
#### Import system modules
import arcpy, sys, os, traceback, re, shutil, csv
from importlib import reload
import urllib, time, json, random
from urllib.request import Request, urlopen
from urllib.error import HTTPError as httpErrors
urllibEncode = urllib.parse.urlencode
parseQueryString = urllib.parse.parse_qsl

sys.dont_write_bytecode=True
scriptPath = os.path.dirname(sys.argv[0])
sys.path.append(scriptPath)

import extract_CLU_by_Tract
reload(extract_CLU_by_Tract)


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


#### Check GeoPortal Connection
#nrcsPortal = 'https://gis-states.sc.egov.usda.gov/portal/'
nrcsPortal = 'https://gis-testing.usda.net/portal/'
portalToken = extract_CLU_by_Tract.getPortalTokenInfo(nrcsPortal)
if not portalToken:
    arcpy.AddError("Could not generate Portal token! Please login to GIS Testing Portal! Exiting...")
    exit()
    

#### Main procedures
try:
    #### Inputs
    arcpy.AddMessage("Reading inputs...\n")
    arcpy.SetProgressorLabel("Reading inputs...")
    sourceDefine = arcpy.GetParameterAsText(0)
    wholeTract = arcpy.GetParameterAsText(1)
    selectFields = arcpy.GetParameterAsText(2)
    sourceAOI = arcpy.GetParameterAsText(3)
    cwdURL = arcpy.GetParameterAsText(4)
##    extentLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(6))
    extentLyr = arcpy.mp.LayerFile(os.path.join(os.path.dirname(sys.argv[0]), "layer_files") + os.sep + "Extent.lyrx").listLayers()[0]


    #### Initial Validations
    arcpy.AddMessage("Verifying inputs...\n")
    arcpy.SetProgressorLabel("Verifying inputs...")
    # If whole tract is 'No' and select fields is 'Yes', make sure projectDAOI has features selected, else exit
    if wholeTract == 'No':
        if selectFields == 'Yes':
            desc = arcpy.Describe(sourceDefine)
            if desc.FIDset == '':
                arcpy.AddError('Selected fields option was used, but the input Define AOI layer has no fields selected. Exiting...')
                exit()

                
    #### Set base path
    sourceDefine_path = arcpy.Describe(sourceDefine).CatalogPath
    if sourceDefine_path.find('.gdb') > 0 and sourceDefine_path.find('Determinations') > 0 and sourceDefine_path.find('Site_Define_AOI') > 0:
        basedataGDB_path = sourceDefine_path[:sourceDefine_path.find('.gdb')+4]
    else:
        arcpy.AddError("\nSelected Define AOI layer is not from a Determinations project folder. Exiting...")
        exit()


    #### Define Variables
    arcpy.AddMessage("Setting variables...\n")
    arcpy.SetProgressorLabel("Setting variables...")
    supportGDB = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb")
    scratchGDB = os.path.join(os.path.dirname(sys.argv[0]), "SCRATCH.gdb")
    templateExtent = supportGDB + os.sep + "master_extent"
    
    basedataGDB_name = os.path.basename(basedataGDB_path)
    basedataFD_name = "Layers"
    basedataFD = basedataGDB_path + os.sep + basedataFD_name
    userWorkspace = os.path.dirname(basedataGDB_path)
    projectName = os.path.basename(userWorkspace).replace(" ", "_")

    wetDir = userWorkspace + os.sep + "Wetlands"
    wcGDB_name = os.path.basename(userWorkspace).replace(" ", "_") + "_WC.gdb"
    wcGDB_path = wetDir + os.sep + wcGDB_name
    wcFD_name = "WC_Data"
    wcFD = wcGDB_path + os.sep + wcFD_name
    
    projectCLU = basedataFD + os.sep + "Site_CLU"
    projectTract = basedataFD + os.sep + "Site_Tract"
    daoiName = "Site_Define_AOI"
    projectDAOI = basedataFD + os.sep + daoiName
    projectTable = basedataGDB_path + os.sep + "Table_" + projectName

    extentName = "Request_Extent"
    projectExtent = basedataFD + os.sep + extentName
    extTempName = "Extent_temp1_" + projectName
    extentTemp1 = scratchGDB + os.sep + extTempName
    extentTemp2 = scratchGDB + os.sep + "Extent_temp2_" + projectName
    extentTemp3 = scratchGDB + os.sep + "Extent_temp3_" + projectName
    tractTest = scratchGDB + os.sep + "Tract_Test_" + projectName

    intCWD = wcGDB_path + os.sep + "Intersected_CWD"

    origCert = wcFD + os.sep + "Previous_CLU_CWD_Original"
    origAdmin = wcFD + os.sep + "Previous_CLU_CWD_Admin_Original"
    origAdminTemp = scratchGDB + os.sep + "OrigAdminTemp"
    
    prevCertName = "Site_Previous_CLU_CWD"
    prevCert = wcFD + os.sep + prevCertName
    prevAdmin = wcFD + os.sep + "Previous_Admin"

    updatedCert = wcFD + os.sep + "Updated_Cert"
    updatedAdmin = wcFD + os.sep + "Updated_Admin"

    prevCertMulti = scratchGDB + os.sep + "pCertMulti"
    prevCertSingle = scratchGDB + os.sep + "pCertSingle"
    prevCertTemp1 = scratchGDB + os.sep + "pCertTemp"

    out_shape_name = "Request_Extent.shp"
    out_shape = wetDir + os.sep + out_shape_name
    
    # Temp layers list for cleanup at the start and at the end
    tempLayers = [extentTemp1, extentTemp2, extentTemp3, prevCertMulti, prevCertSingle, prevCertTemp1, tractTest, intCWD, origAdminTemp]
    deleteTempLayers(tempLayers)


    #### Set up log file path and start logging
    arcpy.AddMessage("Commence logging...\n")
    arcpy.SetProgressorLabel("Commence logging...")
    textFilePath = userWorkspace + os.sep + projectName + "_log.txt"
    logBasicSettings()

                
    #### If project wetlands geodatabase and feature dataset does not exist, create them.
    # Get the spatial reference from the Define AOI feature class and use it, if needed
    AddMsgAndPrint("\nChecking project integrity...",0)
    arcpy.SetProgressorLabel("Checking project integrity...")
    desc = arcpy.Describe(sourceDefine)
    sr = desc.SpatialReference
    
    if not arcpy.Exists(wcGDB_path):
        AddMsgAndPrint("\tCreating Wetlands geodatabase...",0)
        arcpy.SetProgressorLabel("Creating Wetlands geodatabase...")
        arcpy.CreateFileGDB_management(wetDir, wcGDB_name, "10.0")

    if not arcpy.Exists(wcFD):
        AddMsgAndPrint("\tCreating Wetlands feature dataset...",0)
        arcpy.SetProgressorLabel("Creating Wetlands feature dataset...")
        arcpy.CreateFeatureDataset_management(wcGDB_path, "WC_Data", sr)

    # Add or validate the attribute domains for the wetlands geodatabase
    AddMsgAndPrint("\tChecking attribute domains...",0)
    arcpy.SetProgressorLabel("Checking attribute domains...")
    descGDB = arcpy.Describe(wcGDB_path)
    domains = descGDB.domains

    if not "Evaluation Status" in domains:
        evalTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_evaluation_status")
        arcpy.TableToDomain_management(evalTable, "Code", "Description", wcGDB_path, "Evaluation Status", "Choices for evaluation workflow status", "REPLACE")
        arcpy.AlterDomain_management(wcGDB_path, "Evaluation Status", "", "", "DUPLICATE")
    if not "Line Type" in domains:
        lineTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_line_type")
        arcpy.TableToDomain_management(lineTable, "Code", "Description", wcGDB_path, "Line Type", "Drainage line types", "REPLACE")
        arcpy.AlterDomain_management(wcGDB_path, "Line Type", "", "", "DUPLICATE")
    if not "Method" in domains:
        methodTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_method")
        arcpy.TableToDomain_management(methodTable, "Code", "Description", wcGDB_path, "Method", "Choices for wetland determination method", "REPLACE")
        arcpy.AlterDomain_management(wcGDB_path, "Method", "", "", "DUPLICATE")
    if not "Pre Post" in domains:
        prepostTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_pre_post")
        arcpy.TableToDomain_management(prepostTable, "Code", "Description", wcGDB_path, "Pre Post", "Choices for date relative to 1985", "REPLACE")
        arcpy.AlterDomain_management(wcGDB_path, "Pre Post", "", "", "DUPLICATE")
    if not "Request Type" in domains:
        requestTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_request_type")
        arcpy.TableToDomain_management(requestTable, "Code", "Description", wcGDB_path, "Request Type", "Choices for request type form", "REPLACE")
        arcpy.AlterDomain_management(wcGDB_path, "Request Type", "", "", "DUPLICATE")
    if not "Wetland Labels" in domains:
        wetTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_wetland_labels")
        arcpy.TableToDomain_management(wetTable, "Code", "Description", wcGDB_path, "Wetland Labels", "Choices for wetland determination labels", "REPLACE")
        arcpy.AlterDomain_management(wcGDB_path, "Wetland Labels", "", "", "DUPLICATE")
    if not "Yes No" in domains:
        yesnoTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_yesno")
        arcpy.TableToDomain_management(yesnoTable, "Code", "Description", wcGDB_path, "Yes No", "Yes or no options", "REPLACE")
        arcpy.AlterDomain_management(wcGDB_path, "Yes No", "", "", "DUPLICATE")
    if not "YN" in domains:
        ynTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_yn")
        arcpy.TableToDomain_management(ynTable, "Code", "Description", wcGDB_path, "YN", "Y or N options", "REPLACE")
        arcpy.AlterDomain_management(wcGDB_path, "YN", "", "", "DUPLICATE")

    del descGDB, domains
    

    #### Remove existing extent layer from the Pro maps
    AddMsgAndPrint("\nRemoving extent layer from project maps, if present...\n",0)
    arcpy.SetProgressorLabel("Removing extent layer from project maps, if present...")
    
    # Set starting layers to be removed
    mapLayersToRemove = [extentName, prevCertName]
    
    # Remove the layers in the list
    try:
        for maps in aprx.listMaps():
            for lyr in maps.listLayers():
                if lyr.longName in mapLayersToRemove:
                    maps.removeLayer(lyr)
    except:
        pass


    #### Remove existing extent layer from the geodatabase
    AddMsgAndPrint("\nRemoving extent layer from project database, if present...\n",0)
    arcpy.SetProgressorLabel("Removing extent layer from project database, if present...")
    
    # Set starting datasets to remove
    datasetsToRemove = [projectExtent, origCert, origAdmin, prevCert, prevAdmin]

    # Remove the datasets in the list
    for dataset in datasetsToRemove:
        if arcpy.Exists(dataset):
            try:
                arcpy.Delete_management(dataset)
            except:
                pass


    #### Create the Extent Layer
    AddMsgAndPrint("\nCreating extent layer...",0)
    arcpy.SetProgressorLabel("Creating extent layer...")

    # If wholeTract was set to 'Yes', create by copying the projectTract layer.
    # If wholeTract was set to 'No' and selected fields was 'Yes', create via dissolve on the projectDAOI layer (with its selections)
    # If wholeTract was set to 'No' and selected fields was 'No', create via clip on the projectDAOI layer using the input drawn or selected AOI and then dissolve

    # Setup dissolve fields
    dissolve_fields = ['job_id','admin_state', 'admin_state_name','admin_county','admin_county_name','state_code','state_name','county_code','county_name','farm_number','tract_number']

    if wholeTract == 'Yes':
        #arcpy.Dissolve_management(projectDAOI, extentTemp2, dissolve_fields, "", "MULTI_PART")
        arcpy.CopyFeatures_management(projectTract, extentTemp2)
        
    else:
        if selectFields == 'Yes':
            # Use the sourceDefine layer to grab selections, and dissolve field lines
            arcpy.Dissolve_management(sourceDefine, extentTemp2, dissolve_fields, "", "MULTI_PART")
            
        else:
            # Drawn AOI should have been input. Clip using that input and then dissolve it.
            arcpy.Clip_analysis(projectDAOI, sourceAOI, extentTemp1)
            arcpy.Dissolve_management(extentTemp1, extentTemp2, dissolve_fields, "", "MULTI_PART")

    del dissolve_fields


    #### Check extentTemp2 to see that it fits within the projectTract
    arcpy.Erase_analysis(extentTemp2, projectTract, tractTest)
    result = int(arcpy.GetCount_management(tractTest).getOutput(0))
    if result > 0:
        # Some of the input extent is outside of the tract. Exit.
        AddMsgAndPrint("\nSome of the entered request area is outside of the Tract. Please refine your extent and try again. Exiting...", 2)
        deleteTempLayers(tempLayers)
        exit()
    del result
    

    #### Clean up the fields for projectExtent feature class
    # Add the eval_status field for use with integrating possible pre-existing data and calculate the default value of New Request
    fieldName = "eval_status"
    fieldAlias = "Evaluation Status"
    fieldLength = 24
    arcpy.AddField_management(extentTemp2, fieldName, "TEXT", field_alias = fieldAlias, field_length = fieldLength)

    expression = "\"New Request\""
    arcpy.CalculateField_management(extentTemp2, fieldName, expression, "PYTHON_9.3")
    del expression, fieldName, fieldAlias, fieldLength

    # Delete extraneous fields from the extent layer
    existing_fields = []
    for fld in arcpy.ListFields(extentTemp2):
        existing_fields.append(fld.name)
    drop_fields = ['clu_number', 'clu_calculated_acreage', 'highly_erodible_land_type_code', 'creation_date', 'last_change_date']
    for fld in drop_fields:
        if fld not in existing_fields:
            drop_fields.remove(fld)
    if len(drop_fields) > 0:
        arcpy.DeleteField_management(extentTemp2, drop_fields)
    del drop_fields, existing_fields
    

    #### Check for Existing CWD data within the request extent from the server layer and create the previous certication layers if found.
    AddMsgAndPrint("\tChecking for existing CWD data in the Tract...",0)
    arcpy.SetProgressorLabel("Checking for existing CWD data in the Tract...")

    query_results_fc = queryIntersect(scratchGDB,wetDir, projectTract,cwdURL,intCWD)

    if arcpy.Exists(intCWD):
        # This section runs if any intersecting geometry is returned from the query
        AddMsgAndPrint("\tPrevious certifications found within current Tract! Processing...",0)
        arcpy.SetProgressorLabel("Previous certifications found within current Tract! Processing...")
        
        # Use intersect to apply current clu data to the intCWD in case FSA CLU administrative info changed over time
        arcpy.Intersect_analysis([projectCLU, query_results_fc], prevCertMulti, "NO_FID", "#", "INPUT")

        # Explode features into single part
        arcpy.MultipartToSinglepart_management(prevCertMulti, prevCertSingle)
        arcpy.Delete_management(prevCertMulti)

        # Transer the job_id_1 attributes to the job_id field
        fields = ['job_id','job_id_1']
        cursor = arcpy.da.UpdateCursor(prevCertSingle, fields)
        for row in cursor:
            row[0] = row[1]
            cursor.updateRow(row)
        del fields
        del cursor

        # Temporarily calc acres to zero to retain the field through the next dissolve
        arcpy.CalculateField_management(prevCertSingle, "acres", 0, "PYTHON_9.3")

        # Dissolve the layer to potentially clean up slivers caused by old and new field lines (also removes all the "_1" and other extraneous fields)
        dis_fields = ['job_id', 'admin_state', 'admin_state_name', 'admin_county', 'admin_county_name', 'state_code', 'state_name', 'county_code', 'county_name',
                      'farm_number', 'tract_number', 'clu_number', 'eval_status', 'wetland_label', 'occur_year', 'acres', 'three_factors', 'request_date', 'request_type',
                      'deter_method', 'deter_staff', 'dig_staff', 'dig_date', 'cwd_comments', 'cert_date']
        arcpy.Dissolve_management(prevCertSingle, origCert, dis_fields, "", "SINGLE_PART", "")
        del dis_fields

        # Calculate the eval_status field to "Certified-Digital"
        expression = "\"Certified-Digital\""
        arcpy.CalculateField_management(origCert, "eval_status", expression, "PYTHON_9.3")
        del expression

        # Update the acres in the resulting layer
        expression = "round(!Shape.Area@acres!,2)"
        arcpy.CalculateField_management(origCert, "acres", expression, "PYTHON_9.3")

        # Delete the orig_id field
        drop_fields = ['ORIG_ID']
        existing_fields = []
        for fld in arcpy.ListFields(origCert):
            existing_fields.append(fld.name)
        for fld in drop_fields:
            if fld not in existing_fields:
                drop_fields.remove(fld)
        if len(drop_fields) > 0:
            arcpy.DeleteField_management(origCert, drop_fields)
        del drop_fields, existing_fields
        
        # Create the origAdmin layer using Dissolve (drop anything from the Clu field or the wetland label level).
        dis_fields = ['job_id','admin_state','admin_state_name','admin_county','admin_county_name','state_code','state_name','county_code','county_name','farm_number','tract_number','eval_status']
        arcpy.Dissolve_management(origCert, origAdmin, dis_fields, "", "SINGLE_PART", "")
        del dis_fields

        # Also Delete orig_id field from the origAdmin layer
        drop_fields = ['ORIG_ID']
        existing_fields = []
        for fld in arcpy.ListFields(origAdmin):
            existing_fields.append(fld.name)
        for fld in drop_fields:
            if fld not in existing_fields:
                drop_fields.remove(fld)
        if len(drop_fields) > 0:
            arcpy.DeleteField_management(origAdmin, drop_fields)
        del drop_fields, existing_fields

        # Create prevCert and prevAdmin layers
        arcpy.CopyFeatures_management(origCert, prevCert)
        arcpy.CopyFeatures_management(origAdmin, prevAdmin)

    else:
        AddMsgAndPrint("\tNo previous certifications found! Continuing...",0)
        arcpy.SetProgressorLabel("No previous certifications found! Continuing...")
        if arcpy.Exists(origAdmin):
            try:
                arcpy.Delete_management(origAdmin)
                arcpy.Delete_management(origCert)
                arcpy.Delete_management(prevAdmin)
                arcpy.Delete_management(prevCert)
            except:
                pass


    #### Use the origAdmin areas to update the request extent if there is overlap between them
    if arcpy.Exists(origAdmin):
        AddMsgAndPrint("Checking Request Extent relative to existing CWDs...",0)
        arcpy.SetProgressorLabel("Checking Request Extent relative to existing CWDs...")

        # Clip the origAdmin layer with the extent
        arcpy.Clip_analysis(origAdmin, extentTemp2, origAdminTemp)
        
        # Check for any actual overlap
        result = int(arcpy.GetCount_management(origAdminTemp).getOutput(0))
        if result > 0:
            AddMsgAndPrint("Existing CWDs found within Request Extent! Integrating CWD extents to the Request Extent...",0)
            arcpy.SetProgressorLabel("Existing CWDs found within Request Extent! Integrating CWD extents to the Request Extent...")
            # Previous CWDs overlap the Request Extent. Erase the prevAdmin from the new extent and use Append combine them
            arcpy.Erase_analysis(extentTemp2, origAdminTemp, extentTemp3)
            arcpy.Append_management(origAdminTemp, extentTemp3, "NO_TEST")
            arcpy.FeatureClassToFeatureClass_conversion(extentTemp3, basedataFD, extentName)
        else:
            # Previous CWDs do not overlap the Request Extent.
            AddMsgAndPrint("Existing CWDs not found within Request Extent! Using original Request Extent...",0)
            arcpy.SetProgressorLabel("Existing CWDs not found within Request Extent! Using original Request Extent...")
            arcpy.FeatureClassToFeatureClass_conversion(extentTemp2, basedataFD, extentName)
    else:
        # There are no previous CWDs. Just use the newly defined extent.
        arcpy.FeatureClassToFeatureClass_conversion(extentTemp2, basedataFD, extentName)

    # Transfer temporary extent layers into the request extent layer
    arcpy.FeatureClassToFeatureClass_conversion(extentTemp2, basedataFD, extentName)

    #### Export Request Extent shapefile for users to have for external uses (e.g. WSS Reports)
    if arcpy.Exists(out_shape):
        try:
            arcpy.Delete_management(out_shape)
        except:
            pass
    arcpy.FeatureClassToShapefile_conversion([projectExtent], wetDir)
    

    #### Clean up Temporary Datasets
    # Temporary datasets specifically from this tool
    deleteTempLayers(tempLayers)

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


    #### Add to map
    # Use starting reference layer files for the tool installation to add layer with automatic placement
    AddMsgAndPrint("\nAdding layers to the map...",0)
    arcpy.SetProgressorLabel("Adding layers to the map...")

    lyr_list = m.listLayers()
    lyr_name_list = []
    for lyr in lyr_list:
        lyr_name_list.append(lyr.longName)

    if extentName not in lyr_name_list:
        extentLyr_cp = extentLyr.connectionProperties
        extentLyr_cp['connection_info']['database'] = basedataGDB_path
        extentLyr_cp['dataset'] = extentName
        extentLyr.updateConnectionProperties(extentLyr.connectionProperties, extentLyr_cp)
        m.addLayer(extentLyr)

    if arcpy.Exists(prevCert):
        arcpy.SetParameterAsText(5, prevCert)

    #### Clear selections from source AOI layer if it was used with selections
    if selectFields == 'Yes':
        define_name = "Site_Define_AOI"
        define_lyr = m.listLayers(define_name)[0]
        arcpy.SelectLayerByAttribute_management(define_lyr, "CLEAR_SELECTION")


    #### Adjust visibility of layers to aid in moving to the next step in the process
    # Turn off Define_AOI layers
    off_names = [daoiName]
    for maps in aprx.listMaps():
        for lyr in maps.listLayers():
            for name in off_names:
                if name in lyr.longName:
                    lyr.visible = False

    # Turn on Request Extent layer
    on_names = [extentName]
    for maps in aprx.listMaps():
        for lyr in maps.listLayers():
            for name in on_names:
                if (lyr.longName).startswith(name):
                    lyr.visible = True


    #### Compact FGDB
    try:
        AddMsgAndPrint("\nCompacting File Geodatabases..." ,0)
        arcpy.SetProgressorLabel("Compacting File Geodatabases...")
        arcpy.Compact_management(basedataGDB_path)
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
