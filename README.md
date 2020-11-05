# Ingest Earthquake IoT Data to Kafka (MSK)

This small solution allows you to create an MSK cluster with an EC2 instance configured as a Kafka Client.
It also contains a Python script that can be used to ingest data from the 
[openeew](https://registry.opendata.aws/grillo-openeew/) public data set to the running Kafka cluster.

**Requirements:**

- AWS account
- Admin IAM user to run CDK
- Local Python IDE with an environment running Python 3.6+
- AWS CLI and CDK CLI configured to run locally
- SSM Agent installed locally

**How to run it?**

1. Import this project into your local IDE.
2. Install the local dependencies (if not done already by your local IDE).

    ```
    @python3 -m pip install -r {PROJECT_DIRECTORY}/requirements.txt
    ```
   
3. Execute the stack as follows:
   
    ```
    bash {PROJECT_DIRECTORY}/cdk_deploy_to.sh --acount {YOUR_AWS_ACCOUNT} --region {YOUR_DESIRED_REGION}
    ```
   
4. Once the stack is deployed, get the instance ID of your client:
   
    ```
    aws ec2 describe-instances --filters Name=tag:Name,Values=msk-quickstart/msk_quickstart_instance Name=instance-state-name,Values=running --query "Reservations[].Instances[].InstanceId"
    ```
   
    Then, login to the client with SSM using the instance ID retrieved above:
    ```
    aws ssm start-session --target i-XXXXXXXXXXXXX
    sudo su -
    ```
5. Get the relevant connection strings from the Kafka cluster and add them to your environment.

    Get the Kafka Cluster ARN (substitute the region var for the region where you deployed this solution):
    ```
    REGION=$(curl -s http://169.254.169.254/latest/dynamic/instance-identity/document | jq .region -r)
    MSK_ARN=$(aws kafka list-clusters --region ${REGION} | jq -c '.ClusterInfoList[] | select(.ClusterName == "msk-quickstart") | .ClusterArn' | tr -d '"')
    ```
    Set your connection strings as env vars:
    ```
    ZK_HOSTS=$(aws kafka list-clusters --region us-east-1 | jq -c '.ClusterInfoList[] | select(.ClusterName == "msk-quickstart") | .ZookeeperConnectString')
    KAFKA_BROKERS=$(aws kafka --region $REGION get-bootstrap-brokers --cluster-arn $MSK_ARN | jq -c .BootstrapBrokerString)
    KAFKA_BROKERS_TLS=$(aws kafka --region $REGION get-bootstrap-brokers --cluster-arn $MSK_ARN | jq -c .BootstrapBrokerStringTls)
    ```
    If you want to set these environment variables as system variables:
    ```
    echo "export ZK_HOSTS=$ZK_HOSTS" | tee -a /etc/profile.d/kafka.sh
    echo "export KAFKA_BROKERS=$KAFKA_BROKERS" | tee -a /etc/profile.d/kafka.sh
    echo "export KAFKA_BROKERS_TLS=$KAFKA_BROKERS_TLS" | tee -a /etc/profile.d/kafka.sh
    ```
   
6. Create a Kafka topic to store the messages:

    ```
    KAFKA_TOPIC=openeew_mx_json
    kafka-topics.sh --create --zookeeper $ZK_HOSTS --replication-factor 2 --partitions 1 --topic $KAFKA_TOPIC
    ```

7. Unzip the code to run the message producer.
    
    ```
    mkdir ~/earthquake_loader/ && cd ~/earthquake_loader/ && unzip /earthquake_loader.zip
    ```

8. Install the dependencies for the ingestion script:

    ```
    python3 -m pip install -r ~/earthquake_loader/requirements.txt
    ```

9. Run the loader script. This sample run will ingest around 200K JSON serialized messages every 10 minutes.
    
   ```
    python3 ~/earthquake_loader/main.py \
    --kafka-brokers $KAFKA_BROKERS \
    --kafka-topic $KAFKA_TOPIC \
    --country "mx" \
    --periods 6 \
    --frequency-min 10 \
    --start-timestamp-utc "2018-01-01 00:00:00" \
    --parse-json-records
    ```

    *Options*:
    
    `@country: str` - Country code where the sensor data will be collected. 
    Options can be Mexico `mx` or Chile `cl`.
    
    `@periods: int` - Number of time periods to ingest.
    
    `@frequency_min: int` - Length of the time periods in minutes.
    
    `@start_timestamp_utc: str` - Length of the time periods in minutes.
    
    `@parse_json_records: bool` - Pass this flag serialize the messages as JSON. Otherwise they will be sent as bytes.
