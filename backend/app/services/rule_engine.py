import re
import json
from typing import List, Dict, Any, Set, Tuple
import logging

from app.ml.text_normalizer import text_normalizer

logger = logging.getLogger(__name__)

class RuleEngine:
    """Rule-based content filtering with word-boundary matching.

    Uses \\b word-boundary regex to avoid false positives like
    'skill' matching 'kill' or 'studied' matching 'die'.
    Now with context analysis to distinguish harmful vs safe usage.
    """

    def __init__(self):
        # ── Hindi Gali Mappings ──
        self.hindi_galis = {
            "madarchod": [
                r'madar?ch?od', r'madar ?chod', r'madar ?ch?od', r'mdrchod',
                r'mdr ?chod', r'motherchod', r'mother ?chod', r'motherch?od',
                r'mdrch?d', r'madarjaat', r'madar ?jaat', r'madar ?zat',
                r'\bmc\b', r'\bm\.?c\.?\b',
            ],
            "bhenchod": [
                r'b(?:e|o|a|h)?henchod', r'be?hen ?chod', r'b(?:e|o)hn ?chod',
                r'b(?:e|o)han ?chod', r'\bbc\b', r'\bb\.?c\.?\b',
                r'behench?d', r'bhen ?ch?d', r'sisterfucker', r'sister ?fucker'
            ],
            "chutiya": [
                r'\bchutiya\b', r'\bchutiye\b', r'\bchut?iya\b', r'\bchut?iye\b',
                r'\bchoot?iya\b', r'\bchoot?iye\b', r'\bchut?ya\b', r'\bchoot?ya\b',
                r'\bchut?ye\b', r'\bchoot?ye\b'
            ],
            "gandu": [
                r'\bgandu\b', r'\bgand?u\b', r'\bgandoo\b', r'\bgand?oo\b',
                r'\bgandhu\b', r'\bgaa?ndu\b'
            ],
            "randi": [
                r'\brandi\b', r'\brand?i\b', r'\brandee\b', r'\brand?ee\b',
                r'\brandi ?ka\b', r'\brandi ?ke\b', r'\brandi ?ki\b'
            ],
            "bhosdi": [
                r'\bbhosdi\b', r'\bbhosd?i\b', r'\bbhosdike\b', r'\bbhosdi ?ke\b',
                r'\bbhosd?ike\b', r'\bbhosda\b', r'\bbhosd?a\b'
            ],
            "kutta": [
                r'\bkutta\b', r'\bkutte\b', r'\bkutia\b', r'\bkutiya\b',
                r'\bkut?iya\b', r'\bkut?ia\b'
            ],
            "chinal": [
                r'\bchinal\b', r'\bchinnal\b', r'\bchilnal\b'
            ],
            "harami": [
                r'\bharami\b', r'\bharam?i\b', r'\bhara?mi\b',
                r'\bharamza?de\b', r'\bharamzade\b', r'\bharam ?zade\b'
            ],
            "sala": [
                r'\bsala\b', r'\bsaale\b', r'\bsaali\b'
            ],
            "lavde": [
                r'\blavde\b', r'\blawde\b', r'\blaude\b', r'\blavda\b', r'\blawda\b'
            ],
            "chod": [
                r'\bchod\b', r'\bchodd\b',
                r'\bfuck\b', r'\bf\*ck\b', r'\bf\*\*k\b',
                r'\bfuk\b', r'\bfak\b', r'\bphuck\b'
            ],
            "lund": [
                r'\blund\b', r'\blun?d\b', r'\blound\b', r'\blond\b'
            ],
            "gaand": [
                r'\bgaand\b', r'\bgaa?nd\b', r'\bgand\b'
            ],
            "tatte": [
                r'\btatte\b', r'\btat?te\b'
            ],
            "bsdk": [
                r'\bbsdk\b', r'\bb\.?s\.?d\.?k\.?\b',
                r'\bbehen ke\b', r'\bbahan ke\b', r'\bbhen ke\b'
            ]
        }

        # ── English Profanity Patterns (leet-speak aware regex) ──────────────
        # These are character-class regex patterns — NOT simple keywords.
        # They handle common substitutions: a→@, i→1, s→$, t→+, o→0, e→3.
        # Stored as raw patterns and compiled separately (not via banned_categories)
        # so they go through their own pipeline step in check_rules().
        self.english_profanity_patterns = [
            r'[a@][s$][s$]h[o0][l1][e3][s$]?',
            r'b[a@][s$][t+][a@]rd',
            r'b[e3][a@][s$][t+][i1][a@]?[l1]([i1][t+]y)?',
            r'b[e3][a@][s$][t+][i1][l1][i1][t+]y',
            r'b[e3][s$][t+][i1][a@][l1]([i1][t+]y)?',
            r'b[i1][t+]ch[s$]?',
            r'b[i1][t+]ch[e3]r[s$]?',
            r'b[i1][t+]ch[e3][s$]',
            r'b[i1][t+]ch[i1]ng?',
            r'b[l1][o0]wj[o0]b[s$]?',
            r'c[l1][i1][t+]',
            r'(c|k|ck|q)[o0](c|k|ck|q)[s$]u',
            r'(c|k|ck|q)[o0](c|k|ck|q)[s$]u(c|k|ck|q)[e3]d',
            r'(c|k|ck|q)[o0](c|k|ck|q)[s$]u(c|k|ck|q)[e3]r',
            r'(c|k|ck|q)[o0](c|k|ck|q)[s$]u(c|k|ck|q)[i1]ng',
            r'(c|k|ck|q)[o0](c|k|ck|q)[s$]u(c|k|ck|q)[s$]',
            r'cumm??[e3]r',
            r'cumm?[i1]ngcock',
            r'(c|k|ck|q)um[s$]h[o0][t+]',
            r'(c|k|ck|q)un[i1][l1][i1]ngu[s$]',
            r'(c|k|ck|q)un[i1][l1][l1][i1]ngu[s$]',
            r'(c|k|ck|q)unn[i1][l1][i1]ngu[s$]',
            r'(c|k|ck|q)un[t+][s$]?',
            r'(c|k|ck|q)un[t+][l1][i1](c|k|ck|q)',
            r'(c|k|ck|q)un[t+][l1][i1](c|k|ck|q)[e3]r',
            r'(c|k|ck|q)un[t+][l1][i1](c|k|ck|q)[i1]ng',
            r'cyb[e3]r(ph|f)u(c|k|ck|q)',
            r'd[a@]mn',
            r'd[i1]ck',
            r'd[i1][l1]d[o0]',
            r'd[i1][l1]d[o0][s$]',
            r'd[i1]n(c|k|ck|q)',
            r'd[i1]n(c|k|ck|q)[s$]',
            r'[e3]j[a@]cu[l1]',
            r'(ph|f)[a@]g[s$]?',
            r'(ph|f)[a@]gg[i1]ng',
            r'(ph|f)[a@]gg?[o0][t+][s$]?',
            r'(ph|f)[a@]gg[s$]',
            r'(ph|f)[e3][l1][l1]?[a@][t+][i1][o0]',
            r'(ph|f)u(c|k|ck|q)',
            r'(ph|f)u(c|k|ck|q)[s$]?',
            r'g[a@]ngb[a@]ng[s$]?',
            r'g[a@]ngb[a@]ng[e3]d',
            r'h[o0]m?m[o0]',
            r'h[o0]rny',
            r'j[a@](c|k|ck|q)\-?[o0](ph|f)(ph|f)?',
            r'j[e3]rk\-?[o0](ph|f)(ph|f)?',
            r'j[i1][s$z][s$z]?m?',
            r'[ck][o0]ndum[s$]?',
            r'mast(e|ur)b(8|ait|ate)',
            r'n+[i1]+[gq]+[e3]*r+[s$]*',
            r'[o0]rg[a@][s$][i1]m[s$]?',
            r'[o0]rg[a@][s$]m[s$]?',
            r'p[e3]nn?[i1][s$]',
            r'p[i1][s$][s$]',
            r'p[i1][s$][s$][o0](ph|f)(ph|f)',
            r'p[o0]rn',
            r'p[o0]rn[o0][s$]?',
            r'p[o0]rn[o0]gr[a@]phy',
            r'pr[i1]ck[s$]?',
            r'pu[s$][s$][i1][e3][s$]',
            r'pu[s$][s$]y[s$]?',
            r'[s$][e3]x',
            r'[s$]h[i1][t+][s$]?',
            r'[s$][l1]u[t+][s$]?',
            r'[s$]mu[t+][s$]?',
            r'[s$]punk[s$]?',
            r'[t+]w[a@][t+][s$]?',
            # Whole-word-only patterns (were anchored with ^ $ in original)
            r'\b[a@][s$][s$]\b',
            r'\bcum[s$]?\b',
            r'\b(c|k|ck|q)[o0](c|k|ck|q)[s$]?\b',
            r'\bg[a@]y\b',
        ]

        self.banned_categories = {
            "drugs": [
                "drugs", "heroin", "cocaine", "weed", "meth",
                "fentanyl", "dealer", "drug dealer", "coke", "crack",
                "mdma", "ecstasy", "lsd", "acid", "shrooms", "mushrooms",
                "opium", "morphine", "oxy", "percocet", "xanax", "valium",
                "diazepam", "amphetamine", "methamphetamine", "ice",
                "crystal meth", "dope", "smack", "skunk", "ganja",
                "bhang", "charas", "hash", "hashish", "pot", "fent", "white powder",
                "marijuana", "cannabis", "thc", "cbd", "vape", "vaping",
                "nicotine", "tobacco", "cigarette", "cigar"
            ],
            "violence": [
                "kill you", "kill them", "kill him", "kill her",
                "kill everyone", "murder", "bomb", "shoot",
                "mass shooting", "gun violence", "shoot up",
                "stab", "stabbing", "beat up", "beat you", "beat him",
                "beat her", "torture",
                "execute", "execution", "assassinate", "assassination",
                "terrorist", "terrorism", "jihad", "martyr", "martyrdom",
                "explode", "explosion", "blast", "bombing", "suicide bomb"
            ],
            "harm": [
                "suicide", "self-harm", "self harm", "cutting myself",
                "hang myself", "end my life", "want to die", "kill myself",
                "take my life", "end it all", "end it now", "better off dead",
                "no reason to live", "want to disappear",
                "jump off", "jump from", "overdose", "od on",
                "sleep forever", "never wake up"
            ],
            "offensive": [
                "nazi", "white supremacy", "kkk", "ku klux",
                "hitler", "fascist", "neo-nazi", "racist",
                "homophobic", "transphobic", "xenophobic", "islamophobic",
                "antisemitic", "anti-semitic", "destroying this country",
                "removed from society"
            ],
            "sexual": [
                "send nudes", "sext", "sexting", "sex tape", "private video",
                "leaked", "blackmail", "coerce", "forced",
                "creampie", "slut", "whore", "pussy",
                "boobs", "booty", "anal", "oral", "send me more",
                "share these with everyone", "found your photos",
                "blowjob", "handjob", "rape", "raped", "raping", "molest", "molested"
            ],
            "promotional": [
                "earn money", "make money", "work from home",
                "zero effort", "no investment", "cash prize",
                "get rich quick", "invest now", "guaranteed returns",
                "double your money", "money back",
                "referral", "refer and earn", "sign up bonus",
                "free money", "free cash", "free bitcoin",
                "click here", "link in bio", "link in profile",
                "dm me", "whatsapp me"
            ],
        }

        # ── False-positive allowlist ──
        self.allowlist_patterns = [
            r'\bskill(?:s|ed|ful|fully)?\b',
            r'\bkill(?:er)?\s+(?:app|feature|design|look|outfit|shot)\b',
            r'\boverkill\b',
            r'\bpainkiller(?:s)?\b',
            r'\bdie-?cast(?:ing)?\b',
            r'\bstudied\b',
            r'\bstudies\b',
            r'\bstudying\b',
            r'\bsoldier(?:s)?\b',
            r'\baudience(?:s)?\b',
            r'\bdie(?:sel|t|tary|titian|tetics)\b',
            r'\bdead(?:line|wood)(?:s)?\b',
            r'\bheart\s+attack\b',
            r'\bpanic\s+attack\b',
            r'\basthma\s+attack\b',
            r'\banxiety\s+attack\b',
            r'\bbomb(?:astic|shell)\b',
            r'\bphotobomb\b',
            r'\b(?:the|this|that)\s+bomb\b',
            r'\bweed(?:s|ing|ed)?\s+(?:the|my|our|your|a)\s+(?:garden|yard|lawn|bed|field|plant|patch)\b',
            r'\bweed\s+(?:killer|control|removal)\b',
            r'\bphoto\s*shoot\b',
            r'\bshoot(?:ing)?\s+(?:a\s+)?(?:photo|video|film|movie|scene|hoop|basket|ball|goal)\b',
            r'\bshoot(?:er)?\s+(?:game|games)\b',
            r'\bhate\s+(?:bugs?|mondays?|mornings?|traffic|homework|waiting|rain|cold|heat|spiders|snakes)\b',
            r'\bi\s+hate\s+(?:when|that|it\s+when|how)\b',
            r'\bdrug\s+(?:store|shop|pharmacy|prescription|medicine|medication|treatment|therapy)\b',
            r'\bdrugs?\s+(?:for|to)\s+(?:pain|illness|disease|condition|symptom)\b',
            r'\b(?:prescription|medicinal|generic)\s+drugs?\b',
            r'\bcocaine\s+(?:anesthesia|anesthetic|numbing|dental|medical)\b',
            r'\bfrontend\b', r'\bbackend\b', r'\bbandwidth\b',
            r'\bcommand\b', r'\bfind\b', r'\bend\b', r'\bbeyond\b',
            r'\bstandard\b', r'\bfound\b', r'\bground\b', r'\bbound\b',
            r'\bbrand\b', r'\btrend\b', r'\bexpand\b', r'\bblend\b',
        ]

        # ── Tech Taxonomy ──
        self.tech_taxonomy = {
            "general_tech": [
                "application", "applications", "web application", "mobile application",
                "app", "apps", "web app", "mobile app", "desktop app", "saas app",
                "software", "platform", "service", "services", "system", "systems",
                "product", "products", "digital product", "tech product",
                "technology", "tech", "technologies", "digital", "innovation",
                "developer", "developers", "programmer", "programmers",
                "engineer", "engineers", "coder", "coders",
                "development", "programming", "coding", "engineering",
                "architecture", "infrastructure", "scalable", "scalability",
                "performance", "reliable", "reliability", "efficient", "efficiency",
                "responsive", "robust", "modular", "distributed", "decentralized",
                "real-time", "real time", "asynchronous", "synchronous",
                "deployment", "deploy", "deployed", "production", "staging",
                "integration", "testing", "debugging", "debug", "refactor",
                "feature", "features", "functionality", "workflow", "pipeline",
                "open source", "codebase", "repository", "version control",
                "data", "dataset", "analytics", "insights", "metrics",
                "monitoring", "logging", "dashboard", "visualization",
                "security", "secure", "encryption", "authentication",
                "authorization", "cyber", "cybersecurity", "privacy",
                "data protection", "access control",
                "user experience", "ux", "ui", "user interface", "user journey",
                "usability", "accessibility", "interaction design",
                "frontend performance", "loading time", "smooth interactions",
                "cloud", "cloud computing", "cloud-native", "cloud infrastructure",
                "on-premise", "hybrid cloud", "serverless computing",
                "load balancing", "auto-scaling", "high availability",
                "notification", "notifications", "messaging", "instant messaging",
                "live updates", "push notification", "real-time communication",
                "event-driven", "message-driven", "webhook", "webhooks",
                "storage", "cache", "caching", "database", "databases",
                "data storage", "cloud storage",
                "build", "compile", "package", "library", "libraries",
                "dependency", "dependencies", "environment", "runtime",
            ],
            "languages": [
                "python", "javascript", "typescript", "java", "kotlin", "swift",
                "rust", "golang", "go", "cpp", "c++", "csharp", "c#", "ruby", "php",
                "scala", "dart", "elixir", "haskell", "lua", "perl", "bash",
                "powershell", "solidity", "assembly", "cobol", "fortran",
                "matlab", "julia", "groovy", "clojure", "erlang", "ocaml",
                "fsharp", "f#", "zig", "nim", "crystal", "mojo"
            ],
            "web_frameworks": [
                "react", "vue", "angular", "nextjs", "next.js", "nuxt", "svelte",
                "django", "flask", "fastapi", "express", "nestjs", "rails",
                "laravel", "spring", "asp.net", "gatsby", "remix", "astro",
                "htmx", "solidjs", "qwik", "sveltekit", "nuxtjs", "vite",
                "webpack", "parcel", "rollup", "esbuild", "turbopack"
            ],
            "databases": [
                "mysql", "postgresql", "postgres", "mongodb", "redis", "sqlite",
                "cassandra", "dynamodb", "firebase", "supabase", "elasticsearch",
                "neo4j", "mariadb", "cockroachdb", "planetscale", "prisma",
                "sqlalchemy", "pinecone", "weaviate", "qdrant", "chroma",
                "milvus", "clickhouse", "snowflake", "bigquery", "redshift",
                "oracle", "mssql", "influxdb", "timescaledb", "duckdb"
            ],
            "devops_cloud": [
                "docker", "kubernetes", "k8s", "aws", "azure", "gcp",
                "google cloud", "terraform", "ansible", "jenkins",
                "github actions", "gitlab ci", "nginx", "apache", "linux",
                "ubuntu", "debian", "helm", "prometheus", "grafana", "datadog",
                "cloudflare", "pulumi", "vagrant", "argocd", "istio", "envoy",
                "traefik", "vercel", "netlify", "heroku", "railway", "fly.io",
                "digitalocean", "linode", "vultr", "ci/cd", "devops", "sre",
                "gitops", "devsecops", "lambda", "cloud run",
                "containerization", "container", "containers",
                "microservices", "microservice", "monolith", "monorepo"
            ],
            "ml_ai": [
                "machine learning", "deep learning", "neural network", "pytorch",
                "tensorflow", "keras", "scikit-learn", "hugging face", "llm",
                "transformer", "computer vision", "nlp", "bert", "gpt",
                "reinforcement learning", "generative ai", "stable diffusion",
                "langchain", "llamaindex", "rag", "fine-tuning", "embeddings",
                "vector database", "diffusion model", "autoencoder", "gan",
                "xgboost", "lightgbm", "catboost", "pandas", "numpy", "scipy",
                "openai", "anthropic", "gemini", "claude", "llama", "mistral",
                "ollama", "vllm", "cuda", "tensorrt", "onnx", "mlflow",
                "weights and biases", "wandb", "dvc", "feature engineering",
                "model training", "inference", "quantization", "lora", "qlora",
                "artificial intelligence", "ai model", "ai system"
            ],
            "tools_concepts": [
                "api", "apis", "rest", "restful", "graphql", "grpc",
                "websocket", "websockets", "jwt", "oauth", "oauth2",
                "git", "github", "gitlab", "bitbucket", "vscode", "vim",
                "neovim", "npm", "yarn", "pnpm", "pip", "virtualenv", "conda",
                "poetry", "cargo", "gradle", "maven", "makefile", "dockerfile",
                "openapi", "swagger", "postman", "insomnia", "json", "yaml",
                "toml", "protobuf", "orm", "sdk", "cli", "tui",
                "design pattern", "solid principles", "clean code",
                "test driven", "tdd", "bdd", "unit test", "integration test",
                "end to end", "e2e", "playwright", "selenium", "cypress",
                "jest", "pytest", "mocha", "vitest", "storybook", "figma",
                "kafka", "rabbitmq", "message queue", "pub sub",
                "cdn", "dns", "ssl", "tls", "http", "https", "tcp", "udp",
                "load balancer", "reverse proxy", "ingress",
                "ssh", "sftp", "ftp", "vpn", "proxy"
            ],
            "hardware_systems": [
                "raspberry pi", "arduino", "fpga", "embedded", "firmware",
                "cpu", "gpu", "nvme", "ssd", "overclocking", "arm", "risc-v",
                "x86", "kernel", "bios", "uefi", "hypervisor", "vm",
                "virtualization", "bare metal", "soc", "microcontroller",
                "serial port", "uart", "i2c", "spi", "pwm", "iot",
                "edge computing", "wasm", "webassembly", "simd"
            ],
            "security": [
                "cybersecurity", "penetration testing", "pentesting", "ctf",
                "vulnerability", "vpn", "firewall", "zero trust", "siem",
                "threat hunting", "bug bounty", "zero day", "exploit", "cve",
                "owasp", "devsecops", "static analysis", "dynamic analysis",
                "fuzzing", "reverse engineering", "malware analysis",
                "incident response", "soc analyst", "threat intelligence",
                "network security", "application security", "appsec",
                "red team", "blue team", "secure coding", "sql injection",
                "xss", "csrf", "tls certificate", "https encryption",
                "password hashing", "token", "jwt token", "api key",
                "two factor", "2fa", "mfa", "single sign on", "sso",
                "identity provider", "idp", "ldap", "active directory"
            ],
            "tech_culture": [
                "open source", "hackathon", "leetcode", "competitive programming",
                "system design", "code review", "pull request", "merge request",
                "standup", "sprint", "agile", "scrum", "kanban", "jira",
                "stackoverflow", "stack overflow", "tech interview", "dsa",
                "data structures", "algorithms", "big o", "complexity",
                "refactor", "technical debt", "developer experience",
                "side project", "startup", "paas", "iaas",
                "tech stack", "full stack", "fullstack", "backend engineer",
                "frontend engineer", "software engineer", "swe",
                "product engineer", "platform engineer", "cloud engineer"
            ]
        }

        self.ambiguous_tech_terms = [
            "python", "java", "c", "go", "rust", "ruby", "dart", "scala", "bash", "shell", "swift", "kotlin", "julia", "crystal", "nim", "zig", "cobra", "chapel", "red", "blue", "v", "ring",
            "react", "express", "spring", "flask", "bottle", "tornado", "phoenix", "ember", "next", "nuxt", "meteor", "catalyst", "ionic", "foundation", "backbone", "alpine",
            "code", "script", "thread", "process", "object", "class", "method", "function", "variable", "pointer", "reference", "value", "key", "token", "block", "stack", "queue", "heap", "tree", "root", "leaf", "node", "branch",
            "port", "host", "client", "server", "request", "response", "session", "cookie", "cache", "proxy", "gateway", "bridge", "tunnel", "socket", "packet", "route",
            "table", "column", "row", "index", "query", "schema", "model", "record", "field", "keyspace", "cluster", "shard", "document",
            "docker", "container", "image", "build", "deploy", "release", "pipeline", "environment", "version", "tag", "stage", "job", "runner",
            "hash", "salt", "key", "cipher", "token", "signature", "certificate", "vault", "secret", "breach",
            "grid", "layout", "margin", "padding", "theme", "style", "font", "color", "shadow", "layer", "frame",
            "run", "execute", "build", "push", "pull", "commit", "fetch", "merge", "fork", "clone", "install", "update", "upgrade", "fix", "debug", "test",
            "time", "space", "memory", "power", "control", "flow", "state", "event", "trigger", "handler", "service", "system", "platform", "tool",
            "file", "folder", "path", "root", "home", "temp", "log", "config", "bin", "src", "dist",
            "model", "training", "learning", "network", "neuron", "layer", "weight", "bias", "loss", "prediction",
            "watch", "play", "drive", "store", "map", "reduce", "filter", "sort", "search", "match", "split", "join", "count", "check", "print",
            "running", "executed", "building", "deployed", "testing", "fixing", "merging", "pulling", "pushing", "updating", "installing",
            "cached", "storing", "mapping", "filtering", "sorting", "searching", "matched", "splitting", "joining",
            "configured", "configuring", "optimized", "optimizing", "scaling", "scaled",
            "connected", "connecting", "disconnected", "handling", "handled"
        ]

        self.tech_anchors = [
            "javascript", "typescript", "c++", "csharp", "golang", "php",
            "function", "variable", "loop", "recursion", "syntax", "compiler", "interpreter", "runtime", "debugging", "refactor", "dependency", "module", "package",
            "frontend", "backend", "fullstack", "api", "rest", "graphql", "endpoint", "request", "response", "middleware", "routing", "session", "cookie", "authentication", "authorization",
            "framework", "library", "sdk", "cli", "npm", "pip", "maven", "gradle", "webpack", "vite", "babel",
            "database", "sql", "nosql", "mongodb", "mysql", "postgresql", "redis", "schema", "query", "index", "transaction",
            "docker", "kubernetes", "container", "deployment", "ci", "cd", "pipeline", "server", "cloud", "aws", "azure", "gcp", "nginx", "loadbalancer",
            "encryption", "hashing", "token", "jwt", "oauth", "ssl", "tls", "firewall", "vulnerability",
            "algorithm", "data structure", "stack", "queue", "heap", "tree", "graph", "hashmaps", "complexity", "recursion", "dp", "dynamic programming", "memory safe", "memory safety",
            "testing", "unit test", "integration test", "testcases", "mocking", "coverage",
            "git", "github", "gitlab", "commit", "branch", "merge", "rebase", "pull request",
            "model", "training", "inference", "dataset", "classification", "regression", "neural network", "transformer", "embedding"
        ]

        # Clean up taxonomy by removing ambiguous terms
        for cat in self.tech_taxonomy:
            self.tech_taxonomy[cat] = [t for t in self.tech_taxonomy[cat] if t not in self.ambiguous_tech_terms]

        # ── Tech URL domains ──
        self.tech_url_patterns = [
            r'github\.com', r'gitlab\.com', r'bitbucket\.org',
            r'stackoverflow\.com', r'stackexchange\.com',
            r'npmjs\.com', r'pypi\.org', r'crates\.io', r'pkg\.go\.dev',
            r'hub\.docker\.com', r'docs\.[a-z]+\.(?:com|io|dev|org)',
            r'developer\.[a-z]+\.com', r'dev\.to', r'hackernews',
            r'news\.ycombinator\.com', r'producthunt\.com',
            r'leetcode\.com', r'hackerrank\.com', r'codeforces\.com',
            r'codepen\.io', r'replit\.com', r'codesandbox\.io',
            r'vercel\.com', r'netlify\.com', r'heroku\.com',
            r'arxiv\.org', r'huggingface\.co', r'kaggle\.com',
        ]

        # ── Code signal patterns ──
        self.code_signal_patterns = [
            r'```[\w]*\n',
            r'\bv\d+\.\d+(?:\.\d+)?\b',
            r'\b\d+\.\d+\.\d+\b',
            r'(?:import|from)\s+\w+',
            r'(?:def|class|function|const|let|var|async|await)\s+\w+',
            r'(?:=>|->|::|\.\.\.)',
            r'(?:npm|yarn|pip|cargo|go)\s+(?:install|add|run|build|test)',
            r'(?:git\s+(?:clone|push|pull|commit|merge|rebase|checkout))',
            r'(?:docker\s+(?:run|build|push|pull|compose))',
            r'\$\s+\w+',
            r'#\s*(?:TODO|FIXME|HACK|NOTE|BUG):',
            r'(?:localhost|127\.0\.0\.1):\d+',
            r'(?:GET|POST|PUT|PATCH|DELETE)\s+/',
            r'O\((?:n|log n|n log n|n²|1)\)',
        ]

        # ── Non-tech signals ──
        self.non_tech_signals = [
            r'\b(?:recipe|cuisine|restaurant|meal|dish|snack|breakfast|lunch|dinner|cooking|baking|ingredients)\b',
            r'\b(?:cricket|ipl|nba|fifa|wicket|century|stadium|sports match|match score|football match|cricket match)\b',
            r'\b(?:celebrity|bollywood|hollywood|actor|actress|movie star|singer|musician|fan club|box office)\b',
            r'\b(?:election|parliament|senate|congress|minister|prime minister|political party|vote|campaign rally)\b',
            r'\b(?:temple|mosque|church|prayer|worship|sermon|puja|namaz|pilgrimage|religious festival)\b',
            r'\b(?:girlfriend|boyfriend|marriage proposal|wedding ceremony|divorce|breakup|date night|anniversary)\b',
            r'\b(?:outfit of the day|fashion tips|clothing haul|makeup tutorial|skincare routine|haircut|salon visit|wardrobe)\b',
        ]

        # ── Off-topic sentence signals ──
        self.off_topic_sentence_signals = [
            r'\bi (?:saw|noticed|watched|found|met)\s+(?:a|an|some|my|this|the)\s+\w+',
            r'\b(?:dog|cat|bird|monkey|elephant|cow|horse|lion|tiger|snake|spider)\b',
            r'\b(?:wearing|sunglasses|outfit|clothes|dress|shirt|shoes)\b',
            r'\b(?:looked|looked like|seemed|appears|feels)\s+(?:more|so|very|really|quite)\b',
            r'\b(?:most humans|most people|everyone|everybody)\b',
            r'\b(?:ate|eating|cooked|cooking|taste|tasty|delicious|yummy|hungry)\b',
            r'\b(?:movie|film|show|series|episode|season|watch|watched|binge)\b',
            r'\b(?:gym|workout|exercise|fitness|yoga|meditation|sleep|tired|woke up)\b',
            r'\b(?:my friend|my family|my mom|my dad|my sister|my brother|my wife|my husband)\b',
            r'\b(?:today|yesterday|last night|this morning|this evening|weekend)\s+(?:i|we|my)\b',
            r'\bi\s+(?:went|going|came|coming|visited|visited|bought|got|found)\b',
            r'\b(?:believe in yourself|stay positive|keep going|never give up|trust the process|stay patient|discipline)\b',
            r'\b(?:growth|success|failure|mindset|hustle|grind|motivation|inspire|journey)\b',
            r"\bi (?:do not|don't|am|was)\b",
            r"\bthis is\b",
            r"\bi think\b",
            r"\bwhy is\b",
        ]

        # ── Weighted Scoring Lists ──
        self.strong_anchors = ["javascript", "python", "java", "api", "database", "server", "algorithm", "git"]
        self.weak_anchors = ["system", "tool", "platform", "service", "app", "project"]
        self.ambiguous_terms = ["react", "express", "spring", "go", "ruby", "rust"]
        self.emotional_words = ["love", "hate", "boring", "amazing", "bad", "good", "sad", "happy"]
        self.generic_words = ["thing", "stuff", "something", "anything"]

        self.phrase_penalties = [
            r"\bi do not\b", r"\bi don't\b", r"\bi am\b", r"\bi was\b", r"\bi feel\b", r"\bi think\b", r"\bi believe\b",
            r"\bi guess\b", r"\bi just\b", r"\bi really\b", r"\bi love\b", r"\bi hate\b",
            r"\bthis is\b", r"\bthat is\b", r"\bit is\b", r"\bit was\b", r"\bthere is\b", r"\bthere was\b",
            r"\bwhy is\b", r"\bwhat is\b", r"\bhow is\b", r"\bdoes this\b", r"\bcan this\b",
            r"\bthis is boring\b", r"\bthis is amazing\b", r"\bthis is bad\b", r"\bthis is good\b", r"\bso annoying\b", r"\bvery nice\b",
            r"\bthis thing\b", r"\bthat thing\b", r"\bsomething\b", r"\banything\b", r"\bstuff\b",
            r"\bi like\b", r"\bi enjoy\b", r"\bi prefer\b", r"\bi want\b", r"\bi need\b"
        ]

        self._compiled_phrase_penalties = [
            re.compile(p, re.IGNORECASE) for p in self.phrase_penalties
        ]

        # ── Context Analysis definitions ──
        self.safe_words = {
            "kill", "shoot", "execute", "bomb", "blast", "attack", "die", "dead",
            "crack", "weed", "hash", "dump", "hook", "salt", "ice", "pot", "coke"
        }

        self.safe_context_patterns = [
            (r'\b(background)?\s*process(es)?\b', 'system_process'),
            (r'\b(port|pid|task|server|app|daemon|service|thread|job)\b', 'tech_entity'),
            (r'\b(photo|video|screen)?\s*shoot\b', 'media_production'),
            (r'\b(code|script|query|command|file)\b', 'code_execution'),
            (r'\b(error|bug|exception|crash)\b', 'debugging'),
            (r'\b(password|hash|salt|encryption)\b', 'security'),
            (r'\b(game|player|enemy|level)\b', 'gaming')
        ]

        self.harmful_context_patterns = {
            "violence": [
                (r'\b(person|people|someone|anyone|everybody|him|her|them|you|myself)\b', 0.9),
                (r'\b(school|mall|crowd|building)\b', 0.95),
                (r'\b(blood|weapon|gun|knife)\b', 0.8),
            ],
            "harm": [
                (r'\b(myself|my life|all|everything)\b', 0.9),
                (r'\b(tired of living|want to end it|no reason)\b', 0.95),
            ],
            "drugs": [
                (r'\b(buy|sell|deal|smoke|snort|inject|high|drunk)\b', 0.85),
            ]
        }

        # ── Compile all patterns ──────────────────────────────────────────────

        self._compiled_banned = {}
        for category, keywords in self.banned_categories.items():
            for kw in keywords:
                escaped = re.escape(kw)
                pattern = rf'\b{escaped}\b'
                self._compiled_banned[re.compile(pattern, re.IGNORECASE)] = (kw, category)

        self._compiled_hindi = []
        for category, patterns in self.hindi_galis.items():
            for pattern in patterns:
                self._compiled_hindi.append((re.compile(pattern, re.IGNORECASE), category))

        # English profanity: compiled as-is (already include their own anchoring)
        self._compiled_english_profanity = [
            re.compile(p, re.IGNORECASE)
            for p in self.english_profanity_patterns
        ]

        self._compiled_allowlist = [
            re.compile(p, re.IGNORECASE) for p in self.allowlist_patterns
        ]

        self._compiled_tech_urls = [
            re.compile(p, re.IGNORECASE) for p in self.tech_url_patterns
        ]

        self._compiled_code_signals = [
            re.compile(p, re.IGNORECASE | re.MULTILINE) for p in self.code_signal_patterns
        ]

        self._compiled_non_tech = [
            re.compile(p, re.IGNORECASE) for p in self.non_tech_signals
        ]

        self._compiled_off_topic_sentence = [
            re.compile(p, re.IGNORECASE) for p in self.off_topic_sentence_signals
        ]

        self.url_patterns = [
            r'bit\.ly', r'goo\.gl', r't\.co', r'tinyurl\.com', r'is\.gd',
            r'buff\.ly', r't\.me', r'crypto', r'free-prizes', r'shorturl',
            r'ow\.ly', r'short\.link', r'rb\.gy', r'cutt\.ly', r'shorten',
            r'tiny\.cc', r'tr\.im', r'v\.gd', r'cli\.gs', r'shrinke\.me'
        ]

        self.spam_patterns = [
            r'(.)\1{5,}',
            r'\b(viagra|casino|lottery|winner|congratulations|prize|won\s+\d+|\$\d+[kKmM]|\d+[kKmM]\$)\b',
            r'\b(click here|like and share|comment below)\b',
            r'\b(limited time offer|act now|don\'t miss out|earn \$|make \$)\b',
        ]

        self.url_regex  = re.compile('|'.join(self.url_patterns), re.IGNORECASE)
        self.spam_regex = re.compile('|'.join(self.spam_patterns), re.IGNORECASE)

        logger.info("✅ Rule Engine initialized with enhanced context awareness (Hybrid & Context Analysis)")

    # ──────────────────────────────────────────────────────────
    #  Context analysis
    # ──────────────────────────────────────────────────────────

    def _analyze_context(self, text: str, matched_word: str, category: str) -> Dict[str, Any]:
        text_lower = text.lower()

        if matched_word.lower() in self.safe_words:
            return {'is_harmful': False, 'confidence': 0.95, 'context_type': 'safe_word',
                    'reasoning': f"'{matched_word}' is in safe words list"}

        for pattern, context_type in self.safe_context_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                start = max(0, match.start() - 30)
                end   = min(len(text_lower), match.end() + 30)
                if matched_word.lower() in text_lower[start:end]:
                    return {'is_harmful': False, 'confidence': 0.9, 'context_type': context_type,
                            'reasoning': f"Found in safe {context_type} context"}

        for harm_category, patterns in self.harmful_context_patterns.items():
            for pattern, weight in patterns:
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    start = max(0, match.start() - 30)
                    end   = min(len(text_lower), match.end() + 30)
                    if matched_word.lower() in text_lower[start:end]:
                        return {'is_harmful': True, 'confidence': weight,
                                'context_type': harm_category,
                                'reasoning': f"Found in harmful {harm_category} context"}

        words = text_lower.split()
        for i, word in enumerate(words):
            if matched_word.lower() in word:
                start = max(0, i - 5)
                end   = min(len(words), i + 6)
                surrounding = words[start:end]

                educational_verbs = ['learn', 'study', 'practice', 'master', 'develop',
                                     'improve', 'build', 'create']
                if any(verb in surrounding for verb in educational_verbs):
                    return {'is_harmful': False, 'confidence': 0.85, 'context_type': 'educational',
                            'reasoning': "Found near educational verbs"}

                harmful_pronouns = ['i', 'me', 'myself', 'you', 'yourself']
                harmful_verbs    = ['want', 'need', 'will', 'going', 'plan', 'threat']
                if (any(p in surrounding for p in harmful_pronouns) and
                        any(v in surrounding for v in harmful_verbs)):
                    return {'is_harmful': True, 'confidence': 0.8,
                            'context_type': 'personal_threat',
                            'reasoning': "Personal context with harmful intent"}

        if category in ["violence", "harm"]:
            return {'is_harmful': True, 'confidence': 0.6, 'context_type': 'neutral_but_risky',
                    'reasoning': f"Category '{category}' default to suspicious"}

        return {'is_harmful': True, 'confidence': 0.5, 'context_type': 'unknown',
                'reasoning': "No clear context, defaulting to suspicious"}

    def normalize_text(self, text: str) -> str:
        leet_map = {
            '0': 'o', '1': 'i', '2': 'z', '3': 'e', '4': 'a',
            '5': 's', '6': 'b', '7': 't', '8': 'b', '9': 'g',
            '@': 'a', '$': 's', '!': 'i', '+': 't', '|': 'i'
        }
        normalized = text.lower()
        for leet, char in leet_map.items():
            normalized = normalized.replace(leet, char)
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = ' '.join(normalized.split())
        return normalized

    # ──────────────────────────────────────────────────────────
    #  Sentence-level mixing detection
    # ──────────────────────────────────────────────────────────

    def _split_sentences(self, text: str) -> List[str]:
        sentences = re.split(r'[.!?\n]+', text.strip())
        valid = []
        for s in sentences:
            s_clean = s.strip()
            if not s_clean:
                continue
            if len(s_clean.split()) >= 4 or self._sentence_has_tech(s_clean):
                valid.append(s_clean)
        return valid

    def _sentence_has_tech(self, sentence: str) -> bool:
        s_lower = sentence.lower()
        for category, terms in self.tech_taxonomy.items():
            for term in terms:
                if ' ' in term:
                    if term in s_lower:
                        return True
                else:
                    if re.search(rf'\b{re.escape(term)}\b', s_lower):
                        return True
        for pattern in self._compiled_code_signals:
            if pattern.search(sentence):
                return True
        return False

    def _sentence_is_off_topic(self, sentence: str) -> bool:
        s_lower = sentence.lower()
        for pattern in self._compiled_off_topic_sentence:
            if pattern.search(s_lower):
                return True
        return False

    def _detect_content_mixing(self, text: str) -> Dict[str, Any]:
        sentences = self._split_sentences(text)

        if len(sentences) <= 1:
            return {
                "mixing_detected": False,
                "off_topic_sentences": [],
                "tech_sentences": [],
                "total_sentences": len(sentences),
                "mixing_penalty": 0.0,
            }

        tech_sentences      = []
        off_topic_sentences = []

        for sentence in sentences:
            has_tech = self._sentence_has_tech(sentence)
            is_off   = self._sentence_is_off_topic(sentence)

            if has_tech and not is_off:
                tech_sentences.append(sentence)
            elif is_off and not has_tech:
                off_topic_sentences.append(sentence)
            else:
                off_topic_sentences.append(sentence)

        total   = len(sentences)
        n_off   = len(off_topic_sentences)
        n_tech  = len(tech_sentences)
        mixing_detected = n_off >= 1 and n_tech >= 1

        if mixing_detected:
            off_ratio = n_off / total
            if off_ratio <= 0.25:
                mixing_penalty = 0.30
            elif off_ratio <= 0.40:
                mixing_penalty = 0.45
            elif off_ratio <= 0.60:
                mixing_penalty = 0.60
            else:
                mixing_penalty = 0.75
        else:
            mixing_penalty = 0.0

        return {
            "mixing_detected":    mixing_detected,
            "off_topic_sentences": off_topic_sentences,
            "tech_sentences":     tech_sentences,
            "total_sentences":    total,
            "mixing_penalty":     mixing_penalty,
        }

    # ──────────────────────────────────────────────────────────
    #  Tech relevance scoring (Hybrid Model)
    # ──────────────────────────────────────────────────────────

    def check_tech_relevance(self, text: str) -> Dict[str, Any]:
        if not text or not text.strip():
            return {
                "tech_relevance_score": 0.0,
                "zone": "off_topic",
                "matched_categories": [],
                "matched_terms": [],
                "non_tech_signals": [],
                "mixing": {"mixing_detected": False, "off_topic_sentences": [],
                           "tech_sentence_count": 0, "total_sentences": 0, "mixing_penalty": 0.0},
                "details": {}
            }

        text_lower = text.lower()
        words      = text_lower.split()

        strong_anchors_found   = set()
        weak_anchors_found     = set()
        ambiguous_terms_found  = set()
        emotional_matches      = set()
        generic_matches        = set()
        phrase_matches         = set()

        combined_strong = self.strong_anchors + self.tech_anchors
        for w in set(combined_strong):
            if (' ' not in w and re.search(rf'\b{re.escape(w)}\b', text_lower)) or \
               (' ' in w and w in text_lower):
                strong_anchors_found.add(w)

        category_hits    = []
        all_legacy_hits  = []
        for cat, terms in self.tech_taxonomy.items():
            for w in terms:
                if (' ' not in w and re.search(rf'\b{re.escape(w)}\b', text_lower)) or \
                   (' ' in w and w in text_lower):
                    category_hits.append(cat)
                    all_legacy_hits.append(w)
                    if w not in self.weak_anchors and w not in self.ambiguous_terms:
                        strong_anchors_found.add(w)

        for w in self.weak_anchors:
            if (' ' not in w and re.search(rf'\b{re.escape(w)}\b', text_lower)) or \
               (' ' in w and w in text_lower):
                weak_anchors_found.add(w)

        for w in self.ambiguous_terms:
            if (' ' not in w and re.search(rf'\b{re.escape(w)}\b', text_lower)) or \
               (' ' in w and w in text_lower):
                ambiguous_terms_found.add(w)

        for w in self.emotional_words:
            if re.search(rf'\b{re.escape(w)}\b', text_lower):
                emotional_matches.add(w)
        for w in self.generic_words:
            if re.search(rf'\b{re.escape(w)}\b', text_lower):
                generic_matches.add(w)
        for pattern in self._compiled_phrase_penalties:
            m = pattern.search(text_lower)
            if m:
                phrase_matches.add(m.group())
        for pattern in self._compiled_off_topic_sentence:
            m = pattern.search(text_lower)
            if m:
                phrase_matches.add(m.group())

        score = 0
        penalties_applied      = {}
        validated_ambiguous    = []

        if strong_anchors_found:
            score += 3 * len(strong_anchors_found)

        for pattern in self._compiled_tech_urls:
            if pattern.search(text):
                strong_anchors_found.add("tech_url")
                score += 3
                break
        for pattern in self._compiled_code_signals:
            if pattern.search(text):
                strong_anchors_found.add("code_snippet")
                score += 3
                break

        if weak_anchors_found:
            score += 1 * len(weak_anchors_found)

        for term in ambiguous_terms_found:
            if strong_anchors_found:
                score += 2
                validated_ambiguous.append(f"{term} (+2)")
            elif weak_anchors_found:
                score += 1
                validated_ambiguous.append(f"{term} (+1)")
            else:
                validated_ambiguous.append(f"{term} (ignored)")

        if phrase_matches:
            penalty = 2 * len(phrase_matches)
            score  -= penalty
            penalties_applied["phrase_penalties"] = -penalty
        if emotional_matches:
            penalty = 2 * len(emotional_matches)
            score  -= penalty
            penalties_applied["emotional_words"] = -penalty
        if generic_matches:
            penalty = 2 * len(generic_matches)
            score  -= penalty
            penalties_applied["generic_words"] = -penalty

        mixing = self._detect_content_mixing(text)
        if mixing["mixing_detected"]:
            score -= 3
            penalties_applied["content_mixing"] = -3

        zone = "tech" if score > 0 else "off_topic"

        details = {
            "original_text":           text,
            "tokens_detected":         len(words),
            "strong_anchors_found":    list(strong_anchors_found),
            "weak_anchors_found":      list(weak_anchors_found),
            "ambiguous_terms_found":   list(ambiguous_terms_found),
            "validated_ambiguous_terms": validated_ambiguous,
            "phrase_matches":          list(phrase_matches),
            "emotional_matches":       list(emotional_matches),
            "generic_matches":         list(generic_matches),
            "penalties_applied":       penalties_applied,
            "final_score":             score,
            "final_decision":          zone,
        }

        result = {
            "tech_relevance_score": float(score),
            "zone":                 zone,
            "matched_categories":   list(set(category_hits)),
            "matched_terms":        list(strong_anchors_found) + list(ambiguous_terms_found) + list(weak_anchors_found),
            "non_tech_signals":     list(phrase_matches) + list(emotional_matches) + list(generic_matches),
            "mixing":               mixing,
            "details":              details,
        }

        logger.info(f"Hybrid Relevance Engine Debug Logs:\n{json.dumps(details)}")
        return result

    # ──────────────────────────────────────────────────────────
    #  Harm rules
    # ──────────────────────────────────────────────────────────

    def check_rules(self, text: str) -> Dict[str, Any]:
        """Check text against all harm rules. Uses context filtering."""
        text_stripped = text.strip()
        normalized    = self.normalize_text(text_stripped)

        results = {
            "banned_keywords":    [],
            "keyword_categories": [],
            "suspicious_urls":    [],
            "spam_detected":      False,
            "violations":         [],
            "hindi_detection":    {"has_hindi_abuse": False, "matched_words": []},
            "english_profanity_detected": False,
        }

        if not text_stripped:
            results["rule_score"] = 0.0
            return results

        # Step 0: Mask allowlisted spans
        masked_text = text_stripped
        for pattern in self._compiled_allowlist:
            masked_text = pattern.sub(lambda m: '_' * len(m.group()), masked_text)

        masked_normalized = normalized
        for pattern in self._compiled_allowlist:
            masked_normalized = pattern.sub(lambda m: '_' * len(m.group()), masked_normalized)

        # Step 1: Banned keywords (context-analyzed)
        for pattern, (keyword, category) in self._compiled_banned.items():
            if pattern.search(masked_text) or pattern.search(masked_normalized):
                context_result = self._analyze_context(text_stripped, keyword, category)
                if context_result['is_harmful']:
                    results["banned_keywords"].append(keyword)
                    results["keyword_categories"].append(category)
                    results["violations"].append(f"keyword:{keyword}")
                else:
                    logger.debug(
                        f"Context override for '{keyword}': {context_result['reasoning']}"
                    )

        # Step 2: Hindi galis
        hindi_matched = []
        for pattern, category in self._compiled_hindi:
            if pattern.search(masked_text) or pattern.search(masked_normalized):
                hindi_matched.append(category)
                if category not in results["keyword_categories"]:
                    results["keyword_categories"].append(category)
                results["violations"].append(f"hindi_abuse:{category}")

        if hindi_matched:
            results["hindi_detection"]["has_hindi_abuse"] = True
            results["hindi_detection"]["matched_words"]   = list(set(hindi_matched))
            if "bhenchod"  in hindi_matched: results["banned_keywords"].append("bc")
            if "madarchod" in hindi_matched: results["banned_keywords"].append("mc")
            if "bsdk"      in hindi_matched: results["banned_keywords"].append("bsdk")

        # Step 3: English profanity (leet-speak aware) ─────────────────────────
        # These patterns already contain their own character-class anchoring.
        # We run them against the original masked text only (not leet-normalized)
        # because the patterns themselves handle leet substitutions (e.g. [s$]).
        profanity_hit = False
        for pattern in self._compiled_english_profanity:
            if pattern.search(masked_text):
                profanity_hit = True
                results["violations"].append("english_profanity")
                if "sexual" not in results["keyword_categories"]:
                    results["keyword_categories"].append("sexual")
                break   # one hit is enough to flag; avoid stacking violations

        if profanity_hit:
            results["english_profanity_detected"] = True
            results["banned_keywords"].append("profanity")
            logger.info("🔞 English profanity pattern matched")

        # Step 4: Suspicious URLs
        urls = self.url_regex.findall(text_stripped.lower())
        if urls:
            results["suspicious_urls"] = list(set(urls))
            results["violations"].append("suspicious_url")

        # Step 5: Spam
        spam_matches = self.spam_regex.findall(text_stripped)
        if spam_matches:
            spam_count = len(spam_matches)
            if spam_count > 2 or any(
                kw in text_stripped.lower()
                for kw in ["earn money", "winner", "congratulations", "cash prize",
                           "click here", "free bitcoin", "guaranteed returns"]
            ):
                results["spam_detected"] = True
                results["violations"].append("spam")

        # Step 6: Hindi/Hinglish normalizer
        hindi_check = text_normalizer.detect_hindi_abuse(text_stripped)
        if hindi_check["has_hindi_abuse"]:
            for word in hindi_check["matched_words"]:
                results["banned_keywords"].append(word)
                if "hindi_abuse" not in results["keyword_categories"]:
                    results["keyword_categories"].append("hindi_abuse")
                results["violations"].append(f"hindi_abuse:{word}")
            results["hindi_detection"] = hindi_check

        # Score calculation
        unique_violations = len(set(results["violations"]))

        if unique_violations == 0:
            results["rule_score"] = 0.0
        elif unique_violations == 1:
            if any(cat in ["violence", "harm", "sexual"] for cat in results["keyword_categories"]):
                results["rule_score"] = 0.5
            elif "hindi_abuse" in results["keyword_categories"]:
                results["rule_score"] = 0.4
            else:
                results["rule_score"] = 0.2
        elif unique_violations == 2:
            if any(cat in ["violence", "harm", "sexual"] for cat in results["keyword_categories"]):
                results["rule_score"] = 0.7
            elif "spam" in results["violations"]:
                results["rule_score"] = 0.3
            else:
                results["rule_score"] = 0.4
        else:
            results["rule_score"] = 0.8

        severity_multiplier = 1.0
        if "violence"    in results["keyword_categories"]: severity_multiplier = 1.2
        if "harm"        in results["keyword_categories"]: severity_multiplier = 1.2
        if "sexual"      in results["keyword_categories"]: severity_multiplier = 1.1
        if "hindi_abuse" in results["keyword_categories"]: severity_multiplier = 1.1

        results["rule_score"] = min(results["rule_score"] * severity_multiplier, 1.0)

        if results["rule_score"] > 0:
            logger.info(
                f"📊 Rule score: {results['rule_score']:.2f} "
                f"(violations={unique_violations}, categories={results['keyword_categories']})"
            )

        return results
