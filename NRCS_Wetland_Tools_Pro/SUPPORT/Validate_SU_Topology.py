## ===============================================================================================================
## Name:    Validate SU Topology
## Purpose: Verify that the user did not create an internal gaps or overlaps within the request extent.
##
## Authors: Chris Morse
##          GIS Specialist
##          Indianapolis State Office
##          USDA-NRCS
##          chris.morse@usda.gov
##          317.295.5849
##
## Created: 11/04/2020
##
## ===============================================================================================================
## Changes
## ===============================================================================================================
##
## rev. 11/04/2020
## Start revisions of Validate Topology ArcMap tool to National Wetlands Tool in ArcGIS Pro.
##
## rev. 11/18/2020
## Check for internal gaps will have to be handled differently because SUs can go beyond extent/tract edges
##      -Use the outer edge of the extent layer itself in place of the tract layer.
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
    f.write("Executing Validate SU Topology tool...\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("User Parameters:\n")
    f.write("\tSampling Unit Layer: " + sourceSU + "\n")
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
        if arcpy.Exists(lyr)
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
    m2 = aprx.listMaps("Data_Templates")[0]
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
    sourceSU = arcpy.GetParameterAsText(0)
    existing_cwd = arcpy.GetParameterAsText(1)
    suLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(2))
    ropLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(3))
    drainLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(4))
    extentLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(5))


    #### Initial Validations
    arcpy.AddMessage("Verifying inputs...\n")
    # If SU layer has features selected, clear the selections so that all features from it are processed.
    clear_lyr = m.listLayers(sourceSU)[0]
    arcpy.SelectLayerByAttribute_management(clear_lyr, "CLEAR_SELECTION")


    #### Set base path
    sourceSU_path = arcpy.Describe(sourceSU).CatalogPath
    if sourceSU_path.find('.gdb') > 0 and sourceSU_path.find('Determinations') > 0 and sourceSU_path.find('SU_') > 0:
        wcGDB_path = sourceSU_path[:sourceSU_path.find('.gdb')+4]
    else:
        arcpy.AddError("\nSelected SU layer is not from a Determinations project folder. Exiting...")
        exit()


    #### Do not run if an unsaved edits exist in the target workspace
    # Pro opens an edit session when any edit has been made and stays open until edits are committed with Save Edits.
    # Check for uncommitted edits and exit if found, giving the user a message directing them to Save or Discard them.
    workspace = wcGDB_path
    edit = arcpy.da.Editor(workspace)
    if edit.isEditing:
        arcpy.AddError("\nYou have an active edit session. Please Save or Discard Edits and then run this tool again. Exiting...")
        exit()
    del workspace, edit


    #### Define Variables
    arcpy.AddMessage("Setting variables...\n")
    wetDir = os.path.dirname(wcGDB_path)
    wcFD = wcGDB_path + os.sep + "WC_Data"
    userWorkspace = os.path.dirname(wetDir)
    projectName = os.path.basename(userWorkspace).replace(" ", "_")
    basedataGDB_path = userWorkspace + os.sep + projectName + "_BaseData.gdb"
    basedataFD_name = "Layers"
    basedataFD = basedataGDB_path + os.sep + basedataFD_name 
    
    supportGDB = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb")
    scratchGDB = os.path.join(os.path.dirname(sys.argv[0]), "SCRATCH.gdb")
    templateSU = supportGDB + os.sep + "master_sampling_units"
    templateROP = supportGDB + os.sep + "master_rop"
    templateLines = supportGDB + os.sep + "master_drainage_lines"
    templateExtent = supportGDB + os.sep + "master_extent"

    suName = "SU_" + projectName
    projectSU = wcFD + os.sep + suName
    suBackup = wcFD + os.sep + "suBackup1"
    ropName = "ROPs_" + projectName
    projectROP = wcFD + os.sep + ropName
    drainName = "Drainage_Lines_" + projectName
    projectLines = wcFD + os.sep + drainName
    extentName = "Extent_" + projectName
    projectExtent = basedataFD + os.sep + extentName
    projectCLU = basedataFD + os.sep + "CLU_" + projectName
    projectTract = basedataFD + os.sep + "Tract_" + projectName
    projectTable = basedataGDB_path + os.sep + "Table_" + projectName

    prevCert = wcFD + os.sep + "PCWD_" + projectName
    prevAdmin = wcFD + os.sep + "PCWD_Admin_" + projectName
    updatedCert = wcFD + os.sep + "MCWD_" + projectName
    updatedAdmin = wcFD + os.sep + "MCWD_Admin" + projectName

    suTemp1 = scratchGDB + os.sep + "SU_Temp1_" + projectName
    suTemp2 = scratchGDB + os.sep + "SU_Temp2_" + projectName
    suSingle = scratchGDB + os.sep + "SU_Single" + projectName

    # Topology stuff
    suTopoName = "SU_Topology_" + projectName
    suTopo = wcFD + os.sep + suTopoName
    tractTemp = wcFD + os.sep + "Tract_Copy_" + projectName

    # Empty Topo Error Feature Classes
    linesTopoFC = wcFD + os.sep + "SU_Errors_line"
    pointsTopoFC = wcFD + os.sep + "SU_Errors_point"
    # Topo Error Polygon based rules feature class
    polysTopoFC = wcFD + os.sep + "SU_Errors_poly"

    # ArcPro Map Layer Names
    tractCopyOut = "Tract_Copy_" + projectName
    suOut = "SU_" + projectName
    suTopoOut = suTopoName
    
    # Annotation Layer Names (in map)
    anno_list = []
    suAnnoString = "SU_" + projectName + "Anno*"
    #ropAnnoString = "ROPs_" + projectName + "Anno*"
    #drainAnnoString = "Drainage_Lines_" + projectName + "Anno*"

    anno_list.append(suAnnoString)
    #anno_list.append(ropAnnoString)
    #anno_list.append(drainAnnoString)
    
    # Attribute rules files
    rules_su = os.path.join(os.path.dirname(sys.argv[0]), "Rules_SU.csv")
    rules_lines = os.path.join(os.path.dirname(sys.argv[0]), "Rules_Drains.csv")
    
    # Temp layers list for cleanup at the start and at the end
    tempLayers = [suTemp1, suTemp2, suSingle, tractTemp]
    deleteTempLayers(tempLayers)
    

    #### Set up log file path and start logging
    arcpy.AddMessage("Commence logging...\n")
    textFilePath = userWorkspace + os.sep + projectName + "_log.txt"
    logBasicSettings()


    #### If project wetlands feature dataset does not exist, exit.
    if not arcpy.Exists(wcFD):
        AddMsgAndPrint("\tInput SU layer does not come from an expected project feature dataset. Please re-run and select a valid SU layer. Exiting...",2)
        exit()


    #### Remove existing sampling unit related layers from the Pro maps
    AddMsgAndPrint("\nRemoving layers from project maps, if present...\n",0)
    
    # Set starting layers to be removed
    mapLayersToRemove = [suOut, extentOut, suTopoOut]

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


    #### Remove existing sampling unit topology related layers from the geodatabase
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
    datasetsToRemove = [tractTemp]

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


    #### Update the SU Layer geometry
    AddMsgAndPrint("\nReviewing SU Layer Geometry...",0)

    # Copy the original projectSU layer to create a pre-processing backup
    try:
        arcpy.Delete_management(suBackup)
    except:
        pass
    arcpy.CopyFeatures_management(projectSU, suBackup)

    # Enforce tract boundary
    AddMsgAndPrint("\nEnforcing tract boundary...",0)

    # Clip the SU feature class by the tract boundary, then discard the starting SU feature class to regenerate it throughout this process
    # This clip is being done to restrict determinations to stay within the tract boundary of the current request.
    arcpy.Clip_analysis(projectSU, projectTract, suTemp1)
    arcpy.Delete_management(projectSU)


    #### Update the extent layer
    # Look for revised status polygons to create an up to date set of revised SU polygon areas and regenerate an extent.
    arcpy.MakeFeatureLayer_management(suTemp1, "rev_su_temp")
    arcpy.SelectLayerByAttribute_management("rev_su_temp", "NEW_SELECTION", "\"eval_status\" = 'REV'")
    count = int(arcpy.GetCount_management("rev_su_temp").getOutput(0))
    if count > 0:
        if arcpy.Exists(suRev):
            arcpy.Delete_management(suRev)
        arcpy.CopyFeatures_management("rev_su_temp", suRev)
        arcpy.Delete_management("rev_su_temp")
        
        # Append the revised features to the extent layer and then dissolve again to regenerate the extent layer with the new extent
        

    else:
        arcpy.Delete_management("rev_su_temp")
    del count






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
    AddMsgAndPrint("\tChecking for existing CWD data in the Tract...",0)
    # Use intersect so that you apply current tract data to the existing CWD in case it changed over time
    arcpy.Intersect_analysis([projectTract, existing_cwd], prevCertMulti, "NO_FID", "#", "INPUT")

    # Check for any results
    result = int(arcpy.GetCount_management(prevCertMulti).getOutput(0))
    if result > 0:
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

    # Assign domains to the SU layer
    arcpy.AssignDomainToField_management(projectSU, "locked", "Yes No")
    arcpy.AssignDomainToField_management(projectSU, "eval_status", "Evaluation Status")
    arcpy.AssignDomainToField_management(projectSU, "three_factors", "YN")
    arcpy.AssignDomainToField_management(projectSU, "request_type", "Request Type")
    arcpy.AssignDomainToField_management(projectSU, "deter_method", "Method")
    
    # If entire requested area is certified, use the extent to intersect prevCert features and make them into Sampling Units with an eval_status of Certified-Digital. Do not dissolve.
    if fullCWD:
        arcpy.Intersect_analysis([projectExtent, prevCert], suMulti, "NO_FID", "#", "INPUT")
        arcpy.MultipartToSinglepart_management(suMulti, suTemp1)
        arcpy.Append_management(suTemp1, projectSU, "NO_TEST")
    
    # Else, use the extent to intersect the CLU (and optionally dissolve it); and then append prevCert area (without dissolve) if present
    else:
        arcpy.Intersect_analysis([projectExtent, projectCLU], suMulti, "NO_FID", "#", "INPUT")
        arcpy.MultipartToSinglepart_management(suMulti, suTemp1)

        # Dissolve out field lines if that option was selected
        if keepFields == "No":
            dis_fields = ['admin_state','admin_state_name','admin_county','admin_county_name','state_code','state_name','county_code','county_name','farm_number','tract_number','eval_status']
            arcpy.Dissolve_management(suTemp1, suTemp2, dis_fields, "", "SINGLE_PART", "")

            # Clean up dissolve related attributes
            arcpy.Append_management(suTemp2, projectSU, "NO_TEST")

        else:
            arcpy.Append_management(suTemp1, projectSU, "NO_TEST")

        # Assign eval_status attribute as "New Request"
        fields = ['eval_status','locked']
        cursor = arcpy.da.UpdateCursor(projectSU, fields)
        for row in cursor:
            row[0] = "New Request"
            row[1] = "No"
            cursor.updateRow(row)
        del cursor

        # Append Certified Digital areas to the sampling unit layer
        if arcpy.Exists(prevCert):
            arcpy.Append_management(prevCert, projectSU, "NO_TEST")


    #### Update additional SU layer attributes
    # Update calculated acres
    expression = "!Shape.Area@acres!"
    arcpy.CalculateField_management(projectSU, "acres", expression, "PYTHON_9.3")
    del expression

    ## Update attributes: request_date, request_type, deter_staff, dig_staff, and dig_date (current date) from projectTable for New Request areas
    # Get admin attributes from admin info file
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
            if row[0] == "New Request":
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
    suNew = m.listLayers("Sampling Units")[0]
    ropNew = m.listLayers("ROPs")[0]
    drainNew = m.listLayers("Drainage Lines")[0]
    extentNew = m.listLayers("Extent")[0]

    # Call the function to change the data source via CIM
    changeSource(suNew, new_ws=wcGDB_path, new_fd=wcFD_name, new_fc=suName)
    changeSource(ropNew, new_ws=wcGDB_path, new_fd=wcFD_name, new_fc=ropName)
    changeSource(drainNew, new_ws=wcGDB_path, new_fd=wcFD_name, new_fc=drainName)
    changeSource(extentNew, new_ws=basedataGDB_path, new_fd=basedataFD_name, new_fc=extentName)

    # Update the layer names to the development names
    suNew.name = suName
    ropNew.name = ropName
    drainNew.name = drainName
    extentNew.name = extentName
    
    #arcpy.SetParameterAsText(8, projectSU)
    #arcpy.SetParameterAsText(9, projectROP)
    #arcpy.SetParameterAsText(10, projectLines)
    #arcpy.SetParameterAsText(11, projectExtent)
    #m.addDataFromPath(projectSU)
    #m.addDataFromPath(projectExtent)
    #m.addDataFromPath(projectROP)
    #m.addDataFromPath(projectLines)


