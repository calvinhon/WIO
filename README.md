For the email component, run ./startFlutter.sh which will build a Docker container with the Dockerfile. Make sure to run ollama serve, ollama pull mistral:instruct, and ollama pull nuextract before running functions related to LLM calls. 

For sms component, use command `adb devices` to get device_id. After that run `flutter run -d device_id` (from sms_reader_app).
