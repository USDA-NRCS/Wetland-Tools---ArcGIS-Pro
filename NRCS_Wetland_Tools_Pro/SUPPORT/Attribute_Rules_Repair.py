## ===============================================================================================================
## Name:    Attribute Rules - Repair
## Purpose: Repairs attribute rules in all project layers
##
## Authors: Chris Morse
##          GIS Specialist
##          Indianapolis State Office
##          USDA-NRCS
##          chris.morse@usda.gov
##          317.295.5849
##
## Created: 08/30/2021
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
    f.write("Executing Attribute Rules - Repair tool...\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("User Parameters:\n")
    f.write("\tInput Folder: " + inFolder + "\n")
    f.close
    del f
    
## ===============================================================================================================
#### Import system modules
import arcpy, sys, os, traceback, re


#### Update Environments
arcpy.AddMessage("Setting Environments...")
arcpy.SetProgressorLabel("Setting Environments...")

# Set overwrite flag
arcpy.env.overwriteOutput = True

# Test for Pro project.
try:
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    m = aprx.listMaps("Determinations")[0]
except:
    arcpy.AddError("This tool must be run from an active ArcGIS Pro project that was developed from the template distributed with this toolbox. Exiting...")
    exit()


#### Main procedures
try:
    #### Inputs
    arcpy.AddMessage("Reading inputs...")
    arcpy.SetProgressorLabel("Reading inputs...")
    inFolder = arcpy.GetParameterAsText(0)
    
    
    #### Define Variables
    # Project paths
    userWorkspace = inFolder
    projectName = os.path.basename(userWorkspace)

    wetDir = userWorkspace + os.sep + "Wetlands"
    wcGDB_name = projectName + "_WC.gdb"
    wcGDB_path = wetDir + os.sep + wcGDB_name
    wcFD = wcGDB_path + os.sep + "WC_Data"
    
    suName = "Site_Sampling_Units"
    projectSU = wcFD + os.sep + suName
    
    ropName = "Site_ROPs"
    projectROP = wcFD + os.sep + ropName
    
    refName = "Site_Reference_Points"
    projectREF = wcFD + os.sep + refName
    
    drainName = "Site_Drainage_Lines"
    projectDrain = wcFD + os.sep + drainName
    
    pjwName = "Site_PJW"
    projectPJW = wcFD + os.sep + pjwName

    if not arcpy.Exists(wcGDB_path):
        arcpy.AddError("Selected folder is not a determination project or does not contain expected datasets. Exiting...")
        exit()

    textFilePath = userWorkspace + os.sep + projectName + "_log.txt"
    logBasicSettings()

    if arcpy.Exists(projectSU):
        AddMsgAndPrint("\nUpdating Sampling Units Layer...",0)
        arcpy.SetProgressorLabel("Updating Sampling Units Layer...")
        su_expression_1 = 'return First(FeatureSetByName($datastore, "Admin_Table")).job_id'
        su_expression_2 = 'return First(FeatureSetByName($datastore, "Admin_Table")).admin_state'
        su_expression_3 = 'return First(FeatureSetByName($datastore, "Admin_Table")).admin_state_name'
        su_expression_4 = 'return First(FeatureSetByName($datastore, "Admin_Table")).admin_county'
        su_expression_5 = 'return First(FeatureSetByName($datastore, "Admin_Table")).admin_county_name'
        su_expression_6 = 'return First(FeatureSetByName($datastore, "Admin_Table")).state_code'
        su_expression_7 = 'return First(FeatureSetByName($datastore, "Admin_Table")).state_name'
        su_expression_8 = 'return First(FeatureSetByName($datastore, "Admin_Table")).county_code'
        su_expression_9 = 'return First(FeatureSetByName($datastore, "Admin_Table")).county_name'
        su_expression_10 = 'return First(FeatureSetByName($datastore, "Admin_Table")).farm_number'
        su_expression_11 = 'return First(FeatureSetByName($datastore, "Admin_Table")).tract_number'
        su_expression_12 = 'return First(FeatureSetByName($datastore, "Admin_Table")).request_date'
        su_expression_13 = 'return First(FeatureSetByName($datastore, "Admin_Table")).request_type'
        arcpy.AlterAttributeRule_management(projectSU, "Add SU Job ID", "", "", "", "", "INSERT", su_expression_1)
        arcpy.AlterAttributeRule_management(projectSU, "Add SU Admin State", "", "", "", "", "INSERT", su_expression_2)
        arcpy.AlterAttributeRule_management(projectSU, "Add SU Admin State Name", "", "", "", "", "INSERT", su_expression_3)
        arcpy.AlterAttributeRule_management(projectSU, "Add SU Admin County", "", "", "", "", "INSERT", su_expression_4)
        arcpy.AlterAttributeRule_management(projectSU, "Add SU Admin County Name", "", "", "", "", "INSERT", su_expression_5)
        arcpy.AlterAttributeRule_management(projectSU, "Add SU State Code", "", "", "", "", "INSERT", su_expression_6)
        arcpy.AlterAttributeRule_management(projectSU, "Add SU State Name", "", "", "", "", "INSERT", su_expression_7)
        arcpy.AlterAttributeRule_management(projectSU, "Add SU County Code", "", "", "", "", "INSERT", su_expression_8)
        arcpy.AlterAttributeRule_management(projectSU, "Add SU County Name", "", "", "", "", "INSERT", su_expression_9)
        arcpy.AlterAttributeRule_management(projectSU, "Add SU Farm Number", "", "", "", "", "INSERT", su_expression_10)
        arcpy.AlterAttributeRule_management(projectSU, "Add SU Tract Number", "", "", "", "", "INSERT", su_expression_11)
        arcpy.AlterAttributeRule_management(projectSU, "Add Request Date", "", "", "", "", "INSERT", su_expression_12)
        arcpy.AlterAttributeRule_management(projectSU, "Add Request Type", "", "", "", "", "INSERT", su_expression_13)
        
    if arcpy.Exists(projectROP):
        AddMsgAndPrint("\nUpdating ROPs Layer...",0)
        arcpy.SetProgressorLabel("Updating ROPs Layer...")
        rop_expression_1 = 'return First(FeatureSetByName($datastore, "Admin_Table")).admin_state'
        rop_expression_2 = 'return First(FeatureSetByName($datastore, "Admin_Table")).admin_state_name'
        rop_expression_3 = 'return First(FeatureSetByName($datastore, "Admin_Table")).admin_county'
        rop_expression_4 = 'return First(FeatureSetByName($datastore, "Admin_Table")).admin_county_name'
        rop_expression_5 = 'return First(FeatureSetByName($datastore, "Admin_Table")).job_id'
        rop_expression_6 = 'return First(FeatureSetByName($datastore, "Admin_Table")).state_code'
        rop_expression_7 = 'return First(FeatureSetByName($datastore, "Admin_Table")).state_name'
        rop_expression_8 = 'return First(FeatureSetByName($datastore, "Admin_Table")).county_code'
        rop_expression_9 = 'return First(FeatureSetByName($datastore, "Admin_Table")).county_name'
        rop_expression_10 = 'return First(FeatureSetByName($datastore, "Admin_Table")).farm_number'
        rop_expression_11 = 'return First(FeatureSetByName($datastore, "Admin_Table")).tract_number'
        arcpy.AlterAttributeRule_management(projectROP, "Add ROP Admin State Code", "", "", "", "", "INSERT", rop_expression_1)
        arcpy.AlterAttributeRule_management(projectROP, "Add ROP Admin State Name", "", "", "", "", "INSERT", rop_expression_2)
        arcpy.AlterAttributeRule_management(projectROP, "Add ROP Admin County Code", "", "", "", "", "INSERT", rop_expression_3)
        arcpy.AlterAttributeRule_management(projectROP, "Add ROP Admin County Name", "", "", "", "", "INSERT", rop_expression_4)
        arcpy.AlterAttributeRule_management(projectROP, "Add ROP Job ID", "", "", "", "", "INSERT", rop_expression_5)
        arcpy.AlterAttributeRule_management(projectROP, "Add ROP State Code", "", "", "", "", "INSERT", rop_expression_6)
        arcpy.AlterAttributeRule_management(projectROP, "Add ROP State Name", "", "", "", "", "INSERT", rop_expression_7)
        arcpy.AlterAttributeRule_management(projectROP, "Add ROP County Code", "", "", "", "", "INSERT", rop_expression_8)
        arcpy.AlterAttributeRule_management(projectROP, "Add ROP County Name", "", "", "", "", "INSERT", rop_expression_9)
        arcpy.AlterAttributeRule_management(projectROP, "Add ROP Farm Number", "", "", "", "", "INSERT", rop_expression_10)
        arcpy.AlterAttributeRule_management(projectROP, "Add ROP Tract Number", "", "", "", "", "INSERT", rop_expression_11)

    if arcpy.Exists(projectREF):
        AddMsgAndPrint("\nUpdating Reference Points Layer...",0)
        arcpy.SetProgressorLabel("Updating Reference Points Layer...")
        ref_expression_1 = 'return First(FeatureSetByName($datastore, "Admin_Table")).job_id'
        ref_expression_2 = 'return First(FeatureSetByName($datastore, "Admin_Table")).admin_state'
        ref_expression_3 = 'return First(FeatureSetByName($datastore, "Admin_Table")).admin_state_name'
        ref_expression_4 = 'return First(FeatureSetByName($datastore, "Admin_Table")).admin_county'
        ref_expression_5 = 'return First(FeatureSetByName($datastore, "Admin_Table")).admin_county_name'
        ref_expression_6 = 'return First(FeatureSetByName($datastore, "Admin_Table")).state_code'
        ref_expression_7 = 'return First(FeatureSetByName($datastore, "Admin_Table")).state_name'
        ref_expression_8 = 'return First(FeatureSetByName($datastore, "Admin_Table")).county_code'
        ref_expression_9 = 'return First(FeatureSetByName($datastore, "Admin_Table")).county_name'
        ref_expression_10 = 'return First(FeatureSetByName($datastore, "Admin_Table")).farm_number'
        ref_expression_11 = 'return First(FeatureSetByName($datastore, "Admin_Table")).tract_number'
        arcpy.AlterAttributeRule_management(projectREF, "Add RP Job ID", "", "", "", "", "INSERT", ref_expression_1)
        arcpy.AlterAttributeRule_management(projectREF, "Add RP Admin State Code", "", "", "", "", "INSERT", ref_expression_2)
        arcpy.AlterAttributeRule_management(projectREF, "Add RP Admin State Name", "", "", "", "", "INSERT", ref_expression_3)
        arcpy.AlterAttributeRule_management(projectREF, "Add RP Admin County Code", "", "", "", "", "INSERT", ref_expression_4)
        arcpy.AlterAttributeRule_management(projectREF, "Add RP Admin County Name", "", "", "", "", "INSERT", ref_expression_5)
        arcpy.AlterAttributeRule_management(projectREF, "Add RP State Code", "", "", "", "", "INSERT", ref_expression_6)
        arcpy.AlterAttributeRule_management(projectREF, "Add RP State Name", "", "", "", "", "INSERT", ref_expression_7)
        arcpy.AlterAttributeRule_management(projectREF, "Add RP County Code", "", "", "", "", "INSERT", ref_expression_8)
        arcpy.AlterAttributeRule_management(projectREF, "Add RP County Name", "", "", "", "", "INSERT", ref_expression_9)
        arcpy.AlterAttributeRule_management(projectREF, "Add RP Farm Number", "", "", "", "", "INSERT", ref_expression_10)
        arcpy.AlterAttributeRule_management(projectREF, "Add RP Tract Number", "", "", "", "", "INSERT", ref_expression_11)

    if arcpy.Exists(projectDrain):
        AddMsgAndPrint("\nUpdating Drainage Lines Layer...",0)
        arcpy.SetProgressorLabel("Updating Drainage Lines Layer...")
        dl_expression_1 = 'return First(FeatureSetByName($datastore, "Admin_Table")).job_id'
        dl_expression_2 = 'return First(FeatureSetByName($datastore, "Admin_Table")).admin_state'
        dl_expression_3 = 'return First(FeatureSetByName($datastore, "Admin_Table")).admin_state_name'
        dl_expression_4 = 'return First(FeatureSetByName($datastore, "Admin_Table")).admin_county'
        dl_expression_5 = 'return First(FeatureSetByName($datastore, "Admin_Table")).admin_county_name'
        dl_expression_6 = 'return First(FeatureSetByName($datastore, "Admin_Table")).state_code'
        dl_expression_7 = 'return First(FeatureSetByName($datastore, "Admin_Table")).state_name'
        dl_expression_8 = 'return First(FeatureSetByName($datastore, "Admin_Table")).county_code'
        dl_expression_9 = 'return First(FeatureSetByName($datastore, "Admin_Table")).county_name'
        dl_expression_10 = 'return First(FeatureSetByName($datastore, "Admin_Table")).farm_number'
        dl_expression_11 = 'return First(FeatureSetByName($datastore, "Admin_Table")).tract_number'
        arcpy.AlterAttributeRule_management(projectDrain, "Add Drainage Job ID", "", "", "", "", "INSERT", dl_expression_1)
        arcpy.AlterAttributeRule_management(projectDrain, "Add Drainage Admin State Code", "", "", "", "", "INSERT", dl_expression_2)
        arcpy.AlterAttributeRule_management(projectDrain, "Add Drainage Admin State Name", "", "", "", "", "INSERT", dl_expression_3)
        arcpy.AlterAttributeRule_management(projectDrain, "Add Drainage Admin County Code", "", "", "", "", "INSERT", dl_expression_4)
        arcpy.AlterAttributeRule_management(projectDrain, "Add Drainage Admin County Name", "", "", "", "", "INSERT", dl_expression_5)
        arcpy.AlterAttributeRule_management(projectDrain, "Add Drainage State Code", "", "", "", "", "INSERT", dl_expression_6)
        arcpy.AlterAttributeRule_management(projectDrain, "Add Drainage State Name", "", "", "", "", "INSERT", dl_expression_7)
        arcpy.AlterAttributeRule_management(projectDrain, "Add Drainage County Code", "", "", "", "", "INSERT", dl_expression_8)
        arcpy.AlterAttributeRule_management(projectDrain, "Add Drainage County Name", "", "", "", "", "INSERT", dl_expression_9)
        arcpy.AlterAttributeRule_management(projectDrain, "Add Drainage Farm Number", "", "", "", "", "INSERT", dl_expression_10)
        arcpy.AlterAttributeRule_management(projectDrain, "Add Drainage Tract Number", "", "", "", "", "INSERT", dl_expression_11)


    if arcpy.Exists(projectPJW):
        AddMsgAndPrint("\nUpdating PJW Layer...",0)
        arcpy.SetProgressorLabel("Updating PJW Layer...")
        pjw_expression_1 = 'return First(FeatureSetByName($datastore, "Admin_Table")).job_id'
        arcpy.AlterAttributeRule_management(projectPJW, "Add PJW Job ID", "", "", "", "", "INSERT", pjw_expression_1)
        
    
    #### Compact FGDB
    try:
        AddMsgAndPrint("\nCompacting File Geodatabase...",0)
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
