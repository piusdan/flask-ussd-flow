import json
import logging
import os
import re
from threading import Thread

import requests
from flask import current_app, copy_current_request_context

ch = logging.StreamHandler()

ussd_logger = logging.getLogger(__name__)

ussd_logger.setLevel(logging.DEBUG)
ussd_logger.addHandler(ch)


class USSDException(Exception):
    pass


def manage_flows():
    pass


class Callback:
    """
    Manage allowed callback types
    """
    function = "func"
    http = "http"
    asynchronous = "async"


class ScreenValidationTypes:
    regex = 'regex'
    list = 'list'


class USSDFlow():
    confirmation_screen = 'confirmation_screen'
    input_screen = 'input_screen'
    info_screen = 'info_screen'
    intial_screen = 'intial_screen'

    @classmethod
    def types(cls):
        return cls.confirmation_screen, cls.input_screen, cls.info_screen,

    def __init__(self, app=None, function_registry=None):
        self.app = app
        self.function_registry = None
        self.screens_file = None

        if function_registry is None:
            function_registry = {}

        if app is not None:
            self.init_app(app, function_registry)

    def init_app(self, app, function_registry):
        app.ussd_flow = self
        self.function_registry = function_registry

        try:
            self.screens_file = os.path.join(app.config['USSD_TEMPLATES_FOLDER'], 'screens.json')
        except KeyError as exc:
            raise USSDException(
                "Could not find USSD screens defination, did you specify USSD_TEMPLATES_FOLDER in your configuration")

    @classmethod
    def connection_string(cls):
        return {cls.input_screen: 'CON', cls.info_screen: 'END', cls.confirmation_screen: 'CON'}

    @staticmethod
    def locate_screens(folder_path):
        return os.path.join(folder_path, 'screens.json')

    @staticmethod
    def filter_screen_by_name(all_screens, screen_name, user_input):
        """
        Given a screen name it tries to find a screen by the name
        Raises an Exception if no screen by the name can be found
        :param all_screens:
        :param screen_name:
        :param user_input:
        :return:
        """
        screen_name = screen_name.format(user_response=user_input)
        try:
            screen = list(filter(lambda screen: screen.get('name') == screen_name, all_screens))[0]
            return screen
        except IndexError as exc:
            raise USSDException("Screen not found")

    @staticmethod
    def input_is_valid(screen, user_input):
        validation = screen.get("validation", None)
        if validation is None:
            return True
        validation_type = validation['type']
        if validation_type == ScreenValidationTypes.regex:
            # validate user input
            pattern = re.compile(r'{}'.format(validation['value']))

            # if pattern doesn't match and the screen supports retries
            # resend the screen again
            return pattern.match(user_input) or False

        if validation_type == ScreenValidationTypes.list:
            return user_input in validation['value']

    def get_app(self, reference_app=None):
        """Helper method that implements the logic to look up an
                application."""

        if reference_app is not None:
            return reference_app

        if current_app:
            return current_app._get_current_object()

        if self.app is not None:
            return self.app

        raise RuntimeError(
            'No application found. Either work inside a view function or push'
            ' an application context.'
        )

    def get_screens(self, flow_name='main'):
        """
        Gets screen definations for a given flow, if no flow name is specified it defaults to the main flow

        It tries to get a a given flow, if no flow exists in the USSD definations
        It tries to get the screens specified withouth a flow
        if fails with a USSDFlow exception if no screens are found
        :param flow_name:
        :return:
        :raises USSDException:
        """

        try:
            with open(self.screens_file) as f:
                screens = json.load(f)
                # app.logger.debug("screens: {}".format(screens))
                try:
                    flow = screens["flows"][flow_name]
                    _screens = flow['screens']
                except IndexError as exc:
                    _screens = screens.get('screens', None)
                    if _screens is None: raise USSDException('Invalid schema')

                finally:
                    return _screens

        except FileNotFoundError as exc:
            raise USSDException('Looks like you have not specified a screens file')

    def get_screen(self, all_screens, user_inputs, delimeter='*'):
        """
        Parse the provided screens to get users location
        :param screens: All screens to be parsed
        :param screen_name:
        :param user_inputs: A list of USSD inputs delimeted by the delimeter parameter
        :param delimeter:
        :return:
        """
        user_inputs_stack = user_inputs.split(delimeter)
        user_inputs_stack.reverse()

        ussd_logger.debug('stack is {}'.format(user_inputs_stack))

        screen = self.filter_screen_by_name(all_screens, 'initial_screen', '')
        prev_screen = None

        if user_inputs == '':
            ussd_logger.debug('user input is None getting initial screen')
            return prev_screen, screen

        while len(user_inputs_stack) > 0:
            user_input = user_inputs_stack.pop()
            ussd_logger.debug('user input is {}'.format(user_input))

            if self.input_is_valid(screen, user_input):
                ussd_logger.debug(
                    'Match found for validator {} with input {}'.format(screen.get('validation'), user_input))
                # go to the next screen

                screen_name = screen.get('next_screen') or screen.get('go_to', '')
                # check for change of flows
                if len(screen_name.split('.')) > 1:
                    current_app.logger.debug("changing flow with {}".format(screen_name))
                    flow_name, screen_name = screen_name.split('.')
                    all_screens = self.get_screens(flow_name)

                if screen.get("mappings") is None:
                    screen_name = screen_name.format(user_response=user_input)
                else:
                    screen_name = screen_name.format(user_response=screen["mappings"].get(user_input, ''))

                if screen_name == '':
                    raise USSDException('Invalid schema')

                prev_screen = screen
                screen = self.filter_screen_by_name(all_screens, screen_name, user_input)

                while screen.get('go_to', None) is not None:
                    screen_name = screen['go_to']
                    # check for change of flows
                    if len(screen_name.split('.')) > 1:
                        current_app.logger.debug("changing flow with {}".format(screen_name))
                        flow_name, screen_name = screen_name.split('.')
                        all_screens = self.get_screens(flow_name)
                    screen = self.filter_screen_by_name(all_screens, screen_name, user_input)

                ussd_logger.debug('found screen {}'.format(screen))
                ussd_logger.debug('Stack not empty contuning loop')
                continue

            else:
                ussd_logger.debug(
                    'Match not found for validator {} with input {}'.format(screen.get('validation'), user_input))
                screen_supports_retries = screen.get('retry', False)

                if screen_supports_retries:
                    # continue iteration, don't do anything
                    ussd_logger.debug('Input not found and this screen supports retries, retry')
                    continue
                else:
                    # if screen defiantion does not allows apps to retry sending the screen
                    # fallback to the intial screen and continue iteration
                    ussd_logger.debug('Input not found and this screen does not support retries, go to first screen')
                    screen_name = 'initial_screen'
                    screen = self.filter_screen_by_name(all_screens, screen_name, '')
                    continue

        return prev_screen, screen

    def execute_callback(self, sessionId: str, phoneNumber: str, user_input: str, screen: dict):

        app = self.get_app()

        input_is_not_valid = not self.input_is_valid(screen, user_input)

        callback = screen.get('callback', None)
        if callback is None or input_is_not_valid:
            ussd_logger.debug('Input not valid, skipping callback')
            return None

        if screen.get("mappings", None) is not None:
            user_input = screen["mappings"][user_input]

        kwargs = dict(sessionId=sessionId, user_input=user_input, phoneNumber=phoneNumber, callback=callback)
        is_callback_mode_async = (callback.get('mode') == Callback.asynchronous)

        @copy_current_request_context
        def _execute_callback(callback, sessionId, phoneNumber, user_input):
            kwargs = dict(sessionId=sessionId, user_response=user_input, phoneNumber=phoneNumber)

            is_callback_function = (callback.get("type") == Callback.function)
            is_callback_http = (callback.get("type") == Callback.http)
            if is_callback_function:
                if callback["name"] not in self.function_registry.keys():
                    return USSDException("Couldn't find callback in function registry")
                else:
                    return self.function_registry[callback["name"]](**kwargs)

            if is_callback_http:
                try:
                    return requests.post(callback["name"], data=json.dumps(kwargs), timeout=3)
                except requests.exceptions.Timeout as exc:
                    raise USSDException('Unable to reach the provided callback')

            else:
                return USSDException("Edge case exception")

        with app.app_context():
            if is_callback_mode_async:
                thr = Thread(target=_execute_callback, kwargs=kwargs)
                thr.start()
                return thr
            else:
                return _execute_callback(**kwargs)

    def render(self, screen: dict, retry=False) -> str:
        """Given a screen it converts the screen into a format that can be accepted by the USSD callback
        :param screen: USSD screen to be rendered
        :param retry: If true the renderer will try to render the same screen by with a special retry message
        :return:
        """

        if screen.get('type', None) not in self.types():
            raise USSDException('Screen Type not supported')
        if retry:
            screen_message = screen.get('retry_message') or screen['data']
        else:
            screen_message = screen['data']
        return ' '.join((self.connection_string()[screen['type']], screen_message))
