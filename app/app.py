"""
app.py: Flask application that provides a /vectorsearch endpoint
        to perform vector searches on a MongoDB collection.
"""

from flask import Flask, request, jsonify
from pymongo.errors import PyMongoError, OperationFailure, NetworkTimeout
from db import collection, get_embedding, setup_vector_search  # Import necessary utilities

app = Flask(__name__)

@app.route('/', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "message": "Wonders of the World API"})

@app.route('/load-data', methods=['POST'])
def load_data():
    """Load sample data into MongoDB"""
    try:
        count = setup_vector_search()
        return jsonify({
            "status": "success",
            "message": f"Loaded {count} documents into the database"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/vectorsearch', methods=['GET'])
def vector_search():
    """
    Endpoint to perform a vector search on the MongoDB collection.

    This endpoint expects a 'prompt' query parameter and searches the collection
    using vector embeddings to find similar documents.

    Returns:
        JSON response containing the query and the search results.
    """
    # Get the "prompt" query parameter
    prompt = request.args.get('prompt')

    if not prompt:
        return jsonify({
            "error": "Missing required query parameter 'prompt'"
        }), 400

    # Generate the embedding for the user's input
    query_embedding = get_embedding(prompt)

    # Vector search pipeline
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector-index",  # Update this to match your vector search index name
                "queryVector": query_embedding,
                "path": "embedding",  # The field in the collection where embeddings are stored
                "exact": True,
                "limit": 5  # Limit the number of results returned
            }
        },
        {
            "$project": {
                "text": 1,  # Include the field storing document text
                "score": {  # Include the similarity score
                    "$meta": "vectorSearchScore"
                }
            }
        },
        {
            "$sort": {
                "score": -1  # Sort results by descending similarity score
            }
        }
    ]

    # Fetch results using the aggregation pipeline
    data = []
    try:
        results = collection.aggregate(pipeline)
        for doc in results:
            # Convert ObjectId to string for JSON serialization
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])
            data.append(doc)
    except (PyMongoError, OperationFailure, NetworkTimeout) as e:  # Catch specific MongoDB errors
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except ValueError as e:  # Catch data-related errors
        return jsonify({"error": f"Data error: {str(e)}"}), 400


    return jsonify({
        "query": prompt,
        "results": data
    })


if __name__ == '__main__':
    setup_vector_search()
    app.run(port=8080, debug=True, host='0.0.0.0')
