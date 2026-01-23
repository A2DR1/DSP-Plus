import numpy as np
from typing import List, Tuple, Any
from abc import ABC, abstractmethod

def pre_process_input(model_name, input):
    # Add support for OpenAI models
    if model_name in ["gpt-4o-mini", "gpt-4o"]:
        return input
    elif model_name in ["bytedance-research/BFS-Prover", "ByteDance-Seed/BFS-Prover-V1-7B"]:
        return input + ":::"
    else:
        raise NotImplementedError(f"External model '{model_name}' not supported")

def post_process_output(model_name, output):
    # Add support for OpenAI models
    if model_name in ["gpt-4o-mini", "gpt-4o"]:
        return output
    elif model_name in ["bytedance-research/BFS-Prover", "ByteDance-Seed/BFS-Prover-V1-7B"]:
        return output.split(":::")[-1]
    else:
        raise NotImplementedError(f"External model '{model_name}' not supported")

# --- Rest of the file (choices_dedup, sample_outputs_by_logprob, etc.) remains the same ---
def choices_dedup(output_list: List[tuple[str, float]]) -> List[tuple[str, float]]:
    unique_data = {}
    for item in output_list:
        if item[0] not in unique_data or item[1] > unique_data[item[0]]:
            unique_data[item[0]] = item[1]
    sorted_data = sorted(unique_data.items(), key=lambda x: x[1], reverse=True)
    return sorted_data

def sample_outputs_by_logprob(
    result: List[Tuple[Any, float]],
    max_output: int,
) -> List[Tuple[Any, float]]:
    if not result:
        return []
    logprobs = np.array([x[1] for x in result])
    probs = np.exp(logprobs - np.max(logprobs)) 
    probs /= probs.sum()
    size = min(max_output, len(result))
    selected_indices = np.random.choice(len(result), size=size, p=probs, replace=False)
    selected_outputs = [result[i] for i in selected_indices]
    return selected_outputs

class Generator(ABC):
    @abstractmethod
    def generate(self, input: str, target_prefix: str = "") -> List[Tuple[str, float]]:
        pass

class Encoder(ABC):
    @abstractmethod
    def encode(self, input: str) -> np.ndarray:
        pass