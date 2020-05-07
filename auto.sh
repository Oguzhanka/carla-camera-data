#! /bin/bash

source ~/anaconda3/etc/profile.d/conda.sh
conda activate carla

for i in {51..150}
    do
        python main.py $i
    done &
