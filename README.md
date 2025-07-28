---
title: Inteligentny Tutor Geodezyjny
emoji: 🗺️
colorFrom: blue
colorTo: green
sdk: streamlit
sdk_version: "1.36.0"
app_file: app.py
pinned: false
license: mit
---

# 🧠 Inteligentny Tutor Geodezyjny

Twoje osobiste centrum przygotowań do egzaminu na **uprawnienia geodezyjne (zakres 1)**, zasilane przez sztuczną inteligencję Google Gemini. Koniec z monotonnym wertowaniem setek stron PDF! Ta aplikacja zamienia akty prawne w interaktywnego, niestrudzonego korepetytora, który jest dostępny 24/7.

---

## Dla Kogo Jest Ta Aplikacja? 🤔

Aplikacja została stworzona z myślą o:
- **Kandydatach przygotowujących się do egzaminu** na uprawnienia zawodowe w dziedzinie geodezji i kartografii w zakresie 1.
- **Praktykujących geodetach**, którzy chcą szybko odświeżyć swoją wiedzę lub znaleźć konkretną informację w gąszczu przepisów.
- **Studentach geodezji**, którzy chcą w nowoczesny sposób uzupełniać swoją wiedzę.

---

## Kluczowe Funkcje, Które Pomogą Ci Zdać Egzamin 🚀

### 1. Interaktywny Quiz Egzaminacyjny
Sprawdź swoją wiedzę w warunkach zbliżonych do prawdziwego egzaminu!
- **Pytania jedno- i wielokrotnego wyboru** generowane dynamicznie na podstawie wgranych przez Ciebie aktów prawnych.
- **Natychmiastowa informacja zwrotna** – po zakończeniu testu aplikacja oceni Twoje odpowiedzi, wskaże błędy i policzy wynik.
- **Pełna transparentność** – przy każdej odpowiedzi otrzymasz nie tylko uzasadnienie od AI, ale również **dokładny cytat z przepisu**, na podstawie którego powstało pytanie. Uczysz się szybciej, bo od razu wiesz, *dlaczego* dana odpowiedź jest poprawna.

### 2. Symulator Egzaminu Ustnego
Przygotuj się na najbardziej stresującą część egzaminu w bezpiecznym środowisku.
- Poproś o pytanie, a AI wcieli się w rolę **surowego, ale sprawiedliwego egzaminatora**.
- Sformułuj odpowiedź, a aplikacja **szczegółowo ją oceni** – wskaże mocne strony, błędy oraz podpowie, jak powinna brzmieć wzorowa odpowiedź, cytując podstawą prawną.
- Oswoisz się z presją i nauczysz się precyzyjnie formułować myśli.

### 3. Statystyki Twoich Postępów
Śledź swoją skuteczność w czasie rzeczywistym! Aplikacja zlicza, ile pytań rozwiązałeś i jaki jest Twój ogólny procent poprawnych odpowiedzi w trakcie sesji, motywując Cię do dalszej nauki.

---

## Jak To Działa? ⚙️

Aplikacja wykorzystuje technikę **RAG (Retrieval-Augmented Generation)**. Oznacza to, że model językowy **Google Gemini** nie korzysta z ogólnej wiedzy z internetu, ale "czyta" i analizuje **wyłącznie te akty prawne**, które wgrasz do folderu `documents`. Dzięki temu jego odpowiedzi są precyzyjne i osadzone w kontekście obowiązujących w Polsce przepisów.

---

## Jak Zacząć? 🚀

1.  **Sklonuj repozytorium** lub utwórz nowy Space na Hugging Face, używając tego szablonu.
2.  **Wgraj pliki PDF** z ustawami i rozporządzeniami do folderu `documents` w zakładce "Files".
3.  **Dodaj swój klucz Google API** jako "Secret" w ustawieniach Space'a. Nazwa secreta musi brzmieć `GOOGLE_API_KEY`.
4.  **Uruchom aplikację!**

    > **Ważna informacja:** Przy pierwszym uruchomieniu aplikacja będzie tworzyć tzw. bazę wektorową z Twoich dokumentów. **Ten proces może potrwać nawet kilkanaście minut** i będzie sygnalizowany paskiem postępu. To normalne! Po tym jednorazowym procesie każde kolejne uruchomienie aplikacji będzie już błyskawiczne.

---

**Autor:** Rafał 🙂