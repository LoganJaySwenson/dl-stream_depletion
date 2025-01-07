from pathlib import Path

import pandas as pd

def estimate_streamflow_depletion(gauges : pd.DataFrame,
                                  historical_path : Path,
                                  baseline_path : Path) -> pd.DataFrame:
    """
    Estimate streamflow depletion caused by groundwater pumping as the difference between a simulation with pumping and a baseline simulation where pumping is set to zero. 
    """
    import warnings
    import flopy.utils.sfroutputfile as sf

    with warnings.catch_warnings():
        warnings.simplefilter(action="ignore", category=FutureWarning)
    
        historical_package = sf.SfrFile(historical_path  / "trans_2d.sfb")
        baseline_package = sf.SfrFile(baseline_path / "trans_2d.sfb")

        historical = historical_package.get_dataframe().loc[:,["kstpkper", "i", "j", "Qin", "Qaquifer", "Qout", "Qovr", "Qprecip", "Qet", "segment", "reach"]]
        baseline = baseline_package.get_dataframe().loc[:,["kstpkper", "i", "j", "Qin", "Qaquifer", "Qout", "Qovr", "Qprecip", "Qet", "segment", "reach"]]
    
    historical = historical[historical["i"].isin(gauges["i"]) & historical["j"].isin(gauges["j"])]
    baseline = baseline[baseline["i"].isin(gauges["i"]) & baseline["j"].isin(gauges["j"])]

    historical = pd.merge(gauges[["gauge_id", "i", "j"]], historical, on=["i", "j"], how="left")
    baseline = pd.merge(gauges[["gauge_id", "i", "j"]], baseline, on=["i", "j"], how="left")

    historical["ts"], historical["sp"] = zip(*historical["kstpkper"])
    baseline["ts"], baseline["sp"] = zip(*baseline["kstpkper"])
                      
    historical.rename({"Qout" : "Qriver"}, axis=1, inplace=True)
    historical.rename({col: col + "_historical" for col in historical.columns if col.startswith("Q")}, 
                      axis=1, inplace=True)

    baseline.rename({"Qout" : "Qriver"}, axis=1, inplace=True)
    baseline.rename({col: col + "_baseline" for col in baseline.columns if col.startswith("Q")}, 
                    axis=1, inplace=True)

    stream_depletion = pd.merge(historical, baseline.drop(["segment", "reach", "ts", "sp"], axis=1), on=["gauge_id", "i", "j", "kstpkper"], how="left")

    stream_depletion["stream_depletion"] = stream_depletion["Qriver_historical"] - stream_depletion["Qriver_baseline"]

    return stream_depletion[["gauge_id", "i", "j", "segment", "reach", "kstpkper", "ts", "sp", "Qriver_historical", "Qriver_baseline", "stream_depletion"]]










