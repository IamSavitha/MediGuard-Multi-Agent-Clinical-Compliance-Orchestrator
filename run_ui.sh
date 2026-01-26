#!/bin/bash
# Script to run the Streamlit UI with proper environment

cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Check if langchain-ollama is installed
python -c "import langchain_ollama" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing langchain-ollama..."
    pip install langchain-ollama
fi

# Check if streamlit is installed
python -c "import streamlit" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing streamlit..."
    pip install streamlit
fi

# Run Streamlit
echo "Starting Streamlit UI..."
echo "The app will open in your browser at http://localhost:8501"
streamlit run app.py
