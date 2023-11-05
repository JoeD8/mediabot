#imports
from fastapi_poe import make_app
from modal import Image, Stub, asgi_app

from typing import AsyncIterable
import re
import random

from media_links import *
from fastapi_poe import PoeBot
from fastapi_poe.client import stream_request
from fastapi_poe.types import PartialResponse, ProtocolMessage, QueryRequest, SettingsRequest, SettingsResponse

#functions
def is_repetitive(s,length):
    #Check if the last characters are repeats
    if len(s) < length:
        return False
    last = s[-length:]
    return last in s[:-length]
    
async def ask_mistral(request, user_input, max_length, context_lvl = 2, system_message = "") -> str:
    #ask fw-mistral-7b a question
    #remove all but the last couple of input/output pairs
    if user_input == "": user_input = request.query[-1].content
    prev_output = ""
    prev_input = ""
    prev_output1 = ""
    prev_input1 = ""
    backup_query = request.query.copy()
    mistral_query: List[ProtocolMessage] = []

    for chat in reversed(request.query):
        if chat.role == "system" and system_message == "":
            system_message = chat.content
        elif chat.role == "bot":
            if prev_output1 == "" and prev_output != "" and context_lvl > 1: prev_output1 = chat.content
            if prev_output == "" and context_lvl > 0: prev_output = chat.content
        elif chat.role == "user":
            if prev_input1 == "" and prev_output1 != "": prev_input1 = chat.content
            if prev_input == "" and prev_output != "": prev_input = chat.content
            if user_input == "": user_input = chat.content
    
    if system_message != "": mistral_query.append(ProtocolMessage(role="system",content=system_message))
    if prev_input1 != "" and prev_output1 != "":
        mistral_query.append(ProtocolMessage(role="user",content=prev_input1))
        mistral_query.append(ProtocolMessage(role="bot",content=prev_output1))
    if prev_input != "" and prev_output != "":
        mistral_query.append(ProtocolMessage(role="user",content=prev_input))
        mistral_query.append(ProtocolMessage(role="bot",content=prev_output))
    mistral_query.append(ProtocolMessage(role="user",content=user_input))
    
    request.query = mistral_query
    chunks: List[str] = []
    reply = ""
    
    async for msg in stream_request(request, "fw-mistral-7b", request.access_key):
        chunks.append(msg.text)
        reply = "".join(chunks)
        if len(reply) > max_length: break
        if is_repetitive(reply,100): break
        
    stopping_points = ["\n",'."','!"','?"',".","!","?"]    
    for stopping_point in stopping_points:
        if stopping_point in reply:
            reply = reply[:reply.rfind(stopping_point)].strip()
            break
        
    request.query = backup_query
    return reply

