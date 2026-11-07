"""What Darbi is and who it is for, in one place. The interface shows the same sentences (`app.about` in
web/src/i18n); tests/test_about.py fails if they drift apart."""

ABOUT = {
    "en": (
        "Darbi helps graduates of Qatar's Mostaqila schools understand the English language of AI and use AI well at work, "
        "explained in the Gulf dialect they speak every day."
    ),
    "ar": "دربي يساعد خريجي المدارس المستقلة في قطر يفهمون لغة الذكاء الاصطناعي الإنجليزية ويستخدمونه صح في الشغل، بشرح باللهجة الخليجية اللي يتكلمونها كل يوم.",
}

# Who the learner is, for model prompts.
AUDIENCE = "graduates of Qatar's Mostaqila schools who use AI at work"
