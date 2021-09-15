#-------------------------------------------------------------------------------
# Name:        getSSURGO_WCT.py
# Purpose:     Develop SSURGO layers to be referenced within the Wetland
#              Compliance process.

# Author: Adolfo.Diaz anthony :)
#         GIS Specialist
#         National Soil Survey Center
#         USDA - NRCS
# e-mail: adolfo.diaz@usda.gov
# phone: 608.662.4422 ext. 216

# Author:      Chad.Ferguson
#              Soil Scientist
# Created:     07/19/2016
# Copyright:   (c) Charles.Ferguson 2016

# ==========================================================================================
# Updated  2/12/2021 - Adolfo Diaz
# - Hydric Classification Presence was added as an additional optional interpreation.
# - Added the simple soils geometry as a layer.
# - Added 'datetime' as a library to be imported; not sure why it was functioning
#   correclty without it.
# - replaced the reserved python keyword 'property' with soilProperty
# - slightly updated the metadata description

# ==========================================================================================
# Updated  4/7/2021 - Adolfo Diaz
# - Changed Hydric Rating interpretation from dominant condition to component frequency.
#   This uses Jason Nemecek's approach
# - Added URL to access Ecological Site Descriptions in EDIT database
# - Added SSURGO Metadata for spatial and tabular version to final output.

# ==========================================================================================
# Updated  7/9/2021 - Adolfo Diaz
# - Addressed a bug that occurred while adding the symbolized layers to ArcGIS Pro.
#   Updated the map reference object to "aprxMap" when the 'SSURGO Layer' group does NOT exist.
#   Prior to this update, the 'map' object that was being referenced came from the first attempt
#   at determining whether the 'SSURGO Layer' group layer existed.  That 'map' object is now deleted.

