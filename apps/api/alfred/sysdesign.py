"""System-design mentor: Socratic ladder + offline rubric review + a reveal gate.

Same philosophy as the coding AC gate: the reference design is structurally
withheld until the learner submits their own written design; hints never contain
the answer. Review is deterministic (concept-coverage rubric), no LLM, no network.
"""
from __future__ import annotations

from dataclasses import dataclass

MIN_DESIGN_WORDS = 80


@dataclass(frozen=True)
class Concept:
    name: str
    keywords: tuple[str, ...]
    why: str


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    prompt: str
    clarify: tuple[str, ...]
    estimate: tuple[str, ...]
    components: tuple[str, ...]
    pitfalls: tuple[str, ...]
    rubric: tuple[Concept, ...]
    reference: str


def _c(name, kws, why):
    return Concept(name, tuple(kws), why)


SCENARIOS: dict[str, Scenario] = {s.id: s for s in [
    Scenario(
        "url-shortener", "URL shortener",
        "Design a service that turns long URLs into short links and redirects them.",
        ("Custom aliases and expiry?", "Read:write ratio?", "Analytics needed?", "Is a short link ever reassigned?"),
        ("Writes/day and reads/day? (reads usually dominate ~100:1)", "Bytes per record and 5-year storage?", "How many characters are needed for N links in base62?"),
        ("What generates unique short codes without collisions at scale?", "What makes redirects fast?"),
        ("Hot keys", "Guessable sequential IDs", "Counter as a single point of failure"),
        (_c("id generation", ["base62", "counter", "hash", "snowflake", "random"], "Short codes must be unique; pick a scheme and say how collisions are avoided."),
         _c("storage choice", ["key-value", "nosql", "dynamo", "cassandra", "sql", "database"], "State the store and why its access pattern (point lookups) fits."),
         _c("caching", ["cache", "redis", "cdn", "memcached"], "Reads dominate; cache hot links."),
         _c("redirect semantics", ["301", "302", "redirect"], "301 vs 302 changes caching and analytics."),
         _c("scaling", ["shard", "partition", "replica", "load balancer", "horizontal"], "How reads and writes scale out."),
         _c("expiry/cleanup", ["ttl", "expire", "expiry", "cleanup"], "Links may expire; reclaim space."),
         _c("abuse", ["rate limit", "abuse", "malicious", "spam", "validation"], "Protect against spam and malicious URLs.")),
        "Base62-encode a unique ID from a distributed counter/range allocator (or hash+collision check). Store code->URL in a KV store, cache hot codes in Redis/CDN, serve 302 (or 301 if analytics are not needed), shard by code, TTL for expiry, rate-limit creation.",
    ),
    Scenario(
        "rate-limiter", "Rate limiter",
        "Design a rate limiter that caps requests per user/API key across many servers.",
        ("Per user, IP or API key?", "Hard block or soft throttle?", "Multiple limits (per second and per day)?", "Can it be slightly inaccurate?"),
        ("Requests per second at peak?", "Number of distinct keys and bytes of state per key?"),
        ("Where does the counter state live?", "Where is the limiter placed in the request path?"),
        ("Race conditions on counters", "Boundary bursts in fixed windows", "Limiter becoming the bottleneck"),
        (_c("algorithm", ["token bucket", "leaky bucket", "sliding window", "fixed window"], "Name an algorithm and its burst behaviour."),
         _c("shared state", ["redis", "distributed", "central", "in-memory store"], "Multiple servers need shared counters."),
         _c("atomicity", ["atomic", "lua", "incr", "race", "lock"], "Counter updates must not race."),
         _c("placement", ["gateway", "middleware", "edge", "proxy"], "Where the check runs."),
         _c("response behaviour", ["429", "retry-after", "header"], "Tell clients what happened."),
         _c("failure mode", ["fail open", "fail closed", "fallback", "degrade"], "What happens if the limiter store is down.")),
        "Token bucket per key in Redis updated atomically (Lua/INCR+EXPIRE), enforced at the API gateway, return 429 with Retry-After, choose fail-open for availability, shard keys across Redis nodes.",
    ),
    Scenario(
        "chat-system", "Chat system",
        "Design a 1:1 and group chat system with delivery and message history.",
        ("Group size limits?", "Online presence and read receipts?", "Media messages?", "Message retention?"),
        ("Messages per second and concurrent connections?", "Storage per message and per year?"),
        ("How does a message reach an online user instantly?", "What happens for an offline user?"),
        ("Message ordering", "Duplicate delivery on retries", "Huge group fan-out"),
        (_c("realtime transport", ["websocket", "long poll", "sse", "persistent connection"], "Push needs a persistent connection."),
         _c("message storage", ["cassandra", "hbase", "nosql", "partition", "time-series", "database"], "History is append-heavy; pick and justify a store."),
         _c("ordering", ["sequence", "ordering", "timestamp", "monotonic", "id"], "Define per-conversation ordering."),
         _c("delivery guarantees", ["ack", "at least once", "idempotent", "retry", "dedup"], "Acks, retries, dedup."),
         _c("offline handling", ["push notification", "queue", "offline", "sync"], "Offline users get messages later."),
         _c("fan-out", ["fan-out", "fanout", "pub/sub", "kafka", "broker"], "Group messages need fan-out.")),
        "WebSocket gateways keep connections; messages go through a broker (Kafka/pubsub) to recipients' gateways, persisted in a partitioned wide-column store keyed by conversation with per-conversation sequence numbers; acks + idempotent client IDs for at-least-once; offline users get push notifications and sync on reconnect.",
    ),
    Scenario(
        "news-feed", "News feed",
        "Design a social news feed showing recent posts from people you follow.",
        ("Ranked or chronological?", "Celebrity accounts with millions of followers?", "Media in posts?", "Feed freshness expectation?"),
        ("Users, average follows, posts per day?", "Feed reads per second?"),
        ("Compute the feed when read, or precompute when posted?", "How do you treat celebrity accounts?"),
        ("Fan-out write amplification", "Hot celebrity partitions", "Stale feed caches"),
        (_c("fan-out strategy", ["fan-out on write", "fan-out on read", "push", "pull", "hybrid"], "Choose push, pull or hybrid and justify."),
         _c("celebrity handling", ["celebrity", "hybrid", "hot user", "large follower"], "Push does not work for huge follower counts."),
         _c("feed cache", ["cache", "redis", "timeline"], "Precomputed timelines live in a cache."),
         _c("graph storage", ["follow", "graph", "adjacency", "relationship"], "Who follows whom must be stored."),
         _c("ranking", ["rank", "score", "relevance", "machine learning", "chronological"], "State how order is decided."),
         _c("media", ["cdn", "object storage", "s3", "blob"], "Media is stored and served separately.")),
        "Hybrid fan-out: push new posts into followers' cached timelines (Redis) for normal users, pull celebrity posts at read time and merge, ranked by a score; follow graph in a sharded store; media in object storage behind a CDN.",
    ),
    Scenario(
        "notification-service", "Notification service",
        "Design a service that sends push, email and SMS notifications reliably.",
        ("Channels and priorities?", "User preferences and quiet hours?", "Scheduled sends?", "Exactly-once needed?"),
        ("Notifications per day and peak burst?", "Third-party provider rate limits?"),
        ("How do bursts avoid overwhelming providers?", "How do you avoid sending twice?"),
        ("Duplicate sends on retry", "Provider outages", "One slow channel blocking others"),
        (_c("queueing", ["queue", "kafka", "sqs", "rabbitmq", "broker"], "Decouple producers from slow providers."),
         _c("per-channel workers", ["worker", "consumer", "per channel", "separate"], "Isolate channels."),
         _c("retries and dlq", ["retry", "backoff", "dead letter", "dlq"], "Handle provider failures."),
         _c("idempotency", ["idempotent", "dedup", "idempotency key"], "Prevent double sends."),
         _c("preferences", ["preference", "opt out", "unsubscribe", "quiet hours"], "Respect user settings."),
         _c("rate limiting providers", ["rate limit", "throttle", "backpressure"], "Respect provider quotas.")),
        "API validates and writes to a per-channel queue; workers call providers with exponential backoff and a dead-letter queue; idempotency keys dedupe; preference service checked before enqueue; throttling protects provider quotas.",
    ),
    Scenario(
        "key-value-store", "Distributed key-value store",
        "Design a distributed, highly available key-value store.",
        ("Consistency requirement: strong or eventual?", "Value sizes?", "Range queries?", "Multi-region?"),
        ("Total data size and QPS?", "Replication factor and node count?"),
        ("How is data spread across nodes and found?", "What happens when a node dies?"),
        ("Hot partitions", "Split brain", "Read repair cost"),
        (_c("partitioning", ["consistent hashing", "hash ring", "partition", "shard"], "Spread keys and support adding nodes."),
         _c("replication", ["replica", "replication", "quorum", "n=3"], "Survive node loss."),
         _c("consistency model", ["quorum", "eventual", "strong", "cap", "w+r"], "State the trade-off explicitly."),
         _c("failure detection", ["gossip", "heartbeat", "hinted handoff", "failure detect"], "Detect and route around failures."),
         _c("conflict resolution", ["vector clock", "last write wins", "lww", "crdt", "conflict"], "Concurrent writes need a rule."),
         _c("storage engine", ["lsm", "sstable", "memtable", "wal", "commit log", "write-ahead"], "How a node stores data durably.")),
        "Consistent hashing with virtual nodes; replicate to N nodes with tunable quorum (W+R>N); gossip for membership, hinted handoff and read repair; vector clocks or LWW for conflicts; LSM-tree storage with WAL.",
    ),
]}


