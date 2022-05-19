# Created by Edwin Muniz, May 11, 2022

Sys.setenv(RSTUDIO_PANDOC = "C:/Program Files/RStudio/bin/quarto/bin")

#Set working directory from tool default

tool_exec <- function(in_params, out_params)
{
  if (!requireNamespace("xlsx", quietly = TRUE))
    install.packages("xlsx")
  if (!requireNamespace("rmarkdown", quietly = TRUE))
    install.packages("rmarkdown")
  if (!requireNamespace("knitr", quietly = TRUE))
    install.packages("knitr")
  if (!requireNamespace("flextable", quietly = TRUE))
    install.packages("flextable")
  if (!requireNamespace("textreadr", quietly = TRUE))
    install.packages("textreadr")
  if (!requireNamespace("dbplyr", quietly = TRUE))
    install.packages("dbplyr")
  require(xlsx)
  require(rmarkdown)
  require(knitr)
  require(flextable)
  require(textreadr)
  require(dbplyr)
  
  arc.progress_label('Loading required dataset...')
  arc.progress_pos(0)

  print(paste0(
    'Input parameter names: `', paste(names(in_params), collapse =  '`, `'), '`' 
  ))
  print(paste0(
    'Output parameter names: `', paste(names(out_params), collapse =  '`, `'), '`' 
  ))
  
#Get input/ouput paramenters
  Admin_Excel_Path <- in_params$Admin_Excel_Path
  CLU_CWD_028_Excel_Path <- in_params$CLU_CWD_028_Excel_Path
  Path_to_the_install_directory <- in_params$Path_to_the_install_directory

#out_params is output_file + file name 
  Wetlands_Folder_Path <- out_params$Wetlands_Folder_Path
  
  # Generate CPA028
  arc.progress_label('Creating CPA-028 report...')
  arc.progress_pos(60)
  
  rmarkdown::render(file.path(Path_to_the_install_directory, "Templates","NRCS-CPA-028-WC-Form.Rmd"),
                    output_file = "NRCS-CPA-028-WC-Form", output_dir = Wetlands_Folder_Path)

  
  arc.progress_label('Wait for documents to open in MS-Word')
  arc.progress_pos(100)
  
  filepath <- Wetlands_Folder_Path
  browseURL(file.path("file:/", filepath, "NRCS-CPA-028-WC-Form.docx"))

  return(out_params)
}
