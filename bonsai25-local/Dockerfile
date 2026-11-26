FROM ghcr.io/ggml-org/llama.cpp:server-cuda@sha256:f8e7c336e3660804f6bc35a4147dbfdf1ddae9b7c3c50d412fab49b323e28fea
COPY downloads/llama-prism-b12232-f702476-bin-linux-cuda-12.8-x64.tar.gz /tmp/prism.tar.gz
RUN echo "5aeef1a6c543765a488920a771c4cde0931b95f4cb52dfa9aa3c7e0e106d329f  /tmp/prism.tar.gz" | sha256sum -c - \
    && mkdir /runtime \
    && tar -xzf /tmp/prism.tar.gz -C /runtime --strip-components=1 \
    && rm /tmp/prism.tar.gz
