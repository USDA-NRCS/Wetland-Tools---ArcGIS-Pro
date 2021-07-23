## ===============================================================================================================
## Name:    Create Wetlands Project
## Purpose: Create a wetland determination project folder in C:\Determinations. Download a
##          single CLU Tract specified by user inputs for admin state, county, and tract.
##
## Authors: Chris Morse
##          GIS Specialist
##          Indianapolis State Office
##          USDA-NRCS
##          chris.morse@usda.gov
##          317.295.5849
##
##          Adolfo Diaz
##          GIS Specialist
##          National Soil Survey Center
##          USDA-NRCS
##          adolfo.diaz@usda.gov
##          608.662.4422, ext. 216
##
## Created: 8/20/2020
##
## ===============================================================================================================
## Changes
## ===============================================================================================================
##
## rev. 8/20/2020
## Start revisions of Create Project Folder ArcMap tool to National Wetlands Tool in ArcGIS Pro.
## Change CLU generation to use GeoPortal based web service and Extract CLU code by Adolfo Diaz.
## Change input parameters to use lookup table for states & counties downloaded from US Census.
## Change processing to use lookup table obtained from US Census for state and county names.
##
## rev. 10/13/2020
## Change processing to create a template blank CLU feature class and then append downloaded CLU features to it
## Incorporated option to update an existing project after the month/year that the project was started has passed
##
## rev. 03/02/2021
## -Removed tract buffer and tract AOI generation steps. Moved them to Define Request Extent to tie to the
##  extent of the request, instead of defaulting to the extent of the tract. This was done to limit processing of
##  the entirety of very large tracts where only small requests in one part of the tract take place and are needed.
## -Added the Job ID generation to the CLU and Tract layer outputs.
##
## rev. 07/08/2021
## -Added checks for Determinations map coordinate system to stop if a recommended PCS is not assigned
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
def splitThousands(someNumber):
    # Determines where to put a thousands separator in an integer.
    # Integer with or without thousands seperator is returned.

    try:
        return re.sub(r'(\d{3})(?=\d)', r'\1,', str(someNumber)[::-1])[::-1]

    except:
        errorMsg()
        return someNumber
        
