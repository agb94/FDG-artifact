FROM nimmis/ubuntu:18.04

# disable interactive functions
ENV DEBIAN_FRONTEND noninteractive

# set default java environment variable
ENV JAVA_VERSION_MAJOR=8 \
    JAVA_VERSION_MINOR=111 \
    JAVA_HOME=/usr/lib/jvm/default-jvm \
    PATH=${PATH}:/usr/lib/jvm/default-jvm/bin/

ARG TARGETARCH

RUN add-apt-repository ppa:openjdk-r/ppa -y && \
    # update data from repositories
    apt-get update && \
    # upgrade OS
    apt-get -y dist-upgrade && \
    # Make info file about this build
    printf "Build of nimmis/java:openjdk-8-jdk, date: %s\n"  `date -u +"%Y-%m-%dT%H:%M:%SZ"` > /etc/BUILDS/java && \
    # install application
    apt-get install -y --no-install-recommends openjdk-8-jdk && \
    # fix default setting
    ln -s java-8-openjdk-${TARGETARCH}  /usr/lib/jvm/default-jvm && \
    # remove apt cache from image
    apt-get clean all

RUN java -version && \
    javac -version

# Install linux packages
RUN apt-get update
RUN apt-get -qq -y install git curl build-essential subversion perl wget unzip vim

RUN apt install -y python3-pip

RUN apt-get install bc

WORKDIR /root
COPY resources/vimrc .vimrc

# D4J Setup
COPY resources/d4j_install.sh d4j_install.sh
RUN chmod +x d4j_install.sh
RUN ./d4j_install.sh
ENV PATH="${PATH}:/root/defects4j/framework/bin"

ENV D4J_EXPR="/root/workspace"

# Evosuite Setup
COPY resources/evosuite-master-1.0.7-SNAPSHOT.jar evosuite-master-1.0.7-SNAPSHOT.jar
COPY resources/evosuite-config evosuite-config

ENV EVOSUITE="java -jar /root/evosuite-master-1.0.7-SNAPSHOT.jar"
ENV EVOSUITE_DEFAULT_CONFIG="/root/evosuite-config"

ENV D4J_EXPR_RESULTS="/root/results"

RUN python3.6 -m pip install tqdm tabulate
RUN python3.6 -m pip install numpy scipy pandas
RUN python3.6 -m pip install torch==1.9.0 --extra-index-url https://download.pytorch.org/whl/cpu
WORKDIR /root/workspace

ENV D4J_METADATA="$D4J_EXPR_RESULTS/metadata/"
ENV EVOSUITE_CONFIG="$D4J_EXPR_RESULTS/evosuite_config/"
ENV EVOSUITE_TEST="$D4J_EXPR_RESULTS/evosuite_test/"
ENV EVOSUITE_REPORT="$D4J_EXPR_RESULTS/evosuite_report/"
ENV EVOSUITE_COVERAGE="$D4J_EXPR_RESULTS/evosuite_coverage/"
ENV EVOSUITE_ORACLE="$D4J_EXPR_RESULTS/evosuite_oracles/"
