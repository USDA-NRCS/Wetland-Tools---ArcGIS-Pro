## ===============================================================================================================
## Name:    Create Wetlands Project
## Purpose: Create a wetland determination project folder in C:\Determinations. Download a
##          single CLU Tract specified by user inputs for admin state, county, and tract.
##
## Authors: Chris Morse
##          GIS Specialist
##          Indianapolis State Office
##          USDA-NRCS
##          chris.morse@usda.gov
##          317.295.5849
##
##          Adolfo Diaz
##          GIS Specialist
##          National Soil Survey Center
##          USDA-NRCS
##          adolfo.diaz@usda.gov
##          608.662.4422, ext. 216
##
## Created: 8/20/2020
##
## ===============================================================================================================
## Changes
## ===============================================================================================================
##
## rev. 8/20/2020
## Start revisions of Create Project Folder ArcMap tool to National Wetlands Tool in ArcGIS Pro.
## Change CLU generation to use GeoPortal based web service and Extract CLU code by Adolfo Diaz.
## Change input parameters to use lookup table for states & counties downloaded from US Census.
## Change processing to use lookup table obtained from US Census for state and county names.
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
def splitThousands(someNumber):
    # Determines where to put a thousands separator in an integer.
    # Integer with or without thousands seperator is returned.

    try:
        return re.sub(r'(\d{3})(?=\d)', r'\1,', str(someNumber)[::-1])[::-1]

    except:
        errorMsg()
        return someNumber
    
## ===============================================================================================================
def getPortalTokenInfo(portalURL):
    try:
        # Returns the URL of the active Portal
        # i.e. 'https://gis.sc.egov.usda.gov/portal/'
        activePortal = arcpy.GetActivePortalURL()

        # {'SSL_enabled': False, 'portal_version': 6.1, 'role': '', 'organization': '', 'organization_type': ''}
        #portalInfo = arcpy.GetPortalInfo(activePortal)

        # targeted portal is NOT set as default
        if activePortal != portalURL:

               # List of managed portals
               managedPortals = arcpy.ListPortalURLs()

               # portalURL is available in managed list
               if activePortal in managedPortals:
                   AddMsgAndPrint("\nYour Active portal is set to: " + activePortal,2)
                   AddMsgAndPrint("Set your active portal and sign into: " + portalURL,2)
                   return False

               # portalURL must first be added to list of managed portals
               else:
                    AddMsgAndPrint("\nYou must add " + portalURL + " to your list of managed portals",2)
                    AddMsgAndPrint("Open the Portals Tab to manage portal connections",2)
                    AddMsgAndPrint("For more information visit the following ArcGIS Pro documentation:",2)
                    AddMsgAndPrint("https://pro.arcgis.com/en/pro-app/help/projects/manage-portal-connections-from-arcgis-pro.htm",1)
                    return False

        # targeted Portal is correct; try to generate token
        else:

            # Get Token information
            tokenInfo = arcpy.GetSigninToken()

            # Not signed in.  Token results are empty
            if not tokenInfo:
                AddMsgAndPrint("\nYou are not signed into: " + portalURL,2)
                return False

            # Token generated successfully
            else:
                return tokenInfo

    except:
        errorMsg()
        return False

