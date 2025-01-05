from pathlib import Path
from typing import List, Tuple, Dict

import pandas as pd

def get_data(gauge_ids : List[str],
             meteorological_variables : List[str],
             water_use_variables : List[str],
             attribute_variables : List[str],
             target : List[str],
             dates : List=None,
             historical : bool=True) -> Tuple[pd.DataFrame, pd.DataFrame]:

    """
    TO DO: add docstring to helper function
    """
    
    if isinstance(gauge_ids, str):
        gauge_ids = [gauge_ids]
    
    meteorological_forcings = pd.DataFrame()
    for gauge_id in gauge_ids:
        meteorological_forcings = pd.concat([meteorological_forcings, 
                                             pd.read_csv(Path("data", "climatepy", gauge_id + ".csv"), 
                                                         usecols = ["gauge_id", "date"] + meteorological_variables,
                                                         dtype={"gauge_id":str},
                                                         parse_dates=["date"])])
    
    flow = pd.read_csv(Path("data", "flow.csv"), usecols = ["gauge_id", "date"] + target, dtype={"gauge_id": str}, parse_dates=["date"])
    water_use = pd.read_csv(Path("data", "water_use.csv"), usecols = ["gauge_id", "year"] + water_use_variables, dtype={"gauge_id": str})
    
    timeseries = (pd.Series(gauge_ids, name="gauge_id")
                  .to_frame()
                  .merge(meteorological_forcings, on=["gauge_id"], how="left")
                  .merge(flow, on=["gauge_id", "date"], how="left")
                  .merge(water_use, left_on=["gauge_id", meteorological_forcings["date"].dt.year], 
                     right_on=["gauge_id", "year"], how="left")
                  .drop(["year"], axis=1))

    if not historical:
        pass
        # placeholder to add support for future climate/management scenarios under a change factor (e.g., +/- 10% annual precip)

    # dates must be between the valid period of record
    period_start = pd.to_datetime("1980-10-01"); period_end = pd.to_datetime("2023-09-30")
    if dates is None:
         timeseries = timeseries[(timeseries["date"] >= period_start) & (timeseries["date"] <= period_end)].reset_index(drop=True)
    else:
        start_date = pd.to_datetime(dates[0])
        end_date = pd.to_datetime(dates[1])
        if start_date < period_start:
            start_date = period_start
        if end_date > period_end:
            end_date = period_end
        timeseries = timeseries[(timeseries["date"] >= start_date) & (timeseries["date"] <= end_date)].reset_index(drop=True)

    for var in water_use_variables:
        timeseries[var] = timeseries[var].where((timeseries["date"].dt.month >= 4) & (timeseries["date"].dt.month <= 9), 0) # set pumping to 0 where pumping season is False


    #timeseries[water_use_variables[0]] = timeseries[water_use_variables[0]].where((timeseries["date"].dt.month >= 4) & (timeseries["date"].dt.month <= 9), 0) # set pumping to 0 where pumping season is False
    
    #timeseries = timeseries.rename(columns={target[0] : "baseflow", water_use_variables[0] : "irrigation"}) # enforce consisent names among variables for model config file purposes, sigh...
    
    attributes = (
        pd.Series(gauge_ids, name="gauge_id")
        .to_frame()
        .merge(
            pd.concat(
                (pd.read_csv(file, dtype={"gauge_id": str}) for file in Path("data", "attributes").glob("*.csv")),
                ignore_index=True
            )
            .groupby("gauge_id", as_index=False)
            .first(),
            on="gauge_id",  
            how="left"      
        )
    )
    attributes = attributes[["gauge_id"] + attribute_variables]

    return timeseries, attributes




def generate_netcdf_files(data_dir : Path) -> Path:
    """Generate netcdf files for neuralhydrology's GenericDataset class. 
    
    Only time-varying variables (i.e., meteorological forcings, water use, & target) are required as .nc files. 

    Parameters
    ----------
    data_dir : Path
        Path to the folder specified in experiment_name. 

    Returns
    -------
    Path
        Path to folder where .nc files are saved to.
    """
    
    from xarray import Dataset, Variable

    data_path = data_dir / "data"
    timeseries_path = data_dir / "time_series"
    
    for file in data_path.iterdir():
        gauge_id = file.stem
            
        data = pd.read_csv(file, dtype={"gauge_id":str})
        data["date"] = pd.to_datetime(data["date"])
            
        dataset = Dataset()
            
        for column in data.columns:
            if column == "date":
                dataset.coords["date"] = data[column].values
            else:
                dataset[column] = Variable("date", data[column].values)
    
        netcdf_file = timeseries_path / (gauge_id + ".nc")
        dataset.to_netcdf(netcdf_file)
        dataset.close()
    print(f"    Timeseries variables saved as netCDF files to: {repr(timeseries_path)}")
    return timeseries_path




