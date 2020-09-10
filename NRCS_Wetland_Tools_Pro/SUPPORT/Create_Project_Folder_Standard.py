## ==========================================================================================
## Name:    Create Project Folder
## Purpose: Create a wetland determination project folder in C:\Determinations. Download a
##          single CLU Tract specified by user inputs.
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
## Created: 9/9/2020
##
## ==========================================================================================
## Changes
## ==========================================================================================
##
## rev. 8/20/2020
## Start revisions of Create Project Folder ArcMap tool to National Wetlands Tool in ArcGIS Pro.
## Change CLU generation to use GeoPortal based web service and Extract CLU code by Adolfo Diaz.
## Change input parameters to use lookup table for states & counties downloaded from US Census.
## Change processing to use lookup table obtained from US Census for state and county names.
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
def getPortalTokenInfo(portalURL):
    try:
        # Returns the URL of the active Portal
        # i.e. 'https://gis.sc.egov.usda.gov/portal/'
        activePortal = arcpy.GetActivePortalURL()

        # {'SSL_enabled': False, 'portal_version': 6.1, 'role': '', 'organization': '', 'organization_type': ''}
        #portalInfo = arcpy.GetPortalInfo(activePortal)

        # targeted portal is NOT set as default
        if activePortal != portalURL:

               # List of managed portals
               managedPortals = arcpy.ListPortalURLs()

               # portalURL is available in managed list
               if activePortal in managedPortals:
                   AddMsgAndPrint("\nYour Active portal is set to: " + activePortal,2)
                   AddMsgAndPrint("Set your active portal and sign into: " + portalURL,2)
                   return False

               # portalURL must first be added to list of managed portals
               else:
                    AddMsgAndPrint("\nYou must add " + portalURL + " to your list of managed portals",2)
                    AddMsgAndPrint("Open the Portals Tab to manage portal connections",2)
                    AddMsgAndPrint("For more information visit the following ArcGIS Pro documentation:",2)
                    AddMsgAndPrint("https://pro.arcgis.com/en/pro-app/help/projects/manage-portal-connections-from-arcgis-pro.htm",1)
                    return False

        # targeted Portal is correct; try to generate token
        else:

            # Get Token information
            tokenInfo = arcpy.GetSigninToken()

            # Not signed in.  Token results are empty
            if not tokenInfo:
                AddMsgAndPrint("\nYou are not signed into: " + portalURL,2)
                return False

            # Token generated successfully
            else:
                return tokenInfo

    except:
        errorMsg()
        return False

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
# Import system modules
import sys, string, os, traceback
import urllib, re, time, json, random
import datetime, shutil
import arcpy


#### Update Environments
arcpy.AddMessage("Setting Environments...\n")


# Get spatial refrence of the Active Map and set the WKID as the env.outputCoordSystem.
# If the tool was launched from catalog view instead of the catalog pane, this will fail and the tool will exit.
aprx = arcpy.mp.ArcGISProject("CURRENT")
activeMap = aprx.activeMap

try:
    activeMapName = activeMap.name
    activeMapSR = activeMap.getDefinition('V2').spatialReference['latestWkid']
    outSpatialRef = arcpy.SpatialReference(activeMapSR)
    arcpy.env.outputCoordinateSystem = outSpatialRef

except:
    arcpy.AddError("Could not get a spatial reference! Please run the tool from an active Map! Exiting...")
    exit()


# Set transformation (replace with assignment from Transformation lookup from cim object of map frame in the future)
arpcy.env.geographicTransformations = "WGS_1984_(ITRF00)_To_NAD_1983"


# Set overwrite flag
arcpy.env.overwriteOutput = True


#### Check GeoPortal Connection
nrcsPortal = 'https://gis.sc.egov.usda.gov/portal/'
portalToken = getPortalTokenInfo(nrcsPortal)
if not portalToken:
    arcpy.AddError("Could not generate Portal token! Please login to GeoPortal! Exiting...")
    exit()

        
