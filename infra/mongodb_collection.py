"""
Pulumi Custom Resource for MongoDB Collections

This module defines a Pulumi dynamic resource for managing MongoDB collections.
It enables the creation of collections in a MongoDB database and optionally
loads initial data with embeddings.

For more details on Pulumi dynamic providers, visit:
https://www.pulumi.com/docs/iac/concepts/resources/dynamic-providers/
"""

# Standard library imports
import json
import logging
import time
from typing import Optional, Dict

# Third-party imports
from pulumi.dynamic import Resource, ResourceProvider, CreateResult
from pulumi import ResourceOptions  # Pulumi core resource import
from pymongo import MongoClient, errors  # MongoDB connection imports

class MongoDBCollectionProvider(ResourceProvider):
    """
    A Pulumi dynamic resource provider for managing MongoDB collections.

    This provider handles the creation of collections in a MongoDB database. It
    includes retry logic for authentication failures to ensure that the connection
    attempt is robust even if authentication errors occur temporarily.

    The resource provider supports basic MongoDB collection creation operations.
    """

    def __connect_with_retry(self,
                             props: Dict[str, str],
                             max_retries=5,
                             retry_delay=10) -> MongoClient:
        """
        Attempts to connect to MongoDB with retry logic for authentication errors.

        This method retries the connection if an authentication error occurs (e.g.,
        incorrect credentials). It will attempt a maximum number of retries, with
        a delay between each attempt.

        Args:
            props (Dict[str, str]): MongoDB connection details
            max_retries (int): Maximum number of retry attempts for authentication errors.
            retry_delay (int): Delay between retry attempts, in seconds.

        Returns:
            MongoClient: A MongoDB client instance.

        Raises:
            Exception: If unable to authenticate after multiple retries,
            or if another error occurs during connection.
        """
        attempt = 0
        ten_seconds = 10000  # Timeout values in milliseconds
        while attempt < max_retries:
            try:
                # Attempt to create a MongoClient instance
                client = MongoClient(
                    props.get("uri"),
                    username=props.get("user"),
                    password=props.get("pwd"),
                    authSource="admin",  # Explicitly set authentication database
                    # authMechanism="SCRAM-SHA-256",
                    maxPoolSize=10,
                    minPoolSize=1,
                    timeoutMS=ten_seconds,
                    socketTimeoutMS=ten_seconds,
                    appname="iac-demo",
                    connect=False,
                )
                time.sleep(retry_delay)
                # Test the connection by issuing a ping command
                client.admin.command('ping')
                # print(f"Ping result: {client.admin.command('ping')}")
                return client
            except errors.OperationFailure as e:
                # Handle authentication failure
                if "bad auth" in str(e):
                    attempt += 1
                    time.sleep(retry_delay)
                else:
                    print(f"MongoDB operation error: {str(e)}")  # Suppress traceback
            except Exception as e:
                print(f"MongoDB connection error: {str(e)}")  # Suppress tracebac
        print(f"Failed to authenticate after {max_retries} attempts.")
        return None
        # If authentication fails after max_retries, raise an exception
        # raise Exception(f"Failed to authenticate after {max_retries} attempts.")

    def __load_data_with_embeddings(self, client: MongoClient, db_name: str,
                                     collection_name: str, data_file: str) -> int:
        """
        Loads data from a JSON file and generates embeddings for each document.

        Args:
            client: MongoDB client
            db_name: Database name
            collection_name: Collection name
            data_file: Path to JSON file with data

        Returns:
            Number of documents inserted
        """
        try:
            # Import here to avoid dependency issues during infrastructure deployment
            from sentence_transformers import SentenceTransformer

            # Load the embedding model
            print("Loading embedding model...")
            model = SentenceTransformer('nomic-ai/nomic-embed-text-v1', trust_remote_code=True)

            # Load data from file
            print(f"Loading data from {data_file}...")
            with open(data_file, 'r') as f:
                data = json.load(f)

            # Generate embeddings and prepare documents
            print(f"Generating embeddings for {len(data)} documents...")
            documents = []
            for item in data:
                embedding = model.encode(item['text']).tolist()
                documents.append({
                    '_id': item['_id'],
                    'text': item['text'],
                    'embedding': embedding
                })

            # Insert documents
            collection = client[db_name][collection_name]
            collection.insert_many(documents)
            print(f"Successfully loaded {len(documents)} documents with embeddings")

            return len(documents)
        except Exception as e:
            print(f"Error loading data: {str(e)}")
            raise

    def create(self, props: Dict[str, str]) -> CreateResult:
        """
        Creates a MongoDB collection and optionally loads initial data.

        This method connects to MongoDB, creates the specified collection, and
        optionally loads data from a JSON file with generated embeddings.

        Args:
            props (Dict[str, str]): A dictionary containing MongoDB connection details
                                    (URI, username, password, database name,
                                    collection name, and optional data_file path).

        Returns:
            CreateResult: A Pulumi CreateResult object containing the collection details.

        Raises:
            ValueError: If the database name or collection name is missing from the props.
            RuntimeError: If authentication fails, or
            if any error occurs during collection creation.
        """
        # Set up the logger for PyMongo
        logging.basicConfig(level=logging.ERROR)  # Set default logging level
        # Obtain the logger used by PyMongo and set the desired level.
        logger = logging.getLogger('pymongo')
        logger.setLevel(logging.ERROR)

        client = None
        try:
            db_name = props.get("db")
            collection_name = props.get("coll")
            data_file = props.get("data_file")  # Optional data file path

            # Validate that both db and collection names are provided
            if not db_name or not collection_name:
                raise ValueError("Database name and collection name must be provided.")

            # Establish a connection to MongoDB with retries
            client = self.__connect_with_retry(props)
            if not client:
                raise RuntimeError("Failed to create collection")

            # Create the collection using the MongoDB command
            try:
                client[db_name].command("create", collection_name)
                print(f"Created collection {db_name}.{collection_name}")
            except errors.OperationFailure as err:
                if "already exists" in str(err):
                    print(f"Collection {db_name}.{collection_name} already exists")
                else:
                    raise

            # Load data if data_file is provided
            if data_file:
                print(f"Loading data from {data_file}...")
                count = self.__load_data_with_embeddings(client, db_name, collection_name, data_file)
                props["documents_loaded"] = str(count)

            # Return a successful result with the created collection details
            return CreateResult(id_=f"{db_name}.{collection_name}", outs=props)

        except errors.OperationFailure as err:
            # Handle error when collection already exists
            if "already exists" in str(err):
                # Still try to load data if specified and collection is empty
                if data_file and client:
                    collection = client[db_name][collection_name]
                    if collection.count_documents({}) == 0:
                        count = self.__load_data_with_embeddings(client, db_name, collection_name, data_file)
                        props["documents_loaded"] = str(count)
                return CreateResult(id_=f"{db_name}.{collection_name}", outs=props)
            # Raise an error if the collection creation fails
            raise RuntimeError("Failed to create collection.")

        except errors.PyMongoError:
            # Catch and raise any MongoDB connection errors
            raise RuntimeError(f"MongoDB connection error.")
        finally:
            # Ensure that the client is closed if it was successfully created
            if client is not None:
                client.close()

class MongoDBCollection(Resource):
    """
    A Pulumi custom resource representing a MongoDB collection.

    This class allows users to manage MongoDB collections via Pulumi.
    """

    def __init__(
        self, name: str, props: Dict[str, str], opts: Optional[ResourceOptions] = None
    ):
        """
        Initializes the MongoDBCollection resource.

        Args:
            name (str): The Pulumi resource name.
            props (Dict[str, str]): A dictionary containing input properties for the collection.
            opts (Optional[ResourceOptions]): Additional Pulumi resource options.
        """
        super().__init__(MongoDBCollectionProvider(), name, props, opts)