# ==========================================================================================
# Updated  9/3/2021 - Adolfo Diaz
# - Added survey area version and survey area version date to the SSURGO_Mapunits layer

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

    SELECT CONVERT(varchar(10), [SAVEREST], 126) AS SAVEREST FROM SASTATUSMAP WHERE AREASYMBOL = '" + areaSym + "' AND SAPUBSTATUSCODE = 2
    """

    """ -------------------- Query with spatialver and tabularver -----------------
        ~DeclareGeometry(@aoi)~
    select @aoi = geometry::STPolyFromText('POLYGON (( -93.557235688 44.189167781,-93.557235688 44.19613589,-93.547238902 44.19613589,-93.547238902 44.189167781,-93.557235688 44.189167781,-93.557235688 44.189167781))', 4326)
    ~DeclareIdGeomTable(@intersectedPolygonGeometries)~
    ~GetClippedMapunits(@aoi,polygon,geo,@intersectedPolygonGeometries)~

    SELECT L.areasymbol, M.musym, M.muname, id AS mukey, S.spatialversion,
    CONVERT(varchar(10), [S].[spatialverest], 126) AS spatialdate, T.tabularversion,
    CONVERT(varchar(10), [T].[tabularverest], 126) AS tabulardate, geom
    FROM @intersectedPolygonGeometries
    INNER JOIN mapunit M ON id = M.mukey
    INNER JOIN legend L ON M.lkey = L.lkey
    INNER JOIN saspatialver AS S ON L.areasymbol = S.areasymbol
    INNER JOIN satabularver AS T ON L.areasymbol = T.areasymbol"""

    """ -------------------- Query with saversion, spatialver, tabularver -----------------
        ~DeclareGeometry(@aoi)~
    select @aoi = geometry::STPolyFromText('POLYGON (( -93.557235688 44.189167781,-93.557235688 44.19613589,-93.547238902 44.19613589,-93.547238902 44.189167781,-93.557235688 44.189167781,-93.557235688 44.189167781))', 4326)
    ~DeclareIdGeomTable(@intersectedPolygonGeometries)~
    ~GetClippedMapunits(@aoi,polygon,geo,@intersectedPolygonGeometries)~

    SELECT L.areasymbol, M.musym, M.muname, id AS mukey,
    SA.saversion, CONVERT(varchar(10), [SA].[saverest], 126) AS surveyareadate,
    S.spatialversion, CONVERT(varchar(10), [S].[spatialverest], 126) AS spatialdate,
    T.tabularversion, CONVERT(varchar(10), [T].[tabularverest], 126) AS tabulardate, geom

    FROM @intersectedPolygonGeometries
    INNER JOIN mapunit M ON id = M.mukey
    INNER JOIN legend L ON M.lkey = L.lkey
    INNER JOIN sacatalog AS SA ON L.areasymbol = SA.areasymbol
    INNER JOIN saspatialver AS S ON L.areasymbol = S.areasymbol
    INNER JOIN satabularver AS T ON L.areasymbol = T.areasymbol"""


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

        # Create empty feature class - fields will be added based on SDA metadata
        arcpy.management.CreateFeatureclass(os.path.dirname(outSSURGOlayerPath), outputName, "POLYGON", None, None, None, arcpy.env.outputCoordinateSystem )

        now = datetime.datetime.now()
        timeStamp = now.strftime('%Y-%m-%d T%H:%M:%S')

        header = """/** SDA Query application "Wetland Compliance Tool" **/"""
        gQry = header + "\n-- " + timeStamp

        gQry += """
        ~DeclareGeometry(@aoi)~
        select @aoi = geometry::STPolyFromText('POLYGON (( """ + coorStr + """))', 4326)
        ~DeclareIdGeomTable(@intersectedPolygonGeometries)~
        ~GetClippedMapunits(@aoi,polygon,geo,@intersectedPolygonGeometries)~

        SELECT L.areasymbol, M.musym, M.muname, id AS mukey,
        SA.saversion, CONVERT(varchar(10), [SA].[saverest], 126) AS surveyareadate,
        S.spatialversion, CONVERT(varchar(10), [S].[spatialverest], 126) AS spatialdate,
        T.tabularversion, CONVERT(varchar(10), [T].[tabularverest], 126) AS tabulardate, geom

        FROM @intersectedPolygonGeometries
        INNER JOIN mapunit M ON id = M.mukey
        INNER JOIN legend L ON M.lkey = L.lkey
        INNER JOIN sacatalog AS SA ON L.areasymbol = SA.areasymbol
        INNER JOIN saspatialver AS S ON L.areasymbol = S.areasymbol
        INNER JOIN satabularver AS T ON L.areasymbol = T.areasymbol"""

        #AddMsgAndPrint(str(gQry))

        # SDA url
        url = "https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest"
        AddMsgAndPrint('Sending coordinates to Soil Data Access')

        # Create request using JSON, return data as JSON
        request = {}
        request["format"] = "JSON+COLUMNNAME+METADATA"
        request["query"] = gQry

        #json.dumps = serialize obj (request dictionary) to a JSON formatted str
        data = json.dumps(request)

        # Send request to SDA Tabular service using urllib library
        # because we are passing the "data" argument, this is a POST request, not a GET

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
            queryData = qData["Table"]

            columnNames = queryData.pop(0)       # Isolate column names and remove from propertyData
            columnNames.remove(columnNames[-1])     # Remove the geometry column information
            columnInfo = queryData.pop(0)        # Isolate column info and remove from propertyData
            columnInfo.remove(columnInfo[-1])       # Remove the geometry column information

            # Add the necessary fields from SDA to the FC
            if not addSSURGOpropertyFld(outSSURGOlayerPath, columnNames, columnInfo):
                return False

            # Add "SHAPE@WKT" to the list of fields
            # ['areasymbol','musym','muname','mukey','spatialversion','spatialdate','tabularversion','tabulardate','SHAPE@WKT']
            columnNames.append('SHAPE@WKT')

            # Create cursor to reconstruct incdividual polygons and populate the fields
            # I need to design a better way of inserting records based on the number
            # of fields and not hardcode it.
            rows =  arcpy.da.InsertCursor(outSSURGOlayerPath, columnNames)

            for rec in queryData:
                areasym = rec[0]
                musym = rec[1]
                muname = rec[2]
                mukey = rec[3]
                surveyAreaVer = rec[4]
                surveyAreaDate = rec[5]
                spatialVer = rec[6]
                spatialDate = rec[7]
                tabularVer = rec[8]
                tabularDate = rec[9]
                polygon = rec[10]

                value = areasym,musym,muname,mukey,surveyAreaVer,surveyAreaDate,spatialVer,spatialDate,tabularVer,tabularDate,polygon
                rows.insertRow(value)

            AddMsgAndPrint("\nSuccessfully Created SSURGO Layer from Soil Data Access")
            AddMsgAndPrint("Output location: " + str(outSSURGOlayerPath))

            # Update Basic Metadata for the SSURGO_WCT layer
            ssurgoWCTmetadata = md.Metadata(outSSURGOlayerPath)

            if not ssurgoWCTmetadata.isReadOnly:
                AddMsgAndPrint("\n\n Updating Metadata for " + outSSURGOlayerPath)
                newSSURGOmeta = md.Metadata()
                newSSURGOmeta.title = "SSURGO WCT"
                newSSURGOmeta.tags = "USDA, NRCS, Soil and Plant Science Division, Wetland Compliance Tool"
                newSSURGOmeta.summary = "SSURGO Layer used for Wetland Compliance reference - Created: " + timeStamp
                newSSURGOmeta.credits = "USDA - NRCS, Soil and Plant Science Division"
                newSSURGOmeta.description = "\
This layer was produced using SSURGO (Soil Survey Geographic Database)\n\
data derived from Soil Data Access.\n\
"
                newSSURGOmeta.accessConstraints = "\
Soil survey data seldom contain detailed, site-specific information.\n\
They are not intended for use as primary regulatory tools in site-\n\
specific permitting decisions. They are, however, useful for broad\n\
regulatory planning and application.\n\
\n\
Soil survey information cannot replace site-specific details, which\n\
require onsite investigation. It is a valuable tool where acquiring\n\
onsite data is not feasible or is cost prohibitive. It is most useful\n\
as a tool for planning onsite investigation. Understanding the\n\
capability and limitations of the different types of soil data is\n\
essential for making the best conservation-planning decisions."

                ssurgoWCTmetadata.copy(newSSURGOmeta)
                ssurgoWCTmetadata.save()

            return outSSURGOlayerPath

        else:
            AddMsgAndPrint("Failed to create geometry from SDA",2)
            AddMsgAndPrint(gQry,1)
            return False

    except socket.timeout as e:
        AddMsgAndPrint('Soil Data Access timeout error',2)
        return False

    except socket.error as e:
        AddMsgAndPrint('Socket error: ' + str(e),2)
        return False

    except HTTPError as e:
        AddMsgAndPrint('HTTP Error' + str(e),2)
        AddMsgAndPrint(gQry,1)
        return False

    except URLError as e:
        AddMsgAndPrint('URL Error' + str(e),2)
        return False

    except:
        errorMsg()
        return False

# ==============================================================================================================================
def updateMetadataDescription(ssurgoProperty,layerPath):

    try:

        propertyDescriptionDict ={'Drainage Class': "\
Drainage Class (drainagecl)\n\
Drainage class (natural) refers to the frequency and duration of wet\n\
periods under conditions similar those under which the soil formed.\n\
Alterations of the water regime by human activities, either through drainage\n\
or irrigation, are not a consideration unless they have significantly\n\
changed the morphology of the soil. Seven classes of natural soil drainage\n\
are recognized-excessively drained, somewhat excessively drained, well drained,\n\
moderately well drained, somewhat poorly drained, poorly drained, and very poorly\n\
drained. These classes are defined in the Soil Survey Manual.",

                                  'Ecological Classification Type Name': "\
Ecological Classification Type Name (ecoclasstypename)\n\
An ecological site name provides a general description of a particular\n\
ecological site. An ecological site is the product of all the environmental\n\
factors responsible for its development. It has characteristic soils that\n\
have developed over time; a characteristic hydrology particularly\n\
infiltration and runoff, that has developed over time; and a characteristic\n\
plant community (kind and amount of vegetation). The vegetation, soils, and\n\
hydrology are all interrelated. Each is influenced by the others and influences\n\
the development of the others. For example, the hydrology of the site is\n\
influenced by development of the soil and plant community. The plant community\n\
on an ecological site is typified by an association of species that differs\n\
from that of other ecological sites in the kind and/or proportion of species\n\
or in total production.  Descriptions of ecological sites are provided in the\n\
Field Office Technical Guide, which is available in local offices of the Natural\n\
Resources Conservation Service. Descriptions of those displayed in this map\n\
and summary table may also be accessed through the Ecological\n\
Site Assessment tab in Web Soil Survey.",

                                    'Ecological Classification Name': "\
Ecological Classification Name (ecoclassname)\n\
The descriptive name of a particular ecological community. For NRCS ecological\n\
sites, it is the concatenated form of three or six other fields. The actual\n\
fields that are concatenated together to form this name differ between range\n\
and forest ecological sites.",

                                    'Ecological Classification ID': "\
Ecological Classification ID (ecoclassid) \n\
The identifier of a particular ecological community. For NRCS ecological sites,\n\
it is the concatenated form of ecological site type, ecological site MLRA,\n\
ecological site LRU, ecological site number and ecological site state FIPS\n\
alpha code.",

                                    'Flooding Frequency': "\
Flooding Frequency (flodfreqdcd)\n\
The annual probability of a flood event expressed as a class. This column displays\n\
the dominant flood frequency class for the map unit, based on composition percentage\n\
of map unit components whose composition in the map unit is equal to or exceeds 15%.",

                                    'Hydric Rating': "\
Hydric Soils Rating by Mapunit (hydric_rating)\n\
This Hydric Soil Category rating indicates the components of map units that meet the criteria\n\
for hydric soils. Map units are composed of one or more major soil components or soil types\n\
that generally make up 20 percent or more of the map unit and are listed in the map unit name,\n\
and they may also have one or more minor contrasting soil components that generally make up\n\
less than 20 percent of the map unit. Each major and minor map unit component that meets the\n\
hydric criteria is rated hydric. The map unit class ratings based on the hydric components\n\
present are: Hydric, Predominantly Hydric, Partially Hydric, Predominantly Nonhydric, and\n\
Nonhydric.\n\
\n\
     \"Hydric\" means that all major and minor components listed for a given map unit are rated\n\
                as being hydric.\n\
     \"Predominantly Hydric\" means that all major components listed for a given map unit are\n\
                              rated as hydric, and at least one contrasting minor component is\n\
                              not rated hydric.\n\
     \"Partially Hydric\" means that at least one major component listed for a given map unit is\n\
                          rated as hydric, and at least one other major component is not rated hydric.\n\
     \"Predominantly Nonhydric\" means that no major component listed for a given map unit is rated\n\
                                 as hydric, and at least one contrasting minor component is rated hydric.\n\
     \"Nonhydric\" means no major or minor components for the map unit are rated hydric. The assumption is\n\
                   that the map unit is nonhydric even if none of the components within the map unit have\n\
                   been rated.\n\
\n\
Hydric soils are defined by the National Technical Committee for Hydric Soils (NTCHS)\n\
as soils that formed under conditions of saturation, flooding, or ponding long enough\n\
during the growing season to develop anaerobic conditions in the upper part\n\
(Federal Register, 1994). Under natural conditions, these soils are either saturated or\n\
inundated long enough during the growing season to support the growth and reproduction\n\
of hydrophytic vegetation.",

                                    'Hydric Condition': "\
Hydric Condition (hydricon)\n\
Natural condition of the soil component",

                                    'Hydrologic Soil Group':"\
Hydrologic Soil Group (hydgrp)\n\
Hydrologic soil groups are based on estimates of runoff potential. Soils are assigned to\n\
one of four groups according to the rate of water infiltration when the soils are not\n\
protected by vegetation, are thoroughly wet, and receive precipitation from\n\
long-duration storms.\n\
\n\
The soils in the United States are assigned to four groups (A, B, C, and D) and three\n\
dual classes (A/D, B/D, and C/D). The groups are defined as follows:\n\
\n\
\tGroup A. Soils having a high infiltration rate (low runoff potential) when thoroughly wet.\n\
\tThese consist mainly of deep, well drained to excessively drained sands or gravelly sands.\n\
\tThese soils have a high rate of water transmission.\n\
\n\
\tGroup B. Soils having a moderate infiltration rate when thoroughly wet. These consist chiefly\n\
\tof moderately deep or deep, moderately well drained or well drained soils that have moderately\n\
\tfine texture to moderately coarse texture. These soils have a moderate rate of water transmission.\n\
\n\
\tGroup C. Soils having a slow infiltration rate when thoroughly wet. These consist chiefly of\n\
\tsoils having a layer that impedes the downward movement of water or soils of moderately fine\n\
\ttexture or fine texture. These soils have a slow rate of water transmission.\n\
\n\
\tGroup D. Soils having a very slow infiltration rate (high runoff potential) when thoroughly wet.\n\
\tThese consist chiefly of clays that have a high shrink-swell potential, soils that have a high water\n\
\ttable, soils that have a claypan or clay layer at or near the surface, and soils that are shallow\n\
\tover nearly impervious material. These soils have a very slow rate of water transmission.\n\
\n\
\tIf a soil is assigned to a dual hydrologic group (A/D, B/D, or C/D), the first letter is for drained\n\
\tareas and the second is for undrained areas. Only the soils that in their natural condition are in\n\
\tgroup D are assigned to dual classes.",

                                    'Ponding Frequency Class':"\
Ponding Frequency - Presence (pondfreqprs)\n\
Ponding is standing water in a closed depression. The water is removed only by deep percolation,\n\
transpiration, or evaporation or by a combination of these processes. Ponding frequency classes are\n\
based on the number of times that ponding occurs over a given period. Frequency is expressed as none,\n\
rare, occasional, and frequent.\n\
\n\
\"None\" means that ponding is not probable. The chance of ponding is nearly 0 percent in any year.\n\
\n\
\"Rare\" means that ponding is unlikely but possible under unusual weather conditions. The chance of\n\
ponding is nearly 0 percent to 5 percent in any year.\n\
\n\
\"Occasional\" means that ponding occurs, on the average, once or less in 2 years. The chance of ponding\n\
is 5 to 50 percent in any year.\n\
\n\
\"Frequent\" means that ponding occurs, on the average, more than once in 2 years. The chance of ponding\n\
is more than 50 percent in any year.",

                                    'Water Table Depth Annual Minimum':"\
Water Table Depth Annual Minimum (wtdepannmin)\n\
The shallowest depth to a wet soil layer (water table) at any time during the year expressed as centimeters\n\
from the soil surface, for components whose composition in the map unit is equal to or exceeds 15%.",

                                    'Hydric Classification Presence':"\
Hydric Classification Presence (hydclprs)\n\
This rating indicates the percentage of map units that meets the criteria for hydric soils. Map units are\n\
composed of one or more map unit components or soil types, each of which is rated as hydric soil or not hydric.\n\
Map units that are made up dominantly of hydric soils may have small areas of minor nonhydric components in the\n\
higher positions on the landform, and map units that are made up dominantly of nonhydric soils may have small\n\
areas of minor hydric components in the lower positions on the landform. Each map unit is rated based on its\n\
respective components and the percentage of each component within the map unit.\n\
\n\
The thematic map is color coded based on the composition of hydric components. The five color classes are\n\
separated as 100 percent hydric components, 66 to 99 percent hydric components, 33 to 65 percent hydric\n\
components, 1 to 32 percent hydric components, and less than one percent hydric components.\n\
\n\
Hydric soils are defined by the National Technical Committee for Hydric Soils (NTCHS) as soils that formed\n\
under conditions of saturation, flooding, or ponding long enough during the growing season to develop anaerobic\n\
conditions in the upper part (Federal Register, 1994). Under natural conditions, these soils are either saturated\n\
or inundated long enough during the growing season to support the growth and reproduction of hydrophytic\n\
vegetation."}


        if not ssurgoProperty in propertyDescriptionDict:
            AddMsgAndPrint("Could not update metadata description for " + ssurgoProperty)
            return False

        # Update Metadata description for the SSURGO_WCT layer
        lyrMetadata = md.Metadata(layerPath)

        if not lyrMetadata.isReadOnly:

            lyrDescription = lyrMetadata.description
            updatedMetadata = md.Metadata()           # New metadata

            # preserve existing metadata by coping all elements into new one
            updatedMetadata.copy(lyrMetadata)

            # Append to current description if currently populated
            if lyrDescription is None or len(str(lyrDescription)) < 1:
                updatedMetadata.description = propertyDescriptionDict[ssurgoProperty]
            else:
                updatedMetadata.description = lyrDescription + "\n" + (77 * "-") + "\n" + propertyDescriptionDict[ssurgoProperty]

            lyrMetadata.copy(updatedMetadata)
            lyrMetadata.save()
            arcpy.SetProgressorLabel("Successfully updated metadata for " + ssurgoProperty)
            #AddMsgAndPrint("Successfully updated metadata for " + ssurgoProperty)

        else:
            AddMsgAndPrint("Metadata is Read-only.  Could not update Description metadata for: " + ssurgoProperty,1)

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

        # This is for aggregating fields within the Component Ecological Classification
        # Table using the 'Dominant Condition' aggregation method and only returning
        # ecological class names that pertain to the the NRCS classification type
        if aggregationMethod == 'coecoclass':
            # If you want to see the sum of the components and the maximum sum of the components
            # substitute the following SELECT statement with the last SELECT statement
            # " SELECT #domcondition.areasymbol, #domcondition.mukey, #domcondition.musym, #domcondition.sumofcomppct_r, #domcondition2.maxsumofcomppct_R, #domcondition." + ssurgoFld + "\n"\

            pQry = "SELECT areasymbol, mapunit.mukey, musym, SUM(comppct_r) as sumofcomppct_r, " + ssurgoFld + "\n"\
            " INTO #domcondition\n"\
            " FROM legend\n"\
            " JOIN mapunit on mapunit.lkey = legend.lkey\n"\
            " AND mapunit.mukey IN (" + keys + ")\n"\
            " JOIN component on component.mukey = mapunit.mukey\n"\
            " LEFT OUTER JOIN coecoclass ON component.cokey = coecoclass.cokey\n"\
            " AND ecoclasstypename LIKE 'NRCS%'\n"\
            " GROUP BY  areasymbol, mapunit.mukey, musym, " + ssurgoFld + "\n"\
            " order by areasymbol, musym, mapunit.mukey\n"\
            " SELECT areasymbol, mukey, musym, max(sumofcomppct_r) as maxsumofcomppct_R\n"\
            " INTO #domcondition2\n"\
            " from #domcondition\n"\
            " GROUP BY areasymbol,mukey, musym\n"\
            " SELECT #domcondition.areasymbol, #domcondition.mukey, #domcondition.musym, #domcondition." + ssurgoFld + "\n"\
            " FROM #domcondition\n"\
            " JOIN #domcondition2 on #domcondition2.maxsumofcomppct_R = #domcondition.sumofcomppct_r AND #domcondition.mukey = #domcondition2.mukey\n"\
            " order by  #domcondition.areasymbol,#domcondition.musym, #domcondition.mukey\n"\

        # This is for Jason Nemecek's
        elif aggregationMethod == 'Component Count':
            pQry = "SELECT areasymbol, musym, muname, mu.mukey/1  AS mukey,\n"\
            " (SELECT TOP 1 COUNT_BIG(*)\n"\
            " FROM mapunit\n"\
            " INNER JOIN component ON component.mukey=mapunit.mukey AND mapunit.mukey = mu.mukey) AS comp_count,\n"\
            " (SELECT TOP 1 COUNT_BIG(*)\n"\
            " FROM mapunit\n"\
            " INNER JOIN component ON component.mukey=mapunit.mukey AND mapunit.mukey = mu.mukey\n"\
            " AND majcompflag = 'Yes') AS count_maj_comp,\n"\
            " (SELECT TOP 1 COUNT_BIG(*)\n"\
            " FROM mapunit\n"\
            " INNER JOIN component ON component.mukey=mapunit.mukey AND mapunit.mukey = mu.mukey\n"\
            " AND hydricrating = 'Yes' ) AS all_hydric,\n"\
            " (SELECT TOP 1 COUNT_BIG(*)\n"\
            " FROM mapunit\n"\
            " INNER JOIN component ON component.mukey=mapunit.mukey AND mapunit.mukey = mu.mukey\n"\
            " AND majcompflag = 'Yes' AND hydricrating = 'Yes') AS maj_hydric,\n"\
            " (SELECT TOP 1 COUNT_BIG(*)\n"\
            " FROM mapunit\n"\
            " INNER JOIN component ON component.mukey=mapunit.mukey AND mapunit.mukey = mu.mukey\n"\
            " AND majcompflag = 'Yes' AND hydricrating != 'Yes') AS maj_not_hydric,\n"\
            " (SELECT TOP 1 COUNT_BIG(*)\n"\
            " FROM mapunit\n"\
            " INNER JOIN component ON component.mukey=mapunit.mukey AND mapunit.mukey = mu.mukey\n"\
            " AND majcompflag != 'Yes' AND hydricrating  = 'Yes' ) AS hydric_inclusions,\n"\
            " (SELECT TOP 1 COUNT_BIG(*)\n"\
            " FROM mapunit\n"\
            " INNER JOIN component ON component.mukey=mapunit.mukey AND mapunit.mukey = mu.mukey\n"\
            " AND hydricrating  != 'Yes') AS all_not_hydric,\n"\
            " (SELECT TOP 1 COUNT_BIG(*)\n"\
            " FROM mapunit\n"\
            " INNER JOIN component ON component.mukey=mapunit.mukey AND mapunit.mukey = mu.mukey\n"\
            " AND hydricrating  IS NULL ) AS hydric_null\n"\
            " INTO #main_query\n"\
            " FROM legend AS l\n"\
            " INNER JOIN  mapunit AS mu ON mu.lkey = l.lkey AND mu.mukey IN (" + keys + ")\n"\
            " SELECT  areasymbol, musym, muname, mukey,\n"\
            " CASE WHEN comp_count = all_not_hydric + hydric_null THEN  'Nonhydric'\n"\
            " WHEN comp_count = all_hydric  THEN 'Hydric'\n"\
            " WHEN comp_count != all_hydric AND count_maj_comp = maj_hydric THEN 'Predominantly Hydric'\n"\
            " WHEN hydric_inclusions >= 0.5 AND  maj_hydric < 0.5 THEN  'Predominantly Nonydric'\n"\
            " WHEN maj_not_hydric >= 0.5  AND  maj_hydric >= 0.5 THEN 'Partially Hydric' ELSE 'Error' END AS hydric_rating\n"\
            " FROM #main_query\n"\


        elif aggregationMethod == 'comonth':
            pQry = " SELECT areasymbol, mapunit.mukey, musym, component.cokey, component.compname, component.comppct_r,\n"\
            " (SELECT top 1 comonth2." + ssurgoFld + " FROM comonth comonth2 join component component2 on component2.cokey = comonth2.cokey and component2.cokey = component.cokey\n"\
            " ORDER BY (CASE WHEN comonth2." + ssurgoFld + " = 'Frequent' Then 1\n"\
            " WHEN comonth2." + ssurgoFld + " = 'Common' Then 1\n"\
            " WHEN comonth2." + ssurgoFld + " = 'Occasional' Then 2\n"\
            " WHEN comonth2." + ssurgoFld + " = 'Rare' Then 3\n"\
            " WHEN comonth2." + ssurgoFld + " = 'None' Then 4\n"\
            " WHEN comonth2." + ssurgoFld + "  IS NULL Then 4 END) ASC) " + ssurgoFld + "\n"\
            " INTO #mostfrequent\n"\
            " FROM legend\n"\
            " JOIN mapunit on mapunit.lkey = legend.lkey\n"\
            " AND mapunit.mukey IN (" + keys + ")\n"\
            " JOIN component on component.mukey = mapunit.mukey\n"\
            " LEFT OUTER JOIN comonth ON component.cokey = comonth.cokey\n"\
            " GROUP BY  areasymbol, mapunit.mukey, musym,  component.cokey, component.compname, component.comppct_r\n"\
            " order by areasymbol, musym, mapunit.mukey, component.compname\n"\
            " SELECT areasymbol,mukey, musym, SUM(comppct_r) as sumofcomppct_r, CASE WHEN " + ssurgoFld + " IS NULL THEN 'None' ELSE " + ssurgoFld + " END as " + ssurgoFld + "\n"\
            " INTO #domcondition\n"\
            " FROM #mostfrequent\n"\
            " GROUP BY  areasymbol, mukey, " + ssurgoFld + ", musym\n"\
            " order by areasymbol, musym, mukey\n"\
            " SELECT areasymbol, mukey, musym, max(sumofcomppct_r) as maxsumofcomppct_R\n"\
            " INTO #domcondition2\n"\
            " from #domcondition\n"\
            " GROUP BY areasymbol,mukey, musym\n"\
            " SELECT DISTINCT #domcondition.areasymbol, #domcondition.mukey, #domcondition.musym, #domcondition.sumofcomppct_r, #domcondition2.maxsumofcomppct_R,  #domcondition." + ssurgoFld + "\n"\
            " into #domcondition3\n"\
            " FROM #domcondition\n"\
            " JOIN #domcondition2 on #domcondition2.maxsumofcomppct_R = #domcondition.sumofcomppct_r AND #domcondition.mukey = #domcondition2.mukey\n"\
            " order by  #domcondition.areasymbol,#domcondition.musym,  #domcondition.mukey\n"\
            " select areasymbol, mukey, musym, \n"\
            " (SELECT top 1 SUB." + ssurgoFld + " FROM #domcondition3 sub\n"\
            " WHERE sub.mukey = #domcondition3.mukey\n"\
            " ORDER BY (CASE WHEN sub." + ssurgoFld + " = 'Frequent' Then 1\n"\
            " WHEN sub." + ssurgoFld + " = 'Common' Then 1\n"\
            " WHEN sub." + ssurgoFld + " = 'Occasional' Then 2\n"\
            " WHEN sub." + ssurgoFld + " = 'Rare' Then 3\n"\
            " WHEN sub." + ssurgoFld + " = 'None' Then 4\n"\
            " WHEN sub." + ssurgoFld + "  IS NULL Then 4 END) ASC) " + ssurgoFld + "\n"\
            " FROM #domcondition3\n"\
            " GROUP BY  areasymbol, mukey, musym, " + ssurgoFld + "\n"\

        elif aggregationMethod == "Mapunit Aggregate":
            # SELECT mukey,musym,muname,wtdepannmin FROM muaggatt where mukey IN (398974)
            pQry = "SELECT mukey,musym,muname," + ssurgoFld + " FROM muaggatt where mukey IN (" + keys + ")\n"\

        elif aggregationMethod == "Dominant Component (Category)":

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
                    'Hydric Rating':'hydric_rating',
                    'Hydric Classification Presence':'hydclprs',
                    'Drainage Class': 'drainagecl',
                    'Ecological Classification ID':'ecoclassid',
                    'Ecological Classification Name':'ecoclassname',
                    'Ecological Classification Type Name':'ecoclasstypename',
                    'Effective Cation Exchange Capcity - Rep Value': 'ecec_r',
                    'Electrial Conductivity 1:5 by volume - Rep Value': 'ec15_r',
                    'Electrical Conductivity - Rep Value': 'ec_r',
                    'Exchangeable Sodium Percentage - Rep Value': 'esp_r',
                    'Extract Aluminum - Rep Value': 'extral_r',
                    'Extractable Acidity - Rep Value': 'extracid_r',
                    'Fine Sand - Rep Value': 'sandfine_r',
                    'Fine Silt - Rep Value': 'siltfine_r',
                    'Flooding Frequency': 'flodfreqdcd',
                    'Flooding Frequency - Maximum': 'flodfreqmax',
                    'Free Iron - Rep Value': 'freeiron_r',
                    'Gypsum - Rep Value': 'gypsum_r',
                    'Hydrologic Soil Group': 'hydgrp',
                    'Kf': 'kffact',
                    'Ki': 'kifact',
                    'Kr': 'krfact',
                    'Kw': 'kwfact',
                    'LEP - Rep Value': 'lep_r',
                    'Liquid Limit - Rep Value': 'll_r',
                    'Medium Sand - Rep Value': 'sandmed_r',
                    'Organic Matter - Rep Value': 'om_r',
                    'Oxalate Aluminum - Rep Value': 'aloxalate_r',
                    'Oxalate Iron - Rep Value': 'feoxalate_r',
                    'Oxalate Phosphate - Rep Value': 'poxalate_r',
                    'Plasticity Index - Rep Value': 'pi_r',
                    'Ponding Frequency Class': 'pondfreqcl',  # comonth table
                    'Ponding Frequency - Presence': 'pondfreqprs', # muaggat table
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
                    'Water Table Depth Annual Minimum': 'wtdepannmin',
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
##        AddMsgAndPrint(str(fldNames),1)
##        AddMsgAndPrint("--------------------",1)
##        AddMsgAndPrint(str(fldInfo),1)

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
            queryData = qData["Table"]

##            # remove the column names and column info lists from propRes list above
##            # Last element represents info for specific property
##            # [u'areasymbol', u'musym', u'muname', u'mukey', u'drainagecl']
##            # [u'ColumnOrdinal=0,ColumnSize=20,NumericPrecision=255,NumericScale=255,ProviderType=VarChar,IsLong=False,ProviderSpecificDataType=System.Data.SqlTypes.SqlString,DataTypeName=varchar',
##            columnNames = list()   # ['drainagecl']
##            columnInfo = list()
##            columnNames.append(propRes.pop(0)[-1])
##            columnInfo.append(propRes.pop(0)[-1])

            columnNames = queryData.pop(0)       # Isolate column names and remove from queryData
            columnInfo = queryData.pop(0)        # Isolate column info and remove from queryData
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

            # rearrange queryData list into a dictionary of lists with the
            # mukey as key and tabular info as a list of values.  This will be used
            # in the UpdateCursor to lookup tabular info by MUKEY
            # '455428': [u'MN161','L110E','Lester-Ridgeton complex, 18 to 25 percent slopes','B']
            propertyDict = dict()

            for item in queryData:
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
        #AddMsgAndPrint("-----------------------")
        #AddMsgAndPrint("Updating symbology for " + lyrxObj.name)
        sym = lyrxObj.symbology

        if sym.renderer.type == 'UniqueValueRenderer':
            # This will essentially reset the values
            # sym.updateRenderer('UniqueValueRenderer')

            # This is the field used to render the symbology i.e. [hydgrp]
            rendererFld = sym.renderer.fields

            # In order to add or remove values from a symbology list the group
            # heading must be populated.  For the SSURGO_WCT Tool, the group heading
            # name used was the Field Alias Name of the renderer field.
            fieldAlias = ""
            if rendererFld[0] in [f.name for f in arcpy.ListFields(ssurgoFC)]:
                fieldAlias = [f.aliasName for f in arcpy.ListFields(ssurgoFC,rendererFld[0] + "*")][0]
            else:
                return None

            # These are the values found in the FC being symbolized
            uniqueFCvalues = list(set([row[0] for row in arcpy.da.SearchCursor(ssurgoFC,rendererFld)]))

            uniqueRendererValues = list() # list of unique values in the symbology renderer
            valuesToAdd = list()          # list of values that need to be added to renderer
            bUpdateRenderer = False       # flag to update symbology

            # Get a list of unique values in symbology renderer. Each value is an item
            # and each item is associated within an ItemGroup.
            for grp in sym.renderer.groups:
                for itm in grp.items:
                    uniqueRendererValues.append(itm.values[0][0])

            # determine whether FC values will be removed or added to
            # symbology renderer
            for val in uniqueFCvalues:
                if val in uniqueRendererValues:
                    uniqueRendererValues.remove(val)
                else:
                    valuesToAdd.append(val)

            # Remove values from Symbology renderer
            if len(uniqueRendererValues) > 0:
                bUpdateRenderer = True
                for val in uniqueRendererValues:
                    sym.renderer.removeValues({fieldAlias: [val]})
                    #AddMsgAndPrint("REMOVING " + str(val))

            # Add values to Symbology renderer
            if len(valuesToAdd) > 0:
                bUpdateRenderer = True
                for val in valuesToAdd:
                    sym.renderer.addValues({fieldAlias: [val]})
                    #AddMsgAndPrint("ADDING " + str(val))

                # The symbology for the newly added values will be the default symbology
                # Update the outlineColor and size
                for grp in sym.renderer.groups:
                    for itm in grp.items:
                        # Set the outline color and size to black and 1.5
                        itm.symbol.outlineColor = {'RGB' : [0, 0, 0, 0]}
                        itm.symbol.size = 1.5
                        #AddMsgAndPrint("Updated Symbology for " + itm.label)

            if bUpdateRenderer:
                lyrxObj.symbology = sym
                #AddMsgAndPrint("SYMBOLOGY UPDATED!!!!!!!!!!!!!!")
    # ------------------------------------------------------------------

    try:
        AddMsgAndPrint("Adding Layers to ArcGIS Pro")

        # path to individual .lyrx files
        scriptPath = os.path.dirname(__file__)

        # isolate the property names (remove aggregation method)
        propertyNames = [soilproperty.split('-')[0] for soilproperty in listOfProperties]
        lyrxToAddToArcPro = []

        # Update the connection properties for the .lyrx files that will be added to ArcGIS Pro
        for soilproperty in listOfProperties:

            # 'Drainage Class - Dominant Condition'
            propSplit = soilproperty.split('-')               # ['Drainage Class ', ' Dominant Condition']
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

            # The layer is missing a .lyrx.  Exception is Ecological class ID and Type
            else:
                if not soilproperty in ['Ecological Classification ID - coecoclass','Ecological Classification Type Name - coecoclass']:
                    AddMsgAndPrint(soilproperty + " is missing .lyrx file",1)
                    AddMsgAndPrint(str(lyrxPath),2)

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

        # Add Layer to existing ArcGIS Pro 'SSURGO Layers' Group
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
                        arcpy.SetProgressorLabel("Adding Layer to ArcGIS Pro: " + lyrx.name)
                        #AddMsgAndPrint("Adding Layer to ArcGIS Pro: " + lyrx.name)

                break
        del map

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
                aprxMap.addLayerToGroup(mapGroupLayer,lyrx)
                #map.addLayerToGroup(mapGroupLayer,lyrx)
                bAddedLyrxFilesToPro = True
                arcpy.SetProgressorLabel("Adding Layer to ArcGIS Pro: " + lyrx.name)
                #AddMsgAndPrint("Adding Layer to ArcGIS Pro: " + lyrx.name)

        # Update symbology for newly added SSURGO_WCT layers
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        for lyr in mapObject.listLayers():

            # This is the 'SSURGO Layers' Group
            # iterate through the nested layers and up
            # the symbology
            if lyr.name == groupLayerName and lyr.isGroupLayer:
                for newLayer in lyr.listLayers():
                    UpdateLyrxSymbology(newLayer)

                    # Turn off visibility for every layer except the SSURGO Mapunits layer
                    if not newLayer.name == "SSURGO Mapunits":
                        newLayer.showLabels = False
                        newLayer.transparency = 50
                        newLayer.visible = False

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

        # --------------- This section is for Ecological Classification
        #                   and Ponding Frequency Class -------------------------------------------
        ecoList = ['Ecological Classification Name - Dominant Condition',
                   'Ecological Classification ID - Dominant Condition',
                   'Ecological Classification Type Name - Dominant Condition']

        tempList = soilPropertyList  # make a copy of the soilPropertyList
        bEcoInterpPresent = False    # True if ecological interp is present

        # iterate through the soilPropertyList and modify the ecological interp.
        # If any Ecological Classification interp is included in the soil
        # property list then include all and make sure they are the last
        # 3 in the list.  Also, update the 'Dominant Condition' aggregation
        # method to 'coecoclass'
        for tempProp in tempList:
            if tempProp in ecoList:
                bEcoInterpPresent = True
                ecoList.pop(ecoList.index(tempProp)) # remove eco interp from ecoList

                # rename item from:
                # 'Ecological Classification Type Name - Dominant Condition' TO
                # 'Ecological Classification Type Name - coecoclass'
                updatePropertyName = tempProp[0:tempProp.find('-')+2] + 'coecoclass'
                soilPropertyList = [x.replace(tempProp,updatePropertyName) for x in soilPropertyList]

                # Put the newly updated eco interp to the end of the list so that
                # all eco interps are together.
                soilPropertyList.sort(key=updatePropertyName.__eq__)

        # If Ecological Classification interp was included in user selection then
        # Add Eco Class ID and Type name
        if bEcoInterpPresent and ecoList:
            for ecoInterp in ecoList:
                updateEcoName = ecoInterp[0:ecoInterp.find('-')+2] + 'coecoclass'
                soilPropertyList.append(updateEcoName)

        # iterate through the soilPropertyList and rename the ponding interp
        # from Dominant Condition' aggregation method to 'comonth'
        for tempProp in tempList:
            if tempProp == 'Ponding Frequency Class - Dominant Condition':

                # rename item from:
                # 'Ponding Frequency Class - Dominant Condition' TO
                # 'Ponding Frequency Class - comonth'
                updatePropertyName = tempProp[0:tempProp.find('-')+2] + 'comonth'
                soilPropertyList = [x.replace(tempProp,updatePropertyName) for x in soilPropertyList]

##            if tempProp == 'Hydric Classification Presence - Mapunit Aggregate':
##
##                # rename item from:
##                # 'Ponding Frequency Class - Dominant Condition' TO
##                # 'Ponding Frequency Class - comonth'
##                updatePropertyName = tempProp[0:tempProp.find('-')+2] + 'hydroclass'
##                soilPropertyList = [x.replace(tempProp,updatePropertyName) for x in soilPropertyList]

        # get SSURGO polgyons from SDA
        #outSSURGOlayer = r'E:\Temp\scratch.gdb\SSURGO_Mapunits'
        outSSURGOlayer = getSSURGOgeometryFromSDA(aoi, outputWS, "SSURGO_Mapunits")

        if not outSSURGOlayer:
            AddMsgAndPrint("Failed to get SSURGO from Soil Data Access",2)
            exit()

        listOfMukeys = list(set([row[0] for row in arcpy.da.SearchCursor(outSSURGOlayer,["MUKEY"])]))

        if listOfMukeys:

            for soilproperty in soilPropertyList:

                propSplit = soilproperty.split('-')  # ['Hydric Classification Presence ', ' Mapunit Aggregate']
                soilproperty = propSplit[0].strip()  # Hydric Classification Presence
                aggMethod = propSplit[1].strip()     # Mapunit Aggregate

##                print(propSplit)
##                print(soilproperty)
##                print(aggMethod)
##                exit()

                theQuery = compileSQLquery(soilproperty,aggMethod,listOfMukeys)
                #AddMsgAndPrint(str(theQuery),1)
                tbRequest = getSDATabularRequest(theQuery,outSSURGOlayer)
                updateMetadataDescription(soilproperty,outSSURGOlayer)

            # Add EDIT URL field if ecoclassname or ecoclassid fields are present
            if "Ecological Classification Name - coecoclass" in soilPropertyList:

                AddMsgAndPrint("Adding Ecological Site Description web link")
                # https://edit.jornada.nmsu.edu/catalogs/esd/103X/F103XY030MN
                editURL = r'https://edit.jornada.nmsu.edu/catalogs/esd'
                editFld = "EDIT_URL"

                arcpy.AddField_management(outSSURGOlayer, editFld, "text", "", "", 100, "EDIT URL")

                expression = "getEditURL(!ecoclassid!)"
                codeblock = """
