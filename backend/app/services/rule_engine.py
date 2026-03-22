import re
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

        # ── Off-topic sentence signals — used for mixing detection ──
        # These are patterns that indicate a sentence is clearly personal/casual/unrelated
        self.off_topic_sentence_signals = [
            # Personal observations about animals/people
            r'\bi (?:saw|noticed|watched|found|met)\s+(?:a|an|some|my|this|the)\s+\w+',
            r'\b(?:dog|cat|bird|monkey|elephant|cow|horse|lion|tiger)\b',
            r'\b(?:wearing|sunglasses|outfit|clothes|dress|shirt|shoes)\b',
            r'\b(?:looked|looked like|seemed|appears|feels)\s+(?:more|so|very|really|quite)\b',
            r'\b(?:most humans|most people|everyone|everybody)\b',
            # Food/lifestyle casual
            r'\b(?:ate|eating|cooked|cooking|taste|tasty|delicious|yummy|hungry)\b',
            r'\b(?:movie|film|show|series|episode|season|watch|watched|binge)\b',
            r'\b(?:gym|workout|exercise|fitness|yoga|meditation|sleep|tired|woke up)\b',
            # Personal life casual
            r'\b(?:my friend|my family|my mom|my dad|my sister|my brother|my wife|my husband)\b',
            r'\b(?:today|yesterday|last night|this morning|this evening|weekend)\s+(?:i|we|my)\b',
            r'\bi\s+(?:went|going|came|coming|visited|visited|bought|got|found)\b',
            # Motivational / quote-style
            r'\b(?:believe in yourself|stay positive|keep going|never give up|trust the process|stay patient|discipline)\b',
            r'\b(?:growth|success|failure|mindset|hustle|grind|motivation|inspire|journey)\b',
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

        # Suspicious URL patterns
        self.url_patterns = [
            r'bit\.ly', r'goo\.gl', r't\.co', r'tinyurl\.com', r'is\.gd',
            r'buff\.ly', r't\.me', r'crypto', r'free-prizes', r'shorturl',
            r'ow\.ly', r'short\.link', r'rb\.gy', r'cutt\.ly', r'shorten',
            r'tiny\.cc', r'tr\.im', r'v\.gd', r'cli\.gs', r'shrinke\.me'
        ]

        # Spam patterns
        # Note: [A-Z]{12,} is removed because re.IGNORECASE makes it match any word with 12+ letters
        self.spam_patterns = [
            r'(.)\1{5,}',
            r'\b(viagra|casino|lottery|winner|congratulations|prize|won\s+\d+|\$\d+[kKmM]|\d+[kKmM]\$)\b',
            r'\b(click here|like and share|comment below)\b',
            r'\b(limited time offer|act now|don\'t miss out|earn \$|make \$)\b',
        ]

        self.url_regex = re.compile('|'.join(self.url_patterns), re.IGNORECASE)
        self.spam_regex = re.compile('|'.join(self.spam_patterns), re.IGNORECASE)
        
        logger.info("✅ Rule Engine initialized with enhanced context awareness")

    def _analyze_context(self, text: str, matched_word: str, category: str) -> Dict[str, Any]:
        """
        Analyze context around a matched word to determine if usage is harmful.
        
        Returns:
            {
                'is_harmful': bool,
                'confidence': float,
                'context_type': str,
                'reasoning': str
            }
        """
        text_lower = text.lower()
        
        # First check if the matched word itself is in safe words list
        if matched_word.lower() in self.safe_words:
            return {
                'is_harmful': False,
                'confidence': 0.95,
                'context_type': 'safe_word',
                'reasoning': f"'{matched_word}' is in safe words list"
            }
        
        # Step 1: Check for safe contexts first (override)
        for pattern, context_type in self.safe_context_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                # Get surrounding context (30 chars before and after)
                start = max(0, match.start() - 30)
                end = min(len(text_lower), match.end() + 30)
                context = text_lower[start:end]
                
                if matched_word.lower() in context:
                    return {
                        'is_harmful': False,
                        'confidence': 0.9,
                        'context_type': context_type,
                        'reasoning': f"Found in safe {context_type} context"
                    }
        
        # Step 2: Check for harmful contexts
        for harm_category, patterns in self.harmful_context_patterns.items():
            for pattern, weight in patterns:
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    start = max(0, match.start() - 30)
                    end = min(len(text_lower), match.end() + 30)
                    context = text_lower[start:end]
                    
                    if matched_word.lower() in context:
                        return {
                            'is_harmful': True,
                            'confidence': weight,
                            'context_type': harm_category,
                            'reasoning': f"Found in harmful {harm_category} context"
                        }
        
        # Step 3: Check surrounding words for educational context
        words = text_lower.split()
        for i, word in enumerate(words):
            if matched_word.lower() in word:
                start = max(0, i - 5)
                end = min(len(words), i + 6)
                surrounding = words[start:end]
                
                # Educational verbs indicate safe usage
                educational_verbs = ['learn', 'study', 'practice', 'master', 'develop', 'improve', 'build', 'create']
                if any(verb in surrounding for verb in educational_verbs):
                    return {
                        'is_harmful': False,
                        'confidence': 0.85,
                        'context_type': 'educational',
                        'reasoning': f"Found near educational verbs"
                    }
                
                # Harmful personal pronouns with harmful verbs
                harmful_pronouns = ['i', 'me', 'myself', 'you', 'yourself']
                harmful_verbs = ['want', 'need', 'will', 'going', 'plan', 'threat']
                if any(pronoun in surrounding for pronoun in harmful_pronouns):
                    if any(verb in surrounding for verb in harmful_verbs):
                        return {
                            'is_harmful': True,
                            'confidence': 0.8,
                            'context_type': 'personal_threat',
                            'reasoning': f"Personal context with harmful intent"
                        }
        
        # Step 4: Default based on category
        # If it's in violence/harm category but no harmful context, assume safe
        if category in ["violence", "harm"]:
            return {
                'is_harmful': False,
                'confidence': 0.6,
                'context_type': 'neutral',
                'reasoning': f"No harmful context detected for {category} word"
            }
        
        # Default to suspicious (fail-safe)
        return {
            'is_harmful': True,
            'confidence': 0.5,
            'context_type': 'unknown',
            'reasoning': "No clear context, defaulting to suspicious"
        }

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

    # ──────────────────────────────────────────────────────────
    #  Sentence-level mixing detection  ← NEW
    # ──────────────────────────────────────────────────────────

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences, handling missing spaces after punctuation."""
        # Split on punctuation (.!?) or newlines
        sentences = re.split(r'[.!?\n]+', text.strip())
        
        valid_sentences = []
        for s in sentences:
            s_clean = s.strip()
            if not s_clean:
                continue
            
            # Keep if it's long enough (ignores "Hi."), OR if it contains tech keywords
            if len(s_clean.split()) >= 4 or self._sentence_has_tech(s_clean):
                valid_sentences.append(s_clean)
                
        return valid_sentences

    def _sentence_has_tech(self, sentence: str) -> bool:
        """Return True if a sentence contains at least one tech taxonomy term."""
        s_lower = sentence.lower()
        for category, terms in self.tech_taxonomy.items():
            for term in terms:
                if ' ' in term:
                    if term in s_lower:
                        return True
                else:
                    if re.search(rf'\b{re.escape(term)}\b', s_lower):
                        return True
        # Also check code signals
        for pattern in self._compiled_code_signals:
            if pattern.search(sentence):
                return True
        return False

    def _sentence_is_off_topic(self, sentence: str) -> bool:
        """Return True if a sentence clearly signals personal/casual/off-topic content."""
        s_lower = sentence.lower()
        matches = 0
        for pattern in self._compiled_off_topic_sentence:
            if pattern.search(s_lower):
                matches += 1
                if matches >= 1:
                    return True
        return False

    def _detect_content_mixing(self, text: str) -> Dict[str, Any]:
        """Detect when off-topic sentences are mixed into tech content.

        Returns:
            mixing_detected     : bool
            off_topic_sentences : list of sentences that are clearly off-topic
            tech_sentences      : count of tech sentences
            total_sentences     : total sentence count
            mixing_penalty      : float penalty to apply to tech relevance score
        """
        sentences = self._split_sentences(text)

        if len(sentences) <= 1:
            return {
                "mixing_detected": False,
                "off_topic_sentences": [],
                "tech_sentences": [],
                "total_sentences": len(sentences),
                "mixing_penalty": 0.0
            }

        tech_sentences = []
        off_topic_sentences = []

        for sentence in sentences:
            has_tech = self._sentence_has_tech(sentence)
            is_off   = self._sentence_is_off_topic(sentence)

            if has_tech and not is_off:
                tech_sentences.append(sentence)
            elif is_off and not has_tech:
                off_topic_sentences.append(sentence)
            elif not has_tech and not is_off:
                # Neutral sentence (no signal either way) — treat as slightly off-topic
                off_topic_sentences.append(sentence)

        total = len(sentences)
        n_off  = len(off_topic_sentences)
        n_tech = len(tech_sentences)

        # Mixing detected if there is at least one clearly off-topic sentence
        # AND at least one tech sentence (pure off-topic posts are handled by base score)
        mixing_detected = n_off >= 1 and n_tech >= 1

        # Penalty scales with the ratio of off-topic sentences
        # 1 off-topic in 3 sentences → 0.40 penalty
        # 1 off-topic in 2 sentences → 0.50 penalty
        # 2 off-topic in 3 sentences → 0.65 penalty
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
            "mixing_detected": mixing_detected,
            "off_topic_sentences": off_topic_sentences,
            "tech_sentences": tech_sentences,
            "total_sentences": total,
            "mixing_penalty": mixing_penalty
        }

    # ──────────────────────────────────────────────────────────
    #  Tech relevance scoring
    # ──────────────────────────────────────────────────────────

    def check_tech_relevance(self, text: str) -> Dict[str, Any]:
        """Score how tech-relevant a post is.

        Now includes sentence-level mixing detection to catch posts
        that inject off-topic content between tech sentences.
        """
        if not text or not text.strip():
            return {
                "tech_relevance_score": 0.0,
                "zone": "off_topic",
                "matched_categories": [],
                "matched_terms": [],
                "non_tech_signals": [],
                "mixing": {"mixing_detected": False},
                "details": {}
            }

        text_lower = text.lower()
        words = text_lower.split()
        total_words = max(len(words), 1)

        # ── 1. Taxonomy term matching ──
        category_hits: Dict[str, List[str]] = {}
        all_matched_terms: List[str] = []

        for category, terms in self.tech_taxonomy.items():
            hits = []
            for term in terms:
                if ' ' in term:
                    if term in text_lower:
                        hits.append(term)
                else:
                    if re.search(rf'\b{re.escape(term)}\b', text_lower):
                        hits.append(term)
            if hits:
                category_hits[category] = hits
                all_matched_terms.extend(hits)

        unique_terms      = len(set(all_matched_terms))
        unique_categories = len(category_hits)

        # ── 2. Tech URL bonus ──
        tech_url_bonus = 0.0
        for pattern in self._compiled_tech_urls:
            if pattern.search(text):
                tech_url_bonus = 0.2
                break

        # ── 3. Code signal bonus ──
        code_bonus = 0.0
        for pattern in self._compiled_code_signals:
            if pattern.search(text):
                code_bonus = min(code_bonus + 0.05, 0.25)

        # ── 4. Non-tech signal penalty (whole-post level) ──
        non_tech_penalty = 0.0
        matched_non_tech: List[str] = []
        for pattern in self._compiled_non_tech:
            m = pattern.search(text_lower)
            if m:
                matched_non_tech.append(m.group())
                non_tech_penalty = min(non_tech_penalty + 0.12, 0.35)

        # ── 5. Base score ──
        if unique_terms == 0:
            base_score = 0.0
        elif unique_terms == 1:
            base_score = 0.40
        elif unique_terms == 2:
            base_score = 0.52
        elif unique_terms <= 4:
            base_score = 0.65
        elif unique_terms <= 7:
            base_score = 0.78
        else:
            base_score = 0.90

        if unique_categories >= 3:
            base_score = min(base_score + 0.10, 1.0)
        elif unique_categories == 2:
            base_score = min(base_score + 0.05, 1.0)

        density = (unique_terms / total_words) * 100
        if density > 8:
            base_score = min(base_score + 0.10, 1.0)
        elif density > 4:
            base_score = min(base_score + 0.05, 1.0)

        # ── 6. Sentence-level mixing detection ──  NEW
        mixing = self._detect_content_mixing(text)
        mixing_penalty = mixing["mixing_penalty"]

        if mixing["mixing_detected"]:
            logger.warning(
                f"🔀 Content mixing detected: "
                f"{len(mixing['off_topic_sentences'])} off-topic sentence(s) "
                f"in {mixing['total_sentences']} total. "
                f"Penalty: -{mixing_penalty:.2f}"
            )

        # ── 7. Final score — mixing penalty applied last ──
        final_score = base_score + tech_url_bonus + code_bonus - non_tech_penalty - mixing_penalty
        final_score = round(max(0.0, min(1.0, final_score)), 3)

        # ── 8. Zone ──
        if final_score >= 0.38:
            zone = "tech"
        elif final_score >= 0.20:
            zone = "review"
        else:
            zone = "off_topic"

        result = {
            "tech_relevance_score": final_score,
            "zone": zone,
            "matched_categories": list(category_hits.keys()),
            "matched_terms": list(set(all_matched_terms))[:15],
            "non_tech_signals": matched_non_tech,
            "mixing": {
                "mixing_detected":      mixing["mixing_detected"],
                "off_topic_sentences":  mixing["off_topic_sentences"],
                "tech_sentence_count":  len(mixing["tech_sentences"]),
                "total_sentences":      mixing["total_sentences"],
                "mixing_penalty":       mixing_penalty,
            },
            "details": {
                "base_score":        round(base_score, 3),
                "tech_url_bonus":    tech_url_bonus,
                "code_bonus":        round(code_bonus, 3),
                "non_tech_penalty":  round(non_tech_penalty, 3),
                "mixing_penalty":    round(mixing_penalty, 3),
                "unique_terms":      unique_terms,
                "unique_categories": unique_categories,
                "density_pct":       round(density, 2),
            }
        }

        logger.info(
            f"🔍 Tech relevance: score={final_score:.3f}, zone={zone}, "
            f"terms={unique_terms}, mixing={mixing['mixing_detected']}, "
            f"categories={list(category_hits.keys())}"
        )

        return result

    # ──────────────────────────────────────────────────────────
    #  Harm rules
    # ──────────────────────────────────────────────────────────

    def check_rules(self, text: str) -> Dict[str, Any]:
        """Check text against all harm rules."""
        text_stripped = text.strip()
        normalized    = self.normalize_text(text_stripped)

        results = {
            "banned_keywords":  [],
            "keyword_categories": [],
            "suspicious_urls":  [],
            "spam_detected":    False,
            "violations":       [],
            "hindi_detection":  {"has_hindi_abuse": False, "matched_words": []}
        }

        if not text_stripped:
            results["rule_score"] = 0.0
            return results

        # ── Step 0: Mask allowlisted spans ──
        masked_text = text_stripped
        for pattern in self._compiled_allowlist:
            masked_text = pattern.sub(lambda m: '_' * len(m.group()), masked_text)

        masked_normalized = normalized
        for pattern in self._compiled_allowlist:
            masked_normalized = pattern.sub(lambda m: '_' * len(m.group()), masked_normalized)

        # ── Step 1: Banned keywords ──
        for pattern, (keyword, category) in self._compiled_banned.items():
            if pattern.search(masked_text) or pattern.search(masked_normalized):
                results["banned_keywords"].append(keyword)
                results["keyword_categories"].append(category)
                results["violations"].append(f"keyword:{keyword}")

        # ── Step 2: Hindi galis ──
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

        # ── Step 3: Suspicious URLs ──
        urls = self.url_regex.findall(text_stripped.lower())
        if urls:
            results["suspicious_urls"] = list(set(urls))
            results["violations"].append("suspicious_url")

        # ── Step 4: Spam ──
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

        # ── Step 5: Hindi/Hinglish abuse via normalizer ──
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
