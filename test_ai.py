from google import genai

client = genai.Client(api_key="AIzaSyCOjVUdP0lOMdxKpX5I0T1-8y8bX6Lmw30")

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="What causes fever?"
)

print(response.text)