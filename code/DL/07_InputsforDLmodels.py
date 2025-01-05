# 07. Process variables to be fed into LSTM model
from pathlib import Path

import pandas as pd

from datautils import prepare_generic_dataset_folder

gauges = pd.read_csv(Path("data", "gauges.csv"), dtype={"gauge_id":str})

gauge_ids = gauges["gauge_id"]

meteorological_variables = ["pr", "tmmn", "tmmx", "rmin", "rmax", "sph", "vs", "srad", "etr"]

water_use_variables = ["combined_water_use"]

attribute_variables = ["drainage_area", "elevation", "slope",
                       "annual_precip", "annual_etr", "aridity",
                       "annual_average_flow", "annual_max_flow", "annual_min_flow",
                       "crop_cover", "irrigated_area", "pasture_cover", "forest_cover",
                       "sand", "silt", "clay",
                       "degree_regulated", "reserivor_volume", "river_area", "river_volume",
                       "groundwater_depth", "land_surface_runoff",
                       "gauge_id_encoded", "watershed_encoded"]

target = ["baseflow"]

dates = ["1980-10-01", "2023-09-30"]


# Lumped irrigation and other water use for each watershed

print("Historical simulation (irrigation incuded)")

data_dir = prepare_generic_dataset_folder(gauge_ids = gauge_ids, 
                                          experiment_name = "historical",
                                          meteorological_variables = meteorological_variables,
                                          water_use_variables = water_use_variables,
                                          attribute_variables = attribute_variables,
                                          target = target,
                                          dates = dates,
                                          historical = True)


print("\nBaseline simulation (no irrigation)")

data_dir = prepare_generic_dataset_folder(gauge_ids = gauge_ids, 
                                          experiment_name = "baseline",
                                          meteorological_variables = meteorological_variables,
                                          water_use_variables = water_use_variables,
                                          attribute_variables = attribute_variables,
                                          target = target,
                                          dates = dates,
                                          historical = True,
                                          variable_perturbations = {"combined_water_use": ["0", pd.to_datetime("1980-10-01"), pd.to_datetime("2023-09-30")]}
                                         )




# Irrigation and other water use split according to the MODFLOW model domain- possibly a more direct comparison?
water_use_variables = ["outside_irrigation", "outside_other_water_use",
                      "modflow_irrigation", "modflow_other_water_use"]

print("Historical simulation (irrigation incuded)")

data_dir = prepare_generic_dataset_folder(gauge_ids = gauge_ids, 
                                          experiment_name = "historical_domain",
                                          meteorological_variables = meteorological_variables,
                                          water_use_variables = water_use_variables,
                                          attribute_variables = attribute_variables,
                                          target = target,
                                          dates = dates,
                                          historical = True)


print("\nBaseline simulation (no irrigation)")

data_dir = prepare_generic_dataset_folder(gauge_ids = gauge_ids, 
                                          experiment_name = "baseline_domain",
                                          meteorological_variables = meteorological_variables,
                                          water_use_variables = water_use_variables,
                                          attribute_variables = attribute_variables,
                                          target = target,
                                          dates = dates,
                                          historical = True,
                                          variable_perturbations = {
                                              "outside_irrigation": ["0", pd.to_datetime("1980-10-01"), pd.to_datetime("2023-09-30")],
                                              #"outside_other_water_use": ["0", pd.to_datetime("1980-10-01"), pd.to_datetime("2023-09-30")],
                                              "modflow_irrigation": ["0", pd.to_datetime("1980-10-01"), pd.to_datetime("2023-09-30")],
                                              #"modflow_other_water_use": ["0", pd.to_datetime("1980-10-01"), pd.to_datetime("2023-09-30")]
                                          }
                                         )


print("\nBaseline simulation (no irrigation) in MODFLOW domain")

data_dir = prepare_generic_dataset_folder(gauge_ids = gauge_ids, 
                                          experiment_name = "baseline_modflow_domain",
                                          meteorological_variables = meteorological_variables,
                                          water_use_variables = water_use_variables,
                                          attribute_variables = attribute_variables,
                                          target = target,
                                          dates = dates,
                                          historical = True,
                                          variable_perturbations = {
                                              "modflow_irrigation": ["0", pd.to_datetime("1980-10-01"), pd.to_datetime("2023-09-30")],
                                              #"modflow_other_water_use": ["0", pd.to_datetime("1980-10-01"), pd.to_datetime("2023-09-30")]
                                          }
                                         )