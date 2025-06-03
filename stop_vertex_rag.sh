#!/bin/bash
# Stop Vertex AI RAG System

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GOOGLERAGE_DIR="$PROJECT_DIR/GoogleRageEngine"
LOGS_DIR="$GOOGLERAGE_DIR/logs"

echo "🛑 Stopping Vertex AI RAG System"
echo "Project Directory: $PROJECT_DIR"
echo "GoogleRageEngine Directory: $GOOGLERAGE_DIR"

# Function to kill processes on a specific port
kill_port() {
    local port=$1
    local name=$2
    
    echo "🔍 Checking for processes on port $port ($name)..."
    
    # Get PIDs listening on the port
    PIDS=$(lsof -ti:$port 2>/dev/null)
    
    if [ ! -z "$PIDS" ]; then
        echo "⚠️  Found processes on port $port: $PIDS"
        
        # Try graceful termination first
        echo "🔄 Attempting graceful shutdown..."
        for PID in $PIDS; do
            kill -TERM $PID 2>/dev/null
        done
        
        # Wait a bit for graceful shutdown
        sleep 3
        
        # Check if any processes are still running
        REMAINING_PIDS=$(lsof -ti:$port 2>/dev/null)
        
        if [ ! -z "$REMAINING_PIDS" ]; then
            echo "⚡ Force killing remaining processes..."
            for PID in $REMAINING_PIDS; do
                kill -9 $PID 2>/dev/null
            done
            sleep 1
        fi
        
        # Final check
        FINAL_CHECK=$(lsof -ti:$port 2>/dev/null)
        if [ -z "$FINAL_CHECK" ]; then
            echo "✅ $name stopped successfully"
        else
            echo "❌ Failed to stop $name"
        fi
    else
        echo "ℹ️  No $name processes found on port $port"
    fi
}

# Kill FastAPI backend (port 8000)
kill_port 8000 "FastAPI Backend"

# Kill Streamlit frontend (port 8501)  
kill_port 8501 "Streamlit Frontend"

# Additional cleanup - kill any remaining Python processes running our scripts
echo ""
echo "🧹 Additional cleanup..."

# Kill any remaining fastapi_vertex_rag.py processes
FASTAPI_PIDS=$(pgrep -f "fastapi_vertex_rag.py" 2>/dev/null)
if [ ! -z "$FASTAPI_PIDS" ]; then
    echo "🔄 Killing remaining FastAPI processes: $FASTAPI_PIDS"
    for PID in $FASTAPI_PIDS; do
        kill -9 $PID 2>/dev/null
    done
fi

# Kill any remaining streamlit_vertex_rag.py processes
STREAMLIT_PIDS=$(pgrep -f "streamlit_vertex_rag.py" 2>/dev/null)
if [ ! -z "$STREAMLIT_PIDS" ]; then
    echo "🔄 Killing remaining Streamlit processes: $STREAMLIT_PIDS"
    for PID in $STREAMLIT_PIDS; do
        kill -9 $PID 2>/dev/null
    done
fi

# Kill any remaining uvicorn processes
UVICORN_PIDS=$(pgrep -f "uvicorn" 2>/dev/null)
if [ ! -z "$UVICORN_PIDS" ]; then
    echo "🔄 Killing remaining Uvicorn processes: $UVICORN_PIDS"
    for PID in $UVICORN_PIDS; do
        kill -9 $PID 2>/dev/null
    done
fi

echo ""
echo "🔍 Final verification..."

# Check if ports are clear
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "❌ Port 8000 still in use"
else
    echo "✅ Port 8000 is clear"
fi

if lsof -ti:8501 > /dev/null 2>&1; then
    echo "❌ Port 8501 still in use"
else
    echo "✅ Port 8501 is clear"
fi

echo ""
echo "🏁 Vertex AI RAG System shutdown complete!"
echo ""
echo "📝 Log files are preserved at:"
echo "• Backend logs:  $LOGS_DIR/backend.log"
echo "• Frontend logs: $LOGS_DIR/frontend.log"
echo ""
echo "💡 To restart the system, run:"
echo "  ./GoogleRageEngine/start_vertex_rag.sh"
echo "" 