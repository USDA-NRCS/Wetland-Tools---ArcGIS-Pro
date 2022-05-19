## ===============================================================================================================
## Name:    Create Base Map Layers
## Purpose: Use the request extent to create sampling units, ROPs, Reference Points, and Drainage Lines layers,
##          including import of previously certified data where applicable.
##
## Authors: Chris Morse
##          GIS Specialist
##          Indianapolis State Office
##          USDA-NRCS
##          chris.morse@usda.gov
##          317.295.5849
##
## Created: 03/03/2021
##
## ===============================================================================================================
## Changes
## ===============================================================================================================
##
## rev. 03/03/2021
## - Separated base map layer generation steps from Define Request Extent tool, to create this tool.
## - Added functions to create or reset layers on an individual basis, as specified by user input parameters.
## - Updated Sampling Unit creation process to blend New Request and Certified-Digital areas by downloading
##   existing digital SU data within the origAdmin layer extent.
##
## rev. 05/10/2021
## - Debugging passes to get replacement layers working
## - Change the way that layers are added to the map
##
## rev. 02/18/2022
## - Replaced clip of overlapped existing data with download overlapped existing data from server
##
## rev. 02/22/2022
## - Replaced intersects with overlaps in query function.
##
## rev. 02/25/2022
## - Debugged query/download function and related file cleanup
##
## rev. 04/29/2022
## - Adjusted previous determination data workflows and corrected related bugs
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
    f.write("Executing Create Base Map Layers tool...\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("User Parameters:\n")
    f.write("\tRetain Field Lines?: " + str(keepFields) + "\n")
    f.write("\tReset Sampling Units?: " + str(resetSU) + "\n")
    f.write("\tReset ROPs?: " + str(resetROPs) + "\n")
    f.write("\tReset Reference Points?: " + str(resetREF) + "\n")
    f.write("\tReset Drainage Lines?: " + str(resetDrains) + "\n")
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
def createSU():
    #### Remove existing sampling unit related layers from the Pro maps
    AddMsgAndPrint("\nRemoving Sampling Unit related layers from project maps, if present...\n",0)

    # Remove attribute rules from the SU layer first
    if arcpy.Exists(projectSU):
        try:
            arcpy.DeleteAttributeRule_management(projectSU, rules_su_names)
        except:
            pass
        
    # Set sampling unit related layers to remove from the map
    mapLayersToRemove = [suName, suTopoName]

    # Find Sampling Unit related annotation layers to add to the list of map layers to be removed
    suAnnoString = "Site_Sampling_Units" + "Anno*"
    for maps in aprx.listMaps():
        for lyr in maps.listLayers(suAnnoString):
            mapLayersToRemove.append(lyr.name)

    # Remove the layers
    removeLayers(mapLayersToRemove)
    del mapLayersToRemove

    # Remove existing sampling unit layers from the geodatabase
    AddMsgAndPrint("\nRemoving Sampling Unit related layers from project database, if present...\n",0)
    datasetsToRemove = [projectSU]
##    toposToRemove = [suTopo]
    wildcard = '*Sampling_Units*'
    wkspace = wcGDB_path
    removeFCs(datasetsToRemove, wildcard, wkspace)
    del datasetsToRemove, wildcard, wkspace

    arcpy.Compact_management(wcGDB_path)
    
    #### Create the Sampling Unit Layer
    AddMsgAndPrint("\nCreating the Sampling Units layer...\n",0)
    # Create an empty Sampling Unit feature class
    arcpy.CreateFeatureclass_management(wcFD, suNewName, "POLYGON", templateSU)

    # Download existing sampling unit data if previous certifications exist
    if arcpy.Exists(origAdmin):
        
        # Download the existing sampling units data in the tract
        AddMsgAndPrint("\tDownloading previous Sampling Unit data...",0)

        query_url = suURL + "/query"
        query_results_fc = queryIntersect(scratchGDB,wetDir,projectExtent,query_url,intSU)

        if arcpy.Exists(intSU):
            AddMsgAndPrint("\tPrevious sampling units found within the request extent! Processing...",0)
            arcpy.SetProgressorLabel("Previous sampling units found within the request extent! Processing...")
            
            # Use intersect to update tract numbers.
            arcpy.Intersect_analysis([projectTract, query_results_fc], prevSUmulti, "NO_FID", "#", "INPUT")
            # Transer the job_id_1 attributes to the job_id field (continue to keep the original job IDs for now) and set Certified-Digital status
            fields = ['job_id','job_id_1','eval_status']
            cursor = arcpy.da.UpdateCursor(prevSUmulti, fields)
            for row in cursor:
                row[0] = row[1]
                row[2] = "Certified-Digital"
                cursor.updateRow(row)
            del fields
            del cursor
            
            # Trim the previous sampling units by the request extent
            AddMsgAndPrint("\tIntegrating previous Sampling Unit data into new Sampling Unit layer...",0)
            arcpy.Clip_analysis(prevSUmulti, projectExtent, prevSUclip)
            arcpy.MultipartToSinglepart_management(prevSUclip, prevSU)

            # Use erase on the projectExtent to reduce the area to be turned into sampling units
            arcpy.Erase_analysis(projectExtent, prevSU, extentTemp1)
            erased_results = int(arcpy.GetCount_management(extentTemp1).getOutput(0))
            if erased_results == 0:
                # Entire request extent filled by prevSU. Convert entire prevSU to the suNew layer.
                arcpy.Append_management(prevSU, projectSUnew, "NO_TEST")
            else:
                # Partial Extent of Previous and Partial New
                arcpy.Intersect_analysis([extentTemp1, projectCLU], suMulti, "NO_FID", "#", "INPUT")
                arcpy.MultipartToSinglepart_management(suMulti, suTemp1)

                if keepFields == "No":
                    dis_fields = ['job_id','admin_state','admin_state_name','admin_county','admin_county_name','state_code','state_name','county_code','county_name','farm_number','tract_number','eval_status']
                    arcpy.Dissolve_management(suTemp1, suTemp2, dis_fields, "", "SINGLE_PART", "")
                    arcpy.Append_management(suTemp2, projectSUnew, "NO_TEST")
                    arcpy.Append_management(prevSU, projectSUnew, "NO_TEST")
                else:
                    arcpy.Append_management(suTemp1, projectSUnew, "NO_TEST")
                    arcpy.Append_management(prevSU, projectSUnew, "NO_TEST")
        else:
            AddMsgAndPrint("\tNo previous sampling units found in online data! Continuing...",0)
            arcpy.SetProgressorLabel("No previous sampling units found in online data! Continuing...")

    else:
        # Create the SU layer by intersecting the Reqeust Extent with the CLU
        arcpy.Intersect_analysis([projectExtent, projectCLU], suMulti, "NO_FID", "#", "INPUT")
        arcpy.MultipartToSinglepart_management(suMulti, suTemp1)

        # Dissolve out field lines if that option was selected
        if keepFields == "No":
            dis_fields = ['job_id','admin_state','admin_state_name','admin_county','admin_county_name','state_code','state_name','county_code','county_name','farm_number','tract_number','eval_status']
            arcpy.Dissolve_management(suTemp1, suTemp2, dis_fields, "", "SINGLE_PART", "")
            arcpy.Append_management(suTemp2, projectSUnew, "NO_TEST")
        else:
            arcpy.Append_management(suTemp1, projectSUnew, "NO_TEST")


    #### Assign domains to the SU layer
    arcpy.AssignDomainToField_management(projectSUnew, "eval_status", "Evaluation Status")
    arcpy.AssignDomainToField_management(projectSUnew, "three_factors", "YN")
    arcpy.AssignDomainToField_management(projectSUnew, "request_type", "Request Type")
    arcpy.AssignDomainToField_management(projectSUnew, "deter_method", "Method")

    # Update calculated acres
    expression = "round(!Shape.Area@acres!,2)"
    arcpy.CalculateField_management(projectSUnew, "acres", expression, "PYTHON_9.3")
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
        cursor = arcpy.da.UpdateCursor(projectSUnew, fields)
        for row in cursor:
            if row[0] == "New Request" or row[0] == "Revision":
                row[1] = rDate
                row[2] = rType
                row[3] = detStaff
                row[4] = digStaff
                row[5] = digDate
            cursor.updateRow(row)
        del cursor, fields
    else:
        AddMsgAndPrint("\nCould not find project table. Rerun Enter Basic info. Exiting...",2)
        exit()

    # Rename to get final correct version of layer
    arcpy.Rename_management(projectSUnew, projectSU)

##    #### Import attribute rules
##    arcpy.ImportAttributeRules_management(projectSU, rules_su)

## ===============================================================================================================
def createROP():
    # Import ROPs will be a separate utility tool that appends features to existing ROP layer.
    #### Remove existing ROP related layers from the Pro maps
    AddMsgAndPrint("\nRemoving ROP related layers from project maps, if present...\n",0)

    # Remove attribute rules from the ROP layer first
    if arcpy.Exists(projectROP):
        try:
            arcpy.DeleteAttributeRule_management(projectROP, rules_rop_names)
        except:
            pass
        
    # Set ROP related layers to remove from the map
    mapLayersToRemove = [ropName]

    # Find ROP related annotation layers to add to the list of map layers to be removed
    ropAnnoString = "Site_ROPs" + "Anno*"
    for maps in aprx.listMaps():
        for lyr in maps.listLayers(ropAnnoString):
            mapLayersToRemove.append(lyr.name)

    # Remove the layers
    removeLayers(mapLayersToRemove)
    del mapLayersToRemove

    # Remove existing ROP layers from the geodatabase
    AddMsgAndPrint("\nRemoving ROP related layers from project database, if present...\n",0)
    datasetsToRemove = [projectROP]
    wildcard = '*ROPs*'
    wkspace = wcGDB_path
    removeFCs(datasetsToRemove, wildcard, wkspace)
    del datasetsToRemove, wildcard, wkspace


    #### Create the ROPs Layer
    AddMsgAndPrint("\nCreating the ROPs layer...\n",0)
    arcpy.CreateFeatureclass_management(wcFD, ropName, "POINT", templateROP)

##    # Check for existing ROP data if previous determinations are associated to the site and append them if found
##    if arcpy.Exists(origAdmin):
##
##        # Download ROPs
##        AddMsgAndPrint("\tDownloading previous ROPs data...",0)
##
##        query_url = ropURL + "/query"
##        query_results_fc = queryIntersect(scratchGDB,wetDir,projectExtent,query_url,intROP)
##
##        if arcpy.Exists(intROP):
##            AddMsgAndPrint("\tPrevious ROPs found within the request extent! Processing...",0)
##            arcpy.SetProgressorLabel("Previous ROPs found within the request extent! Processing...")
##
##            # Use intersect to update tract numbers.
##            arcpy.Intersect_analysis([projectTract, query_results_fc], prevROP, "NO_FID", "#", "INPUT")
##            result = int(arcpy.GetCount_management(prevROP).getOutput(0))
##            if result > 0:
##                # Transer the job_id_1 attributes to the job_id field (continue to keep the original job IDs for now)
##                fields = ['job_id','job_id_1']
##                cursor = arcpy.da.UpdateCursor(prevROP, fields)
##                for row in cursor:
##                    row[0] = row[1]
##                    cursor.updateRow(row)
##                del fields
##                del cursor
##
##                # Incorporate the certified areas into the current SU layer
##                AddMsgAndPrint("\tIntegrating previous ROPs data into new ROPs layer...",0)
##                arcpy.Clip_analysis(prevROP, origAdmin, prevROPclip)
##                clipped_results = int(arcpy.GetCount_management(prevROPclip).getOutput(0))
##                if clipped_results > 0:
##                    # ROPs found in the previous area, specifically. Append these to the ROPs layer
##                    arcpy.Append_management(prevROPclip, projectROP, "NO_TEST")
##                    arcpy.Delete_management(intROP)
##            else:
##                AddMsgAndPrint("\tNo previous ROPs found within request extent! Continuing...",0)
##                arcpy.SetProgressorLabel("No previous ROPs found within request extent! Continuing...")
##                arcpy.Delete_management(intROP)
##        else:
##            AddMsgAndPrint("\tNo previous ROPs found within request extent! Continuing...",0)
##            arcpy.SetProgressorLabel("No previous ROPs found within request extent! Continuing...")

##    #### Import Attribute Rules
##    arcpy.ImportAttributeRules_management(projectROP, rules_rops)
    
## ===============================================================================================================
def createREF():
    #### Remove existing Reference Points related layers from the Pro maps
    AddMsgAndPrint("\nRemoving Reference Point related layers from project maps, if present...\n",0)

    # Remove attribute rules from the REF layer first
    if arcpy.Exists(projectREF):
        try:
            arcpy.DeleteAttributeRule_management(projectREF, rules_ref_names)
        except:
            pass
        
    # Set Reference Points related layers to remove from the map
    mapLayersToRemove = [refName]

    # Find Reference Points related annotation layers to add to the list of map layers to be removed
    refAnnoString = "Site_Reference_Points" + "Anno*"
    for maps in aprx.listMaps():
        for lyr in maps.listLayers(refAnnoString):
            mapLayersToRemove.append(lyr.name)

    # Remove the layers
    removeLayers(mapLayersToRemove)
    del mapLayersToRemove

    # Remove existing Reference Points layers from the geodatabase
    AddMsgAndPrint("\nRemoving Reference Points related layers from project database, if present...\n",0)
    datasetsToRemove = [projectREF]
    wildcard = '*Reference_Points*'
    wkspace = wcGDB_path
    removeFCs(datasetsToRemove, wildcard, wkspace)
    del datasetsToRemove, wildcard, wkspace

    arcpy.Compact_management(wcGDB_path)
    
            
    #### Create the Reference Points Layer
    AddMsgAndPrint("\nCreating the Reference Points layer...\n",0)
    arcpy.CreateFeatureclass_management(wcFD, refName, "POINT", templateREF)


    #### Assign domains to the Reference Points layer
    AddMsgAndPrint("\nAssigning Domains to the Reference Points layer...\n",0)
    arcpy.AssignDomainToField_management(projectREF, "hydro", "Yes No")
    arcpy.AssignDomainToField_management(projectREF, "veg", "Yes No")
    arcpy.AssignDomainToField_management(projectREF, "soil", "Yes No")


    #### Import attribute rules
##    AddMsgAndPrint("\nImporting Attribute Rules to the Reference Points layer...\n",0)
##    arcpy.ImportAttributeRules_management(projectREF, rules_refs)
    
## ===============================================================================================================
def createDRAIN():
    #### Remove existing Drainage Lines related layers from the Pro maps
    AddMsgAndPrint("\nRemoving Drainage Lines related layers from project maps, if present...\n",0)

    # Remove attribute rules from the Drainage layer first
    if arcpy.Exists(projectLines):
        try:
            arcpy.DeleteAttributeRule_management(projectLines, rules_line_names)
        except:
            pass
        
    # Set Drainage Lines related layers to remove from the map
    mapLayersToRemove = [drainName]

    # Find Drainage Lines related annotation layers to add to the list of map layers to be removed
    drainAnnoString = "Site_Drainage_Lines" + "Anno*"
    for maps in aprx.listMaps():
        for lyr in maps.listLayers(drainAnnoString):
            mapLayersToRemove.append(lyr.name)

    # Remove the layers
    removeLayers(mapLayersToRemove)
    del mapLayersToRemove

    # Remove existing Drainage Lines layers from the geodatabase
    AddMsgAndPrint("\nRemoving Drainage Lines related layers from project database, if present...\n",0)
    datasetsToRemove = [projectLines]
    wildcard = '*Drainage_Lines*'
    wkspace = wcGDB_path
    removeFCs(datasetsToRemove, wildcard, wkspace)
    del datasetsToRemove, wildcard, wkspace

    arcpy.Compact_management(wcGDB_path)
    
            
    #### Create the Drainage Lines Layer
    AddMsgAndPrint("\nCreating the Drainage Lines layer...\n",0)
    arcpy.CreateFeatureclass_management(wcFD, drainName, "POLYLINE", templateLines)


    #### Assign domains to the Drainage Lines layer
    arcpy.AssignDomainToField_management(projectLines, "line_type", "Line Type")
    arcpy.AssignDomainToField_management(projectLines, "manip_era", "Pre Post")


    #### Import attribute rules
##    arcpy.ImportAttributeRules_management(projectLines, rules_lines)

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
            AddMsgAndPrint("\nUnknown error encountered. Make sure you are online and signed in and that the portal is online. Exiting...",2)
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
##            if arcpy.Exists(item):
##                arcpy.management.Delete(item)

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
#nrcsPortal = 'https://gis.sc.egov.usda.gov/portal/'
nrcsPortal = 'https://gis-testing.usda.net/portal/'
portalToken = extract_CLU_by_Tract.getPortalTokenInfo(nrcsPortal)
if not portalToken:
    arcpy.AddError("Could not generate Portal token! Please login to GIS Testing Portal! Exiting...")
    exit()
    

#### Main procedures
try:
    #### Inputs
    arcpy.AddMessage("Reading inputs...\n")
    arcpy.SetProgressorLabel("Reading inputs...")
    sourceExtent = arcpy.GetParameterAsText(0)
    keepFields = arcpy.GetParameterAsText(1)
    resetSU = arcpy.GetParameterAsText(2)
    resetROPs = arcpy.GetParameterAsText(3)
    resetREF = arcpy.GetParameterAsText(4)
    resetDrains = arcpy.GetParameterAsText(5)
    suURL = arcpy.GetParameterAsText(6)
    ropURL = arcpy.GetParameterAsText(7)
####    existingSU = arcpy.GetParameterAsText(6)
####    existingROP = arcpy.GetParameterAsText(7)
####    existingREF = arcpy.GetParameterAsText(8)
####    existingDRAIN = arcpy.GetParameterAsText(9)
##    suLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(7)).listLayers()[0]
##    ropLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(8)).listLayers()[0]
##    refLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(9)).listLayers()[0]
##    drainLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(10)).listLayers()[0]
    suLyr = arcpy.mp.LayerFile(os.path.join(os.path.dirname(sys.argv[0]), "layer_files") + os.sep + "Sampling_Units.lyrx").listLayers()[0]
    ropLyr = arcpy.mp.LayerFile(os.path.join(os.path.dirname(sys.argv[0]), "layer_files") + os.sep + "ROP.lyrx").listLayers()[0]
    refLyr = arcpy.mp.LayerFile(os.path.join(os.path.dirname(sys.argv[0]), "layer_files") + os.sep + "Reference_Points.lyrx").listLayers()[0]
    drainLyr = arcpy.mp.LayerFile(os.path.join(os.path.dirname(sys.argv[0]), "layer_files") + os.sep + "Drainage_Lines.lyrx").listLayers()[0]


    #### Initial Validations
    arcpy.AddMessage("Verifying inputs...\n")
    arcpy.SetProgressorLabel("Verifying inputs...")
    # If Extent layer has features selected, clear the selections so that all features from it are processed.
    clear_lyr = m.listLayers(sourceExtent)[0]
    arcpy.SelectLayerByAttribute_management(clear_lyr, "CLEAR_SELECTION")
    
                
    #### Set base path
    sourceExtent_path = arcpy.Describe(sourceExtent).CatalogPath
    if sourceExtent_path.find('.gdb') > 0 and sourceExtent_path.find('Determinations') > 0 and sourceExtent_path.find('Request_Extent') > 0:
        basedataGDB_path = sourceExtent_path[:sourceExtent_path.find('.gdb')+4]
    else:
        arcpy.AddError("\nSelected Request Extent layer is not from a Determinations project folder. Exiting...")
        exit()


    #### Define Variables
    arcpy.AddMessage("Setting variables...\n")
    arcpy.SetProgressorLabel("Setting variables...")
    supportGDB = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb")
    scratchGDB = os.path.join(os.path.dirname(sys.argv[0]), "SCRATCH.gdb")
    templateSU = supportGDB + os.sep + "master_sampling_units"
    templateROP = supportGDB + os.sep + "master_rop"
    templateREF = supportGDB + os.sep + "master_reference"
    templateLines = supportGDB + os.sep + "master_drainage_lines"
    #templateExtent = supportGDB + os.sep + "master_extent"
    
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
    #projectTractB = basedataFD + os.sep + "Site_Tract_Buffer"
    projectTable = basedataGDB_path + os.sep + "Table_" + projectName
    wetDetTableName = "Admin_Table"
    wetDetTable = wcGDB_path + os.sep + wetDetTableName
    projectAOI = basedataFD + os.sep + "project_AOI"
    projectAOI_B = basedataFD + os.sep + "project_AOI_B"
    projectDAOI = basedataFD + os.sep + "Site_Define_AOI"

    suName = "Site_Sampling_Units"
    projectSU = wcFD + os.sep + suName
    suNewName = "Site_Sampling_Units_New"
    projectSUnew = wcFD + os.sep + suNewName
    suMulti = scratchGDB + os.sep + "SU_Multi" + projectName
    suTemp1 = scratchGDB + os.sep + "SU_Temp1_" + projectName
    suTemp2 = scratchGDB + os.sep + "SU_Temp2_" + projectName
    suTemp3 = scratchGDB + os.sep + "SU_Temp3_" + projectName
    suTemp4 = scratchGDB + os.sep + "SU_Temp4_" + projectName
    suTemp5 = scratchGDB + os.sep + "SU_Temp5_" + projectName
    prevSUmulti = scratchGDB + os.sep + "prevSUmutli"
    prevSUclip = scratchGDB + os.sep + "prevSUclip"
    prevSU = scratchGDB + os.sep + "Previous_Sampling_Units"
    intSU = wcGDB_path + os.sep + "Intersected_SU"
    prevROP = scratchGDB + os.sep + "prevROP"
    prevROPclip = scratchGDB + os.sep + "prevROPclip"
    intROP = wcGDB_path + os.sep + "Intersected_ROP"

    ropName = "Site_ROPs"
    projectROP = wcFD + os.sep + ropName

    refName = "Site_Reference_Points"
    projectREF = wcFD + os.sep + refName

    drainName = "Site_Drainage_Lines"
    projectLines = wcFD + os.sep + drainName

    extentName = "Request_Extent"
    projectExtent = basedataFD + os.sep + extentName
    extentTemp1 = scratchGDB + os.sep + "Extent_temp1"

    suTopoName = "Sampling_Units_Topology"
    suTopo = wcFD + os.sep + suTopoName

    origCert = wcFD + os.sep + "Previous_CLU_CWD_Original"
    origAdmin = wcFD + os.sep + "Previous_CLU_CWD_Admin_Original"
    origAdminTemp = scratchGDB + os.sep + "OrigAdminTemp"
    
    prevCertName = "Site_Previous_CLU_CWD"
    prevCert = wcFD + os.sep + prevCertName
    prevAdmin = wcFD + os.sep + "Previous_Admin"
    
    # Attribute rule files and lists
    rules_su = os.path.join(os.path.dirname(sys.argv[0]), "Rules_SU.csv")
    rules_su_names = ['Update Acres', 'Add SU Job ID', 'Add SU Admin State', 'Add SU Admin State Name',
                      'Add SU Admin County', 'Add SU Admin County Name', 'Add SU State Code', 'Add SU State Name',
                      'Add SU County Code', 'Add SU County Name', 'Add SU Farm Number', 'Add SU Tract Number',
                      'Add Request Date', 'Add Request Type', 'Add Eval Status']
    rules_rops = os.path.join(os.path.dirname(sys.argv[0]), "Rules_ROPs.csv")
    rules_rop_names = ['Add ROP Admin State Code', 'Add ROP Admin State Name', 'Add ROP Admin County Code',
                       'Add ROP Admin County Name', 'Add ROP Job ID', 'Add ROP State Code', 'Add ROP State Name',
                       'Add ROP County Code', 'Add ROP County Name', 'Add ROP Farm Number', 'Add ROP Tract Number']
    rules_refs = os.path.join(os.path.dirname(sys.argv[0]), "Rules_REF.csv")
    rules_ref_names = ['Add RP Job ID', 'Add RP Admin State Code', 'Add RP Admin State Name', 'Add RP Admin County Code',
                       'Add RP Admin County Name', 'Add RP State Code', 'Add RP State Name', 'Add RP County Code',
                       'Add RP County Name', 'Add RP Farm Number', 'Add RP Tract Number', 'Set Default Hydro',
                       'Set Default Veg', 'Set Default Soil']
    rules_lines = os.path.join(os.path.dirname(sys.argv[0]), "Rules_Drains.csv")
    rules_line_names = ['Update Length', 'Add Drainage Job ID', 'Add Drainage Admin State Code', 'Add Drainage Admin State Name',
                        'Add Drainage Admin County Code', 'Add Drainage Admin County Name', 'Add Drainage State Code',
                        'Add Drainage State Name', 'Add Drainage County Code', 'Add Drainage County Name',
                        'Add Drainage Farm Number', 'Add Drainage Tract Number']

    # Temp layers list for cleanup at the start and at the end
    tempLayers = [suMulti, suTemp1, suTemp2, suTemp3, suTemp4, suTemp5, prevSU, prevSUmulti, prevSUclip, projectSUnew, intSU, intROP, prevROP, prevROPclip, extentTemp1]
    deleteTempLayers(tempLayers)


    #### Set up log file path and start logging
    arcpy.AddMessage("Commence logging...\n")
    arcpy.SetProgressorLabel("Commence logging...")
    textFilePath = userWorkspace + os.sep + projectName + "_log.txt"
    logBasicSettings()


    #### If project wetlands geodatabase and feature dataset do not exist, create them.
    # Get the spatial reference from the Define AOI feature class and use it, if needed
    AddMsgAndPrint("\nChecking project integrity...",0)
    arcpy.SetProgressorLabel("Checking project integrity...")
    desc = arcpy.Describe(sourceExtent)
    sr = desc.SpatialReference
    
    if not arcpy.Exists(wcGDB_path):
        AddMsgAndPrint("\tCreating Wetlands geodatabase...",0)
        arcpy.CreateFileGDB_management(wetDir, wcGDB_name, "10.0")

    if not arcpy.Exists(wcFD):
        AddMsgAndPrint("\tCreating Wetlands feature dataset...",0)
        arcpy.CreateFeatureDataset_management(wcGDB_path, "WC_Data", sr)

    # Copy the administrative table into the wetlands database for use with the attribute rules during digitizing
    if not arcpy.Exists(wetDetTable):
        arcpy.TableToTable_conversion(projectTable, wcGDB_path, wetDetTableName)

    # Add or validate the attribute domains for the wetlands geodatabase
    AddMsgAndPrint("\tChecking attribute domains...",0)
    arcpy.SetProgressorLabel("Checking attribute domains...")
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


    #### Remove any other project layers in the map that are found in the project's WC geodatabase to prevent locks while importing attributes.
    #### Layers will be re-added at the end of the process.
    mapLayersToRemove = [prevCertName]
    try:
        for maps in aprx.listMaps():
            for lyr in maps.listLayers():
                if lyr.name in mapLayersToRemove:
                    maps.removeLayer(lyr)
    except:
        pass

    
    #### Create or Reset the Sampling Units layer
    if not arcpy.Exists(projectSU):
        AddMsgAndPrint("\nCreating Sampling Units layer...\n",0)
        arcpy.SetProgressorLabel("Creating Sampling Units layer...")
        createSU()
        AddMsgAndPrint("\nImporting Attribute Rules to the Sampling Units layer...\n",0)
        arcpy.SetProgressorLabel("Importing Attribute Rules to the Sampling Units layer...")
        arcpy.ImportAttributeRules_management(projectSU, rules_su)
    if resetSU == "Yes":
        AddMsgAndPrint("\nCreating Sampling Units layer...\n",0)
        arcpy.SetProgressorLabel("Creating Sampling Units layer...")
        createSU()
        AddMsgAndPrint("\nImporting Attribute Rules to the Sampling Units layer...\n",0)
        arcpy.SetProgressorLabel("Importing Attribute Rules to the Sampling Units layer...")
        arcpy.ImportAttributeRules_management(projectSU, rules_su)


    #### Create or Reset the ROPs Layer
    if not arcpy.Exists(projectROP):
        AddMsgAndPrint("\nCreating ROPs layer...",0)
        arcpy.SetProgressorLabel("Creating ROPs layer...")
        createROP()
        AddMsgAndPrint("\nImporting Attribute Rules to the ROPs layer...\n",0)
        arcpy.SetProgressorLabel("Importing Attribute Rules to the ROPs layer...")
        arcpy.ImportAttributeRules_management(projectROP, rules_rops)
    if resetROPs == "Yes":
        AddMsgAndPrint("\nCreating ROPs layer...",0)
        arcpy.SetProgressorLabel("Creating ROPs layer...")
        createROP()
        AddMsgAndPrint("\nImporting Attribute Rules to the ROPs layer...\n",0)
        arcpy.SetProgressorLabel("Importing Attribute Rules to the ROPs layer...")
        arcpy.ImportAttributeRules_management(projectROP, rules_rops)


    #### Create or Reset the Reference Points Layer
    if not arcpy.Exists(projectREF):
        AddMsgAndPrint("\nCreating Reference Points layer...",0)
        arcpy.SetProgressorLabel("Creating Reference Points layer...")
        createREF()
        AddMsgAndPrint("\nImporting Attribute Rules to the Reference Points layer...\n",0)
        arcpy.SetProgressorLabel("Importing Attribute Rules to the Reference Points layer...")
        arcpy.ImportAttributeRules_management(projectREF, rules_refs)
    if resetREF == "Yes":
        AddMsgAndPrint("\nCreating Reference Points layer...",0)
        arcpy.SetProgressorLabel("Creating Reference Points layer...")
        createREF()
        AddMsgAndPrint("\nImporting Attribute Rules to the Reference Points layer...\n",0)
        arcpy.SetProgressorLabel("Importing Attribute Rules to the Reference Points layer...")
        arcpy.ImportAttributeRules_management(projectREF, rules_refs)


    #### Create or Reset the Drainage Lines Layer
    if not arcpy.Exists(projectLines):
        AddMsgAndPrint("\nCreating Drainage Lines layer...",0)
        arcpy.SetProgressorLabel("Creating Drainage Lines layer...")
        createDRAIN()
        AddMsgAndPrint("\nImporting Attribute Rules to the Drainage Lines layer...\n",0)
        arcpy.SetProgressorLabel("Importing Attribute Rules to the Drainage Lines layer...")
        arcpy.ImportAttributeRules_management(projectLines, rules_lines)
    if resetDrains == "Yes":
        AddMsgAndPrint("\nCreating Drainage Lines layer...",0)
        arcpy.SetProgressorLabel("Creating Drainage Lines layer...")
        createDRAIN()
        AddMsgAndPrint("\nImporting Attribute Rules to the Drainage Lines layer...\n",0)
        arcpy.SetProgressorLabel("Importing Attribute Rules to the Drainage Lines layer...")
        arcpy.ImportAttributeRules_management(projectLines, rules_lines)


    #### Clean up Temporary Datasets
    # Temporary datasets specifically from this tool
    AddMsgAndPrint("\nCleaning up temp data...",0)
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
    arcpy.SetProgressorLabel("Adding layers to the map...")
    
    lyr_list = m.listLayers()
    lyr_name_list = []
    for lyr in lyr_list:
        lyr_name_list.append(lyr.name)
        
    if suName not in lyr_name_list:
        suLyr_cp = suLyr.connectionProperties
        suLyr_cp['connection_info']['database'] = wcGDB_path
        suLyr_cp['dataset'] = suName
        suLyr.updateConnectionProperties(suLyr.connectionProperties, suLyr_cp)
        m.addLayer(suLyr)

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


    #### Re-add other business layers that are created previous to this point
    if arcpy.Exists(prevCert):
        arcpy.SetParameterAsText(8, prevCert)

    
    #### Adjust visibility of layers to aid in moving to the next step in the process
    # Turn off all CLUs/Common, Define_AOI, and Extent layers
    off_names = ["CLU","Common","Site_Define_AOI","Request_Extent"]
    for maps in aprx.listMaps():
        for lyr in maps.listLayers():
            for name in off_names:
                if name in lyr.name:
                    lyr.visible = False

    # Turn on the Site SU, ROP, Reference Points, and Drainage Lines layers
    on_names = [suName,drainName,refName,ropName]
    for maps in aprx.listMaps():
        for lyr in maps.listLayers():
            for name in on_names:
                if (lyr.name).startswith(name):
                    lyr.visible = True

    
    #### Compact FGDB
    try:
        AddMsgAndPrint("\nCompacting File Geodatabases...",0)
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
