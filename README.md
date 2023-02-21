# Wetland-Tools---ArcGIS-Pro
NRCS wetlands conservation compliance tools for creating determination products in ArcGIS Pro

## **Version 2.0.1 (02/21/2023; Production Release):**

### **New Features/Changes**
- Changed all workflows and tool references that imported or exported Excel tables to use CSV to avoid compatibility problems with ArcGIS Pro 3.0.3.
- CSV files cannot have multiple tables or tabs, so split the NRCS Address Excel file into an NRCS Address CSV file and FSA Address CSV file.
- Converted the NAD Address Excel file to CSV.
- Removed the NRCS Address and NAD Addres Excel files (now replaced by CSV files referenced above).
- Updated the State Tool Administrator guide and the User Guide to reflect changes from Excel to CSV.

### **Changed Files**
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\Create_CWD_Mapping_Layers.py
- ..\NRCS_Welland_Tools_Pro\SUPPORT\Create_Forms_and_Letters.py
- ..\NRCS_Welland_Tools_Pro\SUPPORT\Download_Soil_Data.py
- ..\NRCS_Welland_Tools_Pro\SUPPORT\Export_Soil_Table.py
- ..\NRCS_Welland_Tools_Pro\SUPPORT\Import_Office_Addresses.py


### Tips on Updating
It is recommended to completely replace existing installation folders and contents. State Tool Administrators can retain the previous NRCS_Address.xlsx file to transfer NRCS and FSA addresses to the new CSV files as necessary (see State Tool Administrator Guide). Newly entered (or transferred) addresses should be imported into the State Tool Administrator's version of the tool before they repackage and deploy it (again, see the State Tool Administrator Guide). 

### Adoption by States that never used any previous version
States that have never adopted the Wetland Tools prior to version 2.0.1 should have the State Tool Administrator download version 2.0.1 and customize it fully, following all instructions in the State Tool Administrator Guide found in the Docs folder.

### Updates for Version 2.0.0 Adopters
States that have adopted version 2.0.0 of the tools already can download version 2.0.1, and only need to update the following:
- Save a copy of the NRCS_Address.xlsx from version 2.0.0.
- Edit the new NRCS_Address.csv and FSA_Address.csv files, per the instructions in the State Tool Administrator Guide.
- Note: Records can be copied and pasted from the previous NRCS_Address.xlsx spreadsheet tabs to the new, respective CSV files.
- Import the updated address tables to the tool, per the instructions in the State Tool Administrator Guide.
- APRX templates created from version 2.0.x of the tool do not need to be rebuilt and overwritten for users.
- Distribute their customized version in their respective state.

### Updates for Version 1.x.x Adopters
States that adopted a version before 2.0.0 and which have not yet switched to 2.0.0 can skip to 2.0.1, and should do the following:
- Save a copy of the NRCS_Address.xlsx from version 1.x.x.
- Edit the new NRCS_Address.csv and FSA_Address.csv files, per the instructions in the State Tool Administrator Guide.
- Note: Records can be copied and pasted from the previous NRCS_Address.xlsx spreadsheet tabs to the new, respective CSV files.
- Import the updated address tables to the tool, per the instructions in the State Tool Administrator Guide.
- Create new state level APRX templates as needed, from the newly created Blank Templates now provided in the install folder.
- Distribute their customized version in their respective state.

### Version 1.x.x APRX File Compatibility with Version 2.x.x APRX Files
APRX Templates or files from any 1.x.x version of the tools will work in version 2.x.x of the tools, except for the *Validate Sampling Units* and *Export Base Map* tools. Due to the changes related to the Base Map in version 2.x.x, existing projects created under any 1.x.x version of the tools *can* be made to work by importing the new Base Map layout file (PAGX) from the *Installed_Templates* folder, per the following procedure. The following procedure is *only* recommended for existing work projects that were not complete at the time a user updates from version 1.x.x to 2.x.x of the tool. These steps are ONLY recommended for existing projects that were started BEFORE a user upgraded version to 2.x.x tools and ONLY if the user has subsequently updated to version 2.x.x.

