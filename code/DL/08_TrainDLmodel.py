# 08. Train LSTM on high-performance computer

from pathlib import Path

import torch

from neuralhydrology.nh_run import start_run

if torch.cuda.is_available():
    start_run(config_file=Path("config.yml"))
else:
    start_run(config_file=Path("config.yml"), gpu=-1)