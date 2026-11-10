"""What Darbi is and who it is for, in one place. The interface shows the same sentences (`app.about` in
web/src/i18n); tests/test_about.py fails if they drift apart."""

ABOUT = {
    "en": (
        "Darbi helps students and graduates of Qatar's Mostaqila schools understand the English of AI and technology "
        "and use AI well in their studies and at work, explained in the Gulf dialect they speak every day."
    ),
    "ar": "دربي يساعد طلاب وخريجي المدارس المستقلة في قطر يفهمون إنجليزي الذكاء الاصطناعي والتقنية ويستخدمون الذكاء الاصطناعي صح في الدراسة والشغل، بشرح باللهجة الخليجية اللي يتكلمونها كل يوم.",
}

# Who the learner is, for model prompts.
AUDIENCE = "students and graduates of Qatar's Mostaqila schools who meet English and AI tools in their studies and at work"
