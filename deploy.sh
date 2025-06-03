#!/bin/bash

# Exit on error
set -e

# Configuration
IMAGE_NAME="finance-advisor-agent"
IMAGE_TAG="latest"
CONTAINER_NAME="finance-advisor-agent"
PORT=5000

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building Docker image...${NC}"
docker build -t ${IMAGE_NAME}:${IMAGE_TAG} ./finance-advisor-agent

echo -e "${GREEN}Checking if container is running...${NC}"
if [ "$(docker ps -q -f name=${CONTAINER_NAME})" ]; then
    echo -e "${GREEN}Stopping existing container...${NC}"
    docker stop ${CONTAINER_NAME}
    docker rm ${CONTAINER_NAME}
fi

echo -e "${GREEN}Starting new container...${NC}"
docker run -d \
    --name ${CONTAINER_NAME} \
    -p ${PORT}:${PORT} \
    -e PORT=${PORT} \
    ${IMAGE_NAME}:${IMAGE_TAG}

echo -e "${GREEN}Container is running!${NC}"
echo -e "You can access the application at http://localhost:${PORT}"
echo -e "To view logs, run: docker logs ${CONTAINER_NAME}" 