## ===============================================================================================================
## Name:    Validate SU Topology
## Purpose: Verify that the user did not create an internal gaps or overlaps within the request extent.
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
## -Start revisions of Validate Topology ArcMap tool to National Wetlands Tool in ArcGIS Pro.
##
## rev. 11/18/2020
## -Check for internal gaps will have to be handled differently because SUs can go beyond extent/tract edges
##      -Use the outer edge of the extent layer itself in place of the tract layer.
##
## rev. 03/05/2021
## -Added enforcement of previous sampling units within previously certified areas unless marked for revision.
## -Areas marked for revision are updated to be revised sampling units within the current request extent.
## -Adjusted processing not alter the request extent
##      -Request Extent enforcement uses selection (or dissolve) of new request and revision types
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
    f.write("Executing Validate SU Topology tool...\n")
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
##    m.addLayer(extentLyr)
##        
##    suNew = m.listLayers("Site_Sampling_Units")[0]
##    ropNew = m.listLayers("Site_ROPs")[0]
##    extentNew = m.listLayers("Request_Extent")[0]
##
##    changeSource(suNew, new_ws=wcGDB_path, new_fd=wcFD_name, new_fc=suName)
##    changeSource(ropNew, new_ws=wcGDB_path, new_fd=wcFD_name, new_fc=ropName)
##    changeSource(extentNew, new_ws=basedataGDB_path, new_fd=basedataFD_name, new_fc=extentName)
##
##    suNew.name = suName
##    ropNew.name = ropName
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
    arcpy.AddError("\nThis tool must be run from a active ArcGIS Pro project that was developed from the template distributed with this toolbox. Exiting...\n")
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
    suLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(1))
    ropLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(2))
    #extentLyr = arcpy.mp.LayerFile(arcpy.GetParameterAsText(3))


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
        arcpy.AddError("\nSelected Samplint Units layer is not from a Determinations project folder. Exiting...")
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
    
    suName = "Site_Sampling_Units"
    projectSU = wcFD + os.sep + suName
    suTemp1 = wcFD + os.sep + "SU_Reference"
    suBackup = wcFD + os.sep + "suBackup1"
    
    ropName = "Site_ROPs"
    projectROP = wcFD + os.sep + ropName
    rop_Temp = wcFD + os.sep + "rop_temp"
    rop_Temp2 = wcFD + os.sep + "rop_temp2"
    
    extentName = "Request_Extent"
    projectExtent = basedataFD + os.sep + extentName
    extMulti = scratchGDB + os.sep + "Extent_temp_multi"
    extTempName = "Extent_temp1_" + projectName
    extentTemp1 = scratchGDB + os.sep + extTempName
    extentTemp2 = scratchGDB + os.sep + "Extent_temp2_" + projectName
    extentTemp3 = scratchGDB + os.sep + "Extent_temp3_" + projectName
    extBackup = basedataFD + os.sep + "extBackup1"
    extTemp = wcFD + os.sep + "Extent_Temp"

    suTopoName = "Sampling_Units_Topology"
    suTopo = wcFD + os.sep + suTopoName

    # Empty Topo Error Feature Classes
    linesTopoFC = wcFD + os.sep + "SU_Errors_line"
    pointsTopoFC = wcFD + os.sep + "SU_Errors_point"
    # Topo Error Polygon based rules feature class
    polysTopoFC = wcFD + os.sep + "SU_Errors_poly"

    # ArcPro Map Layer Names
    extentOut = "Request_Extent"
    suTopoOut = suTopoName
    suTempOut = "SU_Reference"
    extTempOut = "Extent_Temp"
    
##    # Annotation Layer Names (in map)
##    anno_list = []
##    suAnnoString = "Site_Sampling_Units" + "Anno*"
##    anno_list.append(suAnnoString)
    
    # Temp layers list for cleanup at the start and at the end
    tempLayers = [rop_Temp, rop_Temp2, extMulti, extentTemp1, extentTemp2, extentTemp3]
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


    #### Remove existing sampling unit related layers from the Pro maps
    AddMsgAndPrint("\nRemoving layers from project maps, if present...\n",0)
    
    # Set starting layers to be removed
    mapLayersToRemove = [extentOut, suTopoOut, suTempOut, extTempOut]

