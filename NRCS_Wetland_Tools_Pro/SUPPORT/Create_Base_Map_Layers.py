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
## -Separated base map layer generation steps from Define Request Extent tool, to create this tool.
## -Added functions to create or reset layers on an individual basis, as specified by user input parameters.
## -Updated Sampling Unit creation process to blend New Request and Certified-Digital areas by downloading
##  existing digital SU data within the prevAdminSite layer extent.
##
## rev. 05/10/2021
## -Debugging passes to get replacement layers working
## -Change the way that layers are added to the map
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
def changeSource(cur_lyr, new_ws, new_fc):
    cp = cur_lyr.connectionProperties
    cp['connection_info']['database'] = new_ws
    cp['dataset'] = new_fc
    cur_lyr.updateConnectionProperties(cur_lyr.connectionProperties, cp)

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
    toposToRemove = [suTopo]
    wildcard = '*Sampling_Units*'
    wkspace = wcGDB_path
    removeFCs(datasetsToRemove, wildcard, wkspace, toposToRemove)
    del datasetsToRemove, wildcard, wkspace, toposToRemove

    arcpy.Compact_management(wcGDB_path)
    
            
    #### Create the Sampling Unit Layer
    AddMsgAndPrint("\nCreating the Sampling Units layer...\n",0)
    # Create an empty Sampling Unit feature class
    arcpy.CreateFeatureclass_management(wcFD, suNewName, "POLYGON", templateSU)

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

    # Incorporate existing sampling unit data if previous certifications fall within the request extent
    if arcpy.Exists(prevAdminSite):
        if arcpy.Exsists(existingSU):
            AddMsgAndPrint("\tDownloading previous Sampling Unit data...",0)
            # Download the existing sampling units data. Use intersect to update tract numbers.
            arcpy.Intersect_analysis([projectExtent, existingSU], prevSUmulti, "NO_FID", "#", "INPUT")
                    
            # Incorporate the certified areas into the current SU layer
            AddMsgAndPrint("\tIntegrating previous Sampling Unit data into new Sampling Unit layer...",0)
            arcpy.Clip_analysis(prevSUmulti, prevAdminSite, prevSUclip)
            arcpy.MultipartToSinglepart_management(prevSUclip, prevSU)
            arcpy.Erase_analysis(projectSUnew, prevAdminSite, suTemp4)
            arcpy.MultipartToSinglepart_management(suTemp4, suTemp5)
            arcpy.Delete_management(projectSU)
            arcpy.CreateFeatureclass_management(wcFD, suName, "POLYGON", templateSU)
            arcpy.Append_management(suTemp5, projectSU, "NO_TEST")
            arcpy.Append_management(prevSU, projectSU, "NO_TEST")


    #### Assign domains to the SU layer
    arcpy.AssignDomainToField_management(projectSUnew, "eval_status", "Evaluation Status")
    arcpy.AssignDomainToField_management(projectSUnew, "three_factors", "YN")
    arcpy.AssignDomainToField_management(projectSUnew, "request_type", "Request Type")
    arcpy.AssignDomainToField_management(projectSUnew, "deter_method", "Method")

    #### Update SU layer attributes
##    # job_id and eval_status are now inherited from the Extent layer

    # Update calculated acres
    expression = "!Shape.Area@acres!"
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

    # Rename to get final correct version of layer
    arcpy.Rename_management(projectSUnew, projectSU)


    #### Import attribute rules
    arcpy.ImportAttributeRules_management(projectSU, rules_su)

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

    arcpy.Compact_management(wcGDB_path)
    
            
    #### Create the ROPs Layer
    AddMsgAndPrint("\nCreating the ROPs layer...\n",0)
    arcpy.CreateFeatureclass_management(wcFD, ropName, "POINT", templateROP)

##    # Incorporate existing ROPs data if previous certifications fall within the request extent
##    if arcpy.Exists(prevAdminSite):
##        if arcpy.Exsists(existingROP):
##            AddMsgAndPrint("\tDownloading previous ROPs data...",0)
##            # Download the existing ROPs data. Use intersect to update tract numbers.
##            arcpy.Intersect_analysis([projectExtent, existingROP], prevROPs, "NO_FID", "#", "INPUT")
##            arcpy.Append_management(prevROPs, projectROPs, "NO_TEST")


    #### Import Attribute Rules
    arcpy.ImportAttributeRules_management(projectROP, rules_rops)
    
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
    arcpy.AssignDomainToField_management(projectREF, "hydro", "Yes No")
    arcpy.AssignDomainToField_management(projectREF, "veg", "Yes No")
    arcpy.AssignDomainToField_management(projectREF, "soil", "Yes No")


    #### Import attribute rules
    arcpy.ImportAttributeRules_management(projectREF, rules_refs)
    
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
    arcpy.ImportAttributeRules_management(projectLines, rules_lines)

## ===============================================================================================================
#### Import system modules
import arcpy, sys, os, traceback, re, shutil, csv
from importlib import reload
sys.dont_write_bytecode=True
scriptPath = os.path.dirname(sys.argv[0])
sys.path.append(scriptPath)

import extract_CLU_by_Tract
reload(extract_CLU_by_Tract)


#### Update Environments
arcpy.AddMessage("Setting Environments...\n")

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
portalToken = extract_CLU_by_Tract.getPortalTokenInfo(nrcsPortal)
if not portalToken:
    arcpy.AddError("Could not generate Portal token! Please login to GeoPortal! Exiting...")
    exit()
    

