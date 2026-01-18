from vllm_text_completion import VLLMTextCompletion

client = VLLMTextCompletion(base_url="https://austinszj--vllm-bfs-prover-inference-serve.modal.run")
result = client.complete("h : x = y + 2 ⊢ x - 1 = y + 1:::", max_tokens=100)
print(result)