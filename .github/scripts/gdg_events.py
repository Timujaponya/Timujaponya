"""Write the latest GDG on Campus Sakarya events into README.md."""
import datetime
import json
import re
import urllib.request

CHAPTER_ID = 3497
API = f"https://gdg.community.dev/api/event/?chapter={CHAPTER_ID}&page_size=20&order=-start_date"
README = "README.md"
START, END = "<!-- GDG-EVENTS:START -->", "<!-- GDG-EVENTS:END -->"
LIMIT = 5

req = urllib.request.Request(API, headers={"User-Agent": "profile-readme-bot"})
with urllib.request.urlopen(req, timeout=30) as r:
    events = json.load(r)["results"]

events = [e for e in events if e.get("status") == "Published" and not e.get("is_hidden") and not e.get("is_test")]
events.sort(key=lambda e: e["start_date"], reverse=True)

now = datetime.datetime.now(datetime.timezone.utc)
lines = []
for e in events[:LIMIT]:
    start = datetime.datetime.fromisoformat(e["start_date"])
    when = start.strftime("%d %b %Y")
    tag = "🟢 **upcoming**" if start > now else "✅"
    title = e["title"].replace("GDG on Campus Sakarya University - ", "").replace("GDG on Campus Sakarya Üniversitesi - ", "")
    lines.append(f"- {tag} `{when}` · [{title}]({e['url']})")
if not lines:
    lines.append("- No events yet. Follow the chapter page to hear about the next one.")

with open(README, encoding="utf-8") as f:
    text = f.read()
block = START + "\n" + "\n".join(lines) + "\n" + END
text = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, text, flags=re.S)
with open(README, "w", encoding="utf-8", newline="\n") as f:
    f.write(text)
print("\n".join(lines))
