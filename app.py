import os.path

import aws_cdk.aws_msk as msk
from aws_cdk.aws_s3_assets import Asset
from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam,
    core
)

dirname = os.path.dirname(__file__)
prefix = "msk_quickstart"


class MSKQuickstartStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # VPC
        vpc = ec2.Vpc(
            self, f"{prefix}_vpc",
            nat_gateways=1,
            enable_dns_hostnames=True,
            enable_dns_support=True,
            max_azs=2,
            subnet_configuration=[
                ec2.SubnetConfiguration(name="public", subnet_type=ec2.SubnetType.PUBLIC),
                ec2.SubnetConfiguration(name="privat", subnet_type=ec2.SubnetType.PRIVATE)
            ]
        )

        # MSK Cluster Security Group
        sg_msk = ec2.SecurityGroup(
            self, f"{prefix}_sg",
            vpc=vpc,
            allow_all_outbound=True,
            security_group_name=f"{prefix}_sg_msk"
        )
        for subnet in vpc.public_subnets:
            sg_msk.add_ingress_rule(ec2.Peer.ipv4(subnet.ipv4_cidr_block), ec2.Port.tcp(2181), "Zookeeper Plaintext")
            sg_msk.add_ingress_rule(ec2.Peer.ipv4(subnet.ipv4_cidr_block), ec2.Port.tcp(2182), "Zookeeper TLS")
            sg_msk.add_ingress_rule(ec2.Peer.ipv4(subnet.ipv4_cidr_block), ec2.Port.tcp(9092), "Broker Plaintext")
            sg_msk.add_ingress_rule(ec2.Peer.ipv4(subnet.ipv4_cidr_block), ec2.Port.tcp(9094), "Zookeeper Plaintext")
        for subnet in vpc.private_subnets:
            sg_msk.add_ingress_rule(ec2.Peer.ipv4(subnet.ipv4_cidr_block), ec2.Port.all_traffic(), "All private traffic")

        # MSK Cluster
        msk.CfnCluster(
            self, f"{prefix}_kafka_cluster",
            cluster_name="msk-quickstart",
            number_of_broker_nodes=len(vpc.private_subnets),
            kafka_version="2.6.0",
            encryption_info=msk.CfnCluster.EncryptionInfoProperty(
                encryption_in_transit=msk.CfnCluster.EncryptionInTransitProperty(
                    client_broker="TLS_PLAINTEXT"
                )
            ),
            broker_node_group_info=msk.CfnCluster.BrokerNodeGroupInfoProperty(
                instance_type="kafka.m5.large",
                client_subnets=[subnet.subnet_id for subnet in vpc.private_subnets],
                security_groups=[sg_msk.security_group_id],
                storage_info=msk.CfnCluster.StorageInfoProperty(
                    ebs_storage_info=msk.CfnCluster.EBSStorageInfoProperty(volume_size=200)
                )
            )
        )

        # EC2 Client AMI
        amazon_linux = ec2.MachineImage.latest_amazon_linux(
            generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
            edition=ec2.AmazonLinuxEdition.STANDARD,
            virtualization=ec2.AmazonLinuxVirt.HVM,
            storage=ec2.AmazonLinuxStorage.GENERAL_PURPOSE
            )

        # Instance Role and SSM Managed Policy
        role = iam.Role(
            self,
            f"{prefix}_ssm_role",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com")
        )
        role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonEC2RoleforSSM"))
        role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonMSKReadOnlyAccess"))

        # EC2 Client Instance
        instance = ec2.Instance(
            self, f"{prefix}_instance",
            instance_type=ec2.InstanceType("m5.large"),
            machine_image=amazon_linux,
            vpc=vpc,
            role=role,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)
        )

        # Bootstrap script in S3 as Asset
        asset_bootstrap = Asset(self, f"{prefix}_bootstrap", path=os.path.join(dirname, "configure.sh"))
        local_bootstrap_path = instance.user_data.add_s3_download_command(
            bucket=asset_bootstrap.bucket,
            bucket_key=asset_bootstrap.s3_object_key
        )

        # Loader project in S3 Asset
        asset_loader = Asset(self, f"{prefix}_loader", path=os.path.join(dirname, "earthquake_loader"))
        instance.user_data.add_s3_download_command(
            bucket=asset_loader.bucket,
            bucket_key=asset_loader.s3_object_key,
            local_file="earthquake_loader.zip"
        )

        # Userdata executes bootstrap script from S3
        instance.user_data.add_execute_file_command(file_path=local_bootstrap_path)

        # Grant read permissions to assets
        asset_bootstrap.grant_read(instance.role)
        asset_loader.grant_read(instance.role)


env = core.Environment(account=os.environ["CDK_DEFAULT_ACCOUNT"], region=os.environ["CDK_DEFAULT_REGION"])
app = core.App()
MSKQuickstartStack(app, "msk-quickstart", env=env)

app.synth()
