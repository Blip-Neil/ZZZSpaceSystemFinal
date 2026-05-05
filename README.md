# Dorming

Find your next dorm the easy way.

Dorming is a student housing system for campus living, boarding houses, and apartment rentals with fast search and listings curated for learners.

<video controls>
  <source src="static/uploads/dorm_intro.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Initialize the SQLite database (optional):

```bash
python create_db.py
```


If you skip this step, the database will be created automatically when you run the app.

3. Run the app:

```bash
python app.py
```

4. Open the browser at:

```
http://127.0.0.1:5000/
```

## Production Deployment

For production deployment with gunicorn:

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python create_db.py

# Run with gunicorn
gunicorn --bind 0.0.0.0:8000 app:application

# Or use the configuration file
gunicorn -c gunicorn.conf.py app:application
```

The app will be available at `http://localhost:8000/`
