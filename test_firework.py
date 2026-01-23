import os
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

# 1. Load environment variables from .env file
load_dotenv()

# 2. Initialize the client
# The client automatically looks for "OPENAI_API_KEY" in your environment,
# but passing it explicitly is also common.
client = OpenAI(
    api_key=os.environ.get("FIREWORKS_API_KEY"),
    base_url="https://api.fireworks.ai/inference/v1"
)

def get_chat_response(prompt, model="fireworks/deepseek-v3p2", system_role="You are a helpful assistant."):
    """
    Sends a prompt to the OpenAI API and returns the text response.
    """
    try:
        # 3. Create the API request
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7, # Controls randomness (0 = strict, 1 = creative)
            max_tokens=150   # Limits the length of the response
        )

        # 4. Extract and return the content
        return response.choices[0].message.content

    except OpenAIError as e:
        # Handle API-specific errors (rate limits, auth issues, etc.)
        return f"OpenAI API Error: {e}"
    except Exception as e:
        # Handle general Python errors
        return f"An unexpected error occurred: {e}"

# 5. Main execution block
if __name__ == "__main__":
    user_input = "Explain the importance of clean code in one sentence."
    
    print(f"User: {user_input}")
    print("Thinking...")
    
    result = get_chat_response(user_input)
    
    print("-" * 30)
    print(f"AI: {result}")
    print("-" * 30)