## ===============================================================================================================
def logBasicSettings():    
    # record basic user inputs and settings to log file for future purposes
    import getpass, time
    f = open(textFilePath,'a+')
    f.write("\n######################################################################\n")
    f.write("Executing Create Project Folder tool...\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("User Parameters:\n")
    f.write("\tAdmin State Selected: " + sourceState + "\n")
    f.write("\tAdmin County Selected: " + sourceCounty + "\n")
    f.write("\tTract Entered: " + str(tractNumber) + "\n")
    f.write("\tOverwrite CLU: " + str(owFlag) + "\n")
    f.close
    del f

## ===============================================================================================================
#### Import system modules
import sys, string, os, traceback, re, uuid
import datetime, shutil
import arcpy
from importlib import reload
sys.dont_write_bytecode=True
scriptPath = os.path.dirname(sys.argv[0])
sys.path.append(scriptPath)

import extract_CLU_by_Tract
reload(extract_CLU_by_Tract)


#### Inputs
arcpy.AddMessage("Reading inputs...\n")
projectType = arcpy.GetParameterAsText(0)
existingFolder = arcpy.GetParameterAsText(1)
#sourceLUT = arcpy.GetParameterAsText(2)
#stateFld = arcpy.GetParameterAsText(3)
sourceState = arcpy.GetParameterAsText(4)
#countyFld = arcpy.GetParameterAsText(5)
sourceCounty = arcpy.GetParameterAsText(6)
tractNumber = arcpy.GetParameterAsText(7)
owFlag = arcpy.GetParameter(8)
map_name = arcpy.GetParameterAsText(11)
specific_sr = arcpy.GetParameterAsText(12)


#### Update Environments
arcpy.AddMessage("Setting Environments...\n")

# Test for Pro project.
try:
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    m = aprx.listMaps("Determinations")[0]
except:
    arcpy.AddError("\nThis tool must be run from an active ArcGIS Pro project that was developed from the template distributed with this toolbox. Exiting...\n")
    exit()

# Check for a projected, WGS 1984 UTM coordinate system for the Determinations map
mapSR = m.spatialReference
if mapSR.type != "Projected":
    arcpy.AddError("\nThe Determinations map is not set to a Projected coordinate sytsem.")
    arcpy.AddError("\nPlease assign a WGS 1984 UTM coordinate system to the Determinations map that is appropriate for your site.")
    arcpy.AddError("\nThese systems are found in the Determinations Map Properties under: Coordinate Systems -> Projected Coordinate System -> UTM -> WGS 1984.")
    arcpy.AddError("\nAfter applying a coordinate system, save your template and try this tool again.")
    arcpy.AddError("\nExiting...")
    exit()

if "1984" not in mapSR.name:
    arcpy.AddError("\nThe Determinations map is not using a projected coordinate system tied to WGS 1984.")
    arcpy.AddError("\nPlease assign a WGS 1984 UTM coordinate system to the Determinations map that is appropriate for your site.")
    arcpy.AddError("\nThese systems are found in the Determinations Map Properties under: Coordinate Systems -> Projected Coordinate System -> UTM -> WGS 1984.")
    arcpy.AddError("\nAfter applying a coordinate system, save your template and try this tool again.")
    arcpy.AddError("\nExiting...")
    exit()

if "WGS" not in mapSR.name:
    arcpy.AddError("\nThe Determinations map is not using coordinate system tied to WGS 1984.")
    arcpy.AddError("\nPlease assign a WGS 1984 UTM coordinate system to the Determinations map that is appropriate for your site.")
    arcpy.AddError("\nThese systems are found in the Determinations Map Properties under: Coordinate Systems -> Projected Coordinate System -> UTM -> WGS 1984.")
    arcpy.AddError("\nAfter applying a coordinate system, save your template and try this tool again.")
    arcpy.AddError("\nExiting...")
    exit()


if "UTM" not in mapSR.name:
    arcpy.AddError("\nThe Determinations map is not using a UTM coordinate system.")
    arcpy.AddError("\nPlease assign a WGS 1984 UTM coordinate system to the Determinations map that is appropriate for your site.")
    arcpy.AddError("\nThese systems are found in the Determinations Map Properties under: Coordinate Systems -> Projected Coordinate System -> UTM -> WGS 1984.")
    arcpy.AddError("\nAfter applying a coordinate system, save your template and try this tool again.")
    arcpy.AddError("\nExiting...")
    exit()

# Set output Pro map
if map_name != '':
    activeMap = aprx.listMaps(map_name)[0]
else:
    activeMap = aprx.activeMap

# Set output spatial reference
if specific_sr != '':
    sr = arcpy.SpatialReference()
    sr.loadFromString(specific_sr)
    outSpatialRef = sr
else:
    try:
        activeMapName = activeMap.name
        activeMapSR = activeMap.getDefinition('V2').spatialReference['latestWkid']
        outSpatialRef = arcpy.SpatialReference(activeMapSR)
    except:
        arcpy.AddError("Could not get a spatial reference! Please run the tool from the Catalog Pane with an active ArcGIS Pro Map open! Exiting...")
        exit()

arcpy.env.outputCoordinateSystem = outSpatialRef

# Set transformation (replace with assignment from Transformation lookup from cim object of active map object in the future)
arcpy.env.geographicTransformations = "WGS_1984_(ITRF00)_To_NAD_1983"

# Set overwrite flag
arcpy.env.overwriteOutput = True

# Update the default aprx workspace to be the installed SCRATCH.gdb in case script validation didn't work or wasn't set
aprx.defaultGeodatabase = os.path.join(os.path.dirname(sys.argv[0]), "SCRATCH.gdb")


#### Check GeoPortal Connection
nrcsPortal = 'https://gis.sc.egov.usda.gov/portal/'
portalToken = extract_CLU_by_Tract.getPortalTokenInfo(nrcsPortal)
if not portalToken:
    arcpy.AddError("Could not generate Portal token! Please login to GeoPortal! Exiting...")
    exit()

        
#### Main procedures
try:
    #### Set up initial project folder paths based on input choice for project Type
    workspacePath = r'C:\Determinations'
    
    # Check Inputs for existence and create FIPS code variables
    lut = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "lut_census_fips")
    if not arcpy.Exists(lut):
        arcpy.AddError("Could not find state and county lookup table! Exiting...\n")
        exit()

    # Search for FIPS codes to give to the Extract CLU Tool/Function. Break after the first row (should only find one row in any case).
    stfip, cofip = '', ''
    fields = ['STATEFP','COUNTYFP','NAME','STATE','STPOSTAL']
    field1 = 'STATE'
    field2 = 'NAME'
    expression = "{} = '{}'".format(arcpy.AddFieldDelimiters(lut,field1), sourceState) + " AND " + "{} = '{}'".format(arcpy.AddFieldDelimiters(lut,field2), sourceCounty)
    with arcpy.da.SearchCursor(lut, fields, where_clause = expression) as cursor:
        for row in cursor:
            stfip = row[0]
            cofip = row[1]
            adStatePostal = row[4]
            break

    if len(stfip) != 2 and len(cofip) != 3:
        arcpy.AddError("State and County FIPS codes could not be retrieved! Exiting...\n")
        exit()

    if adStatePostal == '':
        arcpy.AddError("State postal code could not be retrieved! Exiting...\n")
        exit()
        
    # Transfer found values to variables to use for CLU download and project creation.
    adminState = stfip
    adminCounty = cofip
    postal = adStatePostal.lower()

    # Get the current year and month for use in project naming
    current = datetime.datetime.now()
    curyear = current.year
    curmonth = current.month
    theyear = str(curyear)
    themonth = str(curmonth)

    # Refine the tract number and month number to be padded with zeros to create uniform length of project name
    sourceTract = str(tractNumber)
    tractlength = len(sourceTract)
    if tractlength < 7:
        addzeros = 7 - tractlength
        tractname = '0'*addzeros + str(sourceTract)
    else:
        tractname = sourceTract

    monthlength = len(themonth)
    if monthlength < 2:
        finalmonth = '0' + themonth
    else:
        finalmonth = themonth

    # Build project folder path
    if projectType == "New":
        projectFolder = workspacePath + os.sep + postal + adminCounty + "_t" + tractname + "_" + theyear + "_" + finalmonth
        
    else:
        # Get project folder path from user input. Validation was done during script validations on the input
        if existingFolder != '':
            projectFolder = existingFolder
        else:
            arcpy.AddError('Project type was specified as Existing, but no existing project folder was selected. Exiting...')
            exit()

    #### Set additional variables based on constructed path
    folderName = os.path.basename(projectFolder)
    projectName = folderName
    basedataGDB_name = os.path.basename(projectFolder).replace(" ","_") + "_BaseData.gdb"
    basedataGDB_path = projectFolder + os.sep + basedataGDB_name     
    basedataFD = basedataGDB_path + os.sep + "Layers"
    outputWS = basedataGDB_path
    templateCLU = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "master_clu")
    cluTempName = "CLU_Temp_" + projectName
    projectCLUTemp = basedataFD + os.sep + cluTempName
    cluName = "Site_CLU"
    projectCLU = basedataFD + os.sep + cluName
    projectTract = basedataFD + os.sep + "Site_Tract"
