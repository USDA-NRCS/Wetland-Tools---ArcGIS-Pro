#-------------------------------------------------------------------------------
# Name:        Extract CLUs by Tract
# Purpose:
#
# Author: Adolfo.Diaz
#         GIS Specialist
#         National Soil Survey Center
#         USDA - NRCS
# e-mail: adolfo.diaz@usda.gov
# phone: 608.662.4422 ext. 216
#
# Created:     02/27/2020
# Originallly created for the NRCS Wetland Tools.  This tool can be called via an ArcGIS Pro
# tool or can be called from another script.
#
# ==========================================================================================
# Modified 7/8/2021
# Modified the where_clause that is sent to the CLU REST API to use county_ansi_code field
# instead of admin_county field for Alaska only.

# ==========================================================================================
# Modified 7/30/2021
# - Updated getCLUgeometry function to distinguish between an error when submitting a request
#   to the clu REST API vs. returning no geometry associated with a specific tract.
#   If any condition is true, the cluFC will also be deleted.
# - Updated messaging on projecting.  If a transformation method is needed then the message
#   will be a warning otherwise a simple message will be printed.


# ==============================================================================================================================
def AddMsgAndPrint(msg, severity=0):
    # prints message to screen if run as a python script
    # Adds tool message to the geoprocessor
    #
    #Split the message on \n first, so that if it's multiple lines, a GPMessage will be added for each line
    try:

        print(msg)
        #for string in msg.split('\n'):
            #Add a geoprocessing message (in case this is run as a tool)
        if severity == 0:
            arcpy.AddMessage(msg)

        elif severity == 1:
            arcpy.AddWarning(msg)

        elif severity == 2:
            arcpy.AddError("\n" + msg)

    except:
        pass

# ==============================================================================================================================
def errorMsg():
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

# ===================================================================================
def setScratchWorkspace():
    """ This function will set the scratchWorkspace for the interim of the execution
        of this tool.  The scratchWorkspace is used to set the scratchGDB which is
        where all of the temporary files will be written to.  The path of the user-defined
        scratchWorkspace will be compared to existing paths from the user's system
        variables.  If there is any overlap in directories the scratchWorkspace will
        be set to C:\TEMP, assuming C:\ is the system drive.  If all else fails then
        the packageWorkspace Environment will be set as the scratchWorkspace. This
        function returns the scratchGDB environment which is set upon setting the scratchWorkspace"""

    try:
        AddMsgAndPrint("\nSetting Scratch Workspace")
        scratchWK = arcpy.env.scratchWorkspace

        # -----------------------------------------------
        # Scratch Workspace is defined by user or default is set
        if scratchWK is not None:

            # dictionary of system environmental variables
            envVariables = os.environ

            # get the root system drive i.e C:
            if envVariables.has_key('SYSTEMDRIVE'):
                sysDrive = envVariables['SYSTEMDRIVE']
            else:
                sysDrive = None

            varsToSearch = ['ESRI_OS_DATADIR_LOCAL_DONOTUSE','ESRI_OS_DIR_DONOTUSE','ESRI_OS_DATADIR_MYDOCUMENTS_DONOTUSE',
                            'ESRI_OS_DATADIR_ROAMING_DONOTUSE','TEMP','LOCALAPPDATA','PROGRAMW6432','COMMONPROGRAMFILES','APPDATA',
                            'USERPROFILE','PUBLIC','SYSTEMROOT','PROGRAMFILES','COMMONPROGRAMFILES(X86)','ALLUSERSPROFILE']

