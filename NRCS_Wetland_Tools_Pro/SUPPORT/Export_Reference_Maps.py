## ===============================================================================================================
## Name:    Export Reference Maps
## Purpose: Export a series of reference data maps for the site.
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
## Created: 07/19/2021
##
## ===============================================================================================================
## Changes
## ===============================================================================================================
##
## rev. 06/21/2021
## - Start revisions of Export Base Map tool to retool to reference maps.
##
## rev. 01/20/2022
## - Added handling for specifiying imagery layer to display in a map text box.
## - Added automatic control of legends to only show features in map extent and to hide the imagery layer.
## - Added SSURGO Version date string
##
## rev. 02/08/2022
## - Added SSURGO Metadata report PDF to outputs
## - Blocked out annotation related code. Annotation will be handled through training/documentation
##
## rev. 03/15/2022
## - Adjusted Hydric Rating by Map Unit to be "Hydric Classification" for more consistent terminology
## - Modified the legend of the Hydric Classification output to show all classes, not just classes of visible items
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
    f.write("Executing Export Reference Maps tool...\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("User Parameters:\n")
    f.write("\tInput CLU Layer: " + arcpy.Describe(sourceCLU).CatalogPath + "\n")
    f.write("\tZoom method: " + zoomType + "\n")
    if zoomType == "Zoom to a layer":
        f.write("\tZoom layer: " + zoomLyr + "\n")
    f.write("\tElevation - Contours Map: " + str(ctr_map) + "\n")
    f.write("\tElevation - Contours and DEM Map: " + str(dem_map) + "\n")
    f.write("\tElevation - Depth Grid Map: " + str(depth_map) + "\n")
    f.write("\tElevation - Slope Map: " + str(slope_map) + "\n")
    f.write("\tNational Wetland Inventory Map: " + str(nwi_map) + "\n")
    f.write("\tSoil Map Units Map: " + str(mu_map) + "\n")
    f.write("\tSSURGO Drainage Class DCD Map: " + str(drain_map) + "\n")
    f.write("\tSSURGO Ecological Classification Map: " + str(eco_map) + "\n")
    f.write("\tSSURGO Flooding Frequency Map: " + str(flood_map) + "\n")
##    f.write("\tSSURGO Hydric Condition DCD Map: " + str(hydricCon_map) + "\n")
    f.write("\tSSURGO Hydric Classification: " + str(hydricMU_map) + "\n")
##    f.write("\tSSURGO Hydric Rating Component Map: " + str(hydricCOMP_map) + "\n")
    f.write("\tSSURGO Hydrologic Soil Group DCD Map: " + str(hydrologic_map) + "\n")
    f.write("\tSSURGO Ponding Frequency Class Map: " + str(ponding_map) + "\n")
    f.write("\tSSURGO Water Table Depth Annual Min Map: " + str(wtrtbl_map) + "\n")
    if showLocation:
        f.write("\tShow PLSS Location Text Box: True\n")
    else:
        f.write("\tShow PLSS Location Text Box: False\n")
    if owLayouts:
        f.write("\tOverwrite Reference Maps: True\n")
    else:
        f.write("\tOverwrite Reference Maps: False\n")
    if multiLayouts:
        f.write("\tSeperate PDF files: True\n")
    else:
        f.write("\tSeperate PDF files: False\n")
    f.write("\tImage Layer Selected: " + imagery + "\n")
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
def setZoom(layout, extent, scale_up="No"):
    # Sets a zoom extent for a specified layout using a provided extent object
    mapframe = layout.listElements('MAPFRAME_ELEMENT', "Map Frame")[0]
    mf_cam = mapframe.camera
    mf_cam.setExtent(extent)
    if scale_up == "Yes":
        mf_cam.scale *= 1.25
    del mapframe, mf_cam

## ================================================================================================================
def visibility_off(layer_list):
    # Input should be a list of layer objects
    # Turns off visibility for all layers in the list
    
    for layer in layer_list:
        try:
            layer.visible = False
        except:
            pass
    
## ================================================================================================================
#### Import system modules
import arcpy, sys, os, traceback, re
arcpy.AddMessage("Performing imports...\n")
arcpy.SetProgressorLabel("Performing imports...")
import urllib, json, time
import shutil
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
    sourceCLU = arcpy.GetParameterAsText(0)
    zoomType = arcpy.GetParameterAsText(1)
    zoomLyr = arcpy.GetParameterAsText(2)
    mapList = arcpy.GetParameterAsText(3).split(";")
    showLocation = arcpy.GetParameter(4)
    plssPoint = arcpy.GetParameterAsText(5)
    owLayouts = arcpy.GetParameter(6)
    multiLayouts = arcpy.GetParameter(7)
    imagery = arcpy.GetParameterAsText(8)

    site_map = True
    if "'Elevation - Contours'" in mapList:
        ctr_map = True
    else:
        ctr_map = False

    if "'Elevation - Contours and DEM'" in mapList:
        dem_map = True
    else:
        dem_map = False
        
    if "'Elevation - Depth Grid'" in mapList:
        depth_map = True
    else:
        depth_map = False

    if "'Elevation - Slope'" in mapList:
        slope_map = True
    else:
        slope_map = False

    if "'National Wetland Inventory'" in mapList:
        nwi_map = True
    else:
        nwi_map = False

    if "'Soil Map Units'" in mapList:
        mu_map = True
    else:
        mu_map = False

    if "'SSURGO Drainage Class DCD'" in mapList:
        drain_map = True
    else:
        drain_map = False

    if "'SSURGO Ecological Classification'" in mapList:
        eco_map = True
    else:
        eco_map = False

    if "'SSURGO Flooding Frequency'" in mapList:
        flood_map = True
    else:
        flood_map = False

##    if "'SSURGO Hydric Condition DCD'" in mapList:
##        hydricCon_map = True
##    else:
##        hydricCon_map = False

    if "'SSURGO Hydric Classification'" in mapList:
        hydricMU_map = True
    else:
        hydricMU_map = False

    if "'SSURGO Hydric Rating by Component'" in mapList:
        hydricCOMP_map = True
    else:
        hydricCOMP_map = False

    if "'SSURGO Hydrologic Soil Group DCD'" in mapList:
        hydrologic_map = True
    else:
        hydrologic_map = False

    if "'SSURGO Ponding Frequency Class'" in mapList:
        ponding_map = True
    else:
        ponding_map = False

    if "'SSURGO Water Table Depth Annual Min'" in mapList:
        wtrtbl_map= True
    else:
        wtrtbl_map= False


    #### Initial Validations
    arcpy.AddMessage("Verifying inputs...\n")
    arcpy.SetProgressorLabel("Verifying inputs...")
    sourceCLU_path = arcpy.Describe(sourceCLU).CatalogPath
    if sourceCLU_path.find('.gdb') > 0 and sourceCLU_path.find('Determinations') > 0 and sourceCLU_path.find('Site_CLU') > 0:
        basedataGDB_path = sourceCLU_path[:sourceCLU_path.find('.gdb')+4]
    else:
        arcpy.AddError("\nSelected Site CLU layer is not from a Determinations project folder. Exiting...")
        exit()
        

    #### Define Variables
    arcpy.AddMessage("Setting variables...\n")
    arcpy.SetProgressorLabel("Setting variables...")
    
    supportGDB = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb")
    scratchGDB = os.path.join(os.path.dirname(sys.argv[0]), "SCRATCH.gdb")

    userWorkspace = os.path.dirname(basedataGDB_path)
    projectName = os.path.basename(userWorkspace).replace(" ", "_")
    basedataGDB_name = os.path.basename(basedataGDB_path)
    basedataFD_name = "Layers"
    basedataFD = basedataGDB_path + os.sep + basedataFD_name
    wetDir = userWorkspace + os.sep + "Wetlands"
    wcGDB_path = wetDir + os.sep + projectName + "_WC.gdb"
    wcFD = wcGDB_path + os.sep + "WC_Data"
    wcGDB_name = os.path.basename(wcGDB_path)
    
    projectTable = basedataGDB_path + os.sep + "Table_" + projectName

    ssurgo_meta = os.path.join(os.path.dirname(sys.argv[0]), "WCT_SSURGO_Metadata.pdf")

    cluName = "Site_CLU"
    ctrName = "Site_Contours"
    demName = "Site_DEM"
    slopeName = "Site_Slope_Pct"
    hillName = "Site_Hillshade"
    depthName = "Site_Depth_Grid"
    nwiName = "Site_NWI"
    ssurgoGroup = "SSURGO Layers"
    muName = "SSURGO Mapunits"
    ecoName = "Ecological Classification Name"
    wtrtblName = "Water Table Depth - Annual - Minimum"
    pondingName = "Ponding Frequency Class"
    hydrologicName = "Hydrologic Soil Group - Dom. Cond."
    hydricMuName = "Hydric Classification"
    hydricCompName = "Hydric Rating by Component"
##    hydricConName = "Hydric Condition - Dom. Cond."
    floodName = "Flooding Frequency"
    drainName = "Drainage Class Dom. Cond."
    imageName = imagery

    project_soils = basedataGDB_path + os.sep + "SSURGO_Mapunits"
    
    #### Set up log file path and start logging
    arcpy.AddMessage("Commence logging...\n")
    arcpy.SetProgressorLabel("Commence logging...")
    textFilePath = userWorkspace + os.sep + projectName + "_log.txt"
    logBasicSettings()


##    #### Do not run if any unsaved edits exist in the target workspace
##    # Pro opens an edit session when any edit has been made and stays open until edits are committed with Save Edits.
##    # Check for uncommitted edits and exit if found, giving the user a message directing them to Save or Discard them.
##    workspace = wcGDB_path
##    edit = arcpy.da.Editor(workspace)
##    if edit.isEditing:
##        arcpy.AddError("\nThere are unsaved data edits in this project. Please Save or Discard Edits and then run this tool again. Exiting...")
##        exit()
##    del workspace, edit

    
    #### Setup output PDF file name(s)
    AddMsgAndPrint("\nManaging output file names...",0)
    arcpy.SetProgressorLabel("Managing output file names...")
    outPDF = wetDir + os.sep + "Reference_Maps_" + projectName + ".pdf"
    sitePDF = wetDir + os.sep + "Site_" + projectName + ".pdf"
    ctrPDF = wetDir + os.sep + "Contours_" + projectName + ".pdf"
    demPDF = wetDir + os.sep + "DEM_" + projectName + ".pdf"
    depthPDF = wetDir + os.sep + "Depth_Grid_" + projectName + ".pdf"
    slopePDF = wetDir + os.sep + "Slope_" + projectName + ".pdf"
    nwiPDF = wetDir + os.sep + "NWI_" + projectName + ".pdf"
    soilPDF = wetDir + os.sep + "Map_Units_" + projectName + ".pdf"
    drainPDF = wetDir + os.sep + "Drainage_Class_" + projectName + ".pdf"
    ecoPDF = wetDir + os.sep + "Ecological_Classification_" + projectName + ".pdf"
    floodPDF = wetDir + os.sep + "Flooding_Frequency_" + projectName + ".pdf"
##    hydricConPDF = wetDir + os.sep + "Hydric_Condition_" + projectName + ".pdf"
    hydricRatMuPDF = wetDir + os.sep + "Hydric_Rating_MU_" + projectName + ".pdf"
    hydricRatCompPDF = wetDir + os.sep + "Hydric_Rating_Comp_" + projectName + ".pdf"
    hydrologicPDF = wetDir + os.sep + "Hydrologic_Groups_" + projectName + ".pdf"
    pondingPDF = wetDir + os.sep + "Ponding_" + projectName + ".pdf"
    wtrtblPDF = wetDir + os.sep + "Water_Table_" + projectName + ".pdf"
    metadataPDF = wetDir + os.sep + "SSURGO_Metadata_" + projectName + ".pdf"

    PDFlist = [sitePDF, ctrPDF, demPDF, depthPDF, slopePDF, nwiPDF, soilPDF, drainPDF, ecoPDF,
               floodPDF, hydricRatMuPDF, hydricRatCompPDF, hydrologicPDF, pondingPDF, wtrtblPDF,
               metadataPDF]
    
    if owLayouts == False:
        if os.path.exists(outPDF):
            count = 1
            while count > 0:
                outPDF = wetDir + os.sep + "Reference_Maps_" + projectName + "_" + str(count) + ".pdf"
                sitePDF = wetDir + os.sep + "Site_" + projectName + "_" + str(count) + ".pdf"
                ctrPDF = wetDir + os.sep + "Contours_" + projectName + "_" + str(count) + ".pdf"
                demPDF = wetDir + os.sep + "DEM_" + projectName + "_" + str(count) + ".pdf"
                depthPDF = wetDir + os.sep + "Depth_Grid_" + projectName + "_" + str(count) + ".pdf"
                slopePDF = wetDir + os.sep + "Slope_" + projectName + "_" + str(count) + ".pdf"
                nwiPDF = wetDir + os.sep + "NWI_" + projectName + "_" + str(count) + ".pdf"
                soilPDF = wetDir + os.sep + "Map_Units_" + projectName + "_" + str(count) + ".pdf"
                drainPDF = wetDir + os.sep + "Drainage_Class_" + projectName + "_" + str(count) + ".pdf"
                ecoPDF = wetDir + os.sep + "Ecological_Classification_" + projectName + "_" + str(count) + ".pdf"
                floodPDF = wetDir + os.sep + "Flooding_Frequency_" + projectName + "_" + str(count) + ".pdf"
##                hydricConPDF = wetDir + os.sep + "Hydric_Condition_" + projectName + "_" + str(count) + ".pdf"
                hydricRatMuPDF = wetDir + os.sep + "Hydric_Rating_MU_" + projectName + "_" + str(count) + ".pdf"
                hydricRatCompPDF = wetDir + os.sep + "Hydric_Rating_Comp_" + projectName + "_" + str(count) + ".pdf"
                hydrologicPDF = wetDir + os.sep + "Hydrologic_Groups_" + projectName + "_" + str(count) + ".pdf"
                pondingPDF = wetDir + os.sep + "Ponding_" + projectName + "_" + str(count) + ".pdf"
                wtrtblPDF = wetDir + os.sep + "Water_Table_" + projectName + "_" + str(count) + ".pdf"
                metadataPDF = wetDir + os.sep + "SSURGO_Metadata_" + projectName + "_" + str(count) + ".pdf"

                if os.path.exists(outPDF):
                    count += 1
                else:
                    count = 0
    else:
        # Overwrite is enabled. Delete files.
        # outPDF is handled outside of the list, because the list is used again to cleanup temp maps at the end.
        try:
            os.remove(outPDF)
        except:
            pass
        
        PDFlist = [sitePDF, ctrPDF, demPDF, depthPDF, slopePDF, nwiPDF, soilPDF, drainPDF, ecoPDF,
                   floodPDF, hydricRatMuPDF, hydricRatCompPDF, hydrologicPDF, pondingPDF, wtrtblPDF,
                   metadataPDF]
        for item in PDFlist:
            try:
                os.remove(item)
            except:
                pass
            
    # Check if the output PDF file name(s) is currently open in another application.
    # If we can't create a file with the same name, then exit (because that name is in use/locked).
    # In this case, we use PDFDocumentCreate because we are building a generic PDF doc to which we will add each exported map
    # The separate maps scenario always creates a new file name so will pass this check without issue, and actually will end up not using finalPDF
    try:
        finalPDF = arcpy.mp.PDFDocumentCreate(outPDF)
    except:
        AddMsgAndPrint("\nThe reference Maps PDF file is open or in use by another program. Please close the PDF and try running this tool again. Exiting...",2)
        exit()


    #### Copy the metadata map file to the project folder
    try:
        shutil.copy2(ssurgo_meta, metadataPDF)
    except:
        AddMsgAndPrint("\nMetadata PDF file is open or missing. Please close the Metadata PDF if it is open and try running this tool again. Exiting...",2)
        exit()
        
    #### Retrieve PLSS Text for Output Maps, if applicable
    # Set starting boolean for location text box. Stays false unless all query criteria to show location are met
    display_location = False
    plss_text = ''
        
    if showLocation:
        AddMsgAndPrint("\nShow location selected. Processing reference location...",0)
        arcpy.SetProgressorLabel("Processing reference location...")
        plss_text = getPLSS(plssPoint)
        if plss_text != '':
            AddMsgAndPrint("\nThe PLSS query was successful and a location text box will be shown on the output map(s).",0)
            display_location = True
    
    # If any part of the PLSS query failed, or if show location was not enabled, then do not show the Location text box
    if display_location == False:
        AddMsgAndPrint("\tEither the Show Location parameter was not enabled or the PLSS query failed.",0)
        AddMsgAndPrint("\tA Town, Range, Section text box will not be shown on the output map(s).",0)


    #### Harvest project based data from the project table to use on the layout
    if arcpy.Exists(projectTable):
        AddMsgAndPrint("\nCollecting header information from project table...",0)
        arcpy.SetProgressorLabel("Collecting map header info...")
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
    arcpy.SetProgressorLabel("Updating layout elements...")
    # Get various layouts
    try:
        lm_lyt = aprx.listLayouts("Location Map")[0]
    except:
        AddMsgAndPrint("\nCould not find installed Location Map layout. Exiting...",2)
        exit()

    try:
        elev_lyt = aprx.listLayouts("Elevation Map")[0]
    except:
        AddMsgAndPrint("\nCould not find installed Elevation Map layout. Exiting...",2)
        exit()

    try:
        nwi_lyt = aprx.listLayouts("NWI Map")[0]
    except:
        AddMsgAndPrint("\nCould not find installed NWI Map layout. Exiting...",2)
        exit()

    try:
        soil_lyt = aprx.listLayouts("Soil Map")[0]
    except:
        AddMsgAndPrint("\nCould not find installed Soil Map layout. Exiting...",2)
        exit()
        
    # Send information to function to set the layout elements
    setLytElements(lm_lyt, adm_Co_Name, geo_Co_Name, farm_Num, tr_Num, client_Name, dig_staff, imageName, plss_text)
    setLytElements(elev_lyt, adm_Co_Name, geo_Co_Name, farm_Num, tr_Num, client_Name, dig_staff, imageName, plss_text)
    setLytElements(nwi_lyt, adm_Co_Name, geo_Co_Name, farm_Num, tr_Num, client_Name, dig_staff, imageName, plss_text)
    setLytElements(soil_lyt, adm_Co_Name, geo_Co_Name, farm_Num, tr_Num, client_Name, dig_staff, imageName, plss_text)


    #### Create map layer objects for visibility and movement control
    AddMsgAndPrint("\nPreparing map layers for display...",0)
    arcpy.SetProgressorLabel("Preparing map layers...")

    clu_lyr = m.listLayers(cluName)[0]
    try:
        ctr_lyr = m.listLayers(ctrName)[0]
    except:
        ctr_lyr = ''
    try:
        dem_lyr = m.listLayers(demName)[0]
    except:
        dem_lyr = ''
    try:
        slp_lyr = m.listLayers(slopeName)[0]
    except:
        slp_lyr = ''
    try:
        hill_lyr = m.listLayers(hillName)[0]
    except:
        hill_lyr = ''
    try:
        depth_lyr = m.listLayers(depthName)[0]
    except:
        depth_lyr = ''
    try:
        nwi_lyr = m.listLayers(nwiName)[0]
    except:
        nwi_lyr = ''
    try:
        sgroup_lyr = m.listLayers(ssurgoGroup)[0]
    except:
        sgroup_lyr = ''
    try:
        mu_lyr = m.listLayers(muName)[0]
    except:
        mu_lyr = ''
    try:
        eco_lyr = m.listLayers(ecoName)[0]
    except:
        eco_lyr = ''
    try:
        wtrtbl_lyr = m.listLayers(wtrtblName)[0]
    except:
        wtrtbl_lyr = ''
    try:
        ponding_lyr = m.listLayers(pondingName)[0]
    except:
        ponding_lyr = ''
    try:
        hydrologic_lyr = m.listLayers(hydrologicName)[0]
    except:
        hydrologic_lyr = ''
    try:
        hydricMu_lyr = m.listLayers(hydricMuName)[0]
    except:
        hydricMu_lyr = ''
    try:
        hydricComp_lyr = m.listLayers(hydricCompName)[0]
    except:
        hydricComp_lyr = ''
##    try:
##        hydricCon_lyr = m.listLayers(hydricConName)[0]
##    except:
##        hydricCon_lyr = ''
    try:
        flood_lyr = m.listLayers(floodName)[0]
    except:
        flood_lyr = ''
    try:
        drain_lyr = m.listLayers(drainName)[0]
    except:
        drain_lyr = ''

    try:
        image_lyr = m.listLayers(imageName)[0]
    except:
        image_lyr = ''

    plss_lyr = ''
    if plssPoint:
        plssDesc = arcpy.Describe(plssPoint)
        if plssDesc.dataType == "FeatureLayer":
            try:
                plss_lyr = m.listLayers(plssPoint)[0]
            except:
                plss_lyr = ''
                
    # Turn off visibility of operational layers to start, except CLU
    lyr_list = [ctr_lyr, dem_lyr, slp_lyr, hill_lyr, depth_lyr, nwi_lyr, sgroup_lyr, mu_lyr,
                eco_lyr, wtrtbl_lyr, ponding_lyr, hydrologic_lyr, hydricMu_lyr, hydricComp_lyr,
                flood_lyr, drain_lyr]

    visibility_off(lyr_list)

    # Turn on the visibility of the specified image layer
    try:
        image_lyr.visible = True
    except:
        AddMsgAndPrint("\nCannot make specified imagery layer visible. Please run again and select an image layer from within the map contents. Exiting...",2)
        exit()

    # There is no check to set the order for the image layer. If users run it wrong, results should be self evident, they should re-arrange and re-run.

    # Get the elevation layout title for use
    for elm in elev_lyt.listElements():
        if elm.name == "Title":
            elev_title_elm = elm

    # Get the soil layout title and SSURGO Date object for use
    for elm in soil_lyt.listElements():
        if elm.name == "Title":
            soil_title_elm = elm
        if elm.name == "SSURGO Date":
            soil_version_elm = elm
        
    ## Setup the SSURGO Date text string on the soil map layout
    # Search the first row of the map units layer for the saversion and surveyareadate attributes
    if arcpy.Exists(project_soils):
        field_names = ['saversion','surveyareadate']
        with arcpy.da.SearchCursor(project_soils, field_names) as cursor:
            for row in cursor:
                ssa_ver = str(row[0])
                ver_date = row[1]
                break

        # Set the version string
        if ssa_ver != '':
            if ver_date != '':
                fmt_ver_date = ver_date[5:7] + """/""" + ver_date[8:] + """/""" + ver_date[0:4]
                version_string = "Survey Version: " + ssa_ver + ", " + fmt_ver_date
            else:
                version_string = "Survey Version: <Data missing>"
        else:
            version_string = "Survey Version: <Data missing>"

    else:
        version_string = "Survey Version: <Data missing>"

    # Update the soil layout with the version string
    soil_version_elm.text = version_string
    
    # Set starting zoom flags
    update_elev_zoom = False
    update_soil_zoom = False

    
    #### Start exporting maps
    #####################################################################################################
    ########################################## SITE MAP START ###########################################
    #####################################################################################################
    AddMsgAndPrint("\nCreating the Site Map PDF file...",0)
    arcpy.SetProgressorLabel("Creating Site Map...")

    # Zoom to specified extent if applicable (perform for the site map as the basis for all other maps)
    if zoomType == "Zoom to a layer":
        mf = lm_lyt.listElements('MAPFRAME_ELEMENT', "Map Frame")[0]
        lyr = m.listLayers(zoomLyr)[0]
        ext = mf.getLayerExtent(lyr)
        cam = mf.camera
        cam.setExtent(ext)
        cam.scale *= 1.25
        del lyr
    else:
        # Get the current extent of the location map layout to use on all other maps
        mf = lm_lyt.listElements('MAPFRAME_ELEMENT', "Map Frame")[0]
        cam = mf.camera
        ext = cam.getExtent()
        
    # Set required layers to be visible
    clu_lyr.visible = True
    
    # Set the plss input layer to be not visible, if it was used
    if plssPoint:
        try:
            plss_lyr.visible = False
        except:
            pass
            
    # Export the map
    AddMsgAndPrint("\tExporting the Site Map to PDF...",0)
    arcpy.SetProgressorLabel("Exporting Site Map...")
    lm_lyt.exportToPDF(sitePDF, resolution=300, image_quality="NORMAL", layers_attributes="LAYERS_AND_ATTRIBUTES", georef_info=True)
    AddMsgAndPrint("\tBase Map file exported!",0)

    # Reset visibility
    visibility_off(lyr_list)

    
    #####################################################################################################
    ######################################## CONTOUR MAP START ##########################################
    #####################################################################################################
    if ctr_map:
        AddMsgAndPrint("\nCreating the Contour Map PDF file...",0)
        arcpy.SetProgressorLabel("Creating Contour Map...")

        # Proceed if operational layer(s) actually exist(s) in the map
        if ctr_lyr != '':
            if update_elev_zoom == False:
                # Set zoom and visiblility
                if zoomType == "Zoom to a layer":
                    setZoom(elev_lyt, ext, "Yes")
                else:
                    setZoom(elev_lyt, ext)
                update_elev_zoom = True

            ctr_lyr.visible = True
            ctr_lyr.showLabels = True

            # Update the title
            elev_title_elm.text = "Contours"

            # Export the map
            AddMsgAndPrint("\tExporting the Contour Map to PDF...",0)
            arcpy.SetProgressorLabel("Exporting Contour Map...")
            elev_lyt.exportToPDF(ctrPDF, resolution=300, image_quality="NORMAL", layers_attributes="LAYERS_AND_ATTRIBUTES", georef_info=True)
            AddMsgAndPrint("\tBase Map file exported!",0)

            # Reset visibility
            visibility_off(lyr_list)

        else:
            AddMsgAndPrint("\nContour layer not in map. Cannot create Contour Map. Continuing to next map...",1)


    #####################################################################################################
    ########################################## DEM MAP START ############################################
    #####################################################################################################
    if dem_map:
        AddMsgAndPrint("\nCreating the DEM Map PDF file...",0)
        arcpy.SetProgressorLabel("Creating DEM Map...")

        # Proceed if operational layer(s) actually exist(s) in the map
        if dem_lyr != '' and hill_lyr != '':
            if update_elev_zoom == False:
                # Set zoom and visiblility
                if zoomType == "Zoom to a layer":
                    setZoom(elev_lyt, ext, "Yes")
                else:
                    setZoom(elev_lyt, ext)
                update_elev_zoom = True

            dem_lyr.visible = True
            hill_lyr.visible = True
        
            elev_leg = elev_lyt.listElements('LEGEND_ELEMENT')[0]
            for item in elev_leg.items:
                if item.name == hillName:
                    item.visible = False

            # Update the title
            elev_title_elm.text = "Elevation"

            # Export the map
            AddMsgAndPrint("\tExporting the DEM Map to PDF...",0)
            arcpy.SetProgressorLabel("Exporting DEM Map...")
            elev_lyt.exportToPDF(demPDF, resolution=300, image_quality="NORMAL", layers_attributes="LAYERS_AND_ATTRIBUTES", georef_info=True)
            AddMsgAndPrint("\tDEM Map file exported!",0)

            # Reset visibility
            visibility_off(lyr_list)

        else:
            AddMsgAndPrint("\nDEM, and/or Hillshade layer(s) not in map. Cannot create DEM Map. Continuing to next map...",1)


    #####################################################################################################
    ######################################### SLOPE MAP START ###########################################
    #####################################################################################################
    if slope_map:
        AddMsgAndPrint("\nCreating the Slope Map PDF file...",0)
        arcpy.SetProgressorLabel("Creating Slope Map...")

        # Proceed if operational layer(s) actually exist(s) in the map
        if slp_lyr != '' and hill_lyr != '':
            if update_elev_zoom == False:
                # Set zoom and visiblility
                if zoomType == "Zoom to a layer":
                    setZoom(elev_lyt, ext, "Yes")
                else:
                    setZoom(elev_lyt, ext)
                update_elev_zoom = True
                
            slp_lyr.visible = True
            hill_lyr.visible = True

            elev_leg = elev_lyt.listElements('LEGEND_ELEMENT')[0]
            for item in elev_leg.items:
                if item.name == hillName:
                    item.visible = False

            # Update the title
            elev_title_elm.text = "Slope"

            # Export the map
            AddMsgAndPrint("\tExporting the Slope Map to PDF...",0)
            arcpy.SetProgressorLabel("Exporting Slope Map...")
            elev_lyt.exportToPDF(slopePDF, resolution=300, image_quality="NORMAL", layers_attributes="LAYERS_AND_ATTRIBUTES", georef_info=True)
            AddMsgAndPrint("\tSlope Map file exported!",0)

            # Reset visibility
            visibility_off(lyr_list)

        else:
            AddMsgAndPrint("\nSlope and/or Hillshade layer(s) not in map. Cannot create Slope Map. Continuing to next map...",1)
            

    #####################################################################################################
    ######################################### DEPTH MAP START ###########################################
    #####################################################################################################
    if depth_map:
        AddMsgAndPrint("\nCreating the Depth Grid Map PDF file...",0)
        arcpy.SetProgressorLabel("Creating Depth Grid Map...")

        # Proceed if operational layer(s) actually exist(s) in the map
        if depth_lyr != '':
            if update_elev_zoom == False:
                # Set zoom and visiblility
                if zoomType == "Zoom to a layer":
                    setZoom(elev_lyt, ext, "Yes")
                else:
                    setZoom(elev_lyt, ext)
                update_elev_zoom = True
                
            depth_lyr.visible = True

            # Update the title
            elev_title_elm.text = "Depth Grid"

            # Export the map
            AddMsgAndPrint("\tExporting the Depth Grid Map to PDF...",0)
            arcpy.SetProgressorLabel("Exporting Depth Grid Map...")
            elev_lyt.exportToPDF(depthPDF, resolution=300, image_quality="NORMAL", layers_attributes="LAYERS_AND_ATTRIBUTES", georef_info=True)
            AddMsgAndPrint("\tDepth Grid Map file exported!",0)

            # Reset visibility
            visibility_off(lyr_list)

        else:
            AddMsgAndPrint("\nDepth layer not in map. Cannot create Depth Grid Map. Continuing to next map...",1)


    #####################################################################################################
    ########################################## NWI MAP START ############################################
    #####################################################################################################
    if nwi_map:
        AddMsgAndPrint("\nCreating the NWI Map PDF file...",0)
        arcpy.SetProgressorLabel("Creating NWI Map...")

        # Proceed if operational layer(s) actually exist(s) in the map
        if nwi_lyr != '':
            # Set zoom and visiblility
            if zoomType == "Zoom to a layer":
                setZoom(nwi_lyt, ext, "Yes")
            else:
                setZoom(nwi_lyt, ext)
                
            nwi_lyr.visible = True

            # Set the legend to only show nwi features that are visible in the map
            nwi_leg = nwi_lyt.listElements('LEGEND_ELEMENT')[0]
            for item in nwi_leg.items:
                if item.name == nwiName:
                    item.showVisibleFeatures = True

            # Export the map
            AddMsgAndPrint("\tExporting the NWI Map to PDF...",0)
            arcpy.SetProgressorLabel("Exporting NWI Map...")
            nwi_lyt.exportToPDF(nwiPDF, resolution=300, image_quality="NORMAL", layers_attributes="LAYERS_AND_ATTRIBUTES", georef_info=True)
            AddMsgAndPrint("\tNWI Map file exported!",0)

            # Reset visibility
            visibility_off(lyr_list)

        else:
            AddMsgAndPrint("\nNWI layer not in map. Cannot create NWI Map. Continuing to next map...",1)


    #####################################################################################################
    #################################### SOIL MAP UNITS MAP START #######################################
    #####################################################################################################
    if mu_map:
        AddMsgAndPrint("\nCreating the Soil Map Units PDF file...",0)
        arcpy.SetProgressorLabel("Creating Soil Map Units Map...")

        # Proceed if operational layer(s) actually exist(s) in the map
        if sgroup_lyr != '' and mu_lyr != '':
            if update_soil_zoom == False:
                # Set zoom and visiblility
                if zoomType == "Zoom to a layer":
                    setZoom(soil_lyt, ext, "Yes")
                else:
                    setZoom(soil_lyt, ext)
                update_soil_zoom = True
                
            sgroup_lyr.visible = True
            mu_lyr.visible = True
            mu_lyr.showLabels = True

            # Update the title
            soil_title_elm.text = "Soils"

            # Export the map
            AddMsgAndPrint("\tExporting the Soil Map Units to PDF...",0)
            arcpy.SetProgressorLabel("Exporting Soil Map Units Map...")
            soil_lyt.exportToPDF(soilPDF, resolution=300, image_quality="NORMAL", layers_attributes="LAYERS_AND_ATTRIBUTES", georef_info=True)
            AddMsgAndPrint("\tSoil Map Units file exported!",0)

            # Reset visibility
            visibility_off(lyr_list)

        else:
            AddMsgAndPrint("\nSSURGO Layers group or SSURGO Map Units layer not in map. Cannot create Soil Map Units PDF. Continuing to next map...",1)


    #####################################################################################################
    #################################### DRAINAGE CLASS MAP START #######################################
    #####################################################################################################
    if drain_map:
        AddMsgAndPrint("\nCreating the Drainage Class Map PDF file...",0)
        arcpy.SetProgressorLabel("Creating Drainage Class Map...")

        # Proceed if operational layer(s) actually exist(s) in the map
        if sgroup_lyr != '' and mu_lyr != '' and drain_lyr != '':
            if update_soil_zoom == False:
                # Set zoom and visiblility
                if zoomType == "Zoom to a layer":
                    setZoom(soil_lyt, ext, "Yes")
                else:
                    setZoom(soil_lyt, ext)
                update_soil_zoom = True
                
            sgroup_lyr.visible = True
            mu_lyr.visible = True
            mu_lyr.showLabels = True
            drain_lyr.visible = True
            drain_lyr.showLabels = False

            # Set the legend to only show drainage features that are visible in the map
            soil_leg = soil_lyt.listElements('LEGEND_ELEMENT')[0]
            for item in soil_leg.items:
                if item.name == drainName:
                    item.showVisibleFeatures = True

            # Update the title
            soil_title_elm.text = "Drainage Class"

            # Export the map
            AddMsgAndPrint("\tExporting the Drainage Class Map to PDF...",0)
            arcpy.SetProgressorLabel("Exporting Drainage Class Map...")
            soil_lyt.exportToPDF(drainPDF, resolution=300, image_quality="NORMAL", layers_attributes="LAYERS_AND_ATTRIBUTES", georef_info=True)
            AddMsgAndPrint("\tDrainage Class Map file exported!",0)

            # Reset visibility
            visibility_off(lyr_list)

        else:
            AddMsgAndPrint("\nSSURGO Layers group, SSURGO Map Units layer, or Drainage Class layer not in map. Cannot create Drainage Class Map PDF. Continuing to next map...",1)


    #####################################################################################################
    ################################### ECOLOGICAL CLASS MAP START ######################################
    #####################################################################################################
    if eco_map:
        AddMsgAndPrint("\nCreating the Ecological Classification Map PDF file...",0)
        arcpy.SetProgressorLabel("Creating Ecological Classification Map...")

        # Proceed if operational layer(s) actually exist(s) in the map
        if sgroup_lyr != '' and mu_lyr != '' and eco_lyr != '':
            if update_soil_zoom == False:
                # Set zoom and visiblility
                if zoomType == "Zoom to a layer":
                    setZoom(soil_lyt, ext, "Yes")
                else:
                    setZoom(soil_lyt, ext)
                update_soil_zoom = True
                
            sgroup_lyr.visible = True
            mu_lyr.visible = True
            mu_lyr.showLabels = True
            eco_lyr.visible = True
            eco_lyr.showLabels = False

            # Set the legend to only show ecological features that are visible in the map
            soil_leg = soil_lyt.listElements('LEGEND_ELEMENT')[0]
            for item in soil_leg.items:
                if item.name == ecoName:
                    item.showVisibleFeatures = True

            # Update the title
            soil_title_elm.text = "Ecological Classification"

            # Export the map
            AddMsgAndPrint("\tExporting the Ecological Classification Map to PDF...",0)
            arcpy.SetProgressorLabel("Exporting Ecological Classification Map...")
            soil_lyt.exportToPDF(ecoPDF, resolution=300, image_quality="NORMAL", layers_attributes="LAYERS_AND_ATTRIBUTES", georef_info=True)
            AddMsgAndPrint("\tEcological Classification Map file exported!",0)

            # Reset visibility
            visibility_off(lyr_list)

        else:
            AddMsgAndPrint("\nSSURGO Layers group, SSURGO Map Units layer, or Ecological Classification layer not in map. Cannot create Ecological Classification Map PDF. Continuing to next map...",1)


    #####################################################################################################
    ############################### FLOODING FREQUENCY CLASS MAP START ##################################
    #####################################################################################################
    if flood_map:
        AddMsgAndPrint("\nCreating the Flooding Frequency Map PDF file...",0)
        arcpy.SetProgressorLabel("Creating Flooding Frequency Map...")

        # Proceed if operational layer(s) actually exist(s) in the map
        if sgroup_lyr != '' and mu_lyr != '' and flood_lyr != '':
            if update_soil_zoom == False:
                # Set zoom and visiblility
                if zoomType == "Zoom to a layer":
                    setZoom(soil_lyt, ext, "Yes")
                else:
                    setZoom(soil_lyt, ext)
                update_soil_zoom = True
                
            sgroup_lyr.visible = True
            mu_lyr.visible = True
            mu_lyr.showLabels = True
            flood_lyr.visible = True
            flood_lyr.showLabels = False

            # Set the legend to only show flooding frequency features that are visible in the map
            soil_leg = soil_lyt.listElements('LEGEND_ELEMENT')[0]
            for item in soil_leg.items:
                if item.name == floodName:
                    item.showVisibleFeatures = True

            # Update the title
            soil_title_elm.text = "Flooding Frequency"

            # Export the map
            AddMsgAndPrint("\tExporting the Flooding Frequency Map to PDF...",0)
            arcpy.SetProgressorLabel("Exporting Flooding Frequency Map...")
            soil_lyt.exportToPDF(floodPDF, resolution=300, image_quality="NORMAL", layers_attributes="LAYERS_AND_ATTRIBUTES", georef_info=True)
            AddMsgAndPrint("\tFlooding Frequency Map file exported!",0)

            # Reset visibility
            visibility_off(lyr_list)

        else:
            AddMsgAndPrint("\nSSURGO Layers group, SSURGO Map Units layer, or Flooding Frequency layer not in map. Cannot create Flooding Frequency Map PDF. Continuing to next map...",1)


##    #####################################################################################################
##    ################################ HYDRIC CONDITION CLASS MAP START ###################################
##    #####################################################################################################
##    if hydricCon_map:
##        AddMsgAndPrint("\nCreating the Hydric Condition Map PDF file...",0)
##        arcpy.SetProgressorLabel("Creating Hydric Condition Map...")
##
##        # Proceed if operational layer(s) actually exist(s) in the map
##        if sgroup_lyr != '' and mu_lyr != '' and hydricCon_lyr != '':
##            if update_soil_zoom == False:
##                # Set zoom and visiblility
##                if zoomType == "Zoom to a layer":
##                    setZoom(soil_lyt, ext, "Yes")
##                else:
##                    setZoom(soil_lyt, ext)
##                update_soil_zoom = True
##                
##            sgroup_lyr.visible = True
##            mu_lyr.visible = True
##            mu_lyr.showLabels = True
##            hydricCon_lyr.visible = True
##            hydricCon_lyr.showLabels = False
##
##            # Set the legend to only show hydric condition features that are visible in the map
##            soil_leg = soil_lyt.listElements('LEGEND_ELEMENT')[0]
##            for item in soil_leg.items:
##                if item.name == hydricConName:
##                    item.showVisibleFeatures = True
##
##            # Update the title
##            soil_title_elm.text = "Hydric Condition"
##
##            # Export the map
##            AddMsgAndPrint("\tExporting the Hydric Condition Map to PDF...",0)
##            arcpy.SetProgressorLabel("Exporting Hydric Condition Map...")
##            soil_lyt.exportToPDF(hydricConPDF, resolution=300, image_quality="NORMAL", layers_attributes="LAYERS_AND_ATTRIBUTES", georef_info=True)
##            AddMsgAndPrint("\tHydric Condition Map file exported!",0)
##
##            # Reset visibility
##            visibility_off(lyr_list)
##
##        else:
##            AddMsgAndPrint("\nSSURGO Layers group, SSURGO Map Units layer, or Hydric Condition layer not in map. Cannot create Hydric Condition Map PDF. Continuing to next map...",1)


    #####################################################################################################
    ############################## HYDRIC RATING BY MAP UNIT MAP START ##################################
    #####################################################################################################
    if hydricMU_map:
        AddMsgAndPrint("\nCreating the Hydric Classification Map PDF file...",0)
        arcpy.SetProgressorLabel("Creating Hydric Classification Map...")

        # Proceed if operational layer(s) actually exist(s) in the map
        if sgroup_lyr != '' and mu_lyr != '' and hydricMu_lyr != '':
            if update_soil_zoom == False:
                # Set zoom and visiblility
                if zoomType == "Zoom to a layer":
                    setZoom(soil_lyt, ext, "Yes")
                else:
                    setZoom(soil_lyt, ext)
                update_soil_zoom = True
                
            sgroup_lyr.visible = True
            mu_lyr.visible = True
            mu_lyr.showLabels = True
            hydricMu_lyr.visible = True
            hydricMu_lyr.showLabels = False

            # Set the legend to show entire hydric rating symbol range
            soil_leg = soil_lyt.listElements('LEGEND_ELEMENT')[0]
            for item in soil_leg.items:
                if item.name == hydricMuName:
                    item.showVisibleFeatures = False

            # Update the title
            soil_title_elm.text = "Hydric Classification"

            # Export the map
            AddMsgAndPrint("\tExporting the Hydric Classification Map to PDF...",0)
            arcpy.SetProgressorLabel("Exporting Hydric Classification Map...")
            soil_lyt.exportToPDF(hydricRatMuPDF, resolution=300, image_quality="NORMAL", layers_attributes="LAYERS_AND_ATTRIBUTES", georef_info=True)
            AddMsgAndPrint("\tHydric Classification Map file exported!",0)

            # Reset visibility
            visibility_off(lyr_list)

        else:
            AddMsgAndPrint("\nSSURGO Layers group, SSURGO Map Units layer, or Hydric Classification layer not in map. Cannot create Hydric Classification Map PDF. Continuing to next map...",1)


    #####################################################################################################
    ############################# HYDRIC RATING BY COMPONENT MAP START ##################################
    #####################################################################################################
    if hydricCOMP_map:
        AddMsgAndPrint("\nCreating the Hydric Rating by Component Map PDF file...",0)
        arcpy.SetProgressorLabel("Creating Hydric Rating by Comopnent Map...")

        # Proceed if operational layer(s) actually exist(s) in the map
        if sgroup_lyr != '' and mu_lyr != '' and hydricComp_lyr != '':
            if update_soil_zoom == False:
                # Set zoom and visiblility
                if zoomType == "Zoom to a layer":
                    setZoom(soil_lyt, ext, "Yes")
                else:
                    setZoom(soil_lyt, ext)
                update_soil_zoom = True
                
            sgroup_lyr.visible = True
            mu_lyr.visible = True
            mu_lyr.showLabels = True
            hydricComp_lyr.visible = True
            hydricComp_lyr.showLabels = False

            # Set the legend to only show hydric rating features that are visible in the map
            soil_leg = soil_lyt.listElements('LEGEND_ELEMENT')[0]
            for item in soil_leg.items:
                if item.name == hydricCompName:
                    item.showVisibleFeatures = True

            # Update the title
            soil_title_elm.text = "Hydric Rating by Component"

            # Export the map
            AddMsgAndPrint("\tExporting the Hydric Rating by Component Map to PDF...",0)
            arcpy.SetProgressorLabel("Exporting Hydric Rating by Component Map...")
            soil_lyt.exportToPDF(hydricRatCompPDF, resolution=300, image_quality="NORMAL", layers_attributes="LAYERS_AND_ATTRIBUTES", georef_info=True)
            AddMsgAndPrint("\tHydric Rating by Component Map file exported!",0)

            # Reset visibility
            visibility_off(lyr_list)

        else:
            AddMsgAndPrint("\nSSURGO Layers group, SSURGO Map Units layer, or Hydric Rating by Component layer not in map. Cannot create Hydric Rating by Component Unit Map PDF. Continuing to next map...",1)


    #####################################################################################################
    ################################ HYDROLOGIC SOIL GROUP MAP START ####################################
    #####################################################################################################
    if hydrologic_map:
        AddMsgAndPrint("\nCreating the Hydrologic Soil Group Map PDF file...",0)
        arcpy.SetProgressorLabel("Creating Hydrologic Soil Group Map...")

        # Proceed if operational layer(s) actually exist(s) in the map
        if sgroup_lyr != '' and mu_lyr != '' and hydrologic_lyr != '':
            if update_soil_zoom == False:
                # Set zoom and visiblility
                if zoomType == "Zoom to a layer":
                    setZoom(soil_lyt, ext, "Yes")
                else:
                    setZoom(soil_lyt, ext)
                update_soil_zoom = True
                
            sgroup_lyr.visible = True
            mu_lyr.visible = True
            mu_lyr.showLabels = True
            hydrologic_lyr.visible = True
            hydrologic_lyr.showLabels = False

            # Set the legend to only show hydrologic soil group features that are visible in the map
            soil_leg = soil_lyt.listElements('LEGEND_ELEMENT')[0]
            for item in soil_leg.items:
                if item.name == hydrologicName:
                    item.showVisibleFeatures = True

            # Update the title
            soil_title_elm.text = "Hydrologic Groups"

            # Export the map
            AddMsgAndPrint("\tExporting the Hydrologic Soil Group Map to PDF...",0)
            arcpy.SetProgressorLabel("Exporting Hydrologic Soil Group Map...")
            soil_lyt.exportToPDF(hydrologicPDF, resolution=300, image_quality="NORMAL", layers_attributes="LAYERS_AND_ATTRIBUTES", georef_info=True)
            AddMsgAndPrint("\tHydrologic Soil Group Map file exported!",0)

            # Reset visibility
            visibility_off(lyr_list)

        else:
            AddMsgAndPrint("\nSSURGO Layers group, SSURGO Map Units layer, or Hydrologic Soil Group layer not in map. Cannot create Hydrologic Soil Group Map PDF. Continuing to next map...",1)


    #####################################################################################################
    ################################## PONDING FREQUENCY MAP START ######################################
    #####################################################################################################
    if ponding_map:
        AddMsgAndPrint("\nCreating the Ponding Frequency Map PDF file...",0)
        arcpy.SetProgressorLabel("Creating Ponding Frequency Map...")

        # Proceed if operational layer(s) actually exist(s) in the map
        if sgroup_lyr != '' and mu_lyr != '' and ponding_lyr != '':
            if update_soil_zoom == False:
                # Set zoom and visiblility
                if zoomType == "Zoom to a layer":
                    setZoom(soil_lyt, ext, "Yes")
                else:
                    setZoom(soil_lyt, ext)
                update_soil_zoom = True
                
            sgroup_lyr.visible = True
            mu_lyr.visible = True
            mu_lyr.showLabels = True
            ponding_lyr.visible = True
            ponding_lyr.showLabels = False

            # Set the legend to only show ponding features that are visible in the map
            soil_leg = soil_lyt.listElements('LEGEND_ELEMENT')[0]
            for item in soil_leg.items:
                if item.name == pondingName:
                    item.showVisibleFeatures = True

            # Update the title
            soil_title_elm.text = "Ponding Frequency"

            # Export the map
            AddMsgAndPrint("\tExporting the Ponding Frequency Map to PDF...",0)
            arcpy.SetProgressorLabel("Exporting Hydric Frequency Map...")
            soil_lyt.exportToPDF(pondingPDF, resolution=300, image_quality="NORMAL", layers_attributes="LAYERS_AND_ATTRIBUTES", georef_info=True)
            AddMsgAndPrint("\tPonding Frequency Map file exported!",0)

            # Reset visibility
            visibility_off(lyr_list)

        else:
            AddMsgAndPrint("\nSSURGO Layers group, SSURGO Map Units layer, or Ponding Frequency layer not in map. Cannot create Ponding Frequency Map PDF. Continuing to next map...",1)


    #####################################################################################################
    ################################## WATER TABLE DETPH MAP START ######################################
    #####################################################################################################
    if wtrtbl_map:
        AddMsgAndPrint("\nCreating the Water Table Depth Map PDF file...",0)
        arcpy.SetProgressorLabel("Creating Water Table Depth Map...")

        # Proceed if operational layer(s) actually exist(s) in the map
        if sgroup_lyr != '' and mu_lyr != '' and wtrtbl_lyr != '':
            if update_soil_zoom == False:
                # Set zoom and visiblility
                if zoomType == "Zoom to a layer":
                    setZoom(soil_lyt, ext, "Yes")
                else:
                    setZoom(soil_lyt, ext)
                update_soil_zoom = True
                
            sgroup_lyr.visible = True
            mu_lyr.visible = True
            mu_lyr.showLabels = True
            wtrtbl_lyr.visible = True
            wtrtbl_lyr.showLabels = False

            # Set the legend to only show water table depth features that are visible in the map
            soil_leg = soil_lyt.listElements('LEGEND_ELEMENT')[0]
            for item in soil_leg.items:
                if item.name == wtrtblName:
                    item.showVisibleFeatures = True

            # Update the title
            soil_title_elm.text = "Water Table Depth"

            # Export the map
            AddMsgAndPrint("\tExporting the Water Table Depth Map to PDF...",0)
            arcpy.SetProgressorLabel("Exporting Water Table Depth Map...")
            soil_lyt.exportToPDF(wtrtblPDF, resolution=300, image_quality="NORMAL", layers_attributes="LAYERS_AND_ATTRIBUTES", georef_info=True)
            AddMsgAndPrint("\tWater Table Depth Map file exported!",0)

            # Reset visibility
            visibility_off(lyr_list)

        else:
            AddMsgAndPrint("\nSSURGO Layers group, SSURGO Map Units layer, or Water Table Depth layer not in map. Cannot create Water Table Depth Map PDF. Continuing to next map...",1)
    

    #### Build the final PDF file
    AddMsgAndPrint("\nCreating final map book PDF file...",0)
    arcpy.SetProgressorLabel("Creating final map book PDF...")

    AddMsgAndPrint("\tAppending site map...",0)
    finalPDF.appendPages(sitePDF)

    if ctr_map:
        AddMsgAndPrint("\tAppending Contour map...",0)
        try:
            finalPDF.appendPages(ctrPDF)
        except:
            pass
        
    if dem_map:
        AddMsgAndPrint("\tAppending DEM map...",0)
        try:
            finalPDF.appendPages(demPDF)
        except:
            pass
        
    if slope_map:
        AddMsgAndPrint("\tAppending Slope map...",0)
        try:
            finalPDF.appendPages(slopePDF)
        except:
            pass
        
    if depth_map:
        AddMsgAndPrint("\tAppending Depth Grid map...",0)
        try:
            finalPDF.appendPages(depthPDF)
        except:
            pass

    if nwi_map:
        AddMsgAndPrint("\tAppending NWI map...",0)
        try:
            finalPDF.appendPages(nwiPDF)
        except:
            pass

    if mu_map:
        AddMsgAndPrint("\tAppending Soil Map Units map...",0)
        try:
            finalPDF.appendPages(soilPDF)
        except:
            pass

    if drain_map:
        AddMsgAndPrint("\tAppending Drainage Class map...",0)
        try:
            finalPDF.appendPages(drainPDF)
        except:
            pass
        
    if eco_map:
        AddMsgAndPrint("\tAppending Ecological Classification map...",0)
        try:
            finalPDF.appendPages(ecoPDF)
        except:
            pass
    
    if flood_map:
        AddMsgAndPrint("\tAppending Flooding Frequency map...",0)
        try:
            finalPDF.appendPages(floodPDF)
        except:
            pass

##    if hydricCon_map:
##        AddMsgAndPrint("\tAppending Hydric Condition map...",0)
##        try:
##            finalPDF.appendPages(hydricConPDF)
##        except:
##            pass

    if hydricMU_map:
        AddMsgAndPrint("\tAppending Hydric Classification map...",0)
        try:
            finalPDF.appendPages(hydricRatMuPDF)
        except:
            pass

    if hydricCOMP_map:
        AddMsgAndPrint("\tAppending Hydric Rating by Component map...",0)
        try:
            finalPDF.appendPages(hydricRatCompPDF)
        except:
            pass
        
    if hydrologic_map:
        AddMsgAndPrint("\tAppending Hydrologic Group map...",0)
        try:
            finalPDF.appendPages(hydrologicPDF)
        except:
            pass

    if ponding_map:
        AddMsgAndPrint("\tAppending Ponding Frequency map...",0)
        try:
            finalPDF.appendPages(pondingPDF)
        except:
            pass

    if wtrtbl_map:
        AddMsgAndPrint("\tAppending Water Table Depth map...",0)
        try:
            finalPDF.appendPages(wtrtblPDF)
        except:
            pass

    if flood_map or hydricMU_map or hydricCOMP_map or hydrologic_map or ponding_map or wtrtbl_map:
        AddMsgAndPrint("\tAppending SSURGO Metadata report...",0)
        try:
            finalPDF.appendPages(metadataPDF)
        except:
            pass

    AddMsgAndPrint("\nSaving and closing final PDF map book...",0)
    finalPDF.saveAndClose()
    
        
    #### MAINTENANCE
    AddMsgAndPrint("\tRunning cleanup...",0)
    arcpy.SetProgressorLabel("Running cleanup...")
    # Delete the individual maps if they aren't being kept separately
    if multiLayouts == False:
        if owLayouts == True:
            AddMsgAndPrint("\tDeleting temporary PDF maps...",0)
            for item in PDFlist:
                try:
                    os.remove(item)
                except:
                    pass

    # Reset Elevation Layout Title
    elev_title_elm.text = "Elevation"
    
    # Reset Soil Layout Title and version text box
    soil_title_elm.text = "Soils"
    soil_version_elm.text = "Survey Version:"

    ## Reset image text on each layout to be blank
    # Define the imagery text box elements
    for elm in lm_lyt.listElements():
        if elm.name == "Imagery Text Box":
            lm_imagery_elm = elm

    for elm in elev_lyt.listElements():
        if elm.name == "Imagery Text Box":
            elev_imagery_elm = elm
            
    for elm in soil_lyt.listElements():
        if elm.name == "Imagery Text Box":
            soil_imagery_elm = elm

    for elm in nwi_lyt.listElements():
        if elm.name == "Imagery Text Box":
            nwi_imagery_elm = elm
            
    dflt_img_text = " Image: "
    lm_imagery_elm.text = dflt_img_text
    elev_imagery_elm.text = dflt_img_text
    soil_imagery_elm.text = dflt_img_text
    nwi_imagery_elm.text = dflt_img_text
    
    # Reset visibility of operational layers
    visibility_off(lyr_list)
                
    # Look for and delete anything else that may remain in the installed SCRATCH.gdb
    startWorkspace = arcpy.env.workspace
    arcpy.env.workspace = scratchGDB

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
    
    AddMsgAndPrint("\nReference Maps have been created and exported! Exiting...",0)

except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested...exiting.")
