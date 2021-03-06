import logging

from qpid.messaging import Connection
from qpid.messaging.exceptions import ConnectionError, MessagingError

from pulp.common.compat import json
from pulp.server.compat import json_util
from pulp.server.config import config


class TopicPublishManager(object):
    BASE_SUBJECT = 'pulp.server'
    EXCHANGE = config.get('messaging', 'topic_exchange')

    _connection = None
    _logged_disabled = False
    _logger = logging.getLogger(__name__)

    @classmethod
    def _disabled_message(cls):
        """
        Only write a log message once to say that messaging is disabled, because
        otherwise this could be very noisy.
        """
        if not cls._logged_disabled:
            cls._logger.debug(
                'remote messaging is disabled because no server was specified')
            cls._logged_disabled = True

    @classmethod
    def connection(cls):
        """
        :return:    An open connection object if available, or else None.
        :rtype:     qpid.messaging.Connection
        """
        if not cls._connection:
            address = config.get('messaging', 'url')
            if not address:
                cls._disabled_message()
                return
            cls._connection = Connection(address, reconnect=True)
            try:
                cls._connection.open()
            except ConnectionError:
                # log the error, but allow life to go on.
                cls._logger.exception(
                    'could not connect to messaging server %s' % address)
                return

        return cls._connection

    @classmethod
    def publish(cls, event, exchange=None):
        """
        Publish an event to a remote exchange. This sends the JSON-serialized
        version of the output from the event's "data" method as the content
        of the message.

        Failures to publish a message will be logged but will not prevent
        execution from continuing.

        :param event: the event that should be published to a remote exchange
        :type  event: pulp.server.event.data.Event

        :param exchange: optional name of an exchange to use. This will override
                         whatever is setup in the server config.
        :type  exchange: str
        """
        connection = cls.connection()
        if connection:
            subject = '%s.%s' % (cls.BASE_SUBJECT, event.event_type)
            destination = (
                '%s/%s; {create:always, node:{type:topic}, link:{x-declare:{auto-delete:True}}}' % (
                    exchange or cls.EXCHANGE, subject))

            data = json.dumps(event.data(), default=json_util.default)
            try:
                cls.connection().session().sender(destination).send(data)
            except MessagingError, e:
                # log the error, but allow life to go on.
                cls._logger.exception('could not publish message: %s' % str(e))
