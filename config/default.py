#  Copyright (c) Microsoft Corporation.
#  Licensed under the MIT License.

"""
Record all your configurations here
"""

import os

# Input data file path
data = "datasets/minif2f.jsonl"

# Data split names to process
split = ["test"]

# Directory to store outputs
target_dir = "result/dsp_minif2f"

# Number of concurrent processes allowed
concurrent_num = 8

# Attempts means the number of DSP workflow attempts for each problem
attempts = 32

# The maximum number of requests for each model server (will be counted and controlled locally)
draft_max_running_requests = 128

# The maximum number of requests for each model server (will be counted and controlled locally)
sketch_max_running_requests = 128

# Number of Lean servers used for sketch verification
sketch_leanserver_num = 8

# Number of Lean servers used for proof verification
prove_leanserver_num = 64

# Configuration for the draft model servers. Needs to be replaced before launching.
draft_model_config = [
    {
        # "base_url": "https://austinszj-3211-resource.openai.azure.com/openai/v1",
        "base_url": "https://api.fireworks.ai/inference/v1",
        "api_key": os.environ.get("FIREWORK_API_KEY"),
    }
]

# Sampling configuration for draft model
draft_sample_config = {
    "model": "fireworks/deepseek-r1-basic",
    "temperature": 0.6,
    "top_p": 0.95,
    "timeout": 3600,
    "max_tokens": 32768,
}

# Configuration for the sketch model servers. Needs to be replaced before launching.
sketch_model_config = [
    {
        # "base_url": "https://austinszj-3211-resource.openai.azure.com/openai/v1",
        "base_url": "https://api.fireworks.ai/inference/v1",
        "api_key": os.environ.get("FIREWORK_API_KEY"),
    },
]

# Sampling configuration for the sketch model
sketch_sample_config = {
    "model": "fireworks/deepseek-v3p2",
    "temperature": 0.7,
    "top_p": 0.95,
    "timeout": 600,
    "max_tokens": 32768,
}

# Verify configuration used in sketch phase
sketch_verify_config = {
    "verify_timeout": 180,
}

# Configuration for the proving model servers. Needs to be replaced before launching.
prove_model_config = [
    {
        "base_url": "https://austinszj--vllm-bfs-prover-inference-serve.modal.run",
        "api_key": "EMPTY",
    },
]

# Sampling configuration for the proving model
prove_sampling_config = {
    "name_lean_copilot": "BFS-Prover-API",
    "model": "ByteDance-Seed/BFS-Prover-V1-7B",
    "temperature": 1.1,
    "top_p": 1,
    "timeout": 1800,
    "max_tokens": 64,
    "n": 8,
    "max_output": 4,
    "use_beam_search": False,
}

# Verify configuration used in proving phase
prove_verify_config = {
    "verify_timeout": 1200,
    "max_tree_size": 64,
    "search_attempts": 4,
    "port_lean_copilot": 23338,
}