##            """ This is a printout of my system environmmental variables - Windows 7
##            -----------------------------------------------------------------------------------------
##            ESRI_OS_DATADIR_LOCAL_DONOTUSE C:\Users\adolfo.diaz\AppData\Local\
##            ESRI_OS_DIR_DONOTUSE C:\Users\ADOLFO~1.DIA\AppData\Local\Temp\6\arc3765\
##            ESRI_OS_DATADIR_MYDOCUMENTS_DONOTUSE C:\Users\adolfo.diaz\Documents\
##            ESRI_OS_DATADIR_COMMON_DONOTUSE C:\ProgramData\
##            ESRI_OS_DATADIR_ROAMING_DONOTUSE C:\Users\adolfo.diaz\AppData\Roaming\
##            TEMP C:\Users\ADOLFO~1.DIA\AppData\Local\Temp\6\arc3765\
##            LOCALAPPDATA C:\Users\adolfo.diaz\AppData\Local
##            PROGRAMW6432 C:\Program Files
##            COMMONPROGRAMFILES :  C:\Program Files (x86)\Common Files
##            APPDATA C:\Users\adolfo.diaz\AppData\Roaming
##            USERPROFILE C:\Users\adolfo.diaz
##            PUBLIC C:\Users\Public
##            SYSTEMROOT :  C:\Windows
##            PROGRAMFILES :  C:\Program Files (x86)
##            COMMONPROGRAMFILES(X86) :  C:\Program Files (x86)\Common Files
##            ALLUSERSPROFILE :  C:\ProgramData """
##            """------------------------------------------------------------------------------------------"""

            bSetTempWorkSpace = False

            """ Iterate through each Environmental variable; If the variable is within the 'varsToSearch' list
                above then check their value against the user-set scratch workspace.  If they have anything
                in common then switch the workspace to something local  """
            for var in envVariables:

                if not var in varsToSearch:
                    continue

                # make a list from the scratch and environmental paths
                varValueList = (envVariables[var].lower()).split(os.sep)          # ['C:', 'Users', 'adolfo.diaz', 'AppData', 'Local']
                scratchWSList = (scratchWK.lower()).split(os.sep)                 # [u'C:', u'Users', u'adolfo.diaz', u'Documents', u'ArcGIS', u'Default.gdb', u'']

                # remove any blanks items from lists
                if '' in varValueList: varValueList.remove('')
                if '' in scratchWSList: scratchWSList.remove('')

                # First element is the drive letter; remove it if they are
                # the same otherwise review the next variable.
                if varValueList[0] == scratchWSList[0]:
                    scratchWSList.remove(scratchWSList[0])
                    varValueList.remove(varValueList[0])

                # obtain a similarity ratio between the 2 lists above
                #sM = SequenceMatcher(None,varValueList,scratchWSList)

                # Compare the values of 2 lists; order is significant
                common = [i for i, j in zip(varValueList, scratchWSList) if i == j]

                if len(common) > 0:
                    bSetTempWorkSpace = True
                    break

            # The current scratch workspace shares 1 or more directory paths with the
            # system env variables.  Create a temp folder at root
            if bSetTempWorkSpace:
                AddMsgAndPrint("\tCurrent Workspace: " + scratchWK,0)

                if sysDrive:
                    tempFolder = sysDrive + os.sep + "TEMP"

                    if not os.path.exists(tempFolder):
                        os.makedirs(tempFolder,mode=777)

                    arcpy.env.scratchWorkspace = tempFolder
                    AddMsgAndPrint("\tTemporarily setting scratch workspace to: " + arcpy.env.scratchGDB,1)

                else:
                    packageWS = [f for f in arcpy.ListEnvironments() if f=='packageWorkspace']
                    if arcpy.env[packageWS[0]]:
                        arcpy.env.scratchWorkspace = arcpy.env[packageWS[0]]
                        AddMsgAndPrint("\tTemporarily setting scratch workspace to: " + arcpy.env.scratchGDB,1)
                    else:
                        AddMsgAndPrint("\tCould not set any scratch workspace",2)
                        return False

            # user-set workspace does not violate system paths; Check for read/write
            # permissions; if write permissions are denied then set workspace to TEMP folder
            else:
                arcpy.env.scratchWorkspace = scratchWK

                if arcpy.env.scratchGDB == None:
                    AddMsgAndPrint("\tCurrent scratch workspace: " + scratchWK + " is READ only!",0)

                    if sysDrive:
                        tempFolder = sysDrive + os.sep + "TEMP"

                        if not os.path.exists(tempFolder):
                            os.makedirs(tempFolder,mode=777)

                        arcpy.env.scratchWorkspace = tempFolder
                        AddMsgAndPrint("\tTemporarily setting scratch workspace to: " + arcpy.env.scratchGDB,1)

                    else:
                        packageWS = [f for f in arcpy.ListEnvironments() if f=='packageWorkspace']
                        if arcpy.env[packageWS[0]]:
                            arcpy.env.scratchWorkspace = arcpy.env[packageWS[0]]
                            AddMsgAndPrint("\tTemporarily setting scratch workspace to: " + arcpy.env.scratchGDB,1)

                        else:
                            AddMsgAndPrint("\tCould not set any scratch workspace",2)
                            return False

                else:
                    AddMsgAndPrint("\tUser-defined scratch workspace is set to: "  + arcpy.env.scratchGDB,0)

        # No workspace set (Very odd that it would go in here unless running directly from python)
        else:
            AddMsgAndPrint("\tNo user-defined scratch workspace ",0)
            sysDrive = os.environ['SYSTEMDRIVE']

            if sysDrive:
                tempFolder = sysDrive + os.sep + "TEMP"

                if not os.path.exists(tempFolder):
                    os.makedirs(tempFolder,mode=777)

                arcpy.env.scratchWorkspace = tempFolder
                AddMsgAndPrint("\tTemporarily setting scratch workspace to: " + arcpy.env.scratchGDB,1)

            else:
                packageWS = [f for f in arcpy.ListEnvironments() if f=='packageWorkspace']
                if arcpy.env[packageWS[0]]:
                    arcpy.env.scratchWorkspace = arcpy.env[packageWS[0]]
                    AddMsgAndPrint("\tTemporarily setting scratch workspace to: " + arcpy.env.scratchGDB,1)

                else:
                    AddMsgAndPrint("\tCould not set scratchWorkspace. Not even to default!",2)
                    return False

        #arcpy.Compact_management(arcpy.env.scratchGDB)
        return arcpy.env.scratchGDB

    except:

        # All Failed; set workspace to packageWorkspace environment
        try:
            packageWS = [f for f in arcpy.ListEnvironments() if f=='packageWorkspace']
            if arcpy.env[packageWS[0]]:
                arcpy.env.scratchWorkspace = arcpy.env[packageWS[0]]
                arcpy.Compact_management(arcpy.env.scratchGDB)
                return arcpy.env.scratchGDB
            else:
                AddMsgAndPrint("\tCould not set scratchWorkspace. Not even to default!",2)
                return False
        except:
            errorMsg()
            return False

