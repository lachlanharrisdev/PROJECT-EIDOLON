"""
Constants for the Aethon Web Crawler
"""

# Regex patterns
EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
SOCIAL_REGEX = {
    "twitter": r"twitter\.com/([A-Za-z0-9_]+)",
    "facebook": r"facebook\.com/([A-Za-z0-9_.]+)",
    "linkedin": r"linkedin\.com/(?:in|company)/([A-Za-z0-9_-]+)",
    "instagram": r"instagram\.com/([A-Za-z0-9_.]+)",
    "github": r"github\.com/([A-Za-z0-9_-]+)",
}
AWS_BUCKET_REGEX = r"[a-zA-Z0-9_-]+\.s3\.amazonaws\.com"
SECRET_REGEX = {
    "api_key": r'(?i)(api[_-]?key|apikey|app[_-]?key|appkey|auth[_-]?key)["\']?\s*[:=]\s*["\']([a-zA-Z0-9_\-]{10,})["\']',
    "aws_key": r"(?:AKIA|A3T|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{12,}",
    "auth_token": r'(?i)(auth[_-]?token|authentication|access[_-]?token)["\']?\s*[:=]\s*["\']([a-zA-Z0-9_\-\.=]{10,})["\']',
    "jwt": r"eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+",
    "hash": r"[A-Fa-f0-9]{32,64}",
    "firebase": r'(?i)(firebaseConfig|firebase\.initializeApp)\({[^}]*apiKey["\']?\s*:\s*["\']([a-zA-Z0-9_\-]{30,})["\']',
}

# File extension categories
FILE_EXTENSIONS = {
    "audio": ["wav", "mp3", "ogg", "flac", "m4a"],
    "video": ["mp4", "mkv", "avi", "mov", "webm"],
    "document": ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "odt"],
    "image": ["jpg", "jpeg", "png", "gif", "bmp", "svg", "webp", "ico"],
    "archive": ["zip", "tar.gz", "tar", "rar", "7z"],
    "executable": ["exe", "dll", "so", "bin", "apk"],
    "data": ["json", "xml", "csv", "yml", "yaml", "sql"],
    "code": ["js", "php", "py", "rb", "java", "html", "css", "jsx", "ts", "tsx"],
}

# User agent list for randomization or specific selections
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]

# For Ninja mode - referrers to mask crawling
REFERRERS = [
    "https://www.google.com/",
    "https://www.bing.com/",
    "https://www.facebook.com/",
    "https://www.twitter.com/",
    "https://www.linkedin.com/",
    "https://www.reddit.com/",
    "https://developer.facebook.com/",
    "https://codebeautify.com/",
    "https://photopea.com/",
    "https://pixlr.com/",
]
