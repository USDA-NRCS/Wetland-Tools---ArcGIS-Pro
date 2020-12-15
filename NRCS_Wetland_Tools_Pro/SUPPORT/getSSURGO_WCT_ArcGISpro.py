#-------------------------------------------------------------------------------
# Name:        getSSURGO_WCT.py
# Purpose:
#
# Author:      Chad.Ferguson
#
# Created:     19/07/2016
# Copyright:   (c) Charles.Ferguson 2016

# Author: Adolfo.Diaz
#         GIS Specialist
#         National Soil Survey Center
#         USDA - NRCS
# e-mail: adolfo.diaz@usda.gov
# phone: 608.662.4422 ext. 216

# Electrial Conductivity 1:5 by volume - Rep Value was removed, exists in rslvProp, just remoed from validator
# Exchangeable Sodium Percentage - Rep Value was removed, exists in rslvProp, just remoed from validator
# Ki ditto
# Kr ditto
# Unrubber Fiber % - Rep Value
# Rubbed Fiber % - Rep Value
#-------------------------------------------------------------------------------



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

# ==============================================================================================================================
def getSSURGOgeometryFromSDA(aoi, outputWS, outputName="SSURGO_SDA"):
    # Description:
    # This function will create a spatial layer of SSURGO geometry from Soil Data Access using
    # the minimum bounding coordinates from the inFC (input Feature Class)
    # The output spatial layer will be in WGS84 Lat Long Coordinates.
    # The tabular fields will include: areasymbol, musym, munme, and mukey

    # Parameters
    # aoi -      input area of interest that will be used to intersect geometry from SDA.  The
    #            coordinate system of the aoi will be set to WGS84.
    # outputWS - the location of where the SSURGO geometry will be written to.
    #            If the outputWS is a FGDB then the output layer will be a FGDB feature class.
    #            If the outputWS is a folder then the output layer will ba a Shapefile.

    # Prior to the query request, a feature class called "SSURGO_WCT" will be created in WGS84
    # with an MUKEY field.  The original subfunction also created a .lyr file from the feature class
    # but that functionality was commented out.

    # Returns
    # This function returns the directory path to the output spatial layer when it
    # successfully executes.
    # This function will return False if:
    #     - Output workspace is not a FGDB, Folder or FGDB Feature dataset
    #     - The minimum bounding coordinates could not be determined from AOI
    #     - An HTTP Error occurred such as a bad query, server timeout or no response from server

    # Future Upgrades
    # SSURGO spatial version metadata should be included
    # Metadata should be in written into

    # Here is an example of the query submitted to SDA:

    """ --------------------------- OLD Query ------------------------------------
    ~DeclareGeometry(@aoi)~
    select @aoi = geometry::STPolyFromText('POLYGON (( -93.557235688 44.189167781,-93.557235688 44.19613589,-93.547238902 44.19613589,-93.547238902 44.189167781,-93.557235688 44.189167781,-93.557235688 44.189167781))', 4326)
    ~DeclareIdGeomTable(@intersectedPolygonGeometries)~
    ~GetClippedMapunits(@aoi,polygon,geo,@intersectedPolygonGeometries)~

    -- Return WKT for the polygonal geometries
    select * from @intersectedPolygonGeometries where geom.STGeometryType() = 'Polygon'
    where geom.STGeometryType() = 'Polygon'
    """

    """ --------------------------- New Query ------------------------------------
    ~DeclareGeometry(@aoi)~
    select @aoi = geometry::STPolyFromText('POLYGON (( -93.557235688 44.189167781,-93.557235688 44.19613589,-93.547238902 44.19613589,-93.547238902 44.189167781,-93.557235688 44.189167781,-93.557235688 44.189167781))', 4326)
    ~DeclareIdGeomTable(@intersectedPolygonGeometries)~
    ~GetClippedMapunits(@aoi,polygon,geo,@intersectedPolygonGeometries)~

    SELECT areasymbol, M.musym, M.muname, id AS mukey, geom
    FROM @intersectedPolygonGeometries
    INNER JOIN mapunit M ON id = M.mukey
    INNER JOIN legend L ON M.lkey = L.lkey
    """

    try:
        # Determine output SSURGO layer depending on output Workspace
        desc = arcpy.Describe(outputWS)
        if desc.dataType == 'Workspace':
            outSSURGOlayerPath = outputWS + os.sep + outputName
        elif desc.dataType == 'Folder':
            outSSURGOlayerPath = outputWS + os.sep + outputName + ".shp"
        elif desc.dataType == 'FeatureDataset':
            outSSURGOlayerPath = os.path.dirname(outputWS) + outputName
        else:
            AddMsgAndPrint("\nOutput Workspace is invalid: " + str(outputWS),2)
            return False

        arcpy.env.workspace = outputWS

        # Delete outputSSURGOlayer if it exists
        if arcpy.Exists(outSSURGOlayerPath):
            arcpy.Delete_management(outSSURGOlayerPath)
            AddMsgAndPrint("\nSuccessully deleted " + outSSURGOlayerPath)

        # Create a minimum bounding polygon from input AOI feature
        # This is the easiest way to get 4 coordinates in Lat/Long.
        arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(4326)
        minBoundary = "in_memory\minBound"
        try:
            arcpy.Delete_management("in_memory\minBound")
        except:
            pass
        arcpy.MinimumBoundingGeometry_management(aoi,minBoundary,"ENVELOPE","ALL")

        #jSONpolygon = [row[0] for row in arcpy.da.SearchCursor(minBoundary, ['SHAPE@JSON'])][0]

        # create coordinate string from minimum boundary polygon to send to SDA
        # first coordinate is also the last coordinate to close poly
        coorStr = ''
        with arcpy.da.SearchCursor(minBoundary,"SHAPE@XY",explode_to_points=True) as rows:
            for row in rows:
                coorStr = coorStr + (str(row[0][0]) + " " + str(row[0][1]) + ",")

        cIdx = coorStr.find(",")
        endPoint = coorStr[:cIdx]
        coorStr = coorStr + endPoint
        arcpy.Delete_management(minBoundary)

        if coorStr == '':
            AddMsgAndPrint("\nCould note create AOI minimum bounding coordinates",2)
            return False

        # Create empty feature class along with fields
        arcpy.management.CreateFeatureclass(os.path.dirname(outSSURGOlayerPath), outputName, "POLYGON", None, None, None, arcpy.env.outputCoordinateSystem )

        arcpy.management.AddField(outSSURGOlayerPath, "AREASYMBOL", "TEXT", "#","#","20",field_alias="Area Symbol")
        arcpy.management.AddField(outSSURGOlayerPath, "MUSYM", "TEXT", "#","#","6",field_alias="Mapunit Symbol")
        arcpy.management.AddField(outSSURGOlayerPath, "MUNAME", "TEXT", "#", "#", "175", field_alias="Mapunit Name")
        arcpy.management.AddField(outSSURGOlayerPath, "MUKEY", "TEXT", "#","#","30",field_alias="Mapunit Key")

        gQry = """
        ~DeclareGeometry(@aoi)~
        select @aoi = geometry::STPolyFromText('POLYGON (( """ + coorStr + """))', 4326)\n

        -- Extract all intersected polygons
        ~DeclareIdGeomTable(@intersectedPolygonGeometries)~
        ~GetClippedMapunits(@aoi,polygon,geo,@intersectedPolygonGeometries)~

        SELECT areasymbol, M.musym, M.muname, id AS mukey, geom
        FROM @intersectedPolygonGeometries
        INNER JOIN mapunit M ON id = M.mukey
        INNER JOIN legend L ON M.lkey = L.lkey"""

        # SDA url
        url = "https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest"

        AddMsgAndPrint('Sending coordinates to Soil Data Access')

        # Create request using JSON, return data as JSON
        request = {}
        request["format"] = "JSON"
        request["query"] = gQry

        #json.dumps = serialize obj (request dictionary) to a JSON formatted str
        data = json.dumps(request)

        # Send request to SDA Tabular service using urllib library
        # because we are passing the "data" argument, this is a POST request, not a GET

        # ArcMap Request
        #req = urllib.Request(url, data)
        #response = urllib.urlopen(req)

        # ArcPro Request
        data = data.encode('ascii')
        response = urllib.request.urlopen(url,data)

        # read query results
        qResults = response.read()

        # Convert the returned JSON string into a Python dictionary.
        qData = json.loads(qResults)

        # if dictionary key "Table" is found
        if "Table" in qData:

            # extract 'Data' List from dictionary to create list of lists
            # [u'455458',
            #  u'POLYGON ((-93.557235688 44.194375532084884, -93.5571424687631 44.1944048675063, -93.557235688 44.194519999876313, -93.557235688 44.194375532084884))']
            resLst = qData["Table"]

            # Create cursor to reconstruct incdividual polygons
            rows =  arcpy.da.InsertCursor(outSSURGOlayerPath, ["AREASYMBOL","MUSYM","MUNAME","MUKEY","SHAPE@WKT"])

            for rec in resLst:

                areasym = rec[0]
                musym = rec[1]
                muname = rec[2]
                mukey = rec[3]
                polygon = rec[4]

                value = areasym,musym,muname,mukey,polygon
                rows.insertRow(value)

            AddMsgAndPrint("\nSuccessfully Created SSURGO Layer from Soil Data Access")
            AddMsgAndPrint("Output location: " + str(outSSURGOlayerPath))
            return outSSURGOlayerPath

        else:
            AddMsgAndPrint("Failed to create geometry from SDA",2)
            return False

    except socket.timeout as e:
        AddMsgAndPrint('Soil Data Access timeout error',2)
        return False

    except socket.error as e:
        AddMsgAndPrint('Socket error: ' + str(e),2)
        return False

    except HTTPError as e:
        AddMsgAndPrint('HTTP Error' + str(e),2)
        return False

    except URLError as e:
        AddMsgAndPrint('URL Error' + str(e),2)
        return False

    except:
        errorMsg()
        return False

