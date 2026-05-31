#!/bin/bash
# YTForge — one-shot setup & launch script
# Run this from the ytforge/ root directory

set -e

echo ""
echo "⚡ YTForge Setup"
echo "──────────────────────────────────"

# ── 1. Python backend deps ──────────────────────────────────────────────────
echo ""
echo "📦 Installing Python dependencies..."
pip install flask flask-cors yt-dlp --quiet

echo ""
echo "💡 Optional: install Whisper for high-accuracy transcription"
echo "   pip install openai-whisper"
echo "   (requires ~1.5 GB; skip to use auto-subtitle fallback)"

# ── 2. Frontend deps ─────────────────────────────────────────────────────────
echo ""
echo "📦 Installing frontend (Node) dependencies..."
cd frontend
npm install --silent
cd ..

# ── 3. Check yt-dlp ──────────────────────────────────────────────────────────
if ! command -v yt-dlp &> /dev/null; then
  echo ""
  echo "⚠  yt-dlp not on PATH — trying pip install..."
  pip install yt-dlp
fi

echo ""
echo "✅ All dependencies installed!"
echo ""
echo "──────────────────────────────────"
echo "🚀 Starting YTForge..."
echo ""
echo "  Backend  → http://localhost:5000"
echo "  Frontend → http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both servers."
echo "──────────────────────────────────"
echo ""

# ── 4. Start backend in background ──────────────────────────────────────────
python files/app.py &
BACKEND_PID=$!

# ── 5. Start frontend ────────────────────────────────────────────────────────
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# ── 6. Cleanup on exit ───────────────────────────────────────────────────────
trap "echo ''; echo 'Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

wait
