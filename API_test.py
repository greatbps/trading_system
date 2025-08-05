import google.generativeai as genai
 
GOOGLE_API_KEY="AIzaSyBsXOxghiH3pzklMW5eTLuNu-Stu8dv0XU"
 
genai.configure(api_key=GOOGLE_API_KEY)
 
model = genai.GenerativeModel('gemini-2.5-pro')
 
response = model.generate_content("태양계 행성의 종류에 대하여 알려줘")
 
print(response.text)
