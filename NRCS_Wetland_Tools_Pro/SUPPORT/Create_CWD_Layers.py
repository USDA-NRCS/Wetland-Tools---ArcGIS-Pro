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
## - Started updated from ArcMap NRCS Compliance Tools and the Create WC Layer tool.
##
## rev. 05/10/2021
## - Debugging passes to get replacement layers working
## - Change the way that layers are added to the map
##
## rev. 09/21/2021
## - Removed steps to update/replace the wetdetTable which were causing schema locks and attribute rule corruption
## - General code review to clean up edit objects and cursors
##
## rev. 05/06/2022
## - Updated previous determination processing steps
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
                if lyr.longName in layer_list:
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
    AddMsgAndPrint("\nRemoving CWD layers from map...\n",0)
    arcpy.SetProgressorLabel("Removing CWD layers from map...")

    # Remove attribute rules first
    if arcpy.Exists(projectCWD):
        try:
            arcpy.DeleteAttributeRule_management(projectCWD, rules_cwd_names)
        except:
            pass
        
    # Set layers to remove from the map
    mapLayersToRemove = [extentName, cwdName, cluCwdName, prevCertName, suName, ropName, refName, drainName]

    # Find CWD related annotation layers to add to the list of map layers to be removed
    cwdAnnoString = "Site_CWD" + "Anno*"
    clucwdAnnoString = "Site_CLU_CWD" + "Anno*"
    anno_list = [cwdAnnoString, clucwdAnnoString]
    for maps in aprx.listMaps():
        for anno in anno_list:
            for lyr in maps.listLayers(anno):
                mapLayersToRemove.append(lyr.longName)

    # Remove the layers
    removeLayers(mapLayersToRemove)
    del mapLayersToRemove

    # Remove existing cwd layers from the geodatabase to create or re-create them
    AddMsgAndPrint("\nRemoving CWD layers from project database...\n",0)
    arcpy.SetProgressorLabel("Removing CWD layers layers from database...")
    datasetsToRemove = [projectCWD,cluCWD]