##    projectTractB = basedataFD + os.sep + "Site_Tract_Buffer"
##    bufferDist = "500 Feet"
##    bufferDistPlus = "550 Feet"
##    projectAOI = basedataFD + os.sep + "Site_AOI"
    DAOIname = "Site_Define_AOI"
    projectDAOI = basedataFD + os.sep + DAOIname
##    helFolder = projectFolder + os.sep + "HEL"
##    helGDB_name = folderName + "_HEL.gdb"
##    helGDB_path = helFolder + os.sep + helGDB_name
##    hel_fd = helGDB_path + os.sep + "HEL_Data"
    wetlandsFolder = projectFolder + os.sep + "Wetlands"
    wetDir = wetlandsFolder
    wcGDB_name = folderName + "_WC.gdb"
    wcGDB_path = wetlandsFolder + os.sep + wcGDB_name
    wcFD = wcGDB_path + os.sep + "WC_Data"
##    docs_folder = projectFolder + os.sep + "Doc_Templates"
##    doc028 = "NRCS-CPA-028.docx"
##    doc026h = "NRCS-CPA-026-HELC.docx"
##    doc026w = "NRCS-CPA-026-WC.docx"
##    doc026wp = "NRCS-CPA-026-WC-PJW.docx"
##    source_028 = os.path.join(os.path.dirname(sys.argv[0]), "AddIns" + os.sep + doc028)
##    source_026h = os.path.join(os.path.dirname(sys.argv[0]), "AddIns" + os.sep + doc026h)
##    source_026w = os.path.join(os.path.dirname(sys.argv[0]), "AddIns" + os.sep + doc026w)
##    source_026wp = os.path.join(os.path.dirname(sys.argv[0]), "AddIns" + os.sep + doc026wp)
##    target_028 = docs_folder + os.sep + doc028
##    target_026h = docs_folder + os.sep + doc026h
##    target_026w = docs_folder + os.sep + doc026w
##    target_026wp = docs_folder + os.sep + doc026wp

    # Job ID
    jobid = uuid.uuid4()

    # Map Layer Names
    cluOut = "Site_CLU"
    DAOIOut = "Site_Define_AOI"


    #### Create the project directory

    # Check if C:\Determinations exists, else create it
    arcpy.AddMessage("\nChecking project directories...")
    if not os.path.exists(workspacePath):
        try:
            os.mkdir(workspacePath)
            arcpy.AddMessage("\nThe Determinations folder did not exist on the C: drive and has been created.")
        except:
            arcpy.AddError("\nThe Determinations folder cannot be created. Please check your permissions to the C: drive. Exiting...\n")
            exit()
            
    # Check if C:\Determinations\projectFolder exists, else create it
    if not os.path.exists(projectFolder):
        try:
            os.mkdir(projectFolder)
            arcpy.AddMessage("\nThe project folder has been created within Determinations.")
        except:
            arcpy.AddError("\nThe project folder cannot be created. Please check your permissions to C:\Determinations. Exiting...\n")
            exit()


    #### Project folder now exists. Set up log file path and start logging
    textFilePath = projectFolder + os.sep + folderName + "_log.txt"
    logBasicSettings()


    #### Continue creating sub-directories
    # Check if the Wetlands folder exists within the projectFolder, else create it
    if not os.path.exists(wetlandsFolder):
        try:
            os.mkdir(wetlandsFolder)
            AddMsgAndPrint("\nThe Wetlands folder has been created within " + projectFolder + ".",0)
        except:
            AddMsgAndPrint("\nCould not access C:\Determinations. Check your permissions for C:\Determinations. Exiting...\n",2)
            exit()
            
