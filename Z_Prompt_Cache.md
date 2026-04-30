Das **696 Mio cached** bedeutet nicht, dass du in *einer* Antwort 696 Mio Tokens verarbeitet hast.

Es bedeutet ziemlich sicher:

> Über viele Requests hinweg wurden **696’693’120 Input-Tokens aus einem Prompt-/Context-Cache wiederverwendet**, statt jedes Mal vollständig neu verarbeitet zu werden.

Also: Das System zählt nicht nur die “echten neuen” Input-Tokens, sondern auch die Tokens, die technisch im Modellkontext wieder auftauchen, aber schon gecached waren.

## Warum kann das so riesig sein?

Weil bei langen Chats oder Agent-/Tool-Workflows oft immer wieder derselbe Kontext mitgeschickt wird:

* System-Instructions
* Developer-Instructions
* Memory / Custom Instructions
* lange Chat-Historie
* vorherige Tool-Ergebnisse
* Projektkontext
* evtl. Dateien, Code, Dokumente, Specs

Wenn davon z. B. **100’000 Tokens** jedes Mal im Kontext stehen und du machst **7’000 Interaktionen / interne Modellaufrufe**, dann ergibt das:

```text
100’000 × 7’000 = 700’000’000 cached tokens
```

Das ist also nicht absurd. Es ist ein **kumulativer Zähler**.

## Was heisst “cached” technisch?

Stell dir vor, das Modell muss den Prompt lesen. Normalerweise kostet das Rechenzeit, weil jeder Token durch die Transformer-Schichten läuft.

Bei Prompt Caching merkt sich das System intern ungefähr:

> “Diesen Anfang des Prompts habe ich schon verarbeitet.”

Dann muss es bei einem späteren ähnlichen Request nicht wieder alles von Null berechnen. Besonders der **Prefix** des Prompts wird wiederverwendet.

Vereinfacht:

```text
Request 1:
[System + Memory + langer Chat + neue Frage]
→ alles neu verarbeiten

Request 2:
[System + Memory + gleicher langer Chat + neue Frage]
→ grosser Anfang gecached
→ nur neuer Teil wird frisch verarbeitet
```

## Bedeutet cached = kostenlos?

Nicht zwingend. Je nach Produkt/API kann cached Input:

* günstiger sein,
* schneller verarbeitet werden,
* anders gezählt werden,
* oder nur intern als Performance-Metrik erscheinen.

Bei ChatGPT selbst ist es eher eine **Nutzungs-/Diagnoseanzeige**, nicht automatisch eine direkte Rechnung wie bei der API.

## Warum ist cached höher als normaler Input?

Deine Zahlen:

```text
input:   18’831’387
cached: 696’693’120
output:   1’318’967
```

Das heisst: Über alle gezählten Vorgänge hinweg wurde sehr viel Kontext immer wieder recycelt.

Das Verhältnis:

```text
696’693’120 / 18’831’387 ≈ 37
```

Also grob: Für jeden “frisch” gezählten Input-Token wurden etwa **37 gecachte Input-Tokens** wiederverwendet.

Das passt gut zu langen Gesprächen, Custom Instructions, Memory, Tool-Workflows und wiederholten Modellaufrufen.

## Wichtig

Das heisst **nicht**:

* dass dein Kontextfenster 696 Mio Tokens gross war,
* dass das Modell alles gleichzeitig im Kopf hatte,
* dass eine einzelne Antwort 696 Mio Tokens gelesen hat,
* dass du 696 Mio neue Tokens verbraucht hast.

Es heisst eher:

> Dein Workflow hat sehr viele wiederkehrende Kontextteile, und das System konnte diese über viele Aufrufe hinweg aus dem Cache bedienen.

Kurz gesagt: **cached tokens sind “wiedererkannte, wiederverwendete Promptteile” — kumuliert über viele Modellaufrufe.**


