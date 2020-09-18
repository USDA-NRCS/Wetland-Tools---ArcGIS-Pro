## ===============================================================================================================
## Name:    Enter Project Info
## Purpose: Update and store user-entered administrative information for the current wetland determination request.
##
## Authors: Chris Morse
##          GIS Specialist
##          Indianapolis State Office
##          USDA-NRCS
##          chris.morse@usda.gov
##          317.295.5849
##
## Created: 9/18/2020
##
## ===============================================================================================================
## Changes
## ===============================================================================================================
##
## rev. 9/18/2020
## Start revisions of Enter Basic Info ArcMap tool to National Wetlands Tool in ArcGIS Pro.
## Removed lookup table steps for state and county names. That is now handled in the Create Project Folder tool.
## Greatly streamlined the tool and processing from the old ArcMap tool.
## Updated attributes for new data model of national tool.
## Added optional entries for client address information for use in creating forms and letters.
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
    
## ================================================================================================================
def logBasicSettings():    
    # record basic user inputs and settings to log file for future purposes
    import getpass, time
    f = open(textFilePath,'a+')
    f.write("\n######################################################################\n")
    f.write("Executing \"Enter Project Info\" tool...\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("User Parameters:\n")
    f.write("\tSelected CLU Layer: " + sourceCLU + "\n")
    f.write("\tClient Name: " + client + "\n")
    f.write("\tDelineator Name: " + delineator + "\n")
    f.write("\tDigitizer Name: " + digitizer + "\n")
    f.write("\tRequest Type: " + requestType + "\n")
    f.write("\tRequest Date: " + requestDate + "\n")
    f.close
    del f
    
## ================================================================================================================
#### Import system modules
import arcpy, os, traceback


#### Update Environments
# Set overwrite
arcpy.env.overwriteOutput = True


#### Main procedures
try:
    #### --------------------------------------------- Input Parameters
    sourceCLU = arcpy.GetParameterAsText(0)         # User selected CLU file from the project
    client = arcpy.GetParameterAsText(1)            # Client Name
    delineator = arcpy.GetParameterAsText(2)        # The person who conducts the technical determination
    digitizer = arcpy.GetParameterAsText(3)         # The person who digitizes the determination (may or may not match the delineator)
    requestType = arcpy.GetParameterAsText(4)       # Request Type (AD-1026, FSA-569, or NRCS-CPA-38)
    requestDate = arcpy.GetParameterAsText(5)       # Determination request date per request form signature date
    clientStreet = arcpy.GetParameterAsText(6)
    clientCity = arcpy.GetParameterAsText(7)
    clientState = arcpy.GetParameterAsText(8)
    clientZip = arcpy.GetParameterAsText(9)

    #### Set base path
    # Get the basedataGDB_path from the input CLU layer. If else retained in case of other project path oddities.
    sourceCLU_path = arcpy.Describe(sourceCLU).CatalogPath
    if sourceCLU_path.find('.gdb') > 0 and sourceCLU_path.find('Determinations') > 0 and sourceCLU_path.find('CLU_') > 0:
        basedataGDB_path = sourceCLU_path[:sourceCLU_path.find('.gdb')+4]
    else:
        arcpy.AddError("\nSelected CLU layer is not from a Determinations project folder. Exiting...")
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
    userWorkspace = os.path.dirname(basedataGDB_path)
    projectName = os.path.basename(userWorkspace).replace(" ", "_")
    wetDir = userWorkspace + os.sep + "Wetlands"
##    helDir = userWorkspace + os.sep + "HEL"
    
    wcGDB_name = os.path.basename(userWorkspace).replace(" ", "_") + "_WC.gdb"
    wcGDB_path = wetDir + os.sep + wcGDB_name
    wc_fd = wcGDB_path + os.sep + "WC_Data"

##    helGDB_name = os.path.basename(userWorkspace).replace(" ", "_") + "_HEL.gdb"
##    helGDB_path = helDir + os.sep + helGDB_name
##    hel_fd = helGDB_path + os.sep + "HEL_Data"
    
    templateTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "table_admin")
    tableName = "Table_" + projectName

    # Permanent Datasets
    projectTable = basedataGDB_path + os.sep + tableName


    #### Set up log file path and start logging
    textFilePath = userWorkspace + os.sep + projectName + "_PTD.txt"
    logBasicSettings()


    #### Table management
    # Determine if the job's admin table does not exist, else create the table.
    if not arcpy.Exists(projectTable):
        AddMsgAndPrint("\nCreating administrative table...",0)
        arcpy.CreateTable_management(basedataGDB_path, tableName, templateTable)

    # Get count of the records in the table.
    recordsCount = int(arcpy.GetCount_management(projectTable).getOutput(0))

    # If record count is greater than 1, delete all rows
    if recordsCount > 1:
        arcpy.DeleteRows(projectTable)

    # If record count is zero, create a row
    if recordsCount == 0:
        rows = arcpy.InsertCursor(projectTable)
        x = 1
        while x <= 1:
            row = rows.newRow()
            rows.insertRow(row)
            x = x+1
        del rows, row, x
    del recordsCount


    #### Update entries to the row in the table. This tool always overwrites
    # Use a search cursor to get the tract location info from the CLU layer
    AddMsgAndPrint("\nImporting tract data from the Project CLU layer...",0)
    field_names = ['admin_state','admin_state_name','admin_county','admin_county_name',
                   'state_code','state_name','county_code','county_name','farm_number','tract_number']
    with arcpy.da.SearchCursor(sourceCLU, field_names) as cursor:
        for row in cursor:
            adminState = row[0]
            adminStateName = row[1]
            adminCounty = row[2]
            adminCountyName = row[3]
            stateCode = row[4]
            stateName = row[5]
            countyCode = row[6]
            countyName = row[7]
            farmNumber = row[8]
            tractNumber = row[9]
            break
    del field_names

    # Use an update cursor to update all values in the admin table at once. Always overwrite.
    AddMsgAndPrint("\nUpdating the administrative table...",0)
    field_names = ['admin_state','admin_state_name','admin_county','admin_county_name',
                   'state_code','state_name','county_code','county_name','farm_number','tract_number',
                   'client','deter_staff','dig_staff','request_date','request_type','street','city',
                   'state','zip']
    with arcpy.da.UpdateCursor(projectTable, field_names) as cursor:
        for row in cursor:
            row[0] = adminState
            row[1] = adminStateName
            row[2] = adminCounty
            row[3] = adminCountyName
            row[4] = stateCode
            row[5] = stateName
            row[6] = countyCode
            row[7] = countyName
            row[8] = farmNumber
            row[9] = tractNumber
            row[10] = client
            row[11] = delineator
            row[12] = digitizer
            row[13] = requestDate
            row[14] = requestType
            if clientStreet != '':
                row[15] = clientStreet
            if clientCity != '':
                row[16] = clientCity
            if clientState != '':
                row[17] = clientState
            if clientZip != '':
                row[18] = clientZip
            cursor.updateRow(row)
    del field_names


    #### Create a text file output version of the admin table for consumption by external data collection forms
    # Set a file name and export to the user workspace folder for the project
    AddMsgAndPrint("\nExporting administrative text file...",0)
    textTable = "Admin_Info_" + projectName + ".txt"
    arcpy.TableToTable_conversion(projectTable, userWorkspace, textTable)


    #### Compact FGDB
    try:
        AddMsgAndPrint("\nCompacting File Geodatabase..." ,0)
        arcpy.Compact_management(basedataGDB_path)
        AddMsgAndPrint("\tDone!",0)
    except:
        pass
    
except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested....exiting")

except:
    errorMsg()
