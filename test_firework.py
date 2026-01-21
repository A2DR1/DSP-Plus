# import requests
# import json

# url = "https://api.fireworks.ai/inference/v1/chat/completions"
# payload = {
#   "model": "austinszj-sw7x9tsqzf/fireworks/models/deepseek-r1-0528",
#   "max_tokens": 4096,
#   "top_p": 1,
#   "top_k": 40,
#   "presence_penalty": 0,
#   "frequency_penalty": 0,
#   "temperature": 0.6,
#   "messages": []
# }
# headers = {
#   "Accept": "application/json",
#   "Content-Type": "application/json",
#   "Authorization": "Bearer fw_98ExHCfZyiyLjLy3PoxJtg"
# }
# response = requests.request("POST", url, headers=headers, data=json.dumps(payload))
# print(response.text)

from openai import OpenAI

# For Together AI
# client = OpenAI(
#     api_key="Bearer fw_98ExHCfZyiyLjLy3PoxJtg",
#     base_url="https://api.together.xyz/v1",
# )

# For Fireworks AI
client = OpenAI(
    api_key="fw_98ExHCfZyiyLjLy3PoxJtg",
    base_url="https://api.fireworks.ai/inference/v1",
)

response = client.chat.completions.create(
    model="fireworks/deepseek-v3p2", # Or the provider's specific model string
    messages=[{"role": "user", "content": "How do I formalize a math theorem in Lean 4?"}],
)

print(response.choices[0].message.content)