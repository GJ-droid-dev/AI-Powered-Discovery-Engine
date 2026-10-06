"""Generate realistic, diverse r/googlephotos seed data for offline / fallback collection."""

import json
from pathlib import Path
from datetime import datetime, timezone

SEED_POSTS = [
    {
        "title": "Why can't Google Photos search by atmosphere or vibe? 'Cozy coffee shop rainy day' gives me zero results",
        "body": "I took a photo 2 years ago sitting by the window in a quiet café in Seattle while it was pouring outside. I remember the warm string lights, steam from my latte mug, and rain streaks on the window. When I type 'coffee shop rainy day' or 'rainy coffee shop Seattle' it brings up random pictures of rain in my backyard and a Starbucks receipt. It completely fails to understand the scene context!",
        "subreddit": "googlephotos",
        "permalink": "/r/googlephotos/comments/12a1b1/why_cant_google_photos_search_by_atmosphere/",
        "score": 142,
        "author": "seattle_coffee_lover",
        "date": "2024-11-12T14:32:00Z",
        "comments": [
            "Same issue here. I tried searching 'sunny picnic in the park with red blanket' and it showed photos of red cars. Google Photos AI is good at object tags ('coffee cup', 'dog') but terrible at understanding narrative memory or context.",
            "I spent 45 minutes scrolling through 2022 trying to find my anniversary dinner photo because I only remember the candlelit table and dimmed lighting, but search only knows 'table' or 'restaurant' which brings up 500 work lunch pictures.",
            "This is what drives me crazy. Our human memory recalls how an event felt or the situation (e.g. 'breakfast after my morning hike') but search only accepts literal nouns like 'pancake'."
        ]
    },
    {
        "title": "Search by date is completely broken when I don't know the exact year or month",
        "body": "I know I went to that concert sometime in late autumn between 2017 and 2019. If I search 'concert fall 2018' or 'outdoor music festival autumn', it gives nothing. I literally have to manually scroll through 3 years of thumbnails hoping my eyes catch the stage lighting. Why can't I search 'concert in October or November around 2018'?",
        "subreddit": "googlephotos",
        "permalink": "/r/googlephotos/comments/13b2c2/search_by_date_is_completely_broken_temporal/",
        "score": 89,
        "author": "festival_goer_99",
        "date": "2024-10-05T09:15:00Z",
        "comments": [
            "Temporal search is so rigid. You either type 'October 2018' or nothing. Humans don't remember timestamps, we remember 'about 5 years ago around Thanksgiving'.",
            "Also when you travel across timezones, the timestamps get messed up and photos from the same evening get split across different days in the timeline."
        ]
    },
    {
        "title": "Searching for a specific visual detail is impossible (e.g. 'yellow vintage suitcase in hotel room')",
        "body": "I took a photo of my luggage tag on a bright mustard yellow vintage suitcase inside a hotel room. Searching 'yellow suitcase' shows yellow flowers, yellow t-shirts, and my friend's yellow car. It doesn't pinpoint the suitcase at all. I had to scroll back through 10,000 photos to find it.",
        "subreddit": "googlephotos",
        "permalink": "/r/googlephotos/comments/14c3d3/searching_for_visual_detail_is_impossible/",
        "score": 67,
        "author": "nomad_traveler",
        "date": "2024-09-20T18:40:00Z",
        "comments": [
            "Color search in Google Photos is the worst. If I search 'blue dress', it matches any photo that has a blue sky in the background!",
            "I was searching for a picture of my dog wearing a red bandana. Search 'dog red bandana' showed every photo of my dog (over 800 photos) and highlighted random red objects in other photos."
        ]
    },
    {
        "title": "People + Event combinations fail constantly. 'Dave and Sarah wedding' brings up every photo of Dave ever taken",
        "body": "I wanted to find the photo where my brother Dave and his fiancée Sarah were dancing at Mark's wedding in 2021. Both Dave and Sarah have named face clusters. When I search 'Dave Sarah wedding', instead of showing photos containing both of them in formal attire or wedding settings, it just dumps every single photo of Dave from 2015 to 2024. The co-occurrence logic is non-existent.",
        "subreddit": "googlephotos",
        "permalink": "/r/googlephotos/comments/15d4e4/people_event_combinations_fail_constantly/",
        "score": 210,
        "author": "family_archivist",
        "date": "2024-12-01T11:05:00Z",
        "comments": [
            "Yes! It performs an OR search instead of an AND search, or it completely ignores the event keyword 'wedding'.",
            "Try searching 'Mom and Dad Christmas'. It gives me 1,200 photos of Mom, half of which Dad isn't in, and half aren't even during Christmas.",
            "Face recognition is amazing in isolation, but query composition where you combine faces + activities + setting is totally broken."
        ]
    },
    {
        "title": "Can't find a picture of a receipt / warranty serial number I snapped 6 months ago",
        "body": "I bought a refrigerator last year and took a photo of the appliance model sticker and the paper receipt from Home Depot. I tried searching 'Home Depot receipt', 'refrigerator serial number', 'appliance sticker', 'model number'. Zero results. The OCR in Google Photos seems to only index words if the image looks like a clean document, not if it's a photo taken under kitchen lighting.",
        "subreddit": "googlephotos",
        "permalink": "/r/googlephotos/comments/16e5f5/cant_find_picture_of_receipt_warranty_serial/",
        "score": 115,
        "author": "homeowner_diy",
        "date": "2024-08-14T20:10:00Z",
        "comments": [
            "OCR search in Google Photos is so hit-or-miss. It will find a sign in the background of a street photo, but fail to find text on a clearly visible handwritten note or store receipt.",
            "I ended up creating an album called 'Receipts and Documents' because searching for screenshots or documents is a nightmare.",
            "Same with parking tickets or parking garage level photos. I take a picture of 'Section 4B Blue Level' so I remember where I parked. Searching 'parking' 3 hours later shows airport runways!"
        ]
    },
    {
        "title": "Searching for secondary objects in the background (not the main subject)",
        "body": "I remember taking a picture of my kid playing in the living room, and in the background on the coffee table was a book my grandmother gave me. I wanted to see the book cover title. Searching 'book' or 'living room book' only shows pictures where a book fills the entire frame. If an object is secondary in the background, Google Photos search completely overlooks it.",
        "subreddit": "googlephotos",
        "permalink": "/r/googlephotos/comments/17f6g6/searching_for_secondary_objects_in_background/",
        "score": 93,
        "author": "bookworm_mom",
        "date": "2024-07-28T16:22:00Z",
        "comments": [
            "This is such a common failure mode. User remembers an incidental detail: 'my brother holding a green water bottle', but the AI only tagged 'person, smiling, indoor'.",
            "I had a similar issue trying to find the paint color on our dining room wall from a photo of Christmas dinner. Couldn't find it without scrolling."
        ]
    },
    {
        "title": "Google Photos search makes me want to switch back to local folders on my PC",
        "body": "I have 45,000 photos in Google Photos spanning 12 years. Finding anything specific is becoming an ordeal. The search bar promises 'search anything' but in reality if you don't remember the exact city or year, you're doomed. What happened to semantic understanding? It feels like search hasn't improved since 2018.",
        "subreddit": "googlephotos",
        "permalink": "/r/googlephotos/comments/18g7h7/google_photos_search_makes_me_want_to_switch/",
        "score": 184,
        "author": "tech_minimalist",
        "date": "2025-01-10T13:45:00Z",
        "comments": [
            "I'm considering exporting everything to Apple Photos or Immich. Immich with CLIP search actually finds complex queries much better than Google Photos.",
            "The frustrating thing is they announce 'Ask Photos' with Gemini, but for 95% of users it's still rolled out selectively or gives vague answers.",
            "If they just allowed natural language queries like 'the photo where I was changing a flat tire in the rain' it would solve 90% of my frustration."
        ]
    },
    {
        "title": "Lost my grandfather's handwritten recipe card photo in a sea of food pictures",
        "body": "A few years ago my grandpa wrote down his secret marinara sauce recipe on an index card. I took a photo of it. When I search 'recipe' or 'handwritten' or 'pasta card' or 'index card', Google Photos shows 300 plates of spaghetti and pizza I ate at restaurants, but NOT the photo of the recipe card. How do I find this without manual scrolling?",
        "subreddit": "googlephotos",
        "permalink": "/r/googlephotos/comments/19h8i8/lost_my_grandfathers_handwritten_recipe_card/",
        "score": 156,
        "author": "culinary_heritage",
        "date": "2025-02-04T17:30:00Z",
        "comments": [
            "Have you tried searching 'text' or 'paper'? Sometimes that works, but yeah, Google Photos struggles to distinguish handwritten notes from restaurant food menus.",
            "I had the exact same experience with an old postcard. Food search is way over-sensitive to any culinary keyword."
        ]
    },
    {
        "title": "Trip photos from a road trip: searching by route or stops is impossible",
        "body": "Took a road trip from Denver to Moab. We stopped at a random quirky diner shaped like a spaceship or teapot. I don't remember the town name or date, just that it was midway on the drive. Searching 'road trip diner' or 'quirky diner Colorado Utah' returns nothing. The map view in Google Photos is clumsy because you have to zoom into every tiny highway pin.",
        "subreddit": "googlephotos",
        "permalink": "/r/googlephotos/comments/1ai9j9/trip_photos_from_a_road_trip_searching_by_route/",
        "score": 78,
        "author": "roadtrip_enthusiast",
        "date": "2024-06-18T10:00:00Z",
        "comments": [
            "The map view on web is basically unusable for road trips with thousands of photos along a corridor.",
            "We need journey-based clustering. 'Photos taken between City A and City B on the same day'."
        ]
    },
    {
        "title": "Searching for emotion or mood: 'funny face', 'crying baby', 'laughing together'",
        "body": "My daughter made this hilarious goofy face with spaghetti on her head when she was a toddler. Searching 'funny face' or 'silly face' or 'laughing' gives generic smiling portraits. It has no semantic grasp of humor, chaos, or candid emotional moments. It treats every smile identically.",
        "subreddit": "googlephotos",
        "permalink": "/r/googlephotos/comments/1bj0k0/searching_for_emotion_or_mood_funny_face_crying/",
        "score": 133,
        "author": "dad_of_two",
        "date": "2025-01-22T08:15:00Z",
        "comments": [
            "Candid vs posed is a huge blind spot. I want to find genuine laughter or emotional moments from our wedding, not the 200 posed formal group shots.",
            "Google Photos prioritizes high technical quality (in focus, bright lighting, centered face) which means candid blurry hilarious memories are buried."
        ]
    },
    {
        "title": "Whiteboard notes from brainstorming sessions are unfindable unless you remember the month",
        "body": "At work we take photos of whiteboards after sprint planning. When I search 'whiteboard' or 'architecture diagram', Google Photos shows whiteboards from 5 years ago mixed with pictures of white walls and notebook pages. Searching for words written on the board like 'Kubernetes migration' fails 80% of the time because the marker glare messes up OCR.",
        "subreddit": "googlephotos",
        "permalink": "/r/googlephotos/comments/1ck1l1/whiteboard_notes_from_brainstorming_unfindable/",
        "score": 112,
        "author": "devops_dan",
        "date": "2024-11-01T15:20:00Z",
        "comments": [
            "Whiteboard photos should have an automatic contrast booster and dedicated OCR pipeline like Office Lens. Google Photos just treats them as normal JPEG photos.",
            "I have about 80 whiteboard photos. If I search 'whiteboard 2023' it doesn't even filter properly by year."
        ]
    },
    {
        "title": "Finding photos of a pet before and after an adoption or surgery",
        "body": "Our rescue golden retriever had a severe limp and shaved leg when we adopted him in summer 2020. I wanted to show the vet how his leg looked back then versus now. Searching 'dog shaved leg' or 'dog surgery 2020' returned every photo of my dog ever taken. Face recognition grouped him, but attribute-level search across the pet's timeline is completely missing.",
        "subreddit": "googlephotos",
        "permalink": "/r/googlephotos/comments/1dl2m2/finding_photos_of_pet_before_after_surgery/",
        "score": 98,
        "author": "golden_dad",
        "date": "2024-09-12T12:00:00Z",
        "comments": [
            "Pet tagging is great for identity, but terrible for specific pet memories. Try finding 'dog at the beach' when you live near a beach.",
            "I couldn't find the photo of my cat sleeping in a shoe box. Searching 'cat box' showed Amazon delivery boxes on my porch."
        ]
    },
    {
        "title": "Vaccination cards and COVID records disappeared into the photo abyss",
        "body": "Whenever I travel internationally I need my vaccination card photo. I search 'vaccine card', 'CDC card', 'vaccination record', 'immunization'. Nothing comes up. I end up having to scroll back to March 2021 manually. Why doesn't Google Photos recognize important health or identification documents and give them a quick access shelf?",
        "subreddit": "googlephotos",
        "permalink": "/r/googlephotos/comments/1em3n3/vaccination_cards_and_records_in_photo_abyss/",
        "score": 167,
        "author": "world_traveler_88",
        "date": "2025-01-05T19:40:00Z",
        "comments": [
            "They have 'Documents' category under Search -> Categories, but it lumps together parking meters, receipts, screenshots of memes, and tax forms.",
            "The document classification is way too coarse. A meme screenshot should not be in the same bucket as an official passport or vaccination card."
        ]
    },
    {
        "title": "Trying to find a photo where someone was wearing a specific outfit (e.g. green graduation gown)",
        "body": "My cousin graduated college in May 2019. I wanted to find the picture where she was wearing her bright forest green graduation cap and gown hugging our grandfather. Searching 'cousin green gown graduation' gave 0 results. Searching 'cousin graduation' gave photos from her high school graduation in 2015. Outfit color + event + person is such a natural way humans remember things, why can't AI handle it?",
        "subreddit": "googlephotos",
        "permalink": "/r/googlephotos/comments/1fn4o4/trying_to_find_photo_by_specific_outfit_color/",
        "score": 145,
        "author": "proud_cousin",
        "date": "2024-12-19T21:10:00Z",
        "comments": [
            "Color attributes on clothing are one of the strongest visual anchors in human memory. 'I was wearing my black leather jacket', 'she had a yellow sundress'. Google Photos completely ignores clothing color in multi-modal search.",
            "Whenever I describe a photo to someone, the first thing I say is 'remember what we were wearing?'. Search engines are built around object nouns, not human episodic memory."
        ]
    },
    {
        "title": "Car accident and insurance damage photos: can never find the odometer reading picture",
        "body": "Got into a minor fender bender in 2023. Took 15 photos: the bumper dent, license plate of other car, insurance cards, and my dashboard odometer. When the insurance adjuster asked for the mileage photo last week, I typed 'odometer', 'speedometer', 'dashboard mileage', 'car miles'. Nothing found. Had to spend 30 minutes scrolling through thousands of photos to find that specific day.",
        "subreddit": "googlephotos",
        "permalink": "/r/googlephotos/comments/1go5p5/car_accident_insurance_photos_cant_find_odometer/",
        "score": 85,
        "author": "commuter_mike",
        "date": "2024-08-03T14:15:00Z",
        "comments": [
            "Dashboard gauges have high glare and numbers, and Google Photos OCR rarely parses seven-segment LCD or mechanical odometer digits.",
            "Also, why doesn't Google Photos group burst shots or all photos taken within a 15-minute window during an unusual location into an incident cluster?"
        ]
    }
]

def generate_records():
    records = []
    for post in SEED_POSTS:
        # Submission record
        records.append({
            "raw_text": f"{post['title']}\n\n{post['body']}",
            "source_url": f"https://reddit.com{post['permalink']}",
            "date": post["date"],
            "subreddit": post["subreddit"],
            "thread_title": post["title"],
            "reply_depth": 0,
            "author_hash": f"u_{hash(post['author']) & 0xFFFFFFFF:08x}",
            "score": post["score"],
        })
        # Comments
        for idx, comment in enumerate(post["comments"]):
            records.append({
                "raw_text": comment,
                "source_url": f"https://reddit.com{post['permalink']}comment_{idx}",
                "date": post["date"],
                "subreddit": post["subreddit"],
                "thread_title": post["title"],
                "reply_depth": 1,
                "author_hash": f"u_{hash(comment[:20]) & 0xFFFFFFFF:08x}",
                "score": max(5, post["score"] // (idx + 2)),
            })
    return records

if __name__ == "__main__":
    out_dir = Path("data/seed")
    out_dir.mkdir(parents=True, exist_ok=True)
    records = generate_records()
    out_file = out_dir / "reddit_seed.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"Generated {len(records)} Reddit seed records in {out_file}")
