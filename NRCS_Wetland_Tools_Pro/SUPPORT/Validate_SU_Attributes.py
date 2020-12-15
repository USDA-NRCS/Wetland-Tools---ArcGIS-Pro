## ===============================================================================================================
## Name:    Validate SU Attributes
## Purpose: Update and verify a number of attributes in the Sampling Units, ROPs, and Drainage Lines layer
##
## Authors: Chris Morse
##          GIS Specialist
##          Indianapolis State Office
##          USDA-NRCS
##          chris.morse@usda.gov
##          317.295.5849
##
## Created: 12/02/2020
##
## ===============================================================================================================
## Changes
## ===============================================================================================================
##
## rev. 12/02/2020
## Start revisions of Validate Topology ArcMap tool to National Wetlands Tool in ArcGIS Pro.
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
    f.write("Executing Validate SU Attributes tool...\n")
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

#### ===============================================================================================================
##def re_add_layers():
##    m.addLayer(suLyr)
##    m.addLayer(ropLyr)
##    m.addLayer(drainLyr)
##    m.addLayer(extentLyr)
##        
##    suNew = m.listLayers("Site_Sampling_Units")[0]
##    ropNew = m.listLayers("Site_ROPs")[0]
##    drainNew = m.listLayers("Site_Drainage_Lines")[0]
##    extentNew = m.listLayers("Request_Extent")[0]
##
##    changeSource(suNew, new_ws=wcGDB_path, new_fd=wcFD_name, new_fc=suName)
##    changeSource(ropNew, new_ws=wcGDB_path, new_fd=wcFD_name, new_fc=ropName)
##    changeSource(drainNew, new_ws=wcGDB_path, new_fd=wcFD_name, new_fc=drainName)
##    changeSource(extentNew, new_ws=basedataGDB_path, new_fd=basedataFD_name, new_fc=extentName)
##
##    suNew.name = suName
##    ropNew.name = ropName
##    drainNew.name = drainName
##    extentNew.name = extentName

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
##from importlib import reload
##sys.dont_write_bytecode=True
##scriptPath = os.path.dirname(sys.argv[0])
##sys.path.append(scriptPath)
##
##import extract_CLU_by_Tract
##reload(extract_CLU_by_Tract)


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


###### Check GeoPortal Connection
##nrcsPortal = 'https://gis.sc.egov.usda.gov/portal/'
##portalToken = extract_CLU_by_Tract.getPortalTokenInfo(nrcsPortal)
##if not portalToken:
##    arcpy.AddError("Could not generate Portal token! Please login to GeoPortal! Exiting...")
##    exit()
    

#### Main procedures
try:
    #### Inputs
    arcpy.AddMessage("Reading inputs...\n")
    sourceSU = arcpy.GetParameterAsText(0)
    
