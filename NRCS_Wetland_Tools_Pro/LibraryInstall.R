#Script developed to streamline the installation and setup of all the necessary packages in R for the report development as part of the Wetland Compliance tool.
#Chris Morse - GIS Specialist, IN
#Edwin Muniz - State Soil Scientist, NJ
#June, 8, 2021.


#To run this script press the control A key to select the script, then click the Run icon located in the upper right of this pane.

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

