import arcpy.mp

try:
    aprx = arcpy.mp.ArcGISProject(r"C:\Temp\ArcPro\Empty.aprx")
    
    map = aprx.listMaps()[0]
    print(map.name)
    
    layout = aprx.listLayouts()[0]
    mapframe = layout.listElements("MAPFRAME_ELEMENT")[0]
    print (mapframe.name)
    print (mapframe.map.name)

    ext = mapframe.camera.getExtent()
    print ("MapFrame Extent: " + ext.JSON)

    mapframe.map.addDataFromPath(r"C:\Temp\ArcPro\Orthomosaic.tif")
    mapframe.zoomToAllLayers()

    ext = mapframe.camera.getExtent()
    print ("MapFrame Extent: " + ext.JSON)

    mapext = map.defaultCamera.getExtent()
    print ("Map Extent:      " + mapext.JSON)

    aprx.saveACopy(r"C:\Temp\ArcPro\New.aprx")

except Exception as err:
    print("Error Aprx. %s" % str(err))

