FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV STREAMLIT_BASE_URL=/

EXPOSE 8501
# Run Streamlit using the env var for baseUrlPath
CMD streamlit run app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.baseUrlPath=$STREAMLIT_BASE_URL