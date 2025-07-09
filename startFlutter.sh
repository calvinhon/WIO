#!/bin/bash

DOCKERFILE_DIR=.
DOCKERFILE_HASH_FILE="$DOCKERFILE_DIR/.dockerfile_hash"
IMAGE_NAME="flutter-dev"
PROJECT_DIR="$PWD"
APK_PATH="flutter_app_new/build/app/outputs/flutter-apk/app-release.apk"

# Only try to start Docker Desktop if on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
  if ! pgrep -x "Docker" > /dev/null; then
    echo "Starting Docker Desktop..."
    open -a Docker
    while ! docker system info > /dev/null 2>&1; do
      sleep 1
      echo "Waiting for Docker daemon..."
    done
  fi
else
  # On Linux or WSL, just check that Docker is running
  if ! docker system info > /dev/null 2>&1; then
    echo "Docker does not seem to be running. Please start Docker Desktop manually."
    exit 1
  fi
fi

# Compute current Dockerfile hash
CURRENT_HASH=$(shasum "$DOCKERFILE_DIR/Dockerfile" | awk '{ print $1 }')
IMAGE_EXISTS=$(docker image inspect $IMAGE_NAME > /dev/null 2>&1 && echo yes || echo no)

# Rebuild if Dockerfile changed or image doesn't exist
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

echo "Building Flutter APK in Docker..."
docker run --rm \
  -v "$PROJECT_DIR":/src -w /src \
  $IMAGE_NAME \
  bash -c "flutter build apk --release"

if [ ! -f "$APK_PATH" ]; then
  echo "APK build failed or APK not found at $APK_PATH"
  exit 1
fi

echo "APK built successfully at $APK_PATH"

# Try to install on connected device using host ADB
if command -v adb >/dev/null 2>&1; then
  DEVICE=$(adb devices | grep -w "device" | awk 'NR==1 {print $1}')
  if [ -n "$DEVICE" ]; then
    echo "Device detected: $DEVICE"
    adb install -r "$APK_PATH"
  else
    echo "No Android device detected by ADB. Please check USB/debugging."
  fi
else
  echo "ADB not found on host. Please install Android platform tools to enable device installation."
fi

# Always open an interactive shell in the container with project mounted
echo "Opening interactive shell inside the container..."
docker run --rm -it \
  -v "$PROJECT_DIR":/src -w /src \
  $IMAGE_NAME \
  bash
