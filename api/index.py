"""
template from: https://gist.github.com/mdonkers/63e115cc0c79b4f6b8b3a6b797e485c7
License: MIT License
Copyright (c) 2023 Miel Donkers
Very simple HTTP server in python for logging requests
Usage::
    ./server.py [<port>]
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import json
from typing import Any
from dotenv import load_dotenv
import os
import requests
from datetime import datetime

load_dotenv()

BOT_URL = f"https://api.telegram.org/bot{os.getenv('BOT_TOKEN')}"
WEBSITE_URL = os.getenv('WEBSITE_URL')
WEBAPP_URL = os.getenv('WEBAPP_URL')

client_chat_id = ""
current_command = ""


class handler(BaseHTTPRequestHandler):

    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        logging.info("GET request,\nPath: %s\nHeaders:\n%s\n", str(self.path),
                     str(self.headers))
        self._set_response()
        self.wfile.write(
            "<p style='text-color: red; '>this is the server for devpandaz next voting app bot</p><a href='https://t.me/next_voting_app_bot'>use the bot</a>"
            .encode('utf-8'))
        # self.wfile.write("GET request for {}".format(
        # self.path).encode('utf-8'))

    def reply_user(self, data: dict[str, Any]):
        global client_chat_id
        return requests.post(f'{BOT_URL}/sendMessage',
                             json={
                                 "chat_id": client_chat_id,
                                 **data,
                             }).json()

    def do_POST(self):
        global current_command, client_chat_id, jian_kai_memes_photo_id

        content_length = int(
            self.headers['Content-Length'])  # <--- Gets the size of data
        post_data = self.rfile.read(
            content_length)  # <--- Gets the data itself
        # logging.info("POST request,\nPath: %s\nHeaders:\n%s\n\nBody:\n%s\n",
        #              str(self.path), str(self.headers),
        #              post_data.decode('utf-8'))

        self._set_response()
        self.wfile.write("POST request for {}".format(
            self.path).encode('utf-8'))

        # jsonify the incoming data
        data = json.loads(post_data.decode('utf-8'))
        print(json.dumps(data, indent=4))

        # if a message is received
        if "message" in data:
            client_chat_id = data['message']['chat']['id']

            received = data['message']
            if "text" in received:
                try:
                    # checking if it's a bot command
                    if received['entities'][0]['type'] == "bot_command":

                        # removing the '/' in front, and removing the @ received from groups, if got
                        user_command = received['text'][1:].replace(
                            "@devpandaz_telegram_bot", "")

                        # start
                        if user_command == "start":
                            self.reply_user({
                                "text":
                                f"Hello! Get started by pressing <a href='{WEBAPP_URL}'>Open Feed</a>",
                                "parse_mode": "HTML",
                            })
                            return

                        # not a valid bot command (doesn't match any command above)
                        # self.reply_user({
                        #     "text":
                        #     "Invalid command. Refer to the list of commands by pressing the menu button. "
                        # })

                # not a bot command, just some random text
                except KeyError:
                    pass
                    # self.reply_user(
                    #     {"text": "Hello! Get started by pressing Open Feed. "})

        if "inline_query" in data:
            inline_query = data['inline_query']
            if inline_query['query'] == "":
                return

            # fetch data using api
            res = requests.post(f'{WEBSITE_URL}/api/questions',
                                json={
                                    "lastQuestionId": "",
                                    "searchQuery": inline_query['query'].replace(" ", " & ")
                                }).json()
            print(res)
            questionSearchResults = res['questions']
            queryResults = []
            for question in questionSearchResults:
                if len(queryResults) < 10:

                    # fetch question data
                    questionData = requests.post(f"{WEBSITE_URL}/api/questions/{question['id']}", json={
                        "uid": str(inline_query['from']['id']), # this means the user needs to open the web app for the first time so that it can sign up automatically (add user to database) (add-or-update-user) before the user can use bot inline query feature lmao, bcos i need to fetch the question with the api, and it needs the uid lol, altho i just need the public details
                        }).json()['question']

                    questionPostedData = datetime.strptime(questionData['timePublished'][:10], "%Y-%m-%d").astimezone()

                    queryResults.append({
                        "type": "article",
                        "title": question['questionText'],
                        "id": question['id'],
                        "input_message_content": {
                            "message_text":
                            f"<b>{question['questionText']}</b> on Next Voting App\n\nPosted on {questionPostedData.strftime('%Y/%m/%d')}",
                            "parse_mode": "HTML",
                        },
                        # for now the vercel blob image link cant display directly in a browser, instead it downloads
                        # so i think this is an issue for telegram webview (error: switch_webview_url_invalid)
                        # but the vercel blob team says they are working on this directly view feature
                        # so lets wait lmao

                        # "thumbnail_url": question['imageURL'],
                        # "thumbnail_url": "https://placehold.co/600x400/000000/FFFFFF.png",
                        # "thumbnail_width": 800,
                        # "thumbnail_height": 800,
                        # "url": f"{WEBAPP_URL}?startapp={question['id']}",
                        "reply_markup": {
                            "inline_keyboard": [[{
                                "text":
                                f"Open {question['questionText']}",
                                "url":
                                f"{WEBAPP_URL}?startapp={question['id']}",
                            }]]
                        },
                    })
                else: 
                    break

            print(queryResults)

            answer_inline_query_res = requests.post(f'{BOT_URL}/answerInlineQuery',
                                json={
                                    "inline_query_id": inline_query["id"],
                                    "results": queryResults,
                                    "cache_time": 1000,
                                    "button": {
                                        "text":
                                        "Open complete search results in web app",
                                        "web_app": {
                                            "url": f"{WEBSITE_URL}/feed?q={inline_query['query']}",
                                            },
                                    }
                                }).json()

            print(answer_inline_query_res)


def run(server_class=HTTPServer, handler_class=handler, port=8080):
    logging.basicConfig(level=logging.INFO)
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info('Starting httpd...\n')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info('Stopping httpd...\n')


if __name__ == '__main__':
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()
