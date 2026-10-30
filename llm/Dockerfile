FROM ghcr.io/ggml-org/llama.cpp:server-b11946

COPY qwen3.5-2b-q5_k_m.gguf /models/model.gguf

EXPOSE 8080
CMD ["-m", "/models/model.gguf", \
     "--host", "0.0.0.0", "--port", "8080", \
     "-c", "8192", \
     "--jinja", \
     "--chat-template-kwargs", "{\"enable_thinking\": false}"]