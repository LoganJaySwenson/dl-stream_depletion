from pathlib import Path
from typing import List, Tuple, Dict

def update_config_paths(run_id : str,
                        model_name : str,
                        experiment_name : str,
                        historical : bool=True):
    """Update a neuralhydrology model's config filepaths after training on a high-performance cluster.

    Parameters
    ----------
    run_id : str
        Folder name containing the trained model, will be the experiment name and a random identifier. 
    model_name : str
        Name for trained model. 
    experiment_name : str
        Name of folder containing all model inputs for the experiment/GenericDataset class. 
    historical : bool, optional
        Flag indicating whether to use folder for historical conditions (True) or future scenarios (False). By default True.
    """
    from pathlib import Path
    import shutil
    import yaml
    
    # working dir on main computer 
    cpu_dir = Path.cwd()
    
    # folder name 
    if historical:
        base_folder = "historical_conditions"
    else:
        pass
        # placeholder to add support for future climate/management scenarios
    
    if (cpu_dir / "models" / "DL" / run_id).exists():
        (cpu_dir / "models" / "DL" / run_id).rename((cpu_dir / "models" / "DL" / run_id).parent / model_name)
    else:
        pass

    # model run directory on main computer
    run_dir = cpu_dir / "models" / "DL" / model_name
        
    # data dir on main computer
    data_dir = cpu_dir / "models" / "DL" / base_folder / experiment_name
    
    # path to model configs
    cfg_path = run_dir / "config.yml"
    hpc_cfg_path = run_dir / "config_hpc.yml"
    
    if hpc_cfg_path.exists():
        print(f"Config paths have already been updated to {repr(cpu_dir)}")
    else:
        shutil.copy(cfg_path, run_dir / "config_hpc.yml") # save gpu config file for reference or further training 

        # read gpu config file
        with open(cfg_path, 'r') as f:
            cfg = yaml.safe_load(f)

        # paths to be updated for evaluating on cpu
        updates = {
            "data_dir": str(data_dir),
            "run_dir": str(run_dir),
            "train_dir": str(run_dir / "train_data"),
            "img_log_dir": str(run_dir / "img_log"),
            "train_basin_file": str(data_dir / "gauges.txt"),
            "validation_basin_file": str(data_dir / "gauges.txt"),
            "test_basin_file": str(data_dir / "gauges.txt")
        }

        # update those paths in the gpu config file
        cfg.update(updates)
        with open(cfg_path, 'w') as f:
            yaml.dump(cfg, f)
    
        print(f"Config paths updated to {repr(cpu_dir)}")


def update_config_data_dir(model_name : str,
                           experiment_name : str,
                           historical : bool=True):
    """Update a neuralhydrology model's config data_dir filepath to a different one. 
    
    Useful when needing to evaluate baseline or future scenarios with a single trained model.

    Parameters
    ----------
    model_name : str
        Trained model name. 
    experiment_name : str
        Name of folder containing all model inputs for experiment/GenericDataset class. 
    historical : bool, optional
        Flag indicating whether to use folder for historical conditions (True) or future scenarios (False). By default True.
    """
    from pathlib import Path
    import yaml
    
    # working dir on main computer 
    cpu_dir = Path.cwd()

    if historical:
        base_folder = "historical_conditions"
    else:
        pass
        # placeholder to add support for future climate/management scenarios

    # model run directory on main computer
    run_dir = cpu_dir / "models" / "DL" / model_name

    # data dir on main computer
    data_dir = cpu_dir / "models" / "DL" / base_folder / experiment_name
    
    # path to model config
    cfg_path = run_dir / "config.yml" 

    # read gpu config file
    with open(cfg_path, 'r') as f:
        cfg = yaml.safe_load(f)
        
    # paths to be updated for evaluating on cpu
    updates = {
        "data_dir": str(data_dir),
        "train_basin_file": str(data_dir / "gauges.txt"),
        "validation_basin_file": str(data_dir / "gauges.txt"),
        "test_basin_file": str(data_dir / "gauges.txt")
    }

    # update those paths in the gpu config file
    cfg.update(updates)
    with open(cfg_path, 'w') as f:
        yaml.dump(cfg, f)
    
    print(f"Config data_dir path updated to '{experiment_name}'")


def evaluate_model(model_name : str,
                   periods : List[str], 
                   epoch : int,
                   experiment_name : str,
                   historical : bool=True):

    from pathlib import Path
    import pickle
    import pandas as pd
    from neuralhydrology.nh_run import eval_run

    # model run directory on main computer 
    run_dir = Path("models", "DL") / model_name

    # set config path to experiment run dir
    update_config_data_dir(model_name,
                           experiment_name = experiment_name, 
                           historical = historical)
    
    # save folder
    save_folder = Path("models", "DL", "outputs")
    save_folder.mkdir(parents=True, exist_ok=True)
    
    # evaluate trained model
    for period in periods:
        eval_run(run_dir=run_dir, period=period, epoch=epoch, gpu=-1)

    # combine per period output into a single pickle file and timeseries and save to model-comparison folder
    eval_files = {}
    timeseries = []
    
    for period in periods:
        with open(run_dir / period / f"model_epoch{str(epoch).zfill(3)}" / f"{period}_results.p", "rb") as fp:
            eval_files[period] = pickle.load(fp)

        for gauge_id, values in eval_files[period].items():
            df = values["1D"]["xr"].to_dataframe().reset_index().drop(columns=["time_step"]) 
            df["gauge_id"] = gauge_id
            df = df[["gauge_id", "date", "baseflow_obs", "baseflow_sim"]]
            timeseries.append(df)
    
    timeseries = pd.concat(timeseries, ignore_index=True)
    timeseries.rename(columns={"baseflow_sim": f"baseflow_sim_{experiment_name}"}, inplace=True)
    timeseries.to_csv(save_folder / f"{experiment_name}_timeseries.csv", index=False)
    
    with open(save_folder / f"{experiment_name}.p", "wb") as fp:
        pickle.dump(eval_files, fp)

    # save peformance metrics for historical and baseline experiments to model-comparison folder
    if experiment_name in ["historical", "baseline", "historical_domain", "baseline_domain", "baseline_modflow_domain", "sensitivity_experiment_0.0", "sensitivity_experiment_1.0"]:
        performance_metrics = []
        for period in periods:
            period_metrics = pd.read_csv(run_dir / period / f"model_epoch{str(epoch).zfill(3)}" / f"{period}_metrics.csv", dtype={"basin":str})
            period_metrics.rename(columns={"basin": "gauge_id"}, inplace=True)
            period_metrics["period"] = period
            performance_metrics.append(period_metrics)
        performance_metrics = pd.concat(performance_metrics)
        performance_metrics["experiment"] = experiment_name
        performance_metrics.to_csv(save_folder / f"{experiment_name}_performance_metrics.csv", index=False)

