from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the backend directory to the path
backend_dir = str(Path(__file__).parent.parent.absolute())
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'  # Go up two levels: app -> backend
print(f"Loading .env from: {env_path}")
load_dotenv(dotenv_path=env_path, override=True)

# Check for required environment variables
required_env_vars = ["GOOGLE_API_KEY", "PINECONE_API_KEY", "PINECONE_HOST"]
missing_vars = [var for var in required_env_vars if not os.getenv(var) or os.getenv(var).startswith("your_")]
if missing_vars:
    raise EnvironmentError(f"Missing or invalid required environment variables: {', '.join(missing_vars)}")

from app.services.chat import ChatService
from app.services.memory import MemoryService
from app.services.agent import run_agent
from app.models import ChatRequest, ChatResponse, Memory, ClearMemoriesRequest

app = FastAPI(
    title="Chatbot with Memory API",
    description="API for a chatbot with memory capabilities using Google's Gemini",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
memory_service = MemoryService()
chat_service = ChatService()  # No need to pass memory_service for now

@app.post("/chat", response_model=ChatResponse)
async def chat(chat_request: ChatRequest):
    """Handle chat messages and return AI response"""
    print(f"\n=== New Chat Request ===")
    print(f"User ID: {chat_request.user_id}")
    print(f"Message: {chat_request.message}")
    print(f"Use Memory: {chat_request.use_memory}")
    
    try:
        print("Processing message with chat service...")
        response = ""
        if chat_request.use_memory == True:
            agent_response = await run_agent(chat_request.message, chat_service, memory_service, chat_request.user_id)
            response = agent_response.get('reply', '')
        else:
            prompt = """ You are a helpful AI assistant. Respond to the user's message without using memory.
            User's message: {message}"""
            response = await chat_service.generate(prompt, [])
        print("Message processed successfully")
        print(f"Response: {response}")
        
        # Format the response according to ChatResponse model
        return ChatResponse(
            response=response,
            used_memory=chat_request.use_memory,
            relevant_memories=[]
        )
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print("\n=== ERROR DETAILS ===")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print(f"Stack Trace:\n{error_trace}")
        print("====================\n")
        
        # Return more detailed error information
        error_detail = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": error_trace.split('\n')
        }
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )

#clear memory endpoint
@app.post("/clear_memories", response_model=dict)
async def clear_memories(request: ClearMemoriesRequest):
    """Clear all memories for a user"""
    print(f"Clearing memories for user: {request.user_id}")
    try:
        print ("Calling memory service to clear memories...")
        result = await memory_service.clear_memories(request.user_id)
        if result:
            return {"status": "success", "message": "Memories cleared successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to clear memories")
    except Exception as e:
        print(f"Error clearing memories: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
