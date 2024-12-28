from flask import Flask, request, jsonify
import openai
import requests
from dotenv import load_dotenv
import os

load_dotenv()

# Khởi tạo Flask app
app = Flask(__name__)

# Khóa API OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Hàm lấy dữ liệu từ API
def fetch_data_from_api(url, headers):
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and 'data' in data:
                return data['data']
            else:
                print(f"Unexpected data format from {url}: {data}")
                return []
        else:
            print(f"Failed to fetch data from {url}. Status code: {response.status_code}")
            print("Response:", response.text)
            return []
    except Exception as e:
        print(f"Error fetching data from {url}: {e}")
        return []

# Endpoint nhận câu hỏi và trả lời lại
@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        # Lấy dữ liệu jobs và studys
        headers = {'Content-Type': 'application/json'}
        jobs_url = "http://localhost:3000/api/v1/jobs/all"
        studys_url = "http://localhost:3000/api/v1/study/all"

        jobs = fetch_data_from_api(jobs_url, headers)
        studys = fetch_data_from_api(studys_url, headers)

        # Lấy tin nhắn người dùng
        data = request.json
        user_message = data.get("message")

        if not user_message:
            return jsonify({"error": "No message provided"}), 400

        # Chuẩn bị dữ liệu cho OpenAI API
        job_titles = ", ".join(job.get('title', 'N/A') for job in jobs)
        study_titles = ", ".join(study.get('title', 'N/A') for study in studys)

        messages = [
            {"role": "system", "content": f"Bạn là chuyên gia tư vấn du học và xuất khẩu lao động toàn cầu. "
                                          f"Câu trả lời chỉ cần xoay quanh chủ đề du học và xuất khẩu lao động. "
                                          f"Dữ liệu jobs: {job_titles}. Dữ liệu studys: {study_titles}."},
            {"role": "user", "content": user_message}
        ]

        # Gọi OpenAI API
        completion = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )

        bot_reply = completion.choices[0].message.content
        return jsonify({"reply": bot_reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Chạy Flask app
if __name__ == "__main__":
    app.run(debug=True)
