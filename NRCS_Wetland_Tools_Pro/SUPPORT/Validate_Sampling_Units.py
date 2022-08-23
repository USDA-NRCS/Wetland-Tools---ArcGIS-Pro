## ===============================================================================================================
## Name:    Validate Sampling Units
## Purpose: Check for attribute errors in the Sampling Units layer.
##          Topology check dropped due to uncertainty of the integrity of the CLU at a national level
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
## - Start revisions of Validate Topology ArcMap tool to National Wetlands Tool in ArcGIS Pro.
##
## rev. 11/18/2020
## - Check for internal gaps will have to be handled differently because SUs can go beyond extent/tract edges
##      - Use the outer edge of the extent layer itself in place of the tract layer.
##
## rev. 03/05/2021
## - Removed request extent updates and certified area enforcement because if Sampling Units are combined
##   internally, or extented outside of the request extent and/or tract then cutting in Certified-Digital or
##   Revision extents could artificially split a contiguous sampling unit.
## - Request Extent and Certified/Revision areas will be moved to and enforced in the Create CWD Data tool.
## - Removed topology check for gaps steps due to SU's being allowed to extend outside of Request Extent/Tract.
## - Removed the steps to check that ROPs are inside the Sampling Units (now enforced with an attribute rule).
## - Added Sampling Unit attribute validations to this tool, and renamed this tool to Validate Sampling Units.
##
## rev. 05/11/2021
## - Added a check for multiple ROPs within a single sampling unit.
##
## rev. 07/23/2021
## - Blocked out topology checks due to uncertainty of the integrity of the CLU at a national level
##
## rev. 09/09/2021
## - Slight modifications to test edit objects interfering with output schema locks. Confirmed that editing is
##   required during script runtime to allow attribute rules that use the "Update" option to function properly.
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
    f.write("Executing Validate Sampling Units tool...\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("User Parameters:\n")
    f.write("\tSampling Unit Layer: " + sourceSU + "\n")
    f.close
    del f

#### ===============================================================================================================
##def deleteRules(projectFC, rule_names):
##    # Removes a feature class's rules and imports them again
##
##    #### Remove rules
##    if arcpy.Exists(projectFC):
##        try:
##            arcpy.DeleteAttributeRule_management(projectFC, rule_names)
##            return True
##        except:
##            arcpy.AddWarning("Layer may already have no rules or there was a problem deleting the rules. Continuing...")
##            return False

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
    #suLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(1))
    #suLyr = os.path.join(os.path.dirname(sys.argv[0]), "layer_files" + os.sep + "Sampling_Units.lyrx")
    #extentLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(3))


    #### Initial Validations
    arcpy.AddMessage("Verifying inputs...\n")
    arcpy.SetProgressorLabel("Verifying inputs...")
    # If Sampling Units or ROPs layers have features selected, clear the selections so that all features from it are processed.
    try:
        clear_lyr1 = m.listLayers(sourceSU)[0]
        clear_lyr2 = m.listLayers("Site_ROPs")[0]
        arcpy.SelectLayerByAttribute_management(clear_lyr1, "CLEAR_SELECTION")
        arcpy.SelectLayerByAttribute_management(clear_lyr2, "CLEAR_SELECTION")
    except:
        pass
    

    #### Set base path
    sourceSU_path = arcpy.Describe(sourceSU).CatalogPath
    if sourceSU_path.find('.gdb') > 0 and sourceSU_path.find('Determinations') > 0 and sourceSU_path.find('Site_Sampling_Units') > 0:
        wcGDB_path = sourceSU_path[:sourceSU_path.find('.gdb')+4]
    else:
        arcpy.AddError("\nSelected Samplint Units layer is not from a Determinations project folder. Exiting...")
        exit()

##    #### Do not run if any unsaved edits exist in the target workspace
##    # Pro opens an edit session when any edit has been made and stays open until edits are committed with Save Edits.
##    # Check for uncommitted edits and exit if found, giving the user a message directing them to Save or Discard them.
##    workspace = wcGDB_path
##    edit = arcpy.da.Editor(workspace)
##    if edit.isEditing:
##        arcpy.AddError("\nThere are unsaved data edits in this project. Please Save or Discard Edits and then run this tool again. Exiting...")
##        exit()
##    del workspace, edit


    #### Define Variables
    arcpy.AddMessage("Setting variables...\n")
    arcpy.SetProgressorLabel("Setting variables...")
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
    suBackup = wcFD + os.sep + "SU_Backup"
    suTopoName = "Sampling_Units_Topology"
    suTopo = wcFD + os.sep + suTopoName
    linesTopoFC = wcFD + os.sep + "SU_Errors_line"
    pointsTopoFC = wcFD + os.sep + "SU_Errors_point"
    polysTopoFC = wcFD + os.sep + "SU_Errors_poly"
    
    ropName = "Site_ROPs"
    projectROP = wcFD + os.sep + ropName

    ropCount = scratchGDB + os.sep + "ropCount"

    domain_base = supportGDB
    method_domain = domain_base + os.sep + "domain_method"
    eval_domain = domain_base + os.sep + "domain_evaluation_status"
    yn_domain = domain_base + os.sep + "domain_yn"
    yesno_domain = domain_base + os.sep + "domain_yesno"

##    # Possible Rules Files
##    rules_su = os.path.join(os.path.dirname(sys.argv[0]), "Rules_SU.csv")
##    rules_rops = os.path.join(os.path.dirname(sys.argv[0]), "Rules_ROPs.csv")
##    
##    # Possible Rules Names
##    rules_su_names = ['Update Acres', 'Add SU Job ID', 'Add SU Admin State', 'Add SU Admin State Name',
##                      'Add SU Admin County', 'Add SU Admin County Name', 'Add SU State Code', 'Add SU State Name',
##                      'Add SU County Code', 'Add SU County Name', 'Add SU Farm Number', 'Add SU Tract Number',
##                      'Add Request Date', 'Add Request Type', 'Add Eval Status']
##
##    rules_rop_names = ['Add ROP Admin State Code', 'Add ROP Admin State Name', 'Add ROP Admin County Code',
##                       'Add ROP Admin County Name', 'Add ROP Job ID', 'Add ROP State Code', 'Add ROP State Name',
##                       'Add ROP County Code', 'Add ROP County Name', 'Add ROP Farm Number', 'Add ROP Tract Number']

    
    #### Set up log file path and start logging
    arcpy.AddMessage("Commence logging...\n")
    arcpy.SetProgressorLabel("Commence logging...")
    textFilePath = userWorkspace + os.sep + projectName + "_log.txt"
    logBasicSettings()


    #### If project wetlands feature dataset does not exist, exit.
    if not arcpy.Exists(wcFD):
        AddMsgAndPrint("\tInput Site Sampling Units layer does not come from an expected project feature dataset.",2)
        AddMsgAndPrint("\tPlease re-run and select a valid Site Samping Units layer. Exiting...",2)
        exit()

    
    #### At least one ROP record must exist
    AddMsgAndPrint("\nVerifying project integrity...",0)
    arcpy.SetProgressorLabel("Verifing project integrity...")
    result = int(arcpy.GetCount_management(projectROP).getOutput(0))
    if result < 1:
        AddMsgAndPrint("\tAt least one ROP must exist in the Site ROPs layer!",2)
        AddMsgAndPrint("\tPlease digitize ROPs and then try again. Exiting...",2)
        exit()
            
        
##    #### Remove the topology from the Pro maps, if present
##    AddMsgAndPrint("\nRemoving topology from project maps, if present...",0)
##    
##    # Set starting layers to be removed
##    mapLayersToRemove = [suTopoName]
##    
##    # Remove the layers in the list
##    try:
##        for maps in aprx.listMaps():
##            for lyr in maps.listLayers():
##                if lyr.name in mapLayersToRemove:
##                    maps.removeLayer(lyr)
##    except:
##        pass
##
##
##    #### Remove existing sampling unit topology related layers from the geodatabase
##    AddMsgAndPrint("\nRemoving topology from project database, if present...",0)
##
##    # Remove topology first, if it exists
##    toposToRemove = [suTopo]
##    for topo in toposToRemove:
##        if arcpy.Exists(topo):
##            try:
##                arcpy.Delete_management(topo)
##            except:
##                pass


    #### Backup the input Sampling Units layer
    AddMsgAndPrint("\nBacking up the Sampling Units...",0)
    arcpy.SetProgressorLabel("Backing up SU data...")

    if arcpy.Exists(suBackup):
        arcpy.Delete_management(suBackup)
    arcpy.CopyFeatures_management(projectSU, suBackup)


##    #### Topology review 1 (check for overlaps within the SU layer)
##    AddMsgAndPrint("\nChecking for overlaps within the Sampling Units layer...",0)
##
##    # Create and validate the topology for Must Not Overlap
##    cluster = 0.001
##    arcpy.CreateTopology_management(wcFD, suTopoName, cluster)
##    arcpy.AddFeatureClassToTopology_management(suTopo, projectSU, 1, 1)
##    arcpy.AddRuleToTopology_management(suTopo, "Must Not Overlap (Area)", projectSU)
##    arcpy.ValidateTopology_management(suTopo)
##
##    # Export the errors and check for results
##    arcpy.ExportTopologyErrors_management(suTopo, wcFD, "SU_Errors")
##    arcpy.Delete_management(linesTopoFC)
##    arcpy.Delete_management(pointsTopoFC)
##    result = int(arcpy.GetCount_management(polysTopoFC).getOutput(0))
##    if result > 0:
##        AddMsgAndPrint("\tOverlaps found! Generating error layer for the map...",2)
##        arcpy.Delete_management(polysTopoFC)
##        arcpy.SetParameterAsText(1, suTopo)
##        #re_add_layers()
##    
##        AddMsgAndPrint("\tPlease review and correct overlaps and then re-run this tool. Exiting...",2)
##        exit()
##    else:
##        AddMsgAndPrint("\tNo overlaps found! Continuing...",0)
##        arcpy.Delete_management(polysTopoFC)


    #### Get administrative info for the request on the SU and ROP layer
    AddMsgAndPrint("\nCollecting request information...",0)
    arcpy.SetProgressorLabel("Collecting request info...")
    
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

    AddMsgAndPrint("\nUpdating Sampling Units request info...",0)
    arcpy.SetProgressorLabel("Updating Sampling Units request info...")

    # Update the SU layer, using an edit session. Only update the New Request and Revision features.
    workspace = wcGDB_path
    edit = arcpy.da.Editor(workspace)
    edit.startEditing(False, False)
    edit.startOperation()

    fields = ['admin_state','admin_state_name','admin_county','admin_county_name','state_code','state_name','county_code','county_name','farm_number','tract_number','eval_status','request_date','request_type','dig_staff','dig_date','job_id']
    #clause = "\"eval_status\" IN ('New Request', 'Revision')"
    with arcpy.da.UpdateCursor(projectSU, fields) as cursor:
        for row in cursor:
            if row[10] == "New Request" or row[10] == "Revision":
                row[0] = adState
                row[1] = adStateName
                row[2] = adCounty
                row[3] = adCountyName
                row[4] = stateCode
                row[5] = stateName
                row[6] = countyCode
                row[7] = countyName
                row[8] = farmNum
                row[9] = tractNum
                row[11] = rDate
                row[12] = rType
                row[13] = digStaff
                row[14] = digDate
                row[15] = job_id
            cursor.updateRow(row)
    del cursor, fields
    #del clause

    edit.stopOperation()
    edit.stopEditing(True)
    del workspace, edit

    expression = "round(!Shape.Area@acres!,2)"
    arcpy.CalculateField_management(projectSU, "acres", expression, "PYTHON_9.3")
    del expression

    # Update ROPs layer
    AddMsgAndPrint("\tUpdating ROPs request info...",0)
    arcpy.SetProgressorLabel("Updating ROPs info...")
    fields = ['job_id','admin_state','admin_state_name','admin_county','admin_county_name','state_code','state_name','county_code','county_name','farm_number','tract_number']
    cursor = arcpy.da.UpdateCursor(projectROP, fields)
    for row in cursor:
        row[0] = job_id
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
        cursor.updateRow(row)
    del cursor, fields


    #### Start attribute checks
    ### Sampling Units Layer
    AddMsgAndPrint("\nValidating Sampling Units...",0)
    arcpy.SetProgressorLabel("Validating Sampling Units...")

    ## Count the number of ROPs within each SU. If greater than 1, then stop and give an error
    AddMsgAndPrint("\tChecking number of ROPs per Sampling Unit...",0)
    if arcpy.Exists(ropCount):
        arcpy.Delete_management(ropCount)
    arcpy.analysis.SpatialJoin(projectSU, projectROP, ropCount, "JOIN_ONE_TO_ONE", "KEEP_ALL", "", "COMPLETELY_CONTAINS")
    cursor = arcpy.da.SearchCursor(ropCount, "Join_Count")
    for row in cursor:
        if row[0] > 1:
            AddMsgAndPrint("\nAt least one Sampling Unit contains more than one ROP. Delete or move the errant ROP(s). Exiting...", 2)
            arcpy.Delete_management(ropCount)
            exit()
        else:
            AddMsgAndPrint("\nThere is not more than one ROP per Sampling Unit.", 0)
            arcpy.Delete_management(ropCount)
    del cursor
    
    ## Evaluation Status
    # No null eval_status
    
    AddMsgAndPrint("\tChecking Evaluation Status...\n",0)
    checklist = []
    fields = ['eval_status']
    whereClause = "\"eval_status\" IS NULL"
    with arcpy.da.SearchCursor(projectSU, fields, whereClause) as cursor:
        for row in cursor:
            checklist.append(row[0])
    del cursor
    if len(checklist) > 0:
        AddMsgAndPrint("\tAt least one sampling unit does not have an Evaluation Status set. Please correct and re-run. Exiting...\n",2)
        exit()
    
    # Eval_Status values must come from the Evaluation Status domain
    eval_list = []
    cursor = arcpy.da.SearchCursor(projectSU, "eval_status")
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
            AddMsgAndPrint("\n" + item + " is not a valid choice for Evaluation Status. Please correct and re-run. Exiting...\n",2)
            exit()
    del ev_list, eval_list

    ## Sampling Unit Number
    # No null values
    AddMsgAndPrint("\tChecking Sampling Unit Numbers...\n",0)
    checklist = []
    fields = ['su_number']
    whereClause = "\"su_number\" IS NULL"
    with arcpy.da.SearchCursor(projectSU, fields, whereClause) as cursor:
        for row in cursor:
            checklist.append(row[0])
    del cursor
    if len(checklist) > 0:
        AddMsgAndPrint("\tAt least one sampling unit does not have a Sampling Unit Number assigned. Please correct and re-run. Exiting...\n",2)
        exit()
    
    # No repeated Sampling Unit identifiers
    su_list = []
    fields = ['su_number','su_letter']
    cursor = arcpy.da.SearchCursor(projectSU, fields)
    for row in cursor:
        if row[1] == None:
            su_id = str(row[0])
        else:
            su_id = str(row[0]) + row[1]
        if su_id not in su_list:
            su_list.append(su_id)
    del cursor
    su_len = len(su_list)
    su_count = int(arcpy.GetCount_management(projectSU).getOutput(0))
    if su_len != su_count:
        AddMsgAndPrint("\tOne or more Sampling Unit Number and Letter combinations are duplicated.",2)
        AddMsgAndPrint("\tReview the following list to find duplicate Sampling Unit identifier entries:",2)
        for item in su_list:
            AddMsgAndPrint("\t" + item,2)
        AddMsgAndPrint("\tPlease correct and re-run. Exiting...\n",2)
        exit()
    
    ## Associated ROP
    # No null values
    AddMsgAndPrint("\tChecking Sampling Unit Associated ROPs...\n",0)
    checklist = []
    fields = ['associated_rop']
    whereClause = "\"associated_rop\" IS NULL"
    with arcpy.da.SearchCursor(projectSU, fields, whereClause) as cursor:
        for row in cursor:
            checklist.append(row[0])
    del fields, cursor
    if len(checklist) > 0:
        AddMsgAndPrint("\tAt least one sampling unit does not have an Associated ROP Number assigned!",2)
        AddMsgAndPrint("\tThe following Sampling Units do not have a value entered for an Associated ROP:",2)
        fields = ['su_number','su_letter','associated_rop']
        whereClause = "\"associated_rop\" IS NULL"
        with arcpy.da.SearchCursor(projectSU, fields, whereClause) as cursor:
            for row in cursor:
                AddMsgAndPrint("\t" + str(row[0]) + str(row[1]),2)
        del cursor
        AddMsgAndPrint("\tPlease correct and re-run. Exiting...\n",2)
        exit()

    ## 3-Factors
    # No null values
    AddMsgAndPrint("\tChecking Sampling Unit 3-Factors...\n",0)
    checklist = []
    fields = ['three_factors']
    whereClause = "\"three_factors\" = 'U'"
    with arcpy.da.SearchCursor(projectSU, fields, whereClause) as cursor:
        for row in cursor:
            checklist.append(row[0])
    del cursor
    if len(checklist) > 0:
        AddMsgAndPrint("\tAt least one sampling unit does not have Y or N assigned for 3-Factors. Please correct and re-run. Exiting...\n",2)
        exit()
        
    # Values must come from the YN domain
    yn_list = []
    cursor = arcpy.da.SearchCursor(projectSU, "three_factors")
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
            AddMsgAndPrint("\n" + item + " is not a valid choice for 3-Factors in the Sampling Units layer. Please correct and re-run. Exiting...\n",2)
            exit()
    del ynd_list, yn_list

    # No values of U from the YN domain
    u_list = []
    fields = ['three_factors']
    whereClause = "\"three_factors\" = 'U'"
    with arcpy.da.SearchCursor(projectSU, fields, whereClause) as cursor:
        for row in cursor:
            u_list.append(row[0])
    del cursor
    if len(u_list) > 0:
        AddMsgAndPrint("\tAt least one sampling unit has a choice for 3-Factors listed as U. Please correct to Y or N and re-run. Exiting...\n",2)
        exit()
    del u_list
        
    ## Determination Method
    # No Null values
    AddMsgAndPrint("\tChecking Determination Method...\n",0)
    checklist = []
    fields = ['deter_method']
    whereClause = "\"deter_method\" IS NULL"
    with arcpy.da.SearchCursor(projectSU, fields, whereClause) as cursor:
        for row in cursor:
            checklist.append(row[0])
    del cursor
    if len(checklist) > 0:
        AddMsgAndPrint("\tAt least one sampling unit does not have a Determination Method set. Please correct and re-run. Exiting...\n",2)
        exit()
    
    # Values must come from the Method domain
    method_list = []
    cursor = arcpy.da.SearchCursor(projectSU, "deter_method")
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
            AddMsgAndPrint("\n" + item + " is not a valid choice for Determination Method in the Sampling Units layer. Please correct and re-run. Exiting...\n",2)
            exit()
    del md_list, method_list

    ## Determination Staff
    # Make sure determination staff is not null
    AddMsgAndPrint("\tChecking Determination Staff...\n",0)
    checklist = []
    fields = ['deter_staff']
    whereClause = "\"deter_staff\" IS NULL"
    with arcpy.da.SearchCursor(projectSU, fields, whereClause) as cursor:
        for row in cursor:
            checklist.append(row[0])
    del cursor
    if len(checklist) > 0:
        AddMsgAndPrint("\tAt least one Sampling Unit does not list a Determination Staff person. Please correct and re-run. Exiting...\n",2)
        exit()
    
    ### ROP Layer
    ## ROP Number
    # No Null values
    AddMsgAndPrint("\nValidating ROPs...",0)
    arcpy.SetProgressorLabel("Validating ROPs...")
    
    AddMsgAndPrint("\tChecking ROP Numbers...\n",0)
    checklist = []
    fields = ['rop_number']
    whereClause = "\"rop_number\" IS NULL"
    with arcpy.da.SearchCursor(projectROP, fields, whereClause) as cursor:
        for row in cursor:
            checklist.append(row[0])
    del cursor
    if len(checklist) > 0:
        AddMsgAndPrint("\tAt least one ROP does not have a ROP number assigned. Please correct and re-run. Exiting...\n",2)
        exit()
    
    # No repeated ROP Numbers on New Request and Revision SUs
    rop_list = []
    fields = ['rop_number']
##    whereClause = "\"eval_status\" IN ('New Request', 'Revision')"
    cursor = arcpy.da.SearchCursor(projectROP, fields)
    for row in cursor:
        if row[0] not in rop_list:
            rop_list.append(row[0])
    rop_len = len(rop_list)
    rop_count = int(arcpy.GetCount_management(projectROP).getOutput(0))
    del cursor
    if rop_len != rop_count:
        AddMsgAndPrint("\tOne or more ROP Numbers are duplicated. Please correct and re-run. Exiting...\n",2)
        exit()
    
    # Values in Associated ROP (in the sampling units layer) must actually exist in the ROP number attributes
    # Use the list of ROP numbers from the previous step
    # Search associated_rop in the sampling unit layer and check that the value is in the ROP list
    fields = ['associated_rop']
    cursor = arcpy.da.SearchCursor(projectSU, fields)
    for row in cursor:
        if row[0] not in rop_list:
            AddMsgAndPrint("\tOne of the values in a Sampling Unit's Associated ROP attribute does not match a valid ROP number. Please correct and re-run. Exiting...\n",2)
            exit()
    del cursor, fields

    ## Associated SU
    ## Repopulate the associated_su field for each ROP
    AddMsgAndPrint("\tUpdating Associated Sampling Units on ROPs...\n",0)
    # First set each associated_su attribute to null
    fields = ['associated_su']
    cursor = arcpy.da.UpdateCursor(projectROP, fields)
    for row in cursor:
        row[0] = None
        cursor.updateRow(row)
    del cursor, fields

    # For each ROP number, search for itself in SU layer's associated_rop attribute field and if found add that SU number to the
    # associated_su field for that ROP.
    rop_fields = ['rop_number','associated_su']
    su_fields = ['associated_rop','su_number','su_letter',]
    rop_cursor = arcpy.da.UpdateCursor(projectROP, rop_fields)
    for rop_row in rop_cursor:
        su_ids = ''
        rop_num = rop_row[0]
        su_cursor = arcpy.da.SearchCursor(projectSU, su_fields)
        for su_row in su_cursor:
            if su_row[0] == rop_num:
                if su_row[2] == None:
                    cur_su = str(su_row[1])
                else:
                    cur_su = str(su_row[1]) + su_row[2]
                if len(su_ids) == 0:
                    su_ids = su_ids + cur_su
                else:
                    su_ids = su_ids + ', ' + cur_su
        del su_cursor
        rop_row[1] = su_ids
        rop_cursor.updateRow(rop_row)
    del rop_fields, su_fields, rop_cursor

    
    #### Success
    AddMsgAndPrint("\nAll checks passed!\n",0)


##    #### Remove existing sampling unit topology related layers from the geodatabase
##    AddMsgAndPrint("\nRemoving topology from project database, if present...",0)
##
##    # Remove topology first, if it exists
##    toposToRemove = [suTopo]
##    for topo in toposToRemove:
##        if arcpy.Exists(topo):
##            try:
##                arcpy.Delete_management(topo)
##            except:
##                pass

    
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
