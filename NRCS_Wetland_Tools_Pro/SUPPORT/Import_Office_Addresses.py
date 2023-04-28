## ===============================================================================================================
## Name:    Import Office Address Tables
## Purpose: Imports the NRCS and FSA and NAD address CSV files to tables in the install database.
##          This tool has no user input parameters and will attempt to import the installed files to the
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
##
## 02/17/2023 - Chris Morse - Changed inputs from XLSX to CSV
##
## 04/28/2023 - Dylan Harwell - Minor cleanup/refactor
## ===============================================================================================================
#### Import system modules
from os import path
from sys import argv
import arcpy

# Set overwrite flag
arcpy.env.overwriteOutput = True

#### Start

arcpy.AddMessage("Setting variables...")
arcpy.SetProgressorLabel("Setting variables...")

supportGDB = path.join(path.dirname(argv[0]), "SUPPORT.gdb")
templates_folder = path.join(path.dirname(argv[0]), "Templates")
nrcs_address_csv = path.join(templates_folder, "NRCS_Address.csv")
nrcs_temp_path = path.join(supportGDB, "nrcs_temp")
fsa_address_csv = path.join(templates_folder, "FSA_Address.csv")
fsa_temp_path = path.join(supportGDB, "fsa_temp")
nad_address_csv = path.join(templates_folder, "NAD_Address.csv")
nad_temp_path = path.join(supportGDB, "nad_temp")

temp_tables = [nrcs_temp_path, fsa_temp_path, nad_temp_path]
for item in temp_tables:
    if arcpy.Exists(item):
        arcpy.management.Delete(item)