## ===============================================================================================================
def submitFSquery(url,INparams):
    # This function will send a spatial query to a web feature service and convert the results into a python
    # structure.  If the results from the service is an error due to an invalid token then a second attempt will
    # be sent with using a newly generated arcgis token.  If the token is good but the request returned with an
    # error a second attempt will be made.  The function takes in 2 parameters, the URL to the web service and a
    # query string in URLencoded format.

    # Error produced with invalid token
    # {u'error': {u'code': 498, u'details': [], u'message': u'Invalid Token'}}

    # The function returns requested data via a python dictionary

    try:
        # Data should be in bytes; new in Python 3.6
        INparams = INparams.encode('ascii')
        resp = urllib.request.urlopen(url,INparams)  # A failure here will probably throw an HTTP exception
        responseStatus = resp.getcode()
        responseMsg = resp.msg
        jsonString = resp.read()

        # json --> Python; dictionary containing 1 key with a list of lists
        results = json.loads(jsonString)

        # Check for expired token; Update if expired and try again
        if 'error' in results.keys():
            if results['error']['message'] == 'Invalid Token':
                AddMsgAndPrint("\tRegenerating ArcGIS Token Information...")

                # Get new ArcPro Token
                newToken = arcpy.GetSigninToken()

                # Update the original portalToken
                global portalToken
                portalToken = newToken

                # convert encoded string into python structure and update token
                # by parsing the encoded query strting into list of (name, value pairs)
                # i.e [('f', 'json'),('token','U62uXB9Qcd1xjyX1)]
                # convert to dictionary and update the token in dictionary

                queryString = parseQueryString(params)

                requestDict = dict(queryString)
                requestDict.update(token=newToken['token'])

                newParams = urllibEncode(requestDict)
                newParams = newParams.encode('ascii')

                # update incoming parameters just in case a 2nd attempt is needed
                INparams = newParams

                resp = urllib.request.urlopen(url,newParams)  # A failure here will probably throw an HTTP exception

                responseStatus = resp.getcode()
                responseMsg = resp.msg
                jsonString = resp.read()

                results = json.loads(jsonString)

        # Check results before returning them; Attempt a 2nd request if results are bad.
        if 'error' in results.keys() or len(results) == 0:
            time.sleep(5)
            resp = urllib.request.urlopen(url,INparams)  # A failure here will probably throw an HTTP exception

            responseStatus = resp.getcode()
            responseMsg = resp.msg
            jsonString = resp.read()

            results = json.loads(jsonString)

            if 'error' in results.keys() or len(results) == 0:
                AddMsgAndPrint("\t2nd Request Attempt Failed - Error Code: " + str(responseStatus) + " -- " + responseMsg + " -- " + str(results),2)
                return False
            else:
                return results

        else:
             return results

    except httpErrors as e:

        if int(e.code) >= 500:
           #AddMsgAndPrint("\n\t\tHTTP ERROR: " + str(e.code) + " ----- Server side error. Probably exceed JSON imposed limit",2)
           #AddMsgAndPrint("t\t" + str(request))
           pass
        elif int(e.code) >= 400:
           #AddMsgAndPrint("\n\t\tHTTP ERROR: " + str(e.code) + " ----- Client side error. Check the following SDA Query for errors:",2)
           #AddMsgAndPrint("\t\t" + getGeometryQuery)
           pass
        else:
           AddMsgAndPrint('HTTP ERROR = ' + str(e.code),2)

    except:
        errorMsg()
        return False
    
## ===============================================================================================================
def getCLUgeometryByTractQuery(sqlQuery,fc,RESTurl):
    # This funciton will will retrieve CLU geometry from the CLU WFS and assemble into the CLU fc along with the
    # attributes associated with it. It is intended to receive requests that will return records that are below the
    # WFS record limit.
    try:
        params = urllibEncode({'f': 'json',
                               'where':sqlQuery,
                               'geometryType':'esriGeometryPolygon',
                               'returnGeometry':'true',
                               'outFields': '*',
                               'token': portalToken['token']})

        # Send request to feature service; The following dict keys are returned:
        # ['objectIdFieldName', 'globalIdFieldName', 'geometryType', 'spatialReference', 'fields', 'features']
        geometry = submitFSquery(RESTurl,params)

        if not geometry:
           return False

        # Insert Geometry
        with arcpy.da.InsertCursor(fc, [fld for fld in fields]) as cur:

            arcpy.SetProgressor("step", "Assembling Geometry", 0, len(geometry['features']),1)

            # Iterenate through the 'features' key in geometry dict
            # 'features' contains geometry and attributes
            for rec in geometry['features']:

                arcpy.SetProgressorLabel("Assembling Geometry")
                values = list()    # list of attributes

                polygon = json.dumps(rec['geometry'])   # u'geometry': {u'rings': [[[-89.407702228, 43.334059191999984], [-89.40769642800001, 43.33560779300001]}
                attributes = rec['attributes']          # u'attributes': {u'land_unit_id': u'73F53BC1-E3F8-4747-B51F-E598EE445E47'}}

                for fld in fields:
                    if fld == "SHAPE@JSON":
                        continue

                    # DATE values need to be converted from Unix Epoch format
                    # to dd/mm/yyyy format so that it can be inserted into fc.
                    elif fldsDict[fld][0] == 'DATE':
                        dateVal = attributes[fld]
                        if not dateVal in (None,'null','','Null'):
                            epochFormat = float(attributes[fld]) # 1609459200000

                            # Convert to seconds from milliseconds and reformat
                            localFormat = time.strftime('%m/%d/%Y',time.gmtime(epochFormat/1000))   # 01/01/2021
                            values.append(localFormat)
                        else:
                            values.append(None)

                    else:
                        values.append(attributes[fld])

                # geometry goes at the the end
                values.append(polygon)
                cur.insertRow(values)
                arcpy.SetProgressorPosition()

        arcpy.ResetProgressor()
        arcpy.SetProgressorLabel("")
        del cur

        return True

    except:
        try: del cur
        except: pass

        errorMsg()
        return False

