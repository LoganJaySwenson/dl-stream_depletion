# 06. Get watershed attributes for stream gauges

library(tidyverse)

gauges <- file.path("data", "gauges.csv") |>
  read_csv(show_col_types = F) 

gauge_ids <- gauges$gauge_id

dir_save <- file.path("data", "attributes")
dir.create(dir_save)

# drainage area at each stream gauge
write_csv(select(gauges, 
                 gauge_id, drainage_area = area_km),
          file = file.path(dir_save, paste0("drainage_area.csv"))
          )

# flow stats 
flow <- file.path("data", "flow.csv") |>
  read_csv(show_col_types = F) |>
  mutate(year = year(date)) |>
  group_by(gauge_id, year) |>
  summarise(
    annual_min_flow = min(flow_cfs),
    annual_max_flow = max(flow_cfs),
    annual_average_flow = mean(flow_cfs)
  ) |>
  ungroup() |>
  group_by(gauge_id) |>
  summarise(
    annual_min_flow = mean(annual_min_flow),
    annual_max_flow = mean(annual_max_flow),
    annual_average_flow = mean(annual_average_flow)
  ) |>
  ungroup() |>
  arrange(match(gauge_id, gauge_ids)) |>
  mutate_if(is.numeric, round, digits=2)

write_csv(select(flow, 
                 gauge_id, annual_min_flow),
          file = file.path(dir_save, paste0("annual_min_flow.csv"))
          )

write_csv(select(flow, 
                 gauge_id, annual_max_flow),
          file = file.path(dir_save, paste0("annual_max_flow.csv"))
          )

write_csv(select(flow, 
                 gauge_id, annual_average_flow),
          file = file.path(dir_save, paste0("annual_average_flow.csv"))
          )

# climate stats (precip, reference evapotranspiration, & aridity)
climate <- map(gauge_ids, ~{
  read_csv(file.path("data", "climatepy", paste0(.x, ".csv")),
           col_select = c("gauge_id", "date", "pr", "etr"), show_col_types = F)
}) |>
  bind_rows() |>
  arrange(match(gauge_id, gauge_ids)) |>
  mutate(year = year(date)) |>
  group_by(gauge_id, year) |>
  summarise(
    annual_precip = sum(pr),
    annual_etr = sum(etr)
  ) |>
  ungroup() |>
  group_by(gauge_id) |>
  summarise(
    annual_precip = mean(annual_precip),
    annual_etr = mean(annual_etr),
    aridity = annual_precip /annual_etr
  ) |>
  ungroup()|>
  arrange(match(gauge_id, gauge_ids)) |>
  mutate_if(is.numeric, round, digits = 2)


write_csv(select(climate, 
                 gauge_id, annual_precip),
          file = file.path(dir_save, paste0("annual_precip.csv"))
          )

write_csv(select(climate, 
                 gauge_id, annual_etr),
          file = file.path(dir_save, paste0("annual_etr.csv"))
          )

write_csv(select(climate, 
                 gauge_id, aridity),
          file = file.path(dir_save, paste0("aridity.csv"))
          )

# a few Caravan attributes derived from the codes in Kratzert et al. (2023)
caravan_attributes<- c(
  "run_mm_syr",   # land surface runoff (mm)
  "gwt_cm_sav",   # GW depth, spatial mean (cm)
  "ele_mt_sav",   # elevation, spatial mean (m)
  "slp_dg_sav",   # slope, spatial mean (°x10)
  "for_pc_sse",   # forest cover extent (%)
  "crp_pc_sse",   # crop cover extent (%)
  "pst_pc_sse",   # pasture cover extent (%)
  "ire_pc_sse",   # irrigated area extent (%)
  "cly_pc_sav",   # clay fraction (%)
  "slt_pc_sav",   # silt fraction (%)
  "snd_pc_sav",   # sand fraction (%)
  "rev_mc_usu",   # reservoir volume at pour point
  "dor_pc_pva",   # degree of regulation, index at pour point
  "ria_ha_usu",   # river area at pour point
  "riv_tc_usu"   # river volume at pour point
  #"moisture_index", # Mean annual moisture index in range [−1, 1], where −1 indicates water-limited conditions and 1 energy-limited conditions
  #"seasonality",  # Moisture index seasonality in range [0, 2], where 0 indicates no changes in the water/energy budget throughout the year and 2 indicates a change from fully arid to fully humid.
)

attributes <- file.path("data", "caravan_attributes.csv") |>
  read_csv(col_select = c("gauge_id",all_of(caravan_attributes)), show_col_types = F) |>
  arrange(match(gauge_id, gauge_ids)) |>
  rename(
    land_surface_runoff = run_mm_syr,
    groundwater_depth = gwt_cm_sav,
    elevation = ele_mt_sav,
    slope = slp_dg_sav,
    forest_cover = for_pc_sse,
    crop_cover = crp_pc_sse,
    pasture_cover = pst_pc_sse,
    irrigated_area = ire_pc_sse,
    clay = cly_pc_sav,
    silt = slt_pc_sav,
    sand = snd_pc_sav,
    reserivor_volume = rev_mc_usu,
    degree_regulated = dor_pc_pva,
    river_area = ria_ha_usu, 
    river_volume = riv_tc_usu
    ) |>
  mutate_if(is.numeric, round, digits = 2)

caravan_attributes <- names(select(attributes, -gauge_id))

map(caravan_attributes, ~{
  write_csv(select(attributes, gauge_id, all_of(.x)), 
            file = file.path(dir_save, paste0(.x, ".csv"))
            )
})

gauges <- gauges |>
  mutate(
    watershed = case_when(
      str_detect(station_nm, "L ARKANSAS") ~ "L Arkansas",
      str_detect(station_nm, "NF NINNESCAH") ~ "NF Ninnescah",
      str_detect(station_nm, "ARKANSAS") ~ "Arkansas",
      TRUE ~ NA),
    watershed_encoded = factor(watershed) |> as.numeric(),
    gauge_id_encoded = factor(gauge_id) |> as.numeric()
    )

write_csv(select(gauges, 
                 gauge_id, watershed_encoded),
          file = file.path(dir_save, paste0("watershed_encoded.csv"))
          )

write_csv(select(gauges, 
                 gauge_id, gauge_id_encoded),
          file = file.path(dir_save, paste0("gauge_id_encoded.csv"))
          )

