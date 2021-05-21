## ===============================================================================================================
## Name:    Validate CWD
## Purpose: Check for topology overlaps and other attribute errors in the CWD layer.
##
## Authors: Chris Morse
##          GIS Specialist
##          Indianapolis State Office
##          USDA-NRCS
##          chris.morse@usda.gov
##          317.295.5849
##
## Created: 04/02/2021
##
## ===============================================================================================================
## Changes
## ===============================================================================================================
##
## rev. 11/04/2020
## -Start revisions of Validate Topology ArcMap tool to National Wetlands Tool in ArcGIS Pro.
##
## rev. 04/02/2021
## -Combined the Topology validation and the Attribute validation tools.
## -Gaps validation removed
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
    f.write("Executing Validate CWD tool...\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("User Parameters:\n")
    f.write("\tCWD Layer: " + sourceCWD + "\n")
    f.close
    del f

## ===============================================================================================================
#### Import system modules
import arcpy, sys, os, traceback, re, shutil, csv


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
    

#### Main procedures
try:
    #### Inputs
    arcpy.AddMessage("Reading inputs...\n")
    sourceCWD = arcpy.GetParameterAsText(0)
    #cwdLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(1))
    #cwdLyr = os.path.join(os.path.dirname(sys.argv[0]), "layer_files" + os.sep + "CWD.lyrx")


    #### Initial Validations
    arcpy.AddMessage("Verifying inputs...\n")
    # If CWD or PJW layers have features selected, clear the selections so that all features from it are processed.
    try:
        clear_lyr1 = m.listLayers(sourceCWD)[0]
        clear_lyr2 = m.listLayers("Site_PJW")[0]
        arcpy.SelectLayerByAttribute_management(clear_lyr1, "CLEAR_SELECTION")
        arcpy.SelectLayerByAttribute_management(clear_lyr2, "CLEAR_SELECTION")
    except:
        pass


    #### Set base path
    sourceCWD_path = arcpy.Describe(sourceCWD).CatalogPath
    if sourceCWD_path.find('.gdb') > 0 and sourceCWD_path.find('Determinations') > 0 and sourceCWD_path.find('Site_CWD') > 0:
        wcGDB_path = sourceCWD_path[:sourceCWD_path.find('.gdb')+4]
    else:
        arcpy.AddError("\nSelected CWD layer is not from a Determinations project folder. Exiting...")
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
    supportGDB = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb")
    scratchGDB = os.path.join(os.path.dirname(sys.argv[0]), "SCRATCH.gdb")

    wetDir = os.path.dirname(wcGDB_path)
    wcFD = wcGDB_path + os.sep + "WC_Data"
    userWorkspace = os.path.dirname(wetDir)
    projectName = os.path.basename(userWorkspace).replace(" ", "_")
    basedataGDB_path = userWorkspace + os.sep + projectName + "_BaseData.gdb"
    basedataFD_name = "Layers"
    basedataFD = basedataGDB_path + os.sep + basedataFD_name

    projectTract = basedataFD + os.sep + "Site_Tract"
    projectTable = basedataGDB_path + os.sep + "Table_" + projectName

    suName = "Site_Sampling_Units"
    projectSU = wcFD + os.sep + suName
    
    cwdName = "Site_CWD"
    projectCWD = wcFD + os.sep + cwdName
    cwdBackup = wcFD + os.sep + "CWD_Backup"
    cwdTopoName = "CWD_Topology"
    cwdTopo = wcFD + os.sep + cwdTopoName
    linesTopoFC = wcFD + os.sep + "CWD_Errors_line"
    pointsTopoFC = wcFD + os.sep + "CWD_Errors_point"
    polysTopoFC = wcFD + os.sep + "CWD_Errors_poly"

    domain_base = supportGDB
    eval_domain = domain_base + os.sep + "domain_evaluation_status"
    wetland_domain = domain_base + os.sep + "domain_wetland_labels"
    yn_domain = domain_base + os.sep + "domain_yn"
    request_domain = domain_base + os.sep + "domain_request_type"
    method_domain = domain_base + os.sep + "domain_method"
    

    #### Set up log file path and start logging
    arcpy.AddMessage("Commence logging...\n")
    textFilePath = userWorkspace + os.sep + projectName + "_log.txt"
    logBasicSettings()


    #### If project wetlands feature dataset does not exist, exit.
    if not arcpy.Exists(wcFD):
        AddMsgAndPrint("\tInput Site_CWD layer does not come from an expected project feature dataset.",2)
        AddMsgAndPrint("\tPlease re-run and select a valid Site_CWD layer. Exiting...",2)
        exit()

        
    #### Remove the topology from the Pro maps, if present
    AddMsgAndPrint("\nRemoving topology from project maps, if present...",0)
    
    # Set starting layers to be removed
    mapLayersToRemove = [cwdTopoName]
    
    # Remove the layers in the list
    try:
        for maps in aprx.listMaps():
            for lyr in maps.listLayers():
                if lyr.name in mapLayersToRemove:
                    maps.removeLayer(lyr)
    except:
        pass


    #### Remove existing CWD topology related layers from the geodatabase
    AddMsgAndPrint("\nRemoving topology from project database, if present...",0)

    # Remove topology first, if it exists
    toposToRemove = [cwdTopo]
    for topo in toposToRemove:
        if arcpy.Exists(topo):
            try:
                arcpy.Delete_management(topo)
            except:
                pass


    #### Backup the input CWD layer
    AddMsgAndPrint("\nCreating backup of the CWD layer...",0)

    if arcpy.Exists(cwdBackup):
        arcpy.Delete_management(cwdBackup)
    arcpy.CopyFeatures_management(projectCWD, cwdBackup)


    #### Topology review 1 (check for overlaps within the SU layer)
    AddMsgAndPrint("\nChecking for overlaps within the CWD layer...",0)

    # Create and validate the topology for Must Not Overlap
    cluster = 0.001
    arcpy.CreateTopology_management(wcFD, cwdTopoName, cluster)
    arcpy.AddFeatureClassToTopology_management(cwdTopo, projectCWD, 1, 1)
    arcpy.AddRuleToTopology_management(cwdTopo, "Must Not Overlap (Area)", projectCWD)
    arcpy.ValidateTopology_management(cwdTopo)

    # Export the errors and check for results
    arcpy.ExportTopologyErrors_management(cwdTopo, wcFD, "CWD_Errors")
    arcpy.Delete_management(linesTopoFC)
    arcpy.Delete_management(pointsTopoFC)
    result = int(arcpy.GetCount_management(polysTopoFC).getOutput(0))
    if result > 0:
        AddMsgAndPrint("\tOverlaps found! Generating error layer for the map...",2)
        arcpy.Delete_management(polysTopoFC)
        arcpy.SetParameterAsText(1, cwdTopo)
        #re_add_layers()
    
        AddMsgAndPrint("\tPlease review and correct overlaps and then re-run this tool. Exiting...",2)
        exit()
    else:
        AddMsgAndPrint("\tNo overlaps found! Continuing...",0)
        arcpy.Delete_management(polysTopoFC)


    #### Refresh administrative info for the request on the CWD layer
    AddMsgAndPrint("\nValidating request information...",0)
    # Get admin attributes from project table for request_date, request_type, deter_staff, dig_staff, and dig_date (current date)
    fields = ['admin_state','admin_state_name','admin_county','admin_county_name','state_code','state_name','county_code','county_name','farm_number','tract_number','request_date','request_type','job_id']
    cursor = arcpy.da.SearchCursor(projectTable, fields)
    for row in cursor:
        adState = row[0]
        adStateName = row[1]
        adCounty = row[2]
        adCountyName = row[3]
        stateCode = row[4]
        stateName = row[5]
        countyCode = row[6]
        countyName = row[7]
        farmNum = row[8]
        tractNum = row[9]
        rDate = row[10]
        rType = row[11]
        job_id = row[12]
        #break
    del cursor, fields

    digStaff = str(os.getenv('username').replace("."," ")).title()
    digDate = time.strftime('%m/%d/%Y')
    
    expression = "!Shape.Area@acres!"
    arcpy.CalculateField_management(projectCWD, "acres", expression, "PYTHON_9.3")
    del expression

    # Update the CWD layer, using an edit session. Only update the New Request and Revision features.
    workspace = wcGDB_path
    edit = arcpy.da.Editor(workspace)
    edit.startEditing(False, False)

    fields = ['eval_status','admin_state','admin_state_name','admin_county','admin_county_name','state_code','state_name','county_code','county_name','farm_number','tract_number','request_date','request_type','dig_staff','dig_date','job_id']
    cursor = arcpy.da.UpdateCursor(projectCWD, fields)
    for row in cursor:
        if row[0] == "New Request" or row[0] == "Revision":
            row[1] = adState
            row[2] = adStateName
            row[3] = adCounty
            row[4] = adCountyName
            row[5] = stateCode
            row[6] = stateName
            row[7] = countyCode
            row[8] = countyName
            row[9] = farmNum
            row[10] = tractNum
            row[11] = rDate
            row[12] = rType
            row[13] = digStaff
            row[14] = digDate
            row[15] = job_id
        cursor.updateRow(row)
    del cursor, fields

    edit.stopEditing(True)
    del workspace, edit


    #### Start attribute checks
    AddMsgAndPrint("\nValidating request information...",0)

    ### CWD Layer
    ## Evaluation Status
    # No null eval_status
    AddMsgAndPrint("\tChecking Evaluation Status...\n",0)
    checklist = []
    fields = ['eval_status']
    whereClause = "\"eval_status\" IS NULL"
    with arcpy.da.SearchCursor(projectCWD, fields, whereClause) as cursor:
        for row in cursor:
            checklist.append(row[0])
    if len(checklist) > 0:
        AddMsgAndPrint("\tAt least one CWD polygon does not have an Evaluation Status set. Please correct and re-run. Exiting...\n",2)
        exit()

    # Eval_Status values must come from the Evaluation Status domain
    eval_list = []
    cursor = arcpy.da.SearchCursor(projectCWD, "eval_status")
    for row in cursor:
        if row[0] not in eval_list:
            eval_list.append(row[0])
    del cursor
    ev_list = []
    cursor = arcpy.da.SearchCursor(eval_domain, "Code")
    for row in cursor:
        if row[0] not in ev_list:
            ev_list.append(row[0])
    del cursor
    for item in eval_list:
        if item not in ev_list:
            AddMsgAndPrint("\n" + item + " is not a valid choice for Evaluation Status in the CWD layer. Please correct and re-run. Exiting...\n",2)
            exit()
    del ev_list, eval_list

    ## Wetland Label
    # No null wetland labels
    AddMsgAndPrint("\tChecking Wetland Labels...\n",0)
    checklist = []
    fields = ['wetland_label']
    whereClause = "\"wetland_label\" IS NULL"
    with arcpy.da.SearchCursor(projectCWD, fields, whereClause) as cursor:
        for row in cursor:
            checklist.append(row[0])
    if len(checklist) > 0:
        AddMsgAndPrint("\tAt least one CWD polygon does not have a Wetland Label assigned. Please correct and re-run. Exiting...\n",2)
        exit()

    # Wetland Label values must come from the Wetland Labels domain
    wetland_list = []
    cursor = arcpy.da.SearchCursor(projectCWD, "wetland_label")
    for row in cursor:
        if row[0] not in wetland_list:
            wetland_list.append(row[0])
    del cursor
    wl_list = []
    cursor = arcpy.da.SearchCursor(wetland_domain, "Code")
    for row in cursor:
        if row[0] not in wl_list:
            wl_list.append(row[0])
    del cursor
    for item in wetland_list:
        if item not in wl_list:
            AddMsgAndPrint("\n" + item + " is not a valid choice for a Wetland Label in the CWD layer. Please correct and re-run. Exiting...\n",2)
            exit()
    del wl_list, wetland_list

    # No null values for occurrence year in cases where CW+ has been assigned
    checklist = []
    fields = ['wetland_label','occur_year']
    whereClause = "wetland_label = 'CW+' AND occur_year IS NULL"
    with arcpy.da.SearchCursor(projectCWD, fields, whereClause) as cursor:
        for row in cursor:
            checklist.append(row[0])
    if len(checklist) > 0:
        AddMsgAndPrint("\tAt least one CWD polygon labeld with CW+ does not have the Occurrence Year assigned. Please correct and re-run. Exiting...\n",2)
        exit()
    del checklist, fields, whereClause

    # No improper text values stored in occurrence year
    fields = ['wetland_label','occur_year']
    whereClause = "wetland_label = 'CW+'"
    with arcpy.da.SearchCursor(projectCWD, fields, whereClause) as cursor:
        for row in cursor:
            try:
                int(row[1])
            except:
               AddMsgAndPrint("\nThe Occurrence Year for one or more CW+ polygons in the Site_CWD layer may contain text instead of numbers. Please correct and re-run. Exiting...\n",2)
               exit()

    # Proper date range for occurrence year
    checklist = []
    fields = ['wetland_label','occur_year']
    curyear = datetime.datetime.now().year
    whereClause = "wetland_label = 'CW+' AND (CAST(occur_year AS INT) <= 1990 or CAST(occur_year AS INT) > " + str(curyear) + ")"
    with arcpy.da.SearchCursor(projectCWD, fields, whereClause) as cursor:
        for row in cursor:
            checklist.append(row[0])
    if len(checklist) > 0:
        AddMsgAndPrint("\tOne or more CW+ polygons in the Site_CWD layer has the Occurrence Year set prior to 1990 or after the current year. Exiting...\n",2)
        exit()
    del checklist, fields, whereClause, curyear
    

    ## 3-Factors
    # No null values
    AddMsgAndPrint("\tChecking CWD 3-Factors...\n",0)
    checklist = []
    fields = ['three_factors']
    whereClause = "\"three_factors\" = 'U'"
    with arcpy.da.SearchCursor(projectCWD, fields, whereClause) as cursor:
        for row in cursor:
            checklist.append(row[0])
    if len(checklist) > 0:
        AddMsgAndPrint("\tAt least one Site_CWD layer polygon does not have Y or N assigned for 3-Factors. Please correct and re-run. Exiting...\n",2)
        exit()
        
    # Values must come from the YN domain
    yn_list = []
    cursor = arcpy.da.SearchCursor(projectCWD, "three_factors")
    for row in cursor:
        if row[0] not in yn_list:
            yn_list.append(row[0])
    del cursor
    ynd_list = []
    cursor = arcpy.da.SearchCursor(yn_domain, "Code")
    for row in cursor:
        if row[0] not in ynd_list:
            ynd_list.append(row[0])
    del cursor
    for item in yn_list:
        if item not in ynd_list:
            AddMsgAndPrint("\n" + item + " is not a valid choice for 3-Factors in the Site_CWD layer. Please correct and re-run. Exiting...\n",2)
            exit()
    del ynd_list, yn_list

    # No values of U from the YN domain
    u_list = []
    fields = ['three_factors']
    whereClause = "\"three_factors\" = 'U'"
    with arcpy.da.SearchCursor(projectCWD, fields, whereClause) as cursor:
        for row in cursor:
            u_list.append(row[0])
    if len(u_list) > 0:
        AddMsgAndPrint("\tAt least one Site_CWD layer polygon has a choice for 3-Factors listed as U. Please correct to Y or N and re-run. Exiting...\n",2)
        exit()
    del u_list
    
        
    ## Determination Method
    # No Null values
    AddMsgAndPrint("\tChecking Determination Method...\n",0)
    checklist = []
    fields = ['deter_method']
    whereClause = "\"deter_method\" IS NULL"
    with arcpy.da.SearchCursor(projectCWD, fields, whereClause) as cursor:
        for row in cursor:
            checklist.append(row[0])
    if len(checklist) > 0:
        AddMsgAndPrint("\tAt least one Site_CWD layer polygon does not have a Determination Method set. Please correct and re-run. Exiting...\n",2)
        exit()

    # Values must come from the Method domain
    method_list = []
    cursor = arcpy.da.SearchCursor(projectCWD, "deter_method")
    for row in cursor:
        if row[0] not in method_list:
            method_list.append(row[0])
    del cursor
    md_list = []
    cursor = arcpy.da.SearchCursor(method_domain, "Code")
    for row in cursor:
        if row[0] not in md_list:
            md_list.append(row[0])
    del cursor
    for item in method_list:
        if item not in md_list:
            AddMsgAndPrint("\n" + item + " is not a valid choice for Determination Method in the Site_CWD layer. Please correct and re-run. Exiting...\n",2)
            exit()
    del md_list, method_list

    ## Determination Staff
    # Make sure determination staff is not null
    AddMsgAndPrint("\tChecking Determination Staff...\n",0)
    checklist = []
    fields = ['deter_staff']
    whereClause = "\"deter_staff\" IS NULL"
    with arcpy.da.SearchCursor(projectCWD, fields, whereClause) as cursor:
        for row in cursor:
            checklist.append(row[0])
    if len(checklist) > 0:
        AddMsgAndPrint("\tAt least one Site_CWD layer polygon does not list a Determination Staff person. Please correct and re-run. Exiting...\n",2)
        exit()

    
    #### Success
    AddMsgAndPrint("\nAll checks passed!\n",0)

    
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
