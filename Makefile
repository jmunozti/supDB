.PHONY: up down logs install lint test clean env

# Create .env from example if it doesn't exist
env:
	@test -f mcp-server/.env || cp mcp-server/.env.example mcp-server/.env
	@sed -i 's/changeme/dbadmin123/g' mcp-server/.env
	@echo ".env file ready at mcp-server/.env"

# Start PostgreSQL and MongoDB with seed data
up: env
	docker-compose up -d
	@echo "Waiting for databases to be ready..."
	@sleep 5
	@echo "PostgreSQL: localhost:5432"
	@echo "MongoDB:    localhost:27017"
	@echo ""
	@echo "Run 'make install' then 'make run' to start the MCP server"

down:
	docker-compose down -v

logs:
	docker-compose logs -f

# Install Python dependencies with Poetry
install: env
	cd mcp-server && poetry install

# Run the MCP server (stdio mode for Claude Code)
run:
	cd mcp-server && poetry run python server.py

# Lint with ruff
lint:
	cd mcp-server && poetry run ruff check .

# Format code
format:
	cd mcp-server && poetry run ruff format .

# Run tests
test: env
	cd mcp-server && poetry run pytest tests/ -v

# Remove containers and volumes
clean: down
	docker volume prune -f
