import base64
import os

logo_b64 = (
    'iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAABEUlEQVR4Xu3XwQ3AIBADwP7/6bK1R1oKdYbKlJtG8fA2Tj2P+fX8nP5nIAAAAAAAAAAAAAPg+JHa9bu94N5A0wA7gC+Aa4A3gDuAL4BvgDuAL4BvgDuAA8JLtXeafkUYrwAAAABJRU5ErkJggg=='
)

os.makedirs('static', exist_ok=True)
path = os.path.join('static', 'logo.png')
with open(path, 'wb') as f:
    f.write(base64.b64decode(logo_b64))
print('created', path)
