#!/bin/bash

DOCKERFILE_DIR=.
DOCKERFILE_HASH_FILE="$DOCKERFILE_DIR/.dockerfile_hash"
IMAGE_NAME="flutter-dev"
PROJECT_DIR="$PWD"
DEFAULT_APK_PATH="email/build/app/outputs/flutter-apk/app-release.apk"

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
  if ! docker system info > /dev/null 2>&1; then
    echo "Docker is not running. Start Docker and try again."
    exit 1
  fi
fi

# Compute current Dockerfile hash
CURRENT_HASH=$(shasum "$DOCKERFILE_DIR/Dockerfile" | awk '{ print $1 }')
IMAGE_EXISTS=$(docker image inspect $IMAGE_NAME > /dev/null 2>&1 && echo yes || echo no)

# Rebuild image if needed
if [ "$IMAGE_EXISTS" = "no" ] || [ ! -f "$DOCKERFILE_HASH_FILE" ] || [ "$CURRENT_HASH" != "$(cat "$DOCKERFILE_HASH_FILE")" ]; then
  echo "Rebuilding Docker image: $IMAGE_NAME..."
  docker build -t $IMAGE_NAME "$DOCKERFILE_DIR" || { echo "Build failed."; exit 1; }
  echo "$CURRENT_HASH" > "$DOCKERFILE_HASH_FILE"
else
  echo "Using cached Docker image."
fi

echo "🔧 Building Flutter APK inside Docker..."
docker run --rm -v "$PROJECT_DIR":/src -w /src "$IMAGE_NAME" bash -c "flutter build apk --release || (echo '❌ Flutter build failed' && exit 1)"

# Check for the APK file
if [ -f "$DEFAULT_APK_PATH" ]; then
  APK_PATH="$DEFAULT_APK_PATH"
else
  echo "❌ APK not found at expected location. Searching..."
  APK_PATH=$(find "$PROJECT_DIR/build" -type f -name "*.apk" | head -n 1)
  if [ -z "$APK_PATH" ]; then
    echo "❌ APK not found after build. Something went wrong."
    exit 1
  else
    echo "✅ APK found at: $APK_PATH"
  fi
fi

# Try to install via ADB if available
if command -v adb >/dev/null 2>&1; then
  DEVICE=$(adb devices | awk '/device$/{print $1; exit}')
  if [ -n "$DEVICE" ]; then
    echo "📱 Installing APK on device $DEVICE..."
    adb install -r "$APK_PATH"
  else
    echo "⚠️ No Android device connected. Please enable USB debugging and try again."
  fi
else
  echo "⚠️ ADB not found. Install Android platform tools to use device installation."
fi

# Always open an interactive shell in the container with project mounted
echo "Opening interactive shell inside the container..."
docker run --rm -it \
  -v "$PROJECT_DIR":/src -w /src \
  $IMAGE_NAME \
  bash
