#Script developed to streamline the installation and setup of all the necessary packages in R for the report development as part of the Wetland Compliance tool.
#Chris Morse - GIS Specialist, IN
#Edwin Muniz - State Soil Scientist, NJ
#June, 8, 2021.


#This script runs in two parts, first to remove arcgisbinding and redirect the source and second, for install all libraries. To run the first part of the tool highlight or select from line 9 to line 16 and select or click the Run icon in the upper right of this pane. After the section finished with the restart highlight or select from line 18 to line 22 and select or click the Run icon in the upper right of this pane. When process completed close the R Studio section.

#Unistall arcgisbinding package
remove.packages(arcgisbinding)

# Redirect R profile
source('https://raw.githubusercontent.com/ncss-tech/soilReports/master/R/installRprofile.R')
installRprofile(overwrite=TRUE)

#Wait a few seconds for the R section to restart
.rs.restartR()

#Install packages needed for the report generator
install.packages(c("flextable", "knitr", "rmarkdown", "textreadr", "xlsx"), dependencies = TRUE)

#Install arcgidbinding package
install.packages("arcgisbinding", repos = "https://r.esri.com", type = "win.binary")