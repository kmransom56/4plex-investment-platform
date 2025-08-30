#!/bin/bash

# 4-Plex Foreclosure Research - Integrated Platform Startup
# Comprehensive startup script for the complete integrated system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="4-Plex Investment Platform"
COMPOSE_FILE="docker-compose.integrated.yml"
LOG_FILE="/tmp/4plex-startup.log"

echo -e "${PURPLE}🏘️  Starting $PROJECT_NAME${NC}"
echo -e "${CYAN}===========================================${NC}"

# Function to print status messages
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a service is running on a port
check_port() {
    local port=$1
    local service_name=$2
    
    if nc -z localhost $port 2>/dev/null; then
        print_success "$service_name is running on port $port"
        return 0
    else
        print_warning "$service_name is not responding on port $port"
        return 1
    fi
}

# Function to wait for service to be ready
wait_for_service() {
    local port=$1
    local service_name=$2
    local max_attempts=${3:-30}
    local attempt=0
    
    print_status "Waiting for $service_name to be ready on port $port..."
    
    while [ $attempt -lt $max_attempts ]; do
        if nc -z localhost $port 2>/dev/null; then
            print_success "$service_name is ready!"
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done
    
    print_error "$service_name failed to start within expected time"
    return 1
}

# Check prerequisites
print_status "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed or not in PATH"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed or not in PATH"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed or not in PATH"
    exit 1
fi

print_success "All prerequisites are available"

# Check if we're in the right directory
if [ ! -f "$COMPOSE_FILE" ]; then
    print_error "Docker Compose file $COMPOSE_FILE not found in current directory"
    print_error "Please run this script from the 4plex-foreclosure-research directory"
    exit 1
fi

# Create required directories
print_status "Creating required directories..."
mkdir -p data logs config/grafana config/prometheus web/build
print_success "Directories created"

# Stop any existing containers
print_status "Stopping any existing containers..."
docker-compose -f $COMPOSE_FILE down 2>/dev/null || true

# Build and start all services
print_status "Building and starting integrated platform services..."
echo -e "${YELLOW}This may take several minutes for the initial build...${NC}"

# Start core services first
print_status "Starting core database services..."
docker-compose -f $COMPOSE_FILE up -d postgres neo4j redis

# Wait for databases to be ready
wait_for_service 5433 "PostgreSQL" 60
wait_for_service 7688 "Neo4j" 60
wait_for_service 6380 "Redis" 30

# Start application services
print_status "Starting application services..."
docker-compose -f $COMPOSE_FILE up -d foreclosure_research valuation_app integration_service

# Wait for applications to be ready
wait_for_service 11050 "Foreclosure Research System" 120
wait_for_service 3000 "Multifamily Valuation App" 120
wait_for_service 11060 "Integration Service" 60

# Start monitoring services
print_status "Starting monitoring services..."
docker-compose -f $COMPOSE_FILE up -d grafana prometheus

wait_for_service 11062 "Grafana" 30
wait_for_service 11063 "Prometheus" 30

# Build and start the unified dashboard
print_status "Building and starting unified dashboard..."
if [ -d "web" ]; then
    cd web
    if [ -f "package.json" ]; then
        print_status "Installing dashboard dependencies..."
        npm install --silent
        
        print_status "Building React application..."
        npm run build
        
        cd ..
    else
        print_warning "Dashboard package.json not found, skipping npm build"
    fi
else
    print_warning "Web directory not found, creating placeholder dashboard"
    mkdir -p web/build
    echo "<html><body><h1>Dashboard will be available shortly</h1></body></html>" > web/build/index.html
fi

docker-compose -f $COMPOSE_FILE up -d unified_dashboard

wait_for_service 11061 "Unified Dashboard" 60

# Start background services
print_status "Starting background workers..."
docker-compose -f $COMPOSE_FILE up -d celery_worker celery_beat

# Start reverse proxy
print_status "Starting nginx reverse proxy..."
docker-compose -f $COMPOSE_FILE up -d nginx

wait_for_service 11070 "Nginx HTTP" 30
wait_for_service 11071 "Nginx HTTPS" 30

