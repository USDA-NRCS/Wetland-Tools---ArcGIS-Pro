from arcgis.gis import GIS
from arcgis.features import FeatureLayerCollection

from arcpy import Describe, ListTransformations
from arcpy.management import Delete, Project, Rename

from wetland_utils import AddMsgAndPrint, errorMsg


def extract_CLU(admin_state, admin_county, tract, out_gdb, out_sr):
    """
    Downloads and projects a CLU field layer from the NRCS Common Land Service layer for local use.

    Args:
        admin_state (str): State code string value from GetParameterAsText
        admin_county (str): County code string value from GetParameterAsText
        tract (str): Tract number string value from GetParameterAsText
        out_gdb (str): Path to output GBD, remember to include FD in path
        out_sr (SpatialReference): arcpy object defined by user's project
    
    Returns:
        If successful returns path to extracted/projected CLU layer, otherwise False
    """
    try:
        ### Locate Common Land Unit Service in GeoPortal ###
        gis = GIS('pro')
        clu_fs_item = gis.content.get('4b91657af3ae4368ab1c1728c97b281e')
        clu_flc = FeatureLayerCollection.fromitem(clu_fs_item)
        clu_fl = clu_flc.layers[0]
        AddMsgAndPrint('Located Common Land Units Feature Service in GeoPortal')

        ### Query Feature Service by State/County/Tract ###
        if admin_state == '02':
            # Alaska doesn't use Admin_county, they use county_ansi_code
            query = f"ADMIN_STATE = {str(admin_state)} AND COUNTY_ANSI_CODE = {str(admin_county)} AND TRACT_NUMBER = {str(tract)}"
        else:
            query = f"ADMIN_STATE = {str(admin_state)} AND ADMIN_COUNTY = {str(admin_county)} AND TRACT_NUMBER = {str(tract)}"
        
        AddMsgAndPrint(f"Querying USDA-NRCS GeoPortal for CLU fields where: {query}")
        clu_fset = clu_fl.query(where=query)
        clu_count = len(clu_fset)

        ### Validate Number of CLUs Returned ###
        if clu_count == 0:
            AddMsgAndPrint(f"\nThere were no CLU fields associated with tract Number {str(tract)}. Please review Admin State, County, and Tract Number entered.", 1)
            return False
        if clu_count > 1:
            AddMsgAndPrint(f"\nThere are {str(clu_count)} CLU fields associated with tract number {str(tract)}")
        else:
            AddMsgAndPrint(f"\nThere is {str(clu_count)} CLU field associated with tract number {str(tract)}")

        ### Save and Project Extracted CLU Layer to SR Input ###
        extracted_CLU_temp = clu_fset.save(out_gdb, 'extracted_CLU')
        from_sr = Describe(extracted_CLU_temp).spatialReference
        transformation = ListTransformations(from_sr, out_sr)
        if len(transformation):
            transformation = transformation[0]
            msg_type = 1
        else:
            transformation = None
            msg_type = 0

        projected_CLU = f"{extracted_CLU_temp}_prj"
        Project(extracted_CLU_temp, projected_CLU, out_sr, transformation)
        Delete(extracted_CLU_temp)
        Rename(projected_CLU, projected_CLU[0:-4])
        extracted_CLU = projected_CLU[0:-4]

        AddMsgAndPrint('\nProjecting CLU Feature class', msg_type)
        AddMsgAndPrint(f"FROM: {str(from_sr.name)}", msg_type)
        AddMsgAndPrint(f"TO: {str(out_sr.name)}", msg_type)
        AddMsgAndPrint(f"Geographic Transformation used: {str(transformation)}", msg_type)

        return extracted_CLU

    except Exception:
        errorMsg()
        return False


if __name__ == '__main__':
    pass
    # from arcpy import SpatialReference
    # admin_state = '18'
    # admin_county = '091'
    # tract = '12564'
    # out_gdb = 'C:/Determinations/test.gdb'
    # map_sr = SpatialReference(32616)
    # extracted_CLU = extract_CLU(admin_state, admin_county, tract, out_gdb, map_sr)
