# 05. Get water use from WIMAS for wells in watersheds 

# TO DO: Update GridMET data download period to include all of 1979, and once available, 2024, so water use can be estimated.
#        Get 2023 WIMAS data from Brownie.

library(sf)
library(tidyverse)

gauges <- file.path("data", "gauges.csv") |>
  read_csv(show_col_types = F) 

gauge_ids <- gauges$gauge_id

watersheds <- file.path("data", "spatial", "general", "watersheds_perennial_extents.shp") |>
  st_read(quiet = T)

active_domain <- file.path("data", "spatial", "MODFLOW", "domain.shp") |>
  st_read(quiet = T) |>
  filter(active == 1) 

print( file.path("data", "spatial", "wimas+wizard_data.gdb")  |> st_layers() )

wimas_pumping <- file.path("data", "spatial", "wimas+wizard_data.gdb") |>
  st_read(layer = "wimas_pdivs_pumping", quiet = T) |>
  select(PDIV_ID, contains("AF"), geometry = Shape)

watersheds <- st_transform(watersheds, crs = st_crs(wimas_pumping))
active_domain <- st_transform(active_domain, crs = st_crs(wimas_pumping))

precip <- map(gauge_ids, ~{
  read_csv(file.path("data", "climatepy", paste0(.x, ".csv")),
           col_select = c("gauge_id", "date", "pr"), show_col_types = F)
  }) |>
  bind_rows()

precip_annual <- precip |>
  mutate(
    year = year(date),
    ) |>
  group_by(gauge_id, year) |>
  summarise(
    precip_mm = sum(pr),
    #precip_summer_mm = sum(if_else(month(date) >= 4 & month(date) <= 9, pr, 0)),
    #precip_summer_frac = (precip_summer_mm / precip_mm) |> round(digits = 2)
    ) |>
  ungroup() 

res <- list()