# ===================================================================================
def splitThousands(someNumber):
    """will determine where to put a thousands seperator if one is needed. Input is
       an integer.  Integer with or without thousands seperator is returned."""

    try:
        return re.sub(r'(\d{3})(?=\d)', r'\1,', str(someNumber)[::-1])[::-1]

    except:
        errorMsg()
        return someNumber

# ===================================================================================
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

# ===================================================================================
def submitFSquery(url,INparams):
    """ This function will send a spatial query to a web feature service and convert
        the results into a python structure.  If the results from the service is an
        error due to an invalid token then a second attempt will be sent with using
        a newly generated arcgis token.  If the token is good but the request returned
        with an error a second attempt will be made.  The funciion takes in 2 parameters,
        the URL to the web service and a query string in URLencoded format.

        Error produced with invalid token
        {u'error': {u'code': 498, u'details': [], u'message': u'Invalid Token'}}

        The function returns requested data via a python dictionary"""

    try:
        # Python 3.6 - ArcPro
        # Data should be in bytes; new in Python 3.6
        if bArcGISPro:
            INparams = INparams.encode('ascii')
            resp = urllib.request.urlopen(url,INparams)  # A failure here will probably throw an HTTP exception
        # Python 2.7 - ArcMap
        else:
            req = urllib2.Request(url,INparams)
            resp = urllib2.urlopen(req)

        responseStatus = resp.getcode()
        responseMsg = resp.msg
        jsonString = resp.read()

        # json --> Python; dictionary containing 1 key with a list of lists
        results = json.loads(jsonString)

        # Check for expired token; Update if expired and try again
        if 'error' in results.keys():
           if results['error']['message'] == 'Invalid Token':
               AddMsgAndPrint("\tRegenerating ArcGIS Token Information")

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

               if bArcGISPro:
                   newParams = newParams.encode('ascii')

               # update incoming parameters just in case a 2nd attempt is needed
               INparams = newParams

               # Python 3.6 - ArcPro
               if bArcGISPro:
                   resp = urllib.request.urlopen(url,newParams)  # A failure here will probably throw an HTTP exception
               else:
                   req = urllib2.Request(url,newParams)
                   resp = urllib2.urlopen(req)

               responseStatus = resp.getcode()
               responseMsg = resp.msg
               jsonString = resp.read()

               results = json.loads(jsonString)

        # Check results before returning them; Attempt a 2nd request if results are bad.
        if 'error' in results.keys() or len(results) == 0:
            time.sleep(5)

            if bArcGISPro:
                resp = urllib.request.urlopen(url,INparams)  # A failure here will probably throw an HTTP exception
            else:
                req = urllib2.Request(url,INparams)
                resp = urllib2.urlopen(req)

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