#### Main procedures
try:
    #### Inputs
    arcpy.AddMessage("Reading inputs...\n")
    #sourceLUT = arcpy.GetParameterAsText(0)
    #stateFld = arcpy.GetParameterAsText(1)
    sourceState = arcpy.GetParameterAsText(2)
    #countyFld = arcpy.GetParameterAsText(3)
    sourceCounty = arcpy.GetParameterAsText(4)
    tractNumber = arcpy.GetParameterAsText(5)
    owFlag = arcpy.GetParameter(5)


    #### Check Inputs for existence and create FIPS code variables
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


    #### Create additional variables for use in project naming.

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

    # Variables and project names
    workspacePath = r'C:\Determinations'
    projectFolder = workspacePath + os.sep + postal + adminCounty + "_t" + tractname + "_" + theyear + "_" + finalmonth
    folderName = os.path.basename(projectFolder)
    projectName = folderName
    basedataGDB_name = os.path.basename(projectFolder).replace(" ","_") + "_BaseData.gdb"
    basedataGDB_path = projectFolder + os.sep + basedataGDB_name
    basedataFD = basedataGDB_path + os.sep + "Layers"
    projectCLU = basedataFD + os.sep + "CLU_" + projectName
##    helFolder = projectFolder + os.sep + "HEL"
##    helGDB_name = folderName + "_HEL.gdb"
##    helGDB_path = helFolder + os.sep + helGDB_name
##    hel_fd = helGDB_path + os.sep + "HEL_Data"
    wetlandsFolder = projectFolder + os.sep + "Wetlands"
    wetDir = wetlandsFolder
    wcGDB_name = folderName + "_WC.gdb"
    wcGDB_path = wetlandsFolder + os.sep + wcGDB_name
    wc_fd = wcGDB_path + os.sep + "WC_Data"
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

    # ArcMap Layer Names
    cluOut = "CLU_" + projectName


    #### Create the project folder, file geodatabase, and standard contents of a starting project

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
        
    # Project folder now exists. Set up log file path and start logging
    textFilePath = projectFolder + os.sep + folderName + "_PTD.txt"
    logBasicSettings()

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
    
    # Check if the Wetlands folder exists within the projectFolder, else create it
    if not os.path.exists(wetlandsFolder):
        try:
            os.mkdir(wetlandsFolder)
            AddMsgAndPrint("\nThe Wetlands folder has been created within " + projectFolder + ".",0)
        except:
            AddMsgAndPrint("\nCould not access C:\Determinations. Check your permissions for C:\Determinations. Exiting...\n",2)
            exit()

##    # Copy the file templates from the install folder to the project directory
##    # This is done to make the install folder location indepedent on a given computer
##    # Check if the Doc_Templates folder exists within the projectFolder, else create it
##    if not os.path.exists(docs_folder):
##        try:
##            os.mkdir(docs_folder)
##            shutil.copy2(source_028, target_028)
##            shutil.copy2(source_026h, target_026h)
##            shutil.copy2(source_026w, target_026w)
##            shutil.copy2(source_026wp, target_026wp)
##            AddMsgAndPrint("\n\tThe Doc_Templates folder has been created within " + projectFolder + ".",0)
##        except:
##            AddMsgAndPrint("\nCould not access C:\Determinations. Check your permissions for C:\Determinations. Exiting...\n",2)
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


    # If overwrite was not selected, keep any previous datasets, otherwise create them
    if owFlag == False:
        if arcpy.Exists(basedataGDB_path):
            AddMsgAndPrint("\nBase Data geodatabase exists. Continuing...",0)
        else:
            # Create project file geodatabase
            AddMsgAndPrint("\nCreating new FGDB...",0)
            arcpy.CreateFileGDB_management(projectFolder, basedataGDB_name, "10.0")
            # Create base data Feature Dataset using spatial reference of starting Map
            arcpy.CreateFeatureDataset_management(basedataGDB_path, "Layers", outSpatialRef)

        # If Wetlands geodatabase and feature dataset do not exist, create them.
        if arcpy.Exists(wcGDB_path):
            if not arcpy.Exists(wc_fd):
                AddMsgAndPrint("\nCreating wetlands feature dataset in existing wetlands geodatabase...")
                arcpy.CreateFeatureDataset_management(wcGDB_path, "WC_Data", outSpatialRef)
        else:
            AddMsgAndPrint("\nCreating new wetlands database...",0)
            arcpy.CreateFileGDB_management(wetlandsFolder, wcGDB_name, "10.0")
            
            AddMsgAndPrint("\nCreating new wetlands feature dataset...",0)
            arcpy.CreateFeatureDataset_management(wcGDB_path, "WC_Data", outSpatialRef)