##    # Check if the HEL folder exists within the projectFolder, else create it
##    if not os.path.exists(helFolder):
##        try:
##            os.mkdir(helFolder)
##            AddMsgAndPrint("\n\tThe HEL folder has been created within " + projectFolder + ".",0)
##        except:
##            AddMsgAndPrint("\nCould not access C:\Determinations. Check your permissions for C:\Determinations. Exiting...\n",2)
##            exit()
##    else:
##        AddMsgAndPrint("\n\tThe HEL folder already exists within " + projectFolder + ".",0)
##
##
##    #### Copy the file templates from the install folder to the project directory
##    # This is done to make the install folder location indepedent on a given computer
##    # Check if the Doc_Templates folder exists within the projectFolder, else create it
##    if not os.path.exists(docs_folder):
##        try:
##            os.mkdir(docs_folder)
##            AddMsgAndPrint("\n\tThe Doc_Templates folder has been created within " + projectFolder + ".",0)
##        except:
##            AddMsgAndPrint("\nCould not access C:\Determinations. Check your permissions for C:\Determinations. Exiting...\n",2)
##            sys.exit()
##        try:
##            shutil.copy2(source_028, target_028)
##            shutil.copy2(source_026h, target_026h)
##            shutil.copy2(source_026w, target_026w)
##            shutil.copy2(source_026wp, target_026wp)
##            AddMsgAndPrint("\n\tThe 026 form templates have been copied to the Doc_Templates folder within " + projectFolder + ".",0)
##        except:
##            AddMsgAndPrint("\nCould not copy 026 form templates. Please make sure they are closed and try again. Exiting...\n",2)
##            sys.exit()
##    else:
##        # Make sure the .docx template files are in the Doc_Templates folder
##        if not os.path.exists(target_028):
##            shutil.copy2(source_028, target_028)
##        if not os.path.exists(target_026h):
##            shutil.copy2(source_026h, target_026h)
##        if not os.path.exists(target_026w):
##            shutil.copy2(source_026w, target_026w)
##        if not os.path.exists(target_026wp):
##            shutil.copy2(source_026wp, target_026wp)
##        AddMsgAndPrint("\n\tThe Doc_Templates folder already exists within " + projectFolder + ".",0)
##
##    AddMsgAndPrint("\nFolder: " + projectFolder + " and its contents have been created and/or updated within C:\Determinations!\n",1)


    #### If project geodatabases and feature datasets do not exist, create them.
    # BaseData
    if not arcpy.Exists(basedataGDB_path):
        AddMsgAndPrint("\nCreating Base Data geodatabase...",0)
        arcpy.CreateFileGDB_management(projectFolder, basedataGDB_name, "10.0")

    if not arcpy.Exists(basedataFD):
        AddMsgAndPrint("\nCreating Base Data feature dataset...",0)
        arcpy.CreateFeatureDataset_management(basedataGDB_path, "Layers", outSpatialRef)

    # Wetlands
    if not arcpy.Exists(wcGDB_path):
        AddMsgAndPrint("\nCreating Wetlands geodatabase...",0)
        arcpy.CreateFileGDB_management(wetlandsFolder, wcGDB_name, "10.0")

    if not arcpy.Exists(wcFD):
        AddMsgAndPrint("\nCreating Wetlands feature dataset...",0)
        arcpy.CreateFeatureDataset_management(wcGDB_path, "WC_Data", outSpatialRef)
        
