import os
import json
import random
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


load_dotenv()

APP_TITLE = "AI Content Idea Generator"
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

PLATFORMS = [
    "YouTube",
    "TikTok",
    "Blog",
    "Instagram",
    "X / Twitter",
    "LinkedIn",
    "Podcast",
]

TONES = [
    "Educational",
    "Viral",
    "Professional",
    "Funny",
    "Motivational",
    "Storytelling",
    "Bold",
]

IDEA_TYPES = [
    "Any",
    "Listicle",
    "Tutorial",
    "Story",
    "Beginner Tips",
    "Contrarian",
    "Case Study",
    "Myth Busting",
    "How-To",
    "Problem/Solution",
]

TEMPLATE_IDEAS = [
    "10 mistakes beginners make with {topic}",
    "What nobody tells you about {topic}",
    "How to improve at {topic} faster",
    "Best tools for {topic} this year",
    "Myths people still believe about {topic}",
    "Beginner guide to {topic}",
    "Things I wish I knew before starting {topic}",
    "Why most people fail at {topic}",
    "A simple plan to get better at {topic}",
    "What changed everything for me with {topic}",
    "The biggest problems with {topic} and how to fix them",
    "Is {topic} still worth it?",
]

DAY_THEMES = [
    "Beginner topic",
    "Mistakes to avoid",
    "Tools and resources",
    "Myth busting",
    "Step-by-step tutorial",
    "Story or personal angle",
    "Hot take or contrarian post",
    "Checklist or framework",
    "FAQ",
    "Before/after or transformation",
]


def init_state() -> None:
    defaults = {
        "history": [],
        "last_result": None,
        "last_calendar": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


@st.cache_resource(show_spinner=False)
def get_openai_client():
    if not OPENAI_API_KEY or OpenAI is None:
        return None
    try:
        return OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        return None


def call_openai_json(system_prompt: str, user_prompt: str) -> dict:
    client = get_openai_client()
    if client is None:
        raise RuntimeError(
            "OpenAI client is unavailable. Add OPENAI_API_KEY to your .env file to enable AI mode."
        )

    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.9,
    )

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("The AI returned an empty response.")
    return json.loads(content)


def fallback_generate_ideas(topic: str, platform: str, tone: str, audience: str, idea_type: str, count: int) -> dict:
    random.seed()
    ideas = []
    used = set()

    prefixes = [
        "Quick",
        "Simple",
        "Practical",
        "Powerful",
        "Beginner-friendly",
        "Underrated",
        "Smart",
        "Creative",
    ]

    while len(ideas) < count:
        title = random.choice(TEMPLATE_IDEAS).format(topic=topic)
        if idea_type != "Any":
            title = f"{idea_type}: {title}"
        if title in used:
            title = f"{random.choice(prefixes)} {title}"
        used.add(title)
        ideas.append(
            {
                "title": title,
                "description": f"A {tone.lower()} {platform} idea for {audience or 'a general audience'} focused on {topic}.",
                "hook": f"Most people approach {topic} the wrong way — here is a better angle.",
            }
        )

    bonus_titles = [
        f"Why {topic} feels harder than it should",
        f"The easiest way to start with {topic}",
        f"What I would do differently with {topic} today",
    ]

    return {"ideas": ideas, "bonus_titles": bonus_titles}


def generate_ideas(topic: str, platform: str, tone: str, audience: str, idea_type: str, count: int) -> dict:
    system_prompt = (
        "You are a creative content strategist. Return valid JSON only. "
        "Generate original, specific, platform-native content ideas with no repetition."
    )

    user_prompt = f"""
Create {count} content ideas.

Topic: {topic}
Platform: {platform}
Tone: {tone}
Audience: {audience or 'general audience'}
Idea type: {idea_type}

Return JSON in exactly this shape:
{{
  "ideas": [
    {{
      "title": "short catchy title",
      "description": "one sentence explaining why the idea would work",
      "hook": "a one-sentence opening hook"
    }}
  ],
  "bonus_titles": ["title 1", "title 2", "title 3"]
}}

Rules:
- Tailor ideas to the platform
- Make each idea distinct
- Avoid generic filler
- Keep titles concise and clickable
- Hooks should feel natural and scroll-stopping
"""

    try:
        return call_openai_json(system_prompt, user_prompt)
    except Exception:
        return fallback_generate_ideas(topic, platform, tone, audience, idea_type, count)


