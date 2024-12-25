import json
import requests
import pytz
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime
from learn_ai_1 import suggest_jobs
from flask import Flask, request, jsonify

# Khởi tạo Flask app
app = Flask(__name__)

# Job
def content_based_recommendations(jobs_df, selected_jobs_df, top_n=20):
    jobs_df = jobs_df.copy()

    # Tính điểm content_score
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(jobs_df['title'])
    cosine_similarities = cosine_similarity(tfidf_matrix)

    # Khởi tạo cột để lưu điểm content score cho mỗi công việc
    jobs_df['content_score'] = 0.0

    # Cập nhật content_score dựa trên selected_jobs_df
    for _, selected_job in selected_jobs_df.iterrows():
        selected_title = selected_job['title']
        if selected_title in jobs_df['title'].values:
            idx = jobs_df[jobs_df['title'] == selected_title].index[0]
            for i, score in list(enumerate(cosine_similarities[idx])):
                jobs_df.loc[jobs_df.index[i], 'content_score'] += score
        else:
            print(f"Warning: Selected job '{selected_title}' not found in jobs_df.")
    
    # Cập nhật điểm description cho các công việc dựa trên số từ trùng khớp
    def calculate_description_score(row):
        description_score = 0
        for desc in selected_jobs_df['description']:
            # Tính toán số từ trùng khớp
            common_words = set(row['description'].split()).intersection(set(desc.split()))
            description_score += len(common_words)  # Tăng điểm theo số từ trùng khớp
        return description_score

    # Áp dụng hàm tính điểm description
    jobs_df['description_score'] = jobs_df.apply(calculate_description_score, axis=1)

    # Áp dụng hàm chuyển đổi vào cột 'createdAt'
    jobs_df['createdAt'] = pd.to_datetime(jobs_df['createdAt'], utc=True)
    print("Kiểu dữ liệu của 'createdAt':", jobs_df['createdAt'].dtype)

    # Kiểm tra sự tồn tại của cột profession và educational_level
    if 'profession' not in jobs_df.columns or 'profession' not in selected_jobs_df.columns:
        print("Warning: 'profession' column is missing from one of the DataFrames.")
        return jobs_df[["_id", "title"]]

    # Tính toán điểm tổng hợp với các tiêu chí đã cho
    try:
        jobs_df["score"] = (
            jobs_df["country"].apply(lambda x: 1 if x in selected_jobs_df['country'] else 0) * 0.2 +        # Trọng số cho country match
            jobs_df["minSalary"].apply(lambda x: int(x) if pd.notna(x) and str(x).isdigit() else 0) * 0.1 +  # Trọng số cho salary match
            jobs_df["profession"].apply(lambda x: 1 if x in selected_jobs_df['profession'].values else 0) * 0.1 +  # Trọng số cho profession match
            jobs_df["educationalLevel"].apply(lambda x: 1 if x in selected_jobs_df['educationalLevel'].values else 0) * 0.1 +  # Trọng số cho education match
            jobs_df["content_score"] * 1000 +                                                           # Trọng số cho content-based recommendation
            jobs_df["description_score"] * 0.2 +                                                      # Trọng số cho description match
            jobs_df['createdAt'].apply(lambda x: (datetime.now(pytz.UTC) - x).days if pd.notna(x) else 0) * -0.1  # Trọng số cho thời gian (ngày gần đây nhất)
        )
        print("Điểm đã được tính thành công.")
    except Exception as e:
        print("Lỗi khi tính điểm: ", str(e))

    # Sắp xếp danh sách công việc dựa trên điểm tổng hợp
    recommended_jobs = jobs_df.sort_values(by="score", ascending=False).head(top_n)
    print (recommended_jobs)
    return recommended_jobs


# Endpoint nhận yêu cầu và trả kết quả
@app.route("/api/recommend/jobs", methods=["POST"])
def recommend():
    try:
        # Lấy tất cả các jobs
        url = "http://localhost:3000/api/v1/jobs"
        headers = {'Content-Type': 'application/json'}

        
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()  
            jobs = data.get('data', [])  
        else:
            print(f"Failed to fetch jobs. Status code: {response.status_code}")
            print("Response:", response.text)
        
        # Chuyển all jobs sang kiểu DataFrame
        jobs_all = pd.DataFrame(jobs)
        print("All Jobs DataFrame:")
        print(jobs_all)

        # Parse dữ liệu từ body của request
        data = request.get_json()

        # Lấy thông tin `jobs` và `user` từ body
        selected_jobs = data.get("selected_jobs", [])
        user_profile = data.get("user_profile", {})

        # Kiểm tra dữ liệu đầu vào
        print("selected_job:", selected_jobs)
        print("user_profile:", user_profile)

        # selected job
        if not selected_jobs:
            raise ValueError("Selected jobs data is missing or invalid.") 
        selected_jobs_df = pd.DataFrame(selected_jobs)
        if selected_jobs_df.empty or 'title' not in selected_jobs_df.columns:
            raise ValueError("The user activity file does not contain valid 'selected_jobs' data.")

        # Kiểm tra dữ liệu đã được lấy
        print("Selected Jobs DataFrame:")
        print(selected_jobs_df)

        # So sánh tất cả các job với select job
        recommended_jobs_df = content_based_recommendations(jobs_all, selected_jobs_df)
        recommended_jobs_list = recommended_jobs_df.to_dict(orient='records')
        print("recommended_jobs_list", recommended_jobs_list)

        # Lấy gợi ý từ AI
        jobs_id_recomment_of_ai = suggest_jobs(user_profile[0], recommended_jobs_list, "job")
        print("jobs_id_recomment_of_ai", jobs_id_recomment_of_ai)
        
        # Lọc các công việc và giữ nguyên thứ tự của jobs_id_recomment_of_ai
        jobs_recomment_of_ai = jobs_all.set_index('_id').loc[jobs_id_recomment_of_ai].reset_index()
        print ("123", jobs_recomment_of_ai)
        recommended_jobs_list_ai = jobs_recomment_of_ai.to_dict(orient='records')

        # Lấy danh sách ID từ DataFrame
        recommended_jobs_list_ai = jobs_recomment_of_ai['_id'].tolist()

        print("recommended_jobs_list_ai", recommended_jobs_list_ai)

        return jsonify({"accountId": user_profile[0]['accountId'], "jobs": recommended_jobs_list_ai})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)