# ==============================================================================================================================
def compileSQLquery(ssurgoProperty,aggregationMethod,mukeyList):
    # Description:
    # This function will compile an SQL query ready to use in Soil Data Access (SDA).
    # There are query templates for the 5 different aggregation methods:
    #     1) Dominant Component (Category)
    #     2) Dominant Component (Numeric)
    #     3) Dominant Conidtion
    #     4) Weighted Average
    #     5) Minimum / Maximum

    # Parameters
    # ssurgoProperty - The name of the SSURGO Property to compile the SQL query for
    #                  i.e. Hydric Rating
    # aggregationMethod - 1 of the 5 aggregation methods listed above.  The aggregation
    #                     method used will depend on the ssurgoProperty.
    # mukeyList - Python list of MUKEYs.  These are the SSURGO MUKEYs that will be queried
    #             from SDA.

    # Returns
    # This function returns an SQL statement in ascii format.
    # This function will return False if the aggregation method passed in is invalid.

    # Example of SQL query created for Drainage Class
    """
    SELECT areasymbol, musym, muname, mu.mukey  AS mukey, drainagecl AS drainagecl
    FROM legend  AS l
    INNER JOIN  mapunit AS mu ON mu.lkey = l.lkey

    AND mu.mukey IN (398974,398965,398973,398959,398928,398962,398972,455427,455459,3111797,399456,579841,455426,455466,3111798,433237,433242,455428,455458,455451,455433,455439,399529,433240,455482,449401,455444,455450,623986)
    INNER JOIN component AS c ON c.mukey = mu.mukey

    AND c.cokey =
    (SELECT TOP 1 c1.cokey FROM component AS c1
    INNER JOIN mapunit ON c.mukey=mapunit.mukey AND c1.mukey=mu.mukey ORDER BY c1.comppct_r DESC, c1.cokey)
    """

    try:
        # convert list of mukeys to a string of mukeys to pass to SDA
        keys = ",".join(mukeyList)

        ssurgoFld = lookupSSURGOFieldName(ssurgoProperty).strip()

        if aggregationMethod == "Dominant Component (Category)":

            pQry = "SELECT areasymbol, musym, muname, mu.mukey  AS mukey, " + ssurgoFld + " AS " + ssurgoFld + "\n"\
            " FROM legend  AS l\n"\
            " INNER JOIN  mapunit AS mu ON mu.lkey = l.lkey\n\n"\
            " AND mu.mukey IN (" + keys + ")\n"\
            " INNER JOIN component AS c ON c.mukey = mu.mukey\n\n"\
            " AND c.cokey =\n"\
            " (SELECT TOP 1 c1.cokey FROM component AS c1\n"\
            " INNER JOIN mapunit ON c.mukey=mapunit.mukey AND c1.mukey=mu.mukey ORDER BY c1.comppct_r DESC, c1.cokey)"

        elif aggregationMethod == "Dominant Component (Numeric)":
            pQry = "SELECT areasymbol, musym, muname, mukey\n"\
            " INTO #kitchensink\n"\
            " FROM legend  AS lks\n"\
            " INNER JOIN  mapunit AS muks ON muks.lkey = lks.lkey AND muks.mukey IN (" + keys + ")\n"\
            " SELECT mu1.mukey, cokey, comppct_r,\n"\
            " SUM (comppct_r) over(partition by mu1.mukey ) AS SUM_COMP_PCT\n"\
            " INTO #comp_temp\n"\
            " FROM legend  AS l1\n"\
            " INNER JOIN  mapunit AS mu1 ON mu1.lkey = l1.lkey AND mu1.mukey IN (" + keys + ")\n"\
            " INNER JOIN  component AS c1 ON c1.mukey = mu1.mukey AND majcompflag = 'Yes'\n"\
            " AND c1.cokey =\n"\
            " (SELECT TOP 1 c2.cokey FROM component AS c2\n"\
            " INNER JOIN mapunit AS mm1 ON c2.mukey=mm1.mukey AND c2.mukey=mu1.mukey ORDER BY c2.comppct_r DESC, c2.cokey)\n"\
            " SELECT cokey, SUM_COMP_PCT, CASE WHEN comppct_r = SUM_COMP_PCT THEN 1\n"\
            " ELSE CAST (CAST (comppct_r AS  decimal (5,2)) / CAST (SUM_COMP_PCT AS decimal (5,2)) AS decimal (5,2)) END AS WEIGHTED_COMP_PCT\n"\
            " INTO #comp_temp3\n"\
            " FROM #comp_temp\n"\
            " SELECT areasymbol, musym, muname, mu.mukey/1  AS MUKEY, c.cokey AS COKEY, ch.chkey/1 AS CHKEY, compname, hzname, hzdept_r, hzdepb_r, CASE WHEN hzdept_r < " + tDep + " THEN " + tDep + " ELSE hzdept_r END AS hzdept_r_ADJ,"\
            " CASE WHEN hzdepb_r > " + bDep + "  THEN " + bDep + " ELSE hzdepb_r END AS hzdepb_r_ADJ,\n"\
            " CAST (CASE WHEN hzdepb_r > " + bDep + "  THEN " + bDep + " ELSE hzdepb_r END - CASE WHEN hzdept_r <" + tDep + " THEN " + tDep + " ELSE hzdept_r END AS decimal (5,2)) AS thickness,\n"\
            " comppct_r,\n"\
            " CAST (SUM (CASE WHEN hzdepb_r > " + bDep + "  THEN " + bDep + " ELSE hzdepb_r END - CASE WHEN hzdept_r <" + tDep + " THEN " + tDep + " ELSE hzdept_r END) over(partition by c.cokey) AS decimal (5,2)) AS sum_thickness,\n"\
            " CAST (ISNULL (" + ssurgoFld + " , 0) AS decimal (5,2))AS " + ssurgoFld + " \n"\
            " INTO #main\n"\
            " FROM legend  AS l\n"\
            " INNER JOIN  mapunit AS mu ON mu.lkey = l.lkey AND mu.mukey IN (" + keys + ")\n"\
            " INNER JOIN  component AS c ON c.mukey = mu.mukey\n"\
            " INNER JOIN chorizon AS ch ON ch.cokey=c.cokey AND hzname NOT LIKE '%O%'AND hzname NOT LIKE '%r%'\n"\
            " AND hzdepb_r >" + tDep + " AND hzdept_r <" + bDep + "\n"\
            " INNER JOIN chtexturegrp AS cht ON ch.chkey=cht.chkey  WHERE cht.rvindicator = 'yes' AND  ch.hzdept_r IS NOT NULL\n"\
            " AND\n"\
            " texture NOT LIKE '%PM%' and texture NOT LIKE '%DOM' and texture NOT LIKE '%MPT%' and texture NOT LIKE '%MUCK' and texture NOT LIKE '%PEAT%' and texture NOT LIKE '%br%' and texture NOT LIKE '%wb%'\n"\
            " ORDER BY areasymbol, musym, muname, mu.mukey, comppct_r DESC, cokey,  hzdept_r, hzdepb_r\n"\
            " SELECT #main.areasymbol, #main.musym, #main.muname, #main.MUKEY,\n"\
            " #main.COKEY, #main.CHKEY, #main.compname, hzname, hzdept_r, hzdepb_r, hzdept_r_ADJ, hzdepb_r_ADJ, thickness, sum_thickness, " + ssurgoFld + " , comppct_r, SUM_COMP_PCT, WEIGHTED_COMP_PCT ,\n"\
            " SUM((thickness/sum_thickness ) * " + ssurgoFld + "  )over(partition by #main.COKEY)AS COMP_WEIGHTED_AVERAGE\n"\
            " INTO #comp_temp2\n"\
            " FROM #main\n"\
            " INNER JOIN #comp_temp3 ON #comp_temp3.cokey=#main.cokey\n"\
            " ORDER BY #main.areasymbol, #main.musym, #main.muname, #main.MUKEY, comppct_r DESC,  #main.COKEY,  hzdept_r, hzdepb_r\n"\
            " SELECT #comp_temp2.MUKEY,#comp_temp2.COKEY, WEIGHTED_COMP_PCT * COMP_WEIGHTED_AVERAGE AS COMP_WEIGHTED_AVERAGE1\n"\
            " INTO #last_step\n"\
            " FROM #comp_temp2\n"\
            " GROUP BY  #comp_temp2.MUKEY,#comp_temp2.COKEY, WEIGHTED_COMP_PCT, COMP_WEIGHTED_AVERAGE\n"\
            " SELECT areasymbol, musym, muname,\n"\
            " #kitchensink.mukey, #last_step.COKEY,\n"\
            " CAST (SUM (COMP_WEIGHTED_AVERAGE1) over(partition by #kitchensink.mukey) as decimal(5,2))AS " + ssurgoFld + "\n"\
            " INTO #last_step2\n"\
            " FROM #last_step\n"\
            " RIGHT OUTER JOIN #kitchensink ON #kitchensink.mukey=#last_step.mukey\n"\
            " GROUP BY #kitchensink.areasymbol, #kitchensink.musym, #kitchensink.muname, #kitchensink.mukey, COMP_WEIGHTED_AVERAGE1, #last_step.COKEY\n"\
            " ORDER BY #kitchensink.areasymbol, #kitchensink.musym, #kitchensink.muname, #kitchensink.mukey\n"\
            " SELECT #last_step2.areasymbol, #last_step2.musym, #last_step2.muname,\n"\
            " #last_step2.mukey, #last_step2." + ssurgoFld + "\n"\
            " FROM #last_step2\n"\
            " LEFT OUTER JOIN #last_step ON #last_step.mukey=#last_step2.mukey\n"\
            " GROUP BY #last_step2.areasymbol, #last_step2.musym, #last_step2.muname, #last_step2.mukey, #last_step2." + ssurgoFld + "\n"\
            " ORDER BY #last_step2.areasymbol, #last_step2.musym, #last_step2.muname, #last_step2.mukey, #last_step2." + ssurgoFld

        elif aggregationMethod == "Dominant Condition":
            pQry = "SELECT areasymbol, musym, muname, mu.mukey/1  AS mukey,\n"\
            " (SELECT TOP 1 " + ssurgoFld + "\n"\
            " FROM mapunit\n"\
            " INNER JOIN component ON component.mukey=mapunit.mukey\n"\
            " AND mapunit.mukey = mu.mukey\n"\
            " GROUP BY " + ssurgoFld + ", comppct_r ORDER BY SUM(comppct_r) over(partition by " + ssurgoFld + ") DESC) AS " + ssurgoFld + "\n"\
            " FROM legend  AS l\n"\
            " INNER JOIN  mapunit AS mu ON mu.lkey = l.lkey AND  mu.mukey IN (" + keys + ")\n"\
            " INNER JOIN  component AS c ON c.mukey = mu.mukey\n"\
            " AND c.cokey =\n"\
            " (SELECT TOP 1 c1.cokey FROM component AS c1\n"\
            " INNER JOIN mapunit ON c.mukey=mapunit.mukey AND c1.mukey=mu.mukey ORDER BY c1.comppct_r DESC, c1.cokey)\n"\
            " GROUP BY areasymbol, musym, muname, mu.mukey, c.cokey,  compname, comppct_r\n"\
            " ORDER BY areasymbol, musym, muname, mu.mukey, comppct_r DESC, c.cokey\n"\

        elif aggregationMethod == "Weighted Average":
            pQry = "SELECT areasymbol, musym, muname, mukey\n"\
            " INTO #kitchensink\n"\
            " FROM legend  AS lks\n"\
            " INNER JOIN  mapunit AS muks ON muks.lkey = lks.lkey AND muks.mukey IN (" + keys + ")\n"\
            " SELECT mu1.mukey, cokey, comppct_r,"\
            " SUM (comppct_r) over(partition by mu1.mukey ) AS SUM_COMP_PCT\n"\
            " INTO #comp_temp\n"\
            " FROM legend  AS l1\n"\
            " INNER JOIN  mapunit AS mu1 ON mu1.lkey = l1.lkey AND mu1.mukey IN (" + keys + ")\n"\
            " INNER JOIN  component AS c1 ON c1.mukey = mu1.mukey AND majcompflag = 'Yes'\n"\
            " SELECT cokey, SUM_COMP_PCT, CASE WHEN comppct_r = SUM_COMP_PCT THEN 1\n"\
            " ELSE CAST (CAST (comppct_r AS  decimal (5,2)) / CAST (SUM_COMP_PCT AS decimal (5,2)) AS decimal (5,2)) END AS WEIGHTED_COMP_PCT\n"\
            " INTO #comp_temp3\n"\
            " FROM #comp_temp\n"\
            " SELECT\n"\
            " areasymbol, musym, muname, mu.mukey/1  AS MUKEY, c.cokey AS COKEY, ch.chkey/1 AS CHKEY, compname, hzname, hzdept_r, hzdepb_r, CASE WHEN hzdept_r <" + tDep + "  THEN " + tDep + " ELSE hzdept_r END AS hzdept_r_ADJ,\n"\
            " CASE WHEN hzdepb_r > " + bDep + "  THEN " + bDep + " ELSE hzdepb_r END AS hzdepb_r_ADJ,\n"\
            " CAST (CASE WHEN hzdepb_r > " +bDep + "  THEN " +bDep + " ELSE hzdepb_r END - CASE WHEN hzdept_r <" + tDep + " THEN " + tDep + " ELSE hzdept_r END AS decimal (5,2)) AS thickness,\n"\
            " comppct_r,\n"\
            " CAST (SUM (CASE WHEN hzdepb_r > " + bDep + "  THEN " + bDep + " ELSE hzdepb_r END - CASE WHEN hzdept_r <" + tDep + " THEN " + tDep + " ELSE hzdept_r END) over(partition by c.cokey) AS decimal (5,2)) AS sum_thickness,\n"\
            " CAST (ISNULL (" + ssurgoFld + ", 0) AS decimal (5,2))AS " + ssurgoFld +\
            " INTO #main"\
            " FROM legend  AS l\n"\
            " INNER JOIN  mapunit AS mu ON mu.lkey = l.lkey AND mu.mukey IN (" + keys + ")\n"\
            " INNER JOIN  component AS c ON c.mukey = mu.mukey\n"\
            " INNER JOIN chorizon AS ch ON ch.cokey=c.cokey AND hzname NOT LIKE '%O%'AND hzname NOT LIKE '%r%'\n"\
            " AND hzdepb_r >" + tDep + " AND hzdept_r <" + bDep + ""\
            " INNER JOIN chtexturegrp AS cht ON ch.chkey=cht.chkey  WHERE cht.rvindicator = 'yes' AND  ch.hzdept_r IS NOT NULL\n"\
            " AND texture NOT LIKE '%PM%' and texture NOT LIKE '%DOM' and texture NOT LIKE '%MPT%' and texture NOT LIKE '%MUCK' and texture NOT LIKE '%PEAT%' and texture NOT LIKE '%br%' and texture NOT LIKE '%wb%'\n"\
            " ORDER BY areasymbol, musym, muname, mu.mukey, comppct_r DESC, cokey,  hzdept_r, hzdepb_r\n"\
            " SELECT #main.areasymbol, #main.musym, #main.muname, #main.MUKEY,\n"\
            " #main.COKEY, #main.CHKEY, #main.compname, hzname, hzdept_r, hzdepb_r, hzdept_r_ADJ, hzdepb_r_ADJ, thickness, sum_thickness, " + ssurgoFld + ", comppct_r, SUM_COMP_PCT, WEIGHTED_COMP_PCT ,\n"\
            " SUM((thickness/sum_thickness ) * " + ssurgoFld + " )over(partition by #main.COKEY)AS COMP_WEIGHTED_AVERAGE\n"\
            " INTO #comp_temp2\n"\
            " FROM #main\n"\
            " INNER JOIN #comp_temp3 ON #comp_temp3.cokey=#main.cokey\n"\
            " ORDER BY #main.areasymbol, #main.musym, #main.muname, #main.MUKEY, comppct_r DESC,  #main.COKEY,  hzdept_r, hzdepb_r\n"\
            " SELECT #comp_temp2.MUKEY,#comp_temp2.COKEY, WEIGHTED_COMP_PCT * COMP_WEIGHTED_AVERAGE AS COMP_WEIGHTED_AVERAGE1\n"\
            " INTO #last_step\n"\
            " FROM #comp_temp2\n"\
            " GROUP BY  #comp_temp2.MUKEY,#comp_temp2.COKEY, WEIGHTED_COMP_PCT, COMP_WEIGHTED_AVERAGE\n"\
            " SELECT areasymbol, musym, muname,\n"\
            " #kitchensink.mukey, #last_step.COKEY,\n"\
            " CAST (SUM (COMP_WEIGHTED_AVERAGE1) over(partition by #kitchensink.mukey) as decimal(5,2))AS " + ssurgoFld + "\n"\
            " INTO #last_step2"\
            " FROM #last_step\n"\
            " RIGHT OUTER JOIN #kitchensink ON #kitchensink.mukey=#last_step.mukey\n"\
            " GROUP BY #kitchensink.areasymbol, #kitchensink.musym, #kitchensink.muname, #kitchensink.mukey, COMP_WEIGHTED_AVERAGE1, #last_step.COKEY\n"\
            " ORDER BY #kitchensink.areasymbol, #kitchensink.musym, #kitchensink.muname, #kitchensink.mukey\n"\
            " SELECT #last_step2.areasymbol, #last_step2.musym, #last_step2.muname,\n"\
            " #last_step2.mukey, #last_step2." + ssurgoFld + "\n"\
            " FROM #last_step2\n"\
            " LEFT OUTER JOIN #last_step ON #last_step.mukey=#last_step2.mukey\n"\
            " GROUP BY #last_step2.areasymbol, #last_step2.musym, #last_step2.muname, #last_step2.mukey, #last_step2." + ssurgoFld + "\n"\
            " ORDER BY #last_step2.areasymbol, #last_step2.musym, #last_step2.muname, #last_step2.mukey, #last_step2."+ ssurgoFld

        elif aggregationMethod == "Min\Max":
            pQry = "SELECT areasymbol, musym, muname, mu.mukey  AS mukey,\n"\
            " (SELECT TOP 1 " + mmC + " (chm1." + ssurgoFld + ") FROM  component AS cm1\n"\
            " INNER JOIN chorizon AS chm1 ON cm1.cokey = chm1.cokey AND cm1.cokey = c.cokey\n"\
            " AND CASE WHEN chm1.hzname LIKE  '%O%' AND hzdept_r <10 THEN 2\n"\
            " WHEN chm1.hzname LIKE  '%r%' THEN 2\n"\
            " WHEN chm1.hzname LIKE  '%'  THEN  1 ELSE 1 END = 1\n"\
            " ) AS " + ssurgoFld + "\n"+\
            " FROM legend  AS l\n"\
            " INNER JOIN  mapunit AS mu ON mu.lkey = l.lkey AND mu.mukey IN (" + keys + ")\n"\
            " INNER JOIN  component AS c ON c.mukey = mu.mukey  AND c.cokey =\n"\
            " (SELECT TOP 1 c1.cokey FROM component AS c1\n"\
            " INNER JOIN mapunit ON c.mukey=mapunit.mukey AND c1.mukey=mu.mukey ORDER BY c1.comppct_r DESC, c1.cokey)\n"

        else:
            AddMsgAndPrint(aggregationMethod + " aggregation method is Invalid.  Could not compile query",2)
            return False

        return pQry

    except:
        errorMsg()
        return False

