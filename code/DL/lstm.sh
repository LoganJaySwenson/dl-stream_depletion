#!/bin/bash
#SBATCH --job-name=LSTM_Logan    
#SBATCH --partition=sixhour  
#SBATCH --ntasks=1                   # Run task
#SBATCH --gres=gpu --constraint=v100
#SBATCH --mem=30g

#SBATCH --output=OutputLSTM.log
#SBATCH --error=OutputLSTM.err
#SBATCH --mail-type END         
#SBATCH --mail-user loganswenson@ku.edu                           
#SBATCH --time=0-06:00:00    

module load conda
conda activate dl-hydrology
python 08_TrainDLmodel.py