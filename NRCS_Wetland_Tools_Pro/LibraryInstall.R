#Script developed to streamline the installation and setup of all the necessary packages in R for the report development as part of the Wetland Compliance tool.
#Chris Morse - GIS Specialist, IN
#Edwin Muniz - State Soil Scientist, NJ
#June, 8, 2021.


#This script runs in two parts. The first part removes existing arcgisbinding packages that may
# be installed in the documents folder and redirects the local packages library for R to conform
# to the soil survey division's configuration for R. The second part installs all R packages
# needed for the WC Tool.

#To run the first part of the tool highlight lines 19 through 25, below, and then click 
# the Run icon in the upper right corner of this pane. After the first section finishes, highlight
# lines 28 through 31, below, and then click the Run icon in the upper right corner of this pane
# When the second section is complete, close R Studio.


#Unistall arcgisbinding package
remove.packages(arcgisbinding)

# Redirect R profile
source('https://raw.githubusercontent.com/ncss-tech/soilReports/master/R/installRprofile.R')installRprofile(overwrite=TRUE)

#Wait a few seconds for the R section to restart
.rs.restartR()

#Install packages needed for the report generator
install.packages(c("flextable", "knitr", "rmarkdown", "textreader", "xlsx"), dependencies = TRUE)

#Install arcgidbinding package
install.packages("arcgisbinding", repos = "https://r.esri.com", type = "win.binary")