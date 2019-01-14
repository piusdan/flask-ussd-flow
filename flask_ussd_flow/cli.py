import click

from flask.cli import with_appcontext

from . import generate_screens as _generate_screens


@click.group()
def ussd():
    """Perform all USSD related operations"""
    pass


@ussd.commad()
@with_appcontext
def generate_screens():
    """Generates ussd screens
    :return:
    """

    _generate_screens()
