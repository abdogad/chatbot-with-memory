# Chatbot with Memory

A full-stack application featuring a chatbot with memory capabilities using Google's Gemini AI and Pinecone for vector storage.

## Project Structure

```
/
├── frontend/          # Streamlit frontend application
│   ├── app.py        # Main Streamlit application
│   ├── requirements.txt
│   └── .env          # Environment variables (not tracked in git)
├── backend/          # FastAPI backend application
│   ├── app/         # Backend application code
│   ├── requirements.txt
│   └── .env         # Environment variables (not tracked in git)
└── .gitignore
```

## Setup

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file with the following variables:
   ```
   GOOGLE_API_KEY=your_google_api_key
   PINECONE_API_KEY=your_pinecone_api_key
   PINECONE_HOST=your_pinecone_host
   ```

4. Run the backend:
   ```bash
   uvicorn app.main:app --reload
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file with:
   ```
   BACKEND_URL=http://localhost:8000
   ```

4. Run the frontend:
   ```bash
   streamlit run app.py
   ```

## Environment Variables

### Backend (.env)
- `GOOGLE_API_KEY`: Your Google API key for Gemini AI
- `PINECONE_API_KEY`: Your Pinecone API key
- `PINECONE_HOST`: Your Pinecone host URL

### Frontend (.env)
- `BACKEND_URL`: URL of the backend service (default: http://localhost:8000)

## Features

- Chat interface with memory capabilities
- Semantic search for previous conversations
- Real-time response generation
- Memory management and clearing
- Modern and responsive UI

## Technologies Used

- Frontend: Streamlit
- Backend: FastAPI
- AI: Google Gemini
- Vector Database: Pinecone
- Environment Management: python-dotenv 