# -*- coding: utf-8 -*-
"""
Generated by ArcGIS ModelBuilder on : 2020-09-21 10:16:11
"""
import arcpy

def Model():  # Model

    # To allow overwriting outputs change overwriteOutput option to True.
    arcpy.env.overwriteOutput = False

    CLU_in091_t0012564_2020_09 = "CLU_in091_t0012564_2020_09"
    SUPPORT_gdb = "C:\\GIS_Tools\\NRCS_Wetland_Tools_Pro\\SUPPORT\\SUPPORT.gdb"

    # Process: Feature Class to Feature Class (Feature Class to Feature Class) (conversion)
    new_clu = arcpy.conversion.FeatureClassToFeatureClass(in_features=CLU_in091_t0012564_2020_09, out_path=SUPPORT_gdb, out_name="new_clu", where_clause="", field_mapping=
                                                          "GlobalId \"GlobalId\" true true false 38 Guid 0 0,First,#,CLU_in091_t0012564_2020_09,GlobalId,-1,-1;" +
                                                          "admin_state \"Admin State\" true true false 2 Text 0 0,First,#,CLU_in091_t0012564_2020_09,admin_state,0,2;" +
                                                          "admin_state_name \"Admin State Name\" true true false 255 Text 0 0,First,#,CLU_in091_t0012564_2020_09,admin_state_name,0,255;" +
                                                          "admin_county \"Admin County\" true true false 3 Text 0 0,First,#,CLU_in091_t0012564_2020_09,admin_county,0,3;" +
                                                          "admin_county_name \"Admin County Name\" true true false 255 Text 0 0,First,#,CLU_in091_t0012564_2020_09,admin_county_name,0,255;" +
                                                          "state_code \"State Code\" true true false 2 Text 0 0,First,#,CLU_in091_t0012564_2020_09,state_code,0,2;" +
                                                          "state_name \"State Name\" true true false 255 Text 0 0,First,#,CLU_in091_t0012564_2020_09,state_name,0,255;" +
                                                          "county_code \"County Code\" true true false 3 Text 0 0,First,#,CLU_in091_t0012564_2020_09,county_code,0,3;" +
                                                          "county_name \"County Name\" true true false 255 Text 0 0,First,#,CLU_in091_t0012564_2020_09,county_name,0,255;" +
                                                          "farm_number \"Farm Number\" true true false 7 Text 0 0,First,#,CLU_in091_t0012564_2020_09,farm_number,0,7;" +
                                                          "tract_number \"Tract Number\" true true false 7 Text 0 0,First,#,CLU_in091_t0012564_2020_09,tract_number,0,7;" +
                                                          "clu_number \"CLU Number\" true true false 7 Text 0 0,First,#,CLU_in091_t0012564_2020_09,clu_number,0,7;" +
                                                          "clu_calculated_acreage \"CLU Calculated Acreage\" true true false 8 Double 0 0,First,#,CLU_in091_t0012564_2020_09,clu_calculated_acreage,-1,-1;" +
                                                          "highly_erodible_land_type_code \"Highly Erodible Land Type Code\" true true false 4 Text 0 0,First,#,CLU_in091_t0012564_2020_09,highly_erodible_land_type_code,0,4;" +
                                                          "creation_date \"Creation Date\" true true false 8 Date 0 0,First,#,CLU_in091_t0012564_2020_09,creation_date,-1,-1;" +
                                                          "last_change_date \"Last Change Date\" true true false 8 Date 0 0,First,#,CLU_in091_t0012564_2020_09,last_change_date,-1,-1"

if __name__ == '__main__':
    # Global Environment settings
    with arcpy.EnvManager(scratchWorkspace=r"C:\GIS_Tools\NRCS_Wetland_Tools_Pro\SUPPORT\SUPPORT.gdb", workspace=r"C:\GIS_Tools\NRCS_Wetland_Tools_Pro\SUPPORT\SUPPORT.gdb"):
        Model()
