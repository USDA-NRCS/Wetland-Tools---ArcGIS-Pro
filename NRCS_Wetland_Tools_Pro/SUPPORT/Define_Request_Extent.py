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
## -Start revisions of Create SU Layer ArcMap tool to National Wetlands Tool in ArcGIS Pro.
## -CLU and derived layers now use GeoPortal based web service extract attribute schema.
##
## rev. 10/14/2020
## -Incorporate download of previously certified determination areas; used later to restrict request extent
##      -Added check for GeoPortal login using getPortalTokenInfo call to the extract_CLU_by_Tract tool
##      -Added creation of prevCert feature class
##      -Added creation of prevAdmin feature class
##
## rev. 11/17/2020
## -Added a check for the input extent to make sure it is within the FSA Tract for the project.
## -Revised the methodology for developing the sampling unit layer to not include previously certified append step.
##
## rev. 03/02/2021
## -Updated tool to focus on creating the Request Extent layer and display New Request vs Certified-Digital areas
##  within the user entered AOI parameter(s).
## -Removed Sampling Unit and ROP data creation from this tool and moved it to the Create Base Map Layers tool.
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
def changeSource(cur_lyr, new_ws, new_fc):
    cp = cur_lyr.connectionProperties
    cp['connection_info']['database'] = new_ws
    cp['dataset'] = new_fc
    cur_lyr.updateConnectionProperties(cur_lyr.connectionProperties, cp)

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
import arcpy, sys, os, traceback, re, shutil, csv
from importlib import reload
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
nrcsPortal = 'https://gis.sc.egov.usda.gov/portal/'
portalToken = extract_CLU_by_Tract.getPortalTokenInfo(nrcsPortal)
if not portalToken:
    arcpy.AddError("Could not generate Portal token! Please login to GeoPortal! Exiting...")
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
    existing_cwd = arcpy.GetParameterAsText(4)
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

    prevCert = wcFD + os.sep + "Previous_CWD"
    prevCertSite = wcFD + os.sep + "Site_Previous_CWD"
    prevCertMulti = scratchGDB + os.sep + "pCertMulti"
    prevCertTemp1 = scratchGDB + os.sep + "pCertTemp"
    prevAdmin = wcFD + os.sep + "Previous_Admin"
    prevAdminSite = wcFD + os.sep + "Site_Previous_Admin"
    updatedCert = wcFD + os.sep + "Updated_Cert"
    updatedAdmin = wcFD + os.sep + "Updated_Admin"

    out_shape_name = "Request_Extent.shp"
    out_shape = wetDir + os.sep + out_shape_name
    
    # Temp layers list for cleanup at the start and at the end
    tempLayers = [extentTemp1, extentTemp2, extentTemp3, prevCertMulti, prevCertTemp1, tractTest]
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
    

    #### Remove existing sampling unit related layers from the Pro maps
    AddMsgAndPrint("\nRemoving layers from project maps, if present...\n",0)
    arcpy.SetProgressorLabel("Removing layers from project maps, if present...")
    
    # Set starting layers to be removed
    mapLayersToRemove = [extentName]
    
    # Remove the layers in the list
    try:
        for maps in aprx.listMaps():
            for lyr in maps.listLayers():
                if lyr.name in mapLayersToRemove:
                    maps.removeLayer(lyr)
    except:
        pass


    #### Remove existing sampling unit related layers from the geodatabase
    AddMsgAndPrint("\nRemoving layers from project database, if present...\n",0)
    arcpy.SetProgressorLabel("Removing layers from project database, if present...")
    
    # Set starting datasets to remove
    datasetsToRemove = [projectExtent]

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
    

    #### Check for Existing CWD data on the tract from the statewide layer and create the previous certication layers if found.
    if arcpy.Exists(existing_cwd):
        AddMsgAndPrint("\tChecking for existing CWD data in the Tract...",0)
        arcpy.SetProgressorLabel("Checking for existing CWD data in the Tract...")
        process_cwd = False
        # Use intersect so that you apply current tract data to the existing CWD in case it changed over time
        arcpy.Intersect_analysis([projectTract, existing_cwd], prevCertMulti, "NO_FID", "#", "INPUT")

        # Check for any results
        result = int(arcpy.GetCount_management(prevCertMulti).getOutput(0))
        if result > 0:
            process_cwd = True
            # Features were found in the area
            AddMsgAndPrint("\tPrevious certifications found within current Tract! Processing...",0)
            arcpy.SetProgressorLabel("Previous certifications found within current Tract! Processing...")

            # Explode features into single part
            arcpy.MultipartToSinglepart_management(prevCertMulti, prevCert)
            arcpy.Delete_management(prevCertMulti)

            # Calculate the eval_status field to "Certified-Digital"
            expression = "\"Certified-Digital\""
            arcpy.CacluateField_management(prevCert, "eval_status", expression, "PYTHON_9.3")
            del expression

            # Transer the job_id_1 attributes to the job_id field
            fields = ['job_id','job_id_1']
            cursor = arcpy.da.UpdateCursor(prevCert, fields)
            for row in cursor:
                row[0] = row[1]
                cursor.updateRow(row)
            del fields
            del cursor
            
            # Create the prevAdmin layer using Dissolve.
            dis_fields = ['job_id','admin_state','admin_state_name','admin_county','admin_county_name','state_code','state_name','county_code','county_name','farm_number','tract_number','eval_status']
            arcpy.Dissolve_management(prevCert, prevAdmin, dis_fields, "", "SINGLE_PART", "")
            del dis_fields

            # Also Delete excess tabular fields from the prevCert layer
            existing_fields = []
            drop_fields = ['job_id_1','admin_state_1','admin_state_name_1','admin_county_1','admin_county_name_1','state_code_1','state_name_1','county_code_1','county_name_1','farm_number_1',
                           'tract_number_1', 'eval_status_1']
            
            for fld in arcpy.ListFields(prevCert):
                existing_fields.append(fld.name)
            
            for fld in drop_fields:
                if fld not in existing_fields:
                    drop_fields.remove(fld)
                    
            if len(drop_fields) > 0:
                arcpy.DeleteField_management(prevCert, drop_fields)
                
            del drop_fields, existing_fields

        else:
            AddMsgAndPrint("\tNo previous certifications found! Continuing...",0)
            arcpy.SetProgressorLabel("No previous certifications found! Continuing...")
            arcpy.Delete_management(prevCert)
            if arcpy.Exists(prevAdmin):
                try:
                    arcpy.Delete_management(prevAdmin)
                except:
                    pass
        del result


    #### Use the prevAdmin areas to update the request extent if there is overlap between them
    if arcpy.Exists(prevAdmin):
        AddMsgAndPrint("Checking Request Extent relative to existing CWDs...",0)
        arcpy.SetProgressorLabel("Checking Request Extent relative to existing CWDs...")

        # Clip the prevAdmin layer with the extent (also do a clip to create prevCertSite for future steps while we're at it)
        arcpy.Clip_analysis(prevAdmin, extentTemp2, prevAdminSite)
        arcpy.Clip_analysis(prevCert, extentTemp2, prevCertSite)
        
        # Check for any actual overlap
        result = int(arcpy.GetCount_management(prevAdminSite).getOutput(0))
        if result > 0:
            AddMsgAndPrint("Existing CWDs found within Request Extent! Integrating CWD extents to the Request Extent...",0)
            arcpy.SetProgressorLabel("Existing CWDs found within Request Extent! Integrating CWD extents to the Request Extent...")
            # Previous CWDs overlap the Request Extent. Erase the prevAdmin from the new extent and use Append combine them
            arcpy.Erase_analysis(extentTemp2, prevAdminSite, extentTemp3)
            arcpy.Append_management(prevAdminSite, extentTemp3, "NO_TEST")
            arcpy.FeatureClassToFeatureClass_conversion(extentTemp3, basedataFD, extentName)
        else:
            # Previous CWDs do not overlap the Request Extent.
            AddMsgAndPrint("Existing CWDs not found within Request Extent! Using original Request Extent...",0)
            arcpy.SetProgressorLabel("Existing CWDs not found within Request Extent! Using original Request Extent...")
            arcpy.FeatureClassToFeatureClass_conversion(extentTemp2, basedataFD, extentName)
    else:
        # There are no previous CWDs. Just use the newly defined extent.
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
        lyr_name_list.append(lyr.name)

    if extentName not in lyr_name_list:
        extentLyr_cp = extentLyr.connectionProperties
        extentLyr_cp['connection_info']['database'] = basedataGDB_path
        extentLyr_cp['dataset'] = extentName
        extentLyr.updateConnectionProperties(extentLyr.connectionProperties, extentLyr_cp)
        m.addLayer(extentLyr)
    
##    m.addLayer(extentLyr)
##
##    # Replace data sources of layer files from installed layers to the project layers
##    # First get the current layers in the map
##    extentNew = m.listLayers(extentName)[0]
##
##    # Call the function to change the data source via CIM
##    changeSource(extentNew, basedataGDB_path, extentName)


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
                if name in lyr.name:
                    lyr.visible = False

    # Turn on Request Extent layer
    on_names = [extentName]
    for maps in aprx.listMaps():
        for lyr in maps.listLayers():
            for name in on_names:
                if (lyr.name).startswith(name):
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
