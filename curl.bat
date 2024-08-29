curl -X POST http://localhost:11434/api/generate \
     -H "Content-Type: application/json" \
     -d '{

           "model": "qwen2:latest",
           "prompt": "hello!",
           "max_tokens": 100,
           "stream": false
         }'
