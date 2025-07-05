import ollama

class OllamaTool:
    def __init__(self, host: str = None):
        """
        Initializes the OllamaTool.

        Args:
            host (str, optional): The hostname and port of the Ollama server.
                                  Defaults to None, which means the OLLAMA_HOST
                                  environment variable or the default host will be used.
        """
        self.client = ollama.Client(host=host)

    def list_models(self):
        """
        Lists the models available locally in Ollama.

        Returns:
            list: A list of model details.
        """
        try:
            return self.client.list()['models']
        except Exception as e:
            print(f"Error listing Ollama models: {e}")
            print("Please ensure Ollama is running and accessible.")
            return []

    def generate_text(self, model_name: str, prompt: str, system_prompt: str = None,
                      stream: bool = False, **kwargs):
        """
        Generates text using a specified Ollama model.

        Args:
            model_name (str): The name of the model to use (e.g., 'llama2').
            prompt (str): The user prompt.
            system_prompt (str, optional): An optional system prompt to guide the model's behavior.
            stream (bool, optional): Whether to stream the response. Defaults to False.
            **kwargs: Additional parameters to pass to the Ollama API (e.g., options, format).

        Returns:
            dict or iterator: If stream is False, returns the full response dictionary.
                              If stream is True, returns an iterator for streaming chunks.

        Example of a full response (stream=False):
        {
            'model': 'llama2:latest',
            'created_at': '2023-12-12T14:12:00.123Z',
            'response': 'The generated text...',
            'done': True,
            'context': [1, 2, ...],
            'total_duration': 5000000000,
            ...
        }
        """
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})

        try:
            print(f"Generating text with model: {model_name}, prompt: '{prompt[:50]}...'")
            response = self.client.chat(
                model=model_name,
                messages=messages,
                stream=stream,
                **kwargs
            )
            if not stream:
                print("Text generation complete.")
            return response
        except Exception as e:
            print(f"Error generating text with Ollama: {e}")
            print(f"Ensure the model '{model_name}' is available in your Ollama instance.")
            print("You can pull models using 'ollama pull <model_name>'.")
            return None

if __name__ == '__main__':
    # This is an example of how to use the tool.
    # It requires an Ollama instance to be running and the specified model to be pulled.

    print("Attempting to initialize OllamaTool...")
    ollama_tool = OllamaTool()

    print("\nAvailable Ollama models:")
    models = ollama_tool.list_models()
    if models:
        for model in models:
            print(f"- {model['name']} (Size: {model['size'] // (1024**3)}GB)")
    else:
        print("No models found or Ollama not running.")

    # Example: Generate text (non-streaming)
    # Ensure you have a model like 'llama2' or 'mistral' pulled in your Ollama instance.
    # You can pull a model by running `ollama pull llama2` in your terminal.
    # model_to_use = "mistral" # Or any other model you have
    # if any(m['name'].startswith(model_to_use) for m in models):
    #     print(f"\n--- Generating text with '{model_to_use}' (non-streaming) ---")
    #     prompt_text = "Why is the sky blue?"
    #     try:
    #         full_response = ollama_tool.generate_text(
    #             model_name=model_to_use,
    #             prompt=prompt_text,
    #             system_prompt="You are a helpful AI assistant."
    #         )
    #         if full_response:
    #             print("\nResponse:")
    #             print(full_response['message']['content'])
    #             print(f"\nTotal duration: {full_response.get('total_duration', 'N/A') / 1e9:.2f}s")
    #     except Exception as e:
    #         print(f"Error during non-streaming generation: {e}")
    # else:
    #     print(f"\nModel '{model_to_use}' not found. Skipping non-streaming example.")

    # Example: Generate text (streaming)
    # if any(m['name'].startswith(model_to_use) for m in models):
    #     print(f"\n--- Generating text with '{model_to_use}' (streaming) ---")
    #     prompt_text_stream = "Write a short poem about coding."
    #     try:
    #         stream_response = ollama_tool.generate_text(
    #             model_name=model_to_use,
    #             prompt=prompt_text_stream,
    #             stream=True
    #         )
    #         if stream_response:
    #             print("\nStreaming Response:")
    #             for chunk in stream_response:
    #                 print(chunk['message']['content'], end='', flush=True)
    #             print("\n--- Stream complete ---")
    #     except Exception as e:
    #         print(f"Error during streaming generation: {e}")
    # else:
    #     print(f"\nModel '{model_to_use}' not found. Skipping streaming example.")

    print("\nOllamaTool example usage finished.")
    print("Note: Actual generation depends on a running Ollama instance and pulled models.")
    pass
