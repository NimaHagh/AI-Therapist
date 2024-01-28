import gradio as gr
import openai
import constants
from google.cloud import texttospeech
from google.oauth2 import service_account
import langdetect
import os
from gradio_folium import Folium
from folium import Map
import pandas as pd
import pathlib
#import pyttsx3
#import os


credentials = service_account.Credentials.from_service_account_file('key.json')
print("credentials being read")

openai.api_key = constants.APIKEY
conversation =  [
            {"role": "system", "content": "You are the best human therapist in the world."}
        ]


def transcribe(audio):
    #Whisper API
    audio_file = open(audio, "rb")
    transcript = openai.Audio.transcribe("whisper-1", audio_file)
    conversation.append({"role": "user", "content": transcript["text"]})
    #return transcript["text"]
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages = conversation
    )


    system_message = response['choices'][0]['message']['content']
    conversation.append({"role": "system", "content": system_message })

    if not os.path.exists('key.json'):
        raise FileNotFoundError(f"Service account file not found: {'key.json'}")


    client = texttospeech.TextToSpeechClient(credentials=credentials)
    input_text = texttospeech.SynthesisInput(text=system_message)

    
    # Language Detection
    detect_lang = langdetect.detect(transcript["text"])

    # Define dictionary to map the detected language to language code and voice name
    language_dict = {
        'it': {'language_code': 'it-IT', 'voice_name': 'it-IT-Wavenet-D', 'gender': texttospeech.SsmlVoiceGender.FEMALE},
        'de': {'language_code': 'de-DE', 'voice_name': 'de-DE-Wavenet-A', 'gender': texttospeech.SsmlVoiceGender.FEMALE},
        'fr': {'language_code': 'fr-FR', 'voice_name': 'fr-FR-Wavenet-D', 'gender': texttospeech.SsmlVoiceGender.FEMALE},
        'es': {'language_code': 'es-ES', 'voice_name': 'es-ES-Neural2-D', 'gender': texttospeech.SsmlVoiceGender.FEMALE},
        'ja': {'language_code': 'ja-JP', 'voice_name': 'ja-JP-Neural2-D', 'gender': texttospeech.SsmlVoiceGender.FEMALE},
        'hi': {'language_code': 'hi-IN', 'voice_name': 'hi-IN-Standard-D', 'gender': texttospeech.SsmlVoiceGender.FEMALE},
        'ar': {'language_code': 'ar-XA', 'voice_name': 'ar-XA-Wavenet-B', 'gender': texttospeech.SsmlVoiceGender.FEMALE}
    }

    if detect_lang in language_dict:
        language_code = language_dict[detect_lang]['language_code']
        voice_name = language_dict[detect_lang]['voice_name']
        gender = language_dict[detect_lang]['gender']
    else:
        language_code = "en-US"
        voice_name = "en-US-Standard-C"
        gender = texttospeech.SsmlVoiceGender.FEMALE
    
    # Voice configuration
    voice = texttospeech.VoiceSelectionParams(
        language_code= language_code,
        name= voice_name,
        ssml_gender= gender,
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    responses = client.synthesize_speech(
    request={"input": input_text, "voice": voice, "audio_config": audio_config}
    )

    # The response's audio_content is binary.
    with open("output.mp3", "wb") as out:
        out.write(responses.audio_content)
        print('Audio content written to file "output.mp3"')
    return responses.audio_content,system_message

# New function to process text input and return voice and text response
def process_text_and_respond(text_input):
    conversation.append({"role": "user", "content": text_input})
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=conversation
    )
    
    system_message = response['choices'][0]['message']['content']
    conversation.append({"role": "system", "content": system_message })

    # Generate voice response
    client = texttospeech.TextToSpeechClient(credentials=credentials)
    input_text = texttospeech.SynthesisInput(text=system_message)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Standard-C",
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
    )
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    responses = client.synthesize_speech(
       request={"input": input_text, "voice": voice, "audio_config": audio_config}
    )

    # Return both text and voice response
    return responses.audio_content,system_message
article = "If you or someone you know is in crisis" \
          "If you're in immediate danger or need urgent medical support, call 9-1-1." \
          "If you or someone you know is thinking about suicide, call or text 9-8-8. Support is available 24 hours a day, 7 days a week."
# Define the Gradio interfaces
voice_interface = gr.Interface(
    fn=transcribe,
    inputs=gr.Audio(label = "Speak your concerns: ",sources="microphone", type="filepath"),
    outputs= [gr.Audio(label="Response Audio"),gr.Text(label="Response Text")],
    title="Voice Interaction - Team 12 Serenity Hacks 2024", article= article
)

text_interface = gr.Interface(
    fn=process_text_and_respond,
    inputs=gr.Textbox(label = "Type your concerns: "),
    outputs=[gr.Audio(label="Response Audio"),gr.Text(label="Response Text")],
    title="Text Interaction - Team 12 Serenity Hacks 2024", article=article
   
)


df = pd.read_csv(pathlib.Path(__file__).parent / "cities.csv")
def select(df, data: gr.SelectData):
    row = df.iloc[data.index[0], :]
    return Map(location=[row['Latitude'], row['Longitude']])

with gr.Blocks() as demo1:
    gr.Markdown(("# 🗺️ Explore"))
    map = Folium(value=Map(location=[25.7617, -80.1918]), height=400)
    data = gr.DataFrame(value=df, height=200)
    data.select(select, data, map)


# Combine the interfaces in a Tabbed Interface
gr.TabbedInterface([voice_interface, text_interface,demo1], ["Voice", "Text", "Info"]).launch()