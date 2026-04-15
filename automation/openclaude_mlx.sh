#!/bin/bash

# OpenClaude - MLX Bağlantısı

export OPENAI_API_KEY="not-needed"
export OPENAI_API_BASE="http://localhost:8080/v1"

openclaude --provider openai --model default_model "$@"