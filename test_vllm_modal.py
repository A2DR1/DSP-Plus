# from vllm_text_completion import VLLMTextCompletion

# client = VLLMTextCompletion(base_url="https://austinszj--vllm-bfs-prover-inference-serve.modal.run")
# result = client.complete("h : x = y + 2 ⊢ x - 1 = y + 1:::", max_tokens=100)
# print(result)

from openai import OpenAI

# The URL from your Modal deployment
client = OpenAI(
    base_url="https://austinszj--vllm-bfs-prover-inference-serve.modal.run/v1",
    api_key="EMPTY"  # vLLM doesn't require a key by default
)

response = client.chat.completions.create(
    model="ByteDance-Seed/BFS-Prover-V1-7B",
    messages=[{"role": "user", "content": "h : x = y + 2 ⊢ x - 1 = y + 1:::"}],
    max_tokens=64
)

print(response.choices[0].message.content)