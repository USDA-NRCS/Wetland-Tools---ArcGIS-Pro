#Script developed to streamline the installation and setup of all the necessary packages in R for the report development as part of the Wetland Compliance tool.
#Chris Morse - GIS Specialist, IN
#Edwin Muniz - State Soil Scientist, NJ
#October 27, 2022.

#This version install the textreadr package from the archive location.


#This script runs in three parts. The first part removes existing arcgisbinding packages that may
# be installed in the documents folder. The second part redirects the local packages library for
# R to conform to the soil survey division's configuration for R. The third part installs all R packages
# needed for the WC Tool.

#Run one line at a time by highlight the code line, below (lines without #), and then click 
# the Run icon in the upper right corner of this pane. During each line installation a STOP sign
# may show in the upper left corner of the Console pane (below) that mean that the installation
# is in progress do not interrupt the installation and wait for the blinking cursor in the Console pane.
# After the installation is complete close R Studio.


#Unistall arcgisbinding package
remove.packages(arcgisbinding)

# Redirect R profile
# Line 1
source('https://raw.githubusercontent.com/ncss-tech/soilReports/master/R/installRprofile.R')

#Line 2
installRprofile(overwrite=TRUE)

#Wait a few seconds for the R section to restart
.rs.restartR()

#Install packages needed for the report generator
install.packages(c("stringi", "flextable", "knitr", "rmarkdown", "xlsx", "dbplyr"), dependencies = TRUE)

install.packages("devtools")
require(devtools)
install_version("textreadr", version = "1.2.0", repos = "https://cran.r-project.org/")

#Install arcgidbinding package
install.packages("arcgisbinding", repos = "https://r.esri.com", type = "win.binary")