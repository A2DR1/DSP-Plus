from openai import OpenAI

# For Fireworks AI
client = OpenAI(
    api_key="fw_98ExHCfZyiyLjLy3PoxJtg",
    base_url="https://api.fireworks.ai/inference/v1",
)

response = client.chat.completions.create(
    # model="fireworks/deepseek-v3p2", # Or the provider's specific model string
    model="fireworks/deepseek-r1-0528",
    messages=[{"role": "user", "content": "How do I formalize a math theorem in Lean 4?"}],
)

print(response.choices[0].message.content)