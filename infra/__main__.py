"""A Python Pulumi program to provision a MongoDB Atlas cluster with vector search capabilities and AWS Lambda."""

# Standard library imports
import json

# Third-party imports
import pulumi  # Pulumi SDK for infrastructure as code
from pulumi import ResourceOptions
import pulumi_aws as aws
import pulumi_mongodbatlas as mongodbatlas  # Pulumi MongoDB Atlas provider
import pulumi_docker as docker

# Local application imports
from mongodb_collection import MongoDBCollection  # Custom Pulumi resource
from config import MONGODB_ATLAS_PROJECT_ID, IP_ADDRESS, VECTOR_DATABASE, VECTOR_COLLECTION, VECTOR_USER, VECTOR_PASSWORD

# MongoDB resources
# Create a *free* MongoDB Atlas cluster running on Google Cloud
vector_cluster = mongodbatlas.AdvancedCluster(
    "vector-cluster",
    project_id=MONGODB_ATLAS_PROJECT_ID,
    name="vector-cluster",
    cluster_type="REPLICASET",
    replication_specs=[{
        "zone_name": "iac managed",
        "region_configs": [{
            "electable_specs": {
                "instance_size" : "M0",  # Free tier instance size
            },
            "provider_name":"TENANT",
            "backing_provider_name":"GCP",
            "region_name":"CENTRAL_US",
            "priority": 7,
        }],
    }],
)

# Extract the connection string for use in the collection
vector_uri = vector_cluster.connection_strings.apply(lambda c: c[0].standard_srv )

# Create a database user for the cluster with specific privileges
vector_user = mongodbatlas.DatabaseUser(
    "vector-user",
    project_id=MONGODB_ATLAS_PROJECT_ID,
    username=VECTOR_USER,
    password=VECTOR_PASSWORD,
    auth_database_name="admin",
    roles=[{
            "role_name" : "readWrite",
            "database_name" : VECTOR_DATABASE,
            "collection_name" : VECTOR_COLLECTION
    }],
    scopes=[{
            "name" : vector_cluster.name,
            "type" : "CLUSTER"}
    ],
    opts=ResourceOptions(depends_on=[vector_cluster])
)

# Adds the current IP to the access list of the project
my_current_ip = mongodbatlas.ProjectIpAccessList(
    "my-current-ip",
    project_id=MONGODB_ATLAS_PROJECT_ID,
    ip_address=IP_ADDRESS,
    comment = "Enable local cluster access.",
    opts=ResourceOptions(additional_secret_outputs=['ip_address'])
)

# Allow Lambda access from anywhere (Lambda IPs are not static)
lambda_access = mongodbatlas.ProjectIpAccessList(
    "lambda-access",
    project_id=MONGODB_ATLAS_PROJECT_ID,
    cidr_block="0.0.0.0/0",
    comment="Allow Lambda function access"
)

# Creates a MongoDB collection for the Vector Search Index
vector_username = vector_user.username.apply(lambda u: u)
vector_password = vector_user.password.apply(lambda p: p)
vector_collection = MongoDBCollection(
    "vector-collection",
    props={
        "user": vector_username,
        "pwd": vector_password,
        "uri": vector_uri,
        "db": VECTOR_DATABASE,
        "coll": VECTOR_COLLECTION,
        "data_file": "../app/data.json"  # Load sample data during deployment
    },
    opts=ResourceOptions(depends_on=[vector_user, my_current_ip])
    )

# Define the search index fields
vector_search_index_fields = [
    {
        "type": "vector",
        "path": "embedding",        # Field for vector embeddings
        "numDimensions": 768,       # Adjust this to match your embedding dimensions
        "similarity": "dotProduct", # Similarity metric (e.g., cosine, dotProduct)
        "quantization": "scalar"    # Quantization type
    }
]

# Ensure collection is created before proceeding
vector_search_index = mongodbatlas.SearchIndex(
    "vector-index",
    project_id=MONGODB_ATLAS_PROJECT_ID,
    name="vector-index",
    cluster_name=vector_cluster.name,
    database=VECTOR_DATABASE,
    collection_name=VECTOR_COLLECTION,
    type="vectorSearch",
    fields=json.dumps(vector_search_index_fields),
    wait_for_index_build_completion=True,
    opts=ResourceOptions(depends_on=[vector_collection])
)

# Export a full MongoDB URI with credentials and database
full_mongodb_uri = pulumi.Output.all(VECTOR_USER, VECTOR_PASSWORD, vector_uri, VECTOR_DATABASE).apply(
    lambda args: f"mongodb+srv://{args[0]}:{args[1]}@{args[2].split('://')[1]}/{args[3]}?retryWrites=true&w=majority"
)
pulumi.export("MONGODB_URI", pulumi.Output.secret(full_mongodb_uri))

# ECR and Lambda Container Infrastructure

# Create ECR repository
ecr_repository = aws.ecr.Repository(
    "wonders-ecr-repo",
    name="wonders-of-the-world",
    image_scanning_configuration={
        "scan_on_push": True
    },
    force_delete=True
)

# Get ECR authorization token
def get_registry_info(registry_id):
    """Get ECR registry credentials"""
    return aws.ecr.get_authorization_token_output(registry_id=registry_id)

auth_token = get_registry_info(ecr_repository.registry_id)

# Build and push Docker image to ECR
image = docker.Image(
    "wonders-docker-image",
    build=docker.DockerBuildArgs(
        context="..",  # Build from parent directory
        dockerfile="../Dockerfile",
        platform="linux/amd64"
    ),
    image_name=ecr_repository.repository_url,
    registry=docker.RegistryArgs(
        server=ecr_repository.repository_url,
        username=auth_token.user_name,
        password=auth_token.password
    )
)

# Create IAM role for Lambda
lambda_role = aws.iam.Role(
    "wonders-lambda-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Effect": "Allow",
        }]
    })
)

# Attach basic Lambda execution policy
lambda_policy_attachment = aws.iam.RolePolicyAttachment(
    "wonders-lambda-policy",
    role=lambda_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
)

# Create Lambda function from container image
lambda_function = aws.lambda_.Function(
    "wonders-lambda",
    name="wonders-of-the-world",
    package_type="Image",
    image_uri=image.repo_digest,
    role=lambda_role.arn,
    timeout=300,  # 5 minutes for cold start with ML models
    memory_size=3008,  # Increased memory for ML models
    ephemeral_storage={
        "size": 2048  # 2GB ephemeral storage (max for /tmp)
    },
    environment={
        "variables": {
            "MONGODB_URI": full_mongodb_uri
        }
    },
    opts=ResourceOptions(depends_on=[lambda_policy_attachment, vector_search_index])
)

# Create Lambda Function URL
function_url = aws.lambda_.FunctionUrl(
    "wonders-function-url",
    function_name=lambda_function.name,
    authorization_type="NONE"
)

# Export outputs
pulumi.export("ecr_repository_url", ecr_repository.repository_url)
pulumi.export("function_url", function_url.function_url)
pulumi.export("lambda_function_name", lambda_function.name)