#classes
class BotDefinitions(PoeBot):

    async def get_response(
        self, request: QueryRequest
    ) -> AsyncIterable[PartialResponse]:

        #default settings
        chatbot = "chatgpt"
        systemprompt = SYSTEM_PROMPT
        showbot = False
        showimg = False
        mediaset = MEDIA_LIST
        memory = ""
        exclusions = []
        
        chatbots = [
            #"gpt-4",
            "claude-instant-100k",
            "claude-2-100k",
            "claude-instant",
            "chatgpt",
            "solar-0-70b",
            "fw-mistral-7b",
        ]
        
        #separate commands from prompts
        settings: List[str] = []
        for chat in request.query:
            setting = ""
            if chat.content.startswith("["):
                closebracket = chat.content.find("]")
                if closebracket < 1:
                    setting = chat.content[1:].strip()
                    chat.content = ""
                else:
                    setting = chat.content[1:closebracket].strip()
                    chat.content = chat.content[closebracket+1:].strip()
            #ignore images included in previous replies
            chat.content = re.sub('!?\[[^\]]+\]\([^\)]+\)','',chat.content).replace("\n\n\n\n","\n\n")
            settings.append(setting)
        
        #keep track if the latest command requires a bot response
        retrylatest = False
        commandreceived = False
        
        #execute commands
        for index, setting in enumerate(settings, start=0):
            retry = False
            system = False
            updmemory = False
            
            setting = setting.strip()
            settingwords = setting.split()
            if len(settingwords)==0: continue
            
            #loop through, applying commands until there are no more commands
            while len(settingwords)>0:
                currentword = settingwords[0].lower()
                
                #the "retry" or "replace" command ignores or replaces the last response
                if currentword in ["retry","replace"]:
                    if index == len(settings)-1: retrylatest = True
                    retry = True
                    settingwords.pop(0)
                    continue
                
                #the "system" command updates the system prompt
                if currentword == "system":
                    system = True
                    settingwords.pop(0)
                    continue
                
                #the "remember" command adds to the remembered facts
                if currentword == "remember":
                    updmemory = True
                    settingwords.pop(0)
                    continue
                    
                if currentword == "clearmemory":
                    memory = ""
                    settingwords.pop(0)
                    continue
                    
                #giving the name of a bot makes us use that bot instead
                if currentword == "claude": currentword = "claude-instant" 
                if currentword == "claude2": currentword = "claude-2-100k" 
                if currentword == "mistral": currentword = "fw-mistral-7b" 
                if currentword == "solar": currentword = "solar-0-70b" 
                if currentword == "claude100k": currentword = "claude-instant-100k"
                
                if currentword in chatbots:
                    chatbot = currentword
                    settingwords.pop(0)
                    continue

                chatbotupdated = False
                for chatbotname in chatbots:
                    if currentword == chatbotname.replace("-",""):
                        chatbot = chatbotname
                        chatbotupdated = True
                        break
                if chatbotupdated:
                    settingwords.pop(0)
                    continue
                
                if currentword in ["bot","showbot"]:
                    showbot = True
                    settingwords.pop(0)
                    continue
    
                if currentword == "hidebot":
                    showbot = False
                    settingwords.pop(0)
                    continue
                
                if currentword in ["img","showimg"]:
                    showimg = True
                    settingwords.pop(0)
                    continue
    
                if currentword in ["noimg","hideimg"]:
                    showimg = False
                    settingwords.pop(0)
                    continue
                
                
                if currentword == "nojpg":
                    exclusions.append("Image")
                    settingwords.pop(0)
                    continue
                    
                if currentword == "nogif":
                    exclusions.append("GIF")
                    settingwords.pop(0)
                    continue
                
                if currentword == "noaudio":
                    exclusions.append("Audio")
                    settingwords.pop(0)
                    continue
                    
                if currentword == "noexclusions":
                    exclusions = []
                    settingwords.pop(0)
                    continue

                #if currentword isn't a command, exit the loop
                break
            
            remainder = " ".join(settingwords).strip()
            if index == len(settings)-1 and setting != remainder: commandreceived = True
            
            #if retry, replace previous bot response
            if retry and request.query[index-1].role=="bot":
                if system: request.query[index-1].content = ""
                else: request.query[index-1].content = remainder
            if system: 
                if remainder != "":
                    systemprompt = remainder
                elif index == len(settings)-1:
                    yield PartialResponse(text = f"[system: {systemprompt}]")
                    return
            if updmemory:                
                if remainder != "":
                    memory = f"{memory} {remainder}."
                elif index == len(settings)-1:
                    yield PartialResponse(text = f"[memory: {memory}]")
                    return

        #check if latest entry contained only commands
        if request.query[-1].content == "" and not retrylatest and not imglatest:
            if commandreceived: yield PartialResponse(text = f"[{chatbot}] ")
            else: yield PartialResponse(text = f"[...?] ")
            return

        system_text = ""
        if showbot: system_text = f"[{chatbot}] "
        yield PartialResponse(text=system_text)

        #remove blank chat entries
        newchat: List[ProtocolMessage] = []
        for chat in request.query:
            if chat.content.strip() != "":
                newchat.append(chat)
        request.query = newchat
     
        #add a system message
        if systemprompt != "":
            sysmsgexists = False
            for chat in request.query:
                if chat.role == "system":
                    sysmsgexists = True
                    chat.content = systemprompt
            if not sysmsgexists:
                request.query.insert(0,ProtocolMessage(role="system",content=systemprompt))      
            
        #add memory to the user message before the last one
        if memory != "":
            index = 0
            for chat in reversed(request.query):
                if index > 0 and chat.role == "user":
                    chat.content = f"{chat.content} [remember: {memory}.]"
                    break
                index += 1
        
        media_type = ""
        media_prompt = ""
        media_url = ""
        media_caption = ""
        if len(mediaset) > 0:
            #filter out media items the user didn't want to seek
            if exclusions != []:
                newmediaset = []
                for option in mediaset:
                    exclude = False
                    for exclusion in exclusions:
                        if exclusion in option[0]: 
                            exclude = True
                            break
                    if exclude == False:
                        newmediaset.append(option)
                mediaset = newmediaset
            
            #randomly select a list of the remaining items
            optioncount = min(10,len(mediaset))
            mediaset = random.sample(mediaset,k=optioncount)
            
            #construct a prompt that gives the bot a choice of the selected items
            optionprompt = ""
            if len(request.query) > 1:
                paragraphs = request.query[-2].content.split("\n")     
                for paragraph in paragraphs:
                    if paragraph != "": optionprompt = f'Last reply: {paragraph}\n\n'
            
            optionprompt = f'{optionprompt}User says: "{request.query[-1].content}"\n\nPick one of the following {optioncount} options:'
            for index, option in enumerate(mediaset, start=0):
                optionprompt = f"{optionprompt}\n{index} - {option[1]}"
            
            #ask mistral to choose the best option
            print(optionprompt)
            response_text = await ask_mistral(request, optionprompt, 400, 0, CHOOSING_PROMPT)
            print(response_text) #for testing purposes
            
            #get the details of the option mistral picked
            media_index = 0
            if "0" in response_text: media_index = 0
            elif "1" in response_text: media_index = 1
            elif "2" in response_text: media_index = 2
            elif "3" in response_text: media_index = 3
            elif "4" in response_text: media_index = 4
            elif "5" in response_text: media_index = 5
            elif "6" in response_text: media_index = 6
            elif "7" in response_text: media_index = 7
            elif "8" in response_text: media_index = 8
            elif "9" in response_text: media_index = 9
            
            media_type = mediaset[media_index][0]
            media_caption = mediaset[media_index][1]
            media_prompt = mediaset[media_index][2]
            media_url = mediaset[media_index][3]
                
            #add media options to the prompt
            if request.query[-1].content != "": request.query[-1].content = f'{request.query[-1].content}\n\n[Respond normally. If possible, mention {media_prompt}.]'
            if "Image" not in media_type and "GIF" not in media_type: showimg = False
        
        #stream response from chatbot
        replace = False
        if system_text != "": yield PartialResponse(text = system_text, is_replace_response = True)
        else: replace = True
        response_chunks: List[str] = []
        response_text = ""
        if request.query[-1].content != "" or retrylatest:
            if chatbot == "fw-mistral-7b":
                response_text = await ask_mistral(request, "", 2000)
                yield PartialResponse(text = response_text, is_replace_response = replace)
            else:
                async for msg in stream_request(request, chatbot, request.access_key):
                    if msg.text != "" :
                        yield PartialResponse(text = msg.text, is_replace_response = replace)
                        response_chunks.append(msg.text)
                        replace = False
                        if msg.text.endswith(('.','?','!','"')):
                            response_text = "".join(response_chunks)
                            if is_repetitive(response_text,50):
                                #stop streaming reply if it's being repetitive
                                break
        
        linkprefix = ""
        if showimg: linkprefix = "!"
        if media_url != "":
            yield PartialResponse(text = f"{system_text}{response_text}\n\n{linkprefix}[{media_caption} ({media_type})]({media_url})", is_replace_response = True)
            
    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:

        #details about your bot
        return SettingsResponse(
            #this can list a max of 10, even if the bot only ever calls one or two
            server_bot_dependencies={
                "fw-mistral-7b":2,
                #"gpt-4":1,
                "claude-instant-100k":1,
                "claude-2-100k":1,
                "claude-instant":1,
                "chatgpt":1,
                "solar-0-70b":1,
            },
            introduction_message=INTRO_MESSAGE,
        )

#Execute
bot = BotDefinitions()
image = Image.debian_slim().pip_install_from_requirements("requirements.txt")
stub = Stub("mediabot")
@stub.function(image=image)
@asgi_app()
def fastapi_app():
    app = make_app(bot, access_key=ACCESS_KEY)
    return app
