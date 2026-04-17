#!/bin/bash
# MLX Control Center Auto-start Script
cd "/Users/erdinc/Desktop/Mlx/mlx-control-center"
./.venv_modern/bin/python run.py > uvicorn.log 2> server_debug.txt &
