## ===============================================================================================================
## Name:    Generate Base Map
## Purpose: Export a base map for the site at the current map extent.
##
## Authors: Adolfo Diaz
##          GIS Specialist
##          National Soil Survey Center
##          USDA-NRCS
##          adolfo.diaz@usda.gov
##          608.662.4422 ext 216
##
##          Chris Morse
##          GIS Specialist
##          Indianapolis State Office
##          USDA-NRCS
##          chris.morse@usda.gov
##          317.295.5849
##
## Created: 06/23/2021
##
## ===============================================================================================================
## Changes
## ===============================================================================================================
##
## rev. 06/21/2021
## -Start revisions of Generate WC Map ArcMap tool to National Wetlands Tool in ArcGIS Pro and retool to Base Map.
##
## rev. 07/07/2021
## -Add Town Range Section query sequence
## -Refine map export process to streamline tool and remove extraneous layer ordering and display
##
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
    
## ================================================================================================================
def logBasicSettings():
    # record basic user inputs and settings to log file for future purposes
    import getpass, time
    f = open(textFilePath,'a+')
    f.write("\n######################################################################\n")
    f.write("Executing Generate Base Map tool...\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("User Parameters:\n")
    f.write("\tInput Sampling Units Layer: " + arcpy.Describe(sourceSU).CatalogPath + "\n")
    f.write("\tInput ROPs Layer: " + arcpy.Describe(sourceROP).CatalogPath + "\n")
    if includeRP:
        f.write("\tInput Representative Points Layer: " + arcpy.Describe(sourceROP).CatalogPath + "\n")
    if includeDL:
        f.write("\tInput Drainage Lines Layer: " + arcpy.Describe(sourceDL).CatalogPath + "\n")
    if sourceRoads:
        f.write("\tInput Roads Layer: " + sourceRoads + "\n")
    if imageType:
        f.write("\tBase Map Type: " + imageType + "\n")
        if imageType == "Local File or Web Imagery Service":
            f.write("\tImagery Layer: " + sourceImage + "\n")
        if imageType == "Web Map Service or Basemap":
            f.write("\tImagery Layer: " + sourceService + "\n")
    if showLocation:
        f.write("\tShow PLSS Location Text Box: True\n")
    else:
        f.write("\tShow PLSS Location Text Box: False\n")
    if owLayouts:
        f.write("\tOverwrite Base Map: True\n")
    else:
        f.write("\tOverwrite Base Map: False\n")
    f.close
    del f

## ===============================================================================================================
def submitFSquery(url,INparams):
    INparams = INparams.encode('ascii')
    resp = urllib.request.urlopen(url,INparams)
    
    responseStatus = resp.getcode()
    responseMsg = resp.msg
    jsonString = resp.read()
    results = json.loads(jsonString)

    if 'error' in results.keys():
        AddMsgAndPrint("\tPLSS Query failed.",0)
        return False

    else:
        return results

## ===============================================================================================================
def getPLSS(plss_point):

    # URLs for BLM services
    tr_svc = 'https://gis.blm.gov/arcgis/rest/services/Cadastral/BLM_Natl_PLSS_CadNSDI/MapServer/1/query'   # Town and Range
    sec_svc = 'https://gis.blm.gov/arcgis/rest/services/Cadastral/BLM_Natl_PLSS_CadNSDI/MapServer/2/query'  # Sections

    trs_text = ''
    
    # If the plssPoint input is not a point, exit
    AddMsgAndPrint("\tChecking input PLSS reference point...",0)
    plssDesc = arcpy.Describe(plss_point)
    plss_fc = plssDesc.catalogPath
    if plssDesc.shapeType != "Point":
        if plss_fc.find('SCRATCH.gdb') > 0:
            arcpy.Delete_management(plss_point)
        AddMsgAndPrint("\nThe input PLSS location digitizing was not a 'point' layer.",2)
        AddMsgAndPrint("\nPlease digitize a single point in the input point parameter and try again. Exiting...",2)
        exit()
    # If the plssPoint layer has any number of features other than 1, exit
    else:
        plss_fc = plssDesc.catalogPath
        result = int(arcpy.GetCount_management(plss_fc).getOutput(0))
        if result != 1:
            if plss_fc.find('SCRATCH.gdb') > 0:
                arcpy.Delete_management(plss_point)
            AddMsgAndPrint("\nThe input PLSS location layer contains a number of points other than 1.",2)
            AddMsgAndPrint("\nPlease digitize a single point in the input point parameter and try again. Exiting...",2)
            exit()

    # The input is a single point. Continue.
    AddMsgAndPrint("\tInput PLSS location reference is a single point. Using point to query BLM PLSS layers...",0)

    # Get the x,y of the input point
    jsonPoint = [row[0] for row in arcpy.da.SearchCursor(plss_fc, ['SHAPE@JSON'])][0]

    # Set input parameters for a query to get a count of results
    params = urllibEncode({'f': 'json',
                           'geometry':jsonPoint,
                           'geometryType':'esriGeometryPoint',
                           'returnCountOnly':'true'})
    
    # Run and check the count query
    AddMsgAndPrint("\tQuerying BLM Township and Range Layer...",0)
    mer_txt = ''
    countQuery = submitFSquery(tr_svc,params)
    if countQuery:
        returned_records = countQuery['count']
        if returned_records > 0:
            # Run actual query for the town and range fields
            params = urllibEncode({'f': 'json',
                           'geometry':jsonPoint,
                           'geometryType':'esriGeometryPoint',
                           'returnGeometry':'false',
                           'outFields':'PRINMER,TWNSHPNO,TWNSHPDIR,RANGENO,RANGEDIR'})
            trQuery = submitFSquery(tr_svc,params)

            # Read the results
            rdict = trQuery['features'][0]
            adict = rdict['attributes']
            mer_txt = adict["PRINMER"]
            town_no = int(adict["TWNSHPNO"])
            town_dir = adict["TWNSHPDIR"]
            range_no = int(adict["RANGENO"])
            range_dir = adict["RANGEDIR"]

            # Check the results
            if len(mer_txt) > 0 and town_no > 0 and range_no > 0:
                # Query count the sections service
                params = urllibEncode({'f': 'json',
                           'geometry':jsonPoint,
                           'geometryType':'esriGeometryPoint',
                           'returnCountOnly':'true'})
                # Run and check the count query
                AddMsgAndPrint("\tQuerying BLM Sections Layer...",0)
                countQuery = submitFSquery(sec_svc,params)
                if countQuery:
                    returned_records = countQuery['count']
                    if returned_records > 0:
                        # Run actual query for the section field
                        params = urllibEncode({'f': 'json',
                                   'geometry':jsonPoint,
                                   'geometryType':'esriGeometryPoint',
                                   'returnGeometry':'false',
                                   'outFields':'FRSTDIVNO'})
                        secQuery = submitFSquery(sec_svc,params)

                        #Read the results
                        rdict = secQuery['features'][0]
                        adict = rdict['attributes']
                        section_no = int(adict["FRSTDIVNO"])

                        # Check the results
                        if section_no > 0:
                            trs_text = "Location: T" + str(town_no) + town_dir + ", R" + str(range_no) + range_dir + ", Sec " + str(section_no) + "\n" + mer_txt 
    return trs_text

## ================================================================================================================
def setLytElements(lyt, admCoName, geoCoName, farmNum, trNum, clientName, digitizer, location_txt=''):
    
    # Check for appropriate element names on Base Map layout, otherwise exit
    elm_list = []
    for elm in lyt.listElements():
        elm_list.append(elm.name)

    elm_names = ['Location','Farm','Tract','GeoCo','AdminCo','Customer']

    for name in elm_names:
        if name not in elm_list:
            AddMsgAndPrint("\n" + lyt.name + " layout does not contain " + name + " layout element.",2)
            AddMsgAndPrint("\nThe layout had an element deleted or may not be from the current version of the NRCS Wetlands Compliance Tools.",2)
            AddMsgAndPrint("\nExiting....",2)
            exit()

    # Assign each element object to a variable for easy access to the element
    for elm in lyt.listElements():
        # Location element
        if elm.name == "Location":
            loc_elm = elm

        # Farm Number Text element
        if elm.name == "Farm":
            farm_elm = elm

        # Tract Number Text element
        if elm.name == "Tract":
            tract_elm = elm

        # Geographic County Name element
        if elm.name == "GeoCo":
            geo_elm = elm

        # Admin County Name element
        if elm.name == "AdminCo":
            admin_elm = elm

        # Customer element
        if elm.name == "Customer":
            customer_elm = elm
        
##        # Map Prepared By element
##        if elm.name == "Map Author":
##            prep_elm = elm


    #### Update text layout elements
    # If an element fails in this part, it's likely that it was from a different template or was deleted by the project user
    AddMsgAndPrint("\nUpdating Layout Information...",0)
    
    if farmNum != '':
        farm_elm.text = "Farm: " + farmNum
    else:
        farm_elm.text = "Farm: (Not Found)"
        
    if trNum != '':
        tract_elm.text = "Tract: " + trNum
    else:
        tract_elm.text = "Tract: (Not Found)"

    if geoCoName != '':
        geo_elm.text = "Geographic County: " + geoCoName
    else:
        geo_elm.text = "Geographic County: (Not Found)"

    if admCoName != '':
        admin_elm.text = "Administrative County: " + admCoName
    else:
        admin_elm.text = "Administrative County: (Not Found)"

    if clientName != '':
        customer_elm.text = "Customer: " + clientName
    else:
        customer_elm.text = "Customer: (Not Entered)"

    if len(location_txt) > 0:
        loc_elm.visible = True
        loc_elm.text = location_txt
    else:
        loc_elm.visible = False
        loc_elm.text = "Location: "

##    if digitizer != '':
##        prep_elm.text = "Map Prepared By: " + digitizer
##    else:
##        prep_elm.text = "Map Prepared By: (Not Entered)"

        
## ================================================================================================================
#### Import system modules
import arcpy, sys, os, traceback, re
arcpy.AddMessage("Importing Python modules...\n")
import urllib, json, time
from urllib.request import Request, urlopen
from urllib.error import HTTPError as httpErrors
urllibEncode = urllib.parse.urlencode
parseQueryString = urllib.parse.parse_qsl


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
    sourceSU = arcpy.GetParameterAsText(0)
    sourceROP = arcpy.GetParameterAsText(1)
    includeRP = arcpy.GetParameter(2)
    sourceRP = arcpy.GetParameterAsText(3)
    includeDL = arcpy.GetParameter(4)
    sourceDL = arcpy.GetParameterAsText(5)
    sourceRoads = arcpy.GetParameterAsText(6)
    imageType = arcpy.GetParameterAsText(7)
    sourceImage = arcpy.GetParameterAsText(8)
    sourceService = arcpy.GetParameterAsText(9)
    showLocation = arcpy.GetParameter(10)
    plssPoint = arcpy.GetParameterAsText(11)
    owLayouts = arcpy.GetParameter(12)

#### OLD ARCMAP PARAMETERS ###
##    localFlag = arcpy.GetParameter(1)
##    localImage = arcpy.GetParameterAsText(2)
##    webFlag = arcpy.GetParameter(3)
##    webImage = arcpy.GetParameterAsText(4)
##    hideCLUlabels = arcpy.GetParameter(6)
##    ledgerLayout = arcpy.GetParameter(7)
##    wcaLayout = arcpy.GetParameter(8)
##    ropFlag = arcpy.GetParameter(9)
##    sourceROP = arcpy.GetParameterAsText(10)
##    includeLines = arcpy.GetParameter(12)


    #### Initial Validations
    arcpy.AddMessage("Verifying inputs...\n")
    # If Sampling Units or ROPs layers have features selected, clear the selections so that all features from it are processed.
    try:
        clear_lyr1 = m.listLayers(sourceSU)[0]
        clear_lyr2 = m.listLayers("Site_ROPs")[0]
        arcpy.SelectLayerByAttribute_management(clear_lyr1, "CLEAR_SELECTION")
        arcpy.SelectLayerByAttribute_management(clear_lyr2, "CLEAR_SELECTION")
    except:
        pass

    
    #### Set base path
    sourceSU_path = arcpy.Describe(sourceSU).CatalogPath
    if sourceSU_path.find('.gdb') > 0 and sourceSU_path.find('Determinations') > 0 and sourceSU_path.find('Site_Sampling_Units') > 0:
        wcGDB_path = sourceSU_path[:sourceSU_path.find('.gdb')+4]
    else:
        arcpy.AddError("\nSelected Site Sampling Units layer is not from a Determinations project folder. Exiting...")
        exit()


    #### Do not run if any unsaved edits exist in the target workspace
    # Pro opens an edit session when any edit has been made and stays open until edits are committed with Save Edits.
    # Check for uncommitted edits and exit if found, giving the user a message directing them to Save or Discard them.
    workspace = wcGDB_path
    edit = arcpy.da.Editor(workspace)
    if edit.isEditing:
        arcpy.AddError("\nThere are unsaved data edits in this project. Please Save or Discard Edits and then run this tool again. Exiting...")
        exit()
    del workspace, edit


    #### Define Variables
    arcpy.AddMessage("Setting variables...\n")
    supportGDB = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb")
    scratchGDB = os.path.join(os.path.dirname(sys.argv[0]), "SCRATCH.gdb")

    wetDir = os.path.dirname(wcGDB_path)
    wcFD = wcGDB_path + os.sep + "WC_Data"
    userWorkspace = os.path.dirname(wetDir)
    wcGDB_name = os.path.basename(wcGDB_path)
    projectName = os.path.basename(userWorkspace).replace(" ", "_")
    basedataGDB_path = userWorkspace + os.sep + projectName + "_BaseData.gdb"
    basedataGDB_name = os.path.basename(basedataGDB_path)
    basedataFD_name = "Layers"
    basedataFD = basedataGDB_path + os.sep + basedataFD_name
    
    projectCLU = basedataGDB_path + os.sep + "Layers" + os.sep + "CLU_" + projectName
    projectTable = basedataGDB_path + os.sep + "Table_" + projectName

    cluName = "Site_CLU"
    suName = "Site_Sampling_Units"
    ropName = "Site_ROPs"
    rpName = "Site_Reference_Points"
    drainName = "Site_Drainage_Lines"


    #### Set up log file path and start logging
    arcpy.AddMessage("Commence logging...\n")
    textFilePath = userWorkspace + os.sep + projectName + "_log.txt"
    logBasicSettings()


    #### Setup output PDF file name(s)
    outPDF = wetDir + os.sep + "Base_Map_" + projectName + ".pdf"
    # If overwrite existing maps is checked, use standard file name
    if owLayouts == True:
        outPDF = wetDir + os.sep + "Base_Map_" + projectName + ".pdf"
    
    # Else enumerate the output map name(s)
    else:
        if os.path.exists(outPDF):
            count = 1
            while count > 0:
                outPDF = wetDir + os.sep + "Base_Map_" + projectName + "_" + str(count) + ".pdf"
                if os.path.exists(outPDF):
                    count += 1
                else:
                    count = 0


    #### Check if the output PDF file name(s) is currently open in another application.
    # If so, then close it so we can overwrite without an IO error during export later.
    # We can't use Python to check active threads for a file without a special module.
    # We have to get creative with modules available to us, such as os.
    myfile = outPDF
    if os.path.exists(myfile):
        try:
            os.rename(myfile, myfile + "_opentest")
            arcpy.AddMessage("The project's Base Map PDF file is available to overwrite!")
            os.rename(myfile + "_opentest", myfile)
        except:
            arcpy.AddMessage("The Base Map PDF file is open or in use by another program. Please close the PDF and try running this tool again. Exiting...")
            exit()
    else:
        arcpy.AddMessage("The Base Map PDF file does not exist for this project and will be created.")

        
    #### Retrieve PLSS Text for Base Map, if applicable
    # Set starting boolean for location text box. Stays false unless all query criteria to show location are met
    display_bm_location = False
    bm_plss_text = ''
        
    if showLocation:
        AddMsgAndPrint("\nShow location selected. Processing reference location...",0)
        bm_plss_text = getPLSS(plssPoint)
        if bm_plss_text != '':
            AddMsgAndPrint("\nThe PLSS query was successful and a location text box will be shown on the Base Map.",0)
            display_bm_location = True
               
    # If any part of the PLSS query failed, or if show location was not enabled, then do not show the Location text box
    if display_bm_location == False:
        AddMsgAndPrint("\tEither the Show Location parameter was not enabled or the PLSS query failed.",0)
        AddMsgAndPrint("\tA Town, Range, Section text box will not be shown on the Base Map.",0)


    #### Harvest project based data from the project table to use on the layout
    if arcpy.Exists(projectTable):
        AddMsgAndPrint("\nCollecting header information from project table...",0)
        rows = arcpy.SearchCursor(projectTable) 
        for row in rows:
            adm_Co_Name = row.getValue("admin_county_name")
            geo_Co_Name = row.getValue("county_name")
            farm_Num = row.getValue("farm_number")
            tr_Num = row.getValue("tract_number")
            client_Name = row.getValue("client")
            dig_staff = row.getValue("dig_staff")
        del rows, row

    else:
        adm_Co_Name = ''
        geo_Co_Name = ''
        farm_Num = ''
        tr_Num = ''
        client_Name = ''
        dig_staff = ''


    #### Set up layout elements
    AddMsgAndPrint("\nUpdating layout elements...",0)
    # Get Base Map layout
    try:
        bm_lyt = aprx.listLayouts("Base Map")[0]
    except:
        AddMsgAndPrint("\nCould not find installed Base Map layout. Exiting...",2)
        exit()

    # Send information to function to set the layout elements
    setLytElements(bm_lyt, adm_Co_Name, geo_Co_Name, farm_Num, tr_Num, client_Name, dig_staff, bm_plss_text)

    
    #####################################################################################################
    ########################################## BASE MAP START ###########################################
    #####################################################################################################
    #### Manage layers as objects for visibility and movement control
    # Set typical layer objects for layers that must be active on the base map
    AddMsgAndPrint("\nPreparing map layers for display on the layout...",0)
    
    su_lyr = m.listLayers(suName)[0]
    rop_lyr = m.listLayers(ropName)[0]
    try:
        rp_lyr = m.listLayers(rpName)[0]
    except:
        rp_lyr = ''
    try:
        dl_lyr = m.listLayers(drainName)[0]
    except:
        dl_lyr = ''

    plss_lyr = ''
    if plssPoint:
        plssDesc = arcpy.Describe(plssPoint)
        if plssDesc.dataType == "FeatureLayer":
            try:
                plss_lyr = m.listLayers(plssPoint)[0]
            except:
                plss_lyr = ''
                
    # Find annotation for the typical layers, if any
    lyrs = m.listLayers()
    
    su_anno_list = []
    for lyr in lyrs:
        if lyr.name.startswith(suName + "Anno"):
            su_anno_list.append(lyr.name)
    if len(su_anno_list) > 1:
        AddMsgAndPrint("\tThe map contains more than one SU Annotation layer.",2)
        AddMsgAndPrint("\tPlease remove any EXTRA SU Annotation layers and run this tool again. Exiting...",2)
        exit()

    rop_anno_list = []
    for lyr in lyrs:
        if lyr.name.startswith(ropName + "Anno"):
            rop_anno_list.append(lyr.name)
    if len(rop_anno_list) > 1:
        AddMsgAndPrint("\tThe map contains more than one ROPs Annotation layer.",2)
        AddMsgAndPrint("\tPlease remove any EXTRA ROPs Annotation layers and run this tool again. Exiting...",2)
        exit()
        
    rp_anno_list = []
    for lyr in lyrs:
        if lyr.name.startswith(rpName + "Anno"):
            rp_anno_list.append(lyr.name)
    if len(rp_anno_list) > 1:
        AddMsgAndPrint("\tThe map contains more than one Representative Points Annotation layer.",2)
        AddMsgAndPrint("\tPlease remove any EXTRA Representative Points Annotation layers and run this tool again. Exiting...",2)
        exit()
        
    dl_anno_list = []
    for lyr in lyrs:
        if lyr.name.startswith(drainName + "Anno"):
            dl_anno_list.append(lyr.name)
    if len(dl_anno_list) > 1:
        AddMsgAndPrint("\tThe map contains more than one Drainage Lines Annotation layer.",2)
        AddMsgAndPrint("\tPlease remove any EXTRA Drainage Lines Annotation layers and run this tool again. Exiting...",2)
        exit()
        
    su_anno_lyr = ''
    if len(su_anno_list) == 1:
        su_anno_lyr = m.listLayers(su_anno_list[0])

    rop_anno_lyr = ''
    if len(rop_anno_list) == 1:
        rop_anno_lyr = m.listLayers(rop_anno_list[0])

    rp_anno_lyr = ''
    if len(rp_anno_list) == 1:
        rp_anno_lyr = m.listLayers(rp_anno_list[0])

    dl_anno_lyr = ''
    if len(dl_anno_list) == 1:
        dl_anno_lyr = m.listLayers(dl_anno_list[0])


    #### Start exporting maps
    AddMsgAndPrint("\nCreating the Base Map PDF file...",0)

    # Set required layers and corresponding annotation or labels to be visible
    su_lyr.visible = True
    if arcpy.Exists(su_anno_lyr):
        su_anno_lyr.visible = True
        su_lyr.showLabels = False
    else:
        su_lyr.showLabels = True
        
    rop_lyr.visible = True
    if arcpy.Exists(rop_anno_lyr):
        rop_anno_lyr.visible = True
        rop_lyr.showLabels = False
    else:
        rop_lyr.showLabels = True
    
    if includeRP:
        rp_lyr.visible = True
        if arcpy.Exists(rp_anno_lyr):
            rp_anno_lyr.visible = True
            rp_lyr.showLabels = False
        else:
            rp_lyr.showLabels = True
        
    if includeDL:
        dl_lyr.visible = True
        if arcpy.Exists(dl_anno_lyr):
            dl_anno_lyr.visible = True
            dl_lyr.showLabels = False
        else:
            dl_lyr.showLabels = True

    # Set the plss inpoint layer to be not visible, if it was used
    if plssPoint:
        try:
            plss_lyr.visible = False
        except:
            pass
            
    # Export the map
    AddMsgAndPrint("\tExporting the Base Map to PDF...",0)
    bm_lyt.exportToPDF(outPDF, resolution=300, image_quality="NORMAL", layers_attributes="LAYERS_AND_ATTRIBUTES", georef_info=True)
    AddMsgAndPrint("\tBase Map file exported!",0)
    

    #### MAINTENANCE
    # Look for and delete anything else that may remain in the installed SCRATCH.gdb
    startWorkspace = arcpy.env.workspace
    arcpy.env.workspace = scratchGDB
    dss = []
    for ds in arcpy.ListDatasets('*'):
        dss.append(os.path.join(scratchGDB, ds))
    for ds in dss:
        if arcpy.Exists(ds):
            try:
                arcpy.Delete_management(ds)
            except:
                pass
    arcpy.env.workspace = startWorkspace
    del startWorkspace
    
    # Compact FGDB
    try:
        AddMsgAndPrint("\nCompacting File Geodatabases..." ,0)
        arcpy.Compact_management(basedataGDB_path)
        arcpy.Compact_management(wcGDB_path)
        AddMsgAndPrint("\tSuccessful",0)
    except:
        pass
    
    AddMsgAndPrint("\nThe Base Map has been created and exported! Exiting...",0)

except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested...exiting.")
