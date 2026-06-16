FROM python:3.10-slim

WORKDIR /app

# Install dependencies first for better layer caching
COPY requirements.txt pyproject.toml ./
COPY pf_liquidity_risk ./pf_liquidity_risk
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY pipeline ./pipeline
COPY data/raw/sample_interest_rates.csv ./data/raw/sample_interest_rates.csv

# Default: run the full pipeline offline (deterministic, no secrets needed)
ENTRYPOINT ["python", "-m", "pipeline.cli"]
CMD ["run", "--offline", "--iterations", "10000"]
