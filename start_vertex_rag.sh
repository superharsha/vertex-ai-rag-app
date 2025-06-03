#!/bin/bash
# Start Vertex AI RAG System (FastAPI + Streamlit)

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GOOGLERAGE_DIR="$PROJECT_DIR/GoogleRageEngine"
LOGS_DIR="$GOOGLERAGE_DIR/logs"

echo "🚀 Starting Vertex AI RAG System"
echo "Project Directory: $PROJECT_DIR"
echo "GoogleRageEngine Directory: $GOOGLERAGE_DIR"
echo "Logs Directory: $LOGS_DIR"

# Create logs directory
echo "📁 Creating logs directory..."
mkdir -p "$LOGS_DIR"

# Check for existing processes and kill them
echo "🔍 Checking for existing processes..."

# Kill existing backend process on port 8000
BACKEND_PID=$(lsof -ti:8000)
if [ ! -z "$BACKEND_PID" ]; then
    echo "⚠️  Killing existing backend process on port 8000 (PID: $BACKEND_PID)"
    kill -9 $BACKEND_PID 2>/dev/null || true
    sleep 2
fi

# Kill existing frontend process on port 8501
FRONTEND_PID=$(lsof -ti:8501)
if [ ! -z "$FRONTEND_PID" ]; then
    echo "⚠️  Killing existing frontend process on port 8501 (PID: $FRONTEND_PID)"
    kill -9 $FRONTEND_PID 2>/dev/null || true
    sleep 2
fi

# Start FastAPI backend
echo "🔧 Starting FastAPI backend..."
BACKEND_CMD="/opt/homebrew/bin/python3.11 $GOOGLERAGE_DIR/fastapi_vertex_rag.py"
echo "Command: $BACKEND_CMD"
echo "Logs: $LOGS_DIR/backend.log"

cd "$GOOGLERAGE_DIR"
$BACKEND_CMD > "$LOGS_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "✅ Backend started with PID: $BACKEND_PID"

# Wait for backend to start
sleep 5
if lsof -ti:8000 > /dev/null; then
    echo "✅ Backend is running on port 8000"
else
    echo "❌ Backend failed to start on port 8000"
    exit 1
fi

# Start Streamlit frontend
echo "🎨 Starting Streamlit frontend..."
FRONTEND_CMD="/opt/homebrew/bin/python3.11 -m streamlit run $GOOGLERAGE_DIR/streamlit_vertex_rag.py --server.port 8501"
echo "Command: $FRONTEND_CMD"
echo "Logs: $LOGS_DIR/frontend.log"

cd "$GOOGLERAGE_DIR"
$FRONTEND_CMD > "$LOGS_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "✅ Frontend started with PID: $FRONTEND_PID"

# Wait for frontend to start
sleep 5
if lsof -ti:8501 > /dev/null; then
    echo "✅ Frontend is running on port 8501"
else
    echo "❌ Frontend failed to start on port 8501"
    exit 1
fi

echo ""
echo "🎉 Vertex AI RAG System started successfully!"
echo ""
echo "📊 Access Information:"
echo "Frontend (Streamlit UI): http://localhost:8501"
echo "Backend (FastAPI):       http://localhost:8000"
echo "API Documentation:       http://localhost:8000/docs"
echo ""
echo "📝 Log Files:"
echo "Backend logs:  $LOGS_DIR/backend.log"
echo "Frontend logs: $LOGS_DIR/frontend.log"
echo ""
echo "📊 Process IDs:"
echo "Backend PID:  $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "💡 Tips:"
echo "• Monitor backend logs:  tail -f $LOGS_DIR/backend.log"
echo "• Monitor frontend logs: tail -f $LOGS_DIR/frontend.log"
echo "• Stop the system:       ./GoogleRageEngine/stop_vertex_rag.sh"
echo ""
echo "🚀 Ready to use! Open http://localhost:8501 in your browser."
echo "📡 System is running. Press Ctrl+C to stop."

# Function to handle script termination
cleanup() {
    echo ""
    echo "🛑 Shutting down Vertex AI RAG System..."
    
    # Kill backend
    if kill -0 $BACKEND_PID 2>/dev/null; then
        kill $BACKEND_PID
        echo "✅ Backend stopped"
    fi
    
    # Kill frontend  
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        kill $FRONTEND_PID
        echo "✅ Frontend stopped"
    fi
    
    echo "🏁 Vertex AI RAG System shut down complete"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Wait for processes
wait 