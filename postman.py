from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route("/test", methods = ["GET", "POST"])
def test():
    if request.method == "GET":
        return jsonify({"response":"Get Response Called"})
    elif request.method == "POST":
        req_json = request.json
        name = req_json["name"]
        return jsonify({"response": "Hi" + name})


if __name__ == "__main__":
    app.run(debug=True, port = 9090)