# ==============================================================================================================================
def lookupSSURGOFieldName(ssurgoProperty,returnAlias=False):
    # Description
    # This function references a python dictionary to either return a SSURGO Properties
    # and Interpretations Key or SSURGO field name value.

    # Parameters:
    # ssurgoProperty - The expanded name of the SSURGO property.
    # returnAlias - This is an optional parameter set to False by default.
    #               If set to True then the dictionary value (field name) will
    #               be returned instead of the dictiary key (expanded SSURGO property)

    # Returns
    # This function returns the name of the SSURGO field associated with the SSURGO
    # property or interpretation if the parameter returnAlias is set to False.
    # i.e if the property/interp of interest is 'Drainage Class' then return 'drainagecl'
    # if returnAlias is set to True then return the dictionary key (exapnded name)
    # This can be used to populate field alias names.

    try:

        propDict = {'0.1 bar H2O - Rep Value': 'wtenthbar_r',
                    '0.33 bar H2O - Rep Value': 'wthirdbar_r',
                    '15 bar H2O - Rep Value': 'wfifteenbar_r',
                    'Available Water Capacity - Rep Value': 'awc_r',
                    'Bray 1 Phosphate - Rep Value': 'pbray1_r',
                    'Bulk Density 0.1 bar H2O - Rep Value': 'dbtenthbar_r',
                    'Bulk Density 0.33 bar H2O - Rep Value': 'dbthirdbar_r',
                    'Bulk Density 15 bar H2O - Rep Value': 'dbfifteenbar_r',
                    'Bulk Density oven dry - Rep Value': 'dbovendry_r',
                    'CaCO3 Clay - Rep Value': 'claysizedcarb_r',
                    'Calcium Carbonate - Rep Value': 'caco3_r',
                    'Cation Exchange Capcity - Rep Value': 'cec7_r',
                    'Coarse Sand - Rep Value': 'sandco_r',
                    'Coarse Silt - Rep Value': 'siltco_r',
                    'Corrosion of Concrete': 'corcon',
                    'Corrosion of Steel': 'corsteel',
                    'Hydric Condition':'hydricon',
                    'Hydric Rating':'hydricrating',
                    'Drainage Class': 'drainagecl',
                    'Effective Cation Exchange Capcity - Rep Value': 'ecec_r',
                    'Electrial Conductivity 1:5 by volume - Rep Value': 'ec15_r',
                    'Electrical Conductivity - Rep Value': 'ec_r',
                    'Exchangeable Sodium Percentage - Rep Value': 'esp_r',
                    'Extract Aluminum - Rep Value': 'extral_r',
                    'Extractable Acidity - Rep Value': 'extracid_r',
                    'Fine Sand - Rep Value': 'sandfine_r',
                    'Fine Silt - Rep Value': 'siltfine_r',
                    'Free Iron - Rep Value': 'freeiron_r',
                    'Gypsum - Rep Value': 'gypsum_r',
                    'Hydrologic Group': 'hydgrp',
                    'Kf': 'kffact',
                    'Ki ': 'kifact',
                    'Kr ': 'krfact',
                    'Kw ': 'kwfact',
                    'LEP - Rep Value': 'lep_r',
                    'Liquid Limit - Rep Value': 'll_r',
                    'Medium Sand - Rep Value': 'sandmed_r',
                    'Organic Matter - Rep Value': 'om_r',
                    'Oxalate Aluminum - Rep Value': 'aloxalate_r',
                    'Oxalate Iron - Rep Value': 'feoxalate_r',
                    'Oxalate Phosphate - Rep Value': 'poxalate_r',
                    'Plasticity Index - Rep Value': 'pi_r',
                    'Rock Fragments 3 - 10 cm - Rep Value': 'frag3to10_r',
                    'Rock Fragments > 10 cm - Rep Value': 'fraggt10_r',
                    'Rubbed Fiber % - Rep Value': 'fiberrubbedpct_r',
                    'Satiated H2O - Rep Value': 'wsatiated_r',
                    'Saturated Hydraulic Conductivity - Rep Value': 'ksat_r',
                    'Sodium Adsorption Ratio - Rep Value': 'sar_r',
                    'Sum of Bases - Rep Value': 'sumbases_r',
                    'Taxonomic Class Name': 'taxclname',
                    'Taxonomic Order': 'taxorder',
                    'Taxonomic Suborder': 'taxsuborder',
                    'Taxonomic Temperature Regime': 'taxtempregime',
                    'Total Clay - Rep Value': 'claytotal_r',
                    'Total Phosphate - Rep Value': 'ptotal_r',
                    'Total Rock Fragment Volume - Rep Value': 'fragvoltot_r',
                    'Total Sand - Rep Value': 'sandtotal_r',
                    'Total Silt - Rep Value': 'silttotal_r',
                    'Unrubbed Fiber % - Rep Value': 'fiberunrubbedpct_r',
                    'Very Coarse Sand - Rep Value': 'sandvc_r',
                    'Very Fine Sand - Rep Value': 'sandvf_r',
                    'Water Soluble Phosphate - Rep Value': 'ph2osoluble_r',
                    'Wind Erodibility Group': 'weg',
                    'Wind Erodibility Index': 'wei',
                    'no. 10 sieve - Rep Value': 'sieveno10_r',
                    'no. 200 sieve - Rep Value': 'sieveno200_r',
                    'no. 4 sieve - Rep Value': 'sieveno4_r',
                    'no. 40 sieve - Rep Value': 'sieveno40_r',
                    'pH .01M CaCl2 - Rep Value': 'ph01mcacl2_r',
                    'pH 1:1 water - Rep Value': 'ph1to1h2o_r',
                    'pH Oxidized - Rep Value': 'phoxidized_r',
                    't Factor': 'tfact'}

        # Return Dictionary Key (Exapnded SSURGO Property Name)
        if not returnAlias:
            ssurgoField = propDict.get(ssurgoProperty)

            if ssurgoField == "":
                return False
            else:
                return ssurgoField

        # Return Dictionary Value (SSURGO Field name)
        else:
            aliasName = ""
            for alias,fldName in propDict.items():
                if fldName == ssurgoProperty:
                    return alias

            if aliasName == "":
                return False

    except:
        errorMsg()

