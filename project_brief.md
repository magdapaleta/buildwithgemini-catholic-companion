# My agent: Catholic Companion (Oiramen)
One-liner: A conversational Catholic spiritual companion that helps elderly believers and families practice daily prayer, access scripture/liturgical readings, and track prayer intentions with custom holy prayer cards (estampas).

Tool coverage:
- Memory: Remembers user language preference, name, past prayer intentions (person, event, target date), and spiritual follow-ups across sessions.
- Tools: Fetches daily liturgical readings (`get_daily_liturgical_readings`), daily Mass streams (`get_daily_mass`), retrieves authoritative Catholic prayers (`get_traditional_prayer`), looks up patron saints and feast days via free open liturgical feeds (`get_saint_of_the_day`), generates dedicated prayer cards (`generate_custom_prayer_card_image`), and manages/persists prayer intentions in Firestore (`save_prayer_intention`, `get_user_prayer_intentions`).
- Catalog/UI: Catalog of liturgical feasts, traditional Catholic prayers, patron saints registry, user's active prayer intentions, and custom prayer cards (estampas de oración).
- Image gen: Generates custom Vatican-style holy cards / "estampas de oración" dedicated to the user's specific prayer intentions via Gemini image generation.
- Sandbox: n/a

Recommended for every project: memory, storage (Firestore), tools, image generation, A2UI
Agent-specific / stretch (pick what fits): Bilingual support (English & Spanish), Cloud Run web frontend, Cloud Logging / Trace telemetry