##    # HEL
##    if not arcpy.Exists(helGDB_path):
##        AddMsgAndPrint("\nCreating HEL geodatabase...",0)
##        arcpy.CreateFileGDB_management(helFolder, helGDB_name, "10.0")
##
##    if not arcpy.Exists(hel_fd):
##        AddMsgAndPrint("\nCreating HEL feature dataset...",0)
##        arcpy.CreateFeatureDataset_management(helGDB_path, "HEL_Data", outSpatialRef)


    #### Add or validate the attribute domains for the geodatabases
    AddMsgAndPrint("\nChecking attribute domains of wetlands geodatabase...",0)

    # Wetlands Domains
    descGDB = arcpy.Describe(wcGDB_path)
    domains = descGDB.domains

##    if not "CWD Status" in domains:
##        cwdTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_cwd_status")
##        arcpy.TableToDomain_management(cwdTable, "Code", "Description", wcGDB_path, "CWD Status", "Choices for wetland determination status", "REPLACE")
##        arcpy.AlterDomain_management(wcGDB_path, "CWD Status", "", "", "DUPLICATE")
##    if not "Data Form" in domains:
##        dataTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_data_form")
##        arcpy.TableToDomain_management(dataTable, "Code", "Description", wcGDB_path, "Data Form", "Choices for data form completion", "REPLACE")
##        arcpy.AlterDomain_management(wcGDB_path, "Data Form", "", "", "DUPLICATE")
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
##    if not "ROP Status" in domains:
##        ropTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_rop_status")
##        arcpy.TableToDomain_management(ropTable, "Code", "Description", wcGDB_path, "ROP Status", "Choices for ROP status", "REPLACE")
##        arcpy.AlterDomain_management(wcGDB_path, "ROP Status", "", "", "DUPLICATE")
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