## ===============================================================================================================
def createOutputFC(metadata,outputWS,shape="POLYGON"):
    try:
        newFC = outputWS + os.sep + "CLU_" + str(adminState) + "_" + str(adminCounty) + "_" + str(tractNumber)
        
        AddMsgAndPrint("\nCreating New CLU Feature Class: " + os.path.basename(newFC))
        arcpy.SetProgressorLabel("Creating New CLU Feature Class: " + os.path.basename(newFC))
        
        # output FC will have the 'CLU_' as a prefix along with the state, county and tract number
        newFC = outputWS + os.sep + "CLU_" + str(adminState) + "_" + str(adminCounty) + "_" + str(tractNumber)

        # set the spatial Reference to same as WFS
        # Probably WGS_1984_Web_Mercator_Auxiliary_Sphere
        # {'spatialReference': {'latestWkid': 3857, 'wkid': 102100}
        spatialReferences = metadata['extent']['spatialReference']
        if 'latestWkid' in [sr for sr in spatialReferences.keys()]:
            sr = spatialReferences['latestWkid']
        else:
            sr = spatialReferences['wkid']

        outputCS = arcpy.SpatialReference(sr)

        # fields associated with feature service
        fsFields = metadata['fields']
        fieldDict = dict()

        # lookup list for fields that are in DATE field; Date values need to be converted
        # from Unix Epoch format to mm/dd/yyyy format in order to populate a table
        dateFields = list()

        # cross-reference portal attribute description with ArcGIS attribute description
        fldTypeDict = {'esriFieldTypeString':'TEXT','esriFieldTypeDouble':'DOUBLE','esriFieldTypeSingle':'FLOAT',
                       'esriFieldTypeInteger':'LONG','esriFieldTypeSmallInteger':'SHORT','esriFieldTypeDate':'DATE',
                       'esriFieldTypeGUID':'GUID','esriFieldTypeGlobalID':'GUID'}

        # Collect field info to pass to new fc
        for fieldInfo in fsFields:

            # skip the OID field
            if fieldInfo['type'] == 'esriFieldTypeOID':
               continue

            fldType = fldTypeDict[fieldInfo['type']]
            fldAlias = fieldInfo['alias']
            fldName = fieldInfo['name']

            # skip the SHAPE_STArea__ and SHAPE_STLength__ fields
            if fldName.find("SHAPE_ST") > -1:
               continue

            if fldType == 'TEXT':
               fldLength = fieldInfo['length']
            elif fldType == 'DATE':
                 dateFields.append(fldName)
            else:
               fldLength = ""

            fieldDict[fldName] = (fldType,fldLength,fldAlias)

        # Delete newFC if it exists
        if arcpy.Exists(newFC):
           arcpy.Delete_management(newFC)
           AddMsgAndPrint("\t" + os.path.basename(newFC) + " exists.  Deleted")

        # Create empty polygon featureclass with coordinate system that matches AOI.
        arcpy.CreateFeatureclass_management(outputWS, os.path.basename(newFC), shape, "", "DISABLED", "DISABLED", outputCS)

        # Add fields from fieldDict to mimic WFS
        arcpy.SetProgressor("step", "Adding Fields to " + os.path.basename(newFC),0,len(fieldDict),1)
        for field,params in fieldDict.items():
            try:
                fldLength = params[1]
                fldAlias = params[2]
            except:
                fldLength = 0
                pass

            arcpy.SetProgressorLabel("Adding Field: " + field)
            arcpy.AddField_management(newFC,field,params[0],"#","#",fldLength,fldAlias)
            arcpy.SetProgressorPosition()

        arcpy.ResetProgressor()
        arcpy.SetProgressorLabel("")
        return fieldDict,newFC

    except:
        errorMsg()
        AddMsgAndPrint("\tFailed to create scratch " + newFC + " Feature Class",2)
        return False
    
## ===============================================================================================================
def downloadCLU(state,county,trctNmbr,outSR,outWS):
    try:

        global urllibEncode, parseQueryString
        global portalToken, fldsDict, fields
        
        # update variables
        adminState = state
        adminCounty = county
        tractNumber = trctNmbr
        outSpatialRef = outSR
        outputWS = outWS
        
        # Setup urllib elements
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError as httpErrors
        urllibEncode = urllib.parse.urlencode
        parseQueryString = urllib.parse.parse_qsl
        
        # Get CLU Feature Service Metadata
        cluRESTurl_Metadata = """https://gis.sc.egov.usda.gov/appserver/rest/services/common_land_units/common_land_units/FeatureServer/0"""

        # Used for admin or feature service info; Send POST request
        params = urllibEncode({'f': 'json','token': portalToken['token']})

        # request info about the feature service
        fsMetadata = submitFSquery(cluRESTurl_Metadata,params)

        # Create empty CLU FC with necessary fields
        #####################
        fldsDict,cluFC = createOutputFC(fsMetadata,outputWS)
        #####################

        # Isolate the fields that were inserted into new fc
        # Python 3.6 returns a <class 'dict_keys'>
        fields = fldsDict.keys()

        # Convert to a list b/c Python 3.6 doesn't support .append
        fields = list(fields)

        fields.append('SHAPE@JSON')

        # Get the Max record count the REST service can return
        if not 'maxRecordCount' in fsMetadata:
           AddMsgAndPrint('\t\tCould not determine FS maximum record count: Setting default to 1,000 records',1)
           maxRecordCount = 1000
        else:
           maxRecordCount = fsMetadata['maxRecordCount']

        # Query by Admin State, Admin County, and Tract Number
        cluRESTurl = """https://gis.sc.egov.usda.gov/appserver/rest/services/common_land_units/common_land_units/FeatureServer/0/query"""

        # Define query
        whereClause = "ADMIN_STATE = " + str(adminState) + " AND ADMIN_COUNTY = " + str(adminCounty) + " AND TRACT_NUMBER = " + str(tractNumber)

        AddMsgAndPrint("Querying GeoPortal for CLU fields where: " + whereClause)
        if not getCLUgeometryByTractQuery(whereClause,cluFC,cluRESTurl):
            AddMsgAndPrint("\tFailed to query by specified state, county, and tract. Please try again. Exiting...",2)
            exit()
