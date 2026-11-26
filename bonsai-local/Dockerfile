FROM ghcr.io/ggml-org/llama.cpp:server-cuda@sha256:f8e7c336e3660804f6bc35a4147dbfdf1ddae9b7c3c50d412fab49b323e28fea
COPY downloads/llama-prism-b10709-9a9394a-bin-linux-cuda-12.8-x64.tar.gz /tmp/prism.tar.gz
RUN echo "8aec67eb023b251712c7e6490f367b5671bf587eced1436a9b85f4a90c3b7d3d  /tmp/prism.tar.gz" | sha256sum -c - \
    && mkdir /runtime \
    && tar -xzf /tmp/prism.tar.gz -C /runtime --strip-components=1 \
    && rm /tmp/prism.tar.gz