# ==============================================================================================================================
def addSSURGOpropertyFld(layer, fldNames, fldInfo):

    try:
        # Dictionary: SQL Server to FGDB
        dType = dict()

        dType["int"] = "long"
        dType["smallint"] = "short"
        dType["bit"] = "short"
        dType["varbinary"] = "blob"
        dType["nvarchar"] = "text"
        dType["varchar"] = "text"
        dType["char"] = "text"
        dType["datetime"] = "date"
        dType["datetime2"] = "date"
        dType["smalldatetime"] = "date"
        dType["decimal"] = "double"
        dType["numeric"] = "double"
        dType["float"] = "double"
        dType["real"] = "double"  # 8 bytes

        # Iterate through list of field names and add them to the output table
        i = 0

        # ColumnInfo contains:
        # ColumnOrdinal, ColumnSize, NumericPrecision, NumericScale, ProviderType, IsLong, ProviderSpecificDataType, DataTypeName
        # AddMsgAndPrint(" \nFieldName, Length, Precision, Scale, Type", 1)

        if arcpy.Exists(layer):

            layerFlds = [f.name.lower() for f in arcpy.ListFields(layer,"*")]

            for i, fldName in enumerate(fldNames):

                if fldName.lower() in layerFlds:
                    continue

                vals = fldInfo[i].split(",")
                length = int(vals[1].split("=")[1])
                precision = int(vals[2].split("=")[1])
                scale = int(vals[3].split("=")[1])
                dataType = dType[vals[4].lower().split("=")[1]]

                if fldName.lower().endswith("key"):
                    # Per SSURGO standards, key fields should be string. They come from Soil Data Access as long integer.
                    dataType = 'text'
                    length = 30

                arcpy.AddField_management(layer, fldName, dataType, precision, scale, length)

        else:
            AddMsgAndPrint("\n" + str(layer) + " Does Not Exist.  Could not add fields",2)
            return False

        return True

    except:
        errorMsg()
        return False

