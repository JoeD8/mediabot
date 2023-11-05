ACCESS_KEY = "Get_from_bot_setup_page"

SYSTEM_PROMPT = "This is where your bot system prompt goes"

INTRO_MESSAGE = "This is the thing your bot says when you start a new chat. It can include inline images in the format ![Image description](image url)."

CHOOSING_PROMPT = "You are a bot tasked with choosing imagery for the next reply (a different bot is in charge of writing the response). Pick a number from 0 to 9."

MEDIA_LIST = [
    ["GIF","Description the user sees","Prompt for the language bot","GIF url"],
    ["GIF","Description the user sees","Prompt for the language bot","GIF url"],
    ["Image","Description the user sees","Prompt for the language bot","Image url"],
    ["Image","Description the user sees","Prompt for the language bot","Image url"],
    ["Audio","Description the user sees","Prompt for the language bot","Audio url"],
    ["Audio","Description the user sees","Prompt for the language bot","Audio url"],
    #You can configure as many GIFs, Images, and Audios as you want. I guess you could aslo have Video items or other things, they just need a URL.
]
