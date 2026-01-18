"""
Text completion script for vLLM models.
Supports both local vLLM server and Modal deployment.
"""

import argparse
import json
from typing import List, Optional, Dict, Any
import requests


class VLLMTextCompletion:
    """Simple client for vLLM text completion."""
    
    def __init__(self, base_url: str = "http://localhost:8000", model_name: Optional[str] = None):
        """
        Initialize the vLLM client.
        
        Args:
            base_url: The base URL of the vLLM server
            model_name: The model name (will be auto-detected if not provided)
        """
        self.base_url = base_url.rstrip('/')
        self.model_name = model_name
        
        # Auto-detect model name if not provided
        if not self.model_name:
            try:
                response = requests.get(f"{self.base_url}/v1/models")
                if response.status_code == 200:
                    models = response.json().get('data', [])
                    if models:
                        self.model_name = models[0]['id']
                        print(f"Auto-detected model: {self.model_name}")
            except Exception as e:
                print(f"Warning: Could not auto-detect model name: {e}")
    
    def complete(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
        stop: Optional[List[str]] = None,
        stream: bool = False,
        **kwargs
    ) -> str:
        """
        Generate text completion for a given prompt.
        
        Args:
            prompt: The input prompt
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (0.0 to 2.0)
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
            stop: List of stop sequences
            stream: Whether to stream the response
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            Generated text completion
        """
        url = f"{self.base_url}/v1/completions"
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "stream": stream,
        }
        
        if stop:
            payload["stop"] = stop
        
        # Add any additional parameters
        payload.update(kwargs)
        
        try:
            if stream:
                return self._stream_complete(url, payload)
            else:
                response = requests.post(url, json=payload, timeout=120)
                response.raise_for_status()
                result = response.json()
                return result['choices'][0]['text']
        except requests.exceptions.RequestException as e:
            print(f"Error calling vLLM API: {e}")
            raise
    
    def _stream_complete(self, url: str, payload: Dict[str, Any]) -> str:
        """Handle streaming completion."""
        full_text = ""
        
        with requests.post(url, json=payload, stream=True, timeout=120) as response:
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]
                        if data == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data)
                            text = chunk['choices'][0]['text']
                            full_text += text
                            print(text, end='', flush=True)
                        except json.JSONDecodeError:
                            continue
            
            print()  # New line after streaming
        
        return full_text
    
    def batch_complete(
        self,
        prompts: List[str],
        max_tokens: int = 512,
        temperature: float = 0.7,
        **kwargs
    ) -> List[str]:
        """
        Generate completions for multiple prompts.
        
        Args:
            prompts: List of input prompts
            max_tokens: Maximum tokens per completion
            temperature: Sampling temperature
            **kwargs: Additional parameters
            
        Returns:
            List of generated completions
        """
        results = []
        for i, prompt in enumerate(prompts):
            print(f"Processing prompt {i+1}/{len(prompts)}...")
            completion = self.complete(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            results.append(completion)
        return results


def main():
    parser = argparse.ArgumentParser(description="Text completion using vLLM")
    parser.add_argument(
        "--prompt",
        type=str,
        help="Input prompt for completion"
    )
    parser.add_argument(
        "--prompt-file",
        type=str,
        help="File containing prompts (one per line)"
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default="http://localhost:8000",
        help="Base URL of vLLM server"
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Model name (auto-detected if not provided)"
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        help="Maximum tokens to generate"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Sampling temperature"
    )
    parser.add_argument(
        "--top-p",
        type=float,
        default=0.9,
        help="Nucleus sampling parameter"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=50,
        help="Top-k sampling parameter"
    )
    parser.add_argument(
        "--stop",
        type=str,
        nargs="+",
        help="Stop sequences"
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Stream the output"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file to save results"
    )
    
    args = parser.parse_args()
    
    # Initialize client
    client = VLLMTextCompletion(base_url=args.base_url, model_name=args.model)
    
    # Prepare prompts
    prompts = []
    if args.prompt:
        prompts = [args.prompt]
    elif args.prompt_file:
        with open(args.prompt_file, 'r') as f:
            prompts = [line.strip() for line in f if line.strip()]
    else:
        # Interactive mode
        print("Enter your prompt (Ctrl+D or Ctrl+Z to finish):")
        import sys
        prompts = [sys.stdin.read().strip()]
    
    # Generate completions
    results = []
    for i, prompt in enumerate(prompts):
        if len(prompts) > 1:
            print(f"\n{'='*60}")
            print(f"Prompt {i+1}/{len(prompts)}:")
            print(f"{'='*60}")
        
        print(f"Input: {prompt}\n")
        print("Completion:")
        
        completion = client.complete(
            prompt=prompt,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            top_p=args.top_p,
            top_k=args.top_k,
            stop=args.stop,
            stream=args.stream
        )
        
        if not args.stream:
            print(completion)
        
        results.append({
            "prompt": prompt,
            "completion": completion
        })
    
    # Save results if output file specified
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
