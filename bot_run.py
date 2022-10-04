import runpy
import sys
import traceback
import telebot
import getpass
import logging
from zipfile import ZipFile
from contexmock import MockStdin, MockStdout
from multiprocessing import Process
from queue import Queue


class RunScriptBot:
    """
    This is the class for running scripts on Python via TeleBot.

    :param token: token for TeleBot
    :type token: object: 'str'
    """

    __slots__ = (
        "__bot",
        "__mock_in",
        "__mock_out",
        "__is_running_script",
        "__client_id_running",
        "__message_queue"
    )

    def __init__(self, token: str):
        self.__mock_in = MockStdin()
        self.__mock_out = MockStdout()
        self.__bot = telebot.TeleBot(token)
        self.__is_running_script = False
        self.__client_id_running = None
        self.__message_queue = Queue()

        @self.__bot.message_handler(commands=['start'])
        def start(message):
            self.__start_command(message)

        @self.__bot.message_handler(content_types=["text"])
        def receive(message):
            self.__receive_message(message)

    def __receive_message(self, message: telebot.types.Message):
        """
        Checks if the bot is available, if not - puts a message to queue

        :param message: message object from Telebot
        :type message: telebot.types.Message

        :return: None
        """

        if not self.__is_running_script and self.__message_queue.empty():
            self.__run_script(message)
        elif self.__client_id_running == message.from_user.id:
            self.__sent_input(message)
        else:
            # TODO: make sure not to lose messages from another clients while running
            self.__message_queue.put(message)

    def __start_command(self, message: telebot.types.Message):
        """
        Handles behavior when start button is pressed

        :param message: message object from Telebot
        :type message: telebot.types.Message

        :return: None
        """

        mess = "Hello! I can run some scripts on Python\n" \
               "Just send me your code as a message"
        self.__bot.send_message(message.from_user.id, mess)

    def __run_script(self, message: telebot.types.Message):
        """
        Creates a child process which runs the script,
        meanwhile sends script's output to the client

        :param message: message object from Telebot
        :type message: telebot.types.Message

        :return: None
        """

        self.__is_running_script = True
        self.__client_id_running = message.from_user.id

        client_file = f'{message.from_user.id}.py'
        with open(client_file, "w+") as client_source:
            client_source.write(f'{message.text}\n')

        # TODO: start ones instead of on each received message
        run_script_proc = Process(target=child,
                                  args=(
                                      self.__mock_in,
                                      self.__mock_out,
                                      client_file))
        run_script_proc.start()

        to_send = self.__mock_out.read_output()
        while to_send != client_file:
            try:
                self.__bot.send_message(message.from_user.id, to_send)
            except telebot.apihelper.ApiTelegramException:
                logging.warning(f"No output in {message.from_user.id}'s script")
            to_send = self.__mock_out.read_output()

        run_script_proc.join()
        self.__client_id_running = None
        self.__is_running_script = False

    def __sent_input(self, message: telebot.types.Message):
        """
        Sends client's input for the script to the child process

        :param message: message object from Telebot
        :type message: telebot.types.Message

        :return: None
        """

        self.__mock_in.write_input(message.text)

    def run(self):
        """
        Calls Telebot.polling()

        :return: None
        """

        self.__bot.polling()


def child(mock_in: MockStdin, mock_out: MockStdout, client_file: str):
    mock_out.real_stdout = sys.stdout
    mock_in.real_stdin = sys.stdin
    # TODO: optimise output
    with mock_out:
        with mock_in:
            try:
                runpy.run_path(client_file)
            except Exception:
                traceback_info = traceback.format_exc().split('\n')
                line = trace_number = 0
                for trace_number, trace in enumerate(traceback_info):
                    if f'File "{client_file}"' in trace:
                        error_line = trace.split()
                        line = error_line[error_line.index("line") + 1]
                        if not line[-1].isdigit():
                            line = line.replace(line[-1], "")
                        break
                print(f'Line {line}:')
                for trace in traceback_info[trace_number + 1:]:
                    print(trace)
            finally:
                print(client_file)


def main():
    level = logging.DEBUG
    log_format = "[%(levelname)s] - %(message)s"
    logging.basicConfig(level=level, format=log_format)
    logging.getLogger("urllib3.connectionpool").disabled = True

    token_zip = "token.zip"
    token_txt = "token.txt"

    while True:
        password = getpass.getpass(prompt="Enter password to launch the bot:")
        try:
            with ZipFile(token_zip) as token_archive:
                token_archive.setpassword(bytes(password, "utf-8"))
                token = token_archive.read(token_txt).decode("utf-8")
                break
        except RuntimeError:
            print("Wrong password. Please try again")

    bot = RunScriptBot(str(token))
    bot.run()


if __name__ == "__main__":
    main()