##    toposToRemove = [cwdTopo]
    wildcard = '*CWD*'
    wkspace = wcGDB_path
    removeFCs(datasetsToRemove, wildcard, wkspace)
    del datasetsToRemove, wildcard, wkspace


    #### Delete Certified-Digital areas from the Sampling Units layer (in case of download of existing SUs in previous steps)
    edit = arcpy.da.Editor(wcGDB_path)
    edit.startEditing()
    with arcpy.da.UpdateCursor(projectSU, "eval_status") as cursor:
        for row in cursor:
            if row[0] == "Certified-Digital":
                cursor.deleteRow()
    edit.stopEditing(save_changes=True)
    del edit
                
    
    #### Create the CWD Layer
    AddMsgAndPrint("\nConverting Sampling Units layer...",0)
    arcpy.SetProgressorLabel("Converting Sampling Units layer...")
    # Create an empty CWD feature class that will eventually be loaded with the finished data
    arcpy.CreateFeatureclass_management(wcFD, cwdName, "POLYGON", templateCWD)

    #Copy the SU layer for processing it into a CWD layer so that it doesn't get edit locked by this tool
    arcpy.CopyFeatures_management(projectSU, suTemp)
    
    #Clip the SU layer copy by the request extent layer (this is done to trim polygons created outside the request extent)
    arcpy.Clip_analysis(suTemp, projectExtent, SU_Clip_Multi)
    arcpy.MultipartToSinglepart_management(SU_Clip_Multi, SU_Clip_Temp)
    arcpy.Delete_management(SU_Clip_Multi)
    
    # Transfer only the New areas of the SU layer towards creating an SU New layer
    arcpy.MakeFeatureLayer_management(SU_Clip_Temp, "extentTemp")
    arcpy.SelectLayerByAttribute_management("extentTemp", "NEW_SELECTION", "\"eval_status\" = 'New Request'")
    arcpy.CopyFeatures_management("extentTemp", SU_Clip_New)
    arcpy.SelectLayerByAttribute_management("extentTemp", "CLEAR_SELECTION")
    arcpy.Delete_management("extentTemp")
    
    # Check if origAdmin exists and process accordingly
    if arcpy.Exists(origAdminTemp):
        AddMsgAndPrint("\tPrevious Certifications on the tract exist. Resolving potential conflicts with Sampling Units...",0)
        arcpy.SetProgressorLabel("Resolving previous CWD with SU...")
        arcpy.Clip_analysis(SU_Clip_Temp, origAdminTemp, Prev_SU_Multi)
        arcpy.MultipartToSinglepart_management(Prev_SU_Multi, Prev_SU_Temp)

        # Check for Revisions in the Prev_SU_Temp layer
        arcpy.MakeFeatureLayer_management(Prev_SU_Temp, "Previous_SU")
        arcpy.SelectLayerByAttribute_management("Previous_SU", "NEW_SELECTION", "\"eval_status\" = 'Revision'")
        count = int(arcpy.GetCount_management("Previous_SU").getOutput(0))
        if count > 0:
            # Revsions found. Integrate them.
            AddMsgAndPrint("\tRevisions found! Using Revisions to update CWD areas...",0)
            arcpy.SetProgressorLabel("Updating CWD areas with revisions...")
            arcpy.CopyFeatures_management("Previous_SU", suRev)
            arcpy.Delete_management("Previous_SU")

            #Use suRev to Erase revised areas from the origCert and origAdmin layers and create updatedCert and updatedAdmin layers
            arcpy.Erase_analysis(origAdminTemp, suRev, updatedAdmin)
            arcpy.Erase_analysis(origCertTemp, suRev, updatedCert)

            # Check to see if any features remain in updatedAdmin
            count = int(arcpy.GetCount_management(updatedAdmin).getOutput(0))
            if count > 0:
                # It is a partial revision to certified areas within the request extent
                AddMsgAndPrint("\tRevisions cover part of previously certified areas. Integrating Revisions to the determination...",0)
                arcpy.SetProgressorLabel("Updating previous CWDs with revisions...")
                
                # Append the suRev to the SU_Clip_New to create the draft CWD layer
                arcpy.Append_management(suRev, SU_Clip_New, "NO_TEST")
                
                # Append the features of the draft CWD layer to the CWD feature class
                arcpy.Append_management(SU_Clip_New, projectCWD, "NO_TEST")

            else:
                # It is a complete revision of the entire certified area within the request extent
                AddMsgAndPrint("\tRevisions replace all Previous CWDs in the request extent. Updating CWD data...",0)
                arcpy.SetProgressorLabel("Revisions replace all Previous CWDs in the request extent. Updating CWD data...")
                
                # Append the suRev to the SU_Clip_New to create the draft CWD layer
                arcpy.Append_management(suRev, SU_Clip_New, "NO_TEST")

                # Append the features of the draft CWD layer to the CWD feature class
                arcpy.Append_management(SU_Clip_New, projectCWD, "NO_TEST")

                # Delete the prevCert layer
                if arcpy.Exists(prevCert):
                    arcpy.Delete_management(prevCert)

        else:
            # There are no revisions. Process normally.
            AddMsgAndPrint("\tRevisions do not exist. Continuing...",0)
            arcpy.SetProgressorLabel("Revisions do not exist. Continuing...")
            arcpy.Delete_management("Previous_SU")

            # Append the results into the empty CWD feature class
            arcpy.Append_management(SU_Clip_New, projectCWD, "NO_TEST")

    else:
        # No previous certified areas exist and it's a new site only
        AddMsgAndPrint("\tNo previously certified areas on the tract. Processing Sampling Units...",0)
        arcpy.SetProgressorLabel("New Requests only. Processing SUs...")
        
        # Convert any "Revision" areas within the SU_Clip_New back to "New_Request"
        fields = ['eval_status']
        cursor = arcpy.da.UpdateCursor(SU_Clip_New, fields)
        for row in cursor:
            if row[0] == "Revision":
                row[0] = "New Request"
            cursor.updateRow(row)
        del cursor, fields
        
        # Append the results into the empty CWD feature class
        arcpy.Append_management(SU_Clip_New, projectCWD, "NO_TEST")


    #### Assign domains to the CWD layer
    AddMsgAndPrint("\nUpdating CWD attribute domains...",0)
    arcpy.SetProgressorLabel("Updating CWD attribute domains...")
    arcpy.AssignDomainToField_management(projectCWD, "eval_status", "Evaluation Status")
    arcpy.AssignDomainToField_management(projectCWD, "wetland_label", "Wetland Labels")
    arcpy.AssignDomainToField_management(projectCWD, "three_factors", "YN")
    arcpy.AssignDomainToField_management(projectCWD, "request_type", "Request Type")
    arcpy.AssignDomainToField_management(projectCWD, "deter_method", "Method")

    # Update the acres of the CWD layer
    expression = "round(!Shape.Area@acres!,2)"
    arcpy.CalculateField_management(projectCWD, "acres", expression, "PYTHON_9.3")
    del expression
    
    
