# Wetland-Tools---ArcGIS-Pro
NRCS wetlands conservation compliance tools for creating determination products in ArcGIS Pro

## **Version 1.1.0 (9/9/2022; Production Release):**

New Features/Changes:
- Updated the NAD Address Spreadsheet.
- Updated the LibraryInstall.R file to mitigate errors and execution failures of the Create Forms and Letters tool.
- Updated the WC_Report_Tool.r file to mitigate errors and execution failures of the Create Forms and Letters tool.
- Updated Install Base Software section and the Configure R section of the state administrator guide and user guide.

### Tips on Updating
State Tool Administrators should download the new version, customize it (per the guidance in the State Administrator Guide), and the provide their customized version to users in their state.
	
Close any ArcGIS Pro projects for the WC Tools before installing the new version.
	
APRX Templates from v1.0.4 or later are compatible with this new release. Make a copy of your existing custom APRX templates outside of the install folder, install the new version, and then restore your custom templates to the appropriate folder(s) within the new install.
	
The NRCS Address spreadsheet's format from 1.0.4 or later has NOT changed. You can use your existing 1.0.4 or later NRCS Address spreadsheet if you've already customized it. Make a copy of your existing NRCS Address spreadsheet outside of the install folder, install the new version, and then restore your custom NRCS Address spreadsheet in the standard location within the install folder.
	
APRX templates or spreadsheets from version 1.0.3 or earlier should not be brought forward into this version and should instead be rebuilt using the template files provided by the latest install.


## **Version History:**

### v 1.0.9 (8/29/2022; Production Release):

- Replaced the NWI data service with a new, higher performing service. Previous versions of the service will be retired, so you must update to at least this version of the tool to retain NWI download functions during the Create Wetlands Project step.
- Updated State Administrator Guide and User Guide to be in sync with the current tool version number.
- Added an Appendix describing the Wetland Determinations Dashboard to the documentation guides.
- Corrected a bug in the Download Soil Data step to better handle groups of layers being used in the map frame.
- Added further refinements to multiple scripts when groups of layers were being used in the map frame.


### v 1.0.8 (8/13/2022; Production Release):
- Updated contact information in State Tool Administrator Guide to the Central Region GIS Specialist.
- Corrected a bug that affected layer names in scripts when groups were being used in maps.
- Deleted a redundant (bad) copy of a tool that was empty.


### v 1.0.7 (7/13/2022; Production Release):
- Corrected a bug in the Export Reference Maps tool.
- Updated user guides for new installation versions of ArcGIS Pro and R for Windows.


### v 1.0.6 (6/23/2022; Production Release):
- Moved training data from GIS Testing to GIS States and updated all relevant training templates, tools, and documentation accordingly.
- Corrected NWI symbology in the production toolbox references to the NWI layer.
- Corrected minor typos in the user guide.


### v 1.0.5 (5/19/2022; Production Release):
- All tools have been updated to show Help info when hovering over the "i" marker for parameters in the tools.
- The previously determined map and report workflow has been fully enabled and documented and will function for determinations previously digitized by this tool, only. Determinations that are not digitized in this tool cannot be used in this process.
- The revisions workflow has been fully enabled and documented. Determinations that are not digitized in this tool cannot be used in this process.
- The creation of an NWI layer at the project site has been restored to the workflow.  The NWI layer now downloads to the local project by intersecting the Tract boundary with the NWI feature service on GeoPortal.  This takes place automatically during Create Wetlands Project.  If no features are found during the intersect, or if the NWI data service is offline or not responsive, then NWI data will not download but Create Wetlands Project will still run to complete its normal functions.  If NWI data does not download, view the results messages after running the Create Wetlands Project tool to determine if no data was found at the site, or if the download had an error.
- A standalone Download NWI Data tool has been added to the Utilities toolset as a redundant option if the initial download during project creation fails (such as if the NWI data service is offline when the project is created).
- The NWI map option has been re-enabled in the Export Reference Maps tool.
- The parameters for the Create CWD Map Layers tool have been slightly altered to accommodate an NRCS-CPA-028 Report only option (such as if previously digitized determinations cover the entire tract).  The changes have no impact on the normal workflow for requests in new areas.
- Layer files for read-only copies of the national WC Tool web layers have been added to the install directory under the Reference Layers folder. All such files contain the word "View" in their name.  These layers could be useful for viewing in the background of any given site project, as needed, particularly when snapping to work on adjacent tracts.
- Corrected a typo in preliminary letter on the Appeals Information page.
- Disabled the ability to consolidate records by label for the NRCS-CPA-028 form due to complications presented by grouping by certification date in addition to the label.  The capability to consolidate records by label still remains for the NRCS-CPA-026 form.
- Added template Style sheets for State Tool Administrators to use to create custom styles.
- Changed the default symbology for the Site Previous CLU CWD layer.
- Created read-only views of the live data services and used them to create an Operations Dashboard on the GIS-States Portal. Only production data will upload to these layers, views, and the dashboard.  As this release is new, only a tiny amount of test data is currently present in the dashboard until states begin using the tool. 
- The read-only views from the previous bullet point have been shared with the entire Organization. As such, the URLs for those views can be streamed into other secure maps or apps, such as Conservation Desktop. The views (if searching by name on GIS States) are:

  > - NRCS Sampling Units RO View
  > - NRCS ROPs RO View
  > - NRCS WC Reference Points RO View
  > - NRCS WC Drains RO View
  > - NRCS PJW RO View	
  > - NRCS CWD RO View
  > - NRCS CLU CWD Points RO View
  > - NRCS CLU CWD RO View
  > - NRCS CWD Summary Points RO View	
  > - NRCS CWD Summary Areas RO View
		
- The WC Tool State Administrator Guide has been updated and taken out of draft status. Further edits may be made, but the core structure and concepts are in placeThe WC Tool User Guide has been updated and taken out of draft status. Further edits may be made, but the core structure and concepts are in place.


### v 1.0.4 (4/12/2022; Production Release):
- Released production version that connects with data services on GIS States.
- Split Templates and Toolboxes into Training and Live Versions.
- New templates released as a result; all existing projects should be completed prior to upgrading and all templates should be rebuilt.
- New training template, toolbox, and scripts provided to support training in the GIS Testing environment; intended for training/test work only.
- New production template, toolbox, and scripts provided to support determinations in the GIS States environment; intended for actual work.
- Added support for custom styles.
- Added options in Form and Letter creation to select NRCS and FSA office as input parameters.
- Redesigned the NRCS_Address table; new table is not compatible with old versions of the table from versions prior to 1.0.4 and must be re-populated.
- Added new tool to import the NRCS_Address table to the toolboxes.
- Updated Form and Letter templates and processing in R.
- Corrected an issue with field numbers repeating when using the consolidate by label option to generate the form.
- Removed development Task files to reduce confusion for workflow.


### v 1.0.3 (3/22/2022; Training Version):
- Updated Form templates due to new R libraries to correct formatting issues.


### v 1.0.2 (3/15/2022; Training Version):
- Corrections to typos and terminology throughout the tool for greater consistency.


### v 1.0.1 (3/11/2022; Training Version):
- Adjustments to GIS data uploads to server and dashboard.


### v 1.0.0 (3/5/2022; Training Version):
- Initial release. Training Version.
- All principal features enabled except automated NWI map layout export, pending NWI Feature Service maintenance.