##            if addCLUtoSoftware:
##                exit()
##            else:
##                return False

        numOfCLUs = int(arcpy.GetCount_management(cluFC)[0])
        if numOfCLUs > 1:
            AddMsgAndPrint("\nThere are " + splitThousands(numOfCLUs) + " CLU fields part of Tract Number " + str(tractNumber))
        else:
            AddMsgAndPrint("\nThere is " + splitThousands(numOfCLUs) + " CLU field part of Tract Number " + str(tractNumber))

        # Project the CLU to the target spatial reference
        fromSR = arcpy.Describe(cluFC).spatialReference
        toSR = outSpatialRef

        geoTransformation = arcpy.ListTransformations(fromSR,toSR)
        if len(geoTransformation):
            geoTransformation = geoTransformation[0]
        else:
            geoTransformation = None

        AddMsgAndPrint("\nProjecting CLU Feature class",0)
        AddMsgAndPrint("FROM: " + str(fromSR.name),0)
        AddMsgAndPrint("TO: " + str(toSR.name),0)
        AddMsgAndPrint("Geographic Transformation used: " + str(geoTransformation),0)

        arcpy.Project_management(cluFC,projectCLU,toSR,geoTransformation)

        arcpy.Delete_management(cluFC)

    except:
        errorMsg()
        
