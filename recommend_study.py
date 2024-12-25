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


# Study 
def content_based_recommendations(studys_df, selected_studys_df, top_n=20):
    studys_df = studys_df.copy()

    # Tính điểm content_score
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(studys_df['title'])
    cosine_similarities = cosine_similarity(tfidf_matrix)

    # Khởi tạo cột để lưu điểm content score cho mỗi công việc
    studys_df['content_score'] = 0.0

    # Cập nhật content_score dựa trên selected_jobs_df
    for _, selected_study in selected_studys_df.iterrows():
        selected_title = selected_study['title']
        if selected_title in studys_df['title'].values:
            idx = studys_df[studys_df['title'] == selected_title].index[0]
            for i, score in list(enumerate(cosine_similarities[idx])):
                studys_df.loc[studys_df.index[i], 'content_score'] += score
        else:
            print(f"Warning: Selected job '{selected_title}' not found in jobs_df.")
    
    # Cập nhật điểm description cho các công việc dựa trên số từ trùng khớp
    def calculate_description_score(row , attribute):
        description_score = 0
        for desc in selected_studys_df[attribute]:
            # Tính toán số từ trùng khớp
            common_words = set(row[attribute].split()).intersection(set(desc.split()))
            description_score += len(common_words)  # Tăng điểm theo số từ trùng khớp
        return description_score

    # Áp dụng hàm tính điểm description
    studys_df['description_score'] = studys_df.apply(lambda row: calculate_description_score(row, attribute="description"), axis=1)

    # Áp dụng hàm tính điểm description
    studys_df['requirements_score'] = studys_df.apply(lambda row: calculate_description_score(row, attribute="requirements"), axis=1)

    # Áp dụng hàm chuyển đổi vào cột 'created_at'
    studys_df['created_at'] = pd.to_datetime(studys_df['created_at'], utc=True)
    print("Kiểu dữ liệu của 'created_at':", studys_df['created_at'].dtype)

    # Tính toán điểm tổng hợp với các tiêu chí đã cho
    try:
        studys_df["score"] = (
            studys_df["country"].apply(lambda x: 1 if x in selected_studys_df['country'] else 0) * 0.2 +        # Trọng số cho country match
            studys_df["duration"].apply(lambda x: 1 if x in selected_studys_df['duration'].values else 0) * 0.1 +  # Trọng số cho profession match
            studys_df["location"].apply(lambda x: 1 if x in selected_studys_df['location'].values else 0) * 0.1 +  # Trọng số cho education match
            studys_df["content_score"] * 1000 +                                                           # Trọng số cho content-based recommendation
            studys_df["description_score"] * 0.2 + 
            studys_df["requirements_score"] * 0.2 +                                                     # Trọng số cho description match
            studys_df['created_at'].apply(lambda x: (datetime.now(pytz.UTC) - x).days if pd.notna(x) else 0) * -0.1  # Trọng số cho thời gian (ngày gần đây nhất)
        )
        print("Điểm đã được tính thành công.")
    except Exception as e:
        print("Lỗi khi tính điểm: ", str(e))

    # Sắp xếp danh sách công việc dựa trên điểm tổng hợp
    recommended_studys = studys_df.sort_values(by="score", ascending=False).head(top_n)
    print (recommended_studys)
    return recommended_studys

# Endpoint nhận yêu cầu và trả kết quả
@app.route("/api/recommend/studys", methods=["POST"])
def recommend():
    try:
        # Lấy tất cả các jobs
        url = "http://localhost:3000/api/v1/study"
        headers = {'Content-Type': 'application/json'}

        
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()  
            studys = data.get('data', [])  
        else:
            print(f"Failed to fetch jobs. Status code: {response.status_code}")
            print("Response:", response.text)
        
        # Chuyển all jobs sang kiểu DataFrame
        studys_all = pd.DataFrame(studys)
        print("All Jobs DataFrame:")
        print(studys_all)

        # Parse dữ liệu từ body của request
        data = request.get_json()

        # Lấy thông tin `jobs` và `user` từ body
        selected_studys = data.get("selected_studys", [])
        user_profile = data.get("user_profile", {})

        # Kiểm tra dữ liệu đầu vào
        print("selected_studys:", selected_studys)
        print("user_profile:", user_profile)

        # selected job
        if not selected_studys:
            raise ValueError("Selected jobs data is missing or invalid.") 
        selected_studys_df = pd.DataFrame(selected_studys)
        if selected_studys_df.empty or 'title' not in selected_studys_df.columns:
            raise ValueError("The user activity file does not contain valid 'selected_jobs' data.")

        # Kiểm tra dữ liệu đã được lấy
        print("Selected Jobs DataFrame:")
        print(selected_studys_df)

        # So sánh tất cả các job với select job
        recommended_studys_df = content_based_recommendations(studys_all, selected_studys_df)
        recommended_studys_list = recommended_studys_df.to_dict(orient='records')
        print("recommended_jobs_list", recommended_studys_list)

        # Lấy gợi ý từ AI
        studys_id_recomment_of_ai = suggest_jobs(user_profile[0], recommended_studys_list, "study")
        print("jobs_id_recomment_of_ai", studys_id_recomment_of_ai)
        
        # Lọc các công việc và giữ nguyên thứ tự của jobs_id_recomment_of_ai
        studys_recomment_of_ai = studys_all.set_index('_id').loc[studys_id_recomment_of_ai].reset_index()
        print ("123", studys_recomment_of_ai)
        recommended_studys_list_ai = studys_recomment_of_ai.to_dict(orient='records')

        # Lấy danh sách ID từ DataFrame
        recommended_studys_list_ai = studys_recomment_of_ai['_id'].tolist()

        print("recommended_jobs_list_ai", recommended_studys_list_ai)

        return jsonify({"account_id": user_profile[0]['account_id'], "studys": recommended_studys_list_ai})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=6000)