def generate_calendar(topic: str, platform: str, tone: str, audience: str) -> list[dict]:
    system_prompt = (
        "You are a content strategist building a practical 30-day content calendar. Return valid JSON only."
    )

    user_prompt = f"""
Create a 30-day content calendar.

Topic: {topic}
Platform: {platform}
Tone: {tone}
Audience: {audience or 'general audience'}

Return JSON in exactly this shape:
{{
  "days": [
    {{
      "day": 1,
      "theme": "short theme",
      "title": "content title",
      "format": "short-form video/post/article/thread",
      "hook": "opening hook",
      "cta": "simple call to action"
    }}
  ]
}}

Rules:
- Make all 30 days unique
- Vary the themes and formats
- Keep it actionable and specific
- Match the platform naturally
"""

    try:
        data = call_openai_json(system_prompt, user_prompt)
        return data.get("days", [])
    except Exception:
        days = []
        for i in range(30):
            theme = DAY_THEMES[i % len(DAY_THEMES)]
            days.append(
                {
                    "day": i + 1,
                    "theme": theme,
                    "title": f"{topic}: {theme}",
                    "format": "short-form video" if platform in ["TikTok", "Instagram", "YouTube"] else "post",
                    "hook": f"Here is a smarter way to think about {topic}.",
                    "cta": "Ask your audience to share their experience.",
                }
            )
        return days


def add_to_history(entry_type: str, payload: dict) -> None:
    st.session_state.history.insert(
        0,
        {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": entry_type,
            "payload": payload,
        },
    )


def ideas_to_markdown(topic: str, platform: str, ideas_data: dict) -> str:
    lines = [f"# Content Ideas for {topic}", "", f"Platform: {platform}", ""]
    for idx, idea in enumerate(ideas_data.get("ideas", []), start=1):
        lines.append(f"## {idx}. {idea.get('title', 'Untitled')}")
        lines.append(idea.get("description", ""))
        lines.append("")
        lines.append(f"Hook: {idea.get('hook', '')}")
        lines.append("")
    bonus = ideas_data.get("bonus_titles", [])
    if bonus:
        lines.append("## Bonus Titles")
        for item in bonus:
            lines.append(f"- {item}")
    return "\n".join(lines)


def calendar_to_csv(days: list[dict]) -> str:
    headers = ["day", "theme", "title", "format", "hook", "cta"]
    rows = [",".join(headers)]
    for day in days:
        row = []
        for header in headers:
            value = str(day.get(header, "")).replace('"', '""')
            row.append(f'"{value}"')
        rows.append(",".join(row))
    return "\n".join(rows)


def render_history() -> None:
    st.subheader("Saved History")
    if not st.session_state.history:
        st.info("No saved generations yet.")
        return

    for i, item in enumerate(st.session_state.history):
        label = f"{item['timestamp']} — {item['type'].title()}"
        with st.expander(label):
            st.json(item["payload"], expanded=False)
            st.download_button(
                label="Download JSON",
                data=json.dumps(item["payload"], indent=2),
                file_name=f"history_{i + 1}.json",
                mime="application/json",
                key=f"download_history_{i}",
            )


st.set_page_config(page_title=APP_TITLE, page_icon="💡", layout="wide")
init_state()

st.title("💡 AI Content Idea Generator")
st.caption("Generate unlimited ideas, save history, export results, and build a 30-day content calendar.")

with st.sidebar:
    st.header("Settings")
    ai_enabled = bool(OPENAI_API_KEY and OpenAI is not None)
    st.write(f"AI mode: {'On' if ai_enabled else 'Template fallback'}")
    if not ai_enabled:
        st.warning("Add OPENAI_API_KEY to your .env file to enable AI generation.")
    st.divider()
    clear_history = st.button("Clear saved history")
    if clear_history:
        st.session_state.history = []
        st.success("History cleared.")

main_tab, calendar_tab, history_tab = st.tabs(["Idea Generator", "30-Day Calendar", "History"])

