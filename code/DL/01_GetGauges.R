# 01. Get USGS stream gauges in GMD2 for streamflow depletion models
library(sf)
library(tidyverse)

period_of_record <- function(flows){
  
  gauge_ids <- unique(flows$gauge_id)
  periods <- tibble()
  
  for (i in seq_along(gauge_ids)){
    
    flow <- filter(flows, gauge_id == gauge_ids[i])
    
    start <- min(flow$date[!is.na(flow$date)], na.rm = T)
    end <- max(flow$date[!is.na(flow$date)], na.rm = T)
    
    periods <- bind_rows(periods, 
                         tibble(gauge_id = gauge_ids[i],
                                start = start,
                                end = end
                         )
    )
  }
  
  return(periods)
}

# Get a list of stream gauges in GMD2
GMD2 <- file.path("data", "spatial", "general", "gmds.shp") |>
  st_read(quiet = T) |> 
  st_transform(crs = 4326) |>
  filter(NAME == "Equus Beds GMD #2")

states <- c("KS")
gauges <- tibble()

for (i in seq_along(states)){
  gauges <- bind_rows(gauges,
                      as_tibble(dataRetrieval::whatNWISsites(stateCd = states[i],
                                                 parameterCd = "00060",
                                                 outputDataTypeCd = "dv")) |>
                        rename_with(.cols = everything(), tolower) |>
                        rename(gauge_id = site_no,
                               lat = dec_lat_va, 
                               lon = dec_long_va) |>
                        select(gauge_id, station_nm, lat, lon)
                      )
}

gauges <- st_as_sf(gauges, coords = c("lon", "lat"), crs = 4326) 

gauges <- st_filter(gauges, GMD2) 


# Get start & end of flow records for stream gauges in GMD2
gauge_ids <- gauges$gauge_id
flow <- tibble()

for (i in seq_along(gauge_ids)) {
  flow <- bind_rows(flow,
                    as_tibble(dataRetrieval::readNWISdv(siteNumber = gauge_ids[i], 
                                                        parameterCd = "00060", 
                                                        startDate = "1979-10-01")) |>
                      dataRetrieval::renameNWISColumns() |>
                      rename_with(.cols = everything(), tolower) |>
                      rename(gauge_id = site_no)
                    )
}

flow <- select(flow, gauge_id, date, flow)

gauges <- left_join(gauges, period_of_record(flow), by = c("gauge_id")) 

gauges <- drop_na(gauges) # remove gauges without coordinates

gauges <- gauges |>
  mutate(
    record = as.numeric(difftime(end, start, units = "days") / 365.25),
    lon = map(geometry, ~ .x[1]) |> unlist(),  
    lat = map(geometry, ~ .x[2]) |> unlist()
  ) |>
  filter(record > 20 & year(end) == 2024) |> # we select gauges with 20 years of flow observations for streamflow depletion models
  tibble() |>
  select(-geometry)  

write_csv(gauges, file.path("data", "gauges.csv"))

