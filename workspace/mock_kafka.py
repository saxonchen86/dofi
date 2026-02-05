🤖 正在思考 (Model: qwen3-coder:30b)...
----------------------------------------
```python
from kafka import KafkaProducer
import json
import random
import time
from datetime import datetime

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

behaviors = ['click', 'buy', 'fav']
items = [f'item_{i}' for i in range(100)]

while True:
    messages = []
    for _ in range(10):
        message = {
            'user_id': random.randint(1, 1000),
            'item_id': random.choice(items),
            'behavior': random.choice(behaviors),
            'ts': datetime.now().timestamp()
        }
        messages.append(message)
    
    for msg in messages:
        producer.send('user_behavior', msg)
    
    producer.flush()
    time.sleep(1)
```
----------------------------------------
