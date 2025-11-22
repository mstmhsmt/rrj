FROM codinuum/cca:base

LABEL maintainer="mstmhsmt"

WORKDIR /root

COPY cca /opt/cca/

RUN set -x && \
    cd /root && \
    apt-get update && \
    env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
            psmisc time parallel \
            locales locales-all nkf \
            maven pcregrep \
            python3-setuptools \
            python3-psutil \
            python3-matplotlib \
            python3-networkx \
            lv \
            jq \
            curl subversion && \
    pip3 install simplejson --break-system-packages

# For installing helper scripts

COPY python /root/python

RUN set -x && \
    cd /root/python && \
    python3 -m build && \
    pip3 install dist/rrj-*.tar.gz --break-system-packages && \
    cd /root && \
    rm -r python

# Cleanup

RUN set -x && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

CMD ["/bin/bash"]