##    #### Try to apply/update symbology on newly added map layers using template layers
##    for lyr in m2.listLayers():
##        if lyr.name == "ROPs":
##            ropSym = lyr
##        elif lyr.name == "Drainage Lines":
##            drainSym = lyr
##        elif lyr.name == "Sampling Units":
##            suSym = lyr
##
##    ropSym = os.path.join(os.path.dirname(sys.argv[0]), "layer_files") + os.sep + "ROP.lyrx"
##    drainSym = os.path.join(os.path.dirname(sys.argv[0]), "layer_files") + os.sep + "Drainage_Lines.lyrx"
##    suSym = os.path.join(os.path.dirname(sys.argv[0]), "layer_files") + os.sep + "Sampling_Units.lyrx"
##
##    for maps in aprx.listMaps():
##        for lyr in maps.listLayers():
##            if lyr.name == ropOut:
##                arcpy.ApplySymbologyFromLayer_management(lyr, ropSym)
##            elif lyr.name == drainOut:
##                #symFields = [["VALUE_FIELD", "line_type", "line_type"],["VALUE_FIELD", "manip_era", "manip_era"]]
##                arcpy.ApplySymbologyFromLayer_management(lyr, drainSym)
##            elif lyr.name == suOut:
##                arcpy.ApplySymbologyFromLayer_management(lyr, suSym)

    
    #### Adjust visibility of layers to aid in moving to the next step in the process
    # Turn off all CLUs/Common, Define_AOI, and Extent layers
    off_names = ["CLU","Common","Define_AOI","Extent"]
    for maps in aprx.listMaps():
        for lyr in maps.listLayers():
            for name in off_names:
                if name in lyr.name:
                    lyr.visible = False

    # Turn on all SU, ROP, and Drainage_Lines layers
    on_names = ["SU_","Drainage_Lines_","ROPs_"]
    for maps in aprx.listMaps():
        for lyr in maps.listLayers():
            for name in on_names:
                if (lyr.name).startswith(name):
                    lyr.visible = True


    #### Clear selections from source AOI layer if it was used with selections
    if selectFields == 'Yes':
        define_name = "Define_AOI_" + projectName
        define_lyr = m.listLayers(define_name)[0]
        arcpy.SelectLayerByAttribute_management(define_lyr, "CLEAR_SELECTION")
    
    
    #### Compact FGDB
    try:
        AddMsgAndPrint("\nCompacting File Geodatabase..." ,0)
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
