Sys.setenv(RSTUDIO_PANDOC = "C:/Program Files/RStudio/bin/pandoc")

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
  require(xlsx)
  require(rmarkdown)
  require(knitr)
  require(flextable)
  require(textreadr)
  
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
  CLU_CWD_026_Excel_Path <- in_params$CLU_CWD_026_Excel_Path
  CLU_CWD_028_Excel_Path <- in_params$CLU_CWD_028_Excel_Path
  Create_028 <- in_params$Create_028

#out_params is output_file + file name 
  Wetlands_Folder_Path <- out_params$Wetlands_Folder_Path

  # Generate customer letter
  arc.progress_label('Creating customer letter...')
  arc.progress_pos(20)
  
  rmarkdown::render("C:/GIS_Tools/NRCS_Wetland_Tools_Pro/SUPPORT/Templates/WC_CustomerLetter.Rmd",
                    output_file = "WC_Letter", output_dir = Wetlands_Folder_Path)

  # Generate CPA026
  arc.progress_label('Creating CPA-026 report...')
  arc.progress_pos(40)
  
  rmarkdown::render("C:/GIS_Tools/NRCS_Wetland_Tools_Pro/SUPPORT/Templates/NRCS-CPA-026-WC-Form.Rmd",
                    output_file = "NRCS-CPA-026-WC-Form", output_dir = Wetlands_Folder_Path)
  
  # Generate CPA028
  arc.progress_label('Creating CPA-028 report...')
  arc.progress_pos(60)
  
  if(Create_028 == "Yes"){
  rmarkdown::render("C:/GIS_Tools/NRCS_Wetland_Tools_Pro/SUPPORT/Templates/NRCS-CPA-028-WC-Form.Rmd",
                    output_file = "NRCS-CPA-028-WC-Form", output_dir = Wetlands_Folder_Path)
  }
  
  arc.progress_label('Wait for documents to open in MS-Word')
  arc.progress_pos(100)
  
  filepath <- Wetlands_Folder_Path
  browseURL(file.path("file:/", filepath, "WC_Letter.docx"))
  
  filepath <- Wetlands_Folder_Path
  browseURL(file.path("file:/", filepath, "NRCS-CPA-026-WC-Form.docx"))
  
  if(Create_028 == "Yes"){
  filepath <- Wetlands_Folder_Path
  browseURL(file.path("file:/", filepath, "NRCS-CPA-028-WC-Form.docx"))
  }
  
  return(out_params)
}
