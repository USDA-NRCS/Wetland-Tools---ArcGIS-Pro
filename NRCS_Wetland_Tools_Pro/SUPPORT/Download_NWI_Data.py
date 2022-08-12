## ===============================================================================================================
## Name:    Download NWI Data
## Purpose: Downloads NWI features from GeoPortal for all wetland types in the CLU (Tract) extent.
##
## Authors: Chris Morse
##          GIS Specialist
##          Indianapolis State Office
##          USDA-NRCS
##          chris.morse@usda.gov
##          317.295.5849
##
## Created: 05/03/2022
##
## ===============================================================================================================
## Changes
## ===============================================================================================================
##
## rev.
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
    f.write("Executing Dwonload NWI Data utility tool...\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
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

##  ===============================================================================================================
def queryIntersect(ws,temp_dir,fc,RESTurl,outFC):
##  This function uses a REST API query to retrieve geometry from that overlap an input feature class from a
##  hosted feature service.
##  Relies on a global variable of portalToken to exist and be active (checked before running this function)
##  ws is a file geodatabase workspace to store temp files for processing
##  fc is the input feature class. Should be a polygon feature class, but technically shouldn't fail if other types
##  RESTurl is the url for the query where the target hosted data resides
##  Example: """https://gis-testing.usda.net/server/rest/services/Hosted/CWD_Training/FeatureServer/0/query"""
##  outFC is the output feature class path/name that is return if the function succeeds AND finds data
##  Otherwise False is returned

    # Run the query
##    try:
    
    # Set variables
    query_url = RESTurl + "/query"
    jfile = temp_dir + os.sep + "jsonFile.json"
    wmas_fc = ws + os.sep + "wmas_fc"
    wmas_dis = ws + os.sep + "wmas_dis_fc"
    wmas_sr = arcpy.SpatialReference(3857)

    # Convert the input feature class to Web Mercator and to JSON
    arcpy.management.Project(fc, wmas_fc, wmas_sr)
    arcpy.management.Dissolve(wmas_fc, wmas_dis, "", "", "MULTI_PART", "")
    jsonPolygon = [row[0] for row in arcpy.da.SearchCursor(wmas_dis, ['SHAPE@JSON'])][0]

    # Setup parameters for query
    params = urllibEncode({'f': 'json',
                           'geometry':jsonPolygon,
                           'geometryType':'esriGeometryPolygon',
                           'spatialRelationship':'esriSpatialRelOverlaps',
                           'returnGeometry':'true',
                           'outFields':'*',
                           'token': portalToken['token']})


    INparams = params.encode('ascii')
    resp = urllib.request.urlopen(query_url,INparams)

    responseStatus = resp.getcode()
    responseMsg = resp.msg
    jsonString = resp.read()

    # json --> Python; dictionary containing 1 key with a list of lists
    results = json.loads(jsonString)

    # Check for error in results and exit with message if found.
    if 'error' in results.keys():
        if results['error']['message'] == 'Invalid Token':
            AddMsgAndPrint("\nSign-in token expired. Sign-out and sign-in to the portal again and then re-run. Exiting...",2)
            exit()
        else:
            AddMsgAndPrint("\nUnknown error encountered. Make sure you are online and signed in and that " + RESTurl + " is online. Exiting...",2)
            AddMsgAndPrint("\nResponse status code: " + str(responseStatus),2)
            exit()
    else:
        # Convert results to a feature class
        if not len(results['features']):
            return False
        else:
            with open(jfile, 'w') as outfile:
                json.dump(results, outfile)

            arcpy.conversion.JSONToFeatures(jfile, outFC)
            arcpy.management.Delete(jfile)
            arcpy.management.Delete(wmas_fc)
            arcpy.management.Delete(wmas_dis)
            return outFC

##        # Cleanup temp stuff from this function
##        files_to_del = [jfile, wmas_fc, wmas_dis]
##        for item in files_to_del:
##            try:
##                arcpy.management.Delete(item)
##            except:
##                pass

##    except httpErrors as e:
##        if int(e.code) >= 400:
##            AddMsgAndPrint("\nUnknown error encountered. Exiting...",2)
##            AddMsgAndPrint("\nHTTP Error = " + str(e.code),2)
##            errorMsg()
##            exit()
##        else:
##            errorMsg()
##            return False
            
## ===============================================================================================================
#### Import system modules
import arcpy, sys, os, traceback, re, shutil, csv
from importlib import reload
import urllib, time, json, random
from urllib.request import Request, urlopen
from urllib.error import HTTPError as httpErrors
urllibEncode = urllib.parse.urlencode
parseQueryString = urllib.parse.parse_qsl

sys.dont_write_bytecode=True
scriptPath = os.path.dirname(sys.argv[0])
sys.path.append(scriptPath)

import extract_CLU_by_Tract
reload(extract_CLU_by_Tract)


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


#### Check GeoPortal Connection
nrcsPortal = 'https://gis.sc.egov.usda.gov/portal/'
#nrcsPortal = 'https://gis-states.sc.egov.usda.gov/portal/'
#nrcsPortal = 'https://gis-testing.usda.net/portal/'
portalToken = extract_CLU_by_Tract.getPortalTokenInfo(nrcsPortal)
if not portalToken:
    arcpy.AddError("Could not generate Portal token! Please login to GeoPortal! Exiting...")
    exit()
    

#### Main procedures
try:
    #### Inputs
    arcpy.AddMessage("Reading inputs...\n")
    arcpy.SetProgressorLabel("Reading inputs...")
    sourceCLU = arcpy.GetParameterAsText(0)
    nwiURL = arcpy.GetParameterAsText(1)


    #### Initial Validations
    arcpy.AddMessage("Verifying inputs...\n")
    arcpy.SetProgressorLabel("Verifying inputs...")

    
    #### Set base path
    sourceCLU_path = arcpy.Describe(sourceCLU).CatalogPath
    if sourceCLU_path.find('.gdb') > 0 and sourceCLU_path.find('Determinations') > 0 and sourceCLU_path.find('Site_CLU') > 0:
        basedataGDB_path = sourceCLU_path[:sourceCLU_path.find('.gdb')+4]
    else:
        arcpy.AddError("\nSelected Site CLU layer is not from a Determinations project folder. Exiting...")
        exit()
        

    #### Define Variables
    arcpy.AddMessage("Setting variables...\n")
    arcpy.SetProgressorLabel("Setting variables...")
    supportGDB = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb")
    scratchGDB = os.path.join(os.path.dirname(sys.argv[0]), "SCRATCH.gdb")
    
    basedataGDB_name = os.path.basename(basedataGDB_path)
    basedataFD_name = "Layers"
    basedataFD = basedataGDB_path + os.sep + basedataFD_name
    userWorkspace = os.path.dirname(basedataGDB_path)
    projectName = os.path.basename(userWorkspace).replace(" ", "_")

    wetDir = userWorkspace + os.sep + "Wetlands"
    wcGDB_name = os.path.basename(userWorkspace).replace(" ", "_") + "_WC.gdb"
    wcGDB_path = wetDir + os.sep + wcGDB_name
    wcFD_name = "WC_Data"
    wcFD = wcGDB_path + os.sep + wcFD_name
    
    projectCLU = basedataFD + os.sep + "Site_CLU"
    projectTract = basedataFD + os.sep + "Site_Tract"
    NWI_name = "Site_NWI"
    projectNWI = basedataFD + os.sep + "Site_NWI"

    intNWI = basedataGDB_path + os.sep + "Intersected_NWI"
    
    # Temp layers list for cleanup at the start and at the end
    tempLayers = [intNWI]
    deleteTempLayers(tempLayers)


    #### Set up log file path and start logging
    arcpy.AddMessage("Commence logging...\n")
    arcpy.SetProgressorLabel("Commence logging...")
    textFilePath = userWorkspace + os.sep + projectName + "_log.txt"
    logBasicSettings()
    

    #### Remove existing layer from the Pro maps
    AddMsgAndPrint("\nRemoving NWI layer from project maps, if present...\n",0)
    arcpy.SetProgressorLabel("Removing NWI layer from project maps, if present...")
    
    # Set starting layers to be removed
    mapLayersToRemove = [NWI_name]
    
    # Remove the layers in the list
    try:
        for maps in aprx.listMaps():
            for lyr in maps.listLayers():
                if lyr.longName in mapLayersToRemove:
                    maps.removeLayer(lyr)
    except:
        pass


    #### Remove existing NWI layer from the geodatabase
    AddMsgAndPrint("\nRemoving NWI layer from project database, if present...\n",0)
    arcpy.SetProgressorLabel("Removing NWI layer from project database, if present...")
    
    # Set starting datasets to remove
    datasetsToRemove = [projectNWI]

    # Remove the datasets in the list
    for dataset in datasetsToRemove:
        if arcpy.Exists(dataset):
            try:
                arcpy.Delete_management(dataset)
            except:
                pass


    #### Create the NWI Layer
    AddMsgAndPrint("\nCreating NWI layer...",0)
    arcpy.SetProgressorLabel("Creating NWI layer...")

    query_results_fc = queryIntersect(scratchGDB,userWorkspace,projectCLU,nwiURL,intNWI)

    if arcpy.Exists(intNWI):
        # This section runs if any intersecting geometry is returned from the query
        AddMsgAndPrint("\tNWI data found within current Tract! Processing...",0)
        arcpy.SetProgressorLabel("NWI data found within current Tract! Processing...")

        nwi_count = int(arcpy.GetCount_management(query_results_fc).getOutput(0))
        if nwi_count > 0:
            # Confirm multi part to single part with results and create projectNWI in doing so.
            arcpy.MultipartToSinglepart_management(query_results_fc, projectNWI)
            arcpy.Delete_management(query_results_fc)
        else:
            AddMsgAndPrint("\tNo NWI data found! Finishing up...",0)
            arcpy.Delete_management(query_results_fc)

    else:
        AddMsgAndPrint("\tNo NWI data found! Finishing up...",0)
        arcpy.SetProgressorLabel("No NWI data found! Finishing up...")
        try:
            arcpy.management.Delete(query_results_fc)
        except:
            pass
    
    #### Clean up Temporary Datasets
    # Temporary datasets specifically from this tool
    deleteTempLayers(tempLayers)

    # Look for and delete anything else that may remain in the installed SCRATCH.gdb
    startWorkspace = arcpy.env.workspace
    arcpy.env.workspace = scratchGDB
    dss = []
    for ds in arcpy.ListDatasets('*'):
        dss.append(os.path.join(scratchGDB, ds))
    for ds in dss:
        if arcpy.Exists(ds):
            try:
                arcpy.Delete_management(ds)
            except:
                pass
    arcpy.env.workspace = startWorkspace
    del startWorkspace


    #### Add to map
    # Use starting reference layer files for the tool installation to add layer with automatic placement
    AddMsgAndPrint("\nAdding layers to the map...",0)
    arcpy.SetProgressorLabel("Adding layers to the map...")

    if arcpy.Exists(projectNWI):
        arcpy.SetParameterAsText(2, projectNWI)


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
