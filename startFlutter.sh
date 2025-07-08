#!/bin/bash

DOCKERFILE_DIR=~/Desktop/WIO
DOCKERFILE_HASH_FILE="$DOCKERFILE_DIR/.dockerfile_hash"
IMAGE_NAME="flutter-dev"

# Start Docker Desktop if needed
if ! pgrep -x "Docker" > /dev/null; then
  echo "Starting Docker Desktop..."
  open -a Docker
  while ! docker system info > /dev/null 2>&1; do
    sleep 1
    echo "Waiting for Docker daemon..."
  done
fi

# Compute current Dockerfile hash
CURRENT_HASH=$(shasum "$DOCKERFILE_DIR/Dockerfile" | awk '{ print $1 }')

# Check if image exists
IMAGE_EXISTS=$(docker image inspect $IMAGE_NAME > /dev/null 2>&1 && echo yes || echo no)

# Rebuild if Dockerfile changed or image doesn’t exist
if [ "$IMAGE_EXISTS" = "no" ] || [ ! -f "$DOCKERFILE_HASH_FILE" ] || [ "$CURRENT_HASH" != "$(cat "$DOCKERFILE_HASH_FILE")" ]; then
  echo "Dockerfile changed or image missing. Rebuilding $IMAGE_NAME..."
  docker build -t $IMAGE_NAME "$DOCKERFILE_DIR"
  if [ $? -ne 0 ]; then
    echo "Docker build failed. Exiting."
    exit 1
  fi
  echo "$CURRENT_HASH" > "$DOCKERFILE_HASH_FILE"
else
  echo "No changes in Dockerfile. Using cached image."
fi

# Run the container
DEVICE_PATH="/dev/bus/usb/001/005"  # Change as appropriate

if [ -e "$DEVICE_PATH" ]; then
  echo "Device found, running container with device access."
  docker run -it --rm --privileged --device $DEVICE_PATH \
    -v "$PWD":/src -w /src flutter-dev \
    bash --rcfile <(echo 'export PS1="\[\e[1;34m\]Docker \[\e[0m\] \$ "')
else
  echo "No device found, running container without device access."
  docker run -it --rm \
    -v "$PWD":/src -w /src flutter-dev \
    bash --rcfile <(echo 'export PS1="\[\e[1;34m\]Docker \[\e[0m\] \$ "')
fi