## ===============================================================================================================
def logBasicSettings():    
    # record basic user inputs and settings to log file for future purposes
    import getpass, time
    f = open(textFilePath,'a+')
    f.write("\n######################################################################\n")
    f.write("Executing Create Project Folder tool...\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("User Parameters:\n")
    f.write("\tAdmin State Selected: " + sourceState + "\n")
    f.write("\tAdmin County Selected: " + sourceCounty + "\n")
    f.write("\tTract Entered: " + str(tractNumber) + "\n")
    f.write("\tOverwrite CLU: " + str(owFlag) + "\n")
    f.close
    del f


## ===============================================================================================================
#### Import system modules
import sys, string, os, traceback
import urllib, re, time, json, random
import datetime, shutil
import arcpy


#### Update Environments
arcpy.AddMessage("Setting Environments...\n")


# Get spatial refrence of the Active Map and set the WKID as the env.outputCoordSystem.
# If the tool was launched from catalog view instead of the catalog pane, this will fail and the tool will exit.
try:
    aprx = arcpy.mp.ArcGISProject("CURRENT")
except:
    arcpy.AddError("\nThis tool must be from an active ArcGIS Pro project. Exiting...\n")
    exit()
activeMap = aprx.activeMap

try:
    activeMapName = activeMap.name
    activeMapSR = activeMap.getDefinition('V2').spatialReference['latestWkid']
    outSpatialRef = arcpy.SpatialReference(activeMapSR)
    arcpy.env.outputCoordinateSystem = outSpatialRef

except:
    arcpy.AddError("Could not get a spatial reference! Please run the tool from the Catalog Pane with an active ArcGIS Pro Map open! Exiting...")
    exit()


# Set transformation (replace with assignment from Transformation lookup from cim object of active map object in the future)
arcpy.env.geographicTransformations = "WGS_1984_(ITRF00)_To_NAD_1983"


# Set overwrite flag
arcpy.env.overwriteOutput = True


#### Check GeoPortal Connection
nrcsPortal = 'https://gis.sc.egov.usda.gov/portal/'
portalToken = getPortalTokenInfo(nrcsPortal)
if not portalToken:
    arcpy.AddError("Could not generate Portal token! Please login to GeoPortal! Exiting...")
    exit()

        
#### Main procedures
try:
    #### Inputs
    arcpy.AddMessage("Reading inputs...\n")
    #sourceLUT = arcpy.GetParameterAsText(0)
    #stateFld = arcpy.GetParameterAsText(1)
    sourceState = arcpy.GetParameterAsText(2)
    #countyFld = arcpy.GetParameterAsText(3)
    sourceCounty = arcpy.GetParameterAsText(4)
    tractNumber = arcpy.GetParameterAsText(5)
    owFlag = arcpy.GetParameter(6)


    #### Check Inputs for existence and create FIPS code variables
    lut = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "lut_census_fips")
    if not arcpy.Exists(lut):
        arcpy.AddError("Could not find state and county lookup table! Exiting...\n")
        exit()

    # Search for FIPS codes to give to the Extract CLU Tool/Function. Break after the first row (should only find one row in any case).
    stfip, cofip = '', ''
    fields = ['STATEFP','COUNTYFP','NAME','STATE','STPOSTAL']
    field1 = 'STATE'
    field2 = 'NAME'
    expression = "{} = '{}'".format(arcpy.AddFieldDelimiters(lut,field1), sourceState) + " AND " + "{} = '{}'".format(arcpy.AddFieldDelimiters(lut,field2), sourceCounty)
    with arcpy.da.SearchCursor(lut, fields, where_clause = expression) as cursor:
        for row in cursor:
            stfip = row[0]
            cofip = row[1]
            adStatePostal = row[4]
            break

    if len(stfip) != 2 and len(cofip) != 3:
        arcpy.AddError("State and County FIPS codes could not be retrieved! Exiting...\n")
        exit()

    if adStatePostal == '':
        arcpy.AddError("State postal code could not be retrieved! Exiting...\n")
        exit()
        
    # Transfer found values to variables to use for CLU download and project creation.
    adminState = stfip
    adminCounty = cofip
    postal = adStatePostal.lower()


    #### Create additional variables for use in project naming.

    # Get the current year and month for use in project naming
    current = datetime.datetime.now()
    curyear = current.year
    curmonth = current.month
    theyear = str(curyear)
    themonth = str(curmonth)

    # Refine the tract number and month number to be padded with zeros to create uniform length of project name
    sourceTract = str(tractNumber)
    tractlength = len(sourceTract)
    if tractlength < 7:
        addzeros = 7 - tractlength
        tractname = '0'*addzeros + str(sourceTract)
    else:
        tractname = sourceTract

    monthlength = len(themonth)
    if monthlength < 2:
        finalmonth = '0' + themonth
    else:
        finalmonth = themonth

    # Variables and project names
    workspacePath = r'C:\Determinations'
    projectFolder = workspacePath + os.sep + postal + adminCounty + "_t" + tractname + "_" + theyear + "_" + finalmonth
    folderName = os.path.basename(projectFolder)
    projectName = folderName
    basedataGDB_name = os.path.basename(projectFolder).replace(" ","_") + "_BaseData.gdb"
    basedataGDB_path = projectFolder + os.sep + basedataGDB_name
    basedataFD = basedataGDB_path + os.sep + "Layers"
    outputWS = basedataGDB_path
    projectCLU = basedataFD + os.sep + "CLU_" + projectName
    projectTract = basedataFD + os.sep + "Tract_" + projectName
    projectTractB = basedataFD + os.sep + "Tract_Buffer_" + projectName
    bufferDist = "500 Feet"
    bufferDistPlus = "550 Feet"
    projectAOI = basedataFD + os.sep + "AOI_" + projectName
    extentName = "Extent_" + projectName
    projectExtent = basedataFD + os.sep + extentName
##    helFolder = projectFolder + os.sep + "HEL"
##    helGDB_name = folderName + "_HEL.gdb"
##    helGDB_path = helFolder + os.sep + helGDB_name
##    hel_fd = helGDB_path + os.sep + "HEL_Data"
    wetlandsFolder = projectFolder + os.sep + "Wetlands"
    wetDir = wetlandsFolder
    wcGDB_name = folderName + "_WC.gdb"
    wcGDB_path = wetlandsFolder + os.sep + wcGDB_name
    wc_fd = wcGDB_path + os.sep + "WC_Data"