def getEditURL(ecoID):
    # URL of eco site descriptions
    editURL = r'https://edit.jornada.nmsu.edu/catalogs/esd'

    if ecoID:
        # extract MLRA name from ecological class ID
        mlraName = ecoID[1:5]
        return editURL + r'/' + mlraName + r'/' + ecoID
    else:
        return None"""

                arcpy.CalculateField_management(outSSURGOlayer, editFld, expression, "PYTHON3", codeblock)

        else:
            AddMsgAndPrint("Failed to get a list of MUKEYs from " + os.path.basename(outSSURGOlayer),2)
            return False

        # Adding the SSURGO polygons to the list so that it can be automatically added to ArcGISPro
        # The physical layer name will not be altered.
        soilPropertyList.append(os.path.basename(outSSURGOlayer) + " - Polygons")
        AddSSURGOLayersToArcGISPro(outSSURGOlayer,soilPropertyList)

        return outSSURGOlayer

    except:
        errorMsg()

# ====================================== Main Body ==================================
import sys, os, time, urllib, json, traceback, socket, arcpy, datetime
from arcpy import metadata as md

from urllib.error import HTTPError, URLError
from urllib.request import Request

if __name__ == '__main__':

    try:
        feature = arcpy.GetParameterAsText(0) #
        propertyList = arcpy.GetParameter(1)  # python List of SSURGO Properties
        outLoc = arcpy.GetParameterAsText(2)  # Must be a FGDB

##        feature = r'E:\Temp\SSURGO_WCT.gdb\WSS_aoi'
##        propertyList = ['Hydric Classification Presence - Mapunit Aggregate']
##        propertyList = ['Ecological Classification Name - Dominant Condition',
##                         'Drainage Class - Dominant Condition',
##                         'Hydric Classification Presence - Mapunit Aggregate',
##                         'Hydric Condition - Dominant Condition',
##                         'Hydric Rating - Dominant Condition',
##                         'Hydrologic Group - Dominant Condition',
##                         'Ponding Frequency Class - Dominant Component',
##                         'Water Table Depth Annual - Mapunit Aggregate',
##                         'Hydric Rating - Component Count']
##        outLoc = r'E:\Temp\scratch.gdb'

        outputLayer = start(feature,propertyList,outLoc)


    except:
        errorMsg()
