"""A Python Pulumi program to provision a MongoDB Atlas cluster with vector search capabilities."""

# Standard library imports
import json

# Third-party imports
import pulumi  # Pulumi SDK for infrastructure as code
from pulumi import ResourceOptions
import pulumi_mongodbatlas as mongodbatlas  # Pulumi MongoDB Atlas provider
import pulumi_aws as aws  # Pulumi AWS provider

# Local application imports
from mongodb_collection import MongoDBCollection  # Custom Pulumi resource
from config import (
    MONGODB_ATLAS_PROJECT_ID,
    IP_ADDRESS,
    VECTOR_DATABASE,
    VECTOR_COLLECTION,
    VECTOR_USER,
    VECTOR_PASSWORD,
)

# Create a *free* MongoDB Atlas cluster running on Google Cloud
vector_cluster = mongodbatlas.AdvancedCluster(
    "vector-cluster",
    project_id=MONGODB_ATLAS_PROJECT_ID,
    name="vector-cluster",
    cluster_type="REPLICASET",
    replication_specs=[
        {
            "zone_name": "iac managed",
            "region_configs": [
                {
                    "electable_specs": {
                        "instance_size": "M0",  # Free tier instance size
                    },
                    "provider_name": "TENANT",
                    "backing_provider_name": "GCP",
                    "region_name": "CENTRAL_US",
                    "priority": 7,
                }
            ],
        }
    ],
)

# Extract the connection string for use in the collection
vector_uri = vector_cluster.connection_strings.apply(lambda c: c[0].standard_srv)

# Create a database user for the cluster with specific privileges
vector_user = mongodbatlas.DatabaseUser(
    "vector-user",
    project_id=MONGODB_ATLAS_PROJECT_ID,
    username=VECTOR_USER,
    password=VECTOR_PASSWORD,
    auth_database_name="admin",
    roles=[
        {
            "role_name": "readWrite",
            "database_name": VECTOR_DATABASE,
            "collection_name": VECTOR_COLLECTION,
        }
    ],
    scopes=[{"name": vector_cluster.name, "type": "CLUSTER"}],
    opts=ResourceOptions(depends_on=[vector_cluster]),
)

# Adds the current IP to the access list of the project
my_current_ip = mongodbatlas.ProjectIpAccessList(
    "my-current-ip",
    project_id=MONGODB_ATLAS_PROJECT_ID,
    ip_address=IP_ADDRESS,
    comment="Enable local cluster access.",
    opts=ResourceOptions(additional_secret_outputs=["ip_address"]),
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
    },
    opts=ResourceOptions(depends_on=[vector_user, my_current_ip]),
)

# Define the search index fields
vector_search_index_fields = [
    {
        "type": "vector",
        "path": "embedding",  # Field for vector embeddings
        "numDimensions": 768,  # Adjust this to match your embedding dimensions
        "similarity": "dotProduct",  # Similarity metric (e.g., cosine, dotProduct)
        "quantization": "scalar",  # Quantization type
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
    opts=ResourceOptions(depends_on=[vector_collection]),
)

# Export a full MongoDB URI with credentials and database
full_mongodb_uri = pulumi.Output.all(
    VECTOR_USER, VECTOR_PASSWORD, vector_uri, VECTOR_DATABASE
).apply(
    lambda args: f"mongodb+srv://{args[0]}:{args[1]}@{args[2].split('://')[1]}/{args[3]}?retryWrites=true&w=majority"
)
pulumi.export("MONGODB_URI", pulumi.Output.secret(full_mongodb_uri))

# Create IAM role for Lambda execution
lambda_role = aws.iam.Role(
    "lambda-role",
    assume_role_policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Effect": "Allow",
                }
            ],
        }
    ),
)

# Attach basic Lambda execution policy
lambda_role_policy = aws.iam.RolePolicyAttachment(
    "lambda-role-policy",
    role=lambda_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
)

# Create Lambda function with the Flask app
lambda_function = aws.lambda_.Function(
    "vector-search-lambda",
    role=lambda_role.arn,
    runtime="python3.11",
    handler="lambda_handler.handler",
    code=pulumi.AssetArchive({".": pulumi.FileArchive("./app")}),
    timeout=30,
    memory_size=2048,
    environment={"variables": {"MONGODB_URI": full_mongodb_uri}},
    opts=ResourceOptions(depends_on=[lambda_role_policy, vector_search_index]),
)

# Export the Lambda function ARN
pulumi.export("lambda_function_arn", lambda_function.arn)
pulumi.export("lambda_function_name", lambda_function.name)

# Create API Gateway HTTP API
api = aws.apigatewayv2.Api(
    "vector-search-api",
    protocol_type="HTTP",
    description="API Gateway for Vector Search Lambda",
)

# Create Lambda permission for API Gateway to invoke the function
lambda_permission = aws.lambda_.Permission(
    "api-lambda-permission",
    action="lambda:InvokeFunction",
    function=lambda_function.name,
    principal="apigateway.amazonaws.com",
    source_arn=api.execution_arn.apply(lambda arn: f"{arn}/*/*"),
)

# Create API Gateway integration with Lambda
integration = aws.apigatewayv2.Integration(
    "lambda-integration",
    api_id=api.id,
    integration_type="AWS_PROXY",
    integration_uri=lambda_function.arn,
    integration_method="POST",
    payload_format_version="2.0",
)

# Create a default route that forwards all requests to Lambda
route = aws.apigatewayv2.Route(
    "default-route",
    api_id=api.id,
    route_key="$default",
    target=integration.id.apply(lambda id: f"integrations/{id}"),
)

# Create a stage for the API
stage = aws.apigatewayv2.Stage(
    "api-stage", api_id=api.id, name="$default", auto_deploy=True
)

# Export the API endpoint URL
pulumi.export("api_endpoint", api.api_endpoint)
