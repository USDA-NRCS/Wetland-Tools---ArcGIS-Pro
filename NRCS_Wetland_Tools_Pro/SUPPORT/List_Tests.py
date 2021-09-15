import arcpy, os, sys

map_list = arcpy.GetParameterAsText(0).split(";")
arcpy.AddMessage(map_list)

new_list = []
for item in map_list:
    new_item = item.replace("'", "")
    new_list.append(new_item)

arcpy.AddMessage(new_list)
