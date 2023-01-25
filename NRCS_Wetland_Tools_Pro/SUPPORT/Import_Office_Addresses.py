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
## 12/08/2022 - Dylan Harwell - Import NAD_Address.xlsx table to GDB
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
nrcs_address_excel = templates_folder + os.sep + "NRCS_Address.xlsx"
nad_address_excel = templates_folder + os.sep + "NAD_Address.xlsx"
nrcs_table = supportGDB + os.sep + "nrcs_addresses"
fsa_table = supportGDB + os.sep + "fsa_addresses"
nad_table = supportGDB + os.sep + "nad_addresses"

if arcpy.Exists(nrcs_address_excel) and arcpy.Exists(nad_address_excel):
    try:
        arcpy.AddMessage("Importing NRCS Office Table...")
        arcpy.SetProgressorLabel("Importing NRCS Office Table...")
        arcpy.ExcelToTable_conversion(nrcs_address_excel, nrcs_table, "NRCS_Offices", 1)
        
        arcpy.AddMessage("Importing FSA Office Table...")
        arcpy.SetProgressorLabel("Importing FSA Office Table...")
        arcpy.ExcelToTable_conversion(nrcs_address_excel, fsa_table, "FSA_Offices", 1)

        arcpy.AddMessage("Importing NAD Office Table...")
        arcpy.SetProgressorLabel("Importing NAD Office Table...")
        arcpy.ExcelToTable_conversion(nad_address_excel, nad_table, "NAD_Address", 1)
    except:
        arcpy.AddError("Something went wrong in the import process. Exiting...")
        exit()
else:
    arcpy.AddError("Could not find expected NRCS and NAD Address workbooks in install folders. Exiting...")
    exit()

arcpy.AddMessage("Address table imports were successful! Exiting...")
