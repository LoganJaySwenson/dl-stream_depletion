# 02. SFR package 
from pathlib import Path

import numpy as np
import pandas as pd

import geopandas as gpd
from shapely.geometry import Point, LineString

import flopy

from modelutils import estimate_streamflow_depletion

model_dir = Path("models", "MODFLOW")
model_path = model_dir / "GMD2_transient"
modflow_path = model_path / "mf2005.exe"

model = flopy.modflow.Modflow.load("trans_2d.nam",
                                   model_ws = model_path, 
                                   exe_name = modflow_path,
                                   version = "mf2005")


# 1. Snap stream gauges (benchmarking locations) with real-world coordinates onto SFR network in the GMD2 model.
# Translate real-world coordinates to northing/easting.
nrows = model.nrow
ncols = model.ncol

gauges = pd.read_csv(Path("data", "gauges.csv"), dtype={"gauge_id":str}); model_domain = gpd.read_file(Path("data", "spatial", "MODFLOW", "domain.shp")); watersheds = gpd.read_file(Path("data", "spatial", "general", "watersheds.shp"))

domain_crs = model_domain.crs; domain_coords = model_domain.total_bounds

model_domain["geometry"] = model_domain["geometry"].translate(xoff = -domain_coords[0], 
                                                              yoff = -domain_coords[1])

watersheds["geometry"] = watersheds["geometry"].to_crs(domain_crs).translate(xoff = -domain_coords[0], 
                                                                             yoff = -domain_coords[1])

gauges = gpd.GeoDataFrame(
    gauges,
    geometry = [Point(xy) for xy in zip(gauges["lon"], gauges["lat"])],
    crs = "EPSG:4326"
)

gauges.drop(["lon","lat"], axis=1, inplace=True)

gauge_ids = gauges["gauge_id"]

gauges["geometry"] = gauges["geometry"].to_crs(domain_crs).translate(xoff = -domain_coords[0], 
                                                                     yoff = -domain_coords[1])

# Snap benchmarking locations onto the model.modelgrid and plot in MODFLOW coordinates
# FloPy’s BaseModel.modelgrid returns ibound with the origin set in the lower-left corner, but the `.intersect()` method returns i and j coordinates with the origin in the upper-left corner, consistent with MODFLOW’s internal naming convention. 
# Also, because of how the method handles intersections of where a point is on the edge of two grid cells, it can be the case that the returned points are +/- one grid cell off from their locations in the model

coordinates = []

for idx, gauge_id in gauges.iterrows():
    x = gauge_id["geometry"].x 
    y = gauge_id["geometry"].y
    i, j = model.modelgrid.intersect(x=x, y=y)
    
    coordinates.append((i, j))
    gauges.at[idx, "i"] = i
    gauges.at[idx, "j"] = j

gauges["i"] = gauges["i"].astype(int) 
gauges["j"] = gauges["j"].astype(int)

# Perform +/- one grid cell search to ensure snapped points are SFR cells
# In cases where points are offset by +/- one grid cell, we perform a one grid cell search around those points and return the most upstream sfr cell.

import itertools

sfr_network = pd.DataFrame(model.sfr.reach_data)

search_range = [-1, 0, 1]
offsets = list(itertools.product(search_range, search_range))

neighboring_cells = []
for idx, gauge_id in gauges.iterrows():
    for di, dj in offsets:
        neighbor = gauge_id.copy()
        neighbor["i"] = gauge_id["i"] + di
        neighbor["j"] = gauge_id["j"] + dj
        neighboring_cells.append(neighbor)
        
neighboring_cells = pd.DataFrame(neighboring_cells)

neighboring_sfr_cells = pd.merge(neighboring_cells, sfr_network, on=["i", "j"], how="inner")

res = []
for gauge_id in gauge_ids:
    sfr_coords = neighboring_sfr_cells[(neighboring_sfr_cells["gauge_id"] == gauge_id) & neighboring_sfr_cells["i"].isin(gauges["i"].values) & neighboring_sfr_cells["j"].isin(gauges["j"].values)]
    if sfr_coords.empty:
        sfr_coords = neighboring_sfr_cells.loc[neighboring_sfr_cells["reachID"] == neighboring_sfr_cells[neighboring_sfr_cells["gauge_id"] == gauge_id]["reachID"].min()]  
    res.append(sfr_coords)

res = pd.concat(res, ignore_index=True)

# Reminder to self: These coordinates (i and j) are expressed in terms of MODFLOW's internal naming convention for rows/cols, but geometry is set with the orign in the lower-left corner
gauges = pd.merge(gauges.drop(columns=["i","j"]), res[["gauge_id", "i", "j", "iseg", "ireach"]], on=["gauge_id"], how="left")

gauges["x"] = gauges["geometry"].x
gauges["y"] = gauges["geometry"].y
gauges.drop("geometry", axis=1, inplace=True)

gauges.to_csv(Path("data", "gauges_i+jcoordinates.csv"), index=False)




# 2. Extract timeseries of fluxes Qriver [ft3/d] and estimated streamflow depletion [ft3/d]  from a baseline simulation.
stream_depletion = estimate_streamflow_depletion(gauges, 
                                                 historical_path = model_dir / "GMD2_transient", 
                                                 baseline_path = model_dir / "GMD2_transient_baseline"
                                                )

save_path = model_dir / "outputs"
if save_path.exists():
    pass
else:
    save_path.mkdir(parents=True)
    
stream_depletion.to_csv(save_path / "MODFLOW_stream_depletion.csv", index=False)

