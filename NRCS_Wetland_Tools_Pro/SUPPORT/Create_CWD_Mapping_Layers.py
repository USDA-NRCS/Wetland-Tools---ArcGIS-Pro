## ===============================================================================================================
## Name:    Create CWD Mapping Layers
## Purpose: Create the Site_CLU_CWD, Site_Previous_CWD, Site_Previous_CLU_CWD layers and the 026 and 028 tables
##          that will be sent to subsequent tools for form creation and data uploads.
##
## Authors: Chris Morse
##          GIS Specialist
##          Indianapolis State Office
##          USDA-NRCS
##          chris.morse@usda.gov
##          317.295.5849
##
## Created: 04/05/2021
##
## ===============================================================================================================
## Changes
## ===============================================================================================================
##
## rev. 04/05/2021
## - Started updated from ArcMap NRCS Compliance Tools and the Validate WC Layer tool.
##
## rev. 09/21/2021
## - Updated messaging and cursor clean-up in memory
##
## rev. 02/08/2022
## - Added processing to create an alt 026 and 028 table summarized by wetland label and occurence year combos
##   and populated with comma separated lists of fields that have those labels and the total acres of it.
##
## rev. 02/18/2022
## - Added steps to create Request Points and CLU CWD Points layers for the project for use in later upload steps
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
    f.write("Executing Create CWD Mapping Layers tool...\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("User Parameters:\n")
    f.write("\tInput CWD Layer: " + str(sourceCWD) + "\n")
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


###### Check GeoPortal Connection
###nrcsPortal = 'https://gis.sc.egov.usda.gov/portal/'
##nrcsPortal = 'https://gis-testing.usda.net/portal/'
##portalToken = extract_CLU_by_Tract.getPortalTokenInfo(nrcsPortal)
##if not portalToken:
##    arcpy.AddError("Could not generate Portal token! Please login to GeoPortal! Exiting...")
##    exit()
    

#### Main procedures
try:
    #### Inputs
    arcpy.AddMessage("Reading inputs...\n")
    arcpy.SetProgressorLabel("Reading inputs...")
    sourceCWD = arcpy.GetParameterAsText(0)
    

    #### Initial Validations
    arcpy.AddMessage("Verifying inputs...\n")
    arcpy.SetProgressorLabel("Verifying inputs...")
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


    #### Define Variables
    arcpy.AddMessage("Setting variables...\n")
    arcpy.SetProgressorLabel("Setting variables...")
    supportGDB = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb")
    scratchGDB = os.path.join(os.path.dirname(sys.argv[0]), "SCRATCH.gdb")
    templateCWD = supportGDB + os.sep + "master_cwd"
    templatePJW = supportGDB + os.sep + "master_pjw"
    templateCLUCWD = supportGDB + os.sep + "master_clu_cwd"
    templatePrevCLUCWD = supportGDB + os.sep + "master_prev_clu_cwd"
    template026 = supportGDB + os.sep + "table_026"

    wetDir = os.path.dirname(wcGDB_path)
    userWorkspace = os.path.dirname(wetDir)
    projectName = os.path.basename(userWorkspace).replace(" ", "_")

    wcGDB_name = os.path.basename(userWorkspace).replace(" ", "_") + "_WC.gdb"
    wcGDB_path = wetDir + os.sep + wcGDB_name
    wcFD_name = "WC_Data"
    wcFD = wcGDB_path + os.sep + wcFD_name
    
    basedataGDB_path = userWorkspace + os.sep + projectName + "_BaseData.gdb"
    basedataGDB_name = os.path.basename(basedataGDB_path)
    basedataFD_name = "Layers"
    basedataFD = basedataGDB_path + os.sep + basedataFD_name

    cluName = "Site_CLU"
    defineName = "Site_Define_AOI"
    ropName = "Site_ROPs"
    refName = "Site_Reference_Points"
    drainName = "Site_Drainage_Lines"

    projectCLU = basedataGDB_path + os.sep + cluName

    projectTable = basedataGDB_path + os.sep + "Table_" + projectName
    wetDetTableName = "Admin_Table"
    wetDetTable = wcGDB_path + os.sep + wetDetTableName

    extentName = "Request_Extent"
    extentPtsName = "Request_Extent_Points"
    projectExtent = basedataFD + os.sep + extentName
    projectSum = basedataFD + os.sep + "Det_Summary_Areas"
    projectSumPts = basedataFD + os.sep + "Det_Summary_Points"
    
    suName = "Site_Sampling_Units"
    projectSU = wcFD + os.sep + suName
    
    cwdName = "Site_CWD"
    projectCWD = wcFD + os.sep + cwdName

    pjwName = "Site_PJW"
    projectPJW = wcFD + os.sep + pjwName

    cwdTopoName = "CWD_Topology"
    cwdTopo = wcFD + os.sep + cwdTopoName

    cluCwdName = "Site_CLU_CWD"
    cluCwdPtsName = "Site_CLU_CWD_Points"
    cluCWD = wcFD + os.sep + cluCwdName
    clucwd_multi = scratchGDB + os.sep + "clucwd_multi"
    clucwd_single = scratchGDB + os.sep + "clucwd_single"
    cluCWDpts = wcFD + os.sep + cluCwdPtsName
    
    prevCert = wcFD + os.sep + "Previous_CWD"
    psc_name = "Site_Previous_CWD"
    prevCertSite = wcFD + os.sep + psc_name
    pccsName = "Site_Previous_CLU_CWD"
    prevCluCertSite = wcFD + os.sep + pccsName
    pccs_multi = scratchGDB + "pccs_multi"
    pccs_single = scratchGDB + "pccs_single"
    prevAdmin = wcFD + os.sep + "Previous_Admin"
    prevAdminSite = wcFD + os.sep + "Site_Previous_Admin"
    updatedCert = wcFD + os.sep + "Updated_Cert"
    updatedAdmin = wcFD + os.sep + "Updated_Admin"

    name026_unsort = "CLU_CWD_026_unsorted"
    name026 = "CLU_CWD_026"
    name026_temp = "CLU_CWD_026_temp"
    name026_alt = "CLU_CWD_026_alt"
    cluCWD026_unsort = wcGDB_path + os.sep + name026_unsort
    cluCWD026 = wcGDB_path + os.sep + name026
    cluCWD026_temp = wcGDB_path + os.sep + name026_temp
    cluCWD026_alt = wcGDB_path + os.sep + name026_alt

    name028_unsort = "CLU_CWD_028_unsorted"
    name028 = "CLU_CWD_028"
    name028_temp = "CLU_CWD_028_temp"
    name028_alt = "CLU_CWD_028_alt"
    cluCWD028_unsort = wcGDB_path + os.sep + name028_unsort
    cluCWD028 = wcGDB_path + os.sep + name028
    cluCWD028_temp = wcGDB_path + os.sep + name028_temp
    cluCWD028_alt = wcGDB_path + os.sep + name028_alt

    excelAdmin = userWorkspace + os.sep + "Admin_Table.xlsx"
    excel026 = wetDir + os.sep + "CLU_CWD_026.xlsx"
    excel026_alt = wetDir + os.sep + "CLU_CWD_026_alt.xlsx"
    excel028 = wetDir + os.sep + "CLU_CWD_028.xlsx"
    excel028_alt = wetDir + os.sep + "CLU_CWD_028_alt.xlsx"

    # Temp layers list for cleanup at the start and at the end
    tempLayers = [clucwd_multi, clucwd_single, pccs_multi, pccs_single, cluCWD026_unsort, cluCWD028_unsort]
    deleteTempLayers(tempLayers)


    #### Set up log file path and start logging
    arcpy.AddMessage("Commence logging...\n")
    arcpy.SetProgressorLabel("Commence logging...")
    textFilePath = userWorkspace + os.sep + projectName + "_log.txt"
    logBasicSettings()

        
    #### Check Project Integrity
    AddMsgAndPrint("\nChecking project integrity...",0)
    arcpy.SetProgressorLabel("Checking project integrity...")

    # If project wetlands geodatabase and feature dataset do not exist, exit.
    if not arcpy.Exists(wcGDB_path):
        AddMsgAndPrint("\tInput Site CWD layer is not part of a wetlands tool project folder. Exiting...",2)
        exit()

    if not arcpy.Exists(wcFD):
        AddMsgAndPrint("\tInput Site CWD layer is not part of a wetlands tool project folder. Exiting...",2)
        exit()

    # Copy the administrative table into the wetlands database for use with the attribute rules during digitizing
    # Repeated in case enter project info was re-run in between steps.
    if not arcpy.Exists(wetDetTable):
        #arcpy.Delete_management(wetDetTable)
        arcpy.TableToTable_conversion(projectTable, wcGDB_path, wetDetTableName)


    #### Get the current job_id for use in processing
    fields = ['job_id']
    cursor = arcpy.da.SearchCursor(wetDetTable, fields)
    for row in cursor:
        cur_id = row[0]
        break
    del cursor, fields


    #### Remove existing layers from the map and database to be regenerated
    # Set layers to remove from the map
    AddMsgAndPrint("\nRemoving CLU_CWD related layers from project maps, if present...\n",0)
    arcpy.SetProgressorLabel("Removing map finishing layers, if present...")
    mapLayersToRemove = [cluCwdName, psc_name]
    clucwdAnnoString = "Site_CLU_CWD" + "Anno*"
    prevAnnoString = "Site_Previous_CLU_CWD" + "Anno*"
    anno_list = [clucwdAnnoString, prevAnnoString]
    for maps in aprx.listMaps():
        for anno in anno_list:
            for lyr in maps.listLayers(anno):
                mapLayersToRemove.append(lyr.name)
    removeLayers(mapLayersToRemove)
    del mapLayersToRemove, anno_list

    AddMsgAndPrint("\nRemoving CLU_CWD related layers from project database, if present...\n",0)
    datasetsToRemove = [cluCWD, prevCertSite]
    #toposToRemove = []
    wildcard = '*CLU_CWD*'
    wkspace = wcGDB_path
    removeFCs(datasetsToRemove, wildcard, wkspace)
    del datasetsToRemove, wildcard, wkspace
    
    
    #### Main data processing sequence
    ## Handle previously certified layers, if present.
    # Check for a previously certified layer and intersect it with CLUs to get a layer/table suitable for 028 maps and forms
    if arcpy.Exists(prevAdmin):
        AddMsgAndPrint("\nProcessing previously certified areas...\n",0)
        arcpy.SetProgressorLabel("Processing previous CWD areas...")
        if arcpy.Exists(updatedAdmin):
            # Use the updatedCert to create a previous certifications layer with current clu fields
            if arcpy.Exists(prevCluCertSite):
                arcpy.Delete_management(prevCluCertSite)
            arcpy.CreateFeatureclass_management(wcFD, pccsName, "POLYGON", templatePrevCLUCWD)
            arcpy.Intersect_analysis([projectCLU, updatedCert], pccs_multi, "NO_FID", "#", "INPUT")
            arcpy.MultipartToSinglepart_management(pccs_multi, pccs_single)
            arcpy.Append_management(pccs_single, prevCluCertSite, "NO_TEST")
        else:
            # Use the prevcert to create a previous certifications layer with current clu fields
            if arcpy.Exists(prevCluCertSite):
                arcpy.Delete_management(prevCluCertSite)
            arcpy.CreateFeatureclass_management(wcFD, pccsName, "POLYGON", templatePrevCLUCWD)
            arcpy.Intersect_analysis([projectCLU, prevCert], pccs_multi, "NO_FID", "#", "INPUT")
            arcpy.MultipartToSinglepart_management(pccs_multi, pccs_single)
            arcpy.Append_management(pccs_single, prevCluCertSite, "NO_TEST")

        # Update acres
        expression = "round(!Shape.Area@acres!,2)"
        arcpy.CalculateField_management(prevCluCertSite, "acres", expression, "PYTHON_9.3")
        del expression

        # Do summary stats to make an acres table for use with the 028
        AddMsgAndPrint("\nGenerating Previous_CLU_CWD summary tables...\n",0)
        arcpy.SetProgressorLabel("Generating Previous CWD summary tables...")
        case_fields = ["farm_number", "tract_number", "clu_number", "wetland_label", "occur_year","cert_date"]
        stats_fields = [['acres', 'SUM']]
        arcpy.Statistics_analysis(prevCluCertSite, cluCWD028_unsort, stats_fields, case_fields)
        # Sort the results
        sort_fields = [["clu_number", "ASCENDING"], ["wetland_label", "ASCENDING"]]
        arcpy.management.Sort(cluCWD028_unsort, cluCWD028, sort_fields)
        arcpy.management.Delete(cluCWD028_unsort)
        del sort_fields

        # Do summary stats to make an alternate table that combines fields with matching labels for the 028
        case_fields = ["farm_number", "tract_number", "wetland_label", "occur_year","cert_date"]
        stats_fields = [['clu_number','FIRST'],['acres', 'SUM']]
        arcpy.Statistics_analysis(prevCluCertSite, cluCWD028_unsort, stats_fields, case_fields)
        # Sort the results
        sort_fields = [["clu_number", "ASCENDING"], ["wetland_label", "ASCENDING"]]
        arcpy.management.Sort(cluCWD028_unsort, cluCWD028_temp, sort_fields)
        arcpy.management.Delete(cluCWD028_unsort)
        del sort_fields
        
        # Make a list of the labels in the new table
        alt_028_labels = []
        search_fields = ['wetland_label','occur_year']
        with arcpy.da.SearchCursor(cluCWD028_temp, search_fields) as cursor:
            for row in cursor:
                if row[1] is None:
                    value = row[0]
                else:
                    value = row[0] + row[1]
                if value not in alt_028_labels:
                    alt_028_labels.append(value)
        # Use the list of labels to search the previous data and create a dictionary of labels to clu fields
        dict_028_alt = {}            
        search_fields = ['clu_number','wetland_label','occur_year']
        for item in alt_028_labels:
            with arcpy.da.SearchCursor(prevCluCertSite, search_fields) as cursor:
                for row in cursor:
                    if row[2] is None:
                        value = row[1]
                    else:
                        value = row[1] + row[2]
                    if item == value:
                        # This row has a field with the wetland label + occur year being searched. Add it to the dictionary
                        # check if the item is in the dict keys already
                        if item in dict_028_alt.keys():
                            # label is in dictionary, check if clu field is already in dictionary for that label and add if not
                            if (item, row[2]) not in dict_028_alt.items():
                                #append the current row's field
                                dict_028_alt[item] = dict_028_alt[item] + ", " + row[0]
                        else:
                            # label not in keys yet, add key and first field
                            dict_028_alt[item] = row[0]
                            
        # Dictionary populated with all fields (values) that go with each label + occur year (key)
        # Examine the values in the dictionary and sort any sets of field numbers
        for key in dict_028_alt.keys():
            v = dict_028_alt[key]
            if ", " in v:
                split_list = v.split(", ")
                integer_list = sorted(list(map(int, split_list)))
                string_ints = [str(int) for int in integer_list]
                str_of_ints = ", ".join(string_ints)
                dict_028_alt[key]=str_of_ints
        
        # Transfer the new values back to the alt summary stats table (replace values in the clu_number field)
        arcpy.management.AddField(cluCWD028_temp, "clu_number", 'TEXT', '', '', 512)
        field_names = ['wetland_label','occur_year','clu_number']
        with arcpy.da.UpdateCursor(cluCWD028_temp, field_names) as cursor:
            for row in cursor:
                if row[1] is None:
                    value = row[0]
                else:
                    value = row[0] + row[1]
                row[2] = dict_028_alt[value]
                cursor.updateRow(row)

        # Convert the temp table to the final alt table, then delete the temp table
##        # Build field mapping for the conversion
##        fm = arcpy.FieldMap()
##        fms = arcpy.FieldMappings()
##        fm.addInputField(cluCWD028_temp, 'farm_number')
##        fm.addInputField(cluCWD028_temp, 'tract_number')
##        fm.addInputField(cluCWD028_temp, 'clu_number')
##        fm.addInputField(cluCWD028_temp, 'wetland_label')
##        fm.addInputField(cluCWD028_temp, 'occur_year')
##        fm.addInputField(cluCWD028_temp, 'cert_date')
##        fm.addInputField(cluCWD028_temp, 'FREQUENCY')
##        fm.addInputField(cluCWD028_temp, 'SUM_acres')
##        fms.addFieldMap(fm)
        # Convert the table
        field_mapping="farm_number \"Farm Number\" true true false 7 Text 0 0,First,#,CLU_CWD_028_temp,farm_number,0,7;tract_number \"Tract Number\" true true false 7 Text 0 0,First,#,CLU_CWD_028_temp,tract_number,0,7;clu_number \"clu_number\" true true false 512 Text 0 0,First,#,CLU_CWD_028_temp,clu_number,0,512;wetland_label \"Wetland Label\" true true false 12 Text 0 0,First,#,CLU_CWD_028_temp,wetland_label,0,12;occur_year \"Occurrence Year\" true true false 4 Text 0 0,First,#,CLU_CWD_028_temp,occur_year,0,4;FREQUENCY \"FREQUENCY\" true true false 4 Long 0 0,First,#,CLU_CWD_028_temp,FREQUENCY,-1,-1;SUM_acres \"SUM_acres\" true true false 8 Double 0 0,First,#,CLU_CWD_028_temp,SUM_acres,-1,-1"
        arcpy.TableToTable_conversion(cluCWD028_temp, wcGDB_path, name028_alt, fms)
        # Delete the temp table
        arcpy.management.Delete(cluCWD028_temp)
        

    ## Create the CLU CWD layer suitable for 026 maps and forms
    AddMsgAndPrint("\nCreating CLU_CWD Layer...\n",0)
    arcpy.SetProgressorLabel("Creating CLU CWD layer...")
        
    # Intersect the projectCLU and projectCWD layers
    if arcpy.Exists(cluCWD):
        arcpy.Delete_management(cluCWD)
    arcpy.CreateFeatureclass_management(wcFD, cluCwdName, "POLYGON", templateCLUCWD)
    arcpy.Intersect_analysis([projectCLU, projectCWD], clucwd_multi, "NO_FID", "#", "INPUT")
    arcpy.MultipartToSinglepart_management(clucwd_multi, clucwd_single)
    arcpy.Append_management(clucwd_single, cluCWD, "NO_TEST")

    # Update acres
    expression = "round(!Shape.Area@acres!,2)"
    arcpy.CalculateField_management(cluCWD, "acres", expression, "PYTHON_9.3")
    del expression

    # Do summary stats to make an acres table for use with the 026
    AddMsgAndPrint("\nGenerating CLU_CWD summary tables...\n",0)
    arcpy.SetProgressorLabel("Generating CLU CWD summary tables...")
    case_fields = ["farm_number","tract_number","clu_number", "wetland_label", "occur_year"]
    stats_fields = [['acres', 'SUM']]
    arcpy.Statistics_analysis(cluCWD, cluCWD026_unsort, stats_fields, case_fields)
    # Sort the results
    sort_fields = [["clu_number", "ASCENDING"], ["wetland_label", "ASCENDING"]]
    arcpy.management.Sort(cluCWD026_unsort, cluCWD026, sort_fields)
    arcpy.management.Delete(cluCWD026_unsort)
    del sort_fields

    # Do summary stats to make an alternate table that combines fields with matching labels for the 026
    case_fields = ["farm_number", "tract_number", "wetland_label", "occur_year"]
    stats_fields = [['clu_number','FIRST'],['acres', 'SUM']]
    arcpy.Statistics_analysis(cluCWD, cluCWD026_unsort, stats_fields, case_fields)
    # Sort the results
    sort_fields = [["FIRST_clu_number", "ASCENDING"], ["wetland_label", "ASCENDING"]]
    arcpy.management.Sort(cluCWD026_unsort, cluCWD026_temp, sort_fields)
    arcpy.management.Delete(cluCWD026_unsort)
    del sort_fields
    
    # Make a list of the labels in the new table
    alt_026_labels = []
    search_fields = ['wetland_label','occur_year']
    with arcpy.da.SearchCursor(cluCWD026_temp, search_fields) as cursor:
        for row in cursor:
            if row[1] is None:
                value = row[0]
            else:
                value = row[0] + row[1]
            if value not in alt_026_labels:
                alt_026_labels.append(value)
    # Use the list of labels to search the previous data and create a dictionary of labels to clu fields
    dict_026_alt = {}            
    search_fields = ['clu_number','wetland_label','occur_year']
    for item in alt_026_labels:
        with arcpy.da.SearchCursor(cluCWD, search_fields) as cursor:
            for row in cursor:
                if row[2] is None:
                    value = row[1]
                else:
                    value = row[1] + row[2]
                if item == value:
                    # This row has a field with the wetland label + occur year being searched. Add it to the dictionary
                    # check if the item is in the dict keys already
                    if item in dict_026_alt.keys():
                        # label is in dictionary, check if clu field is already in dictionary for that label and add if not
                        if (item, row[2]) not in dict_026_alt.items():
                            #append the current row's field
                            dict_026_alt[item] = dict_026_alt[item] + ", " + row[0]
                    else:
                        # label not in keys yet, add key and first field
                        dict_026_alt[item] = row[0]
                        
    # Dictionary populated with all fields (values) that go with each label + occur year (key)
    # Examine the values in the dictionary and sort any sets of field numbers
    for key in dict_026_alt.keys():
        v = dict_026_alt[key]
        if ", " in v:
            split_list = v.split(", ")
            integer_list = sorted(list(map(int, split_list)))
            string_ints = [str(int) for int in integer_list]
            str_of_ints = ", ".join(string_ints)
            dict_026_alt[key]=str_of_ints
                
    # Transfer the new values back to the alt summary stats table (replace values in the clu_number field)
    arcpy.management.AddField(cluCWD026_temp, "clu_number", 'TEXT', '', '', 512)
    field_names = ['wetland_label','occur_year','clu_number']
    with arcpy.da.UpdateCursor(cluCWD026_temp, field_names) as cursor:
        for row in cursor:
            if row[1] is None:
                value = row[0]
            else:
                value = row[0] + row[1]
            row[2] = dict_026_alt[value]
            cursor.updateRow(row)

    # Convert the temp table to the final alt table, then delete the temp table
##    # Build field mapping for the conversion
##    fm = arcpy.FieldMap()
##    fms = arcpy.FieldMappings()
##    fm.addInputField(cluCWD026_temp, 'farm_number')
##    fm.addInputField(cluCWD026_temp, 'tract_number')
##    fm.addInputField(cluCWD026_temp, 'clu_number')
##    fm.addInputField(cluCWD026_temp, 'wetland_label')
##    fm.addInputField(cluCWD026_temp, 'occur_year')
##    fm.addInputField(cluCWD026_temp, 'FREQUENCY')
##    fm.addInputField(cluCWD026_temp, 'SUM_acres')
##    fms.addFieldMap(fm)
    # Convert the table
    field_mapping="farm_number \"Farm Number\" true true false 7 Text 0 0,First,#,CLU_CWD_026_temp,farm_number,0,7;tract_number \"Tract Number\" true true false 7 Text 0 0,First,#,CLU_CWD_026_temp,tract_number,0,7;clu_number \"clu_number\" true true false 512 Text 0 0,First,#,CLU_CWD_026_temp,clu_number,0,512;wetland_label \"Wetland Label\" true true false 12 Text 0 0,First,#,CLU_CWD_026_temp,wetland_label,0,12;occur_year \"Occurrence Year\" true true false 4 Text 0 0,First,#,CLU_CWD_026_temp,occur_year,0,4;FREQUENCY \"FREQUENCY\" true true false 4 Long 0 0,First,#,CLU_CWD_026_temp,FREQUENCY,-1,-1;SUM_acres \"SUM_acres\" true true false 8 Double 0 0,First,#,CLU_CWD_026_temp,SUM_acres,-1,-1"
    arcpy.TableToTable_conversion(cluCWD026_temp, wcGDB_path, name026_alt, "", field_mapping)
    # Delete the temp table
    arcpy.management.Delete(cluCWD026_temp)
    
    # Update the extent characteristics of the Site_CLU_CWD layer
    arcpy.RecalculateFeatureClassExtent_management(cluCWD)
    

    #### Export Excel Tables to get ready for forms and letters tool.
    AddMsgAndPrint("\nExporting Excel table(s)...\n",0)
    arcpy.SetProgressorLabel("Exporting Excel table(s)...")
    if arcpy.Exists(excelAdmin):
        arcpy.Delete_management(excelAdmin)
    arcpy.TableToExcel_conversion(projectTable, excelAdmin)
    
    if arcpy.Exists(excel026):
        arcpy.Delete_management(excel026)
    arcpy.TableToExcel_conversion(cluCWD026, excel026)
    
    if arcpy.Exists(excel026_alt):
        arcpy.Delete_management(excel026_alt)
    arcpy.TableToExcel_conversion(cluCWD026_alt, excel026_alt)

    if arcpy.Exists(excel028):
        arcpy.Delete_management(excel028)
    if arcpy.Exists(cluCWD028):
        arcpy.TableToExcel_conversion(cluCWD028, excel028)

    if arcpy.Exists(excel028_alt):
        arcpy.Delete_management(excel028_alt)
    if arcpy.Exists(cluCWD028_alt):
        arcpy.TableToExcel_conversion(cluCWD028_alt, excel028_alt)


    #### Create determination summary polygon and points layer, as well as a points layer of the CLUCWD layer
    # Convert CLUCWD to points
    arcpy.management.FeatureToPoint(cluCWD, cluCWDpts, "INSIDE")
    
    # Use Dissolve to create project summary
    dissolve_fields = ['job_id','admin_state','admin_state_name','admin_county','admin_county_name','state_code','county_code','county_name','farm_number','tract_number','eval_status','dig_staff','dig_date']
    stats_fields = [['acres','SUM']]
    arcpy.management.Dissolve(cluCWD, projectSum, dissolve_fields, stats_fields, "MULTI_PART")
    
    # Convert project summary to points
    arcpy.management.FeatureToPoint(projectSum, projectSumPts, "INSIDE")

        
    #### Clean up Temporary Datasets
    # Temporary datasets specifically from this tool
    AddMsgAndPrint("\nCleaning up temporary data...",0)
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
    AddMsgAndPrint("\nAdding layers to the map...\n",0)
    arcpy.SetProgressorLabel("Adding layers to the map...")
    arcpy.SetParameterAsText(1, cluCWD)
    if arcpy.Exists(prevCertSite):
        arcpy.SetParameterAsText(2, prevCertSite)

    
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