for (i in seq_along(gauge_ids)){
  
  watershed <- filter(watersheds, gauge_id == gauge_ids[i])
  watershed_precip <- filter(precip_annual, gauge_id == gauge_ids[i] & (year >= 1980 & year <= 2023)) # estimate relationship with complete years
  watershed_wells <- st_filter(wimas_pumping, watershed) 
  
  MODFLOW_domain_wells <- suppressWarnings(st_filter(wimas_pumping, st_intersection(watershed, active_domain)) |> _$PDIV_ID |> unique())
  
  water_use_per_well <- watershed_wells |>
    as_tibble() |>
    select(PDIV_ID, matches("AF_USED_\\d{4}|AF_USED_(IRR|MUN|STK|IND|REC)_\\d{4}")) |>
    mutate_if(is.numeric, round, 2) |>
    pivot_longer(cols = -PDIV_ID, values_to = "water_use") |>
    mutate(
      year = str_extract(name, "\\d{4}") |> as.numeric(),
      sector = case_when(str_detect(name, "AF_USED_(IRR|MUN|STK|IND|REC)") ~ str_extract(name, "IRR|MUN|STK|IND|REC"),
                         TRUE ~ "ALL"),
      sector = case_when(sector == "ALL" ~ "total",
                         sector == "IRR" ~ "irrigation",
                         sector == "MUN" ~ "municipal",
                         sector == "IND" ~ "industrial",
                         sector == "STK" ~ "stockwater",
                         sector == "REC" ~ "recreation")
      ) |>
    select(PDIV_ID, year, sector, water_use) |>
    group_by(PDIV_ID, sector) |>
    filter(!(all(water_use == 0))) |>  # remove cases water use is 0 for each well and sector
    ungroup()|>
    pivot_wider(names_from = sector, values_from = water_use) |>
    mutate(type = case_when(!is.na(irrigation) ~ "irrigation",
                            !is.na(municipal) ~ "municipal",
                            !is.na(industrial) ~ "industrial",
                            !is.na(recreation) ~ "recreation",
                            !is.na(stockwater) ~ "stockwater",
                            TRUE ~ NA),
           gauge_id = gauge_ids[i]
           ) |>
    select(gauge_id, PDIV_ID, year, type, irrigation, municipal, industrial, stockwater, recreation, total) |>
    mutate(
      MODFLOW_domain = PDIV_ID %in% MODFLOW_domain_wells 
      )
  
  water_use_per_domain <- water_use_per_well |>
    pivot_longer(cols = -c(gauge_id, PDIV_ID, year, type, MODFLOW_domain), names_to = "sector", values_to = "water_use") |>
    group_by(year, sector, MODFLOW_domain) |>
    summarise(
      gauge_id = unique(gauge_id),
      water_use = sum(water_use, na.rm = T)
    ) |>
    ungroup() |>
    pivot_wider(names_from = c("sector", "MODFLOW_domain"), values_from = "water_use",
                names_glue = "{if_else(MODFLOW_domain, 'modflow', 'outside')}_{sector}") |>
    select(gauge_id, year, 
           outside_irrigation, outside_municipal, outside_industrial, outside_stockwater, outside_recreation, outside_total,
           modflow_irrigation, modflow_municipal, modflow_industrial, modflow_stockwater, modflow_recreation, modflow_total) 
  
  water_use_per_sector <- water_use_per_well |>
    pivot_longer(cols = -c(gauge_id, PDIV_ID, year, type), names_to = "sector", values_to = "water_use") |>
    group_by(year, sector) |>
    summarise(
      gauge_id = unique(gauge_id),
      water_use = sum(water_use, na.rm = T)
    ) |>
    ungroup() |>
    pivot_wider(names_from = "sector", values_from = "water_use") |>
    select(gauge_id, year, irrigation, municipal, industrial, stockwater, recreation, total) 
  
  water_use_per_sector <- left_join(water_use_per_sector, water_use_per_domain, by = c("gauge_id", "year"))
  
  pp <- left_join(watershed_precip, water_use_per_sector, by = c("gauge_id", "year"))
  
  # we estimate a linear model between precip and pumping to hindcast historical water use before the WIMAS program started
  # water use [acre-ft] = β0 + β1 * precip [mm] + error
  model = lm(irrigation ~ precip_mm, data = pp |> filter(year >= 1990 & year < 2023)) 

  model_fit <- tibble(guage_id = gauge_ids[i],
                      model = list(model),
                      r_squared = !!summary(model)$r.squared)
  
  pp <- pp |>
    # estimate historical irrigation withdrawals using precip-pumping relationship
    mutate(
      irrigation = if_else(is.na(irrigation), predict(model, newdata = pp), irrigation),
      outside_irrigation = irrigation * mean(outside_irrigation / irrigation, na.rm = T),
      modflow_irrigation = irrigation * mean(modflow_irrigation / irrigation, na.rm = T)
      ) |>
    # row-wise sum across other water use types
    rowwise() |>
    mutate(
      other_water_use = sum(municipal, industrial, stockwater, recreation),
      outside_other_water_use = sum(outside_municipal, outside_industrial, outside_stockwater, outside_recreation),
      modflow_other_water_use = sum(modflow_municipal, modflow_industrial, modflow_stockwater, modflow_recreation),
    ) |>
    ungroup() |>
    # set historical other water use as the minimum amount reported
    mutate(
      other_water_use = if_else(is.na(other_water_use), min(other_water_use, na.rm = T), other_water_use),
      outside_other_water_use = if_else(is.na(outside_other_water_use), min(outside_other_water_use, na.rm = T), outside_other_water_use),
      modflow_other_water_use = if_else(is.na(modflow_other_water_use), min(modflow_other_water_use, na.rm = T), modflow_other_water_use)
      ) |>
    select(gauge_id, year, precip_mm, 
           irrigation, other_water_use, 
           outside_irrigation, outside_other_water_use,
           modflow_irrigation, modflow_other_water_use)
  
  res[[gauge_ids[i]]] <- list(pp, model_fit, water_use_per_sector, water_use_per_well)
  
  rm(watershed, watershed_precip, watershed_wells, water_use_per_well, water_use_per_domain, water_use_per_sector, pp, model, model_fit)
  
}

water_use_estimated <- map(res, ~ .x[[1]]) |> bind_rows() |>
  mutate(
    irrigation = irrigation / 182.5,
    other_water_use = other_water_use / 365.25,
    combined_water_use = irrigation + other_water_use,
    outside_irrigation = outside_irrigation / 182.5,
    outside_other_water_use = outside_other_water_use / 365.25,
    modflow_irrigation = modflow_irrigation / 182.5,
    modflow_other_water_use = modflow_other_water_use / 365.25,
  ) |>
  # conversion factor from https://pubs.usgs.gov/publication/70039401
  # acre-ft per year to m3/d
  # mutate(
  #   irrigation = (irrigation * 1233) / 182.5,
  #   other_water_use = (other_water_use * 1233) / 365.25,
  #   outside_irrigation = (outside_irrigation * 1233) / 182.5,
  #   outside_other_water_use = (outside_other_water_use * 1233) / 365.25,
  #   modflow_irrigation = (modflow_irrigation * 1233) / 182.5,
  #   modflow_other_water_use = (modflow_other_water_use * 1233) / 365.25,
  # ) |>
  mutate_if(is.numeric, round, 2)
write_csv(water_use_estimated, file.path("data", "water_use.csv")) # output is saved as m3/d

model_fits <- map(res, ~ .x[[2]]) |> bind_rows()
print(paste("Median model performance:", median(model_fits$r_squared) |> round(digits=2)))

water_use_per_sector <- map(res, ~ .x[[3]]) |> bind_rows()

water_use_per_well <- map(res, ~ .x[[4]]) |> bind_rows()

