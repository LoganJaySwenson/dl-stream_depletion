# 03. Wel package
from pathlib import Path

import pandas as pd

import geopandas as gpd
from shapely.geometry import Point

import flopy

model_dir = Path("models", "MODFLOW")
model_path = model_dir / "GMD2_transient"
modflow_path = model_path / "mf2005.exe"

model = flopy.modflow.Modflow.load("trans_2d.nam",
                                   model_ws = model_path, 
                                   exe_name = modflow_path,
                                   version = "mf2005")

# Get wel flux timeseries (Qw [ft3/d]) for wells in each watershed.
# Translate real-world coordinates to northing/easting.
gauges = pd.read_csv(Path("data", "gauges_i+jcoordinates.csv"), dtype={"gauge_id":str}); model_domain = gpd.read_file(Path("data", "spatial", "MODFLOW", "domain.shp")); watersheds = gpd.read_file(Path("data", "spatial", "general", "watersheds.shp"))

domain_crs = model_domain.crs; domain_coords = model_domain.total_bounds

model_domain["geometry"] = model_domain["geometry"].translate(xoff = -domain_coords[0], 
                                                              yoff = -domain_coords[1])

watersheds["geometry"] = watersheds["geometry"].to_crs(domain_crs).translate(xoff = -domain_coords[0], 
                                                                             yoff = -domain_coords[1])

gauges = gpd.GeoDataFrame(
    gauges,
    geometry = [Point(xy) for xy in zip(gauges["x"], gauges["y"])],
    crs = "EPSG:4326"
)

gauges.drop(["x","y"], axis=1, inplace=True)

gauge_ids = gauges["gauge_id"]

gauges["geometry"] = gauges["geometry"].to_crs(domain_crs).translate(xoff = -domain_coords[0], 
                                                                     yoff = -domain_coords[1])
# Get wel fluxes (Qw [ft3/d]) for each stress period.
nper = model.dis.nper
kstpkper = [(0, 0)] + [(9, ts) for ts in range(1, nper)] # reproduce FloPy's .get_kstpkper() method; returns a List[(timesteps, stress periods)]

wel_package = model.wel.stress_period_data

wels_all = []

for i in kstpkper:
    ts, sp = i
    wel_sp = pd.DataFrame(wel_package[sp])
    wel_sp["kstpkper"] = [i] * len(wel_sp) ; wel_sp["sp"] = sp ; wel_sp["ts"] = ts
    wel_sp.rename(columns={"flux" : "Qwel"}, inplace = True)
    wels_all.append(wel_sp[["i", "j", "kstpkper", "ts", "sp", "Qwel"]])
    
wels_all = pd.concat(wels_all, ignore_index=True)

wels_all

# Translate wel i and j coordinates to set the origin in the lower-left corner.
save_path = model_dir / "outputs"

nrows = model.nrow
ncols = model.ncol

wels_all["x"] = (wels_all["j"] + 0.5) 
wels_all["y"] = (nrows - wels_all["i"] + 0.5) 

wels_all.to_csv(save_path / "MODFLOW_Qwel_all.csv", index=False)


# Get wels in each watershed
wels_all = gpd.GeoDataFrame(
    wels_all,
    geometry = [Point(xy) for xy in zip(wels_all["x"]*400, wels_all["y"]*400)], 
    crs = domain_crs
)

num_wels = {}
watershed_wels = []

for gauge_id in gauge_ids:

    watershed = watersheds[watersheds["gauge_id"] == gauge_id]
    
    wels = gpd.sjoin(wels_all, watershed, how="inner", predicate="within").drop(columns=["index_right"])
    wels["gauge_id"] = gauge_id

    num_wels[gauge_id] = wels.groupby(["i", "j"]).ngroup().nunique()
    
    watershed_wels.append(wels)

watershed_wels = pd.concat(watershed_wels, ignore_index=True)

watershed_wels = watershed_wels[["gauge_id", "i", "j", "kstpkper", "ts", "sp", "Qwel", "x", "y", "geometry"]]

num_total_wels = wels_all.groupby(["i", "j"]).ngroup().nunique()
num_total_wels_across_watersheds = watershed_wels.groupby(["i", "j"]).ngroup().nunique()
percentage = num_total_wels_across_watersheds / num_total_wels

print("Total number of pumping wells in GMD2 model:", num_total_wels)
print(f"Total number of wells across watersheds:, {num_total_wels_across_watersheds} or {percentage:.2f}%")
print("Number of pumping wells per watershed:")
num_wels

watershed_wels.drop("geometry", axis=1, inplace=True)

watershed_wels.to_csv(save_path / "MODFLOW_Qwel_watersheds.csv", index=False)

watershed_wels




# import numpy as np
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
# ax.scatter(wels_all["j"]+0.5, wels_all["i"]+0.5, marker='o', color="red", edgecolor="#000000", zorder=3)
# ax.scatter(gauges["j"]+0.5, gauges["i"]+0.5, marker='o', color="#F58231", edgecolor="#000000", zorder=4)
# ax.set_xlabel("Column")
# ax.set_ylabel("Row")
# ax.set_aspect("equal")
# plt.show()

# fig, ax = plt.subplots(figsize=(190*mm, 190*mm))
# ax.imshow(np.flip(ibound, axis=0), cmap=cmap, vmin=-1, vmax=1, alpha=0.6, origin="lower", zorder=1)
# ax.scatter(sfr_network["j"], (nrows - sfr_network["i"]), marker="s", color="#377eb8", zorder=2)
# ax.scatter(wels_all["j"]+0.5, (nrows - wels_all["i"]+0.5), marker='o', color="red", edgecolor="#000000", zorder=3)
# ax.scatter(gauges["j"]+0.5, (nrows - gauges["i"]+0.5), marker='o', color="#f58231", edgecolor="#000000", zorder=4)
# ax.set_xlabel("Column")
# ax.set_ylabel("Row")
# ax.set_aspect("equal")
# ax.set_xlim(0,ncols)
# ax.set_ylim(0,nrows)
# plt.show()