##    #### Update the attributes of the CWD layer
##    # Update the job_id of the CWD layer
    fields = ['job_id']
    cursor = arcpy.da.UpdateCursor(projectCWD, fields)
    for row in cursor:
        row[0] = cur_id
        cursor.updateRow(row)
    del cursor, fields

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

        fields = ['eval_status','request_date','request_type','deter_staff','dig_staff','dig_date','cert_date']
        cursor = arcpy.da.UpdateCursor(projectCWD, fields)
        for row in cursor:
            if row[0] == "New Request" or row[0] == "Revision":
                row[1] = rDate
                row[2] = rType
                row[3] = detStaff
                row[4] = digStaff
                row[5] = digDate
                row[6] = None
            cursor.updateRow(row)
        del cursor, fields


##    #### Import attribute rules
##    arcpy.ImportAttributeRules_management(projectCWD, rules_cwd)
    
## ===============================================================================================================
def createPJW():
    #### Remove existing PJW related layers from the Pro maps
    AddMsgAndPrint("\nRemoving PJW related layers from project maps, if present...\n",0)
    arcpy.SetProgressorLabel("Removing PJW layer from map...")

    # Remove attribute rules first
    if arcpy.Exists(projectPJW):
        try:
            arcpy.DeleteAttributeRule_management(projectPJW, rules_pjw_names)
        except:
            pass
        
    # Set PJW related layers to remove from the map
    mapLayersToRemove = [pjwName]

    # Remove the layers
    removeLayers(mapLayersToRemove)
    del mapLayersToRemove

    # Remove existing PJW layers from the geodatabase
    AddMsgAndPrint("\nRemoving PJW related layers from project database, if present...\n",0)
    arcpy.SetProgressorLabel("Removing PJW layers from database...")
    datasetsToRemove = [projectPJW]
    wildcard = '*PJW*'
    wkspace = wcGDB_path
    removeFCs(datasetsToRemove, wildcard, wkspace)
    del datasetsToRemove, wildcard, wkspace

    if not arcpy.Exists(projectPJW):
        AddMsgAndPrint("\tThe projectPJW layer was deleted or did not exist",0)
        
    #### Create the PJW Layer
    AddMsgAndPrint("\nCreating the PJW layer...\n",0)
    arcpy.SetProgressorLabel("Creating the PJW layer...")
    arcpy.CreateFeatureclass_management(wcFD, pjwName, "POINT", templatePJW)


##    #### Import attribute rules to various layers in the project.
##    arcpy.ImportAttributeRules_management(projectPJW, rules_pjw)

