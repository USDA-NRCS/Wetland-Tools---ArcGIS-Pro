## ===============================================================================================================
## Name:    Attribute Rules - Delete
## Purpose: Deletes attribute rules from selected layer.
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
    f.write("Executing Attribute Rules - Delete tool...\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("User Parameters:\n")
    f.write("\tInput Layer: " + in_lyr + "\n")
    f.close
    del f

## ===============================================================================================================
def deleteRules(projectFC, rule_names):
    # Removes a feature class's rules and imports them again

    #### Remove rules
    if arcpy.Exists(projectFC):
        try:
            arcpy.DeleteAttributeRule_management(projectFC, rule_names)
        except:
            arcpy.AddWarning("Layer may already have no rules or there was a problem deleting the rules. Continuing...")

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
    
    # Possible Project Business Layers that have rules
    projectSU = wcFD + os.sep + suName
    projectROP = wcFD + os.sep + ropName
    projectREF = wcFD + os.sep + refName
    projectLines = wcFD + os.sep + drainName
    projectCWD = wcFD + os.sep + cwdName
    projectPJW = wcFD + os.sep + pjwName
    
    # Possible Rules Files
    rules_su = os.path.join(os.path.dirname(sys.argv[0]), "Rules_SU.csv")
    rules_rops = os.path.join(os.path.dirname(sys.argv[0]), "Rules_ROPs.csv")
    rules_refs = os.path.join(os.path.dirname(sys.argv[0]), "Rules_REF.csv")
    rules_lines = os.path.join(os.path.dirname(sys.argv[0]), "Rules_Drains.csv")
    rules_cwd = os.path.join(os.path.dirname(sys.argv[0]), "Rules_CWD.csv")
    rules_pjw = os.path.join(os.path.dirname(sys.argv[0]), "Rules_PJW.csv")
    
    # Possible Rules Names
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

    #### Delete the rules
    AddMsgAndPrint("\nDeleting attribute rules...",0) 

    ## Syntax: deleteRules(projectFC, rule_names)
    if in_lyr == suName:
        #deleteRules(projectSU, rules_su_names)
        deleteRules(in_lyr, rules_su_names)
    if in_lyr == ropName:
        #deleteRules(projectROP, rules_rop_names)
        deleteRules(in_lyr, rules_rop_names)
    if in_lyr == refName:
        #deleteRules(projectREF, rules_ref_names)
        deleteRules(in_lyr, rules_ref_names)
    if in_lyr == drainName:
        #deleteRules(projectLines, rules_line_names)
        deleteRules(in_lyr, rules_line_names)
    if in_lyr == cwdName:
        #deleteRules(projectCWD, rules_cwd_names)
        deleteRules(in_lyr, rules_cwd_names)
    if in_lyr == pjwName:
        #deleteRules(projectPJW, rules_pjw_names)
        deleteRules(in_lyr, rules_pjw_names)

    
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