##    docs_folder = projectFolder + os.sep + "Doc_Templates"
##    doc028 = "NRCS-CPA-028.docx"
##    doc026h = "NRCS-CPA-026-HELC.docx"
##    doc026w = "NRCS-CPA-026-WC.docx"
##    doc026wp = "NRCS-CPA-026-WC-PJW.docx"
##    source_028 = os.path.join(os.path.dirname(sys.argv[0]), "AddIns" + os.sep + doc028)
##    source_026h = os.path.join(os.path.dirname(sys.argv[0]), "AddIns" + os.sep + doc026h)
##    source_026w = os.path.join(os.path.dirname(sys.argv[0]), "AddIns" + os.sep + doc026w)
##    source_026wp = os.path.join(os.path.dirname(sys.argv[0]), "AddIns" + os.sep + doc026wp)
##    target_028 = docs_folder + os.sep + doc028
##    target_026h = docs_folder + os.sep + doc026h
##    target_026w = docs_folder + os.sep + doc026w
##    target_026wp = docs_folder + os.sep + doc026wp

    # ArcMap Layer Names
    cluOut = "CLU_" + projectName
    extentOut = "Extent_" + projectName


    #### Create the project directory

    # Check if C:\Determinations exists, else create it
    arcpy.AddMessage("\nChecking project directories...")
    if not os.path.exists(workspacePath):
        try:
            os.mkdir(workspacePath)
            arcpy.AddMessage("\nThe Determinations folder did not exist on the C: drive and has been created.")
        except:
            arcpy.AddError("\nThe Determinations folder cannot be created. Please check your permissions to the C: drive. Exiting...\n")
            exit()
            
    # Check if C:\Determinations\projectFolder exists, else create it
    if not os.path.exists(projectFolder):
        try:
            os.mkdir(projectFolder)
            arcpy.AddMessage("\nThe project folder has been created within Determinations.")
        except:
            arcpy.AddError("\nThe project folder cannot be created. Please check your permissions to C:\Determinations. Exiting...\n")
            exit()


    #### Project folder now exists. Set up log file path and start logging
    textFilePath = projectFolder + os.sep + folderName + "_PTD.txt"
    logBasicSettings()


    #### Continue creating sub-directories
    # Check if the Wetlands folder exists within the projectFolder, else create it
    if not os.path.exists(wetlandsFolder):
        try:
            os.mkdir(wetlandsFolder)
            AddMsgAndPrint("\nThe Wetlands folder has been created within " + projectFolder + ".",0)
        except:
            AddMsgAndPrint("\nCould not access C:\Determinations. Check your permissions for C:\Determinations. Exiting...\n",2)
            exit()
            
##    # Check if the HEL folder exists within the projectFolder, else create it
##    if not os.path.exists(helFolder):
##        try:
##            os.mkdir(helFolder)
##            AddMsgAndPrint("\n\tThe HEL folder has been created within " + projectFolder + ".",0)
##        except:
##            AddMsgAndPrint("\nCould not access C:\Determinations. Check your permissions for C:\Determinations. Exiting...\n",2)
##            exit()
##    else:
##        AddMsgAndPrint("\n\tThe HEL folder already exists within " + projectFolder + ".",0)


##    #### Copy the file templates from the install folder to the project directory
##    # This is done to make the install folder location indepedent on a given computer
##    # Check if the Doc_Templates folder exists within the projectFolder, else create it
##    if not os.path.exists(docs_folder):
##        try:
##            os.mkdir(docs_folder)
##            shutil.copy2(source_028, target_028)
##            shutil.copy2(source_026h, target_026h)
##            shutil.copy2(source_026w, target_026w)
##            shutil.copy2(source_026wp, target_026wp)
##            AddMsgAndPrint("\n\tThe Doc_Templates folder has been created within " + projectFolder + ".",0)
##        except:
##            AddMsgAndPrint("\nCould not access C:\Determinations. Check your permissions for C:\Determinations. Exiting...\n",2)
##            sys.exit()
##    else:
##        # Make sure the .docx template files are in the Doc_Templates folder
##        if not os.path.exists(target_028):
##            shutil.copy2(source_028, target_028)
##        if not os.path.exists(target_026h):
##            shutil.copy2(source_026h, target_026h)
##        if not os.path.exists(target_026w):
##            shutil.copy2(source_026w, target_026w)
##        if not os.path.exists(target_026wp):
##            shutil.copy2(source_026wp, target_026wp)
##        AddMsgAndPrint("\n\tThe Doc_Templates folder already exists within " + projectFolder + ".",0)


    #### If project geodatabases and feature datasets do not exist, create them.
    # BaseData
    if not arcpy.Exists(basedataGDB_path):
        AddMsgAndPrint("\nCreating Base Data geodatabase...",0)
        arcpy.CreateFileGDB_management(projectFolder, basedataGDB_name, "10.0")

    if not arcpy.Exists(basedataFD):
        AddMsgAndPrint("\nCreating Base Data feature dataset...",0)
        arcpy.CreateFeatureDataset_management(basedataGDB_path, "Layers", outSpatialRef)

    # Wetlands
    if not arcpy.Exists(wcGDB_path):
        AddMsgAndPrint("\nCreating Wetlands geodatabase...",0)
        arcpy.CreateFileGDB_management(wetlandsFolder, wcGDB_name, "10.0")

    if not arcpy.Exists(wc_fd):
        AddMsgAndPrint("\nCreating Wetlands feature dataset...",0)
        arcpy.CreateFeatureDataset_management(wcGDB_path, "WC_Data", outSpatialRef)
        
