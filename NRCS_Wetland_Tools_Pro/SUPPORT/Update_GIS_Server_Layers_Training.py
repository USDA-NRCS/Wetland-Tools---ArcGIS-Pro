## ===============================================================================================================
## Name:    Update GIS Server Layers
## Purpose: Updates layers on GeoPortal with results from the current determination project, including all support
##          layers and all layers needed for running the dashboards.
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
##          608.662.4422 ext 216
##
## Created: 04/12/2021
##
## ===============================================================================================================
## Changes
## ===============================================================================================================
##
## rev. 04/12/2021
## - Replaces the Upload to State Office tool from previous ArcMap based tools.
##
## rev. 08/27/2021
## - Updated all functions and test against GIS States.
## - Updated processing for all layers
## - Incorporated Field Mapping to manage the mismatched GlobalID to globalid field names from local to web
##
## rev. 02/18/2022
## - Complete rewrite to change all server interactions other than Append to use the REST API
## - Added management & upload of layers for Request Extent Points and CLU CWD Points for dashboards
##
## rev. 02/22/2022
## - Replaced intersects with overlaps in query function.
## - Created advanced logic for polygon and point replacement in the update_polys function
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
def logBasicSettings():    
    # record basic user inputs and settings to log file for future purposes
    import getpass, time
    f = open(textFilePath,'a+')
    f.write("\n######################################################################\n")
    f.write("Executing Update GIS Server Layers tool...\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("User Parameters:\n")
    f.write("\tInput CWD Layer: " + str(sourceCWD) + "\n")
    f.close
    del f

## ===============================================================================================================
def deleteTempLayers(lyrs):
    for lyr in lyrs:
        if arcpy.Exists(lyr):
            try:
                arcpy.management.Delete(lyr)
            except:
                pass

## ===============================================================================================================
def queryCount(sqlQuery, RESTurl):
## This function uses the REST API to retrieve a count of found features with an SQL Query
## It returns the count of features as an Int. If no features are found, it returns a count of 0
## Any result besides an Int indicates a failed query, generates an error message, and exits

##    try:
    query_url = RESTurl + "/query"

    params = urllibEncode({'where':sqlQuery,
                           'returnCountOnly':'true',
                           'token': portalToken['token']})

    INparams = params.encode('ascii')
    
    resp = urllib.request.urlopen(query_url,INparams)

    responseStatus = resp.getcode()
    responseMsg = resp.msg
    jsonString = resp.read()
    
    # json --> Python; dictionary containing 1 key with a list of lists
    results = json.loads(jsonString)

    # Check for error in results and exit with message if found.
    if 'error' in results.keys():
        if results['error']['message'] == 'Invalid Token':
            AddMsgAndPrint("\nSign-in token expired. Sign-out and sign-in to the portal again and then re-run. Exiting...",2)
            exit()
        else:
            AddMsgAndPrint("\nUnknown error encountered. Make sure you are online and signed in and that the portal is online. Exiting...",2)
            AddMsgAndPrint("\nResponse status code: " + str(responseStatus),2)
            exit()
    else:
        return results['count']


##    except httpErrors as e:
##        if int(e.code) >= 400:
##            AddMsgAndPrint("\nUnknown error encountered. Exiting...",2)
##            AddMsgAndPrint("\nHTTP Error = " + str(e.code),2)
##            errorMsg()
##            exit()
##        else:
##            errorMsg()
##            return False

## ===============================================================================================================
def del_by_attributes(sqlQuery, RESTurl):
## This function deletes features via the REST API with an SQL Query
## The delete results are grouped whereby if any delete fails, the function exits the script with an error message
## If the deletes are successful, the function returns a status of True

##    try:
    delete_url = RESTurl + "/deleteFeatures"

    params = urllibEncode({'f': 'json',
                           'where': sqlQuery,
                           'rollbackOnFailure': 'true',
                           'returnDeleteResults': 'false',
                           'token': portalToken['token']})

    INparams = params.encode('ascii')

    resp = urllib.request.urlopen(delete_url,INparams)
    
    responseStatus = resp.getcode()
    responseMsg = resp.msg
    jsonString = resp.read()

    # json --> Python; dictionary containing 1 key with a list of lists
    results = json.loads(jsonString)

    # Check for error in results and exit with message if found.
    if 'error' in results.keys():
        if results['error']['message'] == 'Invalid Token':
            AddMsgAndPrint("\nSign-in token expired. Sign-out and sign-in to the portal again and then re-run. Exiting...",2)
            exit()
        else:
            AddMsgAndPrint("\nUnknown error encountered. Make sure you are online and signed in and that the portal is online. Exiting...",2)
            AddMsgAndPrint("\nResponse status code: " + str(responseStatus),2)
            exit()

    elif 'false' in results.values():
        AddMsgAndPrint("\nFeatures found but one or more features could not be deleted for replacement. Confirm your write access. Exiting...",2)
        exit()

    else:
        return True
    
##    else:
##        if 'true' in results.values():
##            AddMsgAndPrint("\nNo existing features were found to delete!",0)
##        else:
##            AddMsgAndPrint("\nFeatures were found to be deleted and replaced!",0)
##        return True
        
##    except httpErrors as e:
##        if int(e.code) >= 400:
##            AddMsgAndPrint("\nUnknown error encountered. Exiting...",2)
##            AddMsgAndPrint("\nHTTP Error = " + str(e.code),2)
##            errorMsg()
##            exit()
##        else:
##            errorMsg()
##            return False

## ===============================================================================================================
def del_by_intersect(ws, temp_dir, fc, RESTurl):
## This function deletes features via the REST API with a spatial overlap
## This is only called if intersecting features are known to exist using the returned shapes from queryIntersect
## If the deletes are successful, the function returns a status of True, otherwise it gives an error and is false

##    try:
    # Set variables
    delete_url = RESTurl + "/deleteFeatures"
    wmas_fc = ws + os.sep + "wmas_fc"
    wmas_dis = ws + os.sep + "wmas_dis_fc"
    wmas_sr = arcpy.SpatialReference(3857)

    # Convert the input feature class to Web Mercator and to JSON
    arcpy.management.Project(fc, wmas_fc, wmas_sr)
    arcpy.management.Dissolve(wmas_fc, wmas_dis, "", "", "MULTI_PART", "")
    jsonPolygon = [row[0] for row in arcpy.da.SearchCursor(wmas_dis, ['SHAPE@JSON'])][0]

    #Logic types for spatial relationship for testing:
    #'spatialRelationship':'esriSpatialRelOverlaps',
    #'spatialRelationship':'esriSpatialRelIntersects',

    # Setup parameters for deletion
    params = urllibEncode({'f': 'json',
                           'geometry':jsonPolygon,
                           'geometryType':'esriGeometryPolygon',
                           'spatialRelationship':'esriSpatialRelIntersects',
                           'rollbackOnFailure':'true',
                           'returnDeleteResults':'false',
                           'token': portalToken['token']})

    INparams = params.encode('ascii')

    resp = urllib.request.urlopen(delete_url,INparams)

    responseStatus = resp.getcode()
    responseMsg = resp.msg
    jsonString = resp.read()

    # json --> Python; dictionary containing 1 key with a list of lists
    results = json.loads(jsonString)

    # Check for error in results and exit with message if found.
    if 'error' in results.keys():
        if results['error']['message'] == 'Invalid Token':
            AddMsgAndPrint("\nSign-in token expired. Sign-out and sign-in to the portal again and then re-run. Exiting...",2)
            exit()
        else:
            AddMsgAndPrint("\nUnknown error encountered. Make sure you are online and signed in and that the portal is online. Exiting...",2)
            AddMsgAndPrint("\nResponse status code: " + str(responseStatus),2)
            exit()

    elif 'false' in results.values():
        AddMsgAndPrint("\nFeatures found but one or more features could not be deleted for replacement. Confirm your write access. Exiting...",2)
        exit()

    else:
        return True
    
##    else:
##        if 'true' in results.values():
##            AddMsgAndPrint("\nNo existing features were found to delete!",0)
##        else:
##            AddMsgAndPrint("\nFeatures were found to delete and replace!",0)
##        return True
        
##    except httpErrors as e:
##        if int(e.code) >= 400:
##            AddMsgAndPrint("\nUnknown error encountered. Exiting...",2)
##            AddMsgAndPrint("\nHTTP Error = " + str(e.code),2)
##            errorMsg()
##            exit()
##        else:
##            errorMsg()
##            return False

##  ===============================================================================================================
def queryIntersect(ws, temp_dir, fc, RESTurl, outFC):
##  This function uses a REST API query to retrieve geometry from that overlap an input feature class from a
##  hosted feature service.
##  Relies on a global variable of portalToken to exist and be active (checked before running this function)
##  ws is a file geodatabase workspace to store temp files for processing
##  fc is the input feature class. Should be a polygon feature class, but technically shouldn't fail if other types
##  RESTurl is the url for the query where the target hosted data resides
##  Example: """https://gis-testing.usda.net/server/rest/services/Hosted/CWD_Training/FeatureServer/0/query"""
##  outFC is the output feature class path/name that is return if the function succeeds AND finds data
##  Otherwise False is returned

    # Run the query
##    try:
        
    # Set variables
    query_url = RESTurl + "/query"
    jfile = temp_dir + os.sep + "jsonFile.json"
    wmas_fc = ws + os.sep + "wmas_fc"
    wmas_dis = ws + os.sep + "wmas_dis_fc"
    wmas_sr = arcpy.SpatialReference(3857)

    # Convert the input feature class to Web Mercator and to JSON
    arcpy.management.Project(fc, wmas_fc, wmas_sr)
    arcpy.management.Dissolve(wmas_fc, wmas_dis, "", "", "MULTI_PART", "")
    jsonPolygon = [row[0] for row in arcpy.da.SearchCursor(wmas_dis, ['SHAPE@JSON'])][0]

    #Logic types for spatial relationship for testing:
    #'spatialRelationship':'esriSpatialRelOverlaps',
    #'spatialRelationship':'esriSpatialRelIntersects',
    
    # Setup parameters for query
    params = urllibEncode({'f': 'json',
                           'geometry':jsonPolygon,
                           'geometryType':'esriGeometryPolygon',
                           'spatialRelationship':'esriSpatialRelIntersects',
                           'returnGeometry':'true',
                           'outFields':'*',
                           'token': portalToken['token']})


    INparams = params.encode('ascii')
    resp = urllib.request.urlopen(query_url,INparams)

    responseStatus = resp.getcode()
    responseMsg = resp.msg
    jsonString = resp.read()

    # json --> Python; dictionary containing 1 key with a list of lists
    results = json.loads(jsonString)

    # Check for error in results and exit with message if found.
    if 'error' in results.keys():
        if results['error']['message'] == 'Invalid Token':
            AddMsgAndPrint("\nSign-in token expired. Sign-out and sign-in to the portal again and then re-run. Exiting...",2)
            exit()
        else:
            AddMsgAndPrint("\nUnknown error encountered. Make sure you are online and signed in and that the portal is online. Exiting...",2)
            AddMsgAndPrint("\nResponse status code: " + str(responseStatus),2)
            exit()
    else:
        # Convert results to a feature class
        if not len(results['features']):
            return False
        else:
            with open(jfile, 'w') as outfile:
                json.dump(results, outfile)

            arcpy.conversion.JSONToFeatures(jfile, outFC)
            # Cleanup temp stuff from this function
            files_to_del = [jfile, wmas_fc, wmas_dis]
            for item in files_to_del:
                if arcpy.Exists(item):
                    arcpy.management.Delete(item)
            return outFC

##    except httpErrors as e:
##        if int(e.code) >= 400:
##            AddMsgAndPrint("\nUnknown error encountered. Exiting...",2)
##            AddMsgAndPrint("\nHTTP Error = " + str(e.code),2)
##            errorMsg()
##            exit()
##        else:
##            errorMsg()
##            return False

## ===============================================================================================================
def update_polys_and_points(up_ws, up_temp_dir, proj_fc, up_RESTurl, local_temp, proj_pts = '', ptsURL = '', fldmapping=''):
## Queries polygon layer for intersects. If none found, appends proceed.
## If intersection is found, query returns the geometry for local processing to split the old areas from the new.
## Once local processing is complete the two pieces are put through Delete intersect and then re-uploaded.
## If the related pts and ptsURL variables are populated, the remnant poly data is used to check and move points
## as needed to maintain points. This effectively moves the existing points, if they are not completely
## overwritten, into the remnant poly areas.
    
##    try:
    # set variables
    int_fc = up_ws + os.sep + "int_fc"
    test_fc = up_ws + os.sep + "test_fc"
    pts_temp = up_ws + os.sep + "pts_temp"

    # Manage the local_temp file in case of previous run of tool that had an error or crashed
    if arcpy.Exists(local_temp):
        # Query local temp against the server to see if data is still there. If nothing returned,
        # then append the local temp to the server to restore "deleted" features
        overlapCheck = queryIntersect(up_ws, up_temp_dir, local_temp, up_RESTurl, int_fc)
        if arcpy.Exists(int_fc):
            # Do another intersect to see if there is actual overlap and not just coincident edges
            arcpy.analysis.Intersect([local_temp,overlapCheck], test_fc, "NO_FID", "#", "INPUT")
            if int(arcpy.GetCount_management(test_fc).getOutput(0)) == 0:
                # Features were lost from the server. Restore the local_temp onto the server without the field mapping setting (not needed)
                # Then delete local temps
                arcpy.management.Append(local_temp, up_RESTurl, "NO_TEST")
                # Also handle proj_pts again to make sure they remain restored on the server if necessary
                if proj_pts != '':
                    # Convert local temp to points
                    arcpy.management.FeatureToPoint(local_temp, pts_temp, "INSIDE")
                    # Delete server points
                    del_by_intersect(up_ws, up_temp_dir, local_temp, ptsURL)
                    # Append updated server points
                    arcpy.management.Append(pts_temp, ptsURL, "NO_TEST", fldmapping)
                    arcpy.management.Delete(pts_temp)
                    arcpy.management.Delete(test_fc)
                arcpy.management.Delete(local_temp)
                arcpy.management.Delete(test_fc)
                arcpy.management.Delete(int_fc)
            else:
                # Server features take precedence. Delete local_temp. It will be re-created, if needed, in the next step.
                arcpy.management.Delete(local_temp)
                arcpy.management.Delete(test_fc)
                arcpy.management.Delete(int_fc)
        else:
            # Server features take precedence. Delete local_temp. It will be re-created, if needed, in the next step.
            arcpy.management.Delete(local_temp)
            
    # Check whether the input project area data overlaps anything on the server
    test_results = queryIntersect(up_ws, up_temp_dir, proj_fc, up_RESTurl, int_fc)
    if arcpy.Exists(int_fc):
        # Do another intersect to see if there is actual overlap and not just coincident edges
        arcpy.analysis.Intersect([proj_fc,test_results], test_fc, "NO_FID", "#", "INPUT")
        if int(arcpy.GetCount_management(test_fc).getOutput(0)) > 0:
            ## Features found. Process the geometry changes locally to prep layers for upload.
            # Use the proj_fc to erase overlapping area from the downloaded polygons and check results
            arcpy.analysis.Erase(test_results, proj_fc, poly_multi)
            result = int(arcpy.management.GetCount(poly_multi).getOutput(0))
            if result > 0:
                # Not a 100% replace. Change to single part and update acres
                arcpy.management.MultipartToSinglepart(poly_multi, poly_single)
                expression = "round(!Shape.Area@acres!,2)"
                arcpy.management.CalculateField(poly_single, "acres", expression, "PYTHON_9.3")
                del expression
                # Copy the residual features to the local temp layer to be used in re-upload later in the process
                arcpy.management.CopyFeatures(poly_single, local_temp)
                ## Also process the points layer if there is overlap
                if proj_pts != '':
                    # Create a new set of points to upload
                    arcpy.management.FeatureToPoint(local_temp, pts_temp, "INSIDE")

                # Overlaps exist between new features and remnant features. Do deletes and then uploads of both.
                del_by_intersect(up_ws, up_temp_dir, proj_fc, up_RESTurl)
                arcpy.management.Append(local_temp, up_RESTurl, "NO_TEST")
                if fldmapping != '':
                    arcpy.management.Append(proj_fc, up_RESTurl, "NO_TEST", fldmapping)
                else:
                    arcpy.management.Append(proj_fc, up_RESTurl, "NO_TEST")

                # Also delete and upload remnant and new points if that parameter was called
                if proj_pts != '':
                    # Delete any points in the new areas (to be replaced)
                    del_by_intersect(up_ws, up_temp_dir, proj_fc, ptsURL)
                    # Delete any points in the remnant areas (to be restored from pts_temp)
                    del_by_intersect(up_ws, up_temp_dir, local_temp, ptsURL)
                    if fldmapping != '':
                        arcpy.management.Append(pts_temp, ptsURL, "NO_TEST", fldmapping)
                        arcpy.management.Append(proj_pts, ptsURL, "NO_TEST", fldmapping)
                    else:
                        arcpy.management.Append(pts_temp, ptsURL, "NO_TEST")
                        arcpy.management.Append(proj_pts, ptsURL, "NO_TEST")
            else:
                # A 100% replace, delete and then do uploads of new features, without remnant features
                del_by_intersect(up_ws, up_temp_dir, proj_fc, up_RESTurl)
                if fldmapping != '':
                    arcpy.management.Append(proj_fc, up_RESTurl, "NO_TEST", fldmapping)
                else:
                    arcpy.management.Append(proj_fc, up_RESTurl, "NO_TEST")

                if proj_pts != '':
                    del_by_intersect(up_ws, up_temp_dir, proj_fc, ptsURL)
                    if fldmapping != '':
                        arcpy.management.Append(proj_pts, ptsURL, "NO_TEST", fldmapping)
                    else:
                        arcpy.management.Append(proj_pts, ptsURL, "NO_TEST")

        else:
            # No actual overlaps, probably just touching edges. Do the standard upload with no deletes.
            if fldmapping != '':
                arcpy.management.Append(proj_fc, up_RESTurl, "NO_TEST", fldmapping)
            else:
                arcpy.management.Append(proj_fc, up_RESTurl, "NO_TEST")
            if proj_pts != '':
                if fldmapping != '':
                    arcpy.management.Append(proj_pts, ptsURL, "NO_TEST", fldmapping)
                else:
                    arcpy.management.Append(proj_pts, ptsURL, "NO_TEST")
            
    else:
        # Catch all if the intersect query returns false. Just Append the new data.
        if fldmapping != '':
            arcpy.management.Append(proj_fc, up_RESTurl, "NO_TEST", fldmapping)
        else:
            arcpy.management.Append(proj_fc, up_RESTurl, "NO_TEST")
        if proj_pts != '':
            if fldmapping != '':
                arcpy.management.Append(proj_pts, ptsURL, "NO_TEST", fldmapping)
            else:
                arcpy.management.Append(proj_pts, ptsURL, "NO_TEST")

    files_to_del = [int_fc, test_fc, local_temp, pts_temp]
    for item in files_to_del:
        try:
            arcpy.management.Delete(item)
        except:
            pass

##    except:
##        AddMsgAndPrint("\nSomething went wrong during upload of " + proj_fc + "!. Exiting...",2)
##        exit()

## ===============================================================================================================
def update_polys(up_ws, up_temp_dir, proj_fc, up_RESTurl, local_temp, fldmapping=''):
## Queries polygon layer for intersects. If none found, appends proceed.
## If intersection is found, query returns the geometry for local processing to split the old areas from the new.
## Once local processing is complete the two pieces are put through Delete intersect and then re-uploaded.
    
##    try:
    # set variables
    int_fc = up_ws + os.sep + "int_fc"
    test_fc = up_ws + os.sep + "test_fc"

    # Manage the local_temp file in case of previous run of tool that had an error or crashed
    if arcpy.Exists(local_temp):
        # Query local temp against the server to see if data is still there. If nothing returned,
        # then append the local temp to the server to restore "deleted" features
        overlapCheck = queryIntersect(up_ws, up_temp_dir, local_temp, up_RESTurl, int_fc)
        if arcpy.Exists(int_fc):
            # Do another intersect to see if there is actual overlap and not just coincident edges
            arcpy.analysis.Intersect([local_temp,overlapCheck], test_fc, "NO_FID", "#", "INPUT")
            if int(arcpy.GetCount_management(test_fc).getOutput(0)) == 0:
                # Features were lost from the server. Restore the local_temp onto the server without the field mapping setting (not needed)
                # Then delete local temps
                arcpy.management.Append(local_temp, up_RESTurl, "NO_TEST")
                arcpy.management.Delete(local_temp)
                arcpy.management.Delete(test_fc)
                arcpy.management.Delete(int_fc)
            else:
                # Server features take precedence. Delete local_temp. It will be re-created, if needed, in the next step.
                arcpy.management.Delete(local_temp)
                arcpy.management.Delete(test_fc)
                arcpy.management.Delete(int_fc)
        else:
            # Server features take precedence. Delete local_temp. It will be re-created, if needed, in the next step.
            arcpy.management.Delete(local_temp)
            
    # Check whether the input project area data overlaps anything on the server
    test_results = queryIntersect(up_ws, up_temp_dir, proj_fc, up_RESTurl, int_fc)
    if arcpy.Exists(int_fc):
        # Do another intersect to see if there is actual overlap and not just coincident edges
        arcpy.analysis.Intersect([proj_fc,test_results], test_fc, "NO_FID", "#", "INPUT")
        if int(arcpy.GetCount_management(test_fc).getOutput(0)) > 0:
            ## Features found. Process the geometry changes locally to prep layers for upload.
            # Use the proj_fc to erase overlapping area from the downloaded polygons and check results
            arcpy.analysis.Erase(test_results, proj_fc, poly_multi)
            result = int(arcpy.management.GetCount(poly_multi).getOutput(0))
            if result > 0:
                # Not a 100% replace. Change to single part and update acres
                arcpy.management.MultipartToSinglepart(poly_multi, poly_single)
                expression = "round(!Shape.Area@acres!,2)"
                arcpy.management.CalculateField(poly_single, "acres", expression, "PYTHON_9.3")
                del expression
                # Copy the residual features to the local temp layer to be used in re-upload later in the process
                arcpy.management.CopyFeatures(poly_single, local_temp)

                # Overlaps exist between new features and remnant features. Do deletes and then uploads of both.
                del_by_intersect(up_ws, up_temp_dir, proj_fc, up_RESTurl)
                arcpy.management.Append(local_temp, up_RESTurl, "NO_TEST")
                if fldmapping != '':
                    arcpy.management.Append(proj_fc, up_RESTurl, "NO_TEST", fldmapping)
                else:
                    arcpy.management.Append(proj_fc, up_RESTurl, "NO_TEST")
            else:
                # A 100% replace, delete and then do uploads of new features, without remnant features
                del_by_intersect(up_ws, up_temp_dir, proj_fc, up_RESTurl)
                if fldmapping != '':
                    arcpy.management.Append(proj_fc, up_RESTurl, "NO_TEST", fldmapping)
                else:
                    arcpy.management.Append(proj_fc, up_RESTurl, "NO_TEST")
        else:
            # No actual overlaps, probably just touching edges. Do the standard upload with no deletes.
            if fldmapping != '':
                arcpy.management.Append(proj_fc, up_RESTurl, "NO_TEST", fldmapping)
            else:
                arcpy.management.Append(proj_fc, up_RESTurl, "NO_TEST")
    else:
        # Catch all if the intersect query returns false. Just Append the new data.
        if fldmapping != '':
            arcpy.management.Append(proj_fc, up_RESTurl, "NO_TEST", fldmapping)
        else:
            arcpy.management.Append(proj_fc, up_RESTurl, "NO_TEST")

    files_to_del = [int_fc, test_fc, local_temp]
    for item in files_to_del:
        try:
            arcpy.management.Delete(item)
        except:
            pass

##    except:
##        AddMsgAndPrint("\nSomething went wrong during upload of " + proj_fc + "!. Exiting...",2)
##        exit()
        
#### ===============================================================================================================
##def update_polys(up_ws, up_temp_dir, proj_fc, up_RESTurl, local_temp, fldmapping=''):
#### Queries polygon layer for intersects. If none found, appends proceed.
#### If intersection is found, query returns the geometry for local processing to split the old areas from the new.
#### Once local processing is complete the two pieces are put through Delete intersect and then re-uploaded.
##    
####    try:
##    # set variables
##    int_fc = up_ws + os.sep + "int_fc"
##    test_fc = up_ws + os.sep + "test_fc"
##
##    # Manage the local_temp file in case of previous run of tool that had an error or crashed
##    if arcpy.Exists(local_temp):
##        # Query local temp against the server to see if data is still there. If nothing returned,
##        # then append the local temp to the server to restore "deleted" features
##        overlapCheck = queryIntersect(up_ws, up_temp_dir, local_temp, up_RESTurl, int_fc)
##        if overlapCheck == False:
##            # Restore the local_temp onto the server without the field mapping setting (not needed)
##            arcpy.management.Append(local_temp, up_RESTurl, "NO_TEST")
##            arcpy.management.Delete(local_temp)
##        else:
##            # Server features take precedence. Delete local_temp. It will be re-created, if needed, in the next step.
##            arcpy.management.Delete(local_temp)
##            arcpy.management.Delete(int_fc)
##
##    # Check whether the input project area data overlaps anything on the server
##    test_results = queryIntersect(up_ws, up_temp_dir, proj_fc, up_RESTurl, int_fc)
##    if arcpy.Exists(int_fc):
##        ## Features found. Process the geometry changes locally to prep layers for upload.
##        # Use the proj_fc to erase overlapping area from the downloaded polygons and check results
##        arcpy.analysis.Erase(test_results, proj_fc, poly_multi)
##        result = int(arcpy.management.GetCount(poly_multi).getOutput(0))
##        if result > 0:
##            # Not a 100% replace. Change to single part and update acres
##            arcpy.management.MultipartToSinglepart(poly_multi, poly_single)
##            expression = "round(!Shape.Area@acres!,2)"
##            arcpy.management.CalculateField(poly_single, "acres", expression, "PYTHON_9.3")
##            del expression
##            # Copy the residual features to the local temp layer to be used in re-upload later in the process
##            arcpy.management.CopyFeatures(poly_single, local_temp)
##
##    ## Handle uploads
##    if arcpy.Exists(int_fc):
##        # Overlaps exist. First delete server features that overlap the project area
##        del_by_intersect(up_ws, up_temp_dir, proj_fc, up_RESTurl)
##
##        # Restore remnant local temp copy of server features (around the new data)
##        arcpy.management.Append(local_temp, up_RESTurl, "NO_TEST")
##        arcpy.management.Delete(local_temp)
##
##        #Do append of current project data
##        if fldmapping != '':
##            arcpy.management.Append(proj_fc, up_RESTurl, "NO_TEST", fldmapping)
##        else:
##            arcpy.management.Append(proj_fc, up_RESTurl, "NO_TEST")
##
##        arcpy.management.Delete(int_fc)
##        
##    else:
##        # No overlaps, just Append the new data.
##        if fldmapping != '':
##            arcpy.management.Append(proj_fc, up_RESTurl, "NO_TEST", fldmapping)
##        else:
##            arcpy.management.Append(proj_fc, up_RESTurl, "NO_TEST")
##
##    files_to_del = [int_fc, test_fc, local_temp]
##    for item in files_to_del:
##        try:
##            arcpy.management.Delete(item)
##        except:
##            pass
##        
####    except:
####        AddMsgAndPrint("\nSomething went wrong during upload of " + proj_fc + "!. Exiting...",2)
####        exit()

#### ===============================================================================================================
##def replace_pts_by_area(up_ws, up_temp_dir, proj_fc, area_fc, up_RESTurl, fldmapping=''):
#### This function will check for intersect of the area_fc via queryIntersect function.
#### If features are returned by the queryIntersect, a delete using the area_fc is called.
#### After deleting intersecting data OR finding no intersecting data, it will append the new data to the target HFS
##    
##    try:
##        # set variables
##        int_fc = up_ws + os.sep + "int_fc"
##        
##        # Check whether the input data overlaps anything on the server
##        test_results = queryIntersect(up_ws, up_temp_dir, area_fc, up_RESTurl, int_fc)
##        if test_results != False:
##            # Features found. Delete by intersect and then append
##            del_by_intersect(up_ws, up_temp_dir, area_fc, up_RESTurl)
##            arcpy.management.Delete(test_results)
##            if fldmapping != '':
##                arcpy.Append_management(proj_fc, up_RESTurl, "NO_TEST", fldmapping)
##            else:
##                arcpy.Append_management(proj_fc, up_RESTurl, "NO_TEST")
##        else:
##            # Features not found. Append
##            if fldmapping != '':
##                arcpy.Append_management(proj_fc, up_RESTurl, "NO_TEST", fldmapping)
##            else:
##                arcpy.Append_management(proj_fc, up_RESTurl, "NO_TEST")
##
##    except:
##        AddMsgAndPrint("\nSomething went wrong during upload of " + proj_fc + "!. Exiting...",2)
##        exit()
##        
## ===============================================================================================================
#### Import system modules
import arcpy, sys, os, traceback, re, shutil, csv
from importlib import reload
import urllib, time, json, random
from urllib.request import Request, urlopen
from urllib.error import HTTPError as httpErrors
urllibEncode = urllib.parse.urlencode
parseQueryString = urllib.parse.parse_qsl

sys.dont_write_bytecode=True
scriptPath = os.path.dirname(sys.argv[0])
sys.path.append(scriptPath)

from wetland_utils import getPortalTokenInfo


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


#### Check GeoPortal Connection
#nrcsPortal = 'https://gis.sc.egov.usda.gov/portal/'     # GeoPortal Production 10.8.1
#if not portalToken:
#arcpy.AddError("Could not generate Portal token! Please login or switch active portal to GeoPortal 10.8.1! Exiting...")
#exit()
    
#nrcsPortal = 'https://gis-states.sc.egov.usda.gov/portal/'     # GeoPortal States Production 10.8.1
#if not portalToken:
#arcpy.AddError("Could not generate Portal token! Please login or switch active portal to GeoPortal States 10.8.1! Exiting...")
#exit()

nrcsPortal = 'https://gis-testing.usda.net/portal/'     # GeoPortal Sandbox Testing 10.8.1
portalToken = getPortalTokenInfo(nrcsPortal)
if not portalToken:
    arcpy.AddError("Could not generate Portal token! Please login or switch active portal to GIS-Testing 10.8.1! Exiting...")
    exit()
    

#### Main procedures
try:
    #### Inputs
    arcpy.AddMessage("Reading inputs...\n")
    sourceCWD = arcpy.GetParameterAsText(0)
    ext_HFS = arcpy.GetParameterAsText(1)
    extA_HFS = arcpy.GetParameterAsText(2)
    su_HFS = arcpy.GetParameterAsText(3)
    suA_HFS = arcpy.GetParameterAsText(4)
    rop_HFS = arcpy.GetParameterAsText(5)
    ropA_HFS = arcpy.GetParameterAsText(6)
    rp_HFS = arcpy.GetParameterAsText(7)
    rpA_HFS = arcpy.GetParameterAsText(8)
    drains_HFS = arcpy.GetParameterAsText(9)
    drainsA_HFS = arcpy.GetParameterAsText(10)
    cwd_HFS = arcpy.GetParameterAsText(11)
    cwdA_HFS = arcpy.GetParameterAsText(12)
    pjw_HFS = arcpy.GetParameterAsText(13)
    pjwA_HFS = arcpy.GetParameterAsText(14)
    clucwd_HFS = arcpy.GetParameterAsText(15)
    clucwdA_HFS = arcpy.GetParameterAsText(16)
    reqpts_HFS = arcpy.GetParameterAsText(17)
    reqptsA_HFS = arcpy.GetParameterAsText(18)
    clucwdpts_HFS = arcpy.GetParameterAsText(19)
    clucwdptsA_HFS = arcpy.GetParameterAsText(20)
    

    #### Initial Validations
    arcpy.AddMessage("Verifying inputs...\n")
    arcpy.SetProgressorLabel("Verifying inputs...")
    
                
    #### Set base path
    sourceCWD_path = arcpy.Describe(sourceCWD).CatalogPath
    if sourceCWD_path.find('.gdb') > 0 and sourceCWD_path.find('Determinations') > 0 and sourceCWD_path.find('Site_CWD') > 0:
        wcGDB_path = sourceCWD_path[:sourceCWD_path.find('.gdb')+4]
    else:
        arcpy.AddError("\nSelected CWD layer is not from a Determinations project folder. Exiting...")
        exit()


    #### Define Variables
    arcpy.AddMessage("Setting variables...\n")
    arcpy.SetProgressorLabel("VSetting variables...")
    supportGDB = os.path.join(os.path.dirname(sys.argv[0]), "SUPPORT.gdb")
    scratchGDB = os.path.join(os.path.dirname(sys.argv[0]), "SCRATCH.gdb")

    wetDir = os.path.dirname(wcGDB_path)
    userWorkspace = os.path.dirname(wetDir)
    projectName = os.path.basename(userWorkspace).replace(" ", "_")
    
    wcGDB_name = os.path.basename(userWorkspace).replace(" ", "_") + "_WC.gdb"
    wcGDB_path = wetDir + os.sep + wcGDB_name
    wcFD_name = "WC_Data"
    wcFD = wcGDB_path + os.sep + wcFD_name
    
    basedataGDB_path = userWorkspace + os.sep + projectName + "_BaseData.gdb"
    basedataGDB_name = os.path.basename(basedataGDB_path)
    basedataFD_name = "Layers"
    basedataFD = basedataGDB_path + os.sep + basedataFD_name

    projectTable = basedataGDB_path + os.sep + "Table_" + projectName
    wetDetTableName = "Admin_Table"
    wetDetTable = wcGDB_path + os.sep + wetDetTableName
    
    extentName = "Request_Extent"
    extentPtsName = "Request_Extent_Points"
    projectExtent = basedataFD + os.sep + extentName
    projectSum = basedataFD + os.sep + "Det_Summary_Areas"
    projectSumPts = basedataFD + os.sep + "Det_Summary_Points"
#    extPoints = basedataFD + os.sep + extentPtsName
    ext_server_copy = wcFD + os.sep + "Sum_Server"
    
    suName = "Site_Sampling_Units"
    projectSU = wcFD + os.sep + suName
    su_server_copy = wcFD + os.sep + "SU_Server"

    drainName = "Site_Drainage_Lines"
    projectLines = wcFD + os.sep + drainName

    ropName = "Site_ROPs"
    projectROP = wcFD + os.sep + ropName

    refName = "Site_Reference_Points"
    projectREF = wcFD + os.sep + refName
    
    cwdName = "Site_CWD"
    projectCWD = wcFD + os.sep + cwdName
    #projectCWD_pts = wcFD + os.sep + "Site_CWD_Points"
    #cwd_pub_name = "Publish_CWD"
    #publishCWD = wcFD + os.sep + cwd_pub_name
    cwd_server_copy = wcFD + os.sep + "CWD_Server"

    pjwName = "Site_PJW"
    projectPJW = wcFD + os.sep + pjwName

    cluCwdName = "Site_CLU_CWD"
    cluCwdPtsName = "Site_CLU_CWD_Points"
    projectCLUCWD = wcFD + os.sep + cluCwdName
    cluCWDpts = wcFD + os.sep + cluCwdPtsName
    clucwd_server_copy = wcFD + os.sep + "CLUCWD_Server"

    poly_multi = scratchGDB + os.sep + "poly_multi"
    poly_single = scratchGDB + os.sep + "poly_single"

    # Temp layers list for cleanup at the start and at the end
    tempLayers = [poly_multi, poly_single]
    #deleteTempLayers(tempLayers)


    #### Set up log file path and start logging
    arcpy.AddMessage("Commence logging...\n")
    textFilePath = userWorkspace + os.sep + projectName + "_log.txt"
    logBasicSettings()

        
    #### Check Project Integrity
    AddMsgAndPrint("\nChecking project integrity...",0)
    arcpy.SetProgressorLabel("Checking project integrity...")

    # If project wetlands geodatabase and feature dataset do not exist, exit.
    if not arcpy.Exists(wcGDB_path):
        AddMsgAndPrint("\tInput Site CWD layer is not part of a wetlands tool project folder. Exiting...",2)
        exit()

    if not arcpy.Exists(wcFD):
        AddMsgAndPrint("\tInput Site CWD layer is not part of a wetlands tool project folder. Exiting...",2)
        exit()


    #### Count the features of the input layers.
    # Extent, SU, ROP, CWD, and CLUCWD must have at least 1 feature, else exit.
    if not arcpy.Exists(projectSum):
        AddMsgAndPrint("\tSummary Extents layer does not exist. Re-run Create CWD Mapping Layers. Exiting...",2)
        exit()
    else:
        ext_count = int(arcpy.management.GetCount(projectSum)[0])

    if not arcpy.Exists(projectSumPts):
        AddMsgAndPrint("\tSummary Extent Points layer does not exist. Re-run Create CWD Mapping Layers. Exiting...",2)
        exit()
    else:
        ext_pts_count = int(arcpy.management.GetCount(projectSumPts)[0])

    if not arcpy.Exists(projectSU):
        AddMsgAndPrint("\tSampling Units layer does not exist. Exiting...",2)
        exit()
    else:
        su_count = int(arcpy.management.GetCount(projectSU)[0])
        
    if not arcpy.Exists(projectROP):
        AddMsgAndPrint("\tROPs layer does not exist. Exiting...",2)
        exit()
    else:
        rop_count = int(arcpy.management.GetCount(projectROP)[0])

    if not arcpy.Exists(projectLines):
        AddMsgAndPrint("\tDrainage Lines layer does not exist. Exiting...",2)
        exit()
    else:
        dl_count = int(arcpy.management.GetCount(projectLines)[0])

    if not arcpy.Exists(projectREF):
        AddMsgAndPrint("\tReference Points layer does not exist. Exiting...",2)
        exit()
    else:
        ref_count = int(arcpy.management.GetCount(projectREF)[0])

    if not arcpy.Exists(projectPJW):
        AddMsgAndPrint("\tPJW layer does not exist. Exiting...",2)
        exit()
    else:
        pjw_count = int(arcpy.management.GetCount(projectPJW)[0])

    if not arcpy.Exists(projectCWD):
        AddMsgAndPrint("\tCWD layer does not exist. Exiting...",2)
        exit()
    else:
        cwd_count = int(arcpy.management.GetCount(projectCWD)[0])

    if not arcpy.Exists(projectCLUCWD):
        AddMsgAndPrint("\tCLU CWD layer does not exist. Exiting...",2)
        exit()
    else:
        clucwd_count = int(arcpy.management.GetCount(projectCLUCWD)[0])

    if not arcpy.Exists(cluCWDpts):
        AddMsgAndPrint("\tCLU CWD Points layer does not exist. Re-run Create CWD Mapping Layers. Exiting...",2)
        exit()
    else:
        clucwd_count = int(arcpy.management.GetCount(cluCWDpts)[0])

    if ext_count == 0 or su_count == 0 or rop_count == 0 or cwd_count == 0 or clucwd_count == 0:
        AddMsgAndPrint("\tOne or more critical business layers contains no feature data. Please complete the entire workflow prior to upload.",2)
        AddMsgAndPrint("\tRequest Extent: " + str(ext_count) + " features.",2)
        AddMsgAndPrint("\tSampling Units: " + str(su_count) + " features.",2)
        AddMsgAndPrint("\tROPs: " + str(rop_count) + " features.",2)
        AddMsgAndPrint("\tCWD: " + str(cwd_count) + " features.",2)
        AddMsgAndPrint("\tCLU CWD: " + str(clucwd_count) + " features.",2)
        AddMsgAndPrint("\tExiting...",2)
        exit()

    
    #### Get the current job_id for use in processing
    cur_id = ''
    fields = ['job_id']
    cursor = arcpy.da.SearchCursor(wetDetTable, fields)
    for row in cursor:
        cur_id = row[0]
        break
    del cursor, fields

    if cur_id == '':
        AddMsgAndPrint("\tJob_ID could not be retrieved from admin table. Exiting...",2)
        exit()

    # Build a query out of the job_id
    job_query = "job_id = '" + cur_id + "'"
    

    #### Build field mapping objects that will be needed
    AddMsgAndPrint("\nBuilding field mappings...",0)
    arcpy.SetProgressorLabel("Building field mappings...")
    field_mapping_cwd_to_hfs="globalid \"GlobalID\" false false true 38 GlobalID 0 0,First,#,Site_CWD,GlobalID,-1,-1;job_id \"Job ID\" true true false 128 Text 0 0,First,#,Site_CWD,job_id,0,128;admin_state \"Admin State\" true true false 2 Text 0 0,First,#,Site_CWD,admin_state,0,2;admin_state_name \"Admin State Name\" true true false 64 Text 0 0,First,#,Site_CWD,admin_state_name,0,64;admin_county \"Admin County\" true true false 3 Text 0 0,First,#,Site_CWD,admin_county,0,3;admin_county_name \"Admin County Name\" true true false 64 Text 0 0,First,#,Site_CWD,admin_county_name,0,64;state_code \"State Code\" true true false 2 Text 0 0,First,#,Site_CWD,state_code,0,2;state_name \"State Name\" true true false 64 Text 0 0,First,#,Site_CWD,state_name,0,64;county_code \"County Code\" true true false 3 Text 0 0,First,#,Site_CWD,county_code,0,3;county_name \"County Name\" true true false 64 Text 0 0,First,#,Site_CWD,county_name,0,64;farm_number \"Farm Number\" true true false 7 Text 0 0,First,#,Site_CWD,farm_number,0,7;tract_number \"Tract Number\" true true false 7 Text 0 0,First,#,Site_CWD,tract_number,0,7;eval_status \"Evaluation Status\" true true false 24 Text 0 0,First,#,Site_CWD,eval_status,0,24;wetland_label \"Wetland Label\" true true false 12 Text 0 0,First,#,Site_CWD,wetland_label,0,12;occur_year \"Occurrence Year\" true true false 4 Text 0 0,First,#,Site_CWD,occur_year,0,4;acres \"Acres\" true true false 0 Double 0 0,First,#,Site_CWD,acres,-1,-1;three_factors \"3-Factors\" true true false 1 Text 0 0,First,#,Site_CWD,three_factors,0,1;request_date \"Request Date\" true true false 29 Date 0 0,First,#,Site_CWD,request_date,-1,-1;request_type \"Request Type\" true true false 12 Text 0 0,First,#,Site_CWD,request_type,0,12;deter_method \"Determination Method\" true true false 24 Text 0 0,First,#,Site_CWD,deter_method,0,24;deter_staff \"Determination Staff\" true true false 100 Text 0 0,First,#,Site_CWD,deter_staff,0,100;dig_staff \"Digitizing Staff\" true true false 100 Text 0 0,First,#,Site_CWD,dig_staff,0,100;dig_date \"Digitizing Date\" true true false 29 Date 0 0,First,#,Site_CWD,dig_date,-1,-1;cwd_comments \"Comments\" true true false 255 Text 0 0,First,#,Site_CWD,cwd_comments,0,255;cert_date \"Certification Date\" true true false 0 Double 0 0,First,#,Site_CWD,cert_date,-1,-1"
    field_mapping_su_to_hfs="globalid \"GlobalID\" false false false 38 GlobalID 0 0,First,#,Site_Sampling_Units,GlobalID,-1,-1;job_id \"Job ID\" true true false 128 Text 0 0,First,#,Site_Sampling_Units,job_id,0,128;admin_state \"Admin State\" true true false 2 Text 0 0,First,#,Site_Sampling_Units,admin_state,0,2;admin_state_name \"Admin State Name\" true true false 64 Text 0 0,First,#,Site_Sampling_Units,admin_state_name,0,64;admin_county \"Admin County\" true true false 3 Text 0 0,First,#,Site_Sampling_Units,admin_county,0,3;admin_county_name \"Admin County Name\" true true false 64 Text 0 0,First,#,Site_Sampling_Units,admin_county_name,0,64;state_code \"State Code\" true true false 2 Text 0 0,First,#,Site_Sampling_Units,state_code,0,2;state_name \"State Name\" true true false 64 Text 0 0,First,#,Site_Sampling_Units,state_name,0,64;county_code \"County Code\" true true false 3 Text 0 0,First,#,Site_Sampling_Units,county_code,0,3;county_name \"County Name\" true true false 64 Text 0 0,First,#,Site_Sampling_Units,county_name,0,64;farm_number \"Farm Number\" true true false 7 Text 0 0,First,#,Site_Sampling_Units,farm_number,0,7;tract_number \"Tract Number\" true true false 7 Text 0 0,First,#,Site_Sampling_Units,tract_number,0,7;eval_status \"Evaluation Status\" true true false 24 Text 0 0,First,#,Site_Sampling_Units,eval_status,0,24;su_number \"Sampling Unit Number\" true true false 0 Long 0 0,First,#,Site_Sampling_Units,su_number,-1,-1;su_letter \"Sampling Unit Letter\" true true false 3 Text 0 0,First,#,Site_Sampling_Units,su_letter,0,3;acres \"Acres\" true true false 0 Double 0 0,First,#,Site_Sampling_Units,acres,-1,-1;associated_rop \"Associated ROP\" true true false 0 Long 0 0,First,#,Site_Sampling_Units,associated_rop,-1,-1;associated_ref \"Associated Reference Points\" true true false 255 Text 0 0,First,#,Site_Sampling_Units,associated_ref,0,255;three_factors \"3-Factors?\" true true false 1 Text 0 0,First,#,Site_Sampling_Units,three_factors,0,1;request_date \"Request_Date\" true true false 29 Date 0 0,First,#,Site_Sampling_Units,request_date,-1,-1;request_type \"Request Type\" true true false 24 Text 0 0,First,#,Site_Sampling_Units,request_type,0,24;deter_method \"Determination Method\" true true false 24 Text 0 0,First,#,Site_Sampling_Units,deter_method,0,24;deter_staff \"Determination Staff\" true true false 100 Text 0 0,First,#,Site_Sampling_Units,deter_staff,0,100;dig_staff \"Digitizing Staff\" true true false 100 Text 0 0,First,#,Site_Sampling_Units,dig_staff,0,100;dig_date \"Digitizing Date\" true true false 29 Date 0 0,First,#,Site_Sampling_Units,dig_date,-1,-1;su_comments \"Comments\" true true false 255 Text 0 0,First,#,Site_Sampling_Units,su_comments,0,255"
    field_mapping_rop_to_hfs="globalid \"GlobalID\" false false false 38 GlobalID 0 0,First,#,Site_ROPs,GlobalID,-1,-1;job_id \"Job ID\" true true false 128 Text 0 0,First,#,Site_ROPs,job_id,0,128;admin_state \"Admin State\" true true false 2 Text 0 0,First,#,Site_ROPs,admin_state,0,2;admin_state_name \"Admin State Name\" true true false 64 Text 0 0,First,#,Site_ROPs,admin_state_name,0,64;admin_county \"Admin County\" true true false 3 Text 0 0,First,#,Site_ROPs,admin_county,0,3;admin_county_name \"Admin County Name\" true true false 64 Text 0 0,First,#,Site_ROPs,admin_county_name,0,64;state_code \"State Code\" true true false 2 Text 0 0,First,#,Site_ROPs,state_code,0,2;state_name \"State Name\" true true false 64 Text 0 0,First,#,Site_ROPs,state_name,0,64;county_code \"County Code\" true true false 3 Text 0 0,First,#,Site_ROPs,county_code,0,3;county_name \"County Name\" true true false 64 Text 0 0,First,#,Site_ROPs,county_name,0,64;farm_number \"Farm Number\" true true false 7 Text 0 0,First,#,Site_ROPs,farm_number,0,7;tract_number \"Tract Number\" true true false 7 Text 0 0,First,#,Site_ROPs,tract_number,0,7;rop_number \"ROP Number\" true true false 0 Long 0 0,First,#,Site_ROPs,rop_number,-1,-1;associated_su \"Associated Sampling Units\" true true false 255 Text 0 0,First,#,Site_ROPs,associated_su,0,255;rop_comments \"Comments\" true true false 255 Text 0 0,First,#,Site_ROPs,rop_comments,0,255"
    field_mapping_ref_to_hfs="globalid \"GlobalID\" false false false 38 GlobalID 0 0,First,#,Site_Reference_Points,GlobalID,-1,-1;job_id \"Job ID\" true true false 128 Text 0 0,First,#,Site_Reference_Points,job_id,0,128;admin_state \"Admin State\" true true false 2 Text 0 0,First,#,Site_Reference_Points,admin_state,0,2;admin_state_name \"Admin State Name\" true true false 64 Text 0 0,First,#,Site_Reference_Points,admin_state_name,0,64;admin_county \"Admin County\" true true false 3 Text 0 0,First,#,Site_Reference_Points,admin_county,0,3;admin_county_name \"Admin County Name\" true true false 64 Text 0 0,First,#,Site_Reference_Points,admin_county_name,0,64;state_code \"State Code\" true true false 2 Text 0 0,First,#,Site_Reference_Points,state_code,0,2;state_name \"State Name\" true true false 64 Text 0 0,First,#,Site_Reference_Points,state_name,0,64;county_code \"County Code\" true true false 3 Text 0 0,First,#,Site_Reference_Points,county_code,0,3;county_name \"County Name\" true true false 64 Text 0 0,First,#,Site_Reference_Points,county_name,0,64;farm_number \"Farm Number\" true true false 7 Text 0 0,First,#,Site_Reference_Points,farm_number,0,7;tract_number \"Tract Number\" true true false 7 Text 0 0,First,#,Site_Reference_Points,tract_number,0,7;ref_number \"Reference Point Number\" true true false 0 Long 0 0,First,#,Site_Reference_Points,ref_number,-1,-1;parent_rop \"Parent ROP\" true true false 0 Long 0 0,First,#,Site_Reference_Points,parent_rop,-1,-1;hydro \"Documents Hydrology?\" true true false 3 Text 0 0,First,#,Site_Reference_Points,hydro,0,3;veg \"Documents Vegetation?\" true true false 3 Text 0 0,First,#,Site_Reference_Points,veg,0,3;soil \"Documents Soil?\" true true false 3 Text 0 0,First,#,Site_Reference_Points,soil,0,3;ref_comments \"Comments\" true true false 255 Text 0 0,First,#,Site_Reference_Points,ref_comments,0,255"
    field_mapping_dl_to_hfs="globalid \"GlobalID\" false false false 38 GlobalID 0 0,First,#,Site_Drainage_Lines,GlobalID,-1,-1;job_id \"Job ID\" true true false 128 Text 0 0,First,#,Site_Drainage_Lines,job_id,0,128;admin_state \"Admin State\" true true false 2 Text 0 0,First,#,Site_Drainage_Lines,admin_state,0,2;admin_state_name \"Admin State Name\" true true false 64 Text 0 0,First,#,Site_Drainage_Lines,admin_state_name,0,64;admin_county \"Admin County\" true true false 3 Text 0 0,First,#,Site_Drainage_Lines,admin_county,0,3;admin_county_name \"Admin County Name\" true true false 64 Text 0 0,First,#,Site_Drainage_Lines,admin_county_name,0,64;state_code \"State Code\" true true false 2 Text 0 0,First,#,Site_Drainage_Lines,state_code,0,2;state_name \"State Name\" true true false 64 Text 0 0,First,#,Site_Drainage_Lines,state_name,0,64;county_code \"County Code\" true true false 3 Text 0 0,First,#,Site_Drainage_Lines,county_code,0,3;county_name \"County Name\" true true false 64 Text 0 0,First,#,Site_Drainage_Lines,county_name,0,64;farm_number \"Farm Number\" true true false 7 Text 0 0,First,#,Site_Drainage_Lines,farm_number,0,7;tract_number \"Tract Number\" true true false 7 Text 0 0,First,#,Site_Drainage_Lines,tract_number,0,7;line_type \"Line Type\" true true false 50 Text 0 0,First,#,Site_Drainage_Lines,line_type,0,50;manip_era \"Era\" true true false 12 Text 0 0,First,#,Site_Drainage_Lines,manip_era,0,12;manip_year \"Manipulation Year\" true true false 4 Text 0 0,First,#,Site_Drainage_Lines,manip_year,0,4;line_length \"Length (ft)\" true true false 0 Double 0 0,First,#,Site_Drainage_Lines,line_length,-1,-1;depth \"Depth (ft)\" true true false 0 Double 0 0,First,#,Site_Drainage_Lines,depth,-1,-1;width \"Width (ft)\" true true false 0 Double 0 0,First,#,Site_Drainage_Lines,width,-1,-1;drain_comments \"Comments\" true true false 255 Text 0 0,First,#,Site_Drainage_Lines,drain_comments,0,255"
    field_mapping_clucwd_to_hfs="globalid \"GlobalID\" false false false 38 GlobalID 0 0,First,#,Site_CLU_CWD,GlobalID,-1,-1;job_id \"Job ID\" true true false 128 Text 0 0,First,#,Site_CLU_CWD,job_id,0,128;admin_state \"Admin State\" true true false 2 Text 0 0,First,#,Site_CLU_CWD,admin_state,0,2;admin_state_name \"Admin State Name\" true true false 64 Text 0 0,First,#,Site_CLU_CWD,admin_state_name,0,64;admin_county \"Admin County\" true true false 3 Text 0 0,First,#,Site_CLU_CWD,admin_county,0,3;admin_county_name \"Admin County Name\" true true false 64 Text 0 0,First,#,Site_CLU_CWD,admin_county_name,0,64;state_code \"State Code\" true true false 2 Text 0 0,First,#,Site_CLU_CWD,state_code,0,2;state_name \"State Name\" true true false 64 Text 0 0,First,#,Site_CLU_CWD,state_name,0,64;county_code \"County Code\" true true false 3 Text 0 0,First,#,Site_CLU_CWD,county_code,0,3;county_name \"County Name\" true true false 64 Text 0 0,First,#,Site_CLU_CWD,county_name,0,64;farm_number \"Farm Number\" true true false 7 Text 0 0,First,#,Site_CLU_CWD,farm_number,0,7;tract_number \"Tract Number\" true true false 7 Text 0 0,First,#,Site_CLU_CWD,tract_number,0,7;clu_number \"CLU Number\" true true false 7 Text 0 0,First,#,Site_CLU_CWD,clu_number,0,7;eval_status \"Evaluation Status\" true true false 24 Text 0 0,First,#,Site_CLU_CWD,eval_status,0,24;wetland_label \"Wetland Label\" true true false 12 Text 0 0,First,#,Site_CLU_CWD,wetland_label,0,12;occur_year \"Occurrence Year\" true true false 4 Text 0 0,First,#,Site_CLU_CWD,occur_year,0,4;acres \"Acres\" true true false 0 Double 0 0,First,#,Site_CLU_CWD,acres,-1,-1;three_factors \"3-Factors\" true true false 1 Text 0 0,First,#,Site_CLU_CWD,three_factors,0,1;request_date \"Request Date\" true true false 29 Date 0 0,First,#,Site_CLU_CWD,request_date,-1,-1;request_type \"Request Type\" true true false 12 Text 0 0,First,#,Site_CLU_CWD,request_type,0,12;deter_method \"Determination Method\" true true false 24 Text 0 0,First,#,Site_CLU_CWD,deter_method,0,24;deter_staff \"Determination Staff\" true true false 100 Text 0 0,First,#,Site_CLU_CWD,deter_staff,0,100;dig_staff \"Digitizing Staff\" true true false 100 Text 0 0,First,#,Site_CLU_CWD,dig_staff,0,100;dig_date \"Digitizing Date\" true true false 29 Date 0 0,First,#,Site_CLU_CWD,dig_date,-1,-1;clucwd_comments \"Comments\" true true false 255 Text 0 0,First,#,Site_CLU_CWD,clucwd_comments,0,255;cert_date \"Certification Date\" true true false 29 Date 0 0,First,#,Site_CLU_CWD,cert_date,-1,-1"


    #### Find features with matching job ids and delete them
    AddMsgAndPrint("\nProcessing matching JobIDs...",0)
    arcpy.SetProgressorLabel("Processing matching JobIDs...")

    AddMsgAndPrint("\nProcessing Matching Request Extents in Archive...",0)
    arcpy.SetProgressorLabel("Processing Matching Request Extents in Archive...")
    del_by_attributes(job_query, extA_HFS)

    AddMsgAndPrint("\nProcessing Matching Request Extents on Live...",0)
    arcpy.SetProgressorLabel("Processing Matching Request Extents on Live...")
    del_by_attributes(job_query, ext_HFS)

    AddMsgAndPrint("\nProcessing Matching Request Extent Points in Archive...",0)
    arcpy.SetProgressorLabel("Processing Matching Request Extent Points in Archive...")
    del_by_attributes(job_query, reqptsA_HFS)

    AddMsgAndPrint("\nProcessing Matching Request Extent Points on Live...",0)
    arcpy.SetProgressorLabel("Processing Matching Request Extent Points on Live...")
    del_by_attributes(job_query, reqpts_HFS)
    
    del_by_attributes(job_query, suA_HFS)
    del_by_attributes(job_query, su_HFS)
    del_by_attributes(job_query, ropA_HFS)
    del_by_attributes(job_query, rop_HFS)
    del_by_attributes(job_query, cwdA_HFS)
    del_by_attributes(job_query, cwd_HFS)
    del_by_attributes(job_query, clucwdA_HFS)
    del_by_attributes(job_query, clucwd_HFS)
    del_by_attributes(job_query, clucwdptsA_HFS)
    del_by_attributes(job_query, clucwdpts_HFS)
    if ref_count > 0:
        del_by_attributes(job_query, rpA_HFS)
        del_by_attributes(job_query, rp_HFS)
    if dl_count > 0:
        del_by_attributes(job_query, drainsA_HFS)
        del_by_attributes(job_query, drains_HFS)
    if pjw_count > 0:
        del_by_attributes(job_query, pjwA_HFS)
        del_by_attributes(job_query, pjw_HFS)


    #### Append current work to the Archive Feature Services (other than matching current job, overlap is allowed)
    AddMsgAndPrint("\nUploading to Archive Layers...",0)
    arcpy.SetProgressorLabel("Uploading to Archive Layers...")
    
    arcpy.Append_management(projectSum, extA_HFS, "NO_TEST")
    arcpy.Append_management(projectSumPts, reqptsA_HFS, "NO_TEST")
    arcpy.Append_management(projectSU, suA_HFS, "NO_TEST", field_mapping_su_to_hfs)
    arcpy.Append_management(projectROP, ropA_HFS, "NO_TEST", field_mapping_rop_to_hfs)
    arcpy.Append_management(projectCWD, cwdA_HFS, "NO_TEST", field_mapping_cwd_to_hfs)
    arcpy.Append_management(projectCLUCWD, clucwdA_HFS, "NO_TEST", field_mapping_clucwd_to_hfs)
    arcpy.Append_management(cluCWDpts, clucwdptsA_HFS, "NO_TEST", field_mapping_clucwd_to_hfs)
    if ref_count > 0:
        arcpy.Append_management(projectREF, rpA_HFS, "NO_TEST", field_mapping_ref_to_hfs)
    if dl_count > 0:
        arcpy.Append_management(projectLines, drainsA_HFS, "NO_TEST", field_mapping_dl_to_hfs)
    if pjw_count > 0:
        arcpy.Append_management(projectPJW, pjwA_HFS, "NO_TEST")


    #### Process the Active Data Layers
    AddMsgAndPrint("\nUploading to Active Layers...",0)
    arcpy.SetProgressorLabel("Uploading to Active Layers...")
    
    # Polygon find and replace function syntax references
    # update_polys(up_ws, up_temp_dir, proj_fc, up_RESTurl, local_temp, fldmapping='')
    update_polys(scratchGDB, wetDir, projectSU, su_HFS, su_server_copy, field_mapping_su_to_hfs)        # Sampling Units Layer
    update_polys(scratchGDB, wetDir, projectCWD, cwd_HFS, cwd_server_copy, field_mapping_cwd_to_hfs)    # CWD Layer
    
    # update_polys_and_points(up_ws, up_temp_dir, proj_fc, up_RESTurl, local_temp, proj_pts = '', ptsURL = '', fldmapping='')
    update_polys_and_points(scratchGDB, wetDir, projectSum, ext_HFS, ext_server_copy, projectSumPts, reqpts_HFS)    # Summary Extent Layer and points
    update_polys_and_points(scratchGDB, wetDir, projectCLUCWD, clucwd_HFS, clucwd_server_copy, cluCWDpts, clucwdpts_HFS, field_mapping_clucwd_to_hfs)  # CLU CWD Layer and points

    #arcpy.Append_management(projectSumPts, reqpts_HFS, "NO_TEST", field_mapping_ref_to_hfs)         # Summary points
    arcpy.Append_management(projectROP, rop_HFS, "NO_TEST", field_mapping_rop_to_hfs)           # ROPs Layer
    # replace_pts_by_area(scratchGDB, wetDir, projectROP, projectSU, rop_HFS, field_mapping_rop_to_hfs)             # ROPs Layer - can't do it this way due to legacy ramifications (split SUs)
    #arcpy.Append_management(cluCWDpts, clucwdpts_HFS, "NO_TEST", field_mapping_clucwd_to_hfs)   # CLU CWD Points Layer
    # replace_pts_by_area(scratchGDB, wetDir, cluCWDpts, projectCWD, clucwdpts_HFS, field_mapping_clucwd_to_hfs)    # CLU CWD Pts Layer - can't do it this way due to legacy ramifications (split CLUs or CWDs)
    
    if ref_count > 0:
        arcpy.Append_management(projectREF, rp_HFS, "NO_TEST", field_mapping_ref_to_hfs)        # Reference Points
    if dl_count > 0:
        arcpy.Append_management(projectLines, drains_HFS, "NO_TEST", field_mapping_dl_to_hfs)   # Drainage Lines Layer
    if pjw_count > 0:
        arcpy.Append_management(projectPJW, pjw_HFS, "NO_TEST")                                 # PJW Layer


    #### Clean up Temporary Datasets
    # Temporary datasets specifically from this tool
    AddMsgAndPrint("\nCleaning up temporary data...",0)
    arcpy.SetProgressorLabel("Cleaning up temporary data...")
    deleteTempLayers(tempLayers)

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
                arcpy.management.Delete(fc)
            except:
                pass
    arcpy.env.workspace = startWorkspace
    del startWorkspace

    
    #### Compact FGDB
    try:
        AddMsgAndPrint("\nCompacting File Geodatabases..." ,0)
        arcpy.SetProgressorLabel("Compacting File Geodatabases...")
        arcpy.Compact_management(basedataGDB_path)
        arcpy.Compact_management(wcGDB_path)
        arcpy.Compact_management(scratchGDB)
        AddMsgAndPrint("\tSuccessful",0)
    except:
        pass


except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested. Exiting...")

except:
    errorMsg()