# ==============================================================================================================================
def getSDATabularRequest(sqlQuery,layerPath):
    # Description
    # This function sends an SQL query to Soil Data Access and appends the results to a
    # layer.

    # Parameters
    # sqlQuery - A valid SDA SQL statement in ascii format
    # layerPath - Directory path to an existing spatial layer or table where the SDA results
    #             will be appended to.  The field names returned in the metadata portion
    #             of the JSON request will automatically be added to the layer

    # Returns
    # This function returns True if SDA results were successfully appended to the input
    # layer.  False otherwise.
    # Return Flase if an HTTP Error occurred such as a bad query, server timeout or no
    # response from server

    try:

        #uncomment next line to print interp query to console
        #arcpy.AddMessage(pQry.replace("&gt;", ">").replace("&lt;", "<"))

        # SDA url
        url = r'https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest'

        # Create request using JSON, return data as JSON
        request = {}
        request["format"] = "JSON+COLUMNNAME+METADATA"
        request["query"] = sqlQuery

        #json.dumps = serialize obj (request dictionary) to a JSON formatted str
        data = json.dumps(request)

        # Send request to SDA Tabular service using urllib library
        # because we are passing the "data" argument, this is a POST request, not a GET

        # ArcMap Request
        #req = urllib.Request(url, data)
        #response = urllib.urlopen(req)

        # ArcPro Request
        data = data.encode('ascii')
        response = urllib.request.urlopen(url,data)

        # read query results
        queryResults = response.read()

        # Convert the returned JSON string into a Python dictionary.
        qData = json.loads(queryResults)

        # if dictionary key "Table" is found
        if "Table" in qData:

            # extract 'Data' List from dictionary to create list of lists
            propertyData = qData["Table"]

