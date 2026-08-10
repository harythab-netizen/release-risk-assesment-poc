from flask import Flask, jsonify
app = Flask(__name__)
@app.route("/")
def home():
    return jsonify(
        {
            "service": "release-risk-demo",
            "version": "1.0.1",
            "status": "healthy",
        }
    )
@app.route("/health")
def health():
    return jsonify({"status": "UP"})
    
@app.route("/version")
def version():
    return jsonify(
        {
            "version": "1.0.1",
            "release": "critical-hotfix"
        }
    )
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
