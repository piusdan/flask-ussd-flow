# -*- coding: utf-8 -*-
import json
import logging
import os
import re
import sys
from functools import wraps
from threading import Thread

from jinja2 import FileSystemLoader, Environment

try:
    from flask_script import Manager
except ImportError:
    Manager = None

import requests
from flask import current_app, copy_current_request_context

ch = logging.StreamHandler()

ussd_logger = logging.getLogger(__name__)

ussd_logger.setLevel(logging.DEBUG)
ussd_logger.addHandler(ch)

__author__ = 'npiusdan@gmail.com'
__version__ = '0.0.1'


class USSDFlowException(Exception):
    pass


class USSDFlowConfig(object):
    _screen_types = dict(confirmation_screen='confirmation_screen',
                         input_screen='input_screen',
                         info_screen='info_screen',
                         intial_screen='intial_screen'
                         )

    screen_validation_types = dict(
        regex='regex',
        list='list'
    )

    screen_callback_types = dict(
        function="func",
        http="http"
    )

    screen_callback_execution = dict(
        asynchronous="async"
    )

    @classmethod
    def screen_types(cls):
        return tuple(cls._screen_types.keys())

    @classmethod
    def ussd_string_map(cls):
        _map = {}
        for value in cls._screen_types.values():
            _map[value] = 'CON' if value != cls._screen_types['info_screen'] else 'END'
        return _map


def _build_screens_path(app, ussd_template_folder=''):
    base_template_path = os.path.join(app.root, 'templates', ussd_template_folder, 'screens.json')
    if os.path.isfile(base_template_path):
        return base_template_path
    raise USSDFlowException(
        "Could not find your screen definitions file, please include your"
        " screens.json file under your templates directory"
    )


