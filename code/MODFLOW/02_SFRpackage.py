# 02. SFR package 
from pathlib import Path

import pandas as pd

import geopandas as gpd
from shapely.geometry import Point, LineString

import flopy

from modflowutils import snap_points_to_sfr_network, evaluate_streamflow_depletion

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

# Snap benchmarking locations onto the model.modelgrid and then to SFR network
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

gauges = snap_points_to_sfr_network(gauges,
                                    pd.DataFrame(model.sfr.reach_data),
                                    id = "gauge_id",
                                    search_distance = [-1, 0, 1]
                                   )

gauges["x"] = gauges["geometry"].x
gauges["y"] = gauges["geometry"].y
gauges.drop("geometry", axis=1, inplace=True)

gauges.to_csv(Path("data", "gauges_i+jcoordinates.csv"), index=False) # reminder to self: coordinates (i and j) are expressed in terms of MODFLOW's internal naming convention for rows/cols, but geometry is set with the orign in the lower-left corner


# 2. Extract timeseries of fluxes Qriver [ft3/d] and estimate streamflow depletion [ft3/d]  from a baseline simulation where pumping has been set to 0.
gauges = pd.read_csv(Path("data", "gauges_i+jcoordinates.csv"), dtype={"gauge_id":str})

stream_depletion = evaluate_streamflow_depletion(gauges, 
                                                 historical_path = model_dir / "GMD2_transient", 
                                                 baseline_path = model_dir / "GMD2_transient_baseline",
                                                 id = "gauge_id"
                                                )

save_path = model_dir / "outputs"
if save_path.exists():
    pass
else:
    save_path.mkdir(parents=True)
    
stream_depletion.to_csv(save_path / "MODFLOW_stream_depletion.csv", index=False)



# import  numpy as np
# import matplotlib.pyplot as plt
# from matplotlib.colors import ListedColormap

# mm = 1/25.4  # mm
 
# colors = ["#666666", "none", "#666666"] 
# cmap = ListedColormap(colors)

# nrows = model.nrow
# ncols = model.ncol

# bas = model.get_package("BAS6")
# ibound = bas.ibound.array.squeeze()
# sfr_network = pd.DataFrame(model.sfr.reach_data)

# fig, ax = plt.subplots(figsize=(190*mm, 190*mm))
# ax.imshow(ibound, cmap=cmap, vmin=-1, vmax=1, alpha=0.6, zorder=1)
# ax.scatter(sfr_network["j"], sfr_network["i"], marker="s", color="#377EB8", zorder=2)
# ax.scatter(gauges["j"]+0.5, gauges["i"]+0.5, marker='o', color="#F58231", edgecolor="#000000", zorder=3)
# ax.set_xlabel("Column")
# ax.set_ylabel("Row")
# ax.set_aspect("equal")
# plt.show()


# fig, ax = plt.subplots(figsize=(190*mm, 190*mm))
# ax.imshow(np.flip(ibound, axis=0), cmap=cmap, vmin=-1, vmax=1, alpha=0.6, origin="lower")
# ax.scatter(sfr_network["j"], (nrows - sfr_network["i"]), marker="s", color="#377eb8", zorder=1)
# ax.scatter(gauges["j"]+0.5, (nrows - gauges["i"]+0.5), marker='o', color="#f58231", edgecolor="#000000")
# ax.set_xlabel("Column")
# ax.set_ylabel("Row")
# ax.set_aspect("equal")
# ax.set_xlim(0,ncols)
# ax.set_ylim(0,nrows)
# plt.show()