##    # HEL Domains
##    descGDB = arcpy.Describe(helGDB_path)
##    domains = descGDB.domains
##
##    if not "Yes No" in domains:
##        yesnoTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_yesno")
##        arcpy.TableToDomain_management(yesnoTable, "Code", "Description", helGDB_path, "Yes No", "Yes or no options", "REPLACE")
##    if not "HEL Type" in domains:
##        helTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_hel")
##        arcpy.TableToDomain_management(helTable, "Code", "Description", helGDB_path, "HEL Type", "Choices for HEL label", "REPLACE")
##    if not "HEL Request Type" in domains:
##        helreqTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_hel_request_type")
##        arcpy.TableToDomain_management(helreqTable, "Code", "Description", helGDB_path, "HEL Request Type", "Choice for HEL request form", "REPLACE")
##
##    del descGDB, domains


    #### Remove the existing projectCLU layer from the Map
    AddMsgAndPrint("\nRemoving CLU layer from project maps, if present...\n",0)
    mapLayersToRemove = [cluOut, DAOIOut]
    try:
        for maps in aprx.listMaps():
            for lyr in maps.listLayers():
                if lyr.name in mapLayersToRemove:
                    maps.removeLayer(lyr)
    except:
        pass

    
    #### If overwrite was selected, delete everything and start over
    if owFlag == True:
        AddMsgAndPrint("\nOverwrite selected. Deleting all existing project data...",0)
        if arcpy.Exists(basedataFD):
            ws = arcpy.env.workspace
            arcpy.env.workspace = basedataGDB_path
            fcs = arcpy.ListFeatureClasses(feature_dataset="Layers")
            for fc in fcs:
                try:
                    path = os.path.join(basedataFD, fc)
                    arcpy.Delete_management(path)
                except:
                    pass
            arcpy.Delete_management(basedataFD)
            arcpy.CreateFeatureDataset_management(basedataGDB_path, "Layers", outSpatialRef)
            arcpy.env.workspace = ws
            del ws
            

    #### Download the CLU
    # If the CLU doesn't exist, download it
    if not arcpy.Exists(projectCLU):
        AddMsgAndPrint("\nDownloading latest CLU data for input tract number...",0)
        # Download CLU
        cluTempPath = extract_CLU_by_Tract.start(adminState, adminCounty, tractNumber, outSpatialRef, basedataGDB_path)

        # Convert feature class to the projectTempCLU layer in the project's feature dataset
        # This should work because the input CLU feature class coming from the download should have the same spatial reference as the target feature dataset
        arcpy.FeatureClassToFeatureClass_conversion(cluTempPath, basedataFD, cluTempName)

        # Delete the temporary CLU download
        arcpy.Delete_management(cluTempPath)

        # Add state name and county name fields to the projectTempCLU feature class
        # Add fields
        arcpy.AddField_management(projectCLUTemp, "job_id", "TEXT", "128")
        arcpy.AddField_management(projectCLUTemp, "admin_state_name", "TEXT", "64")
        arcpy.AddField_management(projectCLUTemp, "admin_county_name", "TEXT", "64")
        arcpy.AddField_management(projectCLUTemp, "state_name", "TEXT", "64")
        arcpy.AddField_management(projectCLUTemp, "county_name", "TEXT", "64")

        # Search the downloaded CLU for geographic state and county codes
        stateCo, countyCo = '', ''
        if sourceState == "Alaska":
            field_names = ['state_ansi_code','county_ansi_code']
        else:
            field_names = ['state_code','county_code']
        with arcpy.da.SearchCursor(projectCLUTemp, field_names) as cursor:
            for row in cursor:
                stateCo = row[0]
                countyCo = row[1]
                break
                                       
        # Search for names using FIPS codes.
        stName, coName = '', ''
        fields = ['STATEFP','COUNTYFP','NAME','STATE']
        field1 = 'STATEFP'
        field2 = 'COUNTYFP'
        expression = "{} = '{}'".format(arcpy.AddFieldDelimiters(lut,field1), stateCo) + " AND " + "{} = '{}'".format(arcpy.AddFieldDelimiters(lut,field2), countyCo)
        with arcpy.da.SearchCursor(lut, fields, where_clause = expression) as cursor:
            for row in cursor:
                coName = row[2]
                stName = row[3]
                break

        if stName == '' or coName == '':
            arcpy.AddError("State and County Names for the site could not be retrieved! Exiting...\n")
            exit()

        # Use Update Cursor to populate all rows of the downloaded CLU the same way for the new fields
        field_names = ['job_id','admin_state_name','admin_county_name','state_name','county_name']
        with arcpy.da.UpdateCursor(projectCLUTemp, field_names) as cursor:
            for row in cursor:
                row[0] = jobid
                row[1] = sourceState
                row[2] = sourceCounty
                row[3] = stName
                row[4] = coName
                cursor.updateRow(row)
        del field_names

        # If the state is Alaska, update the admin_county FIPS and county_code FIPS from the county_ansi_code field
        if sourceState == "Alaska":
            field_names = ['admin_county','county_code','county_ansi_code']
            with arcpy.da.UpdateCursor(projectCLUTemp, field_names) as cursor:
                for row in cursor:
                    row[0] = row[2]
                    row[1] = row[2]
                    cursor.updateRow(row)
            del field_names
        
        # Create the projectCLU feature class and append projectCLUTemp to it. This is done as a cheat to using field mappings to re-order fields.
        AddMsgAndPrint("\nWriting Site CLU layer...",0)
        arcpy.CreateFeatureclass_management(basedataFD, cluName, "POLYGON", templateCLU)
        arcpy.Append_management(projectCLUTemp, projectCLU, "NO_TEST")
        arcpy.Delete_management(projectCLUTemp)

    
    #### Create the Tract layer by dissolving the CLU layer.
    # If the Tract layer doesn't exist, create it
    if not arcpy.Exists(projectTract):
        AddMsgAndPrint("\nCreating Tract data...",0)

        dis_fields = ['job_id','admin_state','admin_state_name','admin_county','admin_county_name','state_code','state_name','county_code','county_name','farm_number','tract_number']
        arcpy.Dissolve_management(projectCLU, projectTract, dis_fields, "", "MULTI_PART", "")
        del dis_fields

