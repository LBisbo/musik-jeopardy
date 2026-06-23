# Musik Jeopardy V2

Flask-webapp til musikquiz med quizmaster, publikumsskærm og buzzere.

## Flow i V2

- Når quizmaster vælger et felt, ser publikum kun kategori og point.
- Quizmaster ser straks host_note, spørgsmål og svar.
- Når quizmaster trykker "Vis spørgsmål", ser publikum spørgsmålet, og buzzeren åbner.
- Der er ingen timer før et hold buzzer.
- Første buzz giver 20 sekunders svartid.
- Efter forkert svar får næste buzz 10 sekunders svartid.
- Forkert svar giver minuspoint.
- Guldspørgsmål afsløres ikke på boardet.
- Guldspørgsmål afsløres først, når spørgsmålet vises.

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

Build command:
```bash
pip install -r requirements.txt
```

Start command:
```bash
gunicorn web_app:app
```