##    # Look for annotation related to the layers to be removed and append them to the mapLayersToRemove list
##    for maps in aprx.listMaps():
##        for name in anno_list:
##            for lyr in maps.listLayers(name):
##                mapLayersToRemove.append(lyr.name)
    
    # Remove the layers in the list
    try:
        for maps in aprx.listMaps():
            for lyr in maps.listLayers():
                if lyr.name in mapLayersToRemove:
                    maps.removeLayer(lyr)
    except:
        pass


    #### Remove existing sampling unit topology related layers from the geodatabase
    AddMsgAndPrint("\nRemoving layers from project database, if present...\n",0)

    # Remove topology first, if it exists
    toposToRemove = [suTopo]
    for topo in toposToRemove:
        if arcpy.Exists(topo):
            try:
                arcpy.Delete_management(topo)
            except:
                pass

    # Set starting datasets to remove
    datasetsToRemove = [suTemp1, extTemp]

    # Look for annotation datasets related to the datasets to be removed and delete them
    startWorkspace = arcpy.env.workspace
    arcpy.env.workspace = wcGDB_path
    fcs = []
    for fds in arcpy.ListDatasets('', 'feature') + ['']:
        for fc in arcpy.ListFeatureClasses('*Sampling_Units*', 'Annotation', fds):
            fcs.append(os.path.join(wcGDB_path, fds, fc))
    for fc in fcs:
        datasetsToRemove.append(fc)
    arcpy.env.workspace = startWorkspace
    del startWorkspace

    # Remove the datasets in the list
    for dataset in datasetsToRemove:
        if arcpy.Exists(dataset):
            try:
                arcpy.Delete_management(dataset)
            except:
                pass


    #### Backup the input Sampling Units and Extent layers
    AddMsgAndPrint("\nCreating pre-processing backups of input layers...",0)

    if arcpy.Exists(suBackup):
        arcpy.Delete_management(suBackup)
    arcpy.CopyFeatures_management(projectSU, suBackup)

    if arcpy.Exists(extBackup):
        arcpy.Delete_management(extBackup)
    arcpy.CopyFeatures_management(projectExtent, extBackup)


    #### If the sampling unit layer contains any Revision areas outside of the current Request Extent, update the Request Extent to add those areas
    AddMsgAndPrint("\nReviewing Sampling Unit layer for potential changes to the Request Extent...",0)
    
    # Make a feature layer from the sampling units and check it for any revision areas
    arcpy.MakeFeatureLayer_management(projectSU, "rev_su_temp")
    arcpy.SelectLayerByAttribute_management("rev_su_temp", "NEW_SELECTION", "\"eval_status\" = 'Revision'")
    result = int(arcpy.GetCount_management("rev_su_temp").getOutput(0))
    if result > 0:
        AddMsgAndPrint("\tRevision areas found. Checking their extent relative to the request extent...",0)
        if arcpy.Exists(suRev):
            arcpy.Delete_management(suRev)
        arcpy.CopyFeatures_management("rev_su_temp", suRev)
        arcpy.Delete_management("rev_su_temp")

        # Use erase on the new layer with the extent layer and check for remnant areas outside the original extent
        arcpy.Erase_analysis(suRev, projectExtent, extMulti)
        result = int(arcpy.GetCount_management(extMulti).getOutput(0))
        if result > 0:
            AddMsgAndPrint("\tSome areas marked for Revision fall outside the request extent. Updating the request extent.",0)
            # Make a copy of the projectExtent to work with
            arcpy.CopyFeatures_management(projectExtent, extentTemp1)
            arcpy.Delete_management(projectExtent)
            # Add the new areas marked for revision (possibly copied from existing features in other 'certified' layers)
            arcpy.Append_management(extMulti, extentTemp1, "NO_TEST")
            # Dissolve the results back together using all the standard attribute fields for projectExtent
            dis_fields = ['admin_state','admin_state_name','admin_county','admin_county_name','state_code','state_name','county_code','county_name','farm_number','tract_number','eval_status']
            arcpy.Dissolve_management(extentTemp1, extentTemp2, dis_fields, "", "SINGLE_PART", "")
            # Clip the updated extent by the tract boundary to keep all work within the tract.
            arcpy.Clip_analysis(extentTemp2, projectTract, extentTemp3)
            arcpy.MultipartToSinglepart_management(extentTemp3, projectExtent)
            
    else:
        # No need to update the project extent
        arcpy.Delete_management("rev_su_temp")
    del result


    #### Topology review 1 (check for overlaps within the SU layer itself)
    AddMsgAndPrint("\nChecking for overlaps within the Sampling Units layer...",0)

    # Delete the existing topology if it is present
    if arcpy.Exists(suTopo):
        arcpy.Delete_management(suTopo)

    # Create and validate the topology for Must Not Overlap
    cluster = 0.001
    arcpy.CreateTopology_management(wcFD, suTopoName, cluster)
    arcpy.AddFeatureClassToTopology_management(suTopo, projectSU, 1, 1)
    arcpy.AddRuleToTopology_management(suTopo, "Must Not Overlap (Area)", projectSU)
    arcpy.ValidateTopology_management(suTopo)

    # Export the errors and check for results
    arcpy.ExportTopologyErrors_management(suTopo, wcFD, "SU_Errors")
    arcpy.Delete_management(linesTopoFC)
    arcpy.Delete_management(pointsTopoFC)
    result = int(arcpy.GetCount_management(polysTopoFC).getOutput(0))
    if result > 0:
        AddMsgAndPrint("\tOverlaps found! Generating error layer for the map...",2)
        arcpy.Delete_management(polysTopoFC)
        arcpy.SetParameterAsText(1, projectExtent)
        arcpy.SetParameterAsText(2, suTopo)
        #re_add_layers()
    
        AddMsgAndPrint("\tPlease review and correct overlaps and then re-run this tool. Exiting...",2)
        exit()
        

    #### Topology review 2 (check for gaps in relation to the request extent)
    else:
        AddMsgAndPrint("\tNo overlaps found!",0)
        AddMsgAndPrint("\nChecking for gaps within the Sampling Units layer...",0)

        # Clean up previous topology check results and rules
        arcpy.Delete_management(polysTopoFC)
