import openai
import re
from dotenv import load_dotenv
import os

load_dotenv()

# # Khóa API OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Định dạng lại dữ liệu để tạo prompt cho GPT-3
def format_jobs_data(jobs):
    return "\n".join([
        f"_id: {job['_id']}\n"
        f"title: {job['title']}\n"
        f"description: {job['description']}\n"
        f"requirements: {job['requirements']}\n"
        f"country: {job['country']}\n"
        f"profession: {job['profession']}\n"
        f"experience: {job['experience']}\n"
        for job in jobs
    ])

def suggest_jobs(user_info, jobs_data):
    formatted_jobs = format_jobs_data(jobs_data)
    # Create a conversation message structure
    messages = [
        {"role": "system", "content": "You are a global study abroad and labor export consultant."},
        {"role": "user", "content": f"Based on the user's information (Height: {user_info['height']} cm, Weight: {user_info['weight']} kg, Gender: {user_info['gender']}), Birthday : {user_info['birthday']} " +
        f"suggest exactly 12 most suitable jobs for user from the following list, only return a Python-style list of job IDs, like ['5', '3', '2']. " +
        "Here is the job list:\n\n" + formatted_jobs}
    ]
    # Gọi API GPT-3 để gợi ý công việc
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
    )
    # Hiển thị gợi ý công việc
    suggested_jobs = response.choices[0].message.content

    print("suggested_jobs", suggested_jobs)

    
    def extract_ids_from_response(response_text, valid_ids):
        # Sử dụng regex để tìm tất cả các chuỗi nằm trong dấu nháy đơn và dấu ngoặc vuông
        ids = re.findall(r"'(.*?)'", response_text)
        # Lọc các ID nằm trong danh sách hợp lệ
        filtered_ids = [id for id in ids if id in valid_ids]
        return filtered_ids

        # Danh sách ID hợp lệ từ dữ liệu công việc
    valid_ids = [job["_id"] for job in jobs_data]
    job_recomment_by_ai = extract_ids_from_response(suggested_jobs, valid_ids)
    print (job_recomment_by_ai)
    return job_recomment_by_ai



