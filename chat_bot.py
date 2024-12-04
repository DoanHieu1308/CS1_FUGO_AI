from flask import Flask, request, jsonify
import openai
from dotenv import load_dotenv
import os

load_dotenv()

# Khởi tạo Flask app
app = Flask(__name__)

# 
# # Khóa API OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Endpoint nhận câu hỏi và trả lời lại
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message")

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    # Gửi câu hỏi đến OpenAI API
    messages = [
        {"role": "system", "content": "Bạn là chuyên gia tư vấn du học và xuất khẩu lao động toàn cầu. Câu trả lời chỉ cần xoay quanh chủ đề du học và xuất khẩu lao động"},
        {"role": "user", "content": user_message}
    ]
    completion = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )

    bot_reply = completion.choices[0].message.content
    return jsonify({"reply": bot_reply})

# Chạy Flask app
if __name__ == "__main__":
    app.run(debug=True)
