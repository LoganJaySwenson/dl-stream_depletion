# 10. Perform sensitivity analysis of pumping rates
from pathlib import Path

import pandas as pd

from datautils import prepare_generic_dataset_folder
from modelutils import evaluate_model

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


# Perturb water use by [0, 1.0, 0.1]
pumping_fracs = [round(num * 0.10, 2) for num in range(10 + 1)]
experiments = [f"sensitivity_experiment_{num}" for num in pumping_fracs]

for frac, experiment in zip(pumping_fracs, experiments):
    
    prepare_generic_dataset_folder(gauge_ids = gauge_ids, 
                                   experiment_name = experiment,
                                   meteorological_variables = meteorological_variables,
                                   water_use_variables = water_use_variables,
                                   attribute_variables = attribute_variables,
                                   target = target,
                                   dates = dates,
                                   historical = True,
                                   variable_perturbations = {"combined_water_use": [frac, pd.to_datetime("1980-10-01"), pd.to_datetime("2023-09-30")]}
                                  )


# Evaluate trained model with perturbed water use
import warnings

with warnings.catch_warnings():
    warnings.simplefilter(action="ignore", category=FutureWarning)
    
    for experiment in experiments:
        evaluate_model(model_name = "historical_trained",
                       periods = ["train", "validation", "test"], 
                       epoch=30, 
                       experiment_name = experiment)


save_dir = Path("models", "DL", "outputs")

performance_metrics = list(map(lambda path: pd.read_csv(path, dtype={"gauge_id": str}), [save_dir / "sensitivity_experiment_1.0_performance_metrics.csv", save_dir / "sensitivity_experiment_0.0_performance_metrics.csv"]))

performance_metrics = pd.concat(performance_metrics)

performance_metrics["gauge_id"] = pd.Categorical(
    performance_metrics["gauge_id"],
    categories=gauge_ids,
    ordered=True
)

performance_metrics["period"] = pd.Categorical(
    performance_metrics["period"],
    categories=["train", "validation", "test"],
    ordered=True
)

performance_metrics["experiment"] = pd.Categorical(
    performance_metrics["experiment"],
    categories=["sensitivity_experiment_1.0", "sensitivity_experiment_0.0"],
    ordered=True
)

performance_metrics.groupby(["period", "experiment"], observed=True).median(numeric_only=True)