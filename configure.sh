#!/bin/bash
# This script bootstraps the installation of the necessary libraries
# to use this instance as a Kafka Client machine
set -e

function install_system_packages() {
    /usr/bin/yum -y install java-1.8.0 python3 python3-devel gcc jq git
}

function install_python_modules() {
  /usr/bin/python3 -m pip install --upgrade pip
}

function install_kafka_client_libs() {
    (cd /opt && /usr/bin/wget https://archive.apache.org/dist/kafka/2.2.1/kafka_2.12-2.2.1.tgz)
    (cd /opt && /usr/bin/tar -xzf kafka_2.12-2.2.1.tgz)
    /usr/bin/echo "export KAFKA_HOME=/opt/kafka_2.12-2.2.1" | /usr/bin/tee /etc/profile.d/kafka.sh
    /usr/bin/echo "export PATH=\$PATH:\$KAFKA_HOME/bin" | /usr/bin/tee -a /etc/profile.d/kafka.sh
}

install_system_packages
install_python_modules
install_kafka_client_libs
echo "Bootstrapping complete."