# Final health check
print_status "Performing system health check..."
echo ""

# Check all services
services=(
    "5433:PostgreSQL Database"
    "7688:Neo4j Graph Database" 
    "6380:Redis Cache"
    "11050:Foreclosure Research API"
    "3000:Multifamily Valuation App"
    "11060:Integration Service API"
    "11061:Unified Dashboard"
    "11062:Grafana Monitoring"
    "11063:Prometheus Metrics"
    "11070:Nginx HTTP Proxy"
    "11071:Nginx HTTPS Proxy"
)

all_services_ok=true
for service in "${services[@]}"; do
    port=$(echo $service | cut -d: -f1)
    name=$(echo $service | cut -d: -f2)
    
    if ! check_port $port "$name"; then
        all_services_ok=false
    fi
done

echo ""
if [ "$all_services_ok" = true ]; then
    print_success "🎉 All services are running successfully!"
else
    print_warning "Some services may not be fully ready yet. Check the logs for details."
fi

# Display access information
echo ""
echo -e "${PURPLE}🌟 4-Plex Investment Platform - Access Information${NC}"
echo -e "${CYAN}=================================================${NC}"
echo ""
echo -e "${GREEN}📊 Main Dashboard:${NC}           http://localhost:11061"
echo -e "${GREEN}🔍 Integration API:${NC}          http://localhost:11060"
echo -e "${GREEN}🏘️  Research System:${NC}         http://localhost:11050"
echo -e "${GREEN}💰 Valuation App:${NC}           http://localhost:3000"
echo ""
echo -e "${BLUE}📈 Monitoring:${NC}"
echo -e "   Grafana Dashboard:        http://localhost:11062 (admin/admin)"
echo -e "   Prometheus Metrics:       http://localhost:11063"
echo ""
echo -e "${BLUE}💾 Databases:${NC}"
echo -e "   Neo4j Browser:            http://localhost:7475 (neo4j/unified_neo4j_pass)"
echo -e "   PostgreSQL:               localhost:5433 (unified_user/unified_pass)"
echo -e "   Redis:                    localhost:6380"
echo ""
echo -e "${BLUE}🌐 Reverse Proxy:${NC}"
echo -e "   HTTP:                     http://localhost:11070"
echo -e "   HTTPS:                    https://localhost:11071"
echo ""
echo -e "${GREEN}📋 Quick Health Check:${NC}       http://localhost:11060/api/unified/health"
echo ""

# API Examples
echo -e "${PURPLE}🔧 API Examples:${NC}"
echo ""
echo -e "${CYAN}# Start property discovery in Georgia counties${NC}"
echo "curl -X POST http://localhost:11060/api/unified/discovery/start"
echo ""
echo -e "${CYAN}# Get investment opportunities (score >= 70)${NC}"
echo "curl http://localhost:11060/api/unified/opportunities?min_score=70"
echo ""
echo -e "${CYAN}# Check dashboard summary${NC}"
echo "curl http://localhost:11060/api/unified/dashboard/summary"
echo ""

# Show logs command
echo -e "${YELLOW}📋 To view logs:${NC}"
echo "docker-compose -f $COMPOSE_FILE logs -f [service-name]"
echo ""
echo -e "${YELLOW}📋 To stop all services:${NC}"
echo "docker-compose -f $COMPOSE_FILE down"
echo ""

# Save startup info to log
{
    echo "4-Plex Investment Platform started at $(date)"
    echo "Services running on:"
    for service in "${services[@]}"; do
        echo "  - $service"
    done
    echo ""
    echo "Main dashboard: http://localhost:11061"
    echo "Integration API: http://localhost:11060"
} > $LOG_FILE

print_success "Startup completed! Log saved to $LOG_FILE"

# Open the dashboard in browser if available
if command -v xdg-open &> /dev/null; then
    print_status "Opening dashboard in browser..."
    xdg-open http://localhost:11061 2>/dev/null || true
elif command -v open &> /dev/null; then
    print_status "Opening dashboard in browser..."
    open http://localhost:11061 2>/dev/null || true
fi

echo -e "${PURPLE}🚀 4-Plex Investment Platform is now running!${NC}"