with main_tab:
    col1, col2 = st.columns([1, 1])

    with col1:
        with st.form("idea_form"):
            topic = st.text_input("Topic or niche", placeholder="fitness, skincare, gaming, real estate")
            platform = st.selectbox("Platform", PLATFORMS)
            tone = st.selectbox("Tone", TONES)
            audience = st.text_input("Target audience", placeholder="beginners, busy moms, creators, freelancers")
            idea_type = st.selectbox("Idea type", IDEA_TYPES)
            count = st.slider("Number of ideas", 5, 30, 10)
            submitted = st.form_submit_button("Generate Ideas")

    with col2:
        st.markdown("### Quick Presets")
        preset_cols = st.columns(3)
        preset_map = {
            "Gaming": ("gaming", "YouTube", "Viral", "gamers", "Any", 10),
            "Skincare": ("skincare", "TikTok", "Educational", "women in their 20s", "How-To", 10),
            "Freelancing": ("freelancing", "LinkedIn", "Professional", "new freelancers", "Case Study", 10),
        }
        for idx, (label, values) in enumerate(preset_map.items()):
            with preset_cols[idx]:
                if st.button(label, use_container_width=True):
                    topic, platform, tone, audience, idea_type, count = values
                    with st.spinner("Generating ideas..."):
                        result = generate_ideas(topic, platform, tone, audience, idea_type, count)
                        st.session_state.last_result = {
                            "topic": topic,
                            "platform": platform,
                            "tone": tone,
                            "audience": audience,
                            "idea_type": idea_type,
                            "count": count,
                            "result": result,
                        }
                        add_to_history("ideas", st.session_state.last_result)

    if submitted:
        if not topic.strip():
            st.warning("Please enter a topic.")
        else:
            with st.spinner("Generating ideas..."):
                result = generate_ideas(topic, platform, tone, audience, idea_type, count)
                st.session_state.last_result = {
                    "topic": topic,
                    "platform": platform,
                    "tone": tone,
                    "audience": audience,
                    "idea_type": idea_type,
                    "count": count,
                    "result": result,
                }
                add_to_history("ideas", st.session_state.last_result)

    if st.session_state.last_result:
        data = st.session_state.last_result
        ideas_data = data["result"]
        st.subheader(f"Ideas for {data['topic'].title()}")

        for idx, idea in enumerate(ideas_data.get("ideas", []), start=1):
            with st.container(border=True):
                st.markdown(f"### {idx}. {idea.get('title', 'Untitled')}")
                st.write(idea.get("description", ""))
                st.caption(f"Hook: {idea.get('hook', '')}")

        if ideas_data.get("bonus_titles"):
            st.markdown("### Bonus Titles")
            for title in ideas_data["bonus_titles"]:
                st.write(f"- {title}")

        markdown_export = ideas_to_markdown(data["topic"], data["platform"], ideas_data)
        json_export = json.dumps(data, indent=2)

        export_col1, export_col2 = st.columns(2)
        with export_col1:
            st.download_button(
                "Download as Markdown",
                data=markdown_export,
                file_name=f"{data['topic'].replace(' ', '_')}_ideas.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with export_col2:
            st.download_button(
                "Download as JSON",
                data=json_export,
                file_name=f"{data['topic'].replace(' ', '_')}_ideas.json",
                mime="application/json",
                use_container_width=True,
            )

        st.markdown("### Copy-Friendly Output")
        st.text_area("Copy your ideas", value=markdown_export, height=260)

with calendar_tab:
    st.subheader("30-Day Content Calendar")
    with st.form("calendar_form"):
        cal_topic = st.text_input("Calendar topic", placeholder="gaming, self-care, investing")
        cal_platform = st.selectbox("Calendar platform", PLATFORMS, index=0)
        cal_tone = st.selectbox("Calendar tone", TONES, index=0)
        cal_audience = st.text_input("Calendar audience", placeholder="beginners, creators, students")
        calendar_submitted = st.form_submit_button("Generate 30-Day Calendar")

    if calendar_submitted:
        if not cal_topic.strip():
            st.warning("Please enter a calendar topic.")
        else:
            with st.spinner("Building your 30-day calendar..."):
                days = generate_calendar(cal_topic, cal_platform, cal_tone, cal_audience)
                st.session_state.last_calendar = {
                    "topic": cal_topic,
                    "platform": cal_platform,
                    "tone": cal_tone,
                    "audience": cal_audience,
                    "days": days,
                }
                add_to_history("calendar", st.session_state.last_calendar)

    if st.session_state.last_calendar:
        cal = st.session_state.last_calendar
        days = cal["days"]
        st.markdown(f"### 30-Day Plan for {cal['topic'].title()}")

        for day in days:
            with st.expander(f"Day {day.get('day')} — {day.get('title', 'Untitled')}"):
                st.write(f"**Theme:** {day.get('theme', '')}")
                st.write(f"**Format:** {day.get('format', '')}")
                st.write(f"**Hook:** {day.get('hook', '')}")
                st.write(f"**CTA:** {day.get('cta', '')}")

        csv_data = calendar_to_csv(days)
        st.download_button(
            "Download Calendar as CSV",
            data=csv_data,
            file_name=f"{cal['topic'].replace(' ', '_')}_30_day_calendar.csv",
            mime="text/csv",
            use_container_width=True,
        )

with history_tab:
    render_history()