def _filter_screen_by_name(all_screens: dict, screen_name: str, user_input: str) -> dict:
    """Looks up and returns the specific screen specified by the screen_name parameter,
    from a dictionary conatinng containing all screen definitions
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
        raise USSDFlowException("Screen not found")


def _render_screen(screen: dict, retry=False) -> str:
    """Given a screen it converts the screen into a format that can be accepted by the USSD callback
    :param screen: USSD screen to be rendered
    :param retry: If true the renderer will try to render the same screen by with a special retry message
    :return:
    """

    if screen.get('type', None) not in USSDFlowConfig.screen_types():
        raise USSDFlowException('Screen Type not supported')
    if retry:
        screen_message = screen.get('retry_message') or screen['data']
    else:
        screen_message = screen['data']
    return ' '.join((USSDFlowConfig.ussd_string_map()[screen['type']], screen_message))


def _validate_input(screen, user_input):
    validation = screen.get("validation", None)
    if validation is None:
        return None
    validation_type = validation['type']
    if validation_type == USSDFlowConfig.screen_validation_types['regex']:
        pattern = re.compile(r'{}'.format(validation['value']))
        return bool(pattern.match(user_input))
    if validation_type == USSDFlowConfig.screen_validation_types['list']:
        return user_input in validation['value']


class USSDFlow():
    """This class is used to control the USSD integration to one
    or more Flask applications.  Depending on how you initialize the
    object it is usable right away or will attach as needed to a
    Flask application.
    There are two usage modes which work very similarly.  One is binding
    the instance to a very specific Flask application::
        app = Flask(__name__)
        ussd = USSDFlow(app)

    The second possibility is to create the object once and configure the
    application later to support it::
        ussd = USSDFlow()
        def create_app():
            app = Flask(__name__)
            ussd.init_app(app)
            return app
    """

    def __init__(self, app=None, function_registry=None):
        self.app = app
        self.function_registry = function_registry
        self.screens_file = None

        if self.function_registry is None:
            self.function_registry = {}

        if app is not None:
            self.init_app(app, function_registry)

    def init_app(self, app, function_registry):
        """This callback can be used to initialize an application for the
        use with the ussd definitions

        :param function_registry: key, value mapping of all functions specified as callbacks in the
        USSD definitions file
        """

        app.ussd_flow = self
        self.function_registry = function_registry

        USSD_TEMPLATES_FOLDER = current_app.config.get('USSD_TEMPLATES_FOLDER', '')
        self.screens_file = _build_screens_path(self.app, USSD_TEMPLATES_FOLDER)

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

    def get_screens_definitions(self, flow_name='main'):
        """Given a ussd flow name this function builds a dictionary list of all screens under the flow
        """
        with open(self.screens_file) as f:
            parsed_screen_defs = json.load(f)
            current_flow = parsed_screen_defs["flows"][flow_name]
            screen_definitions = current_flow['screens']
            return screen_definitions

    def get_state(self, screens_definitions, user_inputs, delimeter='*', initial_screen='initial_screen'):
        """Based on user inputs this function determines the current state of the USSD session

        This is a transition function of a finite State Machine that operates the USSD application
        :param screens_definitions: contains a list of screen definition where each screen definition represents a screen which is a state of the FSM
        :param user_inputs the input set,
        * Every state(screen_defination) in the ``screens_definitions`` as regex or list of accepted alphabets
        :param initial_screen: The initial state is a screen named
        * The final state is a screen named ``info_screen``

        """

        input_stack = user_inputs.split(delimeter)
        input_stack.reverse()

        # set the FSM to start state
        current_state = _filter_screen_by_name(screens_definitions, initial_screen, '')
        previous_state = None

        if user_inputs == '':
            return previous_state, current_state

        while len(input_stack) > 0:
            _input = input_stack.pop()

            if _validate_input(current_state, _input):

                screen_name = current_state.get('next_screen') or current_state.get('go_to', '')

                if len(screen_name.split('.')) > 1:
                    flow_name, screen_name = screen_name.split('.')
                    screens_definitions = self.get_screens_definitions(flow_name)

                if current_state.get("mappings") is None:
                    screen_name = screen_name.format(user_response=_input)
                else:
                    screen_name = screen_name.format(user_response=current_state["mappings"].get(_input, ''))

                if screen_name == '':
                    raise USSDFlowException('Invalid schema')

                previous_state, current_state = current_state, _filter_screen_by_name(screens_definitions, screen_name,
                                                                                      _input)

                while current_state.get('go_to', None) is not None:
                    screen_name = current_state['go_to']
                    # check for change of flows
                    if len(screen_name.split('.')) > 1:
                        current_app.logger.debug("changing flow with {}".format(screen_name))
                        flow_name, screen_name = screen_name.split('.')
                        screens_definitions = self.get_screens_definitions(flow_name)
                    current_state = _filter_screen_by_name(screens_definitions, screen_name, _input)

                continue

            else:
                current_state_supports_retries = current_state.get('retry', False)

                if current_state_supports_retries:
                    # continue iteration, don't do anything
                    continue
                else:
                    # if screen defiantion does not allows apps to retry sending the screen
                    # fallback to the initial screen and continue iteration
                    screen_name = 'initial_screen'
                    current_state = _filter_screen_by_name(screens_definitions, screen_name, '')
                    continue

        return previous_state, current_state

    def execute_callback(self, sessionId: str, phone_number: str, user_input: str, screen: dict):
        """Execute the required logic after the USSD screens
        Supports both http based or function based callback
        Given a user input the function generates a payload
            dict(sessionId=sessionId, user_response=user_input, phone_number=phone_number)
        If the callback is a function the payload is passed to the function as a keyword argument
        If the callback if http the payload is dumped to json a post to the given endpoint

        The function also supports asynchronous and synchronous execution type that can be set using the ``mode``
        key in the screens definitions file
        """

        app = self.get_app()

        input_is_not_valid = not _validate_input(screen, user_input)

        callback = screen.get('callback', None)
        if callback is None or input_is_not_valid:
            ussd_logger.debug('Input not valid, skipping callback')
            return None

        if screen.get("mappings", None) is not None:
            user_input = screen["mappings"][user_input]

        kwargs = dict(sessionId=sessionId, user_input=user_input, phone_number=phone_number, callback=callback)
        is_callback_mode_async = (callback.get('mode') == USSDFlowConfig.screen_callback_execution['asynchronous'])

        @copy_current_request_context
        def _execute_callback(callback, sessionId, phone_number, user_input):
            kwargs = dict(sessionId=sessionId, user_response=user_input, phone_number=phone_number)

            is_callback_function = (callback.get("type") == USSDFlowConfig.screen_callback_types['function'])
            is_callback_http = (callback.get("type") == USSDFlowConfig.screen_callback_types['http'])
            if is_callback_function:
                if callback["name"] not in self.function_registry.keys():
                    return USSDFlowException("Couldn't find callback in function registry")
                else:
                    return self.function_registry[callback["name"]](**kwargs)

            if is_callback_http:
                try:
                    return requests.post(callback["name"], data=json.dumps(kwargs), timeout=3)
                except requests.exceptions.Timeout as exc:
                    raise USSDFlowException('Unable to reach the provided callback')

            else:
                return USSDFlowException("Edge case exception")

        with app.app_context():
            if is_callback_mode_async:
                thr = Thread(target=_execute_callback, kwargs=kwargs)
                thr.start()
                return thr
            else:
                return _execute_callback(**kwargs)


def catch_errors(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        try:
            f(*args, **kwargs)
        except (RuntimeError) as exc:
            ussd_logger.error('Error: ' + str(exc))
            sys.exit(1)

    return wrapped


if Manager is not None:
    USSDCommand = Manager(usage='Perform USSDFlow operations')
else:
    class FakeCommand(object):
        def option(self, *args, **kwargs):
            def decorator(f):
                return f

            return decorator


    USSDCommand = FakeCommand()


@catch_errors
def generate_screens(directory):
    """Generates ussd screens
    :return:
    """
    ussd_template_folder = directory or current_app.config.get('USSD_TEMPLATES_FOLDER', '')
    kwargs = {}
    try:
        env = Environment(loader=FileSystemLoader(ussd_template_folder))
        ussd_screens_file_path = os.path.join(ussd_template_folder, 'screens.json')
        template = env.get_template('screens.j2')
        template.stream(**kwargs).dump(ussd_screens_file_path)

    except Exception as exc:
        raise RuntimeError(str(exc))
