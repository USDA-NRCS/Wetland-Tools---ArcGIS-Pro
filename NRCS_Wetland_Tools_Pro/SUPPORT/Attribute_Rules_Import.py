## ===============================================================================================================
## Name:    Attribute Rules - Import
## Purpose: Imports attribute rules to selected layer
##
## Authors: Chris Morse
##          GIS Specialist
##          Indianapolis State Office
##          USDA-NRCS
##          chris.morse@usda.gov
##          317.295.5849
##
## Created: 07/28/2021
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
    f.write("Executing Attribute Rules - Import tool...\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("User Parameters:\n")
    f.write("\tInput Layer: " + in_lyr + "\n")
    f.close
    del f

## ===============================================================================================================
def importRules(projectFC, rule_table):
    # Removes a feature class's rules and imports them again

    #### Remove rules
    if arcpy.Exists(projectFC):
        try:
            #arcpy.ImportAttributeRules_management(projectFC, rule_table)
            arcpy.management.ImportAttributeRules(projectFC, rule_table)
        except:
            arcpy.AddError("There was a problem importing the attribute rules. Exiting...")

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
    in_lyr = arcpy.GetParameterAsText(0)

    #### Define Variables
    # Project paths
    suName = "Site_Sampling_Units"
    ropName = "Site_ROPs"
    refName = "Site_Reference_Points"
    drainName = "Site_Drainage_Lines"
    cwdName = "Site_CWD"
    pjwName = "Site_PJW"
    valid_names = [suName, ropName, refName, drainName, cwdName, pjwName]

    if in_lyr not in valid_names:
        arcpy.AddError("The input layer is not a valid project layer that would have rules to delete. Please try again. Exiting...")
        exit()
    
    try:
        lyr_path = arcpy.Describe(in_lyr).catalogPath
        wcFD = os.path.dirname(lyr_path)
        wcGDB_path = os.path.dirname(wcFD)
        wetDir = os.path.dirname(wcGDB_path)
        userWorkspace = os.path.dirname(wetDir)
        projectName = os.path.basename(userWorkspace)
        wetDir = userWorkspace + os.sep + "Wetlands"
    except:
        arcpy.AddError("The input layer may not be a valid project layer. Cannot determine expected paths. Please try again. Exiting...")
        exit()

    suNameNew = "Site_Sampling_Units_new"
    ropNameNew = "Site_ROPs_new"
    refNameNew = "Site_Reference_Points_new"
    drainNameNew = "Site_Drainage_Lines_new"
    cwdNameNew = "Site_CWD_new"
    pjwNameNew = "Site_PJW_new"

    supportGDB = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb")
    templateSU = supportGDB + os.sep + "master_sampling_units"
    templateROP = supportGDB + os.sep + "master_rop"
    templateREF = supportGDB + os.sep + "master_reference"
    templateLines = supportGDB + os.sep + "master_drainage_lines"
    templateCWD = supportGDB + os.sep + "master_cwd"
    templatePJW = supportGDB + os.sep + "master_pjw"
    
    # Possible Project Business Layers that have rules
    projectSU = wcFD + os.sep + suName
    projectROP = wcFD + os.sep + ropName
    projectREF = wcFD + os.sep + refName
    projectLines = wcFD + os.sep + drainName
    projectCWD = wcFD + os.sep + cwdName
    projectPJW = wcFD + os.sep + pjwName

    projectSUnew = wcFD + os.sep + suName + "_new"
    projectROPnew = wcFD + os.sep + ropName + "_new"
    projectREFnew = wcFD + os.sep + refName + "_new"
    projectLinesnew = wcFD + os.sep + drainName + "_new"
    projectCWDnew = wcFD + os.sep + cwdName + "_new"
    projectPJWnew = wcFD + os.sep + pjwName + "_new"

    # Backup layers
    backupSU = wcFD + os.sep + suName + "_bak"
    backupROP = wcFD + os.sep + ropName + "_bak"
    backupREF = wcFD + os.sep + refName + "_bak"
    backupLines = wcFD + os.sep + drainName + "_bak"
    backupCWD = wcFD + os.sep + cwdName + "_bak"
    backupPJW = wcFD + os.sep + pjwName + "_bak"

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
    
    # Possible Rules Files
    rules_su = os.path.join(os.path.dirname(sys.argv[0]), "Rules_SU.csv")
    rules_rops = os.path.join(os.path.dirname(sys.argv[0]), "Rules_ROPs.csv")
    rules_refs = os.path.join(os.path.dirname(sys.argv[0]), "Rules_REF.csv")
    rules_lines = os.path.join(os.path.dirname(sys.argv[0]), "Rules_Drains.csv")
    rules_cwd = os.path.join(os.path.dirname(sys.argv[0]), "Rules_CWD.csv")
    rules_pjw = os.path.join(os.path.dirname(sys.argv[0]), "Rules_PJW.csv")


    #### Set up log file path and start logging
    arcpy.AddMessage("Commence logging...\n")
    textFilePath = userWorkspace + os.sep + projectName + "_log.txt"
    logBasicSettings()


    #### Process the layer. Back it up, remove it from the map, remove its annotation, delete it, recreate it, append features from backup, delete backup, add to map
    AddMsgAndPrint("\nProcessing the input layer...",0)
    mapLayersToRemove = [in_lyr]
    if in_lyr == suName:
        for lyr in m.listLayers(suAnnoString):
            mapLayersToRemove.append(lyr.name)
        removeLayers(mapLayersToRemove)
        try:
            arcpy.Delete_management(backupSU)
        except:
            pass
        arcpy.CopyFeatures_management(projectSU, backupSU)
        arcpy.Delete_management(projectSU)
        arcpy.CreateFeatureclass_management(wcFD, suNameNew, "POLYGON", templateSU)
        arcpy.AssignDomainToField_management(projectSUnew, "eval_status", "Evaluation Status")
        arcpy.AssignDomainToField_management(projectSUnew, "three_factors", "YN")
        arcpy.AssignDomainToField_management(projectSUnew, "request_type", "Request Type")
        arcpy.AssignDomainToField_management(projectSUnew, "deter_method", "Method")
        arcpy.Append_management(backupSU, projectSUnew, "NO_TEST")
        arcpy.Rename_management(projectSUnew, projectSU)
        arcpy.ImportAttributeRules_management(projectSU, rules_su)
        addLayer(m, suLyr, wcGDB_path, suName)

    if in_lyr == ropName:
        for lyr in m.listLayers(ropAnnoString):
            mapLayersToRemove.append(lyr.name)
        removeLayers(mapLayersToRemove)
        try:
            arcpy.Delete_management(backupROP)
        except:
            pass
        arcpy.CopyFeatures_management(projectROP, backupROP)
        arcpy.Delete_management(projectROP)
        arcpy.CreateFeatureclass_management(wcFD, ropNameNew, "POINT", templateROP)
        arcpy.Append_management(backupROP, projectROPnew, "NO_TEST")
        arcpy.Rename_management(projectROPnew, projectROP)
        arcpy.ImportAttributeRules_management(projectROP, rules_rops)
        addLayer(m, ropLyr, wcGDB_path, ropName)

    if in_lyr == refName:
        for lyr in m.listLayers(refAnnoString):
            mapLayersToRemove.append(lyr.name)
        removeLayers(mapLayersToRemove)
        try:
            arcpy.Delete_management(backupREF)
        except:
            pass
        arcpy.CopyFeatures_management(projectREF, backupREF)
        arcpy.Delete_management(projectREF)
        arcpy.CreateFeatureclass_management(wcFD, refNameNew, "POINT", template)
        arcpy.AssignDomainToField_management(projectREFnew, "hydro", "Yes No")
        arcpy.AssignDomainToField_management(projectREFnew, "veg", "Yes No")
        arcpy.AssignDomainToField_management(projectREFnew, "soil", "Yes No")
        arcpy.Append_management(backupREF, projectREFnew, "NO_TEST")
        arcpy.Rename_management(projectREFnew, projectREF)
        arcpy.ImportAttributeRules_management(projectREF, rules_refs)
        addLayer(m, refLyr, wcGDB_path, refName)

    if in_lyr == drainName:
        for lyr in m.listLayers(drainAnnoString):
            mapLayersToRemove.append(lyr.name)
        removeLayers(mapLayersToRemove)
        try:
            arcpy.Delete_management(backupLines)
        except:
            pass
        arcpy.CopyFeatures_management(projectLines, backupLines)
        arcpy.Delete_management(projectLines)
        arcpy.CreateFeatureclass_management(wcFD, drainNameNew, "POLYLINE", templateLines)
        arcpy.AssignDomainToField_management(projectLinesnew, "line_type", "Line Type")
        arcpy.AssignDomainToField_management(projectLinesnew, "manip_era", "Pre Post")
        arcpy.Append_management(backupLines, projectLinesnew, "NO_TEST")
        arcpy.Rename_management(projectLinesnew, projectLines)
        arcpy.ImportAttributeRules_management(projectLines, rules_lines)
        addLayer(m, drainLyr, wcGDB_path, drainName)

    if in_lyr == cwdName:
        for lyr in m.listLayers(cwdAnnoString):
            mapLayersToRemove.append(lyr.name)
        removeLayers(mapLayersToRemove)
        try:
            arcpy.Delete_management(backupCWD)
        except:
            pass
        arcpy.CopyFeatures_management(projectCWD, backupCWD)
        arcpy.Delete_management(projectCWD)
        arcpy.CreateFeatureclass_management(wcFD, cwdNameNew, "POLYGON", templateCWD)
        arcpy.AssignDomainToField_management(projectCWDnew, "eval_status", "Evaluation Status")
        arcpy.AssignDomainToField_management(projectCWDnew, "wetland_label", "Wetland Labels")
        arcpy.AssignDomainToField_management(projectCWDnew, "three_factors", "YN")
        arcpy.AssignDomainToField_management(projectCWDnew, "request_type", "Request Type")
        arcpy.AssignDomainToField_management(projectCWDnew, "deter_method", "Method")
        arcpy.Append_management(backupCWD, projectCWDnew, "NO_TEST")
        arcpy.Rename_management(projectCWDnew, projectCWD)
        arcpy.ImportAttributeRules_management(projectCWD, rules_cwd)
        addLayer(m, cwdLyr, wcGDB_path, cwdName)

    if in_lyr == pjwName:
        removeLayers(mapLayersToRemove)
        try:
            arcpy.Delete_management(backupPJW)
        except:
            pass
        arcpy.CopyFeatures_management(projectPJW, backupPJW)
        arcpy.Delete_management(projectPJW)
        arcpy.CreateFeatureclass_management(wcFD, pjwNameNew, "POINT", templatePJW)
        arcpy.Append_management(backupPJW, projectPJWnew, "NO_TEST")
        arcpy.Rename_management(projectPJWnew, projectPJW)
        arcpy.ImportAttributeRules_management(projectPJW, rules_pjw)
        addLayer(m, pjwLyr, wcGDB_path, pjwName)

    
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
