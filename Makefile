# Makefile for Wonders of the World
#
# Environment variables are loaded from a .env file in the project root.
# Please create a .env file with the required variables, e.g.:
# MONGODB_ATLAS_PROJECT_ID=your_project_id
# MONGODB_ATLAS_PUBLIC_KEY=your_public_key
# MONGODB_ATLAS_PRIVATE_KEY=your_private_key
# PULUMI_ACCESS_TOKEN=your_pulumi_access_token
# PULUMI_CONFIG_PASSPHRASE=your_passphrase

# Variables
APP_DIR := app
MONGODB_URI_LOCAL := mongodb://localhost:27007/ww?directConnection=true

.PHONY: help run clean clean-local test setup-local setup-cloud setup-venv

# Default target
help:
	@echo "Available commands:"
	@echo "  setup-local    - Setup local environment (venv + vector db)"
	@echo "  setup-cloud    - Setup cloud environment (venv + cloud db)"
	@echo "  run            - Run application locally"
	@echo "  clean          - Clean up generated files"
	@echo "  clean-local    - Clean up local Atlas deployment and venvs"
	@echo "  test           - Test vector search endpoint"

# Check if command exists
check-command = @if ! command -v $(1) &> /dev/null; then \
	echo "Error: $(1) is not installed or not in PATH"; \
	exit 1; \
fi

# Set up virtual environment in specified directory
setup-venv:
	@echo "Setting up Python virtual environment in $(DIR)..."
	$(call check-command,python3)
	@cd $(DIR) && if [ ! -d "venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv venv; \
	else \
		echo "Virtual environment already exists"; \
	fi
	@cd $(DIR) && source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt
	@echo "Virtual environment setup complete for $(DIR)!"

# Setup local environment
setup-local:
	@echo "Setting up local environment..."
	$(MAKE) setup-venv DIR=$(APP_DIR)
	@echo "Setting up local MongoDB deployment..."
	$(call check-command,atlas)
	@cd $(APP_DIR) && if ! grep -q "127.0.0.1 MDB" /etc/hosts; then \
		echo "Adding MDB entry to /etc/hosts (requires sudo)..."; \
		echo "127.0.0.1 MDB" | sudo tee -a /etc/hosts > /dev/null; \
	else \
		echo "MDB entry already exists in /etc/hosts"; \
	fi
	@cd $(APP_DIR) && atlas deployments setup MDB --type LOCAL --port 27007 --force
	@echo "Creating collection"
	@cd $(APP_DIR) && echo "MONGODB_URI=$(MONGODB_URI_LOCAL)" > .env
	@mongosh $(MONGODB_URI_LOCAL) --eval "db.createCollection('facts');"
	@cd $(APP_DIR) && atlas deployments search indexes create --file vector_index.json
	@echo "Local environment setup complete!"

# Setup cloud environment
setup-cloud:
	@set -a; [ -f .env ] && source .env; set +a; \
	echo "Setting up cloud environment..."; \
	echo "Loading environment variables from infra/.env..."; \
	echo "Checking MongoDB Atlas environment variables..."; \
	if [ -z "$$MONGODB_ATLAS_PROJECT_ID" ] || [ -z "$$MONGODB_ATLAS_PUBLIC_KEY" ] || [ -z "$$MONGODB_ATLAS_PRIVATE_KEY" ]; then \
		echo "Error: Required MongoDB Atlas environment variables are not set."; \
		echo "Please set the following environment variables:"; \
		echo "  MONGODB_ATLAS_PROJECT_ID: Your MongoDB Atlas project ID"; \
		echo "  MONGODB_ATLAS_PUBLIC_KEY: Your MongoDB Atlas public API key"; \
		echo "  MONGODB_ATLAS_PRIVATE_KEY: Your MongoDB Atlas private API key"; \
		echo ""; \
		echo "You can set them in your .env file or with export."; \
		exit 1; \
	fi; \
	echo "Checking Pulumi Access Token..."; \
	if [ -z "$$PULUMI_ACCESS_TOKEN" ]; then \
		echo "Error: PULUMI_ACCESS_TOKEN environment variable is not set."; \
		echo "Please set it with:"; \
		echo "  export PULUMI_ACCESS_TOKEN=your_pulumi_access_token"; \
		exit 1; \
	fi; \
	echo "Checking Pulumi Config Passphrase..."; \
    if [ -z "$$PULUMI_CONFIG_PASSPHRASE" ]; then \
        echo "Error: PULUMI_CONFIG_PASSPHRASE environment variable is not set."; \
        echo "Please set it in your .env file or with:"; \
        echo "  export PULUMI_CONFIG_PASSPHRASE=your_passphrase"; \
        exit 1; \
    fi; \
	$(MAKE) setup-venv DIR=$(APP_DIR); \
	echo "Setting up infrastructure with Pulumi..."; \
	if [ ! -d "venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv venv; \
	fi; \
	source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt; \
	pulumi --non-interactive login; \
	pulumi --non-interactive stack init vectorinfra || true; \
	pulumi --non-interactive up  --stack vectorinfra --yes; \
	echo "MONGODB_URI=$$(pulumi stack output MONGODB_URI --show-secrets)" > $(APP_DIR)/.env; \
	echo "Cloud environment setup complete! "

# Run application
run:
	@echo "Running application ..."
	cd $(APP_DIR) && source venv/bin/activate && python app.py > app.log 2>&1 &

# Clean up generated files
clean:
	@echo "Cleaning up generated files..."
	rm -rf $(APP_DIR)/venv venv
	rm -f $(APP_DIR)/app.log $(APP_DIR)/.env
	@echo "Cleanup complete!"

# Clean up local Atlas deployment and deactivate venvs
clean-local:
	@echo "Cleaning up local Atlas deployment..."
	@if command -v atlas &> /dev/null; then \
		atlas deployments delete MDB --force || echo "No local deployment found or already deleted"; \
	else \
		echo "Atlas CLI not found. Skipping deployment cleanup."; \
	fi
	@echo "Removing MDB entry from /etc/hosts..."
	@if grep -q "127.0.0.1 MDB" /etc/hosts; then \
		sudo sed -i '' '/127\.0\.0\.1 MDB/d' /etc/hosts; \
		echo "MDB entry removed from /etc/hosts"; \
	else \
		echo "MDB entry not found in /etc/hosts"; \
	fi
	@echo "Deactivating virtual environments..."
	@if [ -n "$$VIRTUAL_ENV" ]; then \
		echo "Deactivating current virtual environment: $$VIRTUAL_ENV"; \
		deactivate || true; \
	fi
	@echo "Removing virtual environments..."
	rm -rf $(APP_DIR)/venv venv
	@echo "Local Atlas deployment and venv cleanup complete!"

# Test vector search endpoint
test:
	@echo "Testing vector search endpoint..."
	@echo "Testing with prompt: 'Brazil'"
	curl -s "http://localhost:8080/vectorsearch?prompt=Brazil"