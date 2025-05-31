from gtts import gTTS

text = "어서오세요. CCK 커피입니다."
tts = gTTS(text=text, lang='ko')
tts.save("static/welcome.mp3")  # 🔊 static 폴더에 저장됨