##            # remove the column names and column info lists from propRes list above
##            # Last element represents info for specific property
##            # [u'areasymbol', u'musym', u'muname', u'mukey', u'drainagecl']
##            # [u'ColumnOrdinal=0,ColumnSize=20,NumericPrecision=255,NumericScale=255,ProviderType=VarChar,IsLong=False,ProviderSpecificDataType=System.Data.SqlTypes.SqlString,DataTypeName=varchar',
##            columnNames = list()   # ['drainagecl']
##            columnInfo = list()
##            columnNames.append(propRes.pop(0)[-1])
##            columnInfo.append(propRes.pop(0)[-1])

            columnNames = propertyData.pop(0)       # Isolate column names and remove from propertyData
            columnInfo = propertyData.pop(0)        # Isolate column info and remove from propertyData
            mukeyIndex = columnNames.index('mukey') # list index of where 'mukey' is found
            propertyIndex = len(columnNames) -1     # list index of where property of interest is found; normally last place
            propertyFldName = columnNames[propertyIndex] # SSURGO field name of the property of interest

            # Add fields in columnNames to layerPath
            if not addSSURGOpropertyFld(layerPath, columnNames, columnInfo):
                return False

            # Get the expanded SSURGO field name of the property of interest
            fieldAlias = lookupSSURGOFieldName(propertyFldName,returnAlias=True)

            # Update the field alias if possible
            if fieldAlias:
                arcpy.AlterField_management(layerPath,propertyFldName,"#",fieldAlias)

            # rearrange propertyData list into a dictionary of lists with the
            # mukey as key and tabular info as a list of values.  This will be used
            # in the UpdateCursor to lookup tabular info by MUKEY
            # '455428': [u'MN161','L110E','Lester-Ridgeton complex, 18 to 25 percent slopes','B']
            propertyDict = dict()

            for item in propertyData:
                propertyDict[item[mukeyIndex]] = item

            # columnNames = [u'areasymbol', u'musym', u'muname', u'mukey', u'drainagecl']
            with arcpy.da.UpdateCursor(layerPath, columnNames) as cursor:
                for row in cursor:
                    mukey = row[mukeyIndex]

                    # lookup property info by MUKEY; Only update the property of interest
                    # No need to keep updating fields such as areasymbol, musym....etc
                    propertyVal = propertyDict[mukey][propertyIndex]
                    row[propertyIndex] = propertyVal

                    cursor.updateRow(row)

            return True

        else:
            AddMsgAndPrint("Failed to get tabular data (getSDATabularRequest)",2)
            return False

    except socket.timeout as e:
        AddMsgAndPrint('Soil Data Access timeout error',2)
        return False

    except socket.error as e:
        AddMsgAndPrint('Socket error: ' + str(e),2)
        return False

    except HTTPError as e:
        AddMsgAndPrint('HTTP Error' + str(e),2)
        return False

    except URLError as e:
        AddMsgAndPrint('URL Error' + str(e),2)
        return False

    except:
        errorMsg()
        return False