if arcpy.Exists(nrcs_address_csv) and arcpy.Exists(fsa_address_csv) and arcpy.Exists(nad_address_csv):
    try:
        arcpy.AddMessage("Importing NRCS Office Table...")
        arcpy.SetProgressorLabel("Importing NRCS Office Table...")
        arcpy.conversion.TableToTable(nrcs_address_csv, supportGDB, "nrcs_temp")
        regen = False
        nrcs_fields = arcpy.ListFields(nrcs_temp_path)
        for field in nrcs_fields:
            if field.type == 'Integer':
                regen = True
        if regen == True:
            # Use Field Mappings to control column format in output (all output fields need to be text/string in output)
            # CSV defaults anyting that looks like a number to a number, which might be the NRCSZIP field as an Integer from the NRCS_Address.csv table if no entered zips have dashes.
            arcpy.conversion.TableToTable(nrcs_address_csv, supportGDB, "nrcs_addresses", '',
                                          r'NRCSOffice "NRCSOffice" true true false 8000 Text 0 0,First,#,' + nrcs_address_csv + ',NRCSOffice,0,8000;' +
                                          r'NRCSAddress "NRCSAddress" true true false 8000 Text 0 0,First,#,' + nrcs_address_csv + ',NRCSAddress,0,8000;' +
                                          r'NRCSCITY "NRCSCITY" true true false 8000 Text 0 0,First,#,' + nrcs_address_csv + ',NRCSCITY,0,8000;' +
                                          r'NRCSSTATE "NRCSSTATE" true true false 8000 Text 0 0,First,#,' + nrcs_address_csv + ',NRCSSTATE,0,8000;' +
                                          r'NRCSZIP "NRCSZIP" true true false 8000 Text 0 0,First,#,' + nrcs_address_csv + ',NRCSZIP,-1,-1;' +
                                          r'NRCSPHONE "NRCSPHONE" true true false 8000 Text 0 0,First,#,' + nrcs_address_csv + ',NRCSPHONE,0,8000;' +
                                          r'NRCSFAX "NRCSFAX" true true false 8000 Text 0 0,First,#,' + nrcs_address_csv + ',NRCSFAX,0,8000;' +
                                          r'NRCSCounty "NRCSCounty" true true false 8000 Text 0 0,First,#,' + nrcs_address_csv + ',NRCSCounty,0,8000',
                                          '')
        else:
            arcpy.conversion.TableToTable(nrcs_address_csv, supportGDB, "nrcs_addresses")
        arcpy.management.Delete(nrcs_temp_path)
        
        arcpy.AddMessage("Importing FSA Office Table...")
        arcpy.SetProgressorLabel("Importing FSA Office Table...")
        arcpy.conversion.TableToTable(fsa_address_csv, supportGDB, "fsa_temp")
        regen = False
        fsa_fields = arcpy.ListFields(fsa_temp_path)
        for field in fsa_fields:
            if field.type == 'Integer':
                regen = True
        if regen == True:
            # Use Field Mappings to control column format in output (all output fields need to be text/string in output)
            # CSV defaults anyting that looks like a number to a number, which might be the FSAZIP field as an Integer from the FSA_Address.csv table if no entered zips have dashes.
            arcpy.conversion.TableToTable(fsa_address_csv, supportGDB, "fsa_addresses", '',
                                          r'FSAOffice "FSAOffice" true true false 8000 Text 0 0,First,#,' + fsa_address_csv + ',FSAOffice,0,8000;' +
                                          r'FSAAddress "FSAAddress" true true false 8000 Text 0 0,First,#,' + fsa_address_csv + ',FSAAddress,0,8000;' +
                                          r'FSACITY "FSACITY" true true false 8000 Text 0 0,First,#,' + fsa_address_csv + ',FSACITY,0,8000;' +
                                          r'FSASTATE "FSASTATE" true true false 8000 Text 0 0,First,#,' + fsa_address_csv + ',FSASTATE,0,8000;' +
                                          r'FSAZIP "FSAZIP" true true false 8000 Text 0 0,First,#,' + fsa_address_csv + ',FSAZIP,-1,-1;' +
                                          r'FSAPHONE "FSAPHONE" true true false 8000 Text 0 0,First,#,' + fsa_address_csv + ',FSAPHONE,0,8000;' +
                                          r'FSAFAX "FSAFAX" true true false 8000 Text 0 0,First,#,' + fsa_address_csv + ',FSAFAX,0,8000;' +
                                          r'FSACounty "FSACounty" true true false 8000 Text 0 0,First,#,' + fsa_address_csv + ',FSACounty,0,8000',
                                          '')
        else:
            arcpy.conversion.TableToTable(fsa_address_csv, supportGDB, "fsa_addresses")
        arcpy.management.Delete(fsa_temp_path)

        arcpy.AddMessage("Importing NAD Office Table...")
        arcpy.SetProgressorLabel("Importing NAD Office Table...")
        arcpy.conversion.TableToTable(nad_address_csv, supportGDB, "nad_temp")
        regen = False
        nad_fields = arcpy.ListFields(nad_temp_path)
        for field in nad_fields:
            if field.type == 'Integer':
                regen = True
        if regen == True:
            # Use Field Mappings to control column format in output (all output fields need to be text/string in output)
            # CSV defaults anyting that looks like a number to a number, which will be the STATECD field as an Integer from the NAD_Address.csv table.
            arcpy.conversion.TableToTable(nad_address_csv, supportGDB, "nad_addresses", '',
                                          r'STATECD "STATECD" true true false 8000 Text 0 0,First,#,' + nad_address_csv + ',STATECD,-1,-1;' +
                                          r'STATE "STATE" true true false 8000 Text 0 0,First,#,' + nad_address_csv + ',STATE,0,8000;' +
                                          r'NADADDRESS "NADADDRESS" true true false 8000 Text 0 0,First,#,' + nad_address_csv + ',NADADDRESS,0,8000;' +
                                          r'NADCITY "NADCITY" true true false 8000 Text 0 0,First,#,' + nad_address_csv + ',NADCITY,0,8000;' +
                                          r'NADSTATE "NADSTATE" true true false 8000 Text 0 0,First,#,' + nad_address_csv + ',NADSTATE,0,8000;' +
                                          r'NADZIP "NADZIP" true true false 8000 Text 0 0,First,#,' + nad_address_csv + ',NADZIP,0,8000;' +
                                          r'TOLLFREE "TOLLFREE" true true false 8000 Text 0 0,First,#,' + nad_address_csv + ',TOLLFREE,0,8000;' +
                                          r'PHONE "PHONE" true true false 8000 Text 0 0,First,#,' + nad_address_csv + ',PHONE,0,8000;' +
                                          r'TTY "TTY" true true false 8000 Text 0 0,First,#,' + nad_address_csv + ',TTY,0,8000;' +
                                          r'FAX "FAX" true true false 8000 Text 0 0,First,#,' + nad_address_csv + ',FAX,0,8000',
                                          '')
        else:
            arcpy.conversion.TableToTable(nad_address_csv, supportGDB, "nad_addresses")
        arcpy.management.Delete(nad_temp_path)
    except:
        arcpy.AddError("Something went wrong in the import process. Exiting...")
        exit()
else:
    arcpy.AddError("Could not find expected NRCS, FSA, and/or NAD Address CSVs in install folders. Exiting...")
    exit()

arcpy.AddMessage("Address table imports were successful! Exiting...")
