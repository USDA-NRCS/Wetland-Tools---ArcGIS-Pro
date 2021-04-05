## ===============================================================================================================
## Name:    Create CWD Layers
## Purpose: Use the request extent and sampling units layers to create the CWD layer(s), including import of
##          previously certified data where applicable. Also adds the Potential Jurisdictional Waters (PJW) layer
##          and previously certified layer (if applicable) to the project.
##
## Authors: Chris Morse
##          GIS Specialist
##          Indianapolis State Office
##          USDA-NRCS
##          chris.morse@usda.gov
##          317.295.5849
##
## Created: 03/23/2021
##
## ===============================================================================================================
## Changes
## ===============================================================================================================
##
## rev. 03/23/2021
## -Started updated from ArcMap NRCS Compliance Tools and the Create WC Layer tool.
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
    f.write("Executing Create CWD Layers tool...\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("User Parameters:\n")
    f.write("\tInput Sampling Units Layer: " + str(sourceSU) + "\n")
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
def removeLayers(layer_list):
    # Remove the layers in the list
    try:
        for maps in aprx.listMaps():
            for lyr in maps.listLayers():
                if lyr.name in layer_list:
                    maps.removeLayer(lyr)
    except:
        pass

## ===============================================================================================================
def removeFCs(fc_list, wc='', ws ='', in_topos=''):
    # Start by removing the topology items if a topology list was sent; this removes topology locks on layers
    if in_topos != '':
        for topo in in_topos:
            if arcpy.Exists(topo):
                try:
                    arcpy.Delete_management(topo)
                except:
                    pass

    # Use the wildcard to find annotation related to the datasets in the ws and add them to the delete list
    if wc != '':
        startWorkspace = arcpy.env.workspace
        arcpy.env.workspace = ws
        fcs = []
        for fds in arcpy.ListDatasets('', 'feature') + ['']:
            for fc in arcpy.ListFeatureClasses(wc, 'Annotation', fds):
                fcs.append(os.path.join(ws, fds, fc))
        for fc in fcs:
            fc_list.append(fc)
        arcpy.env.workspace = startWorkspace
        del startWorkspace

    # Remove the datasets in the list
    for dataset in fc_list:
        if arcpy.Exists(dataset):
            try:
                arcpy.Delete_management(dataset)
            except:
                pass


## ===============================================================================================================
def createCWD():
    #### Remove existing extent and CWD related layers from the Pro maps to create or re-create them
    AddMsgAndPrint("\nRemoving Request Extent and CWD related layers from project maps, if present...\n",0)

    # Set layers to remove from the map
    mapLayersToRemove = [extentName, cwdName, cluCwdName]

    # Find Sampling Unit related annotation layers to add to the list of map layers to be removed
    cwdAnnoString = "Site_CWD" + "Anno*"
    clucwdAnnoString = "Site_CLU_CWD" + "Anno*"
    anno_list = [cwdAnnoString, clucwdAnnoString]
    for maps in aprx.listMaps():
        for anno in anno_list:
            for lyr in maps.listLayers(anno):
                mapLayersToRemove.append(lyr.name)

    # Remove the layers
    removeLayers(mapLayersToRemove)
    del mapLayersToRemove

    # Remove existing cwd layers from the geodatabase to create or re-create them
    AddMsgAndPrint("\nRemoving CWD related layers from project database, if present...\n",0)
    datasetsToRemove = [projectCWD]
    toposToRemove = [cwdTopo]
    wildcard = '*CWD*'
    wkspace = wcGDB_path
    removeFCs(datasetsToRemove, wildcard, wkspace, toposToRemove)
    del datasetsToRemove, wildcard, wkspace, toposToRemove

    
    #### Create the CWD Layer
    AddMsgAndPrint("\nConverting Sampling Units to the CWD layer...",0)
    # Create an empty CWD feature class that will eventually be loaded with the finished data
    arcpy.CreateFeatureclass_management(wcFD, cwdName, "POLYGON", templateCWD)

    # Clip the SU layer by the request extent layer
    arcpy.Clip_analysis(projectSU, projectExtent, SU_Clip_Temp)

    # Clip the SU layer by the New Request areas of the Request Extent layer
    arcpy.MakeFeatureLayer_management(projectExtent, "extentTemp")
    arcpy.SelectLayerByAttribute_management("extentTemp", "NEW_SELECTION", "\"eval_status\" = 'New Request'")
    arcpy.CopyFeatures_management("extentTemp", extentTemp1)
    arcpy.Clip_analysis(projectSU, extentTemp1, SU_Clip_New)
    arcpy.Delete_management("extentTemp")
    
    # Check if prevAdmin exists and process accordingly
    if arcpy.Exists(prevAdmin):
        AddMsgAndPrint("\tPrevious Certifications on the tract exist. Resolving potential conflicts with Sampling Units...",0)
        arcpy.Clip_analysis(SU_Clip_Temp, prevAdmin, Prev_SU_Temp)

        # Check for Revisions in the Prev_SU_Temp layer
        arcpy.MakeFeatureLayer_management(Prev_SU_Temp, "Previous_SU")
        arcpy.SelectLayerByAttribute_management("Previous_SU", "NEW_SELECTION", "\"eval_status\" = 'Revision'")
        count = int(arcpy.GetCount_management("Previous_SU").getOutput(0))
        if count > 0:
            # Revsions found. Integrate them.
            AddMsgAndPrint("\tRevisions found! Using Revisions to update CWD areas...",0)
            arcpy.CopyFeatures_management("Previous_SU", suRev)
            arcpy.Delete_management("Previous_SU")

            #Use suRev to Erase revised areas from the prevCert and prevAdmin layers and create updatedCert and updatedAdmin layers
            arcpy.Erase_analysis(prevAdmin, suRev, updatedAdmin)
            arcpy.Erase_analysis(prevCert, suRev, updatedCert)

            # Check to see if any features remain in updatedAdmin
            count = int(arcpy.GetCount_management(updatedAdmin).getOutput(0))
            if count > 0:
                # It is a partial revision to certified areas within the request extent
                AddMsgAndPrint("\tRevisions cover part of previously certified areas. Integrating Revisions to the determination...",0)
                
                # Append the suRev to the SU_Clip_New to create the draft CWD layer
                arcpy.Append_management(suRev, SU_Clip_New, "NO_TEST")

                # Erase the prevAdmin area from the Request Extent Layer to make a new temp Request Extent Layer
                arcpy.Erase_analysis(projectExtent, prevAdmin, extentTemp2)
                
                # Append the updatedAdmin area to the Temp Request Extent Layer to make a partial version of the new Request Extent Layer to come
                arcpy.Append_management(updatedAdmin, extentTemp2, "NO_TEST")
                
                # Dissolve the suRev layer to make the suRevDissolve layer as a consolidated area of revisions. Update the 'job_id' to the current job afterwards.
                dissolve_fields = ['job_id','admin_state', 'admin_state_name','admin_county','admin_county_name','state_code','state_name','county_code','county_name','farm_number','tract_number','eval_status']
                arcpy.Dissolve_management(suRev, suRevDissolve)

                workspace = scratchGDB
                edit = arcpy.da.Editor(workspace)
                edit.startEditing(False,False)
                fields = ['job_id']
                cursor = arcpy.da.UpdateCursor(suRevDissolve, fields)
                for row in cursor:
                    row[0] = cur_id
                    cursor.updateRow(row)
                del cursor, fields
                edit.stopEditing(True)
                del workspace, edit
                
                # Append the suRevDissolve to the Temp Request Extent Layer to complete the draft version of the new Request Extent layer.
                arcpy.Append_management(suRevDissolve, extentTemp2, "NO_TEST")
                
                # Copy the Temp Request Extent Layer to a new permanent Request Extent Layer (overwrite replaces the original projectExtent)
                arcpy.CopyFeatures_management(extentTemp2, projectExtent)
                
                # Append the features of the draft CWD layer to the CWD feature class
                arcpy.Append_management(SU_Clip_New, projectCWD, "NO_TEST")
                
                # The updatedCert layer can be made into the prevCertSite layer and can be added to the map at the end of the tool (verify).
                arcpy.CopyFeatures_management(updatedCert, prevCertSite)

            else:
                # It is a complete revision of the entire certified area within the request extent
                AddMsgAndPrint("\tRevisions are to entire existing certified area. Integrating Revisions to the determination...",0)
                
                # Append the suRev to the SU_Clip_New to create the draft CWD layer
                arcpy.Append_management(suRev, SU_Clip_New, "NO_TEST")

                # Convert the "Certified-Digital" areas of the Request Extent Layer to "Revision"
                workspace = scratchGDB
                edit = arcpy.da.Editor(workspace)
                edit.startEditing(False,False)
                fields = ['job_id','eval_status']
                cursor = arcpy.da.UpdateCursor(projectExtent, fields)
                for row in cursor:
                    row[0] = cur_id
                    if row[1] == "Certified-Digital":
                        row[1] = "Revision"
                    cursor.updateRow(row)
                del cursor, fields
                edit.stopEditing(True)
                del workspace, edit

                # Append the features of the draft CWD layer to the CWD feature class
                arcpy.Append_management(SU_Clip_New, projectCWD, "NO_TEST")

                # The prevCert layer should be removed from the map and/or not be re-added to the map at the end of the tool (verify).

        else:
            # The revisions are not in the previously certified areas. Don't update the prevCert and change false Revision status flags to New Request
            AddMsgAndPrint("\tRevisions do not cover the previously certified areas. Resolving Revisions as New Request areas...",0)

            # Convert any "Revision" areas within the SU_Clip_New back to "New_Request"
            workspace = scratchGDB
            edit = arcpy.da.Editor(workspace)
            edit.startEditing(False,False)
            fields = ['eval_status']
            cursor = arcpy.da.UpdateCursor(SU_Clip_New, fields)
            for row in cursor:
                if row[0] == "Revision":
                    row[0] = "New Request"
                cursor.updateRow(row)
            del cursor, fields
            edit.stopEditing(True)
            del workspace, edit

            # Append the results into the empty CWD feature class
            arcpy.Append_management(SU_Clip_New, projectCWD, "NO_TEST")

            # The prevCert can be made into the prevCertSite layer and can be added to the map at the end of the tool (verify).
            arcpy.CopyFeatures_management(prevCert, prevCertSite)

    else:
        # No previous certified areas exist and it's a new site only
        AddMsgAndPrint("\tNo previously certified areas on the tract. Processing Sampling Units...",0)
        
        # Convert any "Revision" areas within the SU_Clip_New back to "New_Request"
        workspace = scratchGDB
        edit = arcpy.da.Editor(workspace)
        edit.startEditing(False,False)
        fields = ['eval_status']
        cursor = arcpy.da.UpdateCursor(SU_Clip_New, fields)
        for row in cursor:
            if row[0] == "Revision":
                row[0] = "New Request"
            cursor.updateRow(row)
        del cursor, fields
        edit.stopEditing(True)
        del workspace, edit
        
        # Append the results into the empty CWD feature class
        arcpy.Append_management(SU_Clip_New, projectCWD, "NO_TEST")


    #### Assign domains to the CWD layer
    AddMsgAndPrint("\nUpdating attribute domains for CWD layer...",0)
    arcpy.AssignDomainToField_management(projectCWD, "eval_status", "Evaluation Status")
    arcpy.AssignDomainToField_management(projectCWD, "wetland_label", "Wetland Labels")
    arcpy.AssignDomainToField_management(projectCWD, "three_factors", "YN")
    arcpy.AssignDomainToField_management(projectCWD, "request_type", "Request Type")
    arcpy.AssignDomainToField_management(projectCWD, "deter_method", "Method")

    
    #### Update the attributes of the CWD layer
    # Update the job_id of the CWD layer
    workspace = wcGDB_path
    edit = arcpy.da.Editor(workspace)
    edit.startEditing(False,False)
    fields = ['job_id']
    cursor = arcpy.da.UpdateCursor(projectCWD, fields)
    for row in cursor:
        row[0] = cur_id
        cursor.updateRow(row)
    del cursor, fields

    
    # Update the acres of the CWD layer
    expression = "!Shape.Area@acres!"
    arcpy.CalculateField_management(projectCWD, "acres", expression, "PYTHON_9.3")
    del expression

    # Get admin attributes from project table for request_date, request_type, deter_staff, dig_staff, and dig_date (current date) and assign them to New/Revised areas
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
        del cursor, fields
    edit.stopEditing(True)
    del workspace, edit

    #### Import attribute rules
    arcpy.ImportAttributeRules_management(projectCWD, rules_cwd)
    

## ===============================================================================================================
def createPJW():
    #### Remove existing PJW related layers from the Pro maps
    AddMsgAndPrint("\nRemoving PJW related layers from project maps, if present...\n",0)

    # Set PJW related layers to remove from the map
    mapLayersToRemove = [pjwName]

    # Remove the layers
    removeLayers(mapLayersToRemove)
    del mapLayersToRemove

    # Remove existing PJW layers from the geodatabase
    AddMsgAndPrint("\nRemoving PJW related layers from project database, if present...\n",0)
    datasetsToRemove = [projectPJW]
    wildcard = '*PJW*'
    wkspace = wcGDB_path
    removeFCs(datasetsToRemove, wildcard, wkspace)
    del datasetsToRemove, wildcard, wkspace

    if not arcpy.Exists(projectPJW):
        AddMsgAndPrint("\tThe projectPJW layer was deleted or did not exist",0)
        
    #### Create the PJW Layer
    AddMsgAndPrint("\nCreating the PJW layer...\n",0)
    arcpy.CreateFeatureclass_management(wcFD, pjwName, "POINT", templatePJW)
    
    #### Import attribute rules to various layers in the project.
    arcpy.ImportAttributeRules_management(projectPJW, rules_pjw)


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
    resetCWD = arcpy.GetParameterAsText(1)
    resetPJW = arcpy.GetParameterAsText(2)
    existingCWD = arcpy.GetParameterAsText(3)                   #### MISSING FROM SCRIPT
    cwdLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(4))
    pjwLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(5))
    extLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(6))


    #### Initial Validations
    arcpy.AddMessage("Verifying inputs...\n")
    # If SU layer has features selected, clear the selections so that all features from it are processed.
    clear_lyr = m.listLayers(sourceSU)[0]
    arcpy.SelectLayerByAttribute_management(clear_lyr, "CLEAR_SELECTION")
    
                
    #### Set base path
    sourceSU_path = arcpy.Describe(sourceSU).CatalogPath
    if sourceSU_path.find('.gdb') > 0 and sourceSU_path.find('Determinations') > 0 and sourceSU_path.find('Site_Sampling_Units') > 0:
        wcGDB_path = sourceSU_path[:sourceSU_path.find('.gdb')+4]
    else:
        arcpy.AddError("\nSelected Site Sampling Units layer is not from a Determinations project folder. Exiting...")
        exit()


    #### Define Variables
    arcpy.AddMessage("Setting variables...\n")
    supportGDB = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb")
    scratchGDB = os.path.join(os.path.dirname(sys.argv[0]), "SCRATCH.gdb")
    templateCWD = supportGDB + os.sep + "master_cwd"
    templatePJW = supportGDB + os.sep + "master_pjw"

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

    cluName = "Site_CLU"
    defineName = "Site_Define_AOI"
    ropName = "Site_ROPs"
    refName = "Site_Reference_Points"
    drainName = "Site_Drainage_Lines"
    cluCwdName = "Site_CLU_CWD"

    projectTable = basedataGDB_path + os.sep + "Table_" + projectName
    wetDetTableName = "Admin_Table"
    wetDetTable = wcGDB_path + os.sep + wetDetTableName

    extentName = "Request_Extent"
    projectExtent = basedataFD + os.sep + extentName
    extentTemp1 = scratchGDB + os.sep + "Extent_Temp_1"
    extentTemp2 = scratchGDB + os.sep + "Extent_Temp_2"
    
    suName = "Site_Sampling_Units"
    projectSU = wcFD + os.sep + suName
    SU_Clip_Temp = scratchGDB + os.sep + "suClipTemp"
    SU_Clip_New = scratchGDB + os.sep + "suClipNew"
    Prev_SU_Temp = scratchGDB + os.sep + "prevSuTemp"
    suRev = scratchGDB + os.sep + "suRevised"
    suRevDissolve = scratchGDB + os.sep + "suRevDis"
    
    cwdName = "Site_CWD"
    projectCWD = wcFD + os.sep + cwdName

    pjwName = "Site_PJW"
    projectPJW = wcFD + os.sep + pjwName

    cwdTopoName = "CWD_Topology"
    cwdTopo = wcFD + os.sep + cwdTopoName
    
    prevCert = wcFD + os.sep + "Previous_CWD"
    prevCertSite = wcFD + os.sep + "Site_Previous_CWD"
    prevAdmin = wcFD + os.sep + "Previous_Admin"
    prevAdminSite = wcFD + os.sep + "Site_Previous_Admin"
    updatedCert = wcFD + os.sep + "Updated_Cert"
    updatedAdmin = wcFD + os.sep + "Updated_Admin"
    
    # Attribute rule files
    rules_cwd = os.path.join(os.path.dirname(sys.argv[0]), "Rules_CWD.csv")
    rules_pjw = os.path.join(os.path.dirname(sys.argv[0]), "Rules_PJW.csv")

    # Temp layers list for cleanup at the start and at the end
    tempLayers = [extentTemp1, extentTemp2, SU_Clip_Temp, SU_Clip_New, Prev_SU_Temp, suRev, suRevDissolve]
    deleteTempLayers(tempLayers)


    #### Set up log file path and start logging
    arcpy.AddMessage("Commence logging...\n")
    textFilePath = userWorkspace + os.sep + projectName + "_log.txt"
    logBasicSettings()

        
    #### Check Project Integrity
    AddMsgAndPrint("\nChecking project integrity...",0)

    # If project wetlands geodatabase and feature dataset do not exist, exit.
    if not arcpy.Exists(wcGDB_path):
        AddMsgAndPrint("\tInput Site Sampling Unit layer is not part of a wetlands tool project folder. Exiting...",2)
        exit()

    if not arcpy.Exists(wcFD):
        AddMsgAndPrint("\tInput Site Sampling Unit layer is not part of a wetlands tool project folder. Exiting...",2)
        exit()

    # Copy the administrative table into the wetlands database for use with the attribute rules during digitizing
    # Repeated in case enter project info was re-run in between steps.
    if arcpy.Exists(wetDetTable):
        arcpy.Delete_management(wetDetTable)
    arcpy.TableToTable_conversion(projectTable, wcGDB_path, wetDetTableName)

    # Add or validate the attribute domains for the wetlands geodatabase
    AddMsgAndPrint("\tChecking attribute domains...",0)
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
    

    #### Get the current job_id for use in processing
    fields = ['job_id']
    cursor = arcpy.da.SearchCursor(wetDetTable, fields)
    for row in cursor:
        cur_id = row[0]
        break
    del cursor, fields
    
    
    #### Create or Reset the CWD layer
    if not arcpy.Exists(projectCWD):
        createCWD()
    if resetCWD == "Yes":
        arcpy.Delete_management(projectCWD)
        createCWD()


    #### Create or Reset the PJW Layer
    if not arcpy.Exists(projectPJW):
        createPJW()
    if resetPJW == "Yes":
        arcpy.Delete_management(projectPJW)
        createPJW()


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


    #### Add to map
    # Use starting reference layer files from the tool installation to add layers with automatic placement
    lyr_list = m.listLayers()
    if cwdName not in lyr_list:
        m.addLayer(cwdLyr)
    if pjwName not in lyr_list:
        m.addLayer(pjwLyr)
    if extentName not in lyr_list:
        m.addLayer(extLyr)

    # Replace data sources of layer files from installed layers to the project layers. Can always do, even if layer is not new or reset.
    # First get the current layers in the map
    cwdNew = m.listLayers(cwdName)[0]
    pjwNew = m.listLayers(pjwName)[0]
    extNew = m.listLayers(extentName)[0]

    # Call the function to change the data source on add layers
    changeSource(cwdNew, wcGDB_path, cwdName)
    changeSource(pjwNew, wcGDB_path, pjwName)
    changeSource(extNew, wcGDB_path, extentName)
    
    #### Adjust visibility of layers to aid in moving to the next step in the process
    # Turn off all layers from previous steps
    off_names = [cluName, defineName, extentName, suName, ropName, refName, drainName, cluCwdName]
    for maps in aprx.listMaps():
        for lyr in maps.listLayers():
            for name in off_names:
                if name in lyr.name:
                    lyr.visible = False

    # Turn on layers for current steps
    on_names = [cwdName, pjwName]
    for maps in aprx.listMaps():
        for lyr in maps.listLayers():
            for name in on_names:
                if (lyr.name).startswith(name):
                    lyr.visible = True

    
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
