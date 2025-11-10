# DICOM MWL-MPPS Makefile
# Simplifies common development and deployment tasks

.PHONY: help build start stop test clean logs shell db-shell

# Default target
help: ## Show this help message
	@echo "DICOM MWL-MPPS Development Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Docker operations
build: ## Build all Docker images
	docker compose build

start: ## Start all services
	docker compose up -d

start-dev: ## Start services with development overrides
	docker compose -f docker-compose.yml -f docker-compose.override.yml up -d

stop: ## Stop all services
	docker compose down

restart: ## Restart all services
	docker compose restart

clean: ## Stop services and remove volumes
	docker compose down -v
	docker system prune -f

# Development
logs: ## Show logs from all services
	docker compose logs -f

logs-api: ## Show logs from API service
	docker compose logs -f mwl-api

logs-dicom: ## Show logs from DICOM service
	docker compose logs -f dicom-mwl-mpps

shell: ## Get shell access to DICOM service
	docker compose exec dicom-mwl-mpps /bin/bash

shell-api: ## Get shell access to API service
	docker compose exec mwl-api /bin/bash

db-shell: ## Get MySQL shell access
	docker compose exec mysql_db mysql -u root -proot orthanc_ris

# Testing
test: ## Run integration tests
	docker compose --profile test run --rm test-runner

test-build: ## Build and run tests
	docker compose build test-runner
	docker compose --profile test run --rm test-runner

test-manual: ## Create test MWL entry and run manual DICOM tests
	@echo "Creating test MWL entry..."
	curl -X POST http://localhost:8000/mwl/create_from_json \
		-H "Content-Type: application/json" \
		-d '{"AccessionNumber": "TEST123", "PatientID": "P1", "PatientName": "DOE^JOHN", "PatientBirthDate": "19800101", "PatientSex": "M", "StudyInstanceUID": "1.2.3.4.5", "ScheduledProcedureStepSequence": [{"ScheduledProcedureStepStartDate": "20240625", "ScheduledStationAETitle": "ORTHANC"}]}'
	@echo ""
	@echo "Testing MWL C-FIND..."
	findscu localhost 4104 -W -v -d -k "AccessionNumber" -k "PatientName" -k "PatientID" || echo "findscu not found, skipping"

# Database operations
db-reset: ## Reset database (WARNING: destroys all data)
	docker compose down -v
	docker compose up -d mysql_db
	@echo "Waiting for database to initialize..."
	sleep 10
	docker compose up -d

db-backup: ## Backup database
	docker compose exec mysql_db mysqldump -u root -proot orthanc_ris > backup_$(shell date +%Y%m%d_%H%M%S).sql

# Package operations
package: ## Create release package
	@echo "Creating release package..."
	tar --exclude='.git' --exclude='*.pyc' --exclude='__pycache__' --exclude='.DS_Store' \
		-czf dicom-mwl-mpps-$(shell date +%Y%m%d).tar.gz .
	@echo "Package created: dicom-mwl-mpps-$(shell date +%Y%m%d).tar.gz"

# Health checks
health: ## Check service health
	@echo "Checking service health..."
	@echo "API Health:"
	curl -s http://localhost:8000/health || echo "API not responding"
	@echo ""
	@echo "DICOM Service:"
	@echo "Port check: $$(nc -z localhost 4104 && echo '✓ Port 4104 open' || echo '✗ Port 4104 closed')"
	@echo "Service check: $$(docker compose exec dicom-mwl-mpps python -c 'import socket; s=socket.socket(); s.settimeout(1); result=s.connect_ex((\"localhost\", 104)); s.close(); print(\"✓ DICOM service responding\" if result==0 else \"✗ DICOM service not responding\")' 2>/dev/null || echo '✗ Container not accessible')"
	@echo ""
	@echo "Database:"
	docker compose exec mysql_db mysqladmin -u root -proot ping || echo "Database not responding"

# Development shortcuts
dev-setup: build start-dev ## Quick development setup
	@echo "Development environment started!"
	@echo "API: http://localhost:8000"
	@echo "DICOM: localhost:4104"
	@echo "MySQL: localhost:3306"

production: ## Start in production mode
	docker compose -f docker-compose.yml up -d

# Documentation
docs: ## Generate documentation (if implemented)
	@echo "Documentation generation not implemented yet"

# Default environment file
.env:
	@echo "Creating default .env file..."
	@echo "DB_HOST=mysql_db" > .env
	@echo "DB_USER=root" >> .env
	@echo "DB_PASSWORD=root" >> .env
	@echo "DB_NAME=orthanc_ris" >> .env
	@echo "WORKLIST_DIR=/worklist" >> .env
	@echo "ENVIRONMENT=development" >> .env
	@echo "LOG_LEVEL=INFO" >> .env 