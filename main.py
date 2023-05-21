from twitchio.ext import commands
from chat import *
from google.cloud import texttospeech_v1beta1 as texttospeech
import vlc
import os 
import time
import nltk
import creds
import requests
CONVERSATION_LIMIT = 20

class Bot(commands.Bot):
    conversation = list()

    def __init__(self):
        Bot.conversation.append({ 'role': 'system', 'content': open_file('prompt_chat.txt') })
        super().__init__(token=creds.TWITCH_TOKEN, prefix='!', initial_channels=[creds.TWITCH_CHANNEL])

    async def event_ready(self):
        print(f'Logged in as | {self.nick}')

    async def event_message(self, message):
        if message.echo:
            return
        
        nltk.download('words')
        
        if not any(word in message.content for word in nltk.corpus.words.words()):
            return
        
        if len(message.content) > 70 or len(message.content) < 3:
            return   
        
        # Check if message contains crypto ticker
        if "BTC" in message.content or "ETH" in message.content or "LTC" in message.content:
            crypto_prices = get_crypto_prices()
            Bot.conversation.append({ 'role': 'assistant', 'content': crypto_prices })
            
        content = message.content.encode(encoding='ASCII',errors='ignore').decode()
        
        Bot.conversation.append({ 'role': 'user', 'content': content })
        
        response = gpt3_completion(Bot.conversation)
        
        if(Bot.conversation.count({ 'role': 'assistant', 'content': response }) == 0):
            Bot.conversation.append({ 'role': 'assistant', 'content': response })
            
        if len(Bot.conversation) > CONVERSATION_LIMIT:
            Bot.conversation = Bot.conversation[1:]
            
        client = texttospeech.TextToSpeechClient()
        
        response = message.content + "? " + response
        
        ssml_text = '<speak>'
        
        response_counter = 0
        mark_array = []
        
        for s in response.split(' '):
            ssml_text += f'<mark name="{response_counter}"/>{s}'
            mark_array.append(s)
            response_counter += 1
            
        ssml_text += '</speak>'
        
        input_text = texttospeech.SynthesisInput(ssml=ssml_text)
        
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-GB",
            name="en-GB-Wavenet-B",
            ssml_gender=texttospeech.SsmlVoiceGender.MALE,
        )
        
        audio_config = texttospeech.AudioConfig(    
            audio_encoding=texttospeech.AudioEncoding.MP3,   
        )
        
        response = client.synthesize_speech(
            request={"input": input_text, "voice": voice, "audio_config": audio_config, "enable_time_pointing": ["SSML_MARK"]}
        )
        
        with open("output.mp3", "wb") as out:
            out.write(response.audio_content)
            
        audio_file = os.path.dirname(__file__) + '/output.mp3'
        
        media = vlc.MediaPlayer(audio_file)
        
        media.play()
        
        count = 0
        current = 0
        
        for i in range(len(response.timepoints)):
            count += 1
            current += 1
            
            with open("output.txt", "a", encoding="utf-8") as out:
                out.write(mark_array[int(response.timepoints[i].mark_name)] + " ")
                
            if i != len(response.timepoints) - 1:
                total_time = response.timepoints[i + 1].time_seconds
                time.sleep(total_time - response.timepoints[i].time_seconds)
                
            if current == 25:
                open('output.txt', 'w', encoding="utf-8").close()
                current = 0
                count = 0
            elif count % 7 == 0:
                with open("output.txt", "a", encoding="utf-8") as out:
                    out.write("\n")
                    
        time.sleep(2)
        open('output.txt', 'w').close()
        
        os.remove(audio_file)
        
        await self.handle_commands(message)

    @commands.command()
    async def hello(self, ctx: commands.Context):
        await ctx.send(f'Hello {ctx.author.name}!')

import requests

def get_crypto_prices():
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    headers = {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": "be7d2dbf-cdd1-4aa3-8876-75a7e241526e"
    }
    params = {
        "symbol": "BTC,ETH,LTC"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    data = response.json()
    
    btc_price = round(data["data"]["BTC"]["quote"]["USD"]["price"])
    eth_price = round(data["data"]["ETH"]["quote"]["USD"]["price"])
    ltc_price = round(data["data"]["LTC"]["quote"]["USD"]["price"])
    
    return f"BTC: ${btc_price}, ETH: ${eth_price}, LTC: ${ltc_price}"


os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = creds.GOOGLE_JSON_PATH

bot = Bot()
bot.run()