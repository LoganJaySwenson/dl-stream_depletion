# 02. Get watershed areas for stream gauges
library(sf)
library(tidyverse)

gauges <- file.path("data", "gauges.csv") |>
  read_csv(show_col_types = F) |>
  st_as_sf(coords = c("lon", "lat"), crs = 4326)

gauge_ids <- gauges$gauge_id

# Search NHDPlus for watershed areas.
NHDplus_watersheds <- file.path("C:", "Users", "Logan", "Downloads", "USGS_GageLoc", "NHDplus", "NHDplus_basins_all.gpkg") |>
  st_read(quiet=T) |>
  rename_all(tolower) |>
  rename(gauge_id = site_no,
         geometry = geom,
         area_mi = sqmi)

watersheds <- NHDplus_watersheds |>
  filter(gauge_id %in% gauge_ids) |>
  mutate(area_km = round(area_mi * 2.59)) |>
  select(gauge_id, area_km, geometry) |>
  st_transform(crs = 4326) |>
  arrange(area_km)

gauges <- left_join(gauges, 
                    watersheds |> tibble() |> select(gauge_id, area_km), 
                    by = "gauge_id") |>
  arrange(area_km)


# We set our model focus to the perennial part of the Arkansas River, and stream-aquifer interactions occurring in the Equus Beds Aquifer 
point_coords <- dataRetrieval::whatNWISsites(siteNumber = "07141220", 
                                             parameterCd = "00060",
                                             outputDataTypeCd = "dv") |>
  rename_with(.cols = everything(), tolower) |>
  rename(gauge_id = site_no,
         lat = dec_lat_va,
         lon = dec_long_va) |>
  select(gauge_id, station_nm, lat, lon) |>
  st_as_sf(coords = c("lon", "lat"), crs = 4326) |>
  st_coordinates()

gauge.ids <- watersheds$gauge_id[watersheds$area_km >= 1e4]

extents <- tibble()

for (i in seq_along(gauge.ids)){

    watershed <- filter(watersheds, gauge_id == gauge.ids[i]) 
    
    watershed_coords <- st_bbox(watershed)
    
    watershed <-lwgeom::st_split(watershed, 
                                 matrix(c(point_coords[1], watershed_coords[2],
                                          point_coords[1], watershed_coords[4]),
                                        ncol = 2, byrow = T) |>
                                   st_linestring() |>
                                   st_sfc(crs = 4326)
                                 ) |>
      st_collection_extract("POLYGON") |>
      slice_tail(n = 1) 
  
  rownames(watershed) <- NULL 
  
  extents <- rbind(extents, watershed)

}

watersheds_extents <- rbind(watersheds |> filter(!gauge_id %in% gauge.ids), extents) |>
  mutate(
    active_area = round(st_area(geometry) |> units::drop_units() |> as.vector() / 1e6),
    active_frac = round(active_area / area_km, digits = 2)
    ) |>
  select(gauge_id, area_km, active_area, active_frac, geometry)

gauges <- gauges |>
  mutate(
    lon = map(geometry, ~ .x[1]) |> unlist(),  
    lat = map(geometry, ~ .x[2]) |> unlist()
  ) |>
  tibble() |>
  select(-geometry)  

write_csv(gauges, file.path("data", "gauges.csv"))

st_write(watersheds, file.path("data","spatial", "general", "watersheds.shp"), overwrite = T, append=F)
st_write(watersheds_extents |> rename(act_area = active_area,
                                      act_frac = active_frac),
         file.path("data","spatial", "general", "watersheds_perennial_extents.shp"), overwrite = T, append=F)

