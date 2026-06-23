# Musik Jeopardy

Flask-webapp til musikquiz med quizmaster, publikumsskærm og buzzere.

## Lokalt

```bash
pip install -r requirements.txt
python web_app.py
```

Åbn:
- http://localhost:5001/host
- http://localhost:5001/audience
- http://localhost:5001/buzzer

## Render

Start command:
```bash
gunicorn web_app:app
```

## Opdatering

Guldspørgsmål afsløres ikke på boardet. De afsløres først, når spørgsmålet åbnes.
Quizmaster-siden har nu knappen **Nulstil hele spillet**.
