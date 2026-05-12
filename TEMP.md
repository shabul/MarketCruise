# Bedrock / GLM Notes

Use this file as a scratchpad for local Bedrock experiments.

## Local auth

- Prefer environment variables instead of hardcoding credentials.
- Typical variables to set locally:
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `AWS_SESSION_TOKEN`
  - `AWS_BEARER_TOKEN_BEDROCK`
- Keep these in your shell profile or a local `.env` file that is not committed.

## Example shape

```python
import boto3
import json

client = boto3.client("bedrock-runtime", region_name="ap-south-1")

response = client.invoke_model(
    modelId="zai.glm-5",
    contentType="application/json",
    accept="application/json",
    body=json.dumps({
        "messages": [
            {"role": "user", "content": "Explain transformers simply"}
        ]
    })
)

result = json.loads(response["body"].read())
print(result)
```