# ===================================================================================
def createOutputFC(metadata,outputWS,shape="POLYGON"):
    """ This function will create an empty polygon feature class within the outputWS
        The feature class will be set to the same spatial reference as the Web Feature
        Service. All fields part of the WFS will also be added to the new feature class.
        A field dictionary containing the field names and their property will also be
        returned.  This fieldDict will be used to create the fields in the CLU fc and
        by the getCLUgeometry insertCursor.

        fieldDict ={field:(fieldType,fieldLength,alias)
        i.e {'clu_identifier': ('TEXT', 36, 'clu_identifier'),'clu_number': ('TEXT', 7, 'clu_number')}

        Return the field dictionary and new feature class including the path
        Return False if error ocurred."""

    try:
        # output FC will have the 'CLU_' as a prefix along with the state, county and tract number
        newFC = outputWS + os.sep + "CLU_" + str(adminState) + "_" + str(adminCounty) + "_" + str(tractNumber)

        AddMsgAndPrint("\nCreating New Feature Class: " + os.path.basename(newFC))
        arcpy.SetProgressorLabel("Creating New Feature Class: " + os.path.basename(newFC))

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
        fsFields = metadata['fields']   # {u'alias':u'land_unit_id',u'domain': None, u'name': u'land_unit_id', u'nullable': True, u'editable': True, u'alias': u'LAND_UNIT_ID', u'length': 38, u'type': u'esriFieldTypeString'}
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

# ===================================================================================
def getCLUgeometryByTractQuery(sqlQuery,fc,RESTurl):
    """ This funciton will will retrieve CLU geometry from the CLU WFS and assemble
        into the CLU fc along with the attributes associated with it.
        It is intended to receive requests that will return records that are
        below the WFS record limit"""

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

        # Error from sumbitFSquery function
        if not geometry:
            return False

        # make sure the request returned geometry; otherwise return False
        if not len(geometry['features']):
            AddMsgAndPrint("\nThere were no CLU fields associated with tract Number " + str(tractNumber),1)
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