##        # Always re-create the buffered areas if you have updated the tract
##        arcpy.Buffer_analysis(projectTract, projectTractB, bufferDist, "FULL", "", "ALL", "")
##        arcpy.Buffer_analysis(projectTract, projectAOI, bufferDistPlus, "FULL", "", "ALL", "")
##
##    # If the tract exists, but the buffer doesn't, re-create both buffers. Overwrite flag applies to the 2nd one.
##    if not arcpy.Exists(projectTractB):
##        arcpy.Buffer_analysis(projectTract, projectTractB, bufferDist, "FULL", "", "ALL", "")
##        arcpy.Buffer_analysis(projectTract, projectAOI, bufferDistPlus, "FULL", "", "ALL", "")


    #### Create the Site Define AOI layer as a copy of the CLU layer
    if not arcpy.Exists(projectDAOI):
        AddMsgAndPrint("\nCreating the Site Define AOI layer...",0)
        arcpy.FeatureClassToFeatureClass_conversion(projectCLU, basedataFD, DAOIname)
    if owFlag == True:
        AddMsgAndPrint("\nCLU overwrite was selected. Resetting the Site Define AOI layer to match...",0)
        arcpy.FeatureClassToFeatureClass_conversion(projectCLU, basedataFD, DAOIname)


    #### Zoom to tract (move out of code and into Tasks for the process)


    #### Prepare to add to map
    if not arcpy.Exists(cluOut):
        arcpy.SetParameterAsText(9, projectCLU)
    if not arcpy.Exists(DAOIOut):
        arcpy.SetParameterAsText(10, projectDAOI)

    
    #### Compact FGDB
    try:
        AddMsgAndPrint("\nCompacting File Geodatabase..." ,0)
        arcpy.Compact_management(basedataGDB_path)
        arcpy.Compact_management(wcGDB_path)
##        arcpy.Compact_management(helGDB_path)
        AddMsgAndPrint("\tSuccessful",0)
    except:
        pass

except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested. Exiting...")

except:
    errorMsg()
