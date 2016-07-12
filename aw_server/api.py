from typing import List, Dict
from datetime import datetime
import binascii
import os

from flask import request
from flask_restful import Resource, Api

from . import app, logger


# SECURITY
# As we work our way through features, disable (while this is False, we should only accept connections from localhost)
SECURITY_ENABLED = False

# For the planned zeroknowledge storage feature
ZEROKNOWLEDGE_ENABLED = False


api = Api(app)

# FIXME: This should probably be scrapped, just something I threw together trying to reason about stuff
class SessionManager:
    # TODO: Don't rely on in-memory session storage
    def __init__(self):
        self._sessions = {}

    # SECURITY
    def start_session(self, session_id: str) -> str:
        # Returns a session key to be used in all following requests in session
        session_key = binascii.hexlify(os.urandom(24)).decode("utf8")
        self._sessions[session_id] = {
            "session_key": session_key
        }
        return session_key

    # SECURITY
    # TODO: Implement session closing
    def stop_session(self):
        pass

    # SECURITY
    def verify_session(self, session_id, session_key):
        # session_id is public, session_key is secret
        if SECURITY_ENABLED:
            if session_id not in self._sessions:
                return False

            session = self._sessions[session_id]
            return session["session_key"] == session_key
        else:
            return True


session_manager = SessionManager()


# Use the following for authentication using user roles:
#   http://flask.pocoo.org/snippets/98/

@api.resource("/api/0/session/<string:session_id>/start")
class StartSessionResource(Resource):
    def post(self, session_id):
        data = request.get_json()
        session_key = session_manager.start_session(session_id)
        return {"session_key": session_key}


@api.resource("/api/0/session/<string:session_id>/stop")
class StopSessionResource(Resource):
    def post(self, session_id):
        data = request.get_json()
        pass


@api.resource("/api/0/buckets/<string:bucket_id>")
class BucketResource(Resource):
    """
    Used to get metadata about buckets and create them.
    """

    def get(self, bucket_id):
        logger.debug("Received get request for bucket '{}'".format(bucket_id))
        return app.db[bucket_id].metadata()

    def post(self, bucket_id):
        # TODO: Implement bucket creation
        raise NotImplementedError


@api.resource("/api/0/buckets/<string:bucket_id>/events")
class EventResource(Resource):
    """
    Used to get and create events in a particular bucket.
    """

    def get(self, bucket_id):
        logger.debug("Received get request for events in bucket '{}'".format(bucket_id))
        return app.db[bucket_id].get()

    def post(self, bucket_id):
        logger.debug("Received post request for event in bucket '{}' and data: {}".format(bucket_id, request.get_json()))
        data = request.get_json()
        if isinstance(data, dict):
            app.db[bucket_id].insert(data)
        elif isinstance(data, list):
            for event in data:
                app.db[bucket_id].insert(event)
        else:
            logger.error("Invalid JSON object")
            return {}, 500
        return {}, 200


heartbeats = {}   # type: Dict[str, datetime]


@api.resource("/api/0/heartbeat/<string:session_id>")
class HeartbeatResource(Resource):
    """
    WIP!

    Used to give clients the ability to signal on regular intervals something particular which can then be post-processed into events.
    The endpoint could compress a list of events which only differ by their timestamps into a event with a list of the timestamps.

    Should store the last time time the client checked in.
    """

    def get(self, client_name):
        logger.debug("Received heartbeat status request for client '{}'".format(client_name))
        if client_name in heartbeats:
            return heartbeats[client_name].isoformat()
        else:
            return "No heartbeat has been received for this client"

    def post(self, client_name):
        logger.debug("Received heartbeat for client '{}'".format(client_name))
        heartbeats[client_name] = datetime.now()
        return "success", 200