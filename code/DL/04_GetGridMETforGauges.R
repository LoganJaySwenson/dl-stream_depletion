# 04. Get GridMET meteorological forcings for watersheds
library(sf)
library(terra)
library(tidyverse)

gauges <- file.path("data", "gauges.csv") |>
  read_csv(show_col_types = F) 

gauge_ids <- gauges$gauge_id

watersheds <- file.path("data", "spatial", "general", "watersheds_perennial_extents.shp") |>
  st_read(quiet = T)

data.catalog = climateR::catalog

start = as.Date("1979-10-01")
end = as.Date("2024-09-30")

vars = c("pr", "tmmn", "tmmx", "rmin", "rmax", "sph", "vs", "srad", "pet", "etr")

dir_save = file.path("data", "climatepy")

dir.create(dir_save)

for (i in seq_along(gauge_ids)){
  
  watershed <- filter(watersheds, gauge_id == gauge_ids[i])
  
  data = tibble(gauge_id = gauge_ids[i],
                date = seq.Date(start, end, by = "day")
  )
  
  for (j in seq_along(vars)){
    
    download = climateR::getGridMET(AOI = watershed,
                                    varname = vars[j],
                                    startDate = start, 
                                    endDate = end)[[1]]
    
    data[[vars[j]]] <- terra::extract(download, watershed, fun = "mean", na.rm=T, ID=F) |> as.vector() |> as.numeric() |> round(digits = 2)
    
  }
  
  file_path <- file.path(dir_save, paste0(gauge_ids[i], ".csv"))
  
  write_csv(data, file_path)
  
  print(paste(gauge_ids[i], "saved to", dir_save))
  
}

