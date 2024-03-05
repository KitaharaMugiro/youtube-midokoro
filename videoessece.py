from pytube import YouTube
import os
import streamlit as st
from openai import OpenAI
import json
import anthropic
from pydub import AudioSegment

@st.cache_data
def save_audio(url):
    yt = YouTube(url, use_oauth=False, allow_oauth_cache=True)
    video = yt.streams.filter(only_audio=True).first()
    if video is None:
        raise ValueError("No audio stream found for this video")

    out_file = video.download()

    # out_fileのディレクトリを取得
    directory = os.path.dirname(out_file)

    # ディレクトリと新しいファイル名を結合して最終的なパスを取得
    final_path = os.path.join(directory, "output.mp3")
    # out_fileをoutput.mp3にリネーム
    os.rename(out_file, "output.mp3")

    print(yt.title + " has been successfully downloaded.")

    # ファイルサイズを下げる
    audio = AudioSegment.from_file("output.mp3")
    # PyDub handles time in milliseconds
    one_hour = 60 * 60 * 1000

    breaked_audio = audio[:one_hour]

    breaked_audio = breaked_audio.set_frame_rate(44100).set_channels(2).set_sample_width(2)
    breaked_audio = breaked_audio.export("output.mp3", format="mp3", bitrate="32k")

    return yt.title, final_path, yt.thumbnail_url


st.title("Youtube見どころシーン抽出")
url = st.text_input("URL", key="url")
language = st.selectbox("Select Language", ["en", "ja"], index=0, key="language")



if st.button("テキスト化"):
    title, file_name, thumbnail_url = save_audio(url)
    audio_file = open(file_name, "rb")

    client = OpenAI()
    client.base_url = "https://oai.langcore.org/v1"
    transcription = client.audio.transcriptions.with_raw_response.create(
      model="whisper-1", 
      file=audio_file,
      response_format="verbose_json",
      language=language,
      timestamp_granularities=["segment"]
    )
    completion = transcription.parse()  # Parse the transcription response to JSON
    #st.write(completion)
    segments = completion.model_dump()["segments"]
    segment_objects = [{"start": segment["start"], "end": segment["end"], "text": segment["text"]} for segment in segments]
    texts = ""
    for segment_object in segment_objects:
        #st.write(f"Start: {segment_object['start']}, End: {segment_object['end']}, Text: {segment_object['text']}")
        texts += f"Start: {segment_object['start']}, End: {segment_object['end']}, Text: {segment_object['text']}\n"
    # st.text_area("テキスト", value=texts, key="text")

    # chat_completion = client.chat.completions.create(
    # messages=[
    #     {
    #         "role": "system",
    #         "content": texts + f"""
    #         StartとEndの単位は秒数です。
            
    #         以下のフォーマットで、見どころシーンのまとめをしてください。
    #         [xx:xx]({url}&t=xxxs), 終了時間yy:yy, 見どころシーン概要 \n
            
    #         例: [01:10]({url}&t=70s), 終了時間01:30, パックンさんが1時間弱は50分くらいだと思う若者がいることに驚きを示すシーン
    #         """,
    #     }
    # ],
    # model="gpt-4-1106-preview",
    # )
    #   text = chat_completion.choices[0].message.content

    client = anthropic.Client(api_key=st.secrets["CLAUDE_API_KEY"])
    message = client.messages.create(
        model="claude-3-opus-20240229",
        temperature=0,
        max_tokens=1000,
        system=f"StartとEndの単位は秒数です。\n            \n以下のフォーマットで、見どころシーンのまとめをしてください。\n[xx:xx]({url}&t=xxxs), 終了時間yy:yy, 見どころシーン概要 \\n\n            \n例: [01:10]({url}&t=70s), 終了時間01:30, パックンさんが1時間弱は50分くらいだと思う若者がいることに驚きを示すシーン",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": texts
                    }
                ]
            }
        ]
    )

    st.markdown(message.content[0].text)

    


