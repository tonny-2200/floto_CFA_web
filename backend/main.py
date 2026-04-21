import os
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

subscription_key = os.getenv("AZURE_API_KEY")
deployment = "gpt-5-mini"

client = AzureOpenAI(
    api_version="2024-12-01-preview",
    azure_endpoint="https://truber-slm.cognitiveservices.azure.com/",
    api_key=subscription_key
)

response = client.chat.completions.create(
    messages=[
        {
            "role": "system",
            "content": "You are a helpful assistant.",
        },
        {
            "role": "user",
            "content": "I am going to Paris, what should I see?",
        }
    ],
    model=deployment
)

print(response.choices[0].message.content)