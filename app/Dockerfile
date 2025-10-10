FROM public.ecr.aws/lambda/python:3.11

# Copy requirements and install dependencies
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt
RUN pip install --no-cache-dir mangum

# Copy application code
COPY app.py ${LAMBDA_TASK_ROOT}/
COPY db.py ${LAMBDA_TASK_ROOT}/
COPY data.json ${LAMBDA_TASK_ROOT}/
COPY lambda_handler.py ${LAMBDA_TASK_ROOT}/

# Set the CMD to your handler
CMD [ "lambda_handler.handler" ]
