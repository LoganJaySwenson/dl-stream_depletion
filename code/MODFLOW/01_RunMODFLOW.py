# 01. Run GMD2 MODFLOW model for historical period and baseline scenario (i.e., with pumping turned off)

from pathlib import Path

import numpy as np
import flopy

model_dir = Path("models", "MODFLOW")

model_path = model_dir / "GMD2_transient"
modflow_path = model_path / "mf2005.exe"

model = flopy.modflow.Modflow.load("trans_2d.nam",
                                   model_ws = model_path, 
                                   exe_name = modflow_path,
                                   version = "mf2005")

print(f"GMD2 transient model for the Equus Beds Aquifer. \n\
https://www.kgs.ku.edu/Publications/OFR/2020/OFR2020-1.pdf \n\
{model}")

print(f"Packages included: {model.get_package_list()} \n\
DIS: Discretization Package \n\
BAS: Basic Package \n\
OC:  Output Control Option \n\
CHD: Time-Variant Specified-Head \n\
WEL: Well Package \n\
SFR: Streamflow-Routing Package \n\
RCH: Recharge Package \n\
DRN: Drain Pacckage \n\
EVT: Evapotranspiration Package \n\
GMG: Geometric MultiGrid Solver Package \n\
LPF: Layer-Property Package \n\
https://www.usgs.gov/software/modflow-2005-usgs-three-dimensional-finite-difference-ground-water-model")


# 1. Run historical simulation
success, mfoutput = model.run_model(silent = False) 
if not success:
    raise Exception("MODFLOW did not terminate successfully.")




# 2. Run baseline simulation (i.e., pumping set to 0)
model.change_model_ws(new_pth = model_dir / "GMD2_transient_baseline")
print("Updated model ws:", model.model_ws)

# Set Qw [ft³/d] to 0 for all stress periods
nper = model.dis.nper
for sp in range(0, nper):
    model.wel.stress_period_data[sp]["flux"][:] = 0.0

# Verify Qw [ft³/d] was set to 0 for all stress periods
wel_fluxes = []
for sp in range(0, nper):
    wel_sp = model.wel.stress_period_data[sp]["flux"]
    wel_fluxes.append(wel_sp)
wel_fluxes = np.concatenate(wel_fluxes)
np.all(wel_fluxes == 0)

model.write_input() 

success, mfoutput = model.run_model(silent = False) 
if not success:
    raise Exception("MODFLOW did not terminate successfully.")