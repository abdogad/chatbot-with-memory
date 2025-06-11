import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
import google.generativeai as genai
from google.generativeai import types

# Configure the Gemini API key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Function schemas
FUNCTION_DEFINITIONS: List[Dict[str, Any]] = {
    "check_memory_necessity": {
        "name": "check_memory_necessity",
        "description": "Determine if memory search is needed",
        "parameters": {
            "type": "object",
            "properties": {
                "needs_memory": {"type": "boolean"},
                "reason": {"type": "string"}
            },
            "required": ["needs_memory", "reason"]
        }
    },
    "generate_search_queries": {
        "name": "generate_search_queries",
        "description": "Generate focused search queries for memory retrieval",
        "parameters": {
            "type": "object",
            "properties": {
                "queries": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["queries"]
        }
    }
}


# Pydantic models for function results
class CheckMemoryResult(BaseModel):
    needs_memory: bool
    reason: Optional[str]

class QueryGeneratorResult(BaseModel):
    queries: List[str]

# ChatService Implementation
class ChatService:
    def __init__(self, model_name: str = "gemini-2.5-flash-preview-05-20"):
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)
        

    async def call_function(self, name: str, prompt: str, type: str) -> Any:
        """
        Invoke a function call via the Gemini chat API.
        Returns a Pydantic-validated result object.
        """
        tool = types.Tool(function_declarations=[FUNCTION_DEFINITIONS[name]])

        response = self.model.generate_content(prompt, tools=[tool])
        print(response)
        if response.candidates[0].content.parts[0].function_call:
            print("Function call found")
            func_call = response.candidates[0].content.parts[0].function_call
            # print(f"Function call: {func_call.args["needs_memory"]}")
            return func_call
        else:
            return False
    async def generate(
        self,
        prompt: str,
        history: List
    ) -> str:
        """
        Generate a text response, optionally conditioning on retrieved memory.
        """
        chat = self.model.start_chat(history=history)
        response = await chat.send_message_async(prompt)
        return response.text
    