# ===================================================================================
def start(state,county,trctNmbr,outSR,outWS,addCLUtoSoftware=False):

    try:
        # Use most of the cores on the machine where ever possible
        arcpy.env.parallelProcessingFactor = "75%"

        global bArcGISPro
        global adminState, adminCounty, tractNumber, outSpatialRef, outputWS
        global bUserDefinedSR
        global urllibEncode, parseQueryString
        global portalToken, fldsDict, fields

        adminState = state
        adminCounty = county
        tractNumber = trctNmbr
        outSpatialRef = outSR
        outputWS = outWS

        # user defined an output spatial reference
        # check if it is an SR object or WKT
        bUserDefinedSR = False
        if outSpatialRef != '':

            # Using a well-known text string representation
            # convert it to a SR object
            if type(outSpatialRef) is str:
                sr = arcpy.SpatialReference()
                sr.loadFromString(outSpatialRef)
                outSpatialRef = sr
            bUserDefinedSR = True

        # Determine the ESRI product and set boolean
        productInfo = arcpy.GetInstallInfo()['ProductName']

         # Python 3.6 - ArcPro
        if productInfo == 'ArcGISPro':
            bArcGISPro = True
            from urllib.request import Request, urlopen
            from urllib.error import HTTPError as httpErrors
            urllibEncode = urllib.parse.urlencode
            parseQueryString = urllib.parse.parse_qsl

            # Get the spatial reference of the Active Map from which the tool was invoked
            # and set the WKID as the env.outputCoordSystem
            if not bUserDefinedSR:
                aprx = arcpy.mp.ArcGISProject("CURRENT")
                activeMap = aprx.activeMap

                # If the tool is invoked by the catalog view vs the catalog pane
                # an active map will not be registered so a coordinate system
                # object cannot be obtained.  Exit.
                try:
                    activeMapName = activeMap.name
                    activeMapSR = activeMap.getDefinition('V2').spatialReference['latestWkid']
                    outSpatialRef = arcpy.SpatialReference(activeMapSR)
                    arcpy.env.outputCoordinateSystem = outSpatialRef
                except:
                    AddMsgAndPrint("Could not obtain Spatial Reference from the ArcGIS Pro Map",2)
                    AddMsgAndPrint("Run the tool from an active map or provide a Coordinate System.  Exiting!",2)
                    exit()

        # Python 2.7 - ArcMap
        else:
            bArcGISPro = False
            import urllib2
            import urlparse                              # This library is included in urllib in 3.7
            from urllib2 import HTTPError as httpErrors
            urllibEncode = urllib.urlencode
            parseQueryString = urlparse.parse_qsl

            if not bUserDefinedSR:

                # If the tool is invoked by ArcCatalog then the dataframe
                # properties is not available so a coordinate system
                # object cannot be obtained.  Exit.
                try:
                    mxd = arcpy.mapping.MapDocument(r"CURRENT")
                    df = arcpy.mapping.ListDataFrames(mxd)[0]
                    outSpatialRef = df.spatialReference
                    arcpy.env.outputCoordinateSystem = outSpatialRef
                except:
                    AddMsgAndPrint("Could not obtain Spatial Reference from the ArcMap Data Frame",2)
                    AddMsgAndPrint("Run the tool from within ArcMap or provide a Coordinate System.  Exiting!",2)
                    exit()

        arcpy.env.overwriteOutput = True
        arcpy.env.geographicTransformations = "WGS_1984_(ITRF00)_To_NAD_1983"

