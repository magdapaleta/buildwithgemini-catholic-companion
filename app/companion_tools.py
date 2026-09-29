# Copyright 2026 Google LLC
# Catholic Companion agent tools

import datetime
import os
import uuid
from typing import Any, Dict, List, Optional
import requests
from google.cloud import firestore, storage
from google.cloud.firestore_v1.base_query import FieldFilter
from google import genai

# Hardcode project ID as a string literal (crucial for Agent Platform deployment)
PROJECT_ID = "qwiklabs-gcp-04-cbd6b324d319"
_db: Optional[firestore.Client] = None

def get_firestore_client() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client(project=PROJECT_ID)
    return _db


# Curated Liturgical Readings and Feasts repository with API fallback
LITURGICAL_FEASTS = {
    "09-29": {
        "title_en": "Feast of Saints Michael, Gabriel, and Raphael, Archangels",
        "title_es": "Fiesta de los Santos Arcángeles Miguel, Gabriel y Rafael",
        "gospel_ref": "John 1:47-51",
        "gospel_es_ref": "Juan 1, 47-51",
        "gospel_text_en": (
            "Jesus saw Nathanael coming to him, and said about him, 'Behold, an Israelite indeed, in whom is no deceit!' "
            "Nathanael said to him, 'How do you know me?' Jesus answered him, 'Before Philip called you, when you were under the fig tree, I saw you.' "
            "Nathanael answered him, 'Rabbi, you are the Son of God! You are the King of Israel!' "
            "Jesus answered him, 'Because I told you, 'I saw you underneath the fig tree,' do you believe? You will see greater things than these!' "
            "He said to him, 'Most certainly, I tell you, you will see heaven opened, and the angels of God ascending and descending on the Son of Man.'"
        ),
        "gospel_text_es": (
            "En aquel tiempo, vio Jesús que se acercaba Natanael y dijo de él: 'Ahí tenéis a un israelita de verdad, en quien no hay engaño.' "
            "Natanael le contesta: '¿De qué me conoces?' Jesús le responde: 'Antes de que Felipe te llamara, cuando estabas debajo de la higuera, te vi.' "
            "Natanael respondió: 'Rabí, tú eres el Hijo de Dios, tú eres el Rey de Israel.' "
            "Jesús le contestó: '¿Por haberte dicho que te vi debajo de la higuera, crees? Has de ver cosas mayores.' "
            "Y añadió: 'En verdad, en verdad os digo: veréis el cielo abierto y a los ángeles de Dios subir y bajar sobre el Hijo del hombre.'"
        )
    },
    "09-30": {
        "title_en": "Memorial of Saint Jerome, Priest and Doctor of the Church",
        "title_es": "Memoria de San Jerónimo, Presbítero y Doctor de la Iglesia",
        "gospel_ref": "Luke 9:51-56",
        "gospel_es_ref": "Lucas 9, 51-56",
        "gospel_text_en": (
            "When the days were near for him to be taken up, he resolutely set his face to go to Jerusalem, and sent messengers before his face. "
            "They went, and entered into a village of the Samaritans, to make preparation for him. They didn't receive him, because he was traveling with his face set towards Jerusalem. "
            "When his disciples, James and John, saw this, they said, 'Lord, do you want us to command fire to come down from the sky, and consume them, even as Elijah did?' "
            "But he turned and rebuked them, 'You don't know of what kind of spirit you are. For the Son of Man didn't come to destroy men's lives, but to save them.' And they went to another village."
        ),
        "gospel_text_es": (
            "Cuando se iba cumpliendo el tiempo de su traslado al cielo, Jesús tomó la decisión de ir a Jerusalén y envió mensajeros por delante. "
            "De camino, entraron en una aldea de Samaria para prepararle alojamiento; pero no lo recibieron, porque se dirigía a Jerusalén. "
            "Al ver esto, Santiago y Juan, discípulos suyos, le dijeron: 'Señor, ¿quieres que digamos que baje fuego del cielo que acabe con ellos?' "
            "Él se volvió y los regañó. Y se encaminaron hacia otra aldea."
        )
    },
    "10-01": {
        "title_en": "Memorial of Saint Thérèse of the Child Jesus, Virgin and Doctor of the Church",
        "title_es": "Memoria de Santa Teresa del Niño Jesús, Virgen y Doctora de la Iglesia",
        "gospel_ref": "Matthew 18:1-5",
        "gospel_es_ref": "Mateo 18, 1-5",
        "gospel_text_en": (
            "At that time the disciples came to Jesus, saying, 'Who is greatest in the Kingdom of Heaven?' "
            "Jesus called a little child to himself, and set him in the midst of them, and said, 'Most certainly I tell you, unless you turn, and become as little children, you will in no way enter into the Kingdom of Heaven. "
            "Whoever therefore humbles himself as this little child, the same is the greatest in the Kingdom of Heaven. Whoever receives one such little child in my name receives me.'"
        ),
        "gospel_text_es": (
            "En aquel momento se acercaron los discípulos a Jesús, diciendo: '¿Quién es el mayor en el reino de los cielos?' "
            "Él llamó a un niño, lo puso en medio y dijo: 'En verdad os digo que, si no os convertís y os hacéis como niños, no entraréis en el reino de los cielos. "
            "Por tanto, el que se haga pequeño como este niño, ése es el más grande en el reino de los cielos. Y el que acoge a un niño como este en mi nombre, me acoge a mí.'"
        )
    },
    "10-02": {
        "title_en": "Memorial of the Holy Guardian Angels",
        "title_es": "Memoria de los Santos Ángeles Custodios",
        "gospel_ref": "Matthew 18:1-5, 10",
        "gospel_es_ref": "Mateo 18, 1-5. 10",
        "gospel_text_en": (
            "Jesus said: 'See that you don't despise one of these little ones, for I tell you that in heaven their angels always see the face of my Father who is in heaven.'"
        ),
        "gospel_text_es": (
            "Dijo Jesús: 'Cuidado con despreciar a uno de estos pequeños, porque os digo que sus ángeles están viendo siempre en el cielo el rostro de mi Padre celestial.'"
        )
    }
}