# ==============================================================================================================================
def AddSSURGOLayersToArcGISPro(ssurgoFC,listOfProperties):
    # propertyList = ['Drainage Class - Dominant Condition',
    #                 'Hydric Condition - Dominant Condition',
    #                 'Hydric Rating - Dominant Condition',
    #                 'Hydrologic Group - Dominant Condition']

    # ------------------------------------------------------------------
    def UpdateLyrxSymbology(lyrxObj):

        sym = lyrxObj.symbology

        if sym.renderer.type == 'UniqueValueRenderer':
            sym.updateRenderer('UniqueValueRenderer')

            # This is the field used to render the symbology i.e. [hydgrp]
            rendererFld = sym.renderer.fields

            # These are the values found in the FC being symbolized
            uniqueValues = list(set([row[0] for row in arcpy.da.SearchCursor(ssurgoFC,rendererFld)]))

            # Get a list of unique Values in the symbology renderer
            uniqueRendererValues = list()
            for grp in sym.renderer.groups:
                for itm in grp.items:
                    uniqueRendererValues.append(itm.values[0][0])

            # remove symbology values that are not present in the FC
            for val in uniqueValues:
                if val in uniqueRendererValues:
                    uniqueRendererValues.remove(val)

            if len(uniqueRendererValues) > 0:
                for val in uniqueRendererValues:
                    sym.renderer.removeValues({rendererFld[0]: [val]})
                    lyrxObj.symbology = sym
    # ------------------------------------------------------------------

    try:
        # path to individual .lyrx files
        scriptPath = os.path.dirname(__file__)

        # isolate the property names (remove aggregation method)
        propertyNames = [property.split('-')[0] for property in listOfProperties]
        lyrxToAddToArcPro = []

        # Update the connection properties for the .lyrx files that will be added to ArcGIS Pro
        for property in listOfProperties:

            # 'Drainage Class - Dominant Condition'
            propSplit = property.split('-')                   # ['Drainage Class ', ' Dominant Condition']
            propName = propSplit[0].strip().replace(" ","")   # DrainageClass
            aggMethod = propSplit[1].strip().replace(" ","")  # DominantCondition

            lyrxPath = os.path.join(scriptPath,"SSURGO_WCT_" + propName + "_" + aggMethod + ".lyrx")

            if arcpy.Exists(lyrxPath):
                lyrxObject = arcpy.mp.LayerFile(lyrxPath).listLayers()[0]  # create a layer object

                # Connection Property Dictionary
                # {'dataset': 'SSURGO_WCT',
                #  'workspace_factory': 'File Geodatabase',
                #  'connection_info': {'database': 'E:\\python_scripts\\GitHub\\SSURGO_WCT\\Wetland_Workspace.gdb'}}
                lyrxConnectProperties = lyrxObject.connectionProperties

                # update CP dictionary database and dataset keys
                lyrxConnectProperties['connection_info']['database'] = os.path.dirname(ssurgoFC)
                lyrxConnectProperties['dataset'] = os.path.basename(ssurgoFC)
                lyrxObject.updateConnectionProperties(lyrxObject.connectionProperties,lyrxConnectProperties)
                lyrxToAddToArcPro.append(lyrxObject)

            else:
                AddMsgAndPrint(property + " is missing .lyrx file",1)

        aprx = arcpy.mp.ArcGISProject("CURRENT")

        # 'SSURGO Layers' group layer object
        groupLayerPath = os.path.join(scriptPath,r'SSURGO_WCT_EmptySSURGOGroupLayer.lyrx')
        groupLayerObject = arcpy.mp.LayerFile(groupLayerPath).listLayers()[0]
        groupLayerName = groupLayerObject.name  # 'SSURGO Layers'

        # Boolean to determine if 'SSURGO Layers' group exists in ArcGIS Pro Session
        bGroupLayerExists = False
        bAddedLyrxFilesToPro = False

        # This is the map object where the lyrx files were added to
        mapObject = ""

        # G
        for map in aprx.listMaps():
            for mapLyr in map.listLayers():

                # 'SSURGO Layers' group exists in Pro Session
                # Add the layers in lyrxToAddToArcPro list to ArcPro
                if mapLyr.name == groupLayerName and mapLyr.isGroupLayer:
                    bGroupLayerExists = True
                    mapObject = map

                    for lyrx in lyrxToAddToArcPro:
                        map.addLayerToGroup(mapLyr,lyrx)
                        bAddedLyrxFilesToPro = True
                        AddMsgAndPrint("Adding Layer to ArcGIS Pro: " + lyrx.name)
            break

        # Get existing group layer object
        if not bGroupLayerExists:

            # Add group layer to ArcGIS Pro Session
            aprxMap = aprx.activeMap
            mapObject = aprxMap
            aprxMap.addLayer(groupLayerObject, 'TOP')

            # Get added group layer
            mapGroupLayer = [lyr for lyr in aprxMap.listLayers(groupLayerName)][0]

            # 'SSURGO Layers' group exists in Pro Session
            # Add the layers in lyrxToAddToArcPro list to ArcPro
            for lyrx in lyrxToAddToArcPro:
                map.addLayerToGroup(mapGroupLayer,lyrx)
                bAddedLyrxFilesToPro = True
                AddMsgAndPrint("Adding Layer to ArcGIS Pro: " + lyrx.name)

        # Update symbology
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        for lyr in mapObject.listLayers():

            # This is the 'SSURGO Layers' Group
            # iterate through the nested layers and up
            # the symbology
            if lyr.name == groupLayerName and lyr.isGroupLayer:
                for newLayer in lyr.listLayers():
                    UpdateLyrxSymbology(newLayer)

    except:
        errorMsg()
        AddMsgAndPrint("Couldn't Add Layers to your ArcGIS Pro Session",1)
        pass