- Open the existing template or APRX.
- In Catalog, expand Layouts.
- Right-click and Delete the existing Base Map Layout.
- Go to the Insert tab.
- Click Import Layout.
- Click Import Layout File (at the bottom of the Import Layout screen).
- Navigate to ..\NRCS_Wetland_Tools_Pro\Installed_Layouts
- Select Base Map Portrait 8.5x11 (this is a PAGX file type).
- Click OK
- The new Base Map will be added to the project and will be open.
- In the Contents pane of the open Base Map, right-click the "Map Frame" item and then click Properties.
- In the Format Map Frame pane that opens, find the Map Frame section and change the Map in the drop down from Determiations1 to Determinations.
- Close the Format Map Frame pane.
- In the Catalog Pane, expand the Maps section.
- Right-click and Delete Determinations1. Do NOT delete Determinations! Only delete any additional Determinations maps that are appended with a number.
- Save the project.


## **Version History:**

### v 2.0.0 (02/09/2023; Production Release):

- Updated recommended ArcGIS Pro version to 2.9.5 in documentation. Pro 2.7.x and 2.8.x still work.
- Confirmed tool functions in Pro 3.0.3, however there are Excel dependency components for Pro 3.0.3 that IT needs to install (described in documentation). These dependent components are NOT needed for Pro 2.7, 2.8, or 2.9. The Excel dependent components needed for Pro 3.0.3 have been requested for Software Center release to Pro 3.0.3 users only, but are not yet available.
- Removed all R components and replaced them with python components in the Forms and Letter tools.
- *R for Windows*, *RStudio*, and/or *RTools* are no longer required dependencies and can be uninstalled unless needed for other work.
- The *R arcgisbinding* no longer needs to be configured, and can be left in place if present.
- A special *Java* installation is no longer needed to support the R components. If you have already have extra versions of Java from previous troubleshooting of the tool, they do not need to be uninstalled.
- Updated the *State Tool Administrator* guide and the *User Guide*.
- Updated both documentation guides to reflect the changes that removed R.
- Updated the *Install Base Software* sections of the guides to account for currently available versions of ArcGIS Pro.
- Updated the *Troubleshooting* appendix in the *User Guide* with a few more issues and resolutions.
- Restored capability to make a elevation maps with and without contours.
- Added a *Total Project Area* text box to the Base Map that autopopulates. See *Tips on Updating*, below, for notes on building new templates or importing the new base map layout file into old projects.
- Changed the Determination Map to display "Potential Jurisdictional Waters" in the legend when running *Export Determination Map*.
- Corrected labeling expressions for the *CLU CWD* layer and *Previous Determinations* layer to properly display the *Occurrence Year* value, when present.
- Updated *Reload Project Layers* tool to reload any missing business layer from the project, not just layers that use attribute rules.
- Retrograded some 2.9 layer (LYRX) files to version 2.7 to reduce error messages in Pro 2.7 and 2.8.
- Added new layer files (LYRX) for NRCS Bare Earth DEM service coverage extents and a new layer for the NRCS 0.5 meter service to the *Reference Layers* folder.
- Updated the *NAD Address Spreadsheet* to correct the name of the TOLLFREE column.
- Updated *Import Office Addresses* tool to also import the *NAD_Address.xlsx* spreadsheet to allow rapid local corrections in the event of address changes.
- Imported the updated the *NAD Address* data table into the SUPPORT.gdb file.
- Fixed bug with apostrophes in county names.
- Fixed bug to reliably generate *Sampling Unit* polygons when a new *Request Extent* is found adjacent to and coincident with previously completed determinations.
- ..\NRCS_Wetland_Tools_Pro\LibraryInstall.R (removed)
- ..\NRCS_Wetland_Tools_Pro\NRCS_Wetland_Tools_Pro.tbx
- ..\NRCS_Wetland_Tools_Pro\NRCS_Wetland_Tools_Pro_Training.tbx
- ..\NRCS_Wetland_Tools_Pro\Template_Blank_2.7.aprx
- ..\NRCS_Wetland_Tools_Pro\Template_Blank_Training_2.7.aprx
- ..\NRCS_Wetland_Tools_Pro\Reference_Layers\NRCS Bare Earth 0.5m.lyrx
- ..\NRCS_Wetland_Tools_Pro\Reference_Layers\NRCS Bare Earth 3m Coverage.lyrx
- ..\NRCS_Wetland_Tools_Pro\Reference_Layers\NRCS Bare Earth 2m Coverage.lyrx
- ..\NRCS_Wetland_Tools_Pro\Reference_Layers\NRCS Bare Earth 1m Coverage.lyrx
- ..\NRCS_Wetland_Tools_Pro\Reference_Layers\NRCS Bare Earth 0.5m Coverage.lyrx
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\Create_028_Form_Only.py
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\Create_Base_Map_Layers.py
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\Create_Base_Map_Layers_Training.py
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\Create_CWD_Layers.py
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\Create_CWD_Mapping_Layers.py
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\Create_Forms_and_Letters.py
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\Create_Wetlands_Project.py
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\Export_Base_Map.py
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\Export_Determination_Map.py
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\Export_Reference_Maps.py
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\Import_Office_Addresses.py
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\Reload_Project_Layers.py
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\Validate_Sampling_Units.py
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\Docs\WC Tool State Administrator Guide.docx
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\Docs\WC Tool State Administrator Guide.pdf
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\Docs\WC Tool User Guide.docx
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\Docs\WC Tool User Guide.pdf
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\layer_files\CLU_CWD.lyrx
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\layer_files\CWD.lyrx
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\layer_files\Previous_CLU_CWD.lyrx
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\layer_files\Sampling_Units.lyrx
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\python_packages (this is a new folder with all new contents)
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\SUPPORT.gdb
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\Templates (all files in this folder that supported R were removed or replaced, except for NAD_Address.xlsx and NRCS_Address.xlsx)
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\Templates\NAD_Address.xlsx


