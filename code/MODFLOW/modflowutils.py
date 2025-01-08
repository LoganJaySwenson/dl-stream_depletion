from pathlib import Path
from typing import List

import pandas as pd

def snap_points_to_sfr_network(points : pd.DataFrame,
                               sfr_network : pd.DataFrame,
                               id : str = "gauge_id",
                               search_distance : List[int]=[-1, 0, 1]) -> pd.DataFrame:
    """Get i and j coordinates of the intersected, or most upstream, sfr cell for points intersected using FloPy's model.modelgrid.intersect() method.

    Because of how the .intersect() method handles intersections of where a point is on the edge of two cells, it can be the case that the returned points are +/- one cell off from their locations in the model.
    In those cases, we perform a one cell search around those points and return the most upstream sfr cell.

    Parameters
    ----------
    points : pd.DataFrame
        Points to be "snapped" onto sfr network; must contain id, "i", and "j" columns.
    stream_network : pd.DataFrame
        FloPy's model.sfr.network. 
    id : str, optional
        id for point's i and j coordinates. By default "gauge_id". 
    search_distance : List[int], optional
        List containing the vector of distances to search neighboring points by. By default [-1, 0, 1]. 
        
    Returns
    -------
    pd.DataFrame
        Points "snapped" onto sfr network with updated "i" and "j" columns that corresponding to the intersected, or most upstream, sfr cell within search_distance. 
    """
    import itertools
    offsets = list(itertools.product(search_distance, search_distance))
    
    neighboring_cells = []
    for idx, point in points.iterrows():
        for di, dj in offsets:
            neighbor = point.copy()
            neighbor["i"] = point["i"] + di
            neighbor["j"] = point["j"] + dj
            neighboring_cells.append(neighbor)
        
    neighboring_cells = pd.DataFrame(neighboring_cells)

    neighboring_sfr_cells = pd.merge(neighboring_cells, sfr_network, on=["i", "j"], how="inner")

    res = []
    for idx, point in points.iterrows():
        sfr_coords = neighboring_sfr_cells[(neighboring_sfr_cells[id] == point[id]) & neighboring_sfr_cells["i"].isin([point["i"]]) & neighboring_sfr_cells["j"].isin([point["j"]])]
        if sfr_coords.empty:
            sfr_coords = neighboring_sfr_cells.loc[neighboring_sfr_cells["reachID"] == neighboring_sfr_cells[neighboring_sfr_cells[id] == point[id]]["reachID"].min()]  
        res.append(sfr_coords)

    res = pd.concat(res, ignore_index=True)

    return pd.merge(points.drop(columns=["i", "j"]), res[[id, "i", "j", "iseg", "ireach"]], on=[id], how="left")


def evaluate_streamflow_depletion(points : pd.DataFrame,
                                  historical_path : Path,
                                  baseline_path : Path,
                                  id : str = "gauge_id") -> pd.DataFrame:
    """Estimate streamflow depletion caused by groundwater pumping as the difference between a simulation with pumping and a baseline simulation where pumping has been set to 0. 

    Parameters
    ----------
    points : pd.DataFrame
        Points to estimate streamflow depletion on sfr network; must contain id, "i", and "j" columns.
    historical_path : Path
        Path to a historical simulation with pumping. 
    baseline_path : Path
        Path to a baseline simulation with pumping set to 0. 
    id : str, optional
        id for point's i and j coordinates. By default "gauge_id". 

    Returns
    -------
    pd.DataFrame
        Timeseries of baseflows and estimated streamflow depletion at points on sfr network. 
    """
    import warnings
    import flopy.utils.sfroutputfile as sf

    with warnings.catch_warnings():
        warnings.simplefilter(action="ignore", category=FutureWarning)
    
        historical_package = sf.SfrFile(historical_path  / "trans_2d.sfb")
        baseline_package = sf.SfrFile(baseline_path / "trans_2d.sfb")

        historical = historical_package.get_dataframe().loc[:,["kstpkper", "i", "j", "Qin", "Qaquifer", "Qout", "Qovr", "Qprecip", "Qet", "segment", "reach"]]
        baseline = baseline_package.get_dataframe().loc[:,["kstpkper", "i", "j", "Qin", "Qaquifer", "Qout", "Qovr", "Qprecip", "Qet", "segment", "reach"]]
    
    historical = historical[historical["i"].isin(points["i"]) & historical["j"].isin(points["j"])]
    baseline = baseline[baseline["i"].isin(points["i"]) & baseline["j"].isin(points["j"])]

    historical = pd.merge(points[[id, "i", "j"]], historical, on=["i", "j"], how="left")
    baseline = pd.merge(points[[id, "i", "j"]], baseline, on=["i", "j"], how="left")

    historical["ts"], historical["sp"] = zip(*historical["kstpkper"])
    baseline["ts"], baseline["sp"] = zip(*baseline["kstpkper"])
                      
    historical.rename({"Qout" : "Qriver"}, axis=1, inplace=True)
    historical.rename({col: col + "_historical" for col in historical.columns if col.startswith("Q")}, 
                      axis=1, inplace=True)

    baseline.rename({"Qout" : "Qriver"}, axis=1, inplace=True)
    baseline.rename({col: col + "_baseline" for col in baseline.columns if col.startswith("Q")}, 
                    axis=1, inplace=True)

    stream_depletion = pd.merge(historical, baseline.drop(["segment", "reach", "ts", "sp"], axis=1), on=[id, "i", "j", "kstpkper"], how="left")

    stream_depletion["stream_depletion"] = stream_depletion["Qriver_historical"] - stream_depletion["Qriver_baseline"]
    
    return stream_depletion[[id, "i", "j", "segment", "reach", "kstpkper", "ts", "sp", "Qriver_historical", "Qriver_baseline", "stream_depletion"]]