class SysDesignError(Exception):
    pass


def get_scenario(sid: str) -> Scenario:
    if sid not in SCENARIOS:
        raise SysDesignError(f"unknown scenario {sid!r}; choose from {sorted(SCENARIOS)}")
    return SCENARIOS[sid]


def list_scenarios() -> list[dict]:
    return [{"id": s.id, "title": s.title} for s in SCENARIOS.values()]


def hint(sid: str, level: int) -> str:
    s = get_scenario(sid)
    if level == 0:
        return s.prompt
    steps = {
        1: ("Clarify requirements first. Ask yourself:", s.clarify),
        2: ("Do back-of-envelope estimates:", s.estimate),
        3: ("Think about the core components:", s.components),
        4: ("Stress-test your design against these failure modes:", s.pitfalls),
    }
    if level not in steps:
        raise SysDesignError("level must be 0-4")
    head, items = steps[level]
    return head + "\n" + "\n".join(f"- {i}" for i in items)


def review(sid: str, design: str) -> dict:
    """Score a written design against the rubric. Refuses thin submissions; only
    a real attempt unlocks the reference design."""
    s = get_scenario(sid)
    words = len(design.split())
    if words < MIN_DESIGN_WORDS:
        raise SysDesignError(f"write your own design first ({words}/{MIN_DESIGN_WORDS} words); the reference stays locked until you do")
    low = design.lower()
    covered = [c for c in s.rubric if any(k in low for k in c.keywords)]
    missing = [c for c in s.rubric if c not in covered]
    return {
        "score": round(len(covered) / len(s.rubric), 2),
        "covered": [c.name for c in covered],
        "missing": [{"concept": c.name, "why": c.why} for c in missing],
        "reference": s.reference,
    }


def render_review(r: dict) -> str:
    out = [f"Coverage: {int(r['score'] * 100)}%", "Covered: " + (", ".join(r["covered"]) or "none")]
    if r["missing"]:
        out.append("Missing:")
        out += [f"- {m['concept']}: {m['why']}" for m in r["missing"]]
    out.append("Reference design: " + r["reference"])
    return "\n".join(out)