#### Main procedures
try:
    #### Inputs
    arcpy.AddMessage("Reading inputs...\n")
    sourceExtent = arcpy.GetParameterAsText(0)
    keepFields = arcpy.GetParameterAsText(1)
    resetSU = arcpy.GetParameterAsText(2)
    resetROPs = arcpy.GetParameterAsText(3)
    resetREF = arcpy.GetParameterAsText(4)
    resetDrains = arcpy.GetParameterAsText(5)
    existingSU = arcpy.GetParameterAsText(6)
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


##    #### Do not run if an unsaved edits exist in the target workspace
##    # Pro opens an edit session when any edit has been made and stays open until edits are committed with Save Edits.
##    # Check for uncommitted edits and exit if found, giving the user a message directing them to Save or Discard them.
##    workspace = basedataGDB_path
##    edit = arcpy.da.Editor(workspace)
##    if edit.isEditing:
##        arcpy.AddError("\nYou have an active edit session. Please Save or Discard Edits and then run this tool again. Exiting...")
##        exit()
##    del workspace, edit


    #### Define Variables
    arcpy.AddMessage("Setting variables...\n")
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
    prevSU = wcFD + os.sep + "Previous_Sampling_Units"

    ropName = "Site_ROPs"
    projectROP = wcFD + os.sep + ropName
##    prevROPs = wcFD + os.sep + "Previous_ROPs"

    refName = "Site_Reference_Points"
    projectREF = wcFD + os.sep + refName
##    prevREF = wcFD + os.sep + "Previous_Reference_Points"

    drainName = "Site_Drainage_Lines"
    projectLines = wcFD + os.sep + drainName
##    prevLines = wcFD + os.sep + "Previous_Drainage_Lines"

    extentName = "Request_Extent"
    projectExtent = basedataFD + os.sep + extentName
##    extTempName = "Extent_temp1_" + projectName
##    extentTemp1 = scratchGDB + os.sep + extTempName
##    extentTemp2 = scratchGDB + os.sep + "Extent_temp2_" + projectName
##    extentTemp3 = scratchGDB + os.sep + "Extent_temp3_" + projectName
##    tractTest = scratchGDB + os.sep + "Tract_Test_" + projectName

    suTopoName = "Sampling_Units_Topology"
    suTopo = wcFD + os.sep + suTopoName

    prevCert = wcFD + os.sep + "Previous_CWD"
    prevCertSite = wcFD + os.sep + "Site_Previous_CWD"
    prevCertMulti = scratchGDB + os.sep + "pCertMulti"
    prevCertTemp1 = scratchGDB + os.sep + "pCertTemp"
    prevAdmin = wcFD + os.sep + "Previous_Admin"
    prevAdminSite = wcFD + os.sep + "Site_Previous_Admin"
    updatedCert = wcFD + os.sep + "Updated_Cert"
    updatedAdmin = wcFD + os.sep + "Updated_Admin"
    
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
    tempLayers = [suMulti, suTemp1, suTemp2, suTemp3, suTemp4, suTemp5, prevSUmulti, prevSUclip, prevCertMulti, prevCertTemp1, projectSUnew]
    deleteTempLayers(tempLayers)


    #### Set up log file path and start logging
    arcpy.AddMessage("Commence logging...\n")
    textFilePath = userWorkspace + os.sep + projectName + "_log.txt"
    logBasicSettings()


    #### If project wetlands geodatabase and feature dataset do not exist, create them.
    # Get the spatial reference from the Define AOI feature class and use it, if needed
    AddMsgAndPrint("\nChecking project integrity...",0)
    desc = arcpy.Describe(sourceExtent)
    sr = desc.SpatialReference
    
    if not arcpy.Exists(wcGDB_path):
        AddMsgAndPrint("\tCreating Wetlands geodatabase...",0)
        arcpy.CreateFileGDB_management(wetDir, wcGDB_name, "10.0")

    if not arcpy.Exists(wcFD):
        AddMsgAndPrint("\tCreating Wetlands feature dataset...",0)
        arcpy.CreateFeatureDataset_management(wcGDB_path, "WC_Data", sr)

    # Copy the administrative table into the wetlands database for use with the attribute rules during digitizing
    if arcpy.Exists(wetDetTable):
        arcpy.Delete_management(wetDetTable)
    arcpy.TableToTable_conversion(projectTable, wcGDB_path, wetDetTableName)

    # Add or validate the attribute domains for the wetlands geodatabase
    AddMsgAndPrint("\tChecking attribute domains...",0)
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
    
    
    #### Create or Reset the Sampling Units layer
    if not arcpy.Exists(projectSU):
        createSU()
    if resetSU == "Yes":
        createSU()


    #### Create or Reset the ROPs Layer
    if not arcpy.Exists(projectROP):
        createROP()
    if resetROPs == "Yes":
        createROP()


    #### Create or Reset the Reference Points Layer
    if not arcpy.Exists(projectREF):
        createREF()
    if resetREF == "Yes":
        createREF()


    #### Create or Reset the Drainage Lines Layer
    if not arcpy.Exists(projectLines):
        createDRAIN()
    if resetDrains == "Yes":
        createDRAIN()


    #### Clean up Temporary Datasets
    # Temporary datasets specifically from this tool
    AddMsgAndPrint("\nCleaning up temporary data...",0)
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