##        scratchWS = arcpy.env.scratchWorkspace
##        scratchWS = r'E:\Temp\scratch.gdb'
##
##        if not arcpy.Exists(scratchWS):
##            scratchWS = setScratchWorkspace()
##            arcpy.env.scratchWorkspace = scratchWS

        """ ---------------------------------------------- ArcGIS Portal Information ---------------------------"""
        nrcsPortal = 'https://gis.sc.egov.usda.gov/portal/'
        portalToken = getPortalTokenInfo(nrcsPortal)
        #portalToken = {'token': 'CaQsxS5eSCBOnMVy9FA0JcKM1lFix1rf5pAdJe9RJLjlv9UVbW3uS92x9WCi0S6LmpO3EMaZkwQ1-hbZgF_wGBX_UHVZbVPComH5hhRgBDjubjXe6zPFpG-FlwQ490epn3ebKEG55FSbhihK0c2ueS0xzPaPHMA79IUGOpaeGsADPS0zNId4ofPeUI6KAwAoQu3H6ibePO5YLHgM0oVeAQv1poNf1_moeNPH3ZHU5uMuCTy8DvLGLMwuNnWw65wCYX7oBDQjoP9g8zc7cqVYmw..', 'referer': 'http://www.esri.com/AGO/780B38ED-ECB9-40FF-B734-3A7A6402C884', 'expires': 1627658762}

        if not portalToken:
           AddMsgAndPrint("Could not generate Portal Token. Exiting!",2)
           exit()

        """ --------------------------------------------- get Feature Service Metadata -------------------------------"""
        # URL for Feature Service Metadata (Service Definition) - Dictionary of ;
        cluRESTurl_Metadata = """https://gis.sc.egov.usda.gov/appserver/rest/services/common_land_units/common_land_units/FeatureServer/0"""

        # Used for admin or feature service info; Send POST request
        params = urllibEncode({'f': 'json','token': portalToken['token']})

        # request info about the feature service
        fsMetadata = submitFSquery(cluRESTurl_Metadata,params)

        # Create empty CLU FC with necessary fields
        # fldsDict - {'clu_number': ('TEXT', 7, 'clu_number')}
        fldsDict,cluFC = createOutputFC(fsMetadata,outputWS)
        #fldsDict['SHAPE@JSON'] = ('SHAPE')

        # Isolate the fields that were inserted into new fc
        # Python 3.6 returns a <class 'dict_keys'>
        # Python 2.7 returns a <type 'list'>
        fields = fldsDict.keys()

        # Convert to a list b/c Python 3.6 doesn't support .append
        if bArcGISPro:
           fields = list(fields)

        fields.append('SHAPE@JSON')

        # Get the Max record count the REST service can return
        if not 'maxRecordCount' in fsMetadata:
           AddMsgAndPrint('\t\tCould not determine FS maximum record count: Setting default to 1,000 records',1)
           maxRecordCount = 1000
        else:
           maxRecordCount = fsMetadata['maxRecordCount']

        """ ---------------------------------------------- query by Admin State, Admin County and Tract Number -----------------------------"""
        cluRESTurl = """https://gis.sc.egov.usda.gov/appserver/rest/services/common_land_units/common_land_units/FeatureServer/0/query"""

        # ADMIN_STATE = 29 AND ADMIN_COUNTY = 017 AND TRACT_NUMBER = 1207
        # This was updated for Alaska purpose only b/c Alaska doesn't use Admin_county, they use county_ansi_code
        if adminState == '02':
            whereClause = "ADMIN_STATE = " + str(adminState) + " AND COUNTY_ANSI_CODE = " + str(adminCounty) + " AND TRACT_NUMBER = " + str(tractNumber)
        else:
            whereClause = "ADMIN_STATE = " + str(adminState) + " AND ADMIN_COUNTY = " + str(adminCounty) + " AND TRACT_NUMBER = " + str(tractNumber)

        AddMsgAndPrint("Querying USDA-NRCS GeoPortal for CLU fields where: " + whereClause)

        # Send geometry request to cluREST API
        if not getCLUgeometryByTractQuery(whereClause,cluFC,cluRESTurl):

            try:
                arcpy.Delete_management(cluFC)
            except:
                pass

            # Script executed directly from ArcGIS Pro
            if addCLUtoSoftware:
                AddMsgAndPrint("Exiting",1)
                exit()

            # Script executed from another script
            else:
                return False

        # Report # of fields assembled
        numOfCLUs = int(arcpy.GetCount_management(cluFC)[0])
        if numOfCLUs > 1:
            AddMsgAndPrint("\nThere are " + splitThousands(numOfCLUs) + " CLU fields associated with tract number " + str(tractNumber))
        else:
            AddMsgAndPrint("\nThere is " + splitThousands(numOfCLUs) + " CLU field associated with tract number " + str(tractNumber))

        """ ---------------------------------------------- Project CLU ---------------------------------------------------------------"""
        # Project cluFC to user-defined spatial reference or the spatial
        # reference set in the AcrGIS Pro Map or Arcmap Dataframe

        fromSR = arcpy.Describe(cluFC).spatialReference
        toSR = outSpatialRef

        geoTransformation = arcpy.ListTransformations(fromSR,toSR)
        if len(geoTransformation):
            geoTransformation = geoTransformation[0]
            msg = 1
        else:
            geoTransformation = None
            msg = 0

        projected_CLU = cluFC + "_prj"
        arcpy.Project_management(cluFC,projected_CLU,toSR,geoTransformation)

        arcpy.Delete_management(cluFC)
        arcpy.Rename_management(projected_CLU,projected_CLU[0:-4])
        cluFC = projected_CLU[0:-4]

        AddMsgAndPrint(" ",msg)
        AddMsgAndPrint("\nProjecting CLU Feature class",msg)
        AddMsgAndPrint("FROM: " + str(fromSR.name),msg)
        AddMsgAndPrint("TO: " + str(toSR.name),msg)
        AddMsgAndPrint("Geographic Transformation used: " + str(geoTransformation),msg)

        # Add final CLU layer to either ArcPro or ArcMap
        if addCLUtoSoftware:
            if bArcGISPro:
                # Add the data to the first ArcPro Map found
                aprx = arcpy.mp.ArcGISProject("CURRENT")
                aprxMaps = aprx.listMaps()

                try:
                    activeMap = aprx.activeMap
                    activeMapName = activeMap.name

                    for map in aprxMaps:
                        if map.name == activeMapName:
                            map.addDataFromPath(cluFC)
                            AddMsgAndPrint(os.path.basename(cluFC) + " added to " + map.name + " Map")
                            break

                except:
                    map = aprx.listMaps()[0]
                    map.addDataFromPath(cluFC)
                    AddMsgAndPrint(os.path.basename(cluFC) + " added to " + map.name + " Map")

            else:
                # could be executed from ArcCatalog
                try:
                    mxd = arcpy.mapping.MapDocument("CURRENT")
                    df = arcpy.mapping.ListDataFrames(mxd)[0]
                    cluLayer = arcpy.mapping.Layer(cluFC)
                    arcpy.mapping.AddLayer(df,cluLayer,"TOP")
                except:
                    pass

        else:
            return cluFC

    except:
        errorMsg()

# ====================================== Main Body ==================================
# Import modules
import sys, string, os, traceback
import urllib, re, time, json, random
import arcpy

if __name__ == '__main__':

    try:
        adminState = arcpy.GetParameterAsText(0)
        adminCounty = arcpy.GetParameterAsText(1)
        tractNumber = arcpy.GetParameterAsText(2)
        outSpatialRef = arcpy.GetParameterAsText(3)
        outputWS = arcpy.GetParameterAsText(4)
        addToSoftware = True

##        adminState = "55"
##        adminCounty = "025"
##        tractNumber = "336499"
##        outSpatialRef = "GEOGCS['GCS_WGS_1984',DATUM['D_WGS_1984',SPHEROID['WGS_1984',6378137.0,298.257223563]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]];-400 -400 1000000000;-100000 10000;-100000 10000;8.98315284119521E-09;0.001;0.001;IsHighPrecision"
##        outputWS = r'E:\Temp\scratch.gdb'
##        addToSoftware = False

        start(adminState,adminCounty,tractNumber,outSpatialRef,outputWS,addToSoftware)

    except:
        errorMsg()