## ===============================================================================================================
#### Import system modules
import arcpy, sys, os, traceback, re, shutil, csv


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
    arcpy.AddMessage("Reading inputs...\n")
    arcpy.SetProgressorLabel("Reading inputs...")
    sourceSU = arcpy.GetParameterAsText(0)
    resetCWD = arcpy.GetParameterAsText(1)
    resetPJW = arcpy.GetParameterAsText(2)
    cwdLyr = arcpy.mp.LayerFile(os.path.join(os.path.dirname(sys.argv[0]), "layer_files") + os.sep + "CWD.lyrx").listLayers()[0]
    pjwLyr = arcpy.mp.LayerFile(os.path.join(os.path.dirname(sys.argv[0]), "layer_files") + os.sep + "PJW.lyrx").listLayers()[0]
    extLyr = arcpy.mp.LayerFile(os.path.join(os.path.dirname(sys.argv[0]), "layer_files") + os.sep + "Extent.lyrx").listLayers()[0]
    suLyr = arcpy.mp.LayerFile(os.path.join(os.path.dirname(sys.argv[0]), "layer_files") + os.sep + "Sampling_Units.lyrx").listLayers()[0]
    ropLyr = arcpy.mp.LayerFile(os.path.join(os.path.dirname(sys.argv[0]), "layer_files") + os.sep + "ROP.lyrx").listLayers()[0]
    refLyr = arcpy.mp.LayerFile(os.path.join(os.path.dirname(sys.argv[0]), "layer_files") + os.sep + "Reference_Points.lyrx").listLayers()[0]
    drainLyr = arcpy.mp.LayerFile(os.path.join(os.path.dirname(sys.argv[0]), "layer_files") + os.sep + "Drainage_Lines.lyrx").listLayers()[0]


    #### Initial Validations
    arcpy.AddMessage("Verifying inputs...\n")
    arcpy.SetProgressorLabel("Verifying Inputs...")
    # If SU layer has features selected, clear the selections so that all features from it are processed.
    clear_lyr = m.listLayers(sourceSU)[0]
    arcpy.SelectLayerByAttribute_management(clear_lyr, "CLEAR_SELECTION")
    del clear_lyr
    
                
    #### Set base path
    sourceSU_path = arcpy.Describe(sourceSU).CatalogPath
    if sourceSU_path.find('.gdb') > 0 and sourceSU_path.find('Determinations') > 0 and sourceSU_path.find('Site_Sampling_Units') > 0:
        wcGDB_path = sourceSU_path[:sourceSU_path.find('.gdb')+4]
    else:
        arcpy.AddError("\nSelected Site Sampling Units layer is not from a Determinations project folder. Exiting...")
        exit()


    #### Define Variables
    arcpy.AddMessage("Setting variables...\n")
    arcpy.SetProgressorLabel("Setting Variables...")
    supportGDB = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb")
    scratchGDB = os.path.join(os.path.dirname(sys.argv[0]), "SCRATCH.gdb")
    templateCWD = supportGDB + os.sep + "master_cwd"
    templatePJW = supportGDB + os.sep + "master_pjw"

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

    cluName = "Site_CLU"
    defineName = "Site_Define_AOI"
    ropName = "Site_ROPs"
    refName = "Site_Reference_Points"
    drainName = "Site_Drainage_Lines"
    cluCwdName = "Site_CLU_CWD"
    cluCWD = wcFD + os.sep + cluCwdName

    projectCLU = basedataFD + os.sep + "Site_CLU"
    projectTract = basedataFD + os.sep + "Site_Tract"
    projectTable = basedataGDB_path + os.sep + "Table_" + projectName
    wetDetTableName = "Admin_Table"
    wetDetTable = wcGDB_path + os.sep + wetDetTableName
    projectAOI = basedataFD + os.sep + "project_AOI"
    projectAOI_B = basedataFD + os.sep + "project_AOI_B"
    projectDAOI = basedataFD + os.sep + "Site_Define_AOI"

    extentName = "Request_Extent"
    projectExtent = basedataFD + os.sep + extentName
    extentTemp1 = scratchGDB + os.sep + "Extent_Temp_1"
    extentTemp2 = scratchGDB + os.sep + "Extent_Temp_2"
    
    suName = "Site_Sampling_Units"
    projectSU = wcFD + os.sep + suName
    suTemp = scratchGDB + os.sep + "suTemp"
    SU_Clip_Multi = scratchGDB + os.sep + "suClipMulti"
    SU_Clip_Temp = scratchGDB + os.sep + "suClipTemp"
    SU_Clip_New = scratchGDB + os.sep + "suClipNew"
    Prev_SU_Multi = scratchGDB + os.sep + "prevSuMulti"
    Prev_SU_Temp = scratchGDB + os.sep + "prevSuTemp"
    suRev = scratchGDB + os.sep + "suRevised"
    suRevDissolve = scratchGDB + os.sep + "suRevDis"
    
    cwdName = "Site_CWD"
    projectCWD = wcFD + os.sep + cwdName

    pjwName = "Site_PJW"
    projectPJW = wcFD + os.sep + pjwName

