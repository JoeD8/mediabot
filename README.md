# mediabot
A Poe server bot that selects from a preconfigured list of images, gifs, and audios to incorporate those into the chat

Follow the instructions at https://developer.poe.com/server-bots/quick-start, installing Python and getting set up with a Modal account.

Put the mediabot.py, requirements.txt, and media_links.py in a directory you're able to run python scripts in.
Run "modal deploy mediabot.py" to get it up and running on Modal.
Go to modal and get the server URL (should be like https://username--mediabot-fastapi-app.modal.run)
On Poe set up a new bot and choose the Use server option, entering the server URL.
Copy the Access key from the bot setup page and paste it into media_links.py, save it and run "modal deploy media.py" again
Save your bot. Run the following command:
Invoke-RestMethod -Method 'Post' -Uri https://api.poe.com/bot/fetch_settings/BOT_NAME/ACCESS_KEY

Update media_links with the images, gifs, audios, videos, or whatever other URLs you want your bot to randomly spit out.
Configure a system prompt, intro message, choosing prompt
Every time you make changes and save them, run
modal deploy media.py
then
Invoke-RestMethod -Method 'Post' -Uri https://api.poe.com/bot/fetch_settings/BOT_NAME/ACCESS_KEY

Backup your work regularly in case things break.
