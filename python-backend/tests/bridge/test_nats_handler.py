import json

from bridge.config import Config
from bridge.nats_handler import (
    SUBJECT_INBOUND,
    SUBJECT_INBOUND_ROUTED,
    SUBJECT_REPLY,
    NATSHandler,
    sanitize_agent_name,
)


class _AgentClient:
    def __init__(self):
        self.calls = 0
        self.kwargs = {}

    async def send_message(self, **kwargs):
        self.calls += 1
        self.kwargs = kwargs
        return "reply"


class _NATS:
    is_closed = False

    def __init__(self):
        self.published = []
        self.subscriptions = []

    async def publish(self, subject, data):
        self.published.append((subject, json.loads(data)))

    async def subscribe(self, subject, cb):
        self.subscriptions.append((subject, cb))
        return object()


class _Msg:
    def __init__(self, payload, subject=SUBJECT_INBOUND):
        self.data = json.dumps(payload).encode()
        self.subject = subject


def _config() -> Config:
    return Config(
        nats_url="nats://test",
        agent_service_url="http://agent",
        agent_timeout_sec=1,
        agent_user_id="@agent-trading:matrix.local",
        host="127.0.0.1",
        port=8097,
    )


def _agent_scoped_config() -> Config:
    cfg = _config()
    cfg.nats_allowed_agents = ("research",)
    return cfg


async def test_thread_id_is_forwarded_as_reply_thread_root_id():
    handler = NATSHandler(_config(), _AgentClient())
    nc = _NATS()
    handler._nc = nc

    await handler._on_inbound(
        _Msg(
            {
                "room_id": "!room:matrix.local",
                "sender": "@alice:matrix.local",
                "body": "hello",
                "thread_id": "$root",
                "target_agent": "research",
            }
        )
    )

    assert nc.published == [
        (
            SUBJECT_REPLY,
            {
                "room_id": "!room:matrix.local",
                "agent_user_id": "@agent-research:matrix.local",
                "text": "reply",
                "is_streaming": False,
                "thread_root_id": "$root",
            },
        )
    ]


async def test_connect_subscribes_global_and_routed_inbound_subjects(monkeypatch):
    nc = _NATS()

    async def fake_connect(*_args, **_kwargs):
        return nc

    monkeypatch.setattr("bridge.nats_handler.nats.connect", fake_connect)

    handler = NATSHandler(_config(), _AgentClient())
    await handler.connect()

    assert [subject for subject, _cb in nc.subscriptions] == [
        SUBJECT_INBOUND,
        SUBJECT_INBOUND_ROUTED,
    ]


async def test_agent_scoped_connect_subscribes_only_allowed_agent_subject(monkeypatch):
    nc = _NATS()

    async def fake_connect(*_args, **_kwargs):
        return nc

    monkeypatch.setattr("bridge.nats_handler.nats.connect", fake_connect)

    handler = NATSHandler(_agent_scoped_config(), _AgentClient())
    await handler.connect()

    assert [subject for subject, _cb in nc.subscriptions] == [
        "matrix.message.inbound.agent.research",
    ]


async def test_agent_scoped_handler_rejects_unallowed_subject_and_target():
    agent = _AgentClient()
    handler = NATSHandler(_agent_scoped_config(), agent)
    nc = _NATS()
    handler._nc = nc

    await handler._on_inbound(
        _Msg(
            {
                "room_id": "!room:matrix.local",
                "sender": "@alice:matrix.local",
                "body": "hello",
                "target_agent": "trading",
            },
            subject="matrix.message.inbound.agent.trading",
        )
    )

    assert agent.calls == 0
    assert nc.published == []


async def test_agent_scoped_handler_accepts_allowed_subject_and_target():
    agent = _AgentClient()
    handler = NATSHandler(_agent_scoped_config(), agent)
    nc = _NATS()
    handler._nc = nc

    await handler._on_inbound(
        _Msg(
            {
                "room_id": "!room:matrix.local",
                "sender": "@alice:matrix.local",
                "body": "hello",
                "target_agent": "Research",
            },
            subject="matrix.message.inbound.agent.research",
        )
    )

    assert agent.calls == 1
    assert nc.published[0][1]["agent_user_id"] == "@agent-research:matrix.local"
    assert agent.kwargs["target_agent"] == "Research"


async def test_handler_ignores_agent_sender_echo():
    agent = _AgentClient()
    handler = NATSHandler(_config(), agent)
    nc = _NATS()
    handler._nc = nc

    await handler._on_inbound(
        _Msg(
            {
                "room_id": "!room:matrix.local",
                "sender": "@agent-research:matrix.local",
                "body": "reply echo",
                "event_id": "$echo",
                "target_agent": "research",
            }
        )
    )

    assert agent.calls == 0
    assert nc.published == []


async def test_handler_dedupes_replayed_event_id():
    agent = _AgentClient()
    handler = NATSHandler(_config(), agent)
    nc = _NATS()
    handler._nc = nc
    payload = {
        "room_id": "!room:matrix.local",
        "sender": "@alice:matrix.local",
        "body": "hello",
        "event_id": "$event-1",
        "target_agent": "research",
    }

    await handler._on_inbound(_Msg(payload))
    await handler._on_inbound(_Msg(payload))

    assert agent.calls == 1
    assert len(nc.published) == 1


async def test_handler_rejects_thread_reply_without_thread_root():
    agent = _AgentClient()
    handler = NATSHandler(_config(), agent)
    nc = _NATS()
    handler._nc = nc

    await handler._on_inbound(
        _Msg(
            {
                "room_id": "!room:matrix.local",
                "sender": "@alice:matrix.local",
                "body": "thread reply",
                "event_id": "$thread",
                "is_thread_reply": True,
                "target_agent": "research",
            }
        )
    )

    assert agent.calls == 0
    assert nc.published == []


def test_sanitize_agent_name_normalizes_matrix_and_nats_unsafe_input():
    assert sanitize_agent_name("Research") == "research"
    assert sanitize_agent_name("@agent-Research.Bot:matrix.local") == "research-bot"
    assert sanitize_agent_name("../../evil") == "evil"
    assert sanitize_agent_name("---") == "default"


def test_resolve_reply_user_id_sanitizes_target_agent():
    handler = NATSHandler(_config(), _AgentClient())

    assert (
        handler._resolve_reply_user_id("@agent-Research.Bot:matrix.local")
        == "@agent-research-bot:matrix.local"
    )
