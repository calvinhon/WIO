FROM cirrusci/flutter:stable

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies including Python, pip, and Tesseract
RUN apt-get update && apt-get install -y \
    wget unzip openjdk-17-jdk \
    sudo android-tools-adb \
    python3 python3-pip \
    tesseract-ocr \
    usbutils \
    libgl1 libglib2.0-0 \
    curl gnupg \
    --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Ollama inside container
RUN curl -fsSL https://ollama.com/install.sh | sh

# Preload the model (start server temporarily and pull the model)
RUN ollama serve & \
    for i in $(seq 1 20); do \
      curl --fail http://127.0.0.1:11434/health && break || sleep 1; \
    done && \
    ollama pull llama2:7b && \
    pkill ollama

# Create a shell entrypoint BEFORE switching to non-root user
RUN echo '#!/bin/bash\nexec bash --rcfile <(echo "export PATH=$PATH")' > /usr/local/bin/start && chmod +x /usr/local/bin/start

# Create non-root user and set working directory
RUN useradd -ms /bin/bash developer

# Set ownership of Flutter SDK and pub cache (critical for Flutter development)
RUN chown -R developer:developer /sdks/flutter
RUN chown -R developer:developer /opt/flutter/.pub-cache || true

# Set a password and sudo access
RUN echo "developer:pass" | chpasswd
RUN usermod -aG sudo developer

# Change permissions on the Android SDK
RUN chmod -R a+rwX /opt/android-sdk-linux \
 && yes | sdkmanager "build-tools;30.0.3" "platform-tools" "platforms;android-33"

# Switch to non-root user for final image
USER developer
WORKDIR /home/developer

# Copy Python dependencies and install them
COPY --chown=developer:developer flutter_app_new/python/requirements.txt ./python/requirements.txt
RUN pip3 install --user -r ./python/requirements.txt

# Entry point
ENTRYPOINT ["/usr/local/bin/start"]
CMD ["bash"]
