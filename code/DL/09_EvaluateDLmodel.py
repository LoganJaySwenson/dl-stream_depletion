# 09. Evaluate LSTM model
from pathlib import Path

import pandas as pd

from modelutils import update_config_paths, evaluate_model

gauges = pd.read_csv(Path("data", "gauges.csv"), dtype={"gauge_id":str})

gauge_ids = gauges["gauge_id"]


# 1. Simulate baseflow in historical and baseline experiments

# Update config paths from high-performance computer
update_config_paths(run_id = "historical_conditions_0301_144142", 
                    model_name = "historical_trained",
                    experiment_name = "historical", 
                    historical = True)

# Evaluate trained model on historical and baseline scenarios
import warnings

experiments = ["historical", "baseline"]

with warnings.catch_warnings():
    warnings.simplefilter(action="ignore", category=FutureWarning)
    
    for experiment in experiments:
        evaluate_model(model_name = "historical_trained",
                       periods = ["train", "validation", "test"], 
                       epoch=30, 
                       experiment_name = experiment)

# Performance across all benchmarking locations
save_dir = Path("models", "DL", "outputs")

performance_metrics = list(map(lambda path: pd.read_csv(path, dtype={"gauge_id": str}), [save_dir / "historical_performance_metrics.csv", save_dir / "baseline_performance_metrics.csv"]))

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
    categories=["historical", "baseline"],
    ordered=True
)

performance_metrics.groupby(["period", "experiment"], observed=True).median(numeric_only=True)

# Performance at each benchmarking location
performance_metrics.groupby(["period", "experiment", "gauge_id"], observed=True).median(numeric_only=True)




# 2. Simulate baseflow in historical and baseline experiments where irrigation and other water use are split according to the MODFLOW model domain- possibly for a more direct comparison? 

# Update config paths from high-performance computer
update_config_paths(run_id = "historical_conditions_domain_0401_120614", 
                    model_name = "historical_domain_trained",
                    experiment_name = "historical_domain", 
                    historical = True)

# Evaluate trained model
import warnings

experiments = ["historical_domain", "baseline_domain", "baseline_modflow_domain"]

with warnings.catch_warnings():
    warnings.simplefilter(action="ignore", category=FutureWarning)
    
    for experiment in experiments:
        evaluate_model(model_name = "historical_domain_trained",
                       periods = ["train", "validation", "test"], 
                       epoch=30, 
                       experiment_name = experiment)

# Performance across all benchmarking locations
save_dir = Path("models", "DL", "outputs")

performance_metrics = list(map(lambda path: pd.read_csv(path, dtype={"gauge_id": str}), [save_dir / "historical_domain_performance_metrics.csv", save_dir / "baseline_domain_performance_metrics.csv", save_dir / "baseline_modflow_domain_performance_metrics.csv"]))

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
    categories=["historical_domain", "baseline_domain", "baseline_modflow_domain"],
    ordered=True
)

performance_metrics.groupby(["period", "experiment"], observed=True).median(numeric_only=True)




# experiment_names = ["historical", "baseline"]

# experiments = {}

# for experiment_name in experiment_names:

#     experiment_folder = Path("model_comparison", "DL")
    
#     file_path = experiment_folder / f"{experiment_name}_timeseries.csv"
    
#     if file_path.exists():
#         experiments[experiment_name] = pd.read_csv(file_path, dtype={"gauge_id": str}, parse_dates=["date"])
#     else:
#         print(f"{experiment_name} not found in {experiment_folder}.")

# for i, experiment_name in enumerate(experiments):

#     if i == 0:
#         historical_conditions = (pd.Series(gauge_ids, name="gauge_id")
#                                  .to_frame()
#                                  .merge(experiments[experiment_name], on=["gauge_id"], how="left")
#                                 )
                                 
#     else:
#         historical_conditions = historical_conditions.merge(experiments[experiment_name], on=["gauge_id", "date", "baseflow_obs"], how="left")


# historical_conditions

