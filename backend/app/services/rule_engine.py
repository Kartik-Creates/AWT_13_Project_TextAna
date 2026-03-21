import re
from typing import List, Dict, Any, Set
import logging
 
from app.ml.text_normalizer import text_normalizer
 
logger = logging.getLogger(__name__)
 
class RuleEngine:
    """Rule-based content filtering with word-boundary matching.
    
    Uses \\b word-boundary regex to avoid false positives like
    'skill' matching 'kill' or 'studied' matching 'die'.
    """
    
    def __init__(self):
        # ── Hindi Gali Mappings (variations and spellings) ──
        self.hindi_galis = {
            "madarchod": [
                r'madar?ch?od', r'madar ?chod', r'madar ?ch?od', r'mdrchod',
                r'mdr ?chod', r'motherchod', r'mother ?chod', r'motherch?od',
                r'mdrch?d', r'madarjaat', r'madar ?jaat', r'madar ?zat',
                r'mc', r'm\.?c\.?', r'm\s*c'
            ],
            "bhenchod": [
                r'b(?:e|o|a|h)?henchod', r'be?hen ?chod', r'b(?:e|o)hn ?chod',
                r'b(?:e|o)han ?chod', r'bc', r'b\.?c\.?', r'b\s*c', r'b\.c',
                r'behench?d', r'bhen ?ch?d', r'sisterfucker', r'sister ?fucker'
            ],
            "chutiya": [
                r'chutiya', r'chutiye', r'chut?iya', r'chut?iye', r'chutiya',
                r'choot?iya', r'choot?iye', r'chut?ya', r'choot?ya',
                r'chut?ye', r'choot?ye', r'ch*t*iya'
            ],
            "gandu": [
                r'gandu', r'gand?u', r'gandoo', r'gand?oo', r'gandhu',
                r'gand?hu', r'gandu', r'gaa?ndu', r'gand ?u'
            ],
            "randi": [
                r'randi', r'rand?i', r'randee', r'rand?ee', r'r*ndi',
                r'randi ?ka', r'randi ?ke', r'randi ?ki'
            ],
            "bhosdi": [
                r'bhosdi', r'bhosd?i', r'bhosdike', r'bhosdi ?ke',
                r'bhosd?ike', r'bhosda', r'bhosd?a', r'bhosd?a'
            ],
            "kutta": [
                r'kutta', r'kutta ?ka', r'kutte', r'kutte ?ka',
                r'kutia', r'kutiya', r'kut?iya', r'kut?ia'
            ],
            "chinal": [
                r'chinal', r'ch?inal', r'chinnal', r'ch?innal',
                r'chilnal', r'ch?ilnal'
            ],
            "harami": [
                r'harami', r'haram?i', r'hara?mi', r'haram ?i',
                r'haramza?de', r'haramzade', r'haram ?zade'
            ],
            "sala": [
                r'sala', r'sa?la', r'saale', r'sa?le', r'saal?e'
            ],
            "lavde": [
                r'lavde', r'lavd?e', r'lawde', r'lawd?e', r'l*avde',
                r'lode', r'lod?e', r'laude', r'laud?e', r'lo?de',
                r'la?ude', r'lvde', r'lv?de', r'la?vde', r'lo?vde'
            ],
            "chod": [
                r'chod', r'ch?od', r'chodd?', r'ch?odd?',
                r'ch*d', r'fuck', r'f\*ck', r'f\*\*k', r'f.u.c.k',
                r'fuk', r'fak', r'phuck'
            ],
            "lund": [
                r'lund', r'l*nd', r'lun?d', r'lound', r'lond'
            ],
            "gaand": [
                r'gaand', r'gaa?nd', r'gand', r'g\*nd', r'ass'
            ],
            "tatte": [
                r'tatte', r'tat?te', r't*tte', r'balls'
            ],
            "bsdk": [
                r'bsdk', r'b\.?s\.?d\.?k\.?', r'b\s*s\s*d\s*k', r'b s d k',
                r'behen ke', r'bahan ke', r'bhen ke'
            ]
        }
        
        # Core categories of harmful content
        self.banned_categories = {
            "drugs": [
                "drugs", "heroin", "cocaine", "weed", "meth",
                "fentanyl", "dealer", "drug dealer", "coke", "crack",
                "mdma", "ecstasy", "lsd", "acid", "shrooms", "mushrooms",
                "opium", "morphine", "oxy", "percocet", "xanax", "valium",
                "diazepam", "amphetamine", "methamphetamine", "ice",
                "crystal meth", "dope", "smack", "skunk", "ganja",
                "bhang", "charas", "hash", "hashish", "weed", "pot",
                "marijuana", "cannabis", "thc", "cbd", "vape", "vaping",
                "nicotine", "tobacco", "cigarette", "cigar"
            ],
            "violence": [
                "kill you", "kill them", "kill him", "kill her",
                "kill everyone", "murder", "bomb", "shoot",
                "attack", "mass shooting", "gun violence", "shoot up",
                "stab", "stabbing", "beat up", "beat you", "beat him",
                "beat her", "slap", "punch", "kick", "torture",
                "execute", "execution", "assassinate", "assassination",
                "terrorist", "terrorism", "jihad", "martyr", "martyrdom",
                "explode", "explosion", "blast", "bombing", "suicide bomb"
            ],
            "harm": [
                "suicide", "self-harm", "self harm", "cutting myself",
                "hang myself", "end my life", "want to die", "kill myself",
                "take my life", "end it all", "end it now", "better off dead",
                "no reason to live", "worthless", "want to disappear",
                "jump off", "jump from", "overdose", "od on", "rope",
                "pills", "sleep forever", "never wake up"
            ],
            "offensive": [
                "nazi", "terrorist", "white supremacy", "kkk", "ku klux",
                "hitler", "fascist", "neo-nazi", "racial slurs", "racist",
                "homophobic", "transphobic", "xenophobic", "islamophobic",
                "antisemitic", "anti-semitic", "jew hating", "black hating"
            ],
            "sexual": [
                "nude", "nudes", "pics", "photos", "send pics", "send nudes",
                "sext", "sexting", "sex tape", "private video", "leaked",
                "leak", "exposed", "expose", "blackmail", "coerce", "forced",
                "creampie", "slut", "whore", "c*ck", "d*ck", "pussy",
                "tits", "boobs", "ass", "booty", "anal", "oral",
                "blowjob", "handjob", "fuck", "fucking", "suck",
                "rape", "raped", "raping", "molest", "molested"
            ],
            "promotional": [
                "earn money", "make money", "work from home",
                "zero effort", "no investment", "cash prize",
                "get rich quick", "bitcoin", "crypto", "cryptocurrency",
                "investment", "invest now", "guaranteed returns",
                "double your money", "money back", "profit",
                "referral", "refer and earn", "sign up bonus",
                "free money", "free cash", "free bitcoin",
                "click here", "link in bio", "link in profile",
                "dm me", "message me", "whatsapp me", "telegram"
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
            r'\bsoldier(?:s)?\b',
            r'\baudience(?:s)?\b',
            r'\bdie(?:sel|t|tary|titian|tetics)\b',
            r'\bdied(?:re)?\b',
            r'\bdies\b',
            r'\bdeadline(?:s)?\b',
            r'\bdeadwood\b',
            r'\bheart\s+attack\b',
            r'\bpanic\s+attack\b',
            r'\basthma\s+attack\b',
            r'\banxiety\s+attack\b',
            r'\bbomb(?:astic|shell)\b',
            r'\bphotobomb\b',
            r'\b(?:the|this|that)\s+bomb\b',
            r'\bweed(?:s|ing|ed)?\s+(?:the|my|our|your|a)\s+(?:garden|yard|lawn|bed|field|plant|patch)\b',
            r'\bpull(?:ing)?\s+(?:out\s+)?weeds?\b',
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
            r'\b(?:dental|medical)\s+cocaine\b',
        ]
        
        # ── Tech Taxonomy ──
        self.tech_taxonomy = {
            "languages": [
                "python", "javascript", "typescript", "java", "kotlin", "swift",
                "rust", "golang", "go", "cpp", "c++", "csharp", "c#", "ruby", "php",
                "scala", "dart", "elixir", "haskell", "lua", "perl", "bash",
                "powershell", "solidity", "assembly", "cobol", "fortran",
                "matlab", "julia", "groovy", "clojure", "erlang", "ocaml",
                "fsharp", "f#", "zig", "nim", "crystal", "v lang", "mojo"
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
                "gitops", "devsecops", "serverless", "lambda", "cloud run"
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
                "model training", "inference", "quantization", "lora", "qlora"
            ],
            "tools_concepts": [
                "api", "rest", "graphql", "grpc", "websocket", "jwt", "oauth",
                "git", "github", "gitlab", "bitbucket", "vscode", "vim",
                "neovim", "npm", "yarn", "pnpm", "pip", "virtualenv", "conda",
                "poetry", "cargo", "gradle", "maven", "makefile", "dockerfile",
                "openapi", "swagger", "postman", "insomnia", "json", "yaml",
                "toml", "protobuf", "orm", "sdk", "cli", "tui", "microservices",
                "monorepo", "monolith", "event-driven", "message queue",
                "kafka", "rabbitmq", "redis pubsub", "websockets", "sse",
                "caching", "load balancer", "reverse proxy", "cdn", "dns",
                "ssl", "tls", "http", "https", "tcp", "udp", "ip", "grpc",
                "design pattern", "solid principles", "clean code",
                "test driven", "tdd", "bdd", "unit test", "integration test",
                "end to end", "e2e", "playwright", "selenium", "cypress",
                "jest", "pytest", "mocha", "vitest", "storybook", "figma"
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
                "vulnerability", "encryption", "vpn", "firewall",
                "zero trust", "siem", "threat hunting", "bug bounty",
                "zero day", "exploit", "cve", "owasp", "devsecops",
                "static analysis", "dynamic analysis", "fuzzing",
                "reverse engineering", "malware analysis", "incident response",
                "soc analyst", "threat intelligence", "network security",
                "application security", "appsec", "red team", "blue team"
            ],
            "tech_culture": [
                "open source", "hackathon", "leetcode", "competitive programming",
                "system design", "code review", "pull request", "merge request",
                "standup", "sprint", "agile", "scrum", "kanban", "jira",
                "stackoverflow", "stack overflow", "tech interview", "dsa",
                "data structures", "algorithms", "big o", "complexity",
                "refactor", "technical debt", "codebase", "repository",
                "developer", "programmer", "engineer", "devrel",
                "side project", "startup", "saas", "paas", "iaas"
            ]
        }
 
        # ── Tech URL domains (strong positive signal) ──
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
            r'medium\.com.*(?:tech|code|program|develop|engineer)',
            r'hashnode\.com', r'substack\.com.*(?:tech|code|dev)',
            r'arxiv\.org', r'huggingface\.co', r'kaggle\.com',
        ]
 
        # ── Code / Tech signal patterns ──
        self.code_signal_patterns = [
            r'```[\w]*\n',                          # Code blocks
            r'\bv\d+\.\d+(?:\.\d+)?\b',            # Version numbers like v1.2.3
            r'\b\d+\.\d+\.\d+\b',                  # Semver 1.2.3
            r'(?:import|from)\s+\w+',              # Python/JS imports
            r'(?:def|class|function|const|let|var|async|await)\s+\w+',  # Code keywords
            r'(?:=>|->|::|\.\.\.)',                 # Code operators
            r'(?:npm|yarn|pip|cargo|go)\s+(?:install|add|run|build|test)',  # Package commands
            r'(?:git\s+(?:clone|push|pull|commit|merge|rebase|checkout))',  # Git commands
            r'(?:docker\s+(?:run|build|push|pull|compose))',               # Docker commands
            r'\$\s+\w+',                            # Terminal commands
            r'#\s*(?:TODO|FIXME|HACK|NOTE|BUG):',  # Code comments
            r'(?:localhost|127\.0\.0\.1):\d+',      # Local dev URL
            r'(?:GET|POST|PUT|PATCH|DELETE)\s+/',   # HTTP methods
            r'(?:200|201|400|401|403|404|500)\b',   # HTTP status codes
            r'O\((?:n|log n|n log n|n²|1)\)',       # Big O notation
        ]
 
        # ── Non-tech signals (off-topic indicators) ──
        self.non_tech_signals = [
            # Food & recipes
            r'\b(?:recipe|cooking|baking|ingredients|cuisine|restaurant|food|meal|dish|snack|breakfast|lunch|dinner)\b',
            # Sports
            r'\b(?:cricket|football|soccer|basketball|tennis|ipl|nba|fifa|match score|wicket|century|goal|stadium)\b',
            # Celebrity / entertainment
            r'\b(?:celebrity|bollywood|hollywood|actor|actress|movie star|singer|musician|concert|album release|fan club)\b',
            # Politics
            r'\b(?:election|politician|parliament|senate|congress|minister|president|prime minister|vote|campaign|party rally)\b',
            # Religion
            r'\b(?:temple|mosque|church|prayer|worship|sermon|festival|puja|namaz|mass|pilgrimage)\b',
            # Relationships / personal life
            r'\b(?:girlfriend|boyfriend|marriage|wedding|divorce|breakup|date night|anniversary|proposal)\b',
            # Fashion & lifestyle
            r'\b(?:outfit|fashion|clothing|makeup|skincare|haircut|salon|wardrobe|style tips)\b',
        ]
 
        # Compile all patterns
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
 
        self._compiled_allowlist = [
            re.compile(p, re.IGNORECASE) for p in self.allowlist_patterns
        ]
 
        # Compile tech URL patterns
        self._compiled_tech_urls = [
            re.compile(p, re.IGNORECASE) for p in self.tech_url_patterns
        ]
 
        # Compile code signal patterns
        self._compiled_code_signals = [
            re.compile(p, re.IGNORECASE | re.MULTILINE) for p in self.code_signal_patterns
        ]
 
        # Compile non-tech signal patterns
        self._compiled_non_tech = [
            re.compile(p, re.IGNORECASE) for p in self.non_tech_signals
        ]
 
        # Suspicious URL patterns
        self.url_patterns = [
            r'bit\.ly', r'goo\.gl', r't\.co', r'tinyurl\.com', r'is\.gd',
            r'buff\.ly', r't\.me', r'crypto', r'free-prizes', r'shorturl',
            r'ow\.ly', r'short\.link', r'rb\.gy', r'cutt\.ly', r'shorten',
            r'tiny\.cc', r'tr\.im', r'v\.gd', r'cli\.gs', r'shrinke\.me'
        ]
 
        # Spam patterns
        self.spam_patterns = [
            r'(.)\1{4,}',
            r'[A-Z]{10,}',
            r'\b(viagra|casino|lottery|winner|congratulations|prize|won\s+\d+|\$\d+|\d+\$)\b',
            r'\b(click here|subscribe|share|like and share|comment below)\b',
            r'\b(free|cheap|discount|offer|limited time|act now|don\'t miss)\b'
        ]
 
        self.url_regex = re.compile('|'.join(self.url_patterns), re.IGNORECASE)
        self.spam_regex = re.compile('|'.join(self.spam_patterns), re.IGNORECASE)
 
    def normalize_text(self, text: str) -> str:
        """Normalize text to catch leetspeak and variations."""
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
 
    def check_tech_relevance(self, text: str) -> Dict[str, Any]:
        """Score how tech-relevant a post is.
 
        Returns a dict with:
          - tech_relevance_score (0.0–1.0): higher = more tech
          - zone: "tech" | "review" | "off_topic"
          - matched_categories: list of taxonomy categories that matched
          - matched_terms: sample of matched tech terms
          - non_tech_signals: off-topic signals detected
          - details: breakdown for debugging
        """
        if not text or not text.strip():
            return {
                "tech_relevance_score": 0.0,
                "zone": "off_topic",
                "matched_categories": [],
                "matched_terms": [],
                "non_tech_signals": [],
                "details": {}
            }
 
        text_lower = text.lower()
        words = text_lower.split()
        total_words = max(len(words), 1)
 
        # ── 1. Count tech taxonomy matches ──
        category_hits: Dict[str, List[str]] = {}
        all_matched_terms: List[str] = []
 
        for category, terms in self.tech_taxonomy.items():
            hits = []
            for term in terms:
                if ' ' in term:
                    # Multi-word: substring match
                    if term in text_lower:
                        hits.append(term)
                else:
                    # Single word: word-boundary match
                    if re.search(rf'\b{re.escape(term)}\b', text_lower):
                        hits.append(term)
            if hits:
                category_hits[category] = hits
                all_matched_terms.extend(hits)
 
        unique_terms = len(set(all_matched_terms))
        unique_categories = len(category_hits)
 
        # ── 2. Tech URL bonus ──
        tech_url_bonus = 0.0
        for pattern in self._compiled_tech_urls:
            if pattern.search(text):
                tech_url_bonus = 0.2
                break
 
        # ── 3. Code signal bonus ──
        code_bonus = 0.0
        code_signals_found = []
        for pattern in self._compiled_code_signals:
            if pattern.search(text):
                code_signals_found.append(pattern.pattern)
                code_bonus = min(code_bonus + 0.05, 0.2)
 
        # ── 4. Non-tech signal penalty ──
        non_tech_penalty = 0.0
        matched_non_tech: List[str] = []
        for pattern in self._compiled_non_tech:
            m = pattern.search(text_lower)
            if m:
                matched_non_tech.append(m.group())
                non_tech_penalty = min(non_tech_penalty + 0.15, 0.4)
 
        # ── 5. Base score from term/category count ──
        if unique_terms == 0:
            base_score = 0.0
        elif unique_terms == 1 and unique_categories == 1:
            base_score = 0.35
        elif unique_terms == 2:
            base_score = 0.50
        elif unique_terms <= 4:
            base_score = 0.65
        elif unique_terms <= 7:
            base_score = 0.78
        else:
            base_score = 0.90
 
        # Multi-category bonus: discussing multiple tech areas signals genuine tech post
        if unique_categories >= 3:
            base_score = min(base_score + 0.10, 1.0)
        elif unique_categories == 2:
            base_score = min(base_score + 0.05, 1.0)
 
        # Keyword density bonus
        density = (unique_terms / total_words) * 100
        if density > 10:
            base_score = min(base_score + 0.10, 1.0)
        elif density > 5:
            base_score = min(base_score + 0.05, 1.0)
 
        # ── 6. Combine all signals ──
        final_score = base_score + tech_url_bonus + code_bonus - non_tech_penalty
        final_score = round(max(0.0, min(1.0, final_score)), 3)
 
        # ── 7. Determine zone ──
        if final_score >= 0.45:
            zone = "tech"
        elif final_score >= 0.25:
            zone = "review"
        else:
            zone = "off_topic"
 
        result = {
            "tech_relevance_score": final_score,
            "zone": zone,
            "matched_categories": list(category_hits.keys()),
            "matched_terms": list(set(all_matched_terms))[:15],
            "non_tech_signals": matched_non_tech,
            "details": {
                "base_score": round(base_score, 3),
                "tech_url_bonus": tech_url_bonus,
                "code_bonus": round(code_bonus, 3),
                "non_tech_penalty": round(non_tech_penalty, 3),
                "unique_terms": unique_terms,
                "unique_categories": unique_categories,
                "density_pct": round(density, 2),
                "code_signals_found": len(code_signals_found),
            }
        }
 
        logger.info(
            f"🔍 Tech relevance: score={final_score:.3f}, zone={zone}, "
            f"terms={unique_terms}, categories={list(category_hits.keys())}"
        )
 
        return result
 
    def check_rules(self, text: str) -> Dict[str, Any]:
        """Check text against all harm rules."""
        text_stripped = text.strip()
        normalized = self.normalize_text(text_stripped)
 
        results = {
            "banned_keywords": [],
            "keyword_categories": [],
            "suspicious_urls": [],
            "spam_detected": False,
            "violations": [],
            "hindi_detection": {"has_hindi_abuse": False, "matched_words": []}
        }
 
        if not text_stripped:
            results["rule_score"] = 0.0
            return results
 
        # ── Step 0: Find allowlisted spans ──
        masked_text = text_stripped
        for pattern in self._compiled_allowlist:
            masked_text = pattern.sub(lambda m: '_' * len(m.group()), masked_text)
 
        masked_normalized = normalized
        for pattern in self._compiled_allowlist:
            masked_normalized = pattern.sub(lambda m: '_' * len(m.group()), masked_normalized)
 
        # ── Step 1: Check banned keywords ──
        for pattern, (keyword, category) in self._compiled_banned.items():
            if pattern.search(masked_text) or pattern.search(masked_normalized):
                results["banned_keywords"].append(keyword)
                results["keyword_categories"].append(category)
                results["violations"].append(f"keyword:{keyword}")
 
        # ── Step 2: Check Hindi galis ──
        hindi_matched = []
        for pattern, category in self._compiled_hindi:
            if pattern.search(masked_text) or pattern.search(masked_normalized):
                hindi_matched.append(category)
                if category not in results["keyword_categories"]:
                    results["keyword_categories"].append(category)
                results["violations"].append(f"hindi_abuse:{category}")
 
        if hindi_matched:
            results["hindi_detection"]["has_hindi_abuse"] = True
            results["hindi_detection"]["matched_words"] = list(set(hindi_matched))
            if "bhenchod" in hindi_matched:
                results["banned_keywords"].append("bc")
            if "madarchod" in hindi_matched:
                results["banned_keywords"].append("mc")
            if "bsdk" in hindi_matched:
                results["banned_keywords"].append("bsdk")
 
        # ── Step 3: Check suspicious URLs ──
        urls = self.url_regex.findall(text_stripped.lower())
        if urls:
            results["suspicious_urls"] = list(set(urls))
            results["violations"].append("suspicious_url")
 
        # ── Step 4: Check spam ──
        spam_matches = self.spam_regex.findall(text_stripped)
        if spam_matches:
            spam_count = len(spam_matches)
            if spam_count > 1 or any(
                kw in text_stripped.lower()
                for kw in ["earn money", "winner", "congratulations", "cash prize", "free", "click here"]
            ):
                results["spam_detected"] = True
                results["violations"].append("spam")
 
        # ── Step 5: Check Hindi/Hinglish abuse via normalizer ──
        hindi_check = text_normalizer.detect_hindi_abuse(text_stripped)
        if hindi_check["has_hindi_abuse"]:
            for word in hindi_check["matched_words"]:
                results["banned_keywords"].append(word)
                if "hindi_abuse" not in results["keyword_categories"]:
                    results["keyword_categories"].append("hindi_abuse")
                results["violations"].append(f"hindi_abuse:{word}")
            results["hindi_detection"] = hindi_check
 
        # ── Score calculation ──
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
            else:
                results["rule_score"] = 0.4
        else:
            results["rule_score"] = 0.8
 
        # Severity multiplier
        severity_multiplier = 1.0
        if "violence" in results["keyword_categories"]:
            severity_multiplier = 1.2
        if "harm" in results["keyword_categories"]:
            severity_multiplier = 1.2
        if "sexual" in results["keyword_categories"]:
            severity_multiplier = 1.1
        if "hindi_abuse" in results["keyword_categories"]:
            severity_multiplier = 1.1
 
        results["rule_score"] = min(results["rule_score"] * severity_multiplier, 1.0)
 
        if results["rule_score"] > 0:
            logger.info(
                f"📊 Rule score: {results['rule_score']:.2f} "
                f"(violations={unique_violations}, categories={results['keyword_categories']})"
            )
 
        return results