##        # If HEL geodatabase and feature dataset do not exist, create them.
##        if arcpy.Exists(helGDB_path):
##            if not arcpy.Exists(hel_fd):
##                AddMsgAndPrint("\nCreating HEL feature dataset in existing HEL geodatabase...")
##                arcpy.CreateFeatureDataset_management(helGDB_path, "HEL_Data", outSpatialRef)
##        else:
##            AddMsgAndPrint("\nCreating new HEL database...",0)
##            arcpy.CreateFileGDB_management(helFolder, helGDB_name, "10.0")
##
##            AddMsgAndPrint("\nCreating new HEL feature dataset...",0)
##            arcpy.CreateFeatureDataset_management(helGDB_path, "HEL_Data", outSpatialRef)

            
    
    else:
        # Remove the existing projectCLU lyaer from the Map
        if arcpy.Exists(cluOut):
            try:
                arcpy.Delete_management(cluOut)
            except:
                pass
        # Remove the existing projectCLU from the database
        if arcpy.Exists(





    descCLU = arcpy.Describe(sourceCLU)
    fdSR = descCLU.SpatialReference

    if owFlag == False:
        if arcpy.Exists(basedataGDB_path):
            AddMsgAndPrint("\nRetaining existing CLU datasets...",0)

        # If project geodatabase and feature dataset do not exist, create them.
        else:
            # Create project file geodatabase (specify 10.0 version as baseline for all possible 10.x systems)
            AddMsgAndPrint("\nDatabase does not exist. Creating new FGDB...",0)
            arcpy.CreateFileGDB_management(projectFolder, basedataGDB_name, "10.0")
            # Create base data Feature Dataset using spatial reference of input CLU
            arcpy.CreateFeatureDataset_management(basedataGDB_path, "Layers", fdSR)

            # Generate the CLU, Tract, and buffered tracts Data
            AddMsgAndPrint("\nCreating project CLU...",0)
            arcpy.Select_analysis(sourceCLU, projectCLU, tractExp)
            AddMsgAndPrint("\tSuccessful",0)

        # If wetlands geodatabase and feature dataset do not exist, create them.
        if arcpy.Exists(wcGDB_path):
            if not arcpy.Exists(wc_fd):
                arcpy.CreateFeatureDataset_management(wcGDB_path, "WC_Data", fdSR)
            AddMsgAndPrint("\nRetaining existing wetlands database...",0)
        else:
            AddMsgAndPrint("\nWetlands database does not exist. Creating new FGDB...",0)
            arcpy.CreateFileGDB_management(wetlandsFolder, wcGDB_name, "10.0")
            arcpy.CreateFeatureDataset_management(wcGDB_path, "WC_Data", fdSR)
            AddMsgAndPrint("\tSuccessful",0)
            
        # If HEL geodatabase and feature dataset do not exist, create them.
        if arcpy.Exists(helGDB_path):
            if not arcpy.Exists(hel_fd):
                arcpy.CreateFeatureDataset_management(helGDB_path, "HEL_Data", fdSR)
            AddMsgAndPrint("\nRetaining existing HEL database...",0)
        else:
            AddMsgAndPrint("\nHEL database does not exist. Creating new FGDB...",0)
            arcpy.CreateFileGDB_management(helFolder, helGDB_name, "10.0")
            arcpy.CreateFeatureDataset_management(helGDB_path, "HEL_Data", fdSR)
            AddMsgAndPrint("\tSuccessful",0)    
    
    if owFlag == True:
        # Remove the CLU Project Layer from ArcMap session
        if arcpy.Exists(cluOut):
            try:
                arcpy.Delete_management(cluOut)
            except:
                pass
            
        # Remove the datasets if the database exists
        if arcpy.Exists(basedataGDB_path):
            datasetsToRemove = [projectCLU]
            x = 0
            for dataset in datasetsToRemove:
                if arcpy.Exists(dataset):
                    # Strictly Formatting
                    if x < 1:
                        AddMsgAndPrint("\nRemoving old CLU datasets from Base Data GDB...",0)
                        x += 1
                    try:
                        arcpy.Delete_management(dataset)
                        AddMsgAndPrint("\tDeleting....." + os.path.basename(dataset),0)
                    except:
                        pass
            del dataset
            del datasetsToRemove
            del x

        # If project geodatabase and feature dataset do not exist, create them.
        else:
            # Create project file geodatabase (specify 10.0 version as baseline for all possible 10.x systems)
            AddMsgAndPrint("\nCreating new FGDB...",0)
            arcpy.CreateFileGDB_management(projectFolder, basedataGDB_name, "10.0")

            # Create base data Feature Dataset using spatial reference of input CLU
            arcpy.CreateFeatureDataset_management(basedataGDB_path, "Layers", fdSR)

        # Always generate the CLU, Tract, and buffered tracts Data in this loop because the original layers were deleted at the start of the if statement
        AddMsgAndPrint("\nCreating project CLU...",0)
        arcpy.Select_analysis(sourceCLU, projectCLU, tractExp)
        AddMsgAndPrint("\tSuccessful",0)

        # If wetlands geodatabase and feature dataset do not exist, create them.
        if arcpy.Exists(wcGDB_path):
            if not arcpy.Exists(wc_fd):
                arcpy.CreateFeatureDataset_management(wcGDB_path, "WC_Data", fdSR)
            AddMsgAndPrint("\nRetaining existing wetlands database...",0)
        else:
            AddMsgAndPrint("\nWetlands database does not exist. Creating new FGDB...",0)
            arcpy.CreateFileGDB_management(wetlandsFolder, wcGDB_name, "10.0")
            arcpy.CreateFeatureDataset_management(wcGDB_path, "WC_Data", fdSR)
            AddMsgAndPrint("\tSuccessful",0)
            
        # If HEL geodatabase and feature dataset do not exist, create them.
        if arcpy.Exists(helGDB_path):
            if not arcpy.Exists(hel_fd):
                arcpy.CreateFeatureDataset_management(helGDB_path, "HEL_Data", fdSR)
            AddMsgAndPrint("\nRetaining existing HEL database...",0)
        else:
            AddMsgAndPrint("\nHEL database does not exist. Creating new FGDB...",0)
            arcpy.CreateFileGDB_management(helFolder, helGDB_name, "10.0")
            arcpy.CreateFeatureDataset_management(helGDB_path, "HEL_Data", fdSR)
            AddMsgAndPrint("\tSuccessful",0)    


    # Validate the domains of the geodatabases
    AddMsgAndPrint("\nValidating Attribute Domains...",0)
    descGDB = arcpy.Describe(wcGDB_path)
    domains = descGDB.domains

    if not "YesNo" in domains:
        # Yes No Labels Domain
        ynTable = os.path.join(os.path.dirname(sys.argv[0]), "PTD_Master.gdb" + os.sep + "yesno_domain")
        arcpy.TableToDomain_management(ynTable, "Code", "Description", wcGDB_path, "YesNo", "Yes-No Labels", "REPLACE")
    if not "Eval" in domains:
        # Evaluation Area Labels Domain
        evalTable = os.path.join(os.path.dirname(sys.argv[0]), "PTD_Master.gdb" + os.sep + "eval_domain")
        arcpy.TableToDomain_management(evalTable, "Code", "Description", wcGDB_path, "Eval", "Evaluated Areas", "REPLACE")
    if not "WetLabels_2006" in domains:
        # FSA Labels Domain
        wetTable = os.path.join(os.path.dirname(sys.argv[0]), "PTD_Master.gdb" + os.sep + "wetlabels_domain")
        arcpy.TableToDomain_management(wetTable, "Code", "Description", wcGDB_path, "WetLabels_2006", "FSA Labels", "REPLACE")
    if not "Method" in domains:
        # Method Domain
        methodTable = os.path.join(os.path.dirname(sys.argv[0]), "PTD_Master.gdb" + os.sep + "method_domain")
        arcpy.TableToDomain_management(methodTable, "Code", "Description", wcGDB_path, "Method", "Determination Method", "REPLACE")
    if not "LineType" in domains:
        # Line Type Domain
        lineTable = os.path.join(os.path.dirname(sys.argv[0]), "PTD_Master.gdb" + os.sep + "linetype_domain")
        arcpy.TableToDomain_management(lineTable, "Code", "Description", wcGDB_path, "LineType", "Line Type", "REPLACE")
    if not "HEL_Type" in domains:
        # HEL Type Domain
        helTable = os.path.join(os.path.dirname(sys.argv[0]), "PTD_Master.gdb" + os.sep + "hel_domain")
        arcpy.TableToDomain_management(helTable, "Code", "Description", wcGDB_path, "HEL_Type", "HEL Type", "REPLACE")
    if not "Request_Type" in domains:
        # Form Domain
        formTable = os.path.join(os.path.dirname(sys.argv[0]), "PTD_Master.gdb" + os.sep + "form_domain")
        arcpy.TableToDomain_management(formTable, "Code", "Description", wcGDB_path, "Request_Type", "Request Type", "REPLACE")
    if not "ROP_Type" in domains:
        # ROP Type Domain
        ropTable = os.path.join(os.path.dirname(sys.argv[0]), "PTD_Master.gdb" + os.sep + "roptype_domain")
        arcpy.TableToDomain_management(ropTable, "Code", "Description", wcGDB_path, "ROP_Type", "ROP Type", "REPLACE")
    if not "SU_Flag" in domains:
        # SU Domain
        suTable = os.path.join(os.path.dirname(sys.argv[0]), "PTD_Master.gdb" + os.sep + "su_domain")
        arcpy.TableToDomain_management(suTable, "Code", "Description", wcGDB_path, "SU_Flag", "SU Flag", "REPLACE")

    del descGDB, domains

    descGDB = arcpy.Describe(helGDB_path)
    domains = descGDB.domains

    if not "YesNo" in domains:
        # Yes No Labels Domain
        ynTable = os.path.join(os.path.dirname(sys.argv[0]), "PTD_Master.gdb" + os.sep + "yesno_domain")
        arcpy.TableToDomain_management(ynTable, "Code", "Description", helGDB_path, "YesNo", "Yes-No Labels", "REPLACE")
    if not "Eval" in domains:
        # Evaluation Area Labels Domain
        evalTable = os.path.join(os.path.dirname(sys.argv[0]), "PTD_Master.gdb" + os.sep + "eval_domain")
        arcpy.TableToDomain_management(evalTable, "Code", "Description", helGDB_path, "Eval", "Evaluated Areas", "REPLACE")
    if not "WetLabels_2006" in domains:
        # FSA Labels Domain
        wetTable = os.path.join(os.path.dirname(sys.argv[0]), "PTD_Master.gdb" + os.sep + "wetlabels_domain")
        arcpy.TableToDomain_management(wetTable, "Code", "Description", helGDB_path, "WetLabels_2006", "FSA Labels", "REPLACE")
    if not "Method" in domains:
        # Method Domain
        methodTable = os.path.join(os.path.dirname(sys.argv[0]), "PTD_Master.gdb" + os.sep + "method_domain")
        arcpy.TableToDomain_management(methodTable, "Code", "Description", helGDB_path, "Method", "Determination Method", "REPLACE")
    if not "LineType" in domains:
        # Line Type Domain
        lineTable = os.path.join(os.path.dirname(sys.argv[0]), "PTD_Master.gdb" + os.sep + "linetype_domain")
        arcpy.TableToDomain_management(lineTable, "Code", "Description", helGDB_path, "LineType", "Line Type", "REPLACE")
    if not "HEL_Type" in domains:
        # HEL Type Domain
        helTable = os.path.join(os.path.dirname(sys.argv[0]), "PTD_Master.gdb" + os.sep + "hel_domain")
        arcpy.TableToDomain_management(helTable, "Code", "Description", helGDB_path, "HEL_Type", "HEL Type", "REPLACE")
    if not "Request_Type" in domains:
        # Form Domain
        formTable = os.path.join(os.path.dirname(sys.argv[0]), "PTD_Master.gdb" + os.sep + "form_domain")
        arcpy.TableToDomain_management(formTable, "Code", "Description", helGDB_path, "Request_Type", "Request Type", "REPLACE")
    if not "ROP_Type" in domains:
        # ROP Type Domain
        ropTable = os.path.join(os.path.dirname(sys.argv[0]), "PTD_Master.gdb" + os.sep + "roptype_domain")
        arcpy.TableToDomain_management(ropTable, "Code", "Description", helGDB_path, "ROP_Type", "ROP Type", "REPLACE")
    if not "SU_Flag" in domains:
        # SU Domain
        suTable = os.path.join(os.path.dirname(sys.argv[0]), "PTD_Master.gdb" + os.sep + "su_domain")
        arcpy.TableToDomain_management(suTable, "Code", "Description", helGDB_path, "SU_Flag", "SU Flag", "REPLACE")

    del descGDB, domains
    
    AddMsgAndPrint("\tSuccessful",0)    

    AddMsgAndPrint("\nBuffering tract...",0)
    projectTract = basedataFD + os.sep + "Tract_" + projectName
    projectTractB = basedataFD + os.sep + "Tract_Buffer_" + projectName
    projectAOI = basedataFD + os.sep + "AOI_" + projectName
    arcpy.Dissolve_management(projectCLU, projectTract, "", "", "MULTI_PART", "")
    arcpy.Buffer_analysis(projectTract, projectTractB, "0.25 Miles", "FULL", "", "ALL", "")
    arcpy.Buffer_analysis(projectTract, projectAOI, "0.30 Miles", "FULL", "", "ALL", "")
    AddMsgAndPrint("\tSuccessful",0)

    # Zoom to tract quarter mile buffer (To be implemented in Pro 2.5)
##    AddMsgAndPrint("\nZooming to tract...",0)
##    fc = projectCLU
##    arcpy.MakeFeatureLayer_management(fc, "CLUExtent")
##    mxd = arcpy.mapping.MapDocument("CURRENT")
##    df = arcpy.mapping.ListDataFrames(mxd)[0]
##    lyr = arcpy.mapping.Layer("CLUExtent")
##    df.extent = lyr.getExtent()
##    df.scale = df.scale * 1.1
##    arcpy.Delete_management("CLUExtent")
##    del fc, mxd, df, lyr
##    AddMsgAndPrint("\tSuccessful",0)

    # Prepare to Add to ArcMap
    if not arcpy.Exists(cluOut):
        arcpy.SetParameterAsText(3, projectCLU)
    
    # Compact FGDB
    try:
        AddMsgAndPrint("\nCompacting File Geodatabase..." ,0)
        arcpy.Compact_management(basedataGDB_path)
        arcpy.Compact_management(wcGDB_path)
        arcpy.Compact_management(helGDB_path)
        AddMsgAndPrint("\tSuccessful",0)
    except:
        pass

except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested....exiting")

except:
    errorMsg()
