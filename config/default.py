#  Copyright (c) Microsoft Corporation.
#  Licensed under the MIT License.
import os
from dotenv import load_dotenv

load_dotenv()

print("Loaded environment variables from .env file.")
print(f"OPENAI_API_KEY: {os.environ.get('OPENAI_API_KEY')}")
print(f"FIREWORKS_API_KEY: {os.environ.get('FIREWORKS_API_KEY')}")

"""
Record all your configurations here
"""

# Input data file path
data = "datasets/minif2f.jsonl"

# Data split names to process
split = ["test"]

# Directory to store outputs
target_dir = "result/dsp_minif2f"

# --- CONCURRENCY & LIMITS ---
# Lowered for OpenAI Tier 1 Rate Limits (RPM/TPM)
concurrent_num = 8

# Attempts: How many times to try the workflow for each problem
attempts = 5

# Resource management for local tracking
draft_max_running_requests = 10
sketch_max_running_requests = 10

# Number of Lean servers for verification (Local CPU usage)
sketch_leanserver_num = 2
prove_leanserver_num = 2

# --- DRAFT PHASE (Thinking/Natural Language Proof) ---
draft_model_config = [
    {
        "base_url": "https://api.fireworks.ai/inference/v1",
        "api_key": os.environ.get("FIREWORKS_API_KEY"),
    },
]

draft_sample_config = {
    "model": "fireworks/deepseek-r1-0528",
    "temperature": 0.6,
    "top_p": 0.95,
    "timeout": 3600,
    "max_tokens": 4096,
}

# --- SKETCH PHASE (Autoformalization into Lean 4) ---
sketch_model_config = [
    {
        "base_url": "https://api.fireworks.ai/inference/v1",
        "api_key": os.environ.get("FIREWORKS_API_KEY"),     
    },
]

sketch_sample_config = {
    "model": "fireworks/deepseek-v3p2",
    "temperature": 0.7,
    "top_p": 0.95,
    "timeout": 600,
    "max_tokens": 4096,
}

sketch_verify_config = {
    "verify_timeout": 180,
}

# --- PROVING PHASE (Symbolic Step-by-Step Tactic Generation) ---
prove_model_config = [
    {
        "base_url": "https://austinszj--vllm-bfs-prover-inference-serve.modal.run/v1",
        "api_key": "EMPTY",
    },
]

prove_sampling_config = {
    "name_lean_copilot": "BFS-Prover-API",
    # "model": "gpt-4o-mini", # Faster and cheaper for high-frequency search
    "model": "ByteDance-Seed/BFS-Prover-V1-7B",
    "temperature": 1.1,
    "top_p": 1,
    "timeout": 1800,
    "max_tokens": 128,
    "n":1,
    "max_output": 4,
    "use_beam_search": False,
}

# Symbolic search parameters
prove_verify_config = {
    "verify_timeout": 1200,
    "max_tree_size": 256,
    "search_attempts": 4,
    "port_lean_copilot": 23338,
}
