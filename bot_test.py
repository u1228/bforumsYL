from requests import Session
from flask import Flask, request, jsonify, abort


s = Session()
app = Flask(__name__)

EMAIL = "bot-test@email.com"
PASSWORD = "bottest1"

LOGIN_URL = "http://bforums.herokuapp.com/api/v1/login"
CALLBACK_URL = "http://bforums.herokuapp.com/api/v1/callback"

@app.route("/", methods=["POST"])
def main():
    args = request.get_json()
    if "message" in args.keys():
        message = args["message"].lower()
        ms = message.split(' ')
        if ms[0] == "переверни":
            return ' '.join(ms[1:])[::-1]
    return ""

def get_ngrok_server():
    return s.get("http://localhost:4040/api/tunnels").json()['tunnels'][0]['public_url']

response = s.post(LOGIN_URL, json={"email": EMAIL, "password": PASSWORD})
if response.ok:
    response = s.post(CALLBACK_URL, json={"server": get_ngrok_server()})

if __name__ == "__main__":
    app.run(port=5282, debug=True)