##    # HEL
##    if not arcpy.Exists(helGDB_path):
##        AddMsgAndPrint("\nCreating HEL geodatabase...",0)
##        arcpy.CreateFileGDB_management(helFolder, helGDB_name, "10.0")
##
##    if not arcpy.Exists(hel_fd):
##        AddMsgAndPrint("\nCreating HEL feature dataset...",0)
##        arcpy.CreateFeatureDataset_management(helGDB_path, "HEL_Data", outSpatialRef)


    #### Add or validate the attribute domains for the geodatabases
    AddMsgAndPrint("\nChecking attribute domains of wetlands geodatabase...",0)

    # Wetlands Domains
    descGDB = arcpy.Describe(wcGDB_path)
    domains = descGDB.domains

    if not "CWD Status" in domains:
        cwdTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_cwd_status")
        arcpy.TableToDomain_management(cwdTable, "Code", "Description", wcGDB_path, "CWD Status", "Choices for wetland determination status", "REPLACE")
    if not "Data Form" in domains:
        dataTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_data_form")
        arcpy.TableToDomain_management(dataTable, "Code", "Description", wcGDB_path, "Data Form", "Choices for data form completion", "REPLACE")
    if not "Evaluation Status" in domains:
        evalTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_evaluation_status")
        arcpy.TableToDomain_management(evalTable, "Code", "Description", wcGDB_path, "Evaluation Status", "Choices for evaluation workflow status", "REPLACE")
    if not "Line Type" in domains:
        lineTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_line_type")
        arcpy.TableToDomain_management(lineTable, "Code", "Description", wcGDB_path, "Line Type", "Drainage line types", "REPLACE")
    if not "Method" in domains:
        methodTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_method")
        arcpy.TableToDomain_management(methodTable, "Code", "Description", wcGDB_path, "Method", "Choices for wetland determination method", "REPLACE")
    if not "Pre Post" in domains:
        prepostTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_pre_post")
        arcpy.TableToDomain_management(prepostTable, "Code", "Description", wcGDB_path, "Pre Post", "Choices for date relative to 1985", "REPLACE")
    if not "Request Type" in domains:
        requestTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_request_type")
        arcpy.TableToDomain_management(requestTable, "Code", "Description", wcGDB_path, "Request Type", "Choices for request type form", "REPLACE")
    if not "ROP Status" in domains:
        ropTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_rop_status")
        arcpy.TableToDomain_management(ropTable, "Code", "Description", wcGDB_path, "ROP Status", "Choices for ROP status", "REPLACE")
    if not "Wetland Labels" in domains:
        wetTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_wetland_labels")
        arcpy.TableToDomain_management(wetTable, "Code", "Description", wcGDB_path, "Wetland Labels", "Choices for wetland determination labels", "REPLACE")
    if not "Yes No" in domains:
        yesnoTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_yesno")
        arcpy.TableToDomain_management(yesnoTable, "Code", "Description", wcGDB_path, "Yes No", "Yes or no options", "REPLACE")
    if not "YN" in domains:
        ynTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_yn")
        arcpy.TableToDomain_management(ynTable, "Code", "Description", wcGDB_path, "YN", "Y or N options", "REPLACE")

    del descGDB, domains

##    # HEL Domains
##    descGDB = arcpy.Describe(helGDB_path)
##    domains = descGDB.domains
##
##    if not "Yes No" in domains:
##        yesnoTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_yesno")
##        arcpy.TableToDomain_management(yesnoTable, "Code", "Description", helGDB_path, "Yes No", "Yes or no options", "REPLACE")
##    if not "HEL Type" in domains:
##        helTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_hel")
##        arcpy.TableToDomain_management(helTable, "Code", "Description", helGDB_path, "HEL Type", "Choices for HEL label", "REPLACE")
##    if not "HEL Request Type" in domains:
##        helreqTable = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb" + os.sep + "domain_hel_request_type")
##        arcpy.TableToDomain_management(helreqTable, "Code", "Description", helGDB_path, "HEL Request Type", "Choice for HEL request form", "REPLACE")
##
##    del descGDB, domains


    #### Remove the existing projectCLU layer from the Map
    AddMsgAndPrint("\nRemoving CLU layer from project maps, if present...\n",0)
    mapLayersToRemove = [cluOut, extentOut]
    try:
        for maps in aprx.listMaps():
            for lyr in maps.listLayers():
                if lyr.name in mapLayersToRemove:
                    maps.removeLayer(lyr)
    except:
        pass

    
    #### If overwrite was selected, delete existing starting datasets (CLU, Tract, and Tract/Request Data Table)
    if owFlag == True:
        if arcpy.Exists(projectCLU):
            AddMsgAndPrint("\nOverwrite selected. Deleting existing data...",0)
            datasetsToRemove = [projectCLU, projectTract, projectTractB, projectAOI, projectExtent]
            for dataset in datasetsToRemove:
                if arcpy.Exists(dataset):
                    try:
                        arcpy.Delete_management(dataset)
                    except:
                        pass
            del dataset, datasetsToRemove


    #### Download the CLU
    # If the CLU doesn't exist, download it
    if not arcpy.Exists(projectCLU):
        AddMsgAndPrint("\nDownloading latest CLU data for input tract number...",0)
        downloadCLU(adminState, adminCounty, tractNumber, outSpatialRef, basedataGDB_path)


    #### Add state name and county name fields to the CLU feature class
    # Add fields
    arcpy.AddField_management(projectCLU, "admin_state_name", "TEXT", "64")
    arcpy.AddField_management(projectCLU, "admin_county_name", "TEXT", "64")
    arcpy.AddField_management(projectCLU, "state_name", "TEXT", "64")
    arcpy.AddField_management(projectCLU, "county_name", "TEXT", "64")

    # Search the downloaded CLU for geographic state and county codes
    stateCo, countyCo = '', ''
    field_names = ['state_code','county_code']
    with arcpy.da.SearchCursor(projectCLU, field_names) as cursor:
        for row in cursor:
            stateCo = row[0]
            countyCo = row[1]
            break
                                   
    # Search for names using FIPS codes.
    stName, coName = '', ''
    fields = ['STATEFP','COUNTYFP','NAME','STATE']
    field1 = 'STATEFP'
    field2 = 'COUNTYFP'
    expression = "{} = '{}'".format(arcpy.AddFieldDelimiters(lut,field1), stateCo) + " AND " + "{} = '{}'".format(arcpy.AddFieldDelimiters(lut,field2), countyCo)
    with arcpy.da.SearchCursor(lut, fields, where_clause = expression) as cursor:
        for row in cursor:
            coName = row[2]
            stName = row[3]
            break

    if stName == '' or coName == '':
        arcpy.AddError("State and County Names for the site could not be retrieved! Exiting...\n")
        exit()

    # Use Update Cursor to populate all rows of the downloaded CLU the same way for the new fields
    field_names = ['admin_state_name','admin_county_name','state_name','county_name']
    with arcpy.da.UpdateCursor(projectCLU, field_names) as cursor:
        for row in cursor:
            row[0] = sourceState
            row[1] = sourceCounty
            row[2] = stName
            row[3] = coName
            cursor.updateRow(row)
    del field_names

    
    #### Buffer Tract and create extent layers
    # If the Tract layer doesn't exist, create it and overwrite its related buffer layers
    if not arcpy.Exists(projectTract):
        AddMsgAndPrint("\nCreating tract data...",0)

        dis_fields = ['admin_state','admin_state_name','admin_county','admin_county_name','state_code','state_name','county_code','county_name','farm_number','tract_number']
        arcpy.Dissolve_management(projectCLU, projectTract, dis_fields, "", "MULTI_PART", "")
        del dis_fields

        # Always re-create the buffered areas if you have updated the tract
        arcpy.Buffer_analysis(projectTract, projectTractB, bufferDist, "FULL", "", "ALL", "")
        arcpy.Buffer_analysis(projectTract, projectAOI, bufferDistPlus, "FULL", "", "ALL", "")

    # If the tract exists, but the buffer doesn't, re-create both buffers. Overwrite flag applies to the 2nd one.
    if not arcpy.Exists(projectTractB):
        arcpy.Buffer_analysis(projectTract, projectTractB, bufferDist, "FULL", "", "ALL", "")
        arcpy.Buffer_analysis(projectTract, projectAOI, bufferDistPlus, "FULL", "", "ALL", "")


    #### Create the Determination Extent Layer as a copy of the CLU layer
    if not arcpy.Exists(projectExtent):
        AddMsgAndPrint("\nCreating Extent layer...",0)
        arcpy.FeatureClassToFeatureClass_conversion(projectCLU, basedataFD, extentName)
    if owFlag == True:
        AddMsgAndPrint("\nCLU overwrite was selected. Resetting the layer extent as a result...",0)
        arcpy.FeatureClassToFeatureClass_conversion(projectCLU, basedataFD, extentName)


    #### Zoom to tract quarter mile buffer (not possible to Implement in Pro?)
##    AddMsgAndPrint("\nZooming to tract...",0)
##    fc = projectCLU
##    arcpy.MakeFeatureLayer_management(fc, "CLUExtent")
##    mxd = arcpy.mapping.MapDocument("CURRENT")
##    df = arcpy.mapping.ListDataFrames(mxd)[0]
##    lyr = arcpy.mapping.Layer("CLUExtent")
##    df.extent = lyr.getExtent()
##    df.scale = df.scale * 1.1
##    arcpy.Delete_management("CLUExtent")
##    del fc, mxd, df, lyr
##    AddMsgAndPrint("\tSuccessful",0)


    #### Prepare to add to map
    if not arcpy.Exists(cluOut):
        arcpy.SetParameterAsText(7, projectCLU)
    if not arcpy.Exists(extentOut):
        arcpy.SetParameterAsText(8, projectExtent)

    
    #### Compact FGDB
    try:
        AddMsgAndPrint("\nCompacting File Geodatabase..." ,0)
        arcpy.Compact_management(basedataGDB_path)
        arcpy.Compact_management(wcGDB_path)
##        arcpy.Compact_management(helGDB_path)
        AddMsgAndPrint("\tSuccessful",0)
    except:
        pass

except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested. Exiting...")

except:
    errorMsg()
