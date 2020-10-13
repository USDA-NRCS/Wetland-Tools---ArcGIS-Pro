## ===============================================================================================================
## Name:    Define Request AOI
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
##      -Add creation of pCert feature class
##      -Add creation of pCertArea feature class
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
    existing_cwd = arcpy.GetParameterAsText(5)


    #### Initial Validations
    # If whole tract is 'No' and select fields is 'Yes', make sure projectDAOI has features selected, else exit
    if wholeTract == 'No':
        if selectFields == 'Yes':
            desc = arcpy.Describe(sourceDefine)
            if desc.FIDset == '':
                arcpy.AddError('Selected fields option was used, but the input Define AOI layer has no fields selected. Exiting...',2)
                exit()

                
    #### Set base path
    sourceDefine_path = arcpy.Describe(sourceDefine).CatalogPath
    if sourceDefine_path.find('.gdb') > 0 and sourceDefine_path.find('Determinations') > 0 and sourceDefine_path.find('Define_') > 0:
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
    basedataGDB_name = os.path.basename(basedataGDB_path)
    basedataFD = basedataGDB_path + os.sep + "Layers"
    projectName = os.path.basename(userWorkspace).replace(" ", "_")
    userWorkspace = os.path.dirname(basedataGDB_path)

    wetDir = userWorkspace + os.sep + "Wetlands"
    wcGDB_name = os.path.basename(userWorkspace).replace(" ", "_") + "_WC.gdb"
    wcGDB_path = wetDir + os.sep + wcGDB_name
    wc_fd = wcGDB_path + os.sep + "WC_Data"
    
    projectCLU = basedataFD + os.sep + "CLU_" + projectName
    projectTract = basedataFD + os.sep + "Tract_" + projectName
    projectTractB = basedataFD + os.sep + "Tract_Buffer_" + projectName
    projectAOI = basedataFD + os.sep + "AOI_" + projectName
    projectDAOI = basedataFD + os.sep + "Define_AOI_" + projectName
    projectSU = wc_fd + os.sep + "SU_" + projectName
    projectROP = wc_fd + os.sep + "ROPs_" + projectName
    projectLines = wc_fd + os.sep + "Drainage_Lines_" + projectName
    extentName = "Extent_" + projectName
    projectExtent = basedataFD + os.sep + extentName
    extTempName = "Extent_temp_" + projectName
    extentTemp = basedataFD + os.sep + extTempName
    templateExtent = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "master_extent")
    suTopoName = "SU_Topology_" + projectName
    suTopo = wc_fd + os.sep + suTopoName
    
    # ArcMap Layer Names
    suOut = "SU_" + projectName
    ropOut = "ROPs_" + projectName
    drainOut = "Drainage_Lines_" + projectName
    extentOut = "Extent_" + projectName
    suTopoOut = suTopoName

    # Annotation Layer Names (in map)
    anno_list = []
    suAnnoString = "SU_" + projectName + "Anno*"
    ropAnnoString = "ROPs_" + projectName + "Anno*"
    drainAnnoString = "Drainage_Lines_" + projectName + "Anno*"

    anno_list.append(suAnnoString)
    anno_list.append(ropAnnoString)
    anno_list.append(drainAnnoString)
    

    #### Set up log file path and start logging
    textFilePath = userWorkspace + os.sep + folderName + "_log.txt"
    logBasicSettings()

                
    #### If project wetlands geodatabase and feature dataset does not exist, create them.
    # Get the spatial reference from the Define AOI feature class and use it, if needed
    desc = arcpy.Describe(sourceDefine)
    sr = desc.SpatialReference
    
    if not arcpy.Exists(wcGDB_path):
        AddMsgAndPrint("\nCreating Wetlands geodatabase...",0)
        arcpy.CreateFileGDB_management(wetDir, wcGDB_name, "10.0")

    if not arcpy.Exists(wc_fd):
        AddMsgAndPrint("\nCreating Wetlands feature dataset...",0)
        arcpy.CreateFeatureDataset_management(wcGDB_path, "WC_Data", sr)

    # Add or validate the attribute domains for the wetlands geodatabase
    AddMsgAndPrint("\nChecking attribute domains of wetlands geodatabase...",0)
    descGDB = arcpy.Describe(wcGDB_path)
    domains = descGDB.domains

    if not "CWD Status" in domains:
        cwdTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_cwd_status")
        arcpy.TableToDomain_management(cwdTable, "Code", "Description", wcGDB_path, "CWD Status", "Choices for wetland determination status", "REPLACE")
    if not "Data Form" in domains:
        dataTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_data_form")
        arcpy.TableToDomain_management(dataTable, "Code", "Description", wcGDB_path, "Data Form", "Choices for data form completion", "REPLACE")
    if not "Evaluation Status" in domains:
        evalTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_evaluation_status")
        arcpy.TableToDomain_management(evalTable, "Code", "Description", wcGDB_path, "Evaluation Status", "Choices for evaluation workflow status", "REPLACE")
    if not "Line Type" in domains:
        lineTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_line_type")
        arcpy.TableToDomain_management(lineTable, "Code", "Description", wcGDB_path, "Line Type", "Drainage line types", "REPLACE")
    if not "Method" in domains:
        methodTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_method")
        arcpy.TableToDomain_management(methodTable, "Code", "Description", wcGDB_path, "Method", "Choices for wetland determination method", "REPLACE")
    if not "Pre Post" in domains:
        prepostTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_pre_post")
        arcpy.TableToDomain_management(prepostTable, "Code", "Description", wcGDB_path, "Pre Post", "Choices for date relative to 1985", "REPLACE")
    if not "Request Type" in domains:
        requestTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_request_type")
        arcpy.TableToDomain_management(requestTable, "Code", "Description", wcGDB_path, "Request Type", "Choices for request type form", "REPLACE")
    if not "ROP Status" in domains:
        ropTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_rop_status")
        arcpy.TableToDomain_management(ropTable, "Code", "Description", wcGDB_path, "ROP Status", "Choices for ROP status", "REPLACE")
    if not "Wetland Labels" in domains:
        wetTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_wetland_labels")
        arcpy.TableToDomain_management(wetTable, "Code", "Description", wcGDB_path, "Wetland Labels", "Choices for wetland determination labels", "REPLACE")
    if not "Yes No" in domains:
        yesnoTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_yesno")
        arcpy.TableToDomain_management(yesnoTable, "Code", "Description", wcGDB_path, "Yes No", "Yes or no options", "REPLACE")
    if not "YN" in domains:
        ynTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_yn")
        arcpy.TableToDomain_management(ynTable, "Code", "Description", wcGDB_path, "YN", "Y or N options", "REPLACE")

    del descGDB, domains
    

    #### Remove existing sampling unit related layers from the Pro maps
    AddMsgAndPrint("\nRemoving layers from project maps, if present...\n",0)
    
    # Set starting layers to be removed
    mapLayersToRemove = [suOut, ropOut, drainOut, extentOut, suTopoOut]

    # Look for annotation related to the layers to be removed and append them to the mapLayersToRemove list
    for maps in aprx.listMaps():
        for name in anno_list:
            for lyr in maps.listLayers(name):
                mapLayersToREmove.append(lyr.name)
    
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
    datasetsToRemove = [projectSU, projectROP, projectLines, projectExtent]

    # Look for annotation datasets related to the datasets to be removed and delete them
    startWorkspace = arcpy.env.workspace
    arcpy.env.workspace = wcGDB_path
    fcs = []
    for fds in arcpy.ListDatasets('', 'feature') + ['']:
        for fc in arcpy.ListFeatureClasses('*SU*', 'Annotation', fds):
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
    # If wholeTract or selectFields were set to 'Yes', create via dissolve
    if wholeTract == 'Yes' or selectFields == 'Yes':
        # Create via dissolve
        dissolve_fields = ['admin_state', 'admin_state_name', 'admin_county', 'admin_county_name', 'state_code', 'state_name', 'county_code', 'county_name', 'farm_number', 'tract_number']
        arcpy.Dissolve_management(projectDAOI, projectExtent, dissolve_fields, "", "MULTI_PART")
        del dissolve_fields
    else:
        # Drawn AOI or selected layer was input. Clip using that input and then dissolve it.
        arcpy.Clip_analysis(projectDAOI, sourceAOI, extentTemp)
        dissolve_fields = ['admin_state', 'admin_state_name', 'admin_county', 'admin_county_name', 'state_code', 'state_name', 'county_code', 'county_name', 'farm_number', 'tract_number']
        arcpy.Dissolve_management(extentTemp, projectExtent, dissolve_fields, "", "MULTI_PART")
        del dissolve_fields



    #### Clean up the fields for projectExtent feature class
    # Add the eval_status field for use with integrating possible pre-existing data and assign its domain
    

    # Delete extraneous fields from the extent layer
    existing_fields = []
    for fld in arcpy.ListFields(projectDAOI):
        existing_fields.append(fld.name)
    drop_fields = ['clu_number', 'clu_calculated_acreage', 'highly_erodible_land_type_code', 'creation_date', 'last_change_date']
    for fld in drop_fields:
        if fld not in existing_fields:
            drop_fields.remove(fld)
    if len(drop_fields) > 0:
        arcpy.DeleteField_management(projectDAOI, drop_fields)
    del drop_fields, existing_fields


    #### Create Sampling Unit Layer


    #### Create ROP Layer


    #### Create Drainage Lines Layer


    #### Create and apply attribute rules to various layers in the project.


    #### Clip out and process Sampling Units and ROPs for previously certified areas from server as separate layers in a group for reference and snapping
    # Check parameters for access/existence (verify login, per setup project folder script?)

    #### Prepare to add to map

    
    #### Compact FGDB
    try:
        AddMsgAndPrint("\nCompacting File Geodatabase..." ,0)
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
