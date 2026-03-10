# This Coffee

**The Caffeinated Storytelling RPG**

A collaborative storytelling RPG about small moments. 2–10 players take turns narrating scenes framed around the ritual of drinking coffee — each sip a chance to shape the story.

## Getting Started

```bash
pip install -r requirements.txt
python app.py
```

Open **http://localhost:8080** in your browser. One player creates a room, others join using the 5-character room code or a direct invite link.

## Game Settings

Before starting, the host chooses two settings:

### Coffee Style (Tone)

| Style | Tone |
|-------|------|
| **Black** | Sharper moments, heavier choices, stronger consequences |
| **With Milk** | Softer scenes, smaller risks, gentler outcomes |
| **With Milk & Sugar** | Lighthearted scenes, gentle stories, humour |

### Game Length

| Length | Sips per Player | Best For |
|--------|----------------|----------|
| **Espresso** | 3 each | 2–3 players |
| **Grande** | 2 each | 4–5 players |
| **Venti** | 1 each | 6+ players |
| **Open** | Until the story feels complete or sugar runs out | Any size |

## How to Play

Players take turns as the **Narrator** in a randomized order. Each turn is called a **Sip** and has two phases.

### Phase 1: Brew (Resolve)

The Narrator answers the question posed by the previous Narrator.

1. **Roll the die** — a single d6, hidden from the other players.
   - **Even** (2, 4, 6) = Favorable outcome
   - **Odd** (1, 3, 5) = Unfavorable outcome
2. **Sugar window** — before the die is revealed, *any* player may spend 1 Sugar from the shared pool to **invert** the result (favorable becomes unfavorable, and vice versa). Only one Sugar can be spent per Sip.
3. **Narrate** — the Narrator writes how the situation resolves, guided by whether the outcome is favorable or unfavorable, then reveals the die.

### Phase 2: Pour (Set Up)

The Narrator sets the scene for the next player.

1. **Describe a coffee moment** — "This coffee is…" — a short atmospheric scene.
2. **Ask a question** — pose a situation with two possible outcomes. This becomes the prompt the next Narrator will resolve in their Brew.
3. **Optionally introduce a side character** by choosing one of:
   - **Coffee is drunk** → a helpful, positive character
   - **Coffee is spilled** → a hindering, negative character

   Give the character a name and brief description. They join the story for the rest of the game.

## Sugar

Sugar is a shared resource the group spends to alter fate.

- **Starting pool**: half the number of players (rounded up)
- **Effect**: inverts a die result before the Narrator reveals it
- **Limit**: 1 Sugar per Sip, and anyone at the table can spend it
- In **Open** mode, the game ends when sugar runs out

## Ending the Game

The game ends when:
- The maximum number of Sips is reached (Espresso / Grande / Venti)
- Sugar is depleted (Open mode)
- The host ends the game early

The final screen — *"The Cup is Empty"* — displays the complete story log.

## Safety Tools

### X-Card

Any player can press the **X-Card** button at any time. This signals to the group that the current content should be reframed — no explanation needed. The Narrator acknowledges and clears it, then adjusts the narrative.

Based on the [X-Card](http://tinyurl.com/x-card-rpg) by John Stavropoulos.

### Lines & Veils

Before or during play, the group can establish:
- **Lines** — topics that are off-limits entirely
- **Veils** — topics that can exist in the story but happen "off-screen"
