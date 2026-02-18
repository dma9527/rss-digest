#!/usr/bin/env python3
from google import genai
import os

api_key = os.environ.get('GEMINI_API_KEY')
if not api_key:
    print("请设置 GEMINI_API_KEY 环境变量")
    exit(1)

client = genai.Client(api_key=api_key)

print("可用的模型:\n")
for model in client.models.list():
    print(f"  ✓ {model.name}")
