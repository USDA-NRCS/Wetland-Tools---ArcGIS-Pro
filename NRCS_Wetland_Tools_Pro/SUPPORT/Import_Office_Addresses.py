## ===============================================================================================================
## Name:    Import Office Address Tables
## Purpose: Imports the NRCS and FSA tabs of the NRCS Address spreadsheet to tables in the install database.
##          This tool has no user input parameters and will attempt to import the installed spreadsheet to the
##          installed database tables, overwriting the database tables in the process.
##
## Authors: Chris Morse
##          GIS Specialist
##          Indianapolis State Office
##          USDA-NRCS
##          chris.morse@usda.gov
##          317.295.5849
##
## Created: 04/04/2022
##
## ===============================================================================================================
## Changes
## ===============================================================================================================
##
## rev. <pending
## - <pending>
##
## ===============================================================================================================
#### Import system modules
import arcpy, sys, os

# Set overwrite flag
arcpy.env.overwriteOutput = True

#### Start

arcpy.AddMessage("Setting variables...")
arcpy.SetProgressorLabel("Setting variables...")

supportGDB = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb")
templates_folder = os.path.join(os.path.dirname(sys.argv[0]), "Templates")
in_excel = templates_folder + os.sep + "NRCS_Address.xlsx"
nrcs_table = supportGDB + os.sep + "nrcs_addresses"
fsa_table = supportGDB + os.sep + "fsa_addresses"
nrcs_sheet = "NRCS_Offices"
fsa_sheet = "FSA_Offices"
title_row = 1

if arcpy.Exists(in_excel):
    try:
        arcpy.AddMessage("Importing NRCS Office Table...")
        arcpy.SetProgressorLabel("Importing NRCS Office Table...")
        arcpy.ExcelToTable_conversion(in_excel, nrcs_table, nrcs_sheet, title_row)
        
        arcpy.AddMessage("Importing FSA Office Table...")
        arcpy.SetProgressorLabel("Importing FSA Office Table...")
        arcpy.ExcelToTable_conversion(in_excel, fsa_table, fsa_sheet, title_row)
    except:
        arcpy.AddError("Something went wrong in the import process. Exiting...")
        exit()
        
else:
    arcpy.AddError("Could not find expected address workbook in install folders. Exiting...")
    exit()

arcpy.AddMessage("Address table imports were successful! Exiting...")
