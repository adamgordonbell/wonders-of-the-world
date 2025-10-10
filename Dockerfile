FROM public.ecr.aws/lambda/python:3.11

# Copy requirements and install dependencies
COPY app/requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r requirements.txt

# Create model cache directory
RUN mkdir -p /opt/ml

# Set environment variables for model caching during build
ENV HF_HOME=/opt/ml
ENV TRANSFORMERS_CACHE=/opt/ml
ENV SENTENCE_TRANSFORMERS_HOME=/opt/ml

# Download and cache the model during build to /opt/ml
RUN python3 -c "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('nomic-ai/nomic-embed-text-v1', trust_remote_code=True); print('Model downloaded successfully')"

# Copy application code
COPY app/app.py ${LAMBDA_TASK_ROOT}/
COPY app/db.py ${LAMBDA_TASK_ROOT}/
COPY app/lambda_handler.py ${LAMBDA_TASK_ROOT}/
COPY app/data.json ${LAMBDA_TASK_ROOT}/

# Set the CMD to your handler
CMD ["lambda_handler.handler"]