### v 1.1.0 (09/09/2022; Production Release):

- Updated the NAD Address Spreadsheet.
- Updated the LibraryInstall.R file to mitigate errors and execution failures of the Create Forms and Letters tool.
- Updated the WC_Report_Tool.r file to mitigate errors and execution failures of the Create Forms and Letters tool.
- Updated Install Base Software section and the Configure R section of the state administrator guide and user guide.
- Updated the labeling expressions for Sampling Units, CWD, CLU CWD, and Previous CLU CWD to round acres to the hundredths.
- ..\NRCS_Wetland_Tools_Pro\LibraryInstall.R
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\Docs\WC Tool State Administrator Guide.docx
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\Docs\WC Tool State Administrator Guide.pdf
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\Docs\WC Tool User Guide.docx
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\Docs\WC Tool User Guide.pdf
- ..\NRCS_Wetland_Tools_Pro\SUPPORT\Templates\WC_Report_Tool.r


### v 1.0.9 (08/29/2022; Production Release):

- Replaced the NWI data service with a new, higher performing service. Previous versions of the service will be retired, so you must update to at least this version of the tool to retain NWI download functions during the Create Wetlands Project step.
- Updated State Administrator Guide and User Guide to be in sync with the current tool version number.
- Added an Appendix describing the Wetland Determinations Dashboard to the documentation guides.
- Corrected a bug in the Download Soil Data step to better handle groups of layers being used in the map frame.
- Added further refinements to multiple scripts when groups of layers were being used in the map frame.


### v 1.0.8 (08/13/2022; Production Release):
- Updated contact information in State Tool Administrator Guide to the Central Region GIS Specialist.
- Corrected a bug that affected layer names in scripts when groups were being used in maps.
- Deleted a redundant (bad) copy of a tool that was empty.


### v 1.0.7 (07/13/2022; Production Release):
- Corrected a bug in the Export Reference Maps tool.
- Updated user guides for new installation versions of ArcGIS Pro and R for Windows.


### v 1.0.6 (06/23/2022; Production Release):
- Moved training data from GIS Testing to GIS States and updated all relevant training templates, tools, and documentation accordingly.
- Corrected NWI symbology in the production toolbox references to the NWI layer.
- Corrected minor typos in the user guide.


### v 1.0.5 (05/19/2022; Production Release):
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


### v 1.0.4 (04/12/2022; Production Release):
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


### v 1.0.3 (03/22/2022; Training Version):
- Updated Form templates due to new R libraries to correct formatting issues.


### v 1.0.2 (03/15/2022; Training Version):
- Corrections to typos and terminology throughout the tool for greater consistency.


### v 1.0.1 (03/11/2022; Training Version):
- Adjustments to GIS data uploads to server and dashboard.


### v 1.0.0 (03/05/2022; Training Version):
- Initial release. Training Version.
- All principal features enabled except automated NWI map layout export, pending NWI Feature Service maintenance.