##        rule_num = str(arcpy.Describe(projectSU).DSID)
##        rule = "Must Not Overlap (" + rule_num + ")"
##        arcpy.RemoveRuleFromTopology_management(suTopo, rule)
        arcpy.RemoveFeatureClassFromTopology_management(suTopo, suName)
        #arcpy.RemoveRuleFromTopology_management(suTopo, "Must Not Overlap (Area)")
        del result

        # Clip the SU layer using the extent layer
        arcpy.Clip_analysis(projectSU, projectExtent, suTemp1)
        # Copy the extent to a temp layer for use in topology analysis
        arcpy.CopyFeatures_management(projectExtent, extTemp)

        # Build and validate the topology
        arcpy.AddFeatureClassToTopology_management(suTopo, extTemp, 1, 1)
        arcpy.AddFeatureClassToTopology_management(suTopo, suTemp1, 2, 2)
        arcpy.AddRuleToTopology_management(suTopo, "Must Cover Each Other (Area-Area)", extTemp, "", suTemp1, "")
        arcpy.ValidateTopology_management(suTopo)

        # Export the errors and check for results
        arcpy.ExportTopologyErrors_management(suTopo, wcFD, "SU_Errors")
        arcpy.Delete_management(linesTopoFC)
        arcpy.Delete_management(pointsTopoFC)
        result = int(arcpy.GetCount_management(polysTopoFC).getOutput(0))
        if result > 0:
            AddMsgAndPrint("\tGaps found! Generating error layer for the map...",2)
            arcpy.Delete_management(polysTopoFC)

            arcpy.SetParameterAsText(1, projectExtent)
            arcpy.SetParameterAsText(2, suTopo)
            arcpy.SetParameterAsText(3, suTemp1)
            arcpy.SetParameterAsText(4, extTemp)
            #re_add_layers()

            AddMsgAndPrint("\tPlease review and correct gaps by editing the Site_Sampling_Units layer.",2)
            AddMsgAndPrint("\tUse the temp layers for reference and do not edit them. When finished, re-run this tool. Exiting...",2)
            exit()

        else:
            AddMsgAndPrint("\tNo gaps found!",0)
            arcpy.Delete_management(polysTopoFC)


    #### Clean up, but keep a final topology to prevent editing errors that force an APRX restart.
    if arcpy.Exists(suTopo):
        arcpy.Delete_management(suTopo)


    #### Re-Create the Topology
    cluster = 0.001
    arcpy.CreateTopology_management(wcFD, suTopoName, cluster)
    arcpy.AddFeatureClassToTopology_management(suTopo, projectSU, 1, 1)
    arcpy.AddRuleToTopology_management(suTopo, "Must Not Overlap (Area)", projectSU)
    arcpy.ValidateTopology_management(suTopo)


    #### Delete other temporary layers
    if arcpy.Exists(suTemp1):
        arcpy.Delete_management(suTemp1)
    if arcpy.Exists(extTemp):
        arcpy.Delete_management(extTemp)


    #### "Topology" review 3 (check that all official ROPs are within the sampling units layer)
    AddMsgAndPrint("\nChecking official ROPs positions relative to sampling units...",0)

    # Make a feature layer of the ROPs and select only the official ROPs
    #arcpy.MakeFeatureLayer_management(projectROP, "rop_temp")
    off_rops = arcpy.SelectLayerByAttribute_management(projectROP, "NEW_SELECTION", "\"rop_status\" = 'Official'")
    #arcpy.SelectLayerByAttribute_management("rop_temp", "NEW_SELECTION", "\"rop_status\" = 'Official'")
    arcpy.CopyFeatures_management(off_rops, rop_Temp2)
    result = int(arcpy.GetCount_management(rop_Temp2).getOutput(0))
    if result <= 1:
        AddMsgAndPrint("\tNo official ROPs found. Please digitize and attribute official ROPs and then re-run this tool. Exiting...",2)
        exit()
    else:
        # Use the result count as the base line number of ROPs, and intersect the feature layer with the Sampling Units layer
        arcpy.Intersect_analysis([rop_Temp2, projectSU], rop_Temp, "NO_FID")
        count = int(arcpy.GetCount_management(rop_Temp).getOutput(0))
        if count != result:
            AddMsgAndPrint("\tOne or more official ROPs are not withing Sampling Units. Please correct and re-run this tool. Exiting...",2)
            arcpy.Delete_management(rop_Temp2, rop_Temp)
            exit()
        else:
            arcpy.Delete_management(rop_Temp2, rop_Temp)
            AddMsgAndPrint("\tROP locations are valid within Sampling Units. Continuing...",0)


    #### Clean up
    deleteTempLayers(tempLayers)


    #### Re-add layers to the project map
    arcpy.SetParameterAsText(1, projectExtent)
    #re_add_layers()


    #### Adjust visibility of layers to aid in moving to the next step in the process
    # Turn off all CLUs/Common, Define_AOI, and Extent layers
    off_names = ["CLU","Common","Site_Define_AOI","Request_Extent"]
    for maps in aprx.listMaps():
        for lyr in maps.listLayers():
            for name in off_names:
                if name in lyr.name:
                    lyr.visible = False

    # Turn on all SU, and ROPs layers
    on_names = ["Site_Sampling_Units","Site_ROPs"]
    for maps in aprx.listMaps():
        for lyr in maps.listLayers():
            for name in on_names:
                if (lyr.name).startswith(name):
                    lyr.visible = True
    
    
    #### Compact FGDB
    try:
        AddMsgAndPrint("\nCompacting File Geodatabasess..." ,0)
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
