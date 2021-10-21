## ===============================================================================================================
## Name:    Repair Project Layers
## Purpose: Reloads project layers and resets their attribute rules to try to free up any editing locks.
##
## Authors: Chris Morse
##          GIS Specialist
##          Indianapolis State Office
##          USDA-NRCS
##          chris.morse@usda.gov
##          317.295.5849
##
## Created: 07/16/2021
##
## ===============================================================================================================
## Changes
## ===============================================================================================================
##
## rev. ##/##/####
## -[enter text for revisions here]
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
    f.write("Executing Repair Project Layers tool...\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("User Parameters:\n")
    f.write("\tProject Folder: " + sourceFolder + "\n")
    f.close
    del f

## ===============================================================================================================
def repairRules(projectFC, rule_names, rule_table):
    # Removes a feature class's rules and imports them again

    #### Remove rules
    if arcpy.Exists(projectFC):
        try:
            arcpy.DeleteAttributeRule_management(projectFC, rule_names)
        except:
            arcpy.AddError("There was a problem removing the rules for the " + os.path.basename(projectFC) + " layer. Continuing...")

    #### Import the rules again
    if arcpy.Exists(projectFC):
        arcpy.ImportAttributeRules_management(projectFC, rule_table)

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
def addLayer(mf, lyr_file, db_path, lyr_name):
    # Adds layers to a map
    cp = lyr_file.connectionProperties
    cp['connection_info']['database'] = db_path
    cp['dataset'] = lyr_name
    lyr_file.updateConnectionProperties(lyr_file.connectionProperties, cp)
    mf.addLayer(lyr_file)

## ===============================================================================================================
#### Import system modules
import arcpy, sys, os, traceback, re


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


#### Main procedures
try:
    #### Inputs
    arcpy.AddMessage("Reading inputs...\n")
    sourceFolder = arcpy.GetParameterAsText(0)

    #### Define Variables
    # Project paths
    userWorkspace = sourceFolder
    projectName = os.path.basename(userWorkspace)
    wetDir = userWorkspace + os.sep + "Wetlands"
    if not arcpy.Exists(wetDir):
        arcpy.AddError("The specified folder does appear to be a determinations project folder.")
        arcpy.AddError("We recommend trying a different folder or starting from scratch on a new project. Exiting...")
        exit()
    wcGDB_path = wetDir + os.sep + projectName + "_WC.gdb"
    if not arcpy.Exists(wcGDB_path):
        arcpy.AddError("The specified folder does contain a wetlands database.")
        arcpy.AddError("We recommend re-running Create Wetlands Project, Create Base Map Layers, or Create CWD Layers. Exiting...")
        exit()
    wcFD = wcGDB_path + os.sep + "WC_Data"
    if not arcpy.Exists(wcFD):
        arcpy.AddError("The specified folder does contain a wetlands database with a correct dataset. Exiting...")
        arcpy.AddError("We recommend re-running Create Wetlands Project, Create Base Map Layers, or Create CWD Layers. Exiting...")
        exit()


    
    # Possible Project Business Layers that have rules
    suName = "Site_Sampling_Units"
    projectSU = wcFD + os.sep + suName
    
    ropName = "Site_ROPs"
    projectROP = wcFD + os.sep + ropName
    
    refName = "Site_Reference_Points"
    projectREF = wcFD + os.sep + refName
    
    drainName = "Site_Drainage_Lines"
    projectLines = wcFD + os.sep + drainName
    
    cwdName = "Site_CWD"
    projectCWD = wcFD + os.sep + cwdName
    
    pjwName = "Site_PJW"
    projectPJW = wcFD + os.sep + pjwName

    # Annotation strings
    suAnnoString = "Site_Sampling_Units" + "Anno*"
    ropAnnoString = "Site_ROPs" + "Anno*"
    refAnnoString = "Site_Reference_Points" + "Anno*"
    drainAnnoString = "Site_Drainage_Lines" + "Anno*"
    cwdAnnoString = "Site_CWD" + "Anno*"
    
    # Layer Files
    suLyr = arcpy.mp.LayerFile(os.path.join(os.path.dirname(sys.argv[0]), "layer_files") + os.sep + "Sampling_Units.lyrx").listLayers()[0]
    ropLyr = arcpy.mp.LayerFile(os.path.join(os.path.dirname(sys.argv[0]), "layer_files") + os.sep + "ROP.lyrx").listLayers()[0]
    refLyr = arcpy.mp.LayerFile(os.path.join(os.path.dirname(sys.argv[0]), "layer_files") + os.sep + "Reference_Points.lyrx").listLayers()[0]
    drainLyr = arcpy.mp.LayerFile(os.path.join(os.path.dirname(sys.argv[0]), "layer_files") + os.sep + "Drainage_Lines.lyrx").listLayers()[0]
    cwdLyr = arcpy.mp.LayerFile(os.path.join(os.path.dirname(sys.argv[0]), "layer_files") + os.sep + "CWD.lyrx").listLayers()[0]
    pjwLyr = arcpy.mp.LayerFile(os.path.join(os.path.dirname(sys.argv[0]), "layer_files") + os.sep + "PJW.lyrx").listLayers()[0]
    
    # Rules Files
    rules_su = os.path.join(os.path.dirname(sys.argv[0]), "Rules_SU.csv")
    rules_rops = os.path.join(os.path.dirname(sys.argv[0]), "Rules_ROPs.csv")
    rules_refs = os.path.join(os.path.dirname(sys.argv[0]), "Rules_REF.csv")
    rules_lines = os.path.join(os.path.dirname(sys.argv[0]), "Rules_Drains.csv")
    rules_cwd = os.path.join(os.path.dirname(sys.argv[0]), "Rules_CWD.csv")
    rules_pjw = os.path.join(os.path.dirname(sys.argv[0]), "Rules_PJW.csv")
    
    # Rules Names
    rules_su_names = ['Update Acres', 'Add SU Job ID', 'Add SU Admin State', 'Add SU Admin State Name',
                      'Add SU Admin County', 'Add SU Admin County Name', 'Add SU State Code', 'Add SU State Name',
                      'Add SU County Code', 'Add SU County Name', 'Add SU Farm Number', 'Add SU Tract Number',
                      'Add Request Date', 'Add Request Type', 'Add Eval Status']

    rules_rop_names = ['Add ROP Admin State Code', 'Add ROP Admin State Name', 'Add ROP Admin County Code',
                       'Add ROP Admin County Name', 'Add ROP Job ID', 'Add ROP State Code', 'Add ROP State Name',
                       'Add ROP County Code', 'Add ROP County Name', 'Add ROP Farm Number', 'Add ROP Tract Number']

    rules_ref_names = ['Add RP Job ID', 'Add RP Admin State Code', 'Add RP Admin State Name', 'Add RP Admin County Code',
                       'Add RP Admin County Name', 'Add RP State Code', 'Add RP State Name', 'Add RP County Code',
                       'Add RP County Name', 'Add RP Farm Number', 'Add RP Tract Number', 'Set Default Hydro',
                       'Set Default Veg', 'Set Default Soil']

    rules_line_names = ['Update Length', 'Add Drainage Job ID', 'Add Drainage Admin State Code', 'Add Drainage Admin State Name',
                        'Add Drainage Admin County Code', 'Add Drainage Admin County Name', 'Add Drainage State Code',
                        'Add Drainage State Name', 'Add Drainage County Code', 'Add Drainage County Name',
                        'Add Drainage Farm Number', 'Add Drainage Tract Number']

    rules_cwd_names = ['Update Acres']

    rules_pjw_names = ['Add PJW Job ID']


    #### Set up log file path and start logging
    arcpy.AddMessage("Commence logging...\n")
    textFilePath = userWorkspace + os.sep + projectName + "_log.txt"
    logBasicSettings()

    #### Remove each layer if it exists in the map
    AddMsgAndPrint("\Remove old layers from the map...",0)
    # Starting list of layer names
    mapLayersToRemove = [suName, ropName, refName, drainName, cwdName, pjwName]

    # Find annotation to remove as well and add it to the list
    annoStrings = [suAnnoString, ropAnnoString, refAnnoString, drainAnnoString, cwdAnnoString]
    for aString in annoStrings:
        for lyr in m.listLayers(aString):
            mapLayersToRemove.append(lyr.name)

    # Remove the layers
    AddMsgAndPrint("\Remove old layers from the map...",0)
    removeLayers(mapLayersToRemove)
    del mapLayersToRemove

##    #### First try to repair the rules
##    AddMsgAndPrint("\Refreshing attribute rules...",0)
##    
##    ## Syntax: repairRules(projectFC, rule_names, rule_table)
##    repairRules(projectSU, rules_su_names, rules_su)
##    repairRules(projectROP, rules_rop_names, rules_rops)
##    repairRules(projectREF, rules_ref_names, rules_refs)
##    repairRules(projectLines, rules_line_names, rules_lines)
##    repairRules(projectCWD, rules_cwd_names, rules_cwd)
##    repairRules(projectPJW, rules_pjw_names, rules_pjw)


##    #### Remove each layer if it exists in the map
##    AddMsgAndPrint("\Remove old layers from the map...",0)
##    # Starting list of layer names
##    mapLayersToRemove = [suName, ropName, refName, drainName, cwdName, pjwName]
##
##    # Find annotation to remove as well and add it to the list
##    annoStrings = [suAnnoString, ropAnnoString, refAnnoString, drainAnnoString, cwdAnnoString]
##    for aString in annoStrings:
##        for lyr in m.listLayers(aString):
##            mapLayersToRemove.append(lyr.name)
##
##    # Remove the layers
##    AddMsgAndPrint("\Remove old layers from the map...",0)
##    removeLayers(mapLayersToRemove)
##    del mapLayersToRemove


    #### Now add back the layers to the map if the corresponding feature class exists.
    AddMsgAndPrint("\Adding layers back to the map...",0)
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
        
##    if arcpy.Exists(projectSU):
##        addLayer(m, suLyr, wcGDB_path, suName)

    if ropName not in lyr_name_list:
        ropLyr_cp = ropLyr.connectionProperties
        ropLyr_cp['connection_info']['database'] = wcGDB_path
        ropLyr_cp['dataset'] = ropName
        ropLyr.updateConnectionProperties(ropLyr.connectionProperties, ropLyr_cp)
        m.addLayer(ropLyr)
        
##    if arcpy.Exists(projectROP):
##        addLayer(m, ropLyr, wcGDB_path, ropName)

    if refName not in lyr_name_list:
        refLyr_cp = ropLyr.connectionProperties
        refLyr_cp['connection_info']['database'] = wcGDB_path
        refLyr_cp['dataset'] = refName
        refLyr.updateConnectionProperties(refLyr.connectionProperties, refLyr_cp)
        m.addLayer(refLyr)
        
##    if arcpy.Exists(projectREF):
##        addLayer(m, refLyr, wcGDB_path, refName)

    if drainName not in lyr_name_list:
        drainLyr_cp = ropLyr.connectionProperties
        drainLyr_cp['connection_info']['database'] = wcGDB_path
        drainLyr_cp['dataset'] = drainName
        drainLyr.updateConnectionProperties(drainLyr.connectionProperties, drainLyr_cp)
        m.addLayer(drainLyr)
        
##    if arcpy.Exists(projectLines):
##        addLayer(m, drainLyr, wcGDB_path, drainName)

    if cwdName not in lyr_name_list:
        cwdLyr_cp = cwdLyr.connectionProperties
        cwdLyr_cp['connection_info']['database'] = wcGDB_path
        cwdLyr_cp['dataset'] = cwdName
        cwdLyr.updateConnectionProperties(cwdLyr.connectionProperties, cwdLyr_cp)
        m.addLayer(cwdLyr)
        
##    if arcpy.Exists(projectCWD):
##        addLayer(m, cwdLyr, wcGDB_path, cwdName)

    if pjwName not in lyr_name_list:
        pjwLyr_cp = pjwLyr.connectionProperties
        pjwLyr_cp['connection_info']['database'] = wcGDB_path
        pjwLyr_cp['dataset'] = pjwName
        pjwLyr.updateConnectionProperties(pjwLyr.connectionProperties, pjwLyr_cp)
        m.addLayer(pjwLyr)
        
##    if arcpy.Exists(projectPJW):
##        addLayer(m, pjwLyr, wcGDB_path, pjwName)

    # Adjust the visibility of the newly added layers to turn them all off to reduce clutter
    off_names = [suName, ropName, refName, drainName, cwdName, pjwName]
    for lyr in m.listLayers():
        for name in off_names:
            if name in lyr.name:
                lyr.visible = False

    
    #### Compact FGDB
    try:
        AddMsgAndPrint("\nCompacting File Geodatabases...",0)
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
