## ===============================================================================================================
## Name:    Create SU AOI
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
## Start revisions of Create SU Layer ArcMap tool to National Wetlands Tool in ArcGIS Pro.
## CLU and derived layers now use GeoPortal based web service extract attribute schema.
##
## rev. 10/14/2020
## Incorporate download of previously certified determination areas; used later to restrict request extent
##      -Add check for GeoPortal login using getPortalTokenInfo call to the extract_CLU_by_Tract tool
##      -Add creation of prevCert feature class
##      -Add creation of prevAdmin feature class
##
## rev. 11/17/2020
## Add a check for the input extent to make sure it is within the FSA Tract for the project
## Revised the methodology for developing the sampling unit layer to not include previously certified append to it.
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
    f.write("Executing Define Request AOI tool...\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("User Parameters:\n")
    f.write("\tWhole Tract?: " + str(wholeTract) + "\n")
    f.write("\tSelected Fields or Subfields?: " + str(selectFields) + "\n")
    f.write("\tRetain Field Lines?: " + str(keepFields) + "\n")
    f.close
    del f

## ===============================================================================================================
def changeSource(cur_lyr, new_ws='', new_fd='', new_fc=''):
    # This function will update the input layer through the CIM to change connection properties for the layer
    # utilizing the provided new workspace path, new feature dataset name, or new feature class name if they were
    # provided to the function.
    # Requires a layer object from a map within an APRX.
    # cur_lyr:  A layer in a map in the current APRX.
    # new_ws:   A path to a folder or workspace (e.g. file geodatabase) that contains the desired feature class.
    # new_fd:   A string that specifies an existing feature dataset name in the specified workspace.
    # new_fc:   A string that represents an existing feature class name in the specified workspace.
    
    lyrCIM = cur_lyr.getDefinition('V2')
    dc = lyrCIM.featureTable.dataConnection

    if new_ws != '':
        if arcpy.Exists(new_ws):
            dc.workspaceConnectionString = 'DATABASE=' + new_ws

    if new_fd != '':
        if new_ws != '':
            fd_path = new_ws + os.sep + new_fd
        else:
            fd_path = dc.workspaceConnectionString[:9] + os.sep + new_fd

        if arcpy.Exists(fd_path):
            dc.featureDataset = new_fd

    if new_fc != '':
        if new_ws!= '':
            if new_fd != '':
                fc_path = new_ws + os.sep + new_fd + os.sep + new_fc
            else:
                fc_path = new_ws + os.sep + dc.featureDataset + os.sep + new_fc
        else:
            if new_fd != '':
                fc_path = dc.workspaceConnectionString[:9] + os.sep + new_fd + os.sep + new_fc
            else:
                fc_path = dc.workspaceConnectionString[:9] + os.sep + dc.featureDataset + os.sep + new_fc

        if arcpy.Exists(fc_path):
            dc.dataset = new_fc

    if new_ws != '' or new_fd != '' or new_fc != '':
        cur_lyr.setDefinition(lyrCIM)

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

# Set overwrite flag
arcpy.env.overwriteOutput = True

# Test for Pro project.
try:
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    m = aprx.listMaps("Determinations")[0]
except:
    arcpy.AddError("\nThis tool must be from an active ArcGIS Pro project. Exiting...\n")
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
    sourceDefine = arcpy.GetParameterAsText(0)
    wholeTract = arcpy.GetParameterAsText(1)
    selectFields = arcpy.GetParameterAsText(2)
    sourceAOI = arcpy.GetParameterAsText(3)
    keepFields = arcpy.GetParameterAsText(4)
    resetROPs = arcpy.GetParameterAsText(5)
    resetDrains = arcpy.GetParameterAsText(6)
    existing_cwd = arcpy.GetParameterAsText(7)
    suLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(8))
    ropLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(9))
    drainLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(10))
    extentLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(11))


    #### Initial Validations
    arcpy.AddMessage("Verifying inputs...\n")
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
    templateSU = supportGDB + os.sep + "master_sampling_units"
    templateROP = supportGDB + os.sep + "master_rop"
    templateLines = supportGDB + os.sep + "master_drainage_lines"
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
    projectTractB = basedataFD + os.sep + "Site_Tract_Buffer"
    projectTable = basedataGDB_path + os.sep + "Table_" + projectName
    projectAOI = basedataFD + os.sep + "Site_AOI"
    projectDAOI = basedataFD + os.sep + "Site_Define_AOI"

    suName = "Site_Sampling_Units"
    projectSU = wcFD + os.sep + suName
    suMulti = scratchGDB + os.sep + "SU_Multi" + projectName
    suTemp1 = scratchGDB + os.sep + "SU_Temp1_" + projectName
    suTemp2 = scratchGDB + os.sep + "SU_Temp2_" + projectName

    ropName = "Site_ROPs"
    projectROP = wcFD + os.sep + ropName

    drainName = "Site_Drainage_Lines"
    projectLines = wcFD + os.sep + drainName

    extentName = "Request_Extent"
    projectExtent = basedataFD + os.sep + extentName
    extTempName = "Extent_temp1_" + projectName
    extentTemp1 = scratchGDB + os.sep + extTempName
    extentTemp2 = scratchGDB + os.sep + "Extent_temp2_" + projectName
    extentTemp3 = scratchGDB + os.sep + "Extent_temp3_" + projectName
    tractTest = scratchGDB + os.sep + "Tract_Test_" + projectName

    suTopoName = "Sampling_Units_Topology_" + projectName
    suTopo = wcFD + os.sep + suTopoName

    prevCertMulti = scratchGDB + os.sep + "pCertMulti_" + projectName
    prevCertTemp1 = scratchGDB + os.sep + "pCertTemp_" + projectName
    prevCert = wcFD + os.sep + "PCWD_" + projectName
    prevAdmin = wcFD + os.sep + "PCWD_Admin_" + projectName
    updatedCert = wcFD + os.sep + "MCWD_" + projectName
    updatedAdmin = wcFD + os.sep + "MCWD_Admin" + projectName
    
    # ArcPro Map Layer Names
    suOut = "Site_Sampling_Units"
    ropOut = "Site_ROPs"
    drainOut = "Site_Drainage_Lines"
    extentOut = "Request_Extent"
    suTopoOut = suTopoName

    # Annotation Layer Names (in map)
    anno_list = []
    suAnnoString = "Site_Sampling_Units" + "Anno*"
    ropAnnoString = "Site_ROPs" + "Anno*"
    drainAnnoString = "Site_Drainage_Lines" + "Anno*"

    anno_list.append(suAnnoString)
    anno_list.append(ropAnnoString)
    anno_list.append(drainAnnoString)
    
    # Attribute rules files
    rules_su = os.path.join(os.path.dirname(sys.argv[0]), "Rules_SU.csv")
    rules_lines = os.path.join(os.path.dirname(sys.argv[0]), "Rules_Drains.csv")

    # Temp layers list for cleanup at the start and at the end
    tempLayers = [suMulti, suTemp1, suTemp2, extentTemp1, extentTemp2, extentTemp3, prevCertMulti, prevCertTemp1, tractTest]
    deleteTempLayers(tempLayers)


    #### Set up log file path and start logging
    arcpy.AddMessage("Commence logging...\n")
    textFilePath = userWorkspace + os.sep + projectName + "_log.txt"
    logBasicSettings()

                
    #### If project wetlands geodatabase and feature dataset does not exist, create them.
    # Get the spatial reference from the Define AOI feature class and use it, if needed
    AddMsgAndPrint("\nChecking project integrity...",0)
    desc = arcpy.Describe(sourceDefine)
    sr = desc.SpatialReference
    
    if not arcpy.Exists(wcGDB_path):
        AddMsgAndPrint("\tCreating Wetlands geodatabase...",0)
        arcpy.CreateFileGDB_management(wetDir, wcGDB_name, "10.0")

    if not arcpy.Exists(wcFD):
        AddMsgAndPrint("\tCreating Wetlands feature dataset...",0)
        arcpy.CreateFeatureDataset_management(wcGDB_path, "WC_Data", sr)

    # Add or validate the attribute domains for the wetlands geodatabase
    AddMsgAndPrint("\tChecking attribute domains...",0)
    descGDB = arcpy.Describe(wcGDB_path)
    domains = descGDB.domains

    if not "CWD Status" in domains:
        cwdTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_cwd_status")
        arcpy.TableToDomain_management(cwdTable, "Code", "Description", wcGDB_path, "CWD Status", "Choices for wetland determination status", "REPLACE")
        arcpy.AlterDomain_management(wcGDB_path, "CWD Status", "", "", "DUPLICATE")
    if not "Data Form" in domains:
        dataTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_data_form")
        arcpy.TableToDomain_management(dataTable, "Code", "Description", wcGDB_path, "Data Form", "Choices for data form completion", "REPLACE")
        arcpy.AlterDomain_management(wcGDB_path, "Data Form", "", "", "DUPLICATE")
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
    if not "ROP Status" in domains:
        ropTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_rop_status")
        arcpy.TableToDomain_management(ropTable, "Code", "Description", wcGDB_path, "ROP Status", "Choices for ROP status", "REPLACE")
        arcpy.AlterDomain_management(wcGDB_path, "ROP Status", "", "", "DUPLICATE")
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
    
    # Set starting layers to be removed
    mapLayersToRemove = [suOut, ropOut, drainOut, extentOut, suTopoOut]

    # Look for annotation related to the layers to be removed and append them to the mapLayersToRemove list
    for maps in aprx.listMaps():
        for name in anno_list:
            for lyr in maps.listLayers(name):
                mapLayersToRemove.append(lyr.name)
    
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

    # Remove topology first, if it exists
    toposToRemove = [suTopo]
    for topo in toposToRemove:
        if arcpy.Exists(topo):
            try:
                arcpy.Delete_management(topo)
            except:
                pass

    # Set starting datasets to remove
    datasetsToRemove = [projectSU, projectExtent]

    # Look for annotation datasets related to the datasets to be removed and delete them
    startWorkspace = arcpy.env.workspace
    arcpy.env.workspace = wcGDB_path
    fcs = []
    for fds in arcpy.ListDatasets('', 'feature') + ['']:
        for fc in arcpy.ListFeatureClasses('*Sampling_Units*', 'Annotation', fds):
            fcs.append(os.path.join(wcGDB_path, fds, fc))
    for fc in fcs:
        datasetsToRemove.append(fc)
    arcpy.env.workspace = startWorkspace
    del startWorkspace

    # Remove the datasets in the list
    for dataset in datasetsToRemove:
        if arcpy.Exists(dataset):
            try:
                arcpy.Delete_management(dataset)
            except:
                pass


    #### Create the Extent Layer
    AddMsgAndPrint("\nCreating extent layer...",0)
    
    # If wholeTract was set to 'Yes', create via dissolve on the projectDAOI layer (or could use the projectCLU layer)
    dissolve_fields = ['admin_state', 'admin_state_name', 'admin_county', 'admin_county_name', 'state_code', 'state_name', 'county_code', 'county_name', 'farm_number', 'tract_number']
    if wholeTract == 'Yes':
        arcpy.Dissolve_management(projectDAOI, extentTemp2, dissolve_fields, "", "MULTI_PART")

    else:
        if selectFields == 'Yes':
            # Use the sourceDefine layer to grab selections
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


    #### Use the temp extent to extract data from the CWD layer and check for overlap
    if arcpy.Exists(existing_cwd):
        AddMsgAndPrint("\tChecking for existing CWD data in the Tract...",0)
        process_cwd = False
        # Use intersect so that you apply current tract data to the existing CWD in case it changed over time
        arcpy.Intersect_analysis([projectTract, existing_cwd], prevCertMulti, "NO_FID", "#", "INPUT")

        # Check for any results
        result = int(arcpy.GetCount_management(prevCertMulti).getOutput(0))
        if result > 0:
            process_cwd = True
            # Features were found in the area
            AddMsgAndPrint("\tPrevious certifications found within current Tract! Processing...",0)

            # Explode features into single part
            arcpy.MultipartToSinglepart_management(prevCertMulti, prevCert)
            arcpy.Delete_management(prevCertMulti)

            # Calculate the eval_status field to "Certified-Digital"
            expression = "\"Certified-Digital\""
            arcpy.CacluateField_management(prevCert, "eval_status", expression, "PYTHON_9.3")
            del expression

            # Create the prevAdmin layer using Dissolve
            dis_fields = ['admin_state','admin_state_name','admin_county','admin_county_name','state_code','state_name','county_code','county_name','farm_number','tract_number','eval_status']
            arcpy.Dissolve_management(prevCert, prevAdmin, dis_fields, "", "SINGLE_PART", "")
            del dis_fields

            # Delete excess tabular fields from the prevCert layer
            existing_fields = []
            drop_fields = ['admin_state_1','admin_state_name_1','admin_county_1','admin_county_name_1','state_code_1','state_name_1','county_code_1','county_name_1','farm_number_1',
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
            arcpy.Delete_management(prevCert)
            if arcpy.Exists(prevAdmin):
                try:
                    arcpy.Delete_management(prevAdmin)
                except:
                    pass
        del result


    #### Erase any prevAdmin areas from the Extent layer to refine the extent
    fullCWD = False
    if arcpy.Exists(prevAdmin):
        AddMsgAndPrint("Updating request extent to eliminate areas that overlap existing CWDs...",0)
        # Erase the prevAdmin from the extent
        arcpy.Erase_analysis(extentTemp2, prevAdmin, extentTemp3)

        # Check the results to count if anything is left
        result = int(arcpy.GetCount_management(extentTemp3).getOutput(0))
        if result > 0:
            # We have some area left over and extentTemp3 can be made into projectExtent, otherwise extentTemp2 is made into projectExtent
            arcpy.FeatureClassToFeatureClass_conversion(extentTemp3, basedataFD, extentName)
        else:
            # All of the requested area is covered by certified determinations, therefore use the original extent
            fullCWD = True
            arcpy.FeatureClassToFeatureClass_conversion(extentTemp2, basedataFD, extentName)
    else:
        # There are no previous CWDs. Just use the newly defined extent.
        arcpy.FeatureClassToFeatureClass_conversion(extentTemp2, basedataFD, extentName)
    

    #### Create the Sampling Unit Layer
    # Create an empty Sampling Unit feature class
    arcpy.CreateFeatureclass_management(wcFD, suName, "POLYGON", templateSU)

    # Create the SU layer by intersecting the extent with the CLU
    arcpy.Intersect_analysis([projectExtent, projectCLU], suMulti, "NO_FID", "#", "INPUT")
    arcpy.MultipartToSinglepart_management(suMulti, suTemp1)

    # Dissolve out field lines if that option was selected
    if keepFields == "No":
        dis_fields = ['admin_state','admin_state_name','admin_county','admin_county_name','state_code','state_name','county_code','county_name','farm_number','tract_number','eval_status']
        arcpy.Dissolve_management(suTemp1, suTemp2, dis_fields, "", "SINGLE_PART", "")
        arcpy.Append_management(suTemp2, projectSU, "NO_TEST")
    else:
        arcpy.Append_management(suTemp1, projectSU, "NO_TEST")


    #### Assign domains to the SU layer
    arcpy.AssignDomainToField_management(projectSU, "locked", "Yes No")
    arcpy.AssignDomainToField_management(projectSU, "eval_status", "Evaluation Status")
    arcpy.AssignDomainToField_management(projectSU, "three_factors", "YN")
    arcpy.AssignDomainToField_management(projectSU, "request_type", "Request Type")
    arcpy.AssignDomainToField_management(projectSU, "deter_method", "Method")


    #### Update SU layer attributes
    # Assign eval_status attribute as "New Request"
    fields = ['eval_status','locked']
    cursor = arcpy.da.UpdateCursor(projectSU, fields)
    for row in cursor:
        row[0] = "New Request"
        row[1] = "No"
        cursor.updateRow(row)
    del cursor

    # If entire request area is certified, update the attributes for eval status to Revision
    if fullCWD:
        fields = ['eval_status']
        cursor = arcpy.da.UpdateCursor(projectSU, fields)
        for row in cursor:
            row[0] = "Revision"
            cursor.updateRow(row)
        del cursor

    # Update calculated acres
    expression = "!Shape.Area@acres!"
    arcpy.CalculateField_management(projectSU, "acres", expression, "PYTHON_9.3")
    del expression

    ## Update attributes: request_date, request_type, deter_staff, dig_staff, and dig_date (current date) from projectTable for New/Revised areas
    # Get admin attributes from project table for request_date, request_type, deter_staff, dig_staff, and dig_date (current date) and assign them to New/Revised (all?) areas
    if arcpy.Exists(projectTable):
        fields = ['request_date','request_type','deter_staff','dig_staff']
        cursor = arcpy.da.SearchCursor(projectTable, fields)
        for row in cursor:
            rDate = row[0]
            rType = row[1]
            detStaff = row[2]
            digStaff = row[3]
            break
        del cursor, fields

        digDate = time.strftime('%m/%d/%Y')

        fields = ['eval_status','request_date','request_type','deter_staff','dig_staff','dig_date']
        cursor = arcpy.da.UpdateCursor(projectSU, fields)
        for row in cursor:
            if row[0] == "New Request" or row[0] == "Revision":
                row[1] = rDate
                row[2] = rType
                row[3] = detStaff
                row[4] = digStaff
                row[5] = digDate
            cursor.updateRow(row)
    
        
    #### Create ROP Layer
    # Don't pull in any ROPs for previously certified areas (people will see them in the display and can copy/paste if needed)
    # Import ROPs will be a separate utility tool that appends features to existing ROP layer.
    if resetROPs == 'Yes':
        arcpy.Delete_management(projectROP)

    if not arcpy.Exists(projectROP):
        AddMsgAndPrint("\nCreating ROPs layer...",0)
        fcName = os.path.basename(projectROP)
        arcpy.CreateFeatureclass_management(wcFD, fcName, "POINT", templateROP)
        del fcName

        arcpy.AssignDomainToField_management(projectROP, "locked", "Yes No")
        arcpy.AssignDomainToField_management(projectROP, "rop_status", "ROP Status")
        arcpy.AssignDomainToField_management(projectROP, "three_factors", "YN")
        arcpy.AssignDomainToField_management(projectROP, "request_type", "Request Type")
        arcpy.AssignDomainToField_management(projectROP, "data_form", "Data Form")
        arcpy.AssignDomainToField_management(projectROP, "deter_method", "Method")
    

    #### Create Drainage Lines Layer
    # Don't pull in any Drainage Lines for previously certified areas (people will see them in the display and can copy/paste if needed)
    if resetDrains == 'Yes':
        arcpy.Delete_management(projectLines)

    if not arcpy.Exists(projectLines):
        AddMsgAndPrint("\nCreating Drainage Lines layer...",0)
        fcName = os.path.basename(projectLines)
        arcpy.CreateFeatureclass_management(wcFD, fcName, "POLYLINE", templateLines)
        del fcName

        arcpy.AssignDomainToField_management(projectLines, "line_type", "Line Type")
        arcpy.AssignDomainToField_management(projectLines, "manip_era", "Pre Post")


    #### Import attribute rules to various layers in the project.
    arcpy.ImportAttributeRules_management(projectSU, rules_su)
    arcpy.ImportAttributeRules_management(projectLines, rules_lines)


    #### Clean up Temporary Datasets
    # Temporary datasets specifically from this tool
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


    #### Add to map
    # Use starting reference layer files for the tool installation to add layer with automatic placement
    m.addLayer(suLyr)
    m.addLayer(ropLyr)
    m.addLayer(drainLyr)
    m.addLayer(extentLyr)

    # Replace data sources of layer files from installed layers to the project layers
    # First get the current layers in the map
    suNew = m.listLayers("Site_Sampling_Units")[0]
    ropNew = m.listLayers("Site_ROPs")[0]
    drainNew = m.listLayers("Site_Drainage_Lines")[0]
    extentNew = m.listLayers("Request_Extent")[0]

    # Call the function to change the data source via CIM
    changeSource(suNew, new_ws=wcGDB_path, new_fd=wcFD_name, new_fc=suName)
    changeSource(ropNew, new_ws=wcGDB_path, new_fd=wcFD_name, new_fc=ropName)
    changeSource(drainNew, new_ws=wcGDB_path, new_fd=wcFD_name, new_fc=drainName)
    changeSource(extentNew, new_ws=basedataGDB_path, new_fd=basedataFD_name, new_fc=extentName)

    # Update the layer names to the development names (now redundant; can comment out or remove)
    suNew.name = suName
    ropNew.name = ropName
    drainNew.name = drainName
    extentNew.name = extentName
    
    #arcpy.SetParameterAsText(8, projectSU)
    #arcpy.SetParameterAsText(9, projectROP)
    #arcpy.SetParameterAsText(10, projectLines)
    #arcpy.SetParameterAsText(11, projectExtent)

    
    #### Adjust visibility of layers to aid in moving to the next step in the process
    # Turn off all CLUs/Common, Define_AOI, and Extent layers
    off_names = ["CLU","Common","Site_Define_AOI","Request_Extent"]
    for maps in aprx.listMaps():
        for lyr in maps.listLayers():
            for name in off_names:
                if name in lyr.name:
                    lyr.visible = False

    # Turn on all SU, ROP, and Drainage_Lines layers
    on_names = ["Site_Sampling_Units","Site_Drainage_Lines","Site_ROPs"]
    for maps in aprx.listMaps():
        for lyr in maps.listLayers():
            for name in on_names:
                if (lyr.name).startswith(name):
                    lyr.visible = True


    #### Clear selections from source AOI layer if it was used with selections
    if selectFields == 'Yes':
        define_name = "Site_Define_AOI"
        define_lyr = m.listLayers(define_name)[0]
        arcpy.SelectLayerByAttribute_management(define_lyr, "CLEAR_SELECTION")
    
    
    #### Compact FGDB
    try:
        AddMsgAndPrint("\nCompacting File Geodatabases..." ,0)
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