##    suLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(8))
##    ropLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(9))
##    drainLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(10))
##    extentLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(11))


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
        arcpy.AddError("\nSelected Sampling Units layer is not from a Determinations project folder. Exiting...")
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

    projectTract = basedataFD + os.sep + "Site_Tract"
    projectTable = basedataGDB_path + os.sep + "Table_" + projectName

    suName = "Site_Sampling_Units"
    projectSU = wcFD + os.sep + suName

    ropName = "Site_ROPs"
    projectROP = wcFD + os.sep + ropName

    drainName = "Site_Drainage_Lines"
    projectLines = wcFD + os.sep + drainName

    extentName = "Request_Extent"
    projectExtent = basedataFD + os.sep + extentName

    suTopoName = "Sampling_Units_Topology"
    suTopo = wcFD + os.sep + suTopoName
    
    domain_base = supportGDB
    method_domain = domain_base + os.sep + "domain_method"
    eval_domain = domain_base + os.sep + "domain_evaluation_status"
    yn_domain = domain_base + os.sep + "domain_yn"
    yesno_domain = domain_base + os.sep + "domain_yesno"
    rop_status_domain = domain_base + os.sep + "domain_rop_status"
    
    # ArcPro Map Layer Names
    suOut = "Site_Sampling_Units"
    ropOut = "Site_ROPs"
    drainOut = "Site_Drainage_Lines"
    extentOut = "Request_Extent"
    suTopoOut = suTopoName

    # Temp layers list for cleanup at the start and at the end
    tempLayers = []
    deleteTempLayers(tempLayers)


    #### Set up log file path and start logging
    arcpy.AddMessage("Commence logging...\n")
    textFilePath = userWorkspace + os.sep + projectName + "_log.txt"
    logBasicSettings()


    #### If project wetlands feature dataset does not exist, exit.
    if not arcpy.Exists(wcFD):
        AddMsgAndPrint("\tInput Site Sampling Units layer does not come from an expected project feature dataset.",2)
        AddMsgAndPrint("\tPlease re-run and select a valid Site Samping Units layer. Exiting...",2)
        exit()


    #### At least one SU record and one ROP record must exist
    AddMsgAndPrint("\nVerifying project layer integrity...",0)
    result = int(arcpy.GetCount_management(projectSU).getOutput(0))
    if result < 1:
        AddMsgAndPrint("\tAt least one sampling unit must exist in the Site Sampling Units layer.",2)
        AddMsgAndPrint("\tPlease backtrack in the workflow to create and digitize sampling units and try again. Exiting...",2)
        exit()

    result = int(arcpy.GetCount_management(projectROP).getOutput(0))
    if result < 1:
        AddMsgAndPrint("\tAt least one ROP must exist in the Site ROPs layer.",2)
        AddMsgAndPrint("\tPlease backtrack in the workflow to create and digitize ROPs and try again. Exiting...",2)
        exit()
    
    
    #### Update request level administrative attributes before performing validations on user entered attributes
    AddMsgAndPrint("\nUpdating administrative attributes...",0)

    # Get admin attributes from project table for request_date, request_type, deter_staff, dig_staff, and dig_date (current date)
    fields = ['admin_state','admin_state_name','admin_county','admin_county_name','state_code','state_name','county_code','county_name','farm_number','tract_number','request_date','request_type']
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
        #break
    del cursor, fields

    digStaff = str(os.getenv('username').replace("."," ")).title()
    digDate = time.strftime('%m/%d/%Y')
    #digDate = time.strftime('%Y-%m-%d') + ' 00:00:00'

    # Update Sampling Units layer
    AddMsgAndPrint("\tUpdating Sampling Units...",0)

    expression = "!Shape.Area@acres!"
    arcpy.CalculateField_management(projectSU, "acres", expression, "PYTHON_9.3")
    del expression

    # For some reason, the SU layer update cursor must be done within an edit session.
    workspace = wcGDB_path
    edit = arcpy.da.Editor(workspace)
    edit.startEditing(False, False)
    
    fields = ['admin_state','admin_state_name','admin_county','admin_county_name','state_code','state_name','county_code','county_name','farm_number','tract_number','request_date','request_type','dig_staff','dig_date']
    cursor = arcpy.da.UpdateCursor(projectSU, fields)
    for row in cursor:
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
        row[10] = rDate
        row[11] = rType
        row[12] = digStaff
        row[13] = digDate
        cursor.updateRow(row)
    del cursor, fields

    edit.stopEditing(True)
    del workspace, edit

    # Update ROPs layer
    AddMsgAndPrint("\tUpdating ROPs...",0)
    fields = ['admin_state','admin_state_name','admin_county','admin_county_name','state_code','state_name','county_code','county_name','farm_number','tract_number','request_date','request_type','dig_staff','dig_date']
    cursor = arcpy.da.UpdateCursor(projectROP, fields)
    for row in cursor:
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
        row[10] = rDate
        row[11] = rType
        row[12] = digStaff
        row[13] = digDate
        cursor.updateRow(row)
    del cursor, fields


    #### Start performing the attribute validations on Sampling Unit layer
    AddMsgAndPrint("\nValidating Sampling Unit layer attributes...",0)

    ### Sampling Units Layer
    ## Evaluation Status
    # No Null values
    AddMsgAndPrint("\tChecking Evaluation Status...\n",0)
    checklist = []
    fields = ['eval_status']
    whereClause = "\"eval_status\" IS NULL"
    with arcpy.da.SearchCursor(projectSU, fields, whereClause) as cursor:
        for row in cursor:
            checklist.append(row[0])
    if len(checklist) > 0:
        AddMsgAndPrint("\tAt least one sampling unit does not have an Evaluation Status set. Please correct and re-run. Exiting...\n",2)
        exit()

    # Values must come from the Evaluation Status domain
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
    if len(checklist) > 0:
        AddMsgAndPrint("\tAt least one sampling unit does not have a Sampling Unit Number assigned. Please correct and re-run. Exiting...\n",2)
        exit()

    # No repeated Sampling Unit Numbers
    su_list = []
    fields = ['su_number']
    cursor = arcpy.da.SearchCursor(projectSU, fields)
    for row in cursor:
        if row[0] not in su_list:
            su_list.append(row[0])
    su_len = len(su_list)
    su_count = int(arcpy.GetCount_management(projectSU).getOutput(0))
    if su_len != su_count:
        AddMsgAndPrint("\tOne or more Sampling Unit Numbers are duplicated. Please correct and re-run. Exiting...\n",2)
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
    if len(checklist) > 0:
        AddMsgAndPrint("\tAt least one sampling unit does not have an Associated ROP Number assigned. Please correct and re-run. Exiting...\n",2)
        exit()

    ## 3-Factors
    # No null values
    AddMsgAndPrint("\tChecking Sampling Unit 3-Factors...\n",0)
    checklist = []
    fields = ['three_factors']
    whereClause = "\"three_factors\" IS NULL"
    with arcpy.da.SearchCursor(projectSU, fields, whereClause) as cursor:
        for row in cursor:
            checklist.append(row[0])
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

    ## Determination Method
    # No Null values
    AddMsgAndPrint("\tChecking Determination Method...\n",0)
    checklist = []
    fields = ['deter_method']
    whereClause = "\"deter_method\" IS NULL"
    with arcpy.da.SearchCursor(projectSU, fields, whereClause) as cursor:
        for row in cursor:
            checklist.append(row[0])
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
    # Read from Sampling Unit and populate.
    AddMsgAndPrint("\tUpdating ROP Determination Staff...\n",0)
    checklist = []
    fields = ['deter_staff']
    whereClause = "\"deter_staff\" IS NULL"
    with arcpy.da.SearchCursor(projectSU, fields, whereClause) as cursor:
        for row in cursor:
            checklist.append(row[0])
    if len(checklist) > 0:
        AddMsgAndPrint("\tAt least one sampling unit does not list a Determination Staff person. Please correct and re-run. Exiting...\n",2)
        exit()


    #### Start performing the attribute validations on ROP layer
    AddMsgAndPrint("\nValidating ROP layer attributes...",0)
    
    ### ROP layer
    ## Associated SU
    ## Repopulate the associated_su field for each ROP
    # First set each associated_su attribute to null
    fields = ['associated_su']
    cursor = arcpy.da.UpdateCursor(projectROP, fields)
    for row in cursor:
        row[0] = None
        cursor.updateRow(row)
    del cursor, fields

    # For each ROP number, search for itself in SU layer's associated_rop attribute field and if found add that SU number to the
    # associated_su field for that ROP.
    rop_fields = ['rop_number','associated_su','deter_staff']
    su_fields = ['associated_rop','su_number','deter_staff']
    rop_cursor = arcpy.da.UpdateCursor(projectROP, rop_fields)
    for rop_row in rop_cursor:
        su_nums = ''
        rop_num = rop_row[0]
        su_cursor = arcpy.da.SearchCursor(projectSU, su_fields)
        for su_row in su_cursor:
            if su_row[0] == rop_num:
                cur_su = str(su_row[1])
                if len(su_nums) == 0:
                    su_nums = su_nums + cur_su
                else:
                    su_nums = su_nums + ', ' + cur_su
        del su_cursor
        rop_row[1] = su_nums
        rop_cursor.updateRow(rop_row)
    del rop_fields, su_fields, rop_cursor

    
    ## ROP Number
    # No Null values
    AddMsgAndPrint("\tChecking ROP Number...\n",0)
    checklist = []
    fields = ['rop_number']
    whereClause = "\"rop_number\" IS NULL"
    with arcpy.da.SearchCursor(projectROP, fields, whereClause) as cursor:
        for row in cursor:
            checklist.append(row[0])
    if len(checklist) > 0:
        AddMsgAndPrint("\tAt least one ROP does not have a ROP number assigned. Please correct and re-run. Exiting...\n",2)
        exit()

    # No repeated ROP Numbers
    rop_list = []
    fields = ['rop_number']
    cursor = arcpy.da.SearchCursor(projectROP, fields)
    for row in cursor:
        if row[0] not in rop_list:
            rop_list.append(row[0])
    rop_len = len(rop_list)
    rop_count = int(arcpy.GetCount_management(projectROP).getOutput(0))
    if rop_len != rop_count:
        AddMsgAndPrint("\tOne or more ROP Numbers are duplicated. Please correct and re-run. Exiting...\n",2)
        exit()

    # Values in Associated ROP (in the sampling units layer) must actually exist in the ROP number attributes
    # Use the list of ROP values from the previous step
    # Search associated_rop in the sampling unit layer and check that the value is in the ROP list
    fields = ['associated_rop']
    cursor = arcpy.da.SearchCursor(projectSU, fields)
    for row in cursor:
        if row[0] not in rop_list:
            AddMsgAndPrint("\tOne of the values in a Sampling Unit's Associated ROP attribute does not match a valid ROP number. Please correct and re-run. Exiting...\n",2)
            exit()
    del cursor, fields
    
    ## ROP Status
    # No Null values
    AddMsgAndPrint("\tChecking ROP Status...\n",0)
    checklist = []
    fields = ['rop_status']
    whereClause = "\"rop_status\" IS NULL"
    with arcpy.da.SearchCursor(projectROP, fields, whereClause) as cursor:
        for row in cursor:
            checklist.append(row[0])
    if len(checklist) > 0:
        AddMsgAndPrint("\tAt least one ROP does not have a ROP status assigned. Please correct and re-run. Exiting...\n",2)
        exit()

    # Values must come from the ROP Status domain
    ros_list = []
    cursor = arcpy.da.SearchCursor(projectROP, "rop_status")
    for row in cursor:
        if row[0] not in ros_list:
            ros_list.append(row[0])
    del cursor
    rs_list = []
    cursor = arcpy.da.SearchCursor(rop_status_domain, "Code")
    for row in cursor:
        if row[0] not in rs_list:
            rs_list.append(row[0])
    del cursor
    for item in ros_list:
        if item not in rs_list:
            AddMsgAndPrint("\n" + item + " is not a valid choice for ROP Status. Please correct and re-run. Exiting...\n",2)
            exit()
    del rs_list, ros_list

    ## 3-Factors
    # No null values
    AddMsgAndPrint("\tChecking ROP 3-Factors...\n",0)
    checklist = []
    fields = ['three_factors']
    whereClause = "\"three_factors\" IS NULL"
    with arcpy.da.SearchCursor(projectROP, fields, whereClause) as cursor:
        for row in cursor:
            checklist.append(row[0])
    if len(checklist) > 0:
        AddMsgAndPrint("\tAt least one ROP does not have Y or N assigned for 3-Factors. Please correct and re-run. Exiting...\n",2)
        exit()

    # Values must come from the YN domain
    yn_list = []
    cursor = arcpy.da.SearchCursor(projectROP, "three_factors")
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
            AddMsgAndPrint("\n" + item + " is not a valid choice for 3-Factors in the ROP layer. Please correct and re-run. Exiting...\n",2)
            exit()
    del ynd_list, yn_list
    
    ## Data Form
    # No null values
    AddMsgAndPrint("\tChecking ROP Data Form...\n",0)
    checklist = []
    fields = ['data_form']
    whereClause = "\"data_form\" IS NULL"
    with arcpy.da.SearchCursor(projectROP, fields, whereClause) as cursor:
        for row in cursor:
            checklist.append(row[0])
    if len(checklist) > 0:
        AddMsgAndPrint("\tAt least one ROP does not have Yes or No assigned for Data Form. Please correct and re-run. Exiting...\n",2)
        exit()

    # Values must come from the YesNo domain
    yn_list = []
    cursor = arcpy.da.SearchCursor(projectROP, "data_form")
    for row in cursor:
        if row[0] not in yn_list:
            yn_list.append(row[0])
    del cursor
    ynd_list = []
    cursor = arcpy.da.SearchCursor(yesno_domain, "Code")
    for row in cursor:
        if row[0] not in ynd_list:
            ynd_list.append(row[0])
    del cursor
    for item in yn_list:
        if item not in ynd_list:
            AddMsgAndPrint("\n" + item + " is not a valid choice for Data Form in the ROP layer. Please correct and re-run. Exiting...\n",2)
            exit()
    del ynd_list, yn_list
    
    ## Determination Method
    # No Null values
    AddMsgAndPrint("\tChecking Determination Method...\n",0)
    checklist = []
    fields = ['deter_method']
    whereClause = "\"deter_method\" IS NULL"
    with arcpy.da.SearchCursor(projectROP, fields, whereClause) as cursor:
        for row in cursor:
            checklist.append(row[0])
    if len(checklist) > 0:
        AddMsgAndPrint("\tAt least one ROP does not have a Determination Method set. Please correct and re-run. Exiting...\n",2)
        exit()

    # Values must come from the Method domain
    method_list = []
    cursor = arcpy.da.SearchCursor(projectROP, "deter_method")
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
            AddMsgAndPrint("\n" + item + " is not a valid choice for Determination Method in the ROP layer. Please correct and re-run. Exiting...\n",2)
            exit()
    del md_list, method_list

    ## Determination Staff
    AddMsgAndPrint("\tChecking Determination Staff...\n",0)
    # Populate from associated Sampling Units
    # For each ROP number, search for itself in SU layer's associated_rop attribute field and if found add that deter_staff to that rop
    rop_fields = ['rop_number','deter_staff']
    su_fields = ['associated_rop','deter_staff']
    rop_cursor = arcpy.da.UpdateCursor(projectROP, rop_fields)
    for rop_row in rop_cursor:
        detStaff = ''
        rop_num = rop_row[0]
        su_cursor = arcpy.da.SearchCursor(projectSU, su_fields)
        for su_row in su_cursor:
            if su_row[0] == rop_num:
                detStaff = su_row[1]
        del su_cursor
        rop_row[1] = detStaff
        rop_cursor.updateRow(rop_row)
    del rop_fields, su_fields, rop_cursor
    

    # No null data (in case all the population left a blank)
    checklist = []
    fields = ['deter_staff']
    whereClause = "\"deter_staff\" IS NULL"
    with arcpy.da.SearchCursor(projectROP, fields, whereClause) as cursor:
        for row in cursor:
            checklist.append(row[0])
    if len(checklist) > 0:
        AddMsgAndPrint("\tAt least one Sampling Unit does not list a Determination Staff person or is not associated to a ROP. Please correct and re-run. Exiting...\n",2)
        exit()


    #### Success
    AddMsgAndPrint("\nAll checks passed!\n",0)

    
    #### Compact FGDB
    try:
        AddMsgAndPrint("\nCompacting File Geodatabases..." ,0)
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
