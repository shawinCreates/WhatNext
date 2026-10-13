"""Hand-curated award winners (Oscars + Cannes).

TMDB carries no awards data, so this list is maintained by hand.
The seed command verifies every id against TMDB and reports misses.
"""

# shortcut: manual curation. Replace with an awards source if one appears.
# (tmdb_id, label). First label wins when a title won both.
AWARDED_MOVIES = [
    (872585, "Oscar · Best Picture 2024"),
    (1064213, "Oscar · Best Picture 2025"),
    (496243, "Oscar · Best Picture 2020"),
    (545611, "Oscar · Best Picture 2023"),
    (581734, "Oscar · Best Picture 2021"),
    (490132, "Oscar · Best Picture 2019"),
    (399055, "Oscar · Best Picture 2018"),
    (376867, "Oscar · Best Picture 2017"),
    (314365, "Oscar · Best Picture 2016"),
    (194662, "Oscar · Best Picture 2015"),
    (76241, "Oscar · Best Picture 2014"),
    (49047, "Oscar · Best Picture 2013"),
    (915935, "Cannes · Palme d'Or 2023"),
    (842942, "Cannes · Palme d'Or 2022"),
    (200203, "Cannes · Palme d'Or 2021"),
]
