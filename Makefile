.PHONY: setup dev stop paper test lint

SESSION := stocker

setup:
	@echo "==> Installing backend dependencies..."
	cd backend && uv sync --all-extras
	@echo "==> Installing frontend dependencies..."
	cd frontend && pnpm install
	@if [ ! -f .envrc.local ]; then \
		cp .envrc.example .envrc.local; \
		echo "==> Created .envrc.local — fill in your API keys, then: direnv allow ."; \
	else \
		echo "==> .envrc.local already exists, skipping."; \
	fi
	@echo "==> Starting infrastructure..."
	docker-compose up -d
	@echo "==> Setup complete."

dev:
	@docker-compose up -d
	@if tmux has-session -t $(SESSION) 2>/dev/null; then \
		tmux attach-session -t $(SESSION); \
	else \
		tmux new-session -d -s $(SESSION); \
		tmux split-window -v -t $(SESSION); \
		tmux split-window -v -t $(SESSION); \
		tmux select-layout -t $(SESSION) even-vertical; \
		tmux send-keys -t $(SESSION):0.0 'cd $(PWD) && direnv exec . sh -c "cd backend && PYTHONPATH=. uv run uvicorn app.main:app --reload --port 7878"' Enter; \
		tmux send-keys -t $(SESSION):0.1 'cd frontend && pnpm dev --port 8787' Enter; \
		tmux send-keys -t $(SESSION):0.2 'docker-compose logs -f' Enter; \
		tmux select-pane -t $(SESSION):0.0; \
		tmux attach-session -t $(SESSION); \
	fi

stop:
	@echo "==> Stopping services..."
	@tmux kill-session -t $(SESSION) 2>/dev/null && echo "tmux session stopped" || true
	@lsof -ti :7878 | xargs kill -9 2>/dev/null && echo "backend stopped" || true
	@lsof -ti :8787 | xargs kill -9 2>/dev/null && echo "frontend stopped" || true
	@echo "==> Done."

paper:
	cd backend && TRADING_MODE=paper PYTHONPATH=. uv run uvicorn app.main:app --reload --port 7878

test:
	cd backend && uv run pytest

lint:
	cd backend && uv run ruff check app tests
	cd frontend && pnpm lint
