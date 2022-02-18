## ===============================================================================================================
## Name:    Export Previous Determination Map
## Purpose: Export a previous determination map for the site at the current map extent.
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
## Created: 07/15/2021
##
## ===============================================================================================================
## Changes
## ===============================================================================================================
##
## rev. 07/15/2021
## -Start revisions from the Export Determination Map tool to retool for the previous determinations map.
##
## rev. 02/03/2022
## - Added handling for specifiying imagery layer to display in a map text box.
## - Added automatic control of legends to only show features in map extent and to hide the imagery layer.
##
## rev. 02/08/2022
## - Blocked out annotation and labels related code
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
    f.write("Executing Export Previous Determinations Map tool...\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("User Parameters:\n")
    f.write("\tInput Previous CLU CWD Layer: " + arcpy.Describe(sourcePrevCWD).CatalogPath + "\n")
    if showLocation:
        f.write("\tShow PLSS Location Text Box: True\n")
    else:
        f.write("\tShow PLSS Location Text Box: False\n")
    if owLayout:
        f.write("\tOverwrite Previous Determinations Map: True\n")
    else:
        f.write("\tOverwrite Previous Determinations Map: False\n")
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
def setLytElements(lyt, admCoName, geoCoName, farmNum, trNum, clientName, digitizer, image_name, location_txt=''):
    
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

        # Imagery Text element
        if elm.name == "Imagery Text Box":
            imagery_elm = elm
            
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

    if imagery != '':
        imagery_elm.text = " Image: " + image_name
    else:
        imagery_elm.text = " Image: "
        
##    if digitizer != '':
##        prep_elm.text = "Map Prepared By: " + digitizer
##    else:
##        prep_elm.text = "Map Prepared By: (Not Entered)"

    #### Turn off the imagery element in each layout
    # Get the legend item for the layout
    leg = lyt.listElements('LEGEND_ELEMENT')[0]
    for item in leg.items:
        if item.name == image_name:
            item.visible = False
            
        
## ================================================================================================================
#### Import system modules
import arcpy, sys, os, traceback, re
import urllib, json, time
from urllib.request import Request, urlopen
from urllib.error import HTTPError as httpErrors
urllibEncode = urllib.parse.urlencode
parseQueryString = urllib.parse.parse_qsl


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


#### Main procedures
try:
    #### Inputs
    arcpy.AddMessage("Reading inputs...\n")
    arcpy.SetProgressorLabel("Reading inputs...")
    sourcePrevCWD = arcpy.GetParameterAsText(0)
    zoomType = arcpy.GetParameterAsText(1)
    zoomLyr = arcpy.GetParameterAsText(2)
    showLocation = arcpy.GetParameter(3)
    plssPoint = arcpy.GetParameterAsText(4)
    owDetLayout = arcpy.GetParameter(5)
    imagery = arcpy.GetParameterAsText(6)


    #### Initial Validations
    arcpy.AddMessage("Verifying inputs...\n")
    arcpy.SetProgressorLabel("Verifying inputs...")

    
    #### Set base path
    sourcePrevCWD_path = arcpy.Describe(sourcePrevCWD).CatalogPath
    if sourcePrevCWD_path.find('.gdb') > 0 and sourcePrevCWD_path.find('Determinations') > 0 and sourcePrevCWD_path.find('CWD') > 0:
        wcGDB_path = sourcePrevCWD_path[:sourcePrevCWD_path.find('.gdb')+4]
    else:
        arcpy.AddError("\nSelected Site Previous CLU CWD layer is not from a Determinations project folder. Exiting...")
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
    arcpy.SetProgressorLabel("Setting variables...")
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
    cwdName = "Site_CWD"
    clucwdName = "Site_CLU_CWD"
    prevcwdName = "Site_Previous_CLU_CWD"
    imageName = imagery

    #### Set up log file path and start logging
    arcpy.AddMessage("Commence logging...\n")
    arcpy.SetProgressorLabel("Commence logging...")
    textFilePath = userWorkspace + os.sep + projectName + "_log.txt"
    logBasicSettings()


    #### Setup output PDF file name(s)
    arcpy.SetProgressorLabel("Configuring output file names...")
    outPDF = wetDir + os.sep + "Previous_Determinations_Map_" + projectName + ".pdf"
    # If overwrite existing maps is checked, use standard file name
    if owDetLayout == True:
        outPDF = wetDir + os.sep + "Previous_Determinations_Map_" + projectName + ".pdf"
    
    # Else enumerate the output map name(s)
    else:
        if os.path.exists(outPDF):
            count = 1
            while count > 0:
                outPDF = wetDir + os.sep + "Previous_Determinations_Map_" + projectName + "_" + str(count) + ".pdf"
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
            arcpy.AddMessage("The project's Previous Determinations Map PDF file is available to overwrite!")
            os.rename(myfile + "_opentest", myfile)
        except:
            arcpy.AddMessage("The Previous Determinations Map PDF file is open or in use by another program. Please close the PDF and try running this tool again. Exiting...")
            exit()
    else:
        arcpy.AddMessage("The Previous Determinations Map PDF file does not exist for this project and will be created.")


    #### Retrieve PLSS Text for Determination Map, if applicable
    # Set starting boolean for location text box. Stays false unless all query criteria to show location are met
    display_dm_location = False
    dm_plss_text = ''
        
    if showLocation:
        AddMsgAndPrint("\nShow location selected for Previous Determinations Map. Processing reference location...",0)
        arcpy.SetProgressorLabel("Retrieving PLSS Location...")
        dm_plss_text = getPLSS(plssPoint)
        if dm_plss_text != '':
            AddMsgAndPrint("\nThe PLSS query was successful and a location text box will be shown on the Previous Determinations Map.",0)
            display_dm_location = True
               
    # If any part of the PLSS query failed, or if show location was not enabled, then do not show the Location text box
    if display_dm_location == False:
        AddMsgAndPrint("\tEither the Show Location parameter was not enabled or the PLSS query failed.",0)
        AddMsgAndPrint("\tA Town, Range, Section text box will not be shown on the Previous Determinations Map.",0)
            

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
    arcpy.SetProgressorLabel("Updating map headers...")
    # Get Map layout
    try:
        dm_lyt = aprx.listLayouts("Previous Determination Map")[0]
    except:
        AddMsgAndPrint("\nCould not find installed Previous Determination Map layout. Exiting...",2)
        exit()

    # Send information to function to set the layout elements
    setLytElements(dm_lyt, adm_Co_Name, geo_Co_Name, farm_Num, tr_Num, client_Name, dig_staff, imageName, dm_plss_text)


    #### Manage layers as objects for visibility and movement control
    AddMsgAndPrint("\nPreparing map layers for display on the Previous Determination Map layout...",0)
    arcpy.SetProgressorLabel("Prepping map layers for display...")

    cwd_lyr = m.listLayers(cwdName)[0]
    clucwd_lyr = m.listLayers(clucwdName)[0]
    prev_cwd_lyr = m.listLayers(prevcwdName)[0]

    plss_lyr = ''
    if plssPoint:
        plssDesc = arcpy.Describe(plssPoint)
        if plssDesc.dataType == "FeatureLayer":
            try:
                plss_lyr = m.listLayers(plssPoint)[0]
            except:
                plss_lyr = ''

    # Turn on the visibility of the specified image layer
    try:
        image_lyr.visible = True
    except:
        AddMsgAndPrint("\nCannot make specified imagery layer visible. Please run again and select an image layer from within the map contents. Exiting...",2)
        exit()
        
    # Find annotation for the typical layers, if any
    lyrs = m.listLayers()

##    prev_cwd_anno_list = []
##    for lyr in lyrs:
##        if lyr.name.startswith(prevcwdName + "Anno"):
##            prev_cwd_anno_list.append(lyr.name)
##    if len(prev_cwd_anno_list) > 1:
##        AddMsgAndPrint("\tThe map contains more than one Site Previous CLU CWD Annotation layer.",2)
##        AddMsgAndPrint("\tPlease remove any EXTRA Site Previous CLU CWD Annotation layers and run this tool again. Exiting...",2)
##        exit()
##    
##    cwd_anno_list = []
##    for lyr in lyrs:
##        if lyr.name.startswith(cwdName + "Anno"):
##            cwd_anno_list.append(lyr.name)
##    if len(cwd_anno_list) > 1:
##        AddMsgAndPrint("\tThe map contains more than one CWD Annotation layer.",2)
##        AddMsgAndPrint("\tPlease remove any EXTRA CWD Annotation layers and run this tool again. Exiting...",2)
##        exit()
##
##    clucwd_anno_list = []
##    for lyr in lyrs:
##        if lyr.name.startswith(clucwdName + "Anno"):
##            clucwd_anno_list.append(lyr.name)
##    if len(clucwd_anno_list) > 1:
##        AddMsgAndPrint("\tThe map contains more than one CLU CWD Annotation layer.",2)
##        AddMsgAndPrint("\tPlease remove any EXTRA CLU CWD Annotation layers and run this tool again. Exiting...",2)
##        exit()
##
##    prev_cwd_anno_lyr = ''
##    if len(prev_cwd_anno_list) == 1:
##        prev_cwd_anno_lyr = m.listLayers(prev_cwd_anno_list[0])
##        
##    cwd_anno_lyr = ''
##    if len(cwd_anno_list) == 1:
##        cwd_anno_lyr = m.listLayers(cwd_anno_list[0])
##
##    clucwd_anno_lyr = ''
##    if len(clucwd_anno_list) == 1:
##        clucwd_anno_lyr = m.listLayers(clucwd_anno_list[0])


    #### Start exporting maps
    #####################################################################################################
    ################################# PREVIOUS  DETERMINATION MAP START #################################
    #####################################################################################################
    AddMsgAndPrint("\nCreating the Previous Determinations Map PDF file...",0)
    arcpy.SetProgressorLabel("Creating Previous Determination Map...")

    # Zoom to specified extent if applicable
    if zoomType == "Zoom to a layer":
        mf = dm_lyt.listElements('MAPFRAME_ELEMENT', "Map Frame")[0]
        lyr = m.listLayers(zoomLyr)[0]
        ext = mf.getLayerExtent(lyr)
        cam = mf.camera
        cam.setExtent(ext)
        cam.scale *= 1.25
        del lyr

    # Set required layers and corresponding annotation or labels to be visible
    prev_cwd_lyr.visible = True
    cwd_lyr.visible = False
    clucwd_lyr.visible = False
    
##    if arcpy.Exists(prev_cwd_anno_lyr):
##        prev_cwd_anno_lyr.visible = True
##        prev_cwd_lyr.showLabels = False
##    else:
##        prev_cwd_lyr.showLabels = True
##        
##    if arcpy.Exists(cwd_anno_lyr):
##        cwd_anno_lyr.visible = False
##        
##    if arcpy.Exists(clucwd_anno_lyr):
##        clucwd_anno_lyr.visible = False

    # Set the legend elements for contingent visibility options
    dm_leg = dm_lyt.listElements('LEGEND_ELEMENT')[0]
    for item in dm_leg.items:
        item.showVisibleFeatures = True

    # Set the plss input layer to not be visible, if it was used
    if plssPoint:
        try:
            plss_lyr.visible = False
        except:
            pass
            
    # Export the map
    AddMsgAndPrint("\tExporting the Previous Determinations Map to PDF...",0)
    arcpy.SetProgressorLabel("Exporting Previous Determination Map...")
    dm_lyt.exportToPDF(outPDF, resolution=300, image_quality="NORMAL", layers_attributes="LAYERS_AND_ATTRIBUTES", georef_info=True)
    AddMsgAndPrint("\tPrevious Determinations Map file exported!",0)


    #### MAINTENANCE
    # Look for and delete anything else that may remain in the installed SCRATCH.gdb
    startWorkspace = arcpy.env.workspace
    arcpy.env.workspace = scratchGDB

    ## Reset image text on each layout to be blank
    # Define the imagery text box elements
    for elm in dm_lyt.listElements():
        if elm.name == "Imagery Text Box":
            dm_imagery_elm = elm

    dflt_img_text = " Image: "
    dm_imagery_elm.text = dflt_img_text
    
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
    
    # Compact FGDB
    try:
        AddMsgAndPrint("\nCompacting File Geodatabases..." ,0)
        arcpy.SetProgressorLabel("Compacting File Geodatabases...")
        arcpy.Compact_management(basedataGDB_path)
        arcpy.Compact_management(wcGDB_path)
        AddMsgAndPrint("\tSuccessful",0)
    except:
        pass
    
    AddMsgAndPrint("\nThe Previous Determinations Map has been created and exported! Exiting...",0)

except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested...exiting.")