##    cwdTopoName = "CWD_Topology"
##    cwdTopo = wcFD + os.sep + cwdTopoName

    origCert = wcFD + os.sep + "Previous_CLU_CWD_Original"
    origCertTemp = scratchGDB + os.sep + "Prev_Orig_Cert_Temp"
    origAdmin = wcFD + os.sep + "Previous_CLU_CWD_Admin_Original"
    origAdminTemp = scratchGDB + os.sep + "Prev_Orig_Admin_Temp"
    
    prevCertName = "Site_Previous_CLU_CWD"
    prevCert = wcFD + os.sep + prevCertName
    prevAdmin = wcFD + os.sep + "Previous_Admin"
    
    updatedCert = scratchGDB + os.sep + "Updated_Cert"
    updatedAdmin = scratchGDB + os.sep + "Updated_Admin"
    
    # Attribute rule files
    rules_cwd = os.path.join(os.path.dirname(sys.argv[0]), "Rules_CWD.csv")
    rules_cwd_names = ['Update Acres']
    rules_pjw = os.path.join(os.path.dirname(sys.argv[0]), "Rules_PJW.csv")
    rules_pjw_names = ['Add PJW Job ID']

    # Temp layers list for cleanup at the start and at the end
    tempLayers = [extentTemp1, extentTemp2, suTemp, SU_Clip_Multi, SU_Clip_Temp, SU_Clip_New, Prev_SU_Multi, Prev_SU_Temp, suRev, suRevDissolve, origCertTemp, origAdminTemp]
    deleteTempLayers(tempLayers)


    #### Set up log file path and start logging
    arcpy.AddMessage("Commence logging...\n")
    arcpy.SetProgressorLabel("Commence logging...")
    textFilePath = userWorkspace + os.sep + projectName + "_log.txt"
    logBasicSettings()


    #### Check the input SU layer to see if it has any New Request or Revised areas. If not, give error message(s) and exit.
    fields = ['eval_status']
    field1 = 'eval_status'
    expression = "{} = '{}'".format(arcpy.AddFieldDelimiters(projectSU,field1), 'New Request') + " OR " + "{} = '{}'".format(arcpy.AddFieldDelimiters(projectSU,field1), 'Revision')
    cursor = [row for row in arcpy.da.SearchCursor(projectSU, fields, where_clause = expression)]
    if len(cursor) == 0:
        AddMsgAndPrint("\nNo Sampling Units are marked for New Request or Revision.",2)
        if arcpy.Exists(origAdmin):
            AddMsgAndPrint("\nPrevious Certifications Exist. Skip to the Create CWD Mapping Layers tool.",2)
        AddMsgAndPrint("\nExiting...")
        exit()
    del fields, field1, expression
    del cursor
    

    #### Get the current job_id for use in processing

    # Copy the administrative table into the wetlands database for use with the attribute rules during digitizing
    if not arcpy.Exists(wetDetTable):
        arcpy.TableToTable_conversion(projectTable, wcGDB_path, wetDetTableName)
        
    fields = ['job_id']
    cursor = arcpy.da.SearchCursor(wetDetTable, fields)
    for row in cursor:
        cur_id = row[0]
        break
    del cursor, fields


    #### Create temp working copies of origAdmin and origCert if they exist to reduce chances of file locks
    if arcpy.Exists(origAdmin):
        arcpy.CopyFeatures_management(origAdmin, origAdminTemp)
    if arcpy.Exists(origCert):
        arcpy.CopyFeatures_management(origCert, origCertTemp)
    
    
    #### Create or Reset the CWD layer
    if not arcpy.Exists(projectCWD):
        AddMsgAndPrint("\nCreating CWD layer...\n",0)
        arcpy.SetProgressorLabel("Creating CWD layer...")
        createCWD()
        AddMsgAndPrint("\nImporting Attribute Rules to the CWD layer...\n",0)
        arcpy.SetProgressorLabel("Importing Attribute Rules to the CWD layer...")
        arcpy.ImportAttributeRules_management(projectCWD, rules_cwd)
    if resetCWD == "Yes":
        AddMsgAndPrint("\nCreating CWD layer...\n",0)
        arcpy.SetProgressorLabel("Creating CWD layer...")
        createCWD()
        AddMsgAndPrint("\nImporting Attribute Rules to the CWD layer...\n",0)
        arcpy.SetProgressorLabel("Importing Attribute Rules to the CWD layer...")
        arcpy.ImportAttributeRules_management(projectCWD, rules_cwd)


    #### Create or Reset the PJW Layer
    if not arcpy.Exists(projectPJW):
        AddMsgAndPrint("\nCreating PJW layer...\n",0)
        arcpy.SetProgressorLabel("Creating PJW layer...")
        createPJW()
        AddMsgAndPrint("\nImporting Attribute Rules to the PJW layer...\n",0)
        arcpy.SetProgressorLabel("Importing Attribute Rules to the PJW layer...")
        arcpy.ImportAttributeRules_management(projectPJW, rules_pjw)
    if resetPJW == "Yes":
        AddMsgAndPrint("\nCreating PJW layer...\n",0)
        arcpy.SetProgressorLabel("Creating PJW layer...")
        createPJW()
        AddMsgAndPrint("\nImporting Attribute Rules to the PJW layer...\n",0)
        arcpy.SetProgressorLabel("Importing Attribute Rules to the PJW layer...")
        arcpy.ImportAttributeRules_management(projectPJW, rules_pjw)


    #### Update or reset the prevCert layer
    if arcpy.Exists(origAdmin):
        # Previous certifications existed before project. Continue...
        if arcpy.Exists(prevCert):
            # prevCert still exists (not a full revision). Continue...
            if arcpy.Exists(updatedCert):
                # Revisions exist. The updatedCert layer can be made into the prevCert layer
                arcpy.CopyFeatures_management(updatedCert, prevCert)
            else:
                # Revisions do not exist. Reset the prevCert layer with the origAdmin
                arcpy.CopyFeatures_management(origCert, prevCert)


    #### Update the acres of the prevCert layer if it exists
    if arcpy.Exists(prevCert):
        expression = "round(!Shape.Area@acres!,2)"
        arcpy.CalculateField_management(prevCert, "acres", expression, "PYTHON_9.3")
        del expression


    #### Delete updatedCert and updatedAdmin if they exist
    updateLayers = [updatedCert, updatedAdmin]
    for lyr in updateLayers:
        if arcpy.Exists(lyr):
            try:
                arcpy.Delete_management(lyr)
            except:
                pass
            

    #### Clean up Temporary Datasets
    # Temporary datasets specifically from this tool
    AddMsgAndPrint("\nCleaning up temporary data...",0)
    arcpy.SetProgressorLabel("Cleaning up temp data...")
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

    # Rasters
    rasters = []
    for ras in arcpy.ListRasters('*'):
        rasters.append(os.path.join(scratchGDB, ras))
    for ras in rasters:
        if arcpy.Exists(ras):
            try:
                arcpy.Delete_management(ras)
            except:
                pass

    # Tables
    tables = []
    for tbl in arcpy.ListTables('*'):
        tables.append(os.path.join(scratchGDB, tbl))
    for tbl in tables:
        if arcpy.Exists(tbl):
            try:
                arcpy.Delete_management(tbl)
            except:
                pass
    
    arcpy.env.workspace = startWorkspace
    del startWorkspace


    #### Add to map
    # Use starting reference layer files from the tool installation to add layers with automatic placement
    AddMsgAndPrint("\nAdding layers to the map...",0)
    arcpy.SetProgressorLabel("Adding layers to map...")

    lyr_list = m.listLayers()
    lyr_name_list = []
    for lyr in lyr_list:
        lyr_name_list.append(lyr.longName)

    if pjwName not in lyr_name_list:
        pjwLyr_cp = pjwLyr.connectionProperties
        pjwLyr_cp['connection_info']['database'] = wcGDB_path
        pjwLyr_cp['dataset'] = pjwName
        pjwLyr.updateConnectionProperties(pjwLyr.connectionProperties, pjwLyr_cp)
        m.addLayer(pjwLyr)
        
    if ropName not in lyr_name_list:
        ropLyr_cp = ropLyr.connectionProperties
        ropLyr_cp['connection_info']['database'] = wcGDB_path
        ropLyr_cp['dataset'] = ropName
        ropLyr.updateConnectionProperties(ropLyr.connectionProperties, ropLyr_cp)
        m.addLayer(ropLyr)

    if refName not in lyr_name_list:
        refLyr_cp = ropLyr.connectionProperties
        refLyr_cp['connection_info']['database'] = wcGDB_path
        refLyr_cp['dataset'] = refName
        refLyr.updateConnectionProperties(refLyr.connectionProperties, refLyr_cp)
        m.addLayer(refLyr)

    if drainName not in lyr_name_list:
        drainLyr_cp = ropLyr.connectionProperties
        drainLyr_cp['connection_info']['database'] = wcGDB_path
        drainLyr_cp['dataset'] = drainName
        drainLyr.updateConnectionProperties(drainLyr.connectionProperties, drainLyr_cp)
        m.addLayer(drainLyr)
        
    if cwdName not in lyr_name_list:
        cwdLyr_cp = cwdLyr.connectionProperties
        cwdLyr_cp['connection_info']['database'] = wcGDB_path
        cwdLyr_cp['dataset'] = cwdName
        cwdLyr.updateConnectionProperties(cwdLyr.connectionProperties, cwdLyr_cp)
        m.addLayer(cwdLyr)

    if suName not in lyr_name_list:
        suLyr_cp = suLyr.connectionProperties
        suLyr_cp['connection_info']['database'] = wcGDB_path
        suLyr_cp['dataset'] = suName
        suLyr.updateConnectionProperties(suLyr.connectionProperties, suLyr_cp)
        m.addLayer(suLyr)
        
    if extentName not in lyr_name_list:
        extLyr_cp = extLyr.connectionProperties
        extLyr_cp['connection_info']['database'] = basedataGDB_path
        extLyr_cp['dataset'] = extentName
        extLyr.updateConnectionProperties(extLyr.connectionProperties, extLyr_cp)
        m.addLayer(extLyr)

    if arcpy.Exists(prevCert):
        arcpy.SetParameterAsText(3, prevCert)
    
    #### Adjust visibility of layers to aid in moving to the next step in the process
    # Turn off all layers from previous steps
    off_names = [cluName, defineName, extentName, suName, ropName, refName, drainName, cluCwdName]
    for maps in aprx.listMaps():
        for lyr in maps.listLayers():
            for name in off_names:
                if name in lyr.longName:
                    lyr.visible = False

    # Turn on layers for current steps
    on_names = [cwdName, pjwName]
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
