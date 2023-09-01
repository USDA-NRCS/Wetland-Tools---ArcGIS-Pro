from getpass import getuser
from os import path
from sys import argv, exc_info, exit
from time import ctime
from traceback import format_exception

from arcpy import AddError, AddMessage, AddWarning, Describe, env, Exists, GetParameterAsText, SetProgressorLabel
from arcpy.conversion import TableToTable
from arcpy.da import InsertCursor, SearchCursor
from arcpy.management import Compact, CreateFeatureDataset, CreateFileGDB, CreateTable, Delete, DeleteRows, GetCount
from arcpy.mp import ArcGISProject


# ================================================================================================================
def AddMsgAndPrint(msg, severity=0):
    print(msg)
    try:
        f = open(textFilePath, 'a+')
        f.write(f"{msg}\n")
        f.close
        del f
        if severity == 0:
            AddMessage(msg)
        elif severity == 1:
            AddWarning(msg)
        elif severity == 2:
            AddError(msg)
    except:
        pass


def errorMsg():
    try:
        exc_type, exc_value, exc_traceback = exc_info()
        theMsg = f"\t{format_exception(exc_type, exc_value, exc_traceback)[1]}\n\t{format_exception(exc_type, exc_value, exc_traceback)[-1]}"
        if theMsg.find('exit') > -1:
            AddMsgAndPrint('\n\n')
            pass
        else:
            AddMsgAndPrint(theMsg, 2)
    except:
        AddMsgAndPrint('Unhandled error in unHandledException method', 2)
        pass
    

def logBasicSettings():
    f = open(textFilePath, 'a+')
    f.write('\n######################################################################\n')
    f.write('Executing \"Enter Project Info\" tool...\n')
    f.write(f"User Name: {getuser()}\n")
    f.write(f"Date Executed: {ctime()}\n")
    f.write('User Parameters:\n')
    f.write(f"\tSelected CLU Layer: {sourceCLU}\n")
    f.write(f"\tClient Name: {client}\n")
    f.write(f"\tDelineator Name: {delineator}\n")
    f.write(f"\tDigitizer Name: {digitizer}\n")
    f.write(f"\tRequest Type: {requestType}\n")
    f.write(f"\tRequest Date: {requestDate}\n")
    f.close
    del f


def getLayout(lyt_name):
    try:
        layout = aprx.listLayouts(lyt_name)[0]
        return layout
    except:
        AddMsgAndPrint(f"\t{lyt_name} layout missing from project. Skipping layout automation for {lyt_name}", 1)
        AddMsgAndPrint(f"\tImporting the missing {lyt_name} layout from the install directory is recommended. Continuing...", 1)
        return False


def updateLayoutText(layout_object, layout_farm, layout_tract, layout_CoName, layout_adminName, layout_client):
    """ Updates various text elements specific to the current request """
    try:
        Farm_ele = layout_object.listElements('TEXT_ELEMENT', 'Farm')[0]
        Tract_ele = layout_object.listElements('TEXT_ELEMENT', 'Tract')[0]
        GeoCo_ele = layout_object.listElements('TEXT_ELEMENT', 'GeoCo')[0]
        AdminCo_ele = layout_object.listElements('TEXT_ELEMENT', 'AdminCo')[0]
        Customer_ele = layout_object.listElements('TEXT_ELEMENT', 'Customer')[0]
    except:
        AddMsgAndPrint(f"\nOne or more expected elements are missing or had its name changed in the {layout_object.name} layout", 1)
        AddMsgAndPrint('\nLayout text cannot be updated automatically. Import the appropriate layout from the installation folder and try again', 1)
        AddMsgAndPrint(f"\nContinuing execution without updating the {layout_object.name} layout...", 1)

    Farm_ele.text = f"Farm: {layout_farm}"
    Tract_ele.text = f"Tract: {layout_tract}"
    GeoCo_ele.text = f"Geographic County: {layout_CoName}"
    AdminCo_ele.text = f"Administrative County: {layout_adminName}"
    Customer_ele.text = f"Customer: {layout_client}"


# ================================================================================================================
# Set arcpy Environment Settings
env.overwriteOutput = True

# Check for active map in Pro Project
try:
    aprx = ArcGISProject('CURRENT')
    m = aprx.listMaps('Determinations')[0]
