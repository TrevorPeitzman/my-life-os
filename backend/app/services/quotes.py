"""quotes.py — Deterministic daily quote and Monday weekly challenge selection."""
from __future__ import annotations

from datetime import date

QUOTES: list[dict[str, str]] = [
    {"text": "The secret of getting ahead is getting started.", "author": "Mark Twain"},
    {"text": "Do what you can, with what you have, where you are.", "author": "Theodore Roosevelt"},
    {"text": "It always seems impossible until it's done.", "author": "Nelson Mandela"},
    {"text": "Don't watch the clock; do what it does. Keep going.", "author": "Sam Levenson"},
    {"text": "The only way to do great work is to love what you do.", "author": "Steve Jobs"},
    {"text": "In the middle of every difficulty lies opportunity.", "author": "Albert Einstein"},
    {"text": "Success is not final, failure is not fatal: it is the courage to continue that counts.", "author": "Winston Churchill"},
    {"text": "Believe you can and you're halfway there.", "author": "Theodore Roosevelt"},
    {"text": "You miss 100% of the shots you don't take.", "author": "Wayne Gretzky"},
    {"text": "The future belongs to those who believe in the beauty of their dreams.", "author": "Eleanor Roosevelt"},
    {"text": "What you get by achieving your goals is not as important as what you become.", "author": "Zig Ziglar"},
    {"text": "Hardships often prepare ordinary people for an extraordinary destiny.", "author": "C.S. Lewis"},
    {"text": "It is during our darkest moments that we must focus to see the light.", "author": "Aristotle"},
    {"text": "The best time to plant a tree was 20 years ago. The second best time is now.", "author": "Chinese Proverb"},
    {"text": "An unexamined life is not worth living.", "author": "Socrates"},
    {"text": "Spread love everywhere you go. Let no one ever come to you without leaving happier.", "author": "Mother Teresa"},
    {"text": "Always remember that you are absolutely unique. Just like everyone else.", "author": "Margaret Mead"},
    {"text": "Don't judge each day by the harvest you reap but by the seeds that you plant.", "author": "Robert Louis Stevenson"},
    {"text": "The only impossible journey is the one you never begin.", "author": "Tony Robbins"},
    {"text": "In three words I can sum up everything I've learned about life: it goes on.", "author": "Robert Frost"},
    {"text": "Too many of us are not living our dreams because we are living our fears.", "author": "Les Brown"},
    {"text": "A person who never made a mistake never tried anything new.", "author": "Albert Einstein"},
    {"text": "You become what you believe.", "author": "Oprah Winfrey"},
    {"text": "I would rather die of passion than of boredom.", "author": "Vincent van Gogh"},
    {"text": "Do one thing every day that scares you.", "author": "Eleanor Roosevelt"},
    {"text": "Nothing is impossible; the word itself says 'I'm possible!'", "author": "Audrey Hepburn"},
    {"text": "The question isn't who is going to let me; it's who is going to stop me.", "author": "Ayn Rand"},
    {"text": "It's not whether you get knocked down, it's whether you get up.", "author": "Vince Lombardi"},
    {"text": "We generate fears while we sit. We overcome them by action.", "author": "Dr. Henry Link"},
    {"text": "Whether you think you can or think you can't, you're right.", "author": "Henry Ford"},
    {"text": "Security is mostly a superstition. Life is either a daring adventure or nothing.", "author": "Helen Keller"},
    {"text": "The only real mistake is the one from which we learn nothing.", "author": "Henry Ford"},
    {"text": "Never let the fear of striking out keep you from playing the game.", "author": "Babe Ruth"},
    {"text": "When you have a dream, you've got to grab it and never let go.", "author": "Carol Burnett"},
    {"text": "Darkness cannot drive out darkness; only light can do that.", "author": "Martin Luther King Jr."},
    {"text": "We must accept finite disappointment, but never lose infinite hope.", "author": "Martin Luther King Jr."},
    {"text": "The most common way people give up their power is by thinking they don't have any.", "author": "Alice Walker"},
    {"text": "You may be disappointed if you fail, but you are doomed if you don't try.", "author": "Beverly Sills"},
    {"text": "Remember that not getting what you want is sometimes a wonderful stroke of luck.", "author": "Dalai Lama"},
    {"text": "You can't use up creativity. The more you use, the more you have.", "author": "Maya Angelou"},
    {"text": "I have learned over the years that when one's mind is made up, this diminishes fear.", "author": "Rosa Parks"},
    {"text": "I alone cannot change the world, but I can cast a stone across the water to create many ripples.", "author": "Mother Teresa"},
    {"text": "When everything seems to be going against you, remember that the airplane takes off against the wind.", "author": "Henry Ford"},
    {"text": "Education is the most powerful weapon which you can use to change the world.", "author": "Nelson Mandela"},
    {"text": "Life is not measured by the number of breaths we take, but by the moments that take our breath away.", "author": "Maya Angelou"},
    {"text": "If you're offered a seat on a rocket ship, don't ask what seat! Just get on.", "author": "Sheryl Sandberg"},
    {"text": "How wonderful it is that nobody need wait a single moment before starting to improve the world.", "author": "Anne Frank"},
    {"text": "You can never plan the future by the past.", "author": "Edmund Burke"},
    {"text": "Live in the sunshine, swim the sea, drink the wild air.", "author": "Ralph Waldo Emerson"},
    {"text": "It is not what you do for your children, but what you have taught them to do for themselves.", "author": "Ann Landers"},
    {"text": "To handle yourself, use your head; to handle others, use your heart.", "author": "Eleanor Roosevelt"},
    {"text": "If you want to lift yourself up, lift up someone else.", "author": "Booker T. Washington"},
    {"text": "Limitations live only in our minds. But if we use our imaginations, our possibilities become limitless.", "author": "Jamie Paolinetti"},
    {"text": "First, have a definite, clear practical ideal — a goal, an objective.", "author": "Aristotle"},
    {"text": "The most wasted of all days is one without laughter.", "author": "E.E. Cummings"},
    {"text": "We must be the change we wish to see in the world.", "author": "Mahatma Gandhi"},
    {"text": "Strive not to be a success, but rather to be of value.", "author": "Albert Einstein"},
    {"text": "Two roads diverged in a wood, and I took the one less traveled by.", "author": "Robert Frost"},
    {"text": "I am not a product of my circumstances. I am a product of my decisions.", "author": "Stephen Covey"},
    {"text": "Every child is an artist. The problem is how to remain an artist once we grow up.", "author": "Pablo Picasso"},
]

