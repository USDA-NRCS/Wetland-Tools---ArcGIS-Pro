# Wetland-Tools---ArcGIS-Pro
NRCS wetlands conservation compliance tools for creating determination products in ArcGIS Pro

Version 1.0.4 (4/12/2022; Production Release):
Released production version that connects with data services on GIS States.
Split Templates and Toolboxes into Training and Live Versions.
New templates released as a result; all existing projects should be completed prior to upgrading and all templates should be rebuilt.
New training template, toolbox, and scripts provided to support training in the GIS Testing environment; intended for training/test work only.
New production template, toolbox, and scripts provided to support determinations in the GIS States environment; intended for actual work.
Added support for custom styles.
Added options in Form and Letter creation to select NRCS and FSA office as input parameters.
Redesigned the NRCS_Address table; new table is not compatible with old versions of the table from versions prior to 1.0.4 and must be re-populated.
Added new tool to import the NRCS_Address table to the toolboxes.
Updated Form and Letter templates and processing in R.
Corrected an issue with field numbers repeating when using the consolidate by label option to generate the form.
Removed development Task files to reduce confusion for workflow.


Version History:

v 1.0.3 (3/22/2022; Training Version):
Updated Form templates due to new R libraries to correct formatting issues.

v 1.0.2 (3/15/2022; Training Version):
Corrections to typos and terminology throughout the tool for greater consistency.

v 1.0.1 (3/11/2022; Training Version):
Adjustments to GIS data uploads to server and dashboard.

v 1.0.0 (3/5/2022; Training Version):
Initial release. Training Version.
All principal features enabled except automated NWI map layout export, pending NWI Feature Service maintenance.