# ==============================================================================================================================
def start(aoi,soilPropertyList,outputWS):

    # propertyList = ['Drainage Class - Dominant Condition',
    #                 'Hydric Condition - Dominant Condition',
    #                 'Hydric Rating - Dominant Condition',
    #                 'Hydrologic Group - Dominant Condition']

    try:

        # get SSURGO polgyons from SDA
        outSSURGOlayer = getSSURGOgeometryFromSDA(aoi, outputWS, "SSURGO_WCT")

        listOfMukeys = [row[0] for row in arcpy.da.SearchCursor(outSSURGOlayer,["MUKEY"])]

        if listOfMukeys:

            for property in soilPropertyList:

                propSplit = property.split('-')
                property = propSplit[0].strip()
                aggMethod = propSplit[1].strip()

                theQuery = compileSQLquery(property,aggMethod,listOfMukeys)
                tbRequest = getSDATabularRequest(theQuery,outSSURGOlayer)

        else:
            arcpy.AddError('Fatal.\n' + listOfMukeys)

        AddSSURGOLayersToArcGISPro(outSSURGOlayer,soilPropertyList)

        return outSSURGOlayer

    except:
        errorMsg()

# ====================================== Main Body ==================================
import sys, os, time, urllib, json, traceback, socket
import arcgisscripting, arcpy

from urllib.error import HTTPError, URLError

if __name__ == '__main__':

    try:
        feature = arcpy.GetParameterAsText(0) #
        propertyList = arcpy.GetParameter(1)  # python List of SSURGO Properties
        outLoc = arcpy.GetParameterAsText(2)  # Must be a FGDB

##        featSet = r'E:\python_scripts\GitHub\SSURGO_WCT\Wetland_Workspace.gdb\CLU_example2'
##        aggMethod = 'Dominant Component (Category)'
##        propParam = ['Drainage Class','Hydric Rating','Hydrologic Group']
##        #aggMethod = 'Dominant Condition'
##        #propParam = ['Hydric Condition']

        outputLayer = start(feature,propertyList,outLoc)
        AddMsgAndPrint(outputLayer)


    except:
        errorMsg()