def prepare_generic_dataset_folder(gauge_ids : List, 
                                   experiment_name : str,
                                   meteorological_variables : List,
                                   water_use_variables : List,
                                   attribute_variables : List,
                                   target : List,
                                   dates : List,
                                   historical : bool=True,
                                   variable_perturbations : Dict=None) -> Path:
    """Create a folder for neuralhydrology's GenericDataset class (https://neuralhydrology.readthedocs.io/en/latest/api/neuralhydrology.datasetzoo.genericdataset.html)

    All variable names passed will remain the same besides irrigation and target, which will be changed to "irrigation" and "baseflow", respectively. 
    This allows us to use a trained neuralhydrology model for forecasting future scenarios while retaining meaningful variable names in personal files. 

    If historical is False, then historical climate conditions are repeated until the end of the 21st century.
    Use the variable_perturbations option to apply a constant change factor to the historical years (e.g., no irrigation water use, +/- 10% annual precip).

    Parameters
    ----------
    gauge_ids : List
        List of stream gauge ids to to model. 
    experiment_name : str
        Name of folder containing all model inputs for GenericDataset class. 
    meteorological_variables : List
        List of meteorological forcing variable names.
    water_use_variables : List
        List containing the water use variable name.
    attribute_variables : List
        List of static attribute variable names.
    target : List
        List containing the target variable name. 
    dates : List
        List of dates to retrieve model inputs. By default None (i.e., returns all dates). 
    historical : bool, optional
         Flag indicating whether returned model inputs will be used for training/evaluation of historical conditions (True) or for forecasting future scenarios (False). By default True.
    variable_perturbations : Dict, optional
        Dictionary of constant change factors (e.g.,  no irrigation water use, +/- 10% annual precip) to be applied for generating baseline or future climate scenarios. 
        Variable name must be the key and the values must be a list containing change factor, start date, and end date, in that specific order. 
        All variable names as keys will be the same as those in the provided lists above, besides irrigation and target, which will need to be named "water_use" and "baseflow", respectively. 

    Returns
    -------
    Path
        Main directory path to the GenericDataset class folder. 
    """
    
    if historical:
        main_dir = Path("models", "DL", "historical_conditions")
        main_dir.mkdir(parents=True, exist_ok=True)
    else:
        main_dir = Path("models", "DL", "future_scenarios")
        main_dir.mkdir(parents=True, exist_ok=True)
        # placeholder to add support for future climate/management scenarios under a change factor (e.g., +/- 10% annual precip)
    
    # Main dir folder
    data_dir = Path(main_dir / experiment_name)
    data_dir.mkdir(parents=True, exist_ok=True)

    print(f"Data folder created at: {repr(data_dir)}")

    # Required sub-folders
    (data_dir / "data").mkdir(parents=True, exist_ok=True)
    (data_dir / "time_series").mkdir(parents=True, exist_ok=True)
    (data_dir / "attributes").mkdir(parents=True, exist_ok=True)

    
    # 1. List of stream gauge ids 
    with open(data_dir / "gauges.txt", "w") as file:
        for gauge_id in gauge_ids:
            file.write(str(gauge_id) + "\n")
    print(f"    USGS gauges to be modeled: {len(gauge_ids)}")

    
    # Get time-varying forcings, target, & attributes 
    timeseries, attributes = get_data(gauge_ids, meteorological_variables, water_use_variables, attribute_variables, target, dates, historical=True)


    # Apply variable pertrubations
    if variable_perturbations:
        timeseries["date"] = pd.to_datetime(timeseries["date"])

        for variable, values in variable_perturbations.items():
            if variable in timeseries.columns:
                perturbation_value = float(values[0])
                start_date = values[1]; end_date = values[2]

                date_range = (timeseries["date"] >= start_date) & (timeseries["date"] <= end_date)
                timeseries.loc[date_range, variable] *= perturbation_value
                
                print(f"    '{variable}' perturbed by {perturbation_value} from {start_date} to {end_date}.")
            else: 
                print(f"    Warning: '{variable}' not found in timeseries variables.")

    
    # 2. Save forcings 
    def save_forcings(gauge_id):
         timeseries[timeseries["gauge_id"] == gauge_id].to_csv(Path(data_dir / "data", f"{gauge_id}.csv"), index=False)
    list(map(save_forcings, gauge_ids))

    data_path = data_dir / "data"
    print(f"    Timeseries variables saved to: {repr(data_path)}")

    timeseries_path = generate_netcdf_files(data_dir)

    
    # 3. Save attributes
    def save_attributes(attribute):
        attributes[["gauge_id", attribute]].to_csv(Path(data_dir / "attributes", f"{attribute}.csv"), index=False)

    list(map(save_attributes, [i for i in attributes.columns if i != "gauge_id"]))
        
    attributes_path = data_dir / "attributes"
    print(f"    Static variables saved to: {repr(attributes_path)}")
    
    return data_dir