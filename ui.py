import datetime
import json
from logging import getLogger, StreamHandler

import coloredlogs as coloredlogs
import gradio as gr

import ChatGPTAPI
import const
from tiktoken_wrapper import num_tokens_from_messages as token_sum


def app():
    logger = getLogger(__name__)
    handler = StreamHandler()
    handler.setLevel("DEBUG")
    logger.addHandler(handler)
    logger.propagate = False
    coloredlogs.install("DEBUG", logger=logger, fmt="%(asctime)s %(levelname)s     %(name)s %(message)s",
                        field_styles=const.DEFAULT_FIELD_STYLES(), level_styles=const.DEFAULT_LEVEL_STYLES())

    unconverted_visible = False
    default_converter = "あなたはこれからUserの文章を、以下のルールに従って書き換えるbotになります。\n" \
                        "*Userの文章の内容は直接書かず、必ず大量の比喩と隠喩に変換して書きます。\n" \
                        "*Userの文章の内容は会話の真ん中辺りで書きます。\n" \
                        "*Userの文章を必ず3倍以上に水増し、最低5行以上書いてください。\n*Userの文章の一人称を猫に変更してください。\n" \
                        "*Userの文章中の全ての名詞や地名に対し、創作で嘘の言葉の由来を書いてください。\n" \
                        "*全ての文章の中に「にゃん」を大量に入れてください。\n" \
                        "*全ての文章中の全ての動詞に対し、必ず擬音や効果音を大量につけて書き換えてください。\n" \
                        "*必ず文章中に無関係な情報を大量に挿入してください。\n*Userの文章の目的は変えないでください。\n" \
                        "*ソースコードは変えないでください。\n*変更した文章だけを書いてください。"

    def history_formatting(history_list: list):
        for c in history_list:
            if c[0] is not None:
                c[0] = c[0].replace("<br>", "")  # .replace("\n\n", "\n")
            if c[1] is not None:
                c[1] = c[1].replace("<br>", "")  # .replace("\n\n", "\n")

        return history_list

    def submit_msg(user_message: str, chat_history: list, original_chat_history: list):
        """
        チャットへ入力
        :param user_message: ユーザー送信文字列
        :param chat_history: 変換後チャット履歴
        :param original_chat_history: 変換前チャット履歴
        :return: 更新後インスタンス
        """
        logger.info("submit_msg")
        chat_history = history_formatting(chat_history)
        original_chat_history = history_formatting(original_chat_history)
        return "", chat_history + [[user_message, None]], original_chat_history + [[user_message, None]]

    def re_generate(chat_history: list, original_chat_history: list):
        """
        再生成
        :param chat_history: 変換後チャット履歴
        :param original_chat_history: 変換前チャット履歴
        :return: 更新後インスタンス
        """
        logger.info("re_generate")
        chat_history = history_formatting(chat_history)
        original_chat_history = history_formatting(original_chat_history)
        if len(chat_history) == 0:
            return chat_history, original_chat_history
        original_chat_history[-1][1] = None
        chat_history[-1][1] = None
        return chat_history, original_chat_history

    def history_rollback(chat_history: list, original_chat_history: list):
        """
        1会話往復を消去
        :param chat_history: 変換後チャット履歴
        :param original_chat_history: 変換前チャット履歴
        :return: 更新後インスタンス
        """
        logger.info("history_rollback")
        chat_history = history_formatting(chat_history)
        original_chat_history = history_formatting(original_chat_history)
        if len(chat_history) == 0:
            return chat_history, original_chat_history
        original_chat_history.pop(-1)
        chat_history.pop(-1)
        return chat_history, original_chat_history

    def reply_msg(chat_history: list, original_chat_history: list,
                  api_tmp: float, api_send_token: int, api_reply_token: int, api_role, api_system_msg,
                  use_converter: bool, converter_api_tmp: float, converter_api_role: str, converter_api_msg: str):
        """
        AIを用いた返信生成
        :param chat_history: 変換後チャット履歴
        :param original_chat_history: 変換前チャット履歴
        :param api_tmp: APIステータス
        :param api_send_token: APIステータス
        :param api_reply_token: APIステータス
        :param api_role: APIステータス
        :param api_system_msg: APIステータス
        :param use_converter: キャラクター変換の有無
        :param converter_api_tmp: APIステータス
        :param converter_api_role: APIステータス
        :param converter_api_msg: APIステータス
        :return: 更新後インスタンス
        """
        logger.info("reply_msg")
        chat_history = history_formatting(chat_history)
        original_chat_history = history_formatting(original_chat_history)
        if len(chat_history) == 0:
            return chat_history, original_chat_history
        bot_message = api_wrapper(original_chat_history,
                                  api_tmp, api_send_token, api_reply_token, api_role, api_system_msg)
        original_chat_history[-1][1] = bot_message
        chat_history[-1][1] = convert(bot_message,
                                      use_converter, converter_api_tmp, converter_api_role, converter_api_msg)
        return chat_history, original_chat_history

    def history_clear():
        """
        チャット履歴の削除
        :return: 更新後インスタンス
        """
        logger.info("history_clear")
        chat_history = []
        original_chat_history = []
        return chat_history, original_chat_history

    def convert(text: str, use_converter: bool, converter_api_tmp: float, converter_api_role: str,
                converter_api_msg: str):
        """
        変換適用
        :param text: 変換前文字列
        :param use_converter: キャラクター変換の有無
        :param converter_api_tmp: APIステータス
        :param converter_api_role: APIステータス
        :param converter_api_msg: APIステータス
        :return: 変換後文字列
        """
        message = [{"role": converter_api_role, "content": converter_api_msg}, {"role": "user", "content": text}]
        if use_converter:
            response = ChatGPTAPI.call_api(messages=message, temperature=converter_api_tmp,
                                           max_tokens=ChatGPTAPI.MAX_TOKEN - token_sum(message))
            text = response["choices"][0]["message"]["content"]

        return text

    def api_wrapper(original_chat_history: list,
                    api_tmp: float, api_send_token: int, api_reply_token: int, api_role: str, api_system_msg: str):
        """
        APIによる返答生成
        OpenAI以外のAPIを呼ぶ出す場合、この関数を変更する
        :param original_chat_history: 変換前チャット履歴
        :param api_tmp: APIステータス
        :param api_send_token: APIステータス
        :param api_reply_token: APIステータス
        :param api_role: APIステータス
        :param api_system_msg: APIステータス
        :return: 応答テキスト
        """
        message_token = 0
        system_message = [{"role": api_role, "content": api_system_msg}]
        message_token += token_sum(system_message)
        chat_list = []
        for c in original_chat_history:
            if c[0] is not None:
                chat_list.append({"role": "user", "content": c[0].replace("<br><br>", "").replace("\n\n", "\n")})
            if c[1] is not None:
                chat_list.append({"role": "assistant", "content": c[1].replace("<br><br>", "").replace("\n\n", "\n")})

        chat_list.reverse()
        message = []

        for c in chat_list:
            c_token = token_sum([c])
            message_token += c_token
            if api_send_token <= message_token:
                message_token -= c_token
                break
            message.append(c)

        message.reverse()
        message = system_message + message
        logger.debug(message)
        max_tokens = ChatGPTAPI.MAX_TOKEN - message_token
        if max_tokens > api_reply_token:
            max_tokens = api_reply_token
        response = ChatGPTAPI.call_api(messages=message, temperature=api_tmp,
                                       max_tokens=max_tokens)
        return response["choices"][0]["message"]["content"]

    def save_history(chat_history: list, original_chat_history: list):
        logger.info("save_history")
        with open("talk_save/talk_" + datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + ".json",
                  mode="w", encoding="utf-8") as f:
            f.write(json.dumps({"chatbot": chat_history, "original_history": original_chat_history},
                               ensure_ascii=False))

    def question_answer(question_msg: str):
        message = [{"role": "system", "content": "あなたは役に立つアシスタントです"}, {"role": "user", "content": question_msg}]

        response = ChatGPTAPI.call_api(messages=message, temperature=0.5,
                                       max_tokens=ChatGPTAPI.MAX_TOKEN - token_sum(message))

        return response["choices"][0]["message"]["content"]

    def qa_save_history(question_msg: str, answer_msg: str):
        logger.info("save_qa_history")
        with open("talk_save/qa_" + datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S") + ".json",
                  mode="w", encoding="utf-8") as f:
            f.write(json.dumps({"Q": question_msg, "A": answer_msg}, ensure_ascii=False))

    # app Design
    with gr.Blocks() as webui:
        with gr.Tab(label="Chat Bot"):
            chatbot = gr.Chatbot(label="chat")
            original_history = gr.Chatbot(label="chat_original", visible=unconverted_visible)
            msg = gr.Textbox(label="message")
            with gr.Row():
                submit = gr.Button("submit")
                regenerate = gr.Button("regenerate")
                rollback = gr.Button("rollback")
                clear = gr.Button("clear")
                save = gr.Button("save")
            with gr.Accordion("API setting"):
                with gr.Row():
                    tmp = gr.Slider(0, 2.0, value=0.5, step=0.1, interactive=True, label="tmp")
                    send_token = gr.Slider(500, 3500, value=1000, step=100, interactive=True, label="send_token")
                    reply_token = gr.Slider(500, 3500, value=1000, step=100, interactive=True, label="reply_token")
                    role = gr.Radio(["system", "assistant", "user"], value="system", label="role", interactive=True)
                system_msg = gr.Textbox(label="system message", value="あなたは役に立つアシスタントです", interactive=True)

            with gr.Accordion("Converter", open=False):
                with gr.Row():
                    enable_converter = gr.Checkbox(label="enable", value=False, interactive=True)
                    converter_tmp = gr.Slider(0, 2.0, value=1.0, step=0.1, interactive=True, label="tmp")
                    converter_role = gr.Radio(["system", "assistant", "user"], value="system",
                                              label="converter role", interactive=True)
                converter_system_msg = gr.Textbox(label="converter message",
                                                  value=default_converter, interactive=True)

        submit.click(submit_msg, [msg, chatbot, original_history], [msg, chatbot, original_history], queue=False) \
            .then(reply_msg, [chatbot, original_history, tmp, send_token, reply_token, role, system_msg,
                              enable_converter, converter_tmp, converter_role, converter_system_msg],
                  [chatbot, original_history], queue=False)
        regenerate.click(re_generate, [chatbot, original_history], [chatbot, original_history], queue=False) \
            .then(reply_msg, [chatbot, original_history, tmp, send_token, reply_token, role, system_msg,
                              enable_converter, converter_tmp, converter_role, converter_system_msg],
                  [chatbot, original_history], queue=False)
        rollback.click(history_rollback, [chatbot, original_history], [chatbot, original_history], queue=False)
        clear.click(history_clear, None, [chatbot, original_history], queue=False)
        save.click(save_history, [chatbot, original_history], None, queue=False)

        with gr.Tab(label="Q & A"):
            with gr.Row():
                question = gr.Textbox(label="question", interactive=True)
                answer = gr.Textbox(label="answer", interactive=False)
            with gr.Row():
                qa_submit = gr.Button("submit")
                qa_save = gr.Button("save")

        qa_submit.click(question_answer, question, answer, queue=False)
        qa_save.click(qa_save_history, [question, answer], None, queue=False)
    webui.launch(inbrowser=True, server_port=3776)
