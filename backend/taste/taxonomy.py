"""Fixed taste taxonomy: every feature key the profile can express.

Heuristic backfill only emits the subset with TMDB metadata signal;
LLM extraction and embeddings refine the rest later. Keys here are
stable API surface — never rename, only append.
"""

GROUPS = ("narrative", "character", "emotion", "craft", "pacing", "theme", "tone")

# key: (group, plain-language label, one-line description)
FEATURES = {
    # narrative
    "narrative_complexity": (
        "narrative",
        "Complex stories",
        "Layered, non-obvious storytelling over simple plots.",
    ),
    "moral_ambiguity": (
        "narrative",
        "Moral gray areas",
        "Characters and choices without clean heroes or villains.",
    ),
    "payoff_strength": (
        "narrative",
        "Strong payoffs",
        "Setups that land — endings worth the journey.",
    ),
    "slow_burn_tolerance": (
        "narrative",
        "Slow burns",
        "Patience for deliberate build-up when the payoff earns it.",
    ),
    # character
    "character_depth": (
        "character",
        "Deep characters",
        "Layered people over plot devices.",
    ),
    "character_growth": (
        "character",
        "Character growth",
        "People who transform across the story.",
    ),
    "antihero_affinity": (
        "character",
        "Flawed protagonists",
        "Rooting for difficult, compromised leads.",
    ),
    # emotion
    "emotional_intensity": (
        "emotion",
        "Emotional intensity",
        "Stories that hit hard, not light entertainment.",
    ),
    "warmth": ("emotion", "Warmth", "Heart, kindness, and human connection."),
    "unease": (
        "emotion",
        "Tension and unease",
        "Dread, suspense, and psychological pressure.",
    ),
    "awe": (
        "emotion",
        "Awe and wonder",
        "Scale and spectacle that inspire amazement.",
    ),
    # craft
    "visual_craft": (
        "craft",
        "Visual craft",
        "Cinematography and imagery as an attraction in itself.",
    ),
    "sound_design": (
        "craft",
        "Sound and music",
        "Score and sound design carrying the experience.",
    ),
    "auteur_vision": (
        "craft",
        "Distinctive direction",
        "A strong directorial hand you can feel.",
    ),
    # pacing
    "deliberate_pacing": (
        "pacing",
        "Deliberate pacing",
        "Unhurried rhythms; mood over momentum.",
    ),
    "propulsive_pacing": (
        "pacing",
        "Propulsive pacing",
        "Momentum and drive; always moving forward.",
    ),
    # theme
    "philosophical_depth": (
        "theme",
        "Big ideas",
        "Philosophy, ideas, and questions beneath the story.",
    ),
    "historical_texture": (
        "theme",
        "Historical texture",
        "Real eras and events grounding the story.",
    ),
    "romantic_core": (
        "theme",
        "Romance at the core",
        "Love stories as the engine, not decoration.",
    ),
    # tone
    "dark_tone": ("tone", "Dark tones", "Bleakness, grit, and shadows."),
    "hopeful_tone": (
        "tone",
        "Hopeful tones",
        "Optimism and uplift, even through hardship.",
    ),
    "wit": ("tone", "Wit", "Humor, irony, and sharp dialogue."),
}

# rating -> preference weight (see 06-ml-and-taste-model.md §3)
RATING_WEIGHTS = (
    (9.0, 1.0),  # strong positive
    (8.0, 0.5),  # moderate positive
    (7.0, 0.15),  # weak positive
    (float("-inf"), -0.5),  # negative
)


def rating_weight(rating):
    for threshold, weight in RATING_WEIGHTS:
        if rating >= threshold:
            return weight
    return -0.5


# TMDB genre name -> {feature_key: prior value}. Only honest mappings;
# genres without signal emit nothing. TV genre variants included.
GENRE_FEATURES = {
    "Action": {"propulsive_pacing": 0.5, "visual_craft": 0.4, "emotional_intensity": 0.3},
    "Action & Adventure": {
        "propulsive_pacing": 0.5,
        "visual_craft": 0.4,
        "awe": 0.4,
    },
    "Adventure": {"awe": 0.5, "propulsive_pacing": 0.4, "hopeful_tone": 0.3},
    "Animation": {"visual_craft": 0.4, "warmth": 0.4, "hopeful_tone": 0.3},
    "Comedy": {"wit": 0.7, "warmth": 0.3, "hopeful_tone": 0.3},
    "Crime": {"moral_ambiguity": 0.6, "dark_tone": 0.5, "narrative_complexity": 0.3},
    "Drama": {"character_depth": 0.6, "emotional_intensity": 0.5, "character_growth": 0.4},
    "Family": {"warmth": 0.5, "hopeful_tone": 0.4},
    "Fantasy": {"awe": 0.5, "visual_craft": 0.4},
    "History": {"historical_texture": 0.7, "character_depth": 0.3},
    "Horror": {"unease": 0.7, "dark_tone": 0.5},
    "Music": {"emotional_intensity": 0.4, "warmth": 0.3},
    "Mystery": {"narrative_complexity": 0.5, "payoff_strength": 0.4},
    "Romance": {"romantic_core": 0.7, "warmth": 0.4, "emotional_intensity": 0.3},
    "Sci-Fi & Fantasy": {
        "philosophical_depth": 0.5,
        "visual_craft": 0.5,
        "awe": 0.3,
    },
    "Science Fiction": {
        "philosophical_depth": 0.5,
        "visual_craft": 0.5,
        "awe": 0.3,
    },
    "Thriller": {"unease": 0.5, "narrative_complexity": 0.4, "payoff_strength": 0.4},
    "War": {"emotional_intensity": 0.5, "dark_tone": 0.5, "historical_texture": 0.3},
    "War & Politics": {
        "emotional_intensity": 0.5,
        "dark_tone": 0.5,
        "historical_texture": 0.3,
    },
    "Western": {"moral_ambiguity": 0.4, "visual_craft": 0.4, "deliberate_pacing": 0.3},
}
