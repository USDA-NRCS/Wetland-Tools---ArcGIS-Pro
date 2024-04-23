from sys import exc_info
from traceback import format_exception

from arcpy import AddError, AddMessage, AddWarning, GetActivePortalURL, GetSigninToken, ListPortalURLs
from arcpy.metadata import Metadata


def AddMsgAndPrint(msg, severity=0, textFilePath=None):
    """ Adds tool message to the geoprocessor. Split the message on \n first, so a GPMessage will be added for each line."""
    try:
        if textFilePath:
            f = open(textFilePath, 'a+')
            f.write(f"{msg}\n")
            f.close
            del f
        if severity == 0:
            AddMessage(msg)
        elif severity == 1:
            AddWarning(msg)
        elif severity == 2:
            AddError(msg)
    except:
        pass


def errorMsg():
    """ Print traceback exceptions. If sys.exit was trapped by default exception then ignore traceback message."""
    try:
        exc_type, exc_value, exc_traceback = exc_info()
        theMsg = f"\t{format_exception(exc_type, exc_value, exc_traceback)[1]}\n\t{format_exception(exc_type, exc_value, exc_traceback)[-1]}"
        if theMsg.find('sys.exit') > -1:
            AddMsgAndPrint('\n\n')
            pass
        else:
            AddMsgAndPrint('\n\tNRCS HEL Tool Error: -------------------------', 2)
            AddMsgAndPrint(theMsg, 2)
    except:
        AddMsgAndPrint('Unhandled error in errorMsg method', 2)
        pass


def getPortalTokenInfo(portalURL):
    try:
        # i.e. 'https://gis.sc.egov.usda.gov/portal/'
        activePortal = GetActivePortalURL()

        # targeted portal is NOT set as default
        if activePortal != portalURL:
            # List of managed portals
            managedPortals = ListPortalURLs()

            # portalURL is available in managed list
            if activePortal in managedPortals:
                AddMsgAndPrint(f"\nYour Active portal is set to: {activePortal}", 2)
                AddMsgAndPrint(f"Set your active portal and sign into: {portalURL}", 2)
                return False

            # portalURL must first be added to list of managed portals
            else:
                AddMsgAndPrint(f"\nYou must add {portalURL} to your list of managed portals", 2)
                AddMsgAndPrint('Open the Portals Tab to manage portal connections', 2)
                AddMsgAndPrint('For more information visit the following ArcGIS Pro documentation:', 2)
                AddMsgAndPrint('https://pro.arcgis.com/en/pro-app/help/projects/manage-portal-connections-from-arcgis-pro.htm', 2)
                return False

        # targeted Portal is correct; try to generate token
        else:
            # Get Token information
            tokenInfo = GetSigninToken()

            # Not signed in.  Token results are empty
            if not tokenInfo:
                AddMsgAndPrint(f"\nYou are not signed into: {portalURL}", 2)
                return False

            # Token generated successfully
            else:
                return tokenInfo

    except:
        errorMsg()
        return False


def importCLUMetadata(source_fc, target_fc):
    ''' Imports metadata from a source feature class to a target feature class.'''
    target_md = Metadata(target_fc)
    target_md.importMetadata(source_fc)
    target_md.save()
