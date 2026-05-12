import boto3
import json

client = boto3.client("bedrock-runtime", region_name="ap-south-1")

response = client.invoke_model(
    modelId="zai.glm-5",  # e.g. zhipu.glm-5
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