WEEKLY_CHALLENGES: list[str] = [
    "Take a 10-minute walk outside every day this week.",
    "Put your phone away for the first hour after waking.",
    "Read for at least 15 minutes before bed each night.",
    "Say one genuine compliment out loud to someone each day.",
    "Take a complete break from social media for the whole week.",
    "Write down three things you are grateful for before bed each night.",
    "Drink 8 glasses of water every day this week.",
    "Say 'I love you' in the mirror every morning this week.",
    "Cook at least one meal from scratch every day.",
    "Spend 10 minutes tidying one area of your home each day.",
    "Reach out to one person you haven't spoken to in a while.",
    "Go to bed 30 minutes earlier than usual every night.",
    "Do 5 minutes of deep breathing or meditation each morning.",
    "Write a handwritten note to someone who matters to you.",
    "No caffeine after 2 PM this week — see how your sleep changes.",
    "Listen to a new album, podcast, or audiobook you have never tried.",
    "Take a photo of something beautiful each day this week.",
    "Eat at least one piece of fruit or vegetable at every meal.",
    "Journal for 5 minutes each evening about what went well.",
    "Set a specific 'stop work' time and honour it every day.",
    "Spend 20 minutes in nature every day, no phone allowed.",
    "Practice one random act of kindness per day.",
    "Unsubscribe from 5 email newsletters you never read.",
    "Go for a run or brisk walk before breakfast at least 3 times.",
    "Write down one goal for the next day the night before — every night.",
    "Have at least one full meal without any screens.",
]


def get_quote(day: date) -> dict:
    """
    Return the quote or challenge for a given date.
    Monday (weekday == 0) returns a weekly challenge.
    All other days return a rotating inspirational quote.
    Both are deterministic: same date always returns the same entry.
    """
    if day.weekday() == 0:  # Monday
        idx = (day.toordinal() // 7) % len(WEEKLY_CHALLENGES)
        return {"type": "challenge", "text": WEEKLY_CHALLENGES[idx], "author": ""}
    idx = day.toordinal() % len(QUOTES)
    q = QUOTES[idx]
    return {"type": "quote", "text": q["text"], "author": q.get("author", "")}
