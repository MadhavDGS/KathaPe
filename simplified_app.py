from flask import Flask

# Create the Flask application
app = Flask(__name__)

@app.route('/')
def hello():
    return "KathaPe is running! Main app is being loaded."

if __name__ == '__main__':
    app.run(debug=True) 