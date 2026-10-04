#!/bin/bash

if tmux has-session -t dev 2>/dev/null; then
    tmux kill-session -t dev
    exit 0
fi

tmux new-session -d -s dev
tmux send-keys -t dev:0 'cd client && bun run dev' C-m

tmux split-window -h -t dev:0
tmux send-keys -t dev:0.1 'cd server && uv run uvicorn main:app --reload' C-m

tmux attach-session -t dev