FROM codinuum/cca:devel

MAINTAINER mstmhsmt

WORKDIR /root

COPY cca /opt/cca/

RUN set -x && \
    cd /root && \
    apt-get update && \
    env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
            psmisc time parallel \
            locales locales-all nkf \
            maven pcregrep \
            python3-distutils \
            python3-psutil \
            python3-matplotlib \
            python3-networkx \
            lv \
            jq \
            curl subversion && \
    pip3 install simplejson

# For installing helper scripts

COPY python /root/python

RUN set -x && \
    cd /root/python && \
    python3 -m build && \
    pip3 install dist/rrj-*.tar.gz && \
    cd /root && \
    rm -r python

# Cleanup

RUN set -x && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

CMD ["/bin/bash"]