except:
    AddMsgAndPrint('\nThis tool must be run from an active ArcGIS Pro project that was developed from the template distributed with this toolbox. Exiting...\n', 2)
    exit()

# Main procedures
try:
    SetProgressorLabel('Reading inputs...')
    sourceCLU = GetParameterAsText(0)         # User selected CLU file from the project
    client = GetParameterAsText(1)            # Client Name
    delineator = GetParameterAsText(2)        # The person who conducts the technical determination
    digitizer = GetParameterAsText(3)         # The person who digitizes the determination (may or may not match the delineator)
    requestType = GetParameterAsText(4)       # Request Type (AD-1026, FSA-569, or NRCS-CPA-38)
    requestDate = GetParameterAsText(5)       # Determination request date per request form signature date
    clientStreet = GetParameterAsText(6)
    clientStreet2 = GetParameterAsText(7)
    clientCity = GetParameterAsText(8)
    clientState = GetParameterAsText(9)
    clientZip = GetParameterAsText(10)

    # Get the basedataGDB_path from the input CLU layer. If else retained in case of other project path oddities.
    sourceCLU_path = Describe(sourceCLU).CatalogPath
    if sourceCLU_path.find('.gdb') > 0 and sourceCLU_path.find('Determinations') > 0 and sourceCLU_path.find('Site_CLU') > 0:
        basedataGDB_path = sourceCLU_path[:sourceCLU_path.find('.gdb')+4]
    else:
        AddMsgAndPrint('\nSelected CLU layer is not from a Determinations project folder. Exiting...', 2)
        exit()

    # Define Variables
    SetProgressorLabel('Setting variables...')
    basedataGDB_name = path.basename(basedataGDB_path)
    userWorkspace = path.dirname(basedataGDB_path)
    projectName = path.basename(userWorkspace).replace(' ', '_')
    cluName = 'Site_CLU'
    projectCLU = path.join(basedataGDB_path, 'Layers', cluName)
    daoiName = 'Site_Define_AOI'
    wetDir = path.join(userWorkspace, 'Wetlands')
    
    wcGDB_name = f"{path.basename(userWorkspace).replace(' ', '_')}_WC.gdb"
    wcGDB_path = path.join(wetDir, wcGDB_name)
    wcFD = path.join(wcGDB_path, 'WC_Data')
    
    templateTable = path.join(path.dirname(argv[0]), path.join('SUPPORT.gdb', 'table_admin'))
    tableName = f"Table_{projectName}"

    # Permanent Datasets
    projectTable = path.join(basedataGDB_path, tableName)
    wetDetTable = path.join(wcGDB_path, 'Admin_Table')

    # Set up log file path and start logging
    SetProgressorLabel('Starting log file...')
    textFilePath = path.join(userWorkspace, f"{projectName}_log.txt")
    logBasicSettings()

    # Get Job ID from input CLU
    SetProgressorLabel('Recording project Job ID...')
    fields = ['job_id']
    with SearchCursor(projectCLU, fields) as cursor:
        for row in cursor:
            jobid = row[0]
            break

    # If the job's admin table exists, clear all rows, else create the table
    if Exists(projectTable):
        SetProgressorLabel('Located project admin table table...')
        recordsCount = int(GetCount(projectTable)[0])
        if recordsCount > 0:
            DeleteRows(projectTable)
            AddMsgAndPrint('\nCleared existing row from project admin table...')
    else:
        SetProgressorLabel('Creating administrative table...')
        CreateTable(basedataGDB_path, tableName, templateTable)
        AddMsgAndPrint('\nCreated administrative table...')

    # Use a search cursor to get the tract location info from the CLU layer
    AddMsgAndPrint('\nImporting tract data from the CLU...')
    SetProgressorLabel('Importing tract data from the CLU...')
    field_names = ['admin_state','admin_state_name','admin_county','admin_county_name',
                   'state_code','state_name','county_code','county_name','farm_number','tract_number']
    with SearchCursor(sourceCLU, field_names) as cursor:
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

    # Use an insert cursor to add record to the admin table
    AddMsgAndPrint('\nUpdating the administrative table...')
    SetProgressorLabel('Updating the administrative table...')
    field_names = ['admin_state','admin_state_name','admin_county','admin_county_name','state_code','state_name',
                   'county_code','county_name','farm_number','tract_number','client','deter_staff',
                   'dig_staff','request_date','request_type','street','street_2','city','state','zip','job_id']
    row = (adminState, adminStateName, adminCounty, adminCountyName, stateCode, stateName, countyCode,
           countyName, farmNumber, tractNumber, client, delineator, digitizer, requestDate, requestType,
           clientStreet if clientStreet else None, clientStreet2 if clientStreet2 else None, clientCity if clientCity else None,
           clientState if clientState else None, clientZip if clientZip else None, jobid)
    with InsertCursor(projectTable, field_names) as cursor:
        cursor.insertRow(row)

    # Create a text file output version of the admin table for consumption by external data collection forms
    # Set a file name and export to the user workspace folder for the project
    AddMsgAndPrint('\nExporting administrative text file...')
    SetProgressorLabel('Exporting administrative text file...')
    textTable = f"Admin_Info_{projectName}.txt"
    if Exists(textTable):
        Delete(textTable)
    TableToTable(projectTable, userWorkspace, textTable)

    # Update template map layouts in the project
    AddMsgAndPrint('\nUpdating map layouts...')
    SetProgressorLabel('Updating map layouts...')
    
    # Define the map layouts
    LM_layout = getLayout('Location Map')
    BM_layout = getLayout('Base Map')
    DM_layout = getLayout('Determination Map')
    EM_layout = getLayout('Elevation Map')
    NM_layout = getLayout('NWI Map')
    PM_layout = getLayout('Previous Determination Map')
    SM_layout = getLayout('Soil Map')
    
    # Update the map layouts
    if LM_layout:
        updateLayoutText(LM_layout, farmNumber, tractNumber, countyName, adminCountyName, client)
    if BM_layout:
        updateLayoutText(BM_layout, farmNumber, tractNumber, countyName, adminCountyName, client)
    if DM_layout:
        updateLayoutText(DM_layout, farmNumber, tractNumber, countyName, adminCountyName, client)
    if EM_layout:
        updateLayoutText(EM_layout, farmNumber, tractNumber, countyName, adminCountyName, client)
    if NM_layout:
        updateLayoutText(NM_layout, farmNumber, tractNumber, countyName, adminCountyName, client)
    if PM_layout:
        updateLayoutText(PM_layout, farmNumber, tractNumber, countyName, adminCountyName, client)
    if SM_layout:
        updateLayoutText(SM_layout, farmNumber, tractNumber, countyName, adminCountyName, client)

    # If project wetlands geodatabase and feature dataset do not exist, create them.
    # Get the spatial reference from the Define AOI feature class and use it, if needed
    AddMsgAndPrint('\nChecking project integrity...')
    SetProgressorLabel('Checking project integrity...')
    desc = Describe(sourceCLU)
    sr = desc.SpatialReference
    
    if not Exists(wcGDB_path):
        AddMsgAndPrint('\tCreating Wetlands geodatabase...')
        SetProgressorLabel('Creating Wetlands geodatabase...')
        CreateFileGDB(wetDir, wcGDB_name)

    if not Exists(wcFD):
        AddMsgAndPrint('\tCreating Wetlands feature dataset...')
        SetProgressorLabel('Creating Wetlands feature dataset...')
        CreateFeatureDataset(wcGDB_path, 'WC_Data', sr)

    # Copy the administrative table into the wetlands database for use with the attribute rules during digitizing
    AddMsgAndPrint('\nUpdating administrative table in GDB...')
    if Exists(wetDetTable):
        Delete(wetDetTable)
    TableToTable(projectTable, wcGDB_path, 'Admin_Table')

    # Adjust layer visibility in maps, turn off CLU layer
    AddMsgAndPrint('\nUpdating layer visibility to off...')
    off_names = [cluName]
    for maps in aprx.listMaps():
        for lyr in maps.listLayers():
            for name in off_names:
                if name in lyr.longName:
                    lyr.visible = False

    # Turn on DAOI layer
    on_names = [daoiName]
    for maps in aprx.listMaps():
        for lyr in maps.listLayers():
            for name in on_names:
                if name in lyr.longName:
                    lyr.visible = True

    # Compact file geodatabase
    try:
        AddMsgAndPrint('\nCompacting File Geodatabase...')
        SetProgressorLabel('Compacting File Geodatabase...')
        Compact(basedataGDB_path)
        AddMsgAndPrint('\tDone')
    except:
        pass
    
except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint('Keyboard interruption requested... Exiting')

except:
    errorMsg()
