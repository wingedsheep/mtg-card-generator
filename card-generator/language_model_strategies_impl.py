import json
from typing import Any, Dict, Optional, List

import json
from typing import Any, Dict, Optional, List

from models import Config
from language_model_strategies import LanguageModelStrategy
from tools.ollama_tool import OllamaTool

# Import OpenAI only if OpenRouter strategy is chosen and used.
# This is good practice for conditional dependencies.
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None # Allows type hinting and runtime checks

class OpenRouterLanguageModel(LanguageModelStrategy):
    def _initialize_client_if_needed(self):
        if OpenAI is None:
            raise ImportError("OpenAI library is not installed. Please install it to use the OpenRouter strategy.")

        api_key = self._get_api_key("openrouter")
        if not api_key:
            raise ValueError("OpenRouter API key not found in settings.")

        base_url = self.strategy_specific_config.get("base_url", "https://openrouter.ai/api/v1")

        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
        )
        print("OpenRouter client initialized.")

    def generate_text(self,
                      prompt: str,
                      system_prompt: Optional[str] = None,
                      model_key: Optional[str] = "default_main",
                      **kwargs: Any) -> str:
        model_id = self._get_model_id(model_key)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Merge default params from config with call-specific kwargs
        final_params = self._get_common_params()
        final_params.update(kwargs) # Call-specific kwargs override config defaults

        print(f"Generating text with OpenRouter model: {model_id}, params: {final_params}")

        completion = self.client.chat.completions.create(
            model=model_id,
            messages=messages,
            extra_headers=self._get_api_headers(),
            **final_params
        )
        return completion.choices[0].message.content

    def generate_json_response(self,
                               prompt: str,
                               system_prompt: Optional[str] = None,
                               model_key: Optional[str] = "default_json",
                               **kwargs: Any) -> Any:
        # Use "json_params" from config if available, else common "params"
        default_params = self.strategy_specific_config.get("json_params", self._get_common_params())
        final_params = default_params.copy()
        final_params.update(kwargs)

        # For OpenAI-compatible APIs, some models support a JSON response mode
        # This might need to be enabled via params if the model supports it, e.g. "response_format": {"type": "json_object"}
        # For now, we assume the model is instructed to produce JSON via the prompt.

        raw_text_response = self.generate_text(
            prompt=prompt,
            system_prompt=system_prompt or "You are a helpful assistant designed to output JSON.",
            model_key=model_key,
            **final_params # Pass merged params
        )

        try:
            # Basic cleaning: find the first '{' or '[' and last '}' or ']'
            json_start = -1
            json_end = -1

            first_brace = raw_text_response.find('{')
            first_bracket = raw_text_response.find('[')

            if first_brace == -1 and first_bracket == -1:
                raise json.JSONDecodeError("No JSON start character found.", raw_text_response, 0)

            if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
                json_start = first_brace
                last_char = '}'
            else:
                json_start = first_bracket
                last_char = ']'

            json_end = raw_text_response.rfind(last_char)

            if json_start != -1 and json_end != -1 and json_end > json_start:
                json_text = raw_text_response[json_start : json_end + 1]
                return json.loads(json_text)
            else:
                raise json.JSONDecodeError("Could not extract valid JSON block.", raw_text_response, 0)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON response from OpenRouter: {e}")
            print("Raw response was:", raw_text_response)
            raise


class OllamaLanguageModel(LanguageModelStrategy):
    def _initialize_client_if_needed(self):
        # OllamaTool itself initializes the client
        host = self.strategy_specific_config.get("host")
        self.tool = OllamaTool(host=host) # OllamaTool client is ollama.Client
        print(f"Ollama client initialized (host: {host or 'default'}).")

    def generate_text(self,
                      prompt: str,
                      system_prompt: Optional[str] = None,
                      model_key: Optional[str] = "default_main",
                      **kwargs: Any) -> str:
        model_id = self._get_model_id(model_key)

        # Merge default params from config with call-specific kwargs
        final_params = self._get_common_params()
        final_params.update(kwargs) # Call-specific kwargs override config defaults

        # OllamaTool's generate_text handles stream=False by default in its signature
        # but we can pass it if it's in final_params
        stream_flag = self.strategy_specific_config.get("stream", False)
        if 'stream' in final_params: # Allow override via kwargs
            stream_flag = final_params.pop('stream')

        print(f"Generating text with Ollama model: {model_id}, params: {final_params}, stream: {stream_flag}")

        response = self.tool.generate_text(
            model_name=model_id,
            prompt=prompt,
            system_prompt=system_prompt,
            stream=stream_flag,
            options=final_params # Ollama specific params go into 'options' usually
        )

        if stream_flag:
            full_response_content = ""
            for chunk in response:
                full_response_content += chunk.get('message', {}).get('content', '')
            return full_response_content
        else:
            return response.get('message', {}).get('content', '') if response else ""


    def generate_json_response(self,
                               prompt: str,
                               system_prompt: Optional[str] = None,
                               model_key: Optional[str] = "default_json",
                               **kwargs: Any) -> Any:
        model_id = self._get_model_id(model_key)

        default_params = self.strategy_specific_config.get("json_params", self._get_common_params())
        final_params = default_params.copy()
        final_params.update(kwargs)

        # Check if Ollama model is instructed to use JSON format directly
        ollama_format = final_params.pop("format", None) # Remove format if it's to be passed directly
        if ollama_format and ollama_format.lower() != 'json':
             print(f"Warning: Ollama json_params contains 'format: {ollama_format}'. Forcing to 'json' for generate_json_response.")
        ollama_format = 'json' # Ensure we request JSON format if possible

        stream_flag = self.strategy_specific_config.get("stream", False)
        if 'stream' in final_params:
             stream_flag = final_params.pop('stream')
        if stream_flag:
            print("Warning: Streaming is not recommended for JSON responses with Ollama, may complicate parsing. Forcing stream=False.")
            stream_flag = False


        print(f"Generating JSON with Ollama model: {model_id}, format: {ollama_format}, params: {final_params}")

        response_data = self.tool.generate_text(
            model_name=model_id,
            prompt=prompt,
            system_prompt=system_prompt or "You are a helpful assistant designed to output JSON.",
            stream=stream_flag, # Should be False for reliable JSON
            format=ollama_format, # Pass format to ollama client call
            options=final_params
        )

        # If format='json' was successful, response_data['message']['content'] should be a string representing JSON
        # or sometimes, the ollama library might parse it if the server does.
        # For robustness, we assume it's a string that needs parsing.

        raw_json_string = response_data.get('message', {}).get('content', '') if response_data else ''

        if not raw_json_string:
            raise ValueError("Ollama returned empty content for JSON response.")

        try:
            # The 'ollama' library with format='json' might return an already parsed dict in 'response'
            # if the model directly outputs a JSON string that the client then parses.
            # Or, 'message.content' might be the string. Let's test.
            # Based on ollama-python docs, if format='json', the response['message']['content'] is a string.
            return json.loads(raw_json_string)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON response from Ollama: {e}")
            print("Raw response string was:", raw_json_string)
            # Provide more context from the full response if available
            if response_data:
                 print("Full Ollama response object:", response_data)
            raise