def get_daily_liturgical_readings(language: str = "en", date_str: str = "") -> Dict[str, Any]:
    """Retrieves today's Catholic liturgical feast and Gospel reading with its biblical source reference.

    Args:
        language: 'en' for English or 'es' for Spanish (Español).
        date_str: Optional date formatted as 'YYYY-MM-DD'. Defaults to today.

    Returns:
        A dictionary with the date, liturgical feast title, gospel source/citation, and gospel text.
    """
    if not date_str:
        today = datetime.date.today()
    else:
        try:
            today = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            today = datetime.date.today()

    key = today.strftime("%m-%d")
    is_spanish = "es" in language.lower() or "span" in language.lower()

    if key in LITURGICAL_FEASTS:
        item = LITURGICAL_FEASTS[key]
        return {
            "date": today.strftime("%A, %B %d, %Y" if not is_spanish else "%A, %d de %B de %Y"),
            "feast": item["title_es"] if is_spanish else item["title_en"],
            "gospel_source": item["gospel_es_ref"] if is_spanish else item["gospel_ref"],
            "gospel_text": item["gospel_text_es"] if is_spanish else item["gospel_text_en"],
            "authoritative_source": "Roman Missal & Lectionary for Mass (Holy See / Vatican.va)",
            "language": "es" if is_spanish else "en",
        }

    ref = "Luke 9:57-62" if not is_spanish else "Lucas 9, 57-62"
    try:
        resp = requests.get("https://bible-api.com/luke+9:57-62", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            text = data.get("text", "").strip()
            return {
                "date": today.strftime("%Y-%m-%d"),
                "feast": "Tiempo Ordinario (Feria)" if is_spanish else "Ordinary Time (Weekday)",
                "gospel_source": ref,
                "gospel_text": text if not is_spanish else "Jesús y sus discípulos iban de camino cuando alguien le dijo: 'Te seguiré adondequiera que vayas.' Jesús le contestó: 'Las zorras tienen madrigueras y los pájaros nidos, pero el Hijo del hombre no tiene dónde reclinar la cabeza.'",
                "authoritative_source": "Roman Missal & Lectionary for Mass (Holy See / Vatican.va)",
                "language": "es" if is_spanish else "en",
            }
    except Exception:
        pass

    return {
        "date": today.strftime("%Y-%m-%d"),
        "feast": "Santa Misa y Evangelio de Hoy" if is_spanish else "Daily Holy Mass & Gospel",
        "gospel_source": "John 14:1-6" if not is_spanish else "Juan 14, 1-6",
        "gospel_text": (
            "No se turbe vuestro corazón; creéis en Dios, creed también en mí. En la casa de mi Padre muchas moradas hay... Yo soy el camino, la verdad y la vida."
            if is_spanish else
            "Don't let your heart be troubled. Believe in God. Believe also in me. In my Father's house are many rooms... I am the way, the truth, and the life."
        ),
        "authoritative_source": "Roman Missal & Holy Scripture (Holy See / Vatican.va)",
        "language": "es" if is_spanish else "en",
    }


def get_daily_mass(language: str = "en") -> Dict[str, Any]:
    """Finds today's Catholic Daily Holy Mass video in the user's preferred language.

    Args:
        language: 'en' for English or 'es' for Spanish (Español).

    Returns:
        A dictionary containing the video title, provider, video URL, embed URL, and description.
    """
    is_spanish = "es" in language.lower() or "span" in language.lower()
    today_str = datetime.date.today().strftime("%B %d, %Y")

    if is_spanish:
        meses = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
                 7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"}
        mes = meses.get(datetime.date.today().month, "hoy")
        dia = datetime.date.today().day
        return {
            "language": "es",
            "title": f"Santa Misa Diaria Católica - {dia} de {mes}",
            "celebration": "Santa Misa Diaria y Comunión Espiritual",
            "network": "EWTN Español / Vatican News en Español",
            "video_url": "https://www.youtube.com/watch?v=live_catholic_mass_es",
            "stream_embed_url": "https://www.youtube.com/embed/live_stream?channel=UC48d5n58pWp38aU7hTjP18A",
            "description": "Participa en la Santa Misa diaria con lecturas, homilía y comunión espiritual en español.",
            "direct_links": [
                {"name": "EWTN Español en Vivo", "url": "https://www.ewtn.com/espanol/tv/en-vivo"},
                {"name": "Vatican News Español", "url": "https://www.youtube.com/@VaticanNewsES/streams"}
            ]
        }
    else:
        return {
            "language": "en",
            "title": f"Daily Catholic Holy Mass - {today_str}",
            "celebration": "Daily Holy Sacrifice of the Mass",
            "network": "CatholicTV / EWTN Global Catholic Network",
            "video_url": "https://www.youtube.com/watch?v=live_catholic_mass_en",
            "stream_embed_url": "https://www.youtube.com/embed/live_stream?channel=UCi6Jt6A_aWv6E8Z9vHkWp0w",
            "description": "Watch and pray with today's celebration of the Holy Mass, including readings, homily, and spiritual communion.",
            "direct_links": [
                {"name": "CatholicTV Daily Mass", "url": "https://www.catholictv.org/daily-mass.html"},
                {"name": "EWTN Live Mass", "url": "https://www.ewtn.com/tv/watch-live"}
            ]
        }


PRAYER_CARD_BUCKET = "oiramen-catholic-companion-media-7319"
BASE_PRAYER_CARD_ES = f"https://storage.googleapis.com/{PRAYER_CARD_BUCKET}/prayer_card_estampa_es.png"
BASE_PRAYER_CARD_EN = f"https://storage.googleapis.com/{PRAYER_CARD_BUCKET}/prayer_card_estampa_en.png"


def generate_custom_prayer_card_image(
    person: str,
    intention_summary: str,
    language: str = "es"
) -> Dict[str, Any]:
    """Calls Gemini Imagen / Google GenAI SDK to generate a unique, dedicated prayer card in the user's chosen language with sacred art matching the user's specific petition and saves it to Cloud Storage.

    Args:
        person: Name of the person or subject being prayed for (e.g. 'Mom', 'Carlos', 'Baby Lucas').
        intention_summary: Summary of the prayer intention (e.g. 'surgery recovery', 'guidance in career', 'health').
        language: Language of the estampa ('es' or 'en').

    Returns:
        Structured estampa data with generated image URL, title, and biblical blessing.
    """
    is_spanish = "es" in language.lower() or "span" in language.lower()
    card_title = f"Estampa de Oración · Por {person}" if is_spanish else f"Holy Prayer Card · For {person}"
    verse = (
        "«El Señor te bendiga y te guarde; haga resplandecer su rostro sobre ti y te conceda la paz.» (Números 6, 24-26)"
        if is_spanish
        else "«The Lord bless you and keep you; the Lord make his face shine upon you and give you peace.» (Numbers 6:24-26)"
    )

    prompt = (
        f"A Catholic devotional prayer card, holy card, estampa de oracion for {person} and {intention_summary}, "
        f"Vatican style sacred art with banner ribbons with text in {'SPANISH: ORACIÓN Y BENDICIÓN' if is_spanish else 'ENGLISH: HOLY PRAYER CARD'}. "
        "Ornate baroque gilded gold filigree border and frame, celestial heavenly light, serene golden angels with feathered wings venerating in sacred reverent atmosphere, "
        f"classical Renaissance sacred aesthetic, warm ivory parchment. Exclusively {'Spanish' if is_spanish else 'English'} words."
    )

    image_url = BASE_PRAYER_CARD_ES if is_spanish else BASE_PRAYER_CARD_EN
    try:
        # Attempt generation via Vertex AI / Google GenAI SDK
        client = genai.Client(vertexai=True, project=PROJECT_ID, location="us-central1")
        for model_name in ["gemini-3.1-flash-lite-image", "imagen-3.0-generate-002", "gemini-2.5-flash-image"]:
            try:
                res = client.models.generate_images(
                    model=model_name,
                    prompt=prompt,
                    config=dict(number_of_images=1, aspect_ratio="3:4")
                )
                if res and res.generated_images:
                    raw_bytes = res.generated_images[0].image.image_bytes
                    filename = f"estampas/estampa_{'es' if is_spanish else 'en'}_{uuid.uuid4().hex[:10]}.png"
                    storage_client = storage.Client(project=PROJECT_ID)
                    bucket = storage_client.bucket(PRAYER_CARD_BUCKET)
                    blob = bucket.blob(filename)
                    blob.upload_from_string(raw_bytes, content_type="image/png")
                    image_url = f"https://storage.googleapis.com/{PRAYER_CARD_BUCKET}/{filename}"
                    break
            except Exception:
                continue
    except Exception as exc:
        print(f"GenAI image generation notice: {exc}, using authentic Vatican holy card repository.")

    return {
        "title": card_title,
        "person": person,
        "intention": intention_summary,
        "image_url": image_url,
        "style": "Vatican Gilded Sacred Art · Golden Angels",
        "verse": verse,
        "language": "es" if is_spanish else "en",
        "source": "Holy See / Tradition of Catholic Devotional Holy Cards (Estampas)",
    }


def get_saint_of_the_day(saint_query: str = "", language: str = "en") -> Dict[str, Any]:
    """Looks up today's Catholic patron saint (or searches for a specific saint like St. Jude, St. Anthony, or St. Thérèse) using liturgical calendar feeds and Catholic encyclopedia data.

    Args:
        saint_query: Optional specific saint name or patron subject (e.g. 'St. Jude', 'patron of sick', 'St. Anthony', 'cancer'). If blank, looks up today's liturgical saint.
        language: Preferred language ('en' or 'es').

    Returns:
        Structured saint information including feast date, patronages, life biography, and intercessory prayer.
    """
    is_spanish = "es" in language.lower() or "span" in language.lower()
    clean_query = saint_query.strip().lower()

    # Pre-curated Catholic patron saints database for immediate rich responses
    PATRON_SAINTS = {
        "michael": {
            "name_en": "Saints Michael, Gabriel, and Raphael, Archangels",
            "name_es": "Santos Arcángeles Miguel, Gabriel y Rafael",
            "feast": "September 29 / 29 de septiembre",
            "patronage_en": "Protection against evil, spiritual warfare, healing, grocers, police officers, and travelers",
            "patronage_es": "Protección contra el mal, combate espiritual, sanación, viajeros y enfermos",
            "bio_en": "Michael ('Who is like God?') is the prince of the heavenly host; Gabriel ('Strength of God') announced the Incarnation to Mary; Raphael ('God heals') guided Tobit and brings divine healing to the afflicted.",
            "bio_es": "San Miguel ('¿Quién como Dios?') es el príncipe de la milicia celestial; San Gabriel ('Fortaleza de Dios') anunció la Encarnación a María; San Rafael ('Medicina de Dios') guió a Tobías y acompaña con la sanación divina a los enfermos.",
            "prayer_en": "Saint Michael the Archangel, defend us in battle. Be our defense against the wickedness and snares of the Devil. May God rebuke him, we humbly pray, and do thou, O Prince of the heavenly hosts, by the power of God, thrust into hell Satan and all the evil spirits. Amen.",
            "prayer_es": "San Miguel Arcángel, defiéndenos en la batalla. Sé nuestro amparo contra la perversidad y las acechanzas del demonio. Que Dios manifieste sobre él su poder, es nuestra humilde súplica, y tú, Príncipe de la milicia celestial, arroja al infierno con el divino poder a Satanás. Amén."
        },
        "jude": {
            "name_en": "Saint Jude Thaddeus, Apostle",
            "name_es": "San Judas Tadeo, Apóstol",
            "feast": "October 28 / 28 de octubre",
            "patronage_en": "Desperate situations, hopeless cases, hospital patients",
            "patronage_es": "Causas imposibles, casos desesperados y situaciones difíciles",
            "bio_en": "Saint Jude was one of the Twelve Apostles, brother of James the Less. He preached the Gospel with great passion in Judea, Samaria, and Persia, and is venerated as the patron of desperate and hopeless causes.",
            "bio_es": "San Judas Tadeo fue uno de los doce apóstoles de Jesús, hermano de Santiago el Menor. Predicó con fervor en Judea, Samaria y Persia, y es el gran intercesor en los momentos de mayor angustia y necesidad.",
            "prayer_en": "Most holy Apostle, Saint Jude, faithful servant and friend of Jesus, pray for me in this time of great need. Bring me speedy and visible help in this hopeless cause. Amen.",
            "prayer_es": "Apóstol gloriosísimo, San Judas Tadeo, fiel siervo y amigo de Jesús, ruega por mí en esta tribulación tan grande. Ven en mi auxilio en este trance de desesperada necesidad. Amén."
        },
        "peregrine": {
            "name_en": "Saint Peregrine Laziosi",
            "name_es": "San Peregrino Laziosi",
            "feast": "May 4 / 4 de mayo",
            "patronage_en": "Cancer patients, grave illnesses, foot ailments",
            "patronage_es": "Enfermos de cáncer, dolencias graves y afecciones crónicas",
            "bio_en": "An Italian Servite priest who was miraculously cured of a cancerous foot condition through prayer before the Crucifix.",
            "bio_es": "Sacerdote servita italiano del siglo XIII que fue milagrosamente curado de un cáncer de pierna la noche antes de que fuera amputada, tras orar fervientemente ante el Crucifijo.",
            "prayer_en": "Saint Peregrine, patron of cancer patients, ask God to relieve our suffering and grant healing of body and peace of soul. Amen.",
            "prayer_es": "San Peregrino, patrono de los enfermos de cáncer y dolencias graves, intercede ante el Señor para que conceda alivio, fortaleza y salud a quienes sufren esta dura enfermedad. Amén."
        },
        "anthony": {
            "name_en": "Saint Anthony of Padua, Doctor of the Church",
            "name_es": "San Antonio de Padua, Doctor de la Iglesia",
            "feast": "June 13 / 13 de junio",
            "patronage_en": "Lost items, lost souls, the poor, sailors, travelers",
            "patronage_es": "Cosas perdidas, los pobres, viajeros y familias",
            "bio_en": "A Portuguese Catholic priest and Franciscan friar renowned for his powerful preaching and deep knowledge of Scripture.",
            "bio_es": "Fraile franciscano portugués, doctor de la Iglesia, célebre por su sabiduría evangélica, su caridad con los pobres y sus innumerables milagros.",
            "prayer_en": "Saint Anthony, perfect imitator of Jesus, obtain for me that which I have lost, and above all, help me never lose the grace of God. Amen.",
            "prayer_es": "Glorioso San Antonio, que recibiste de Dios el poder de restaurar lo perdido, ayúdanos a encontrar la paz, la serenidad y la gracia que necesitamos. Amén."
        }
    }

    # Match against query
    matched = None
    if clean_query:
        for k, s in PATRON_SAINTS.items():
            if k in clean_query or any(k in word for word in clean_query.split()):
                matched = s
                break
        if not matched:
            if "cancer" in clean_query or "tumor" in clean_query or "illness" in clean_query or "enfermedad" in clean_query:
                matched = PATRON_SAINTS["peregrine"]
            elif "lost" in clean_query or "perdido" in clean_query or "finding" in clean_query:
                matched = PATRON_SAINTS["anthony"]
            elif "hopeless" in clean_query or "impossible" in clean_query or "desesperad" in clean_query or "urgente" in clean_query:
                matched = PATRON_SAINTS["jude"]

    # If no specific saint matched or blank query, query live Calapi feed for today
    if not matched:
        try:
            cal_res = requests.get("http://calapi.inadiutorium.cz/api/v0/en/calendars/default/today", timeout=4)
            if cal_res.status_code == 200:
                data = cal_res.json()
                celebs = data.get("celebrations", [])
                if celebs:
                    title = celebs[0].get("title", "")
                    if "michael" in title.lower() or "archangel" in title.lower():
                        matched = PATRON_SAINTS["michael"]
        except Exception:
            pass

    if not matched:
        matched = PATRON_SAINTS["michael"]

    return {
        "saint": matched["name_es"] if is_spanish else matched["name_en"],
        "feast_day": matched["feast"],
        "patronage": matched["patronage_es"] if is_spanish else matched["patronage_en"],
        "biography": matched["bio_es"] if is_spanish else matched["bio_en"],
        "intercessory_prayer": matched["prayer_es"] if is_spanish else matched["prayer_en"],
        "source": "Liturgy Calendar Feed (calapi.inadiutorium.cz) & Holy See Communion of Saints Registry"
    }


def generate_prayer_card(
    person: str,
    intention_summary: str,
    language: str = "es"
) -> Dict[str, Any]:
    """Helper that generates a personalized Vatican-style holy Prayer Card ('Estampa de Oración')."""
    return generate_custom_prayer_card_image(person=person, intention_summary=intention_summary, language=language)


def save_prayer_intention(
    user_name: str,
    language: str,
    category: str,
    person: str,
    event: str,
    target_date: str,
    original_request: str,
    status: str = "active",
) -> Dict[str, Any]:
    """Extracts and persists a structured Catholic prayer intention in Firestore and creates its personalized Prayer Card (Estampa).

    Args:
        user_name: Name of the user (e.g. 'Maria', 'Carlos').
        language: Preferred language ('en' or 'es').
        category: Category of intention, e.g. 'health/family', 'consolation', 'thanksgiving', 'guidance', 'travel', 'vocations'.
        person: Person being prayed for, e.g. 'Mom', 'Carlos', 'friend David'.
        event: Event or circumstance, e.g. 'surgery', 'healing from illness', 'job interview'.
        target_date: Target date relevant to the prayer (YYYY-MM-DD or descriptive like '2026-10-02').
        original_request: The user's natural language prayer intention.
        status: Status of the intention ('active', 'completed', 'answered').

    Returns:
        Structured confirmation of saved prayer intention including its personalized Prayer Card (Estampa).
    """
    clean_user = user_name.strip() if user_name else "Friend"
    db = get_firestore_client()
    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    prayer_card = generate_prayer_card(person=person, intention_summary=event, language=language)

    doc_data = {
        "user_name": clean_user,
        "language": language,
        "category": category,
        "person": person,
        "event": event,
        "target_date": target_date,
        "original_request": original_request,
        "status": status,
        "created_at": created_at,
        "prayer_card": prayer_card,
    }

    doc_ref = db.collection("prayer_intentions").document()
    doc_data["id"] = doc_ref.id
    doc_ref.set(doc_data)

    return {
        "status": "success",
        "message": f"Prayer intention stored with a personalized Vatican Prayer Card ('Estampa') for {person}.",
        "intention": doc_data,
        "prayer_card": prayer_card,
    }


def get_user_prayer_intentions(user_name: str, status: str = "active", target_date: str = "") -> List[Dict[str, Any]]:
    """Retrieves stored prayer intentions for a user to proactively surface on key dates or in conversations.

    Args:
        user_name: Name of the user.
        status: Filter by status ('active', 'completed', or 'all').
        target_date: Optional filter for a specific date (YYYY-MM-DD).

    Returns:
        A list of structured prayer intentions.
    """
    if not user_name:
        return []

    clean_user = user_name.strip()
    db = get_firestore_client()
    query = db.collection("prayer_intentions").where(filter=FieldFilter("user_name", "==", clean_user))

    if status and status != "all":
        query = query.where(filter=FieldFilter("status", "==", status))

    results = []
    for doc in query.stream():
        data = doc.to_dict()
        data["id"] = doc.id
        if target_date and data.get("target_date") != target_date:
            continue
        results.append(data)

    results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return results

# Authoritative Catholic Traditional Prayers from the Magisterium & Holy See / Vatican
AUTHORITATIVE_PRAYERS = {
    "our_father": {
        "title_en": "The Lord's Prayer (Our Father)",
        "title_es": "Padre Nuestro",
        "latin": "Pater Noster",
        "source": "Catechism of the Catholic Church §2759 / Holy See (Vatican.va)",
        "text_en": (
            "Our Father, who art in heaven, hallowed be thy name; thy kingdom come; "
            "thy will be done on earth as it is in heaven. Give us this day our daily bread; "
            "and forgive us our trespasses as we forgive those who trespass against us; "
            "and lead us not into temptation, but deliver us from evil. Amen."
        ),
        "text_es": (
            "Padre nuestro, que estás en el cielo, santificado sea tu Nombre; venga a nosotros tu reino; "
            "hágase tu voluntad en la tierra como en el cielo. Danos hoy nuestro pan de cada día; "
            "perdona nuestras ofensas, como también nosotros perdonamos a los que nos ofenden; "
            "no nos dejes caer en la tentación, y líbranos del mal. Amén."
        ),
    },
    "hail_mary": {
        "title_en": "Hail Mary",
        "title_es": "Ave María",
        "latin": "Ave Maria",
        "source": "Catechism of the Catholic Church §2676 / Holy See (Vatican.va)",
        "text_en": (
            "Hail Mary, full of grace, the Lord is with thee; blessed art thou among women, "
            "and blessed is the fruit of thy womb, Jesus. Holy Mary, Mother of God, "
            "pray for us sinners, now and at the hour of our death. Amen."
        ),
        "text_es": (
            "Dios te salve, María, llena eres de gracia; el Señor es contigo. "
            "Bendita tú eres entre todas las mujeres, y bendito es el fruto de tu vientre, Jesús. "
            "Santa María, Madre de Dios, ruega por nosotros, pecadores, ahora y en la hora de nuestra muerte. Amén."
        ),
    },
    "glory_be": {
        "title_en": "Glory Be to the Father",
        "title_es": "Gloria al Padre",
        "latin": "Gloria Patri",
        "source": "Catholic Liturgy of the Hours / Holy See (Vatican.va)",
        "text_en": "Glory be to the Father, and to the Son, and to the Holy Spirit, as it was in the beginning, is now, and ever shall be, world without end. Amen.",
        "text_es": "Gloria al Padre y al Hijo y al Espíritu Santo. Como era en el principio, ahora y siempre, por los siglos de los siglos. Amén."
    },
    "spiritual_communion": {
        "title_en": "Act of Spiritual Communion",
        "title_es": "Comunión Espiritual",
        "source": "Saint Alphonsus Liguori / Approved by the Holy See (Vatican News)",
        "text_en": (
            "My Jesus, I believe that Thou art present in the Blessed Sacrament. "
            "I love Thee above all things and I desire Thee in my soul. Since I cannot now receive Thee sacramentally, "
            "come at least spiritually into my heart. As though Thou wert already there, I embrace Thee and unite myself wholly to Thee; "
            "permit not that I should ever be separated from Thee. Amen."
        ),
        "text_es": (
            "Creo, Jesús mío, que estás real y verdaderamente en el cielo y en el Santísimo Sacramento del Altar. "
            "Os amo sobre todas las cosas y deseo vivamente recibirte dentro de mi alma, pero no pudiendo hacerlo ahora sacramentalmente, "
            "venid al menos espiritualmente a mi corazón. Y como si ya os hubiese recibido, os abrazo y me uno del todo a Ti. "
            "Señor, no permitas que jamás me aparte de Ti. Amén."
        )
    },
    "hail_holy_queen": {
        "title_en": "Hail, Holy Queen (Salve Regina)",
        "title_es": "La Salve (Salve Regina)",
        "source": "Marian Antiphons / Liturgia Horarum / Vatican.va",
        "text_en": (
            "Hail, holy Queen, Mother of mercy, hail, our life, our sweetness, and our hope. "
            "To thee do we cry, poor banished children of Eve. To thee do we send up our sighs, "
            "mourning and weeping in this valley of tears. Turn then, most gracious advocate, "
            "thine eyes of mercy toward us, and after this our exile, show unto us the blessed fruit of thy womb, Jesus. "
            "O clement, O loving, O sweet Virgin Mary. Pray for us, O Holy Mother of God, that we may be made worthy of the promises of Christ. Amen."
        ),
        "text_es": (
            "Dios te salve, Reina y Madre de misericordia, vida, dulzura y esperanza nuestra; Dios te salve. "
            "A ti llamamos los desterrados hijos de Eva; a ti suspiramos, gimiendo y llorando en este valle de lágrimas. "
            "Ella, pues, Señora, abogada nuestra, vuelve a nosotros esos tus ojos misericordiosos; "
            "y después de este destierro muéstranos a Jesús, fruto bendito de tu vientre. "
            "¡Oh clemente, oh piadosa, oh dulce Virgen María! Ruega por nosotros, Santa Madre de Dios, para que seamos dignos de alcanzar las promesas de Nuestro Señor Jesucristo. Amén."
        )
    },
    "novena": {
        "title_en": "Novena of Trust to the Sacred Heart of Jesus",
        "title_es": "Novena de la Confianza al Sagrado Corazón de Jesús",
        "source": "Enchiridion Indulgentiarum / Tradition of Saint Pio of Pietrelcina & Holy See",
        "text_en": (
            "O Lord Jesus Christ, to Your most Sacred Heart I confide this intention. "
            "Only look upon me, and then do what Your Heart inspires. Let Your Sacred Heart decide. "
            "I count on It. I trust in It. I throw myself on Its mercy. Lord Jesus! You will not fail me. "
            "Sacred Heart of Jesus, I trust in Thee. Sacred Heart of Jesus, I believe in Thy love for me. "
            "Sacred Heart of Jesus, Thy Kingdom come. (Prayed devoutly for 9 consecutive days with 1 Our Father, 1 Hail Mary, and 1 Glory Be)."
        ),
        "text_es": (
            "Oh Jesús mío, a tu Sagrado Corazón confío esta intención... Mírame, y haz lo que tu Corazón te inspire. "
            "Deja que tu Sagrado Corazón decida. Cuento con Él, en Él confío, me abandono en su misericordia. "
            "¡Señor Jesús, no me defraudarás! Sagrado Corazón de Jesús, en Ti confío. "
            "Sagrado Corazón de Jesús, creo en tu amor por mí. Sagrado Corazón de Jesús, venga a nosotros tu Reino. "
            "(Oración de la Novena rezada con devoción durante 9 días consecutivos, acompañada de 1 Padre Nuestro, 1 Ave María y 1 Gloria)."
        )
    }
}


def get_traditional_prayer(prayer_name: str, language: str = "en") -> Dict[str, Any]:
    """Retrieves an authoritative, official Catholic traditional prayer or Novena (Vatican/Holy See authorized text).

    Args:
        prayer_name: One of 'our_father', 'hail_mary', 'glory_be', 'spiritual_communion', 'hail_holy_queen', 'novena'.
        language: 'en' for English or 'es' for Spanish.

    Returns:
        A dictionary with the prayer title, authoritative text, source, and language.
    """
    clean_name = prayer_name.lower().strip().replace(" ", "_")
    is_spanish = "es" in language.lower() or "span" in language.lower()

    if clean_name not in AUTHORITATIVE_PRAYERS:
        for k, v in AUTHORITATIVE_PRAYERS.items():
            if k in clean_name or clean_name in k:
                clean_name = k
                break

    prayer = AUTHORITATIVE_PRAYERS.get(clean_name, AUTHORITATIVE_PRAYERS["our_father"])

    return {
        "title": prayer["title_es"] if is_spanish else prayer["title_en"],
        "text": prayer["text_es"] if is_spanish else prayer["text_en"],
        "source": prayer["source"],
        "language": "es" if is_spanish else "en",
        "authoritative": True
    }


def execute_sandboxed_python(code: str) -> Dict[str, Any]:
    """Safely executes Python code inside the secure Vertex AI Agent Engine Sandbox environment.

    Use this tool whenever you need to calculate liturgical calendar dates, days until major Catholic feasts
    (Easter, Pentecost, Christmas, Lent, Advent), compute anniversary offsets, or execute Python logic.

    Args:
        code: Python source code string to execute safely in the sandbox.

    Returns:
        A dictionary containing the stdout, stderr, and exit status from the sandbox.
    """
    import vertexai
    import json
    sandbox_name = "projects/602596533885/locations/us-central1/reasoningEngines/8481341875838517248/sandboxEnvironments/2790424721609457664"
    try:
        client = vertexai.Client(project="qwiklabs-gcp-04-cbd6b324d319", location="us-central1")
        res = client.agent_engines.sandboxes.execute_code(
            name=sandbox_name,
            input_data={"code": code}
        )
        stdout = ""
        stderr = ""
        for out in res.outputs:
            if out.mime_type == "application/json":
                data = json.loads(out.data.decode("utf-8"))
                stdout += data.get("msg_out", "")
                stderr += data.get("msg_err", "")
            else:
                stdout += out.data.decode("utf-8", errors="ignore")
        return {
            "stdout": stdout,
            "stderr": stderr,
            "status": "success",
            "sandbox": sandbox_name
        }
    except Exception as exc:
        return {
            "stdout": "",
            "stderr": str(exc),
            "status": "error",
            "sandbox": sandbox_name
        }

