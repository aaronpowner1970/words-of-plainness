# Lyric triage - 20261007

55 arrangements: tier A 28, tier B 0, tier C 27.

A = sung words match the sheet. B = only repeats of existing sheet lines (added automatically, ruling R1). C = new words or possibly skipped lines (listed for Aaron, rulings R2/R3).

REPEAT rule: a 4+ word heard run with no sheet match is a REPEAT when its words match (SequenceMatcher token ratio >= 0.72) a contiguous span of 1-10 lines of the same arrangement's sheet; a longer run is consumed left to right by successive spans; otherwise NEW.

| tier | direct % | new | repeat | unsung | model | arrangement | reason |
|---|---:|---:|---:|---:|---|---|---|
| C | 42.6 | 16 | 0 | 35 | medium | `05_02_The_Souls_Sincere_Desire_Contemporary_Christian` | 16 NEW run(s), 35 unsung line(s) |
| C | 59.0 | 22 | 0 | 25 | medium | `05_04_The_Souls_Sincere_Desire_Celtic_Worship` | 22 NEW run(s), 25 unsung line(s) |
| C | 62.2 | 27 | 0 | 28 | medium | `AN_02_One_Voice_One_Mind_Sacred_Americana` | 27 NEW run(s), 28 unsung line(s) |
| C | 70.3 | 0 | 0 | 19 | medium | `15_03_Keep_Me_Turning_To_You_Cinematic_Orchestra` | 0 NEW run(s), 19 unsung line(s) |
| C | 71.9 | 16 | 1 | 9 | medium | `01_02_Introduction_to_Plainness_Cinematic_Inspirational` | 16 NEW run(s), 9 unsung line(s) |
| C | 75.4 | 30 | 0 | 15 | medium | `05_03_The_Souls_Sincere_Desire_Cinematic_Inspirational` | 30 NEW run(s), 15 unsung line(s) |
| C | 78.7 | 32 | 0 | 13 | medium | `05_06_The_Souls_Sincere_Desire_Broadway_Ballad` | 32 NEW run(s), 13 unsung line(s) |
| C | 78.8 | 22 | 0 | 14 | medium | `04_03_When_God_Becomes_Real_Soul_Worship` | 22 NEW run(s), 14 unsung line(s) |
| C | 81.5 | 2 | 1 | 5 | medium | `06_01_I_Have_Tasted_the_Light_Sacred_Americana` | 2 NEW run(s), 5 unsung line(s) |
| C | 83.3 | 14 | 0 | 11 | medium | `04_04_When_God_Becomes_Real_Contemplative_Worship` | 14 NEW run(s), 11 unsung line(s) |
| C | 83.7 | 3 | 2 | 7 | medium | `02_03_Our_Search_Celtic_Worship` | 3 NEW run(s), 7 unsung line(s) |
| C | 85.2 | 9 | 0 | 4 | medium | `06_04_I_Have_Tasted_the_Light_Soul_Worship` | 9 NEW run(s), 4 unsung line(s) |
| C | 86.9 | 31 | 0 | 8 | medium | `05_05_The_Souls_Sincere_Desire_Americana_Folk` | 31 NEW run(s), 8 unsung line(s) |
| C | 87.0 | 0 | 0 | 6 | medium | `16_01_One_Day_in_Seven_Acoustic_Worship` | 0 NEW run(s), 6 unsung line(s) |
| C | 90.3 | 1 | 0 | 3 | medium | `14_01_The_First_One_I_Turn_To_Contemporary_Christian` | 1 NEW run(s), 3 unsung line(s) |
| C | 96.3 | 2 | 0 | 1 | medium | `06_05_I_Have_Tasted_the_Light_Broadway_Ballad` | 2 NEW run(s), 1 unsung line(s) |
| C | 96.3 | 2 | 0 | 1 | medium | `06_06_I_Have_Tasted_the_Light_Americana_Folk` | 2 NEW run(s), 1 unsung line(s) |
| C | 96.3 | 8 | 0 | 1 | medium | `06_07_I_Have_Tasted_the_Light_Contemplative_Worship_Female_Vocal` | 8 NEW run(s), 1 unsung line(s) |
| C | 96.3 | 0 | 0 | 1 | medium | `06_08_I_Have_Tasted_the_Light_Classical_Duet_Female_Vocal` | 0 NEW run(s), 1 unsung line(s) |
| C | 96.3 | 14 | 0 | 1 | medium | `06_09_I_Have_Tasted_the_Light_Indie_Folk` | 14 NEW run(s), 1 unsung line(s) |
| C | 100.0 | 2 | 1 | 0 | medium | `01_03_Introduction_to_Plainness_Americana_Folk` | 2 NEW run(s), 0 unsung line(s) |
| C | 100.0 | 1 | 0 | 0 | medium | `03_01_Two_Halves_of_a_Whole_Celtic_Ballad` | 1 NEW run(s), 0 unsung line(s) |
| C | 100.0 | 1 | 0 | 0 | medium | `04_02_When_God_Becomes_Real_Americana_Folk_Academics_Remix` | 1 NEW run(s), 0 unsung line(s) |
| C | 100.0 | 3 | 0 | 0 | medium | `06_02_I_Have_Tasted_the_Light_Contemporary_Christian` | 3 NEW run(s), 0 unsung line(s) |
| C | 100.0 | 1 | 0 | 0 | medium | `06_03_I_Have_Tasted_the_Light_Classical_Duet` | 1 NEW run(s), 0 unsung line(s) |
| C | 100.0 | 1 | 1 | 0 | medium | `08_01_Prepared_in_All_Things_Desert_Troubadour` | 1 NEW run(s), 0 unsung line(s) |
| C | 100.0 | 1 | 0 | 0 | medium | `13_02_Understood_the_Assignment_Cinematic_Orchestral` | 1 NEW run(s), 0 unsung line(s) |
| A | 100.0 | 0 | 0 | 0 | medium | `AN_01_The_Marks_of_Your_Worth_Sacred_Americana` | sung words match the sheet |
| A | 100.0 | 0 | 0 | 0 | medium | `AN_01_One_Voice_One_Mind_Cinematic_Inspirational` | sung words match the sheet |
| A | 100.0 | 0 | 0 | 0 | small | `01_01_Introduction_to_Plainness_Sacred_Americana` | sung words match the sheet |
| A | 100.0 | 0 | 0 | 0 | medium | `02_01_Our_Search_Sacred_Americana` | sung words match the sheet |
| A | 100.0 | 0 | 0 | 0 | medium | `02_02_Our_Search_Cinematic_Inspirational` | sung words match the sheet |
| A | 100.0 | 0 | 0 | 0 | small | `03_02_Two_Halves_of_a_Whole_Americana_Folk` | sung words match the sheet |
| A | 100.0 | 0 | 0 | 0 | small | `03_03_Two_Halves_of_a_Whole_Classical_Crossover` | sung words match the sheet |
| A | 100.0 | 0 | 0 | 0 | small | `04_01_When_God_Becomes_Real_Sacred_Americana` | sung words match the sheet |
| A | 100.0 | 0 | 0 | 0 | medium | `05_01_The_Souls_Sincere_Desire_Soul_Worship` | sung words match the sheet |
| A | 100.0 | 0 | 0 | 0 | small | `07_01_Promises_Kept_Folk_Hymn` | sung words match the sheet |
| A | 100.0 | 0 | 0 | 0 | small | `09_01_Established_in_Him_Sacred_Americana` | sung words match the sheet |
| A | 100.0 | 0 | 0 | 0 | small | `10_01_He_Always_Knew_Me_Cinematic_Worship` | sung words match the sheet |
| A | 100.0 | 0 | 0 | 0 | small | `10_02_He_Always_Knew_Me_Contemporary_Christian` | sung words match the sheet |
| A | 100.0 | 0 | 0 | 0 | small | `10_03_He_Always_Knew_Me_Gospel_Soul` | sung words match the sheet |
| A | 100.0 | 0 | 0 | 0 | small | `11_01_Panteles_Sacred_Ballad` | sung words match the sheet |
| A | 100.0 | 0 | 0 | 0 | medium | `12_01_What_You_Were_Made_to_Be` | sung words match the sheet |
| A | 100.0 | 0 | 0 | 0 | small | `13_01_Understood_the_Assignment_Contemporary_Christian` | sung words match the sheet |
| A | 100.0 | 0 | 0 | 0 | small | `13_03_Understood_the_Assignment_Bluegrass_Fireside` | sung words match the sheet |
| A | 100.0 | 0 | 0 | 0 | small | `13_04_Understood_the_Assignment_Blues` | sung words match the sheet |
| A | 100.0 | 0 | 0 | 0 | small | `13_05_Understood_the_Assignment_Country` | sung words match the sheet |
| A | 100.0 | 0 | 0 | 0 | small | `13_06_Understood_the_Assignment_A_Cappella` | sung words match the sheet |
| A | 100.0 | 0 | 0 | 0 | medium | `14_02_The_First_One_I_Turn_To_A_Cappella` | sung words match the sheet |
| A | 100.0 | 0 | 0 | 0 | small | `14_03_The_First_One_I_Turn_To_Piano_Ballad` | sung words match the sheet |
| A | 100.0 | 0 | 0 | 0 | small | `14_04_The_First_One_I_Turn_To_Roots_Gospel` | sung words match the sheet |
| A | 100.0 | 0 | 0 | 0 | small | `14_05_The_First_One_I_Turn_To_Theatrical_Ballad` | sung words match the sheet |
| A | 100.0 | 0 | 0 | 0 | small | `15_01_Keep_Me_Turning_To_You_Piano_Ballad` | sung words match the sheet |
| A | 100.0 | 0 | 0 | 0 | small | `15_02_Keep_Me_Turning_To_You_A_Capella` | sung words match the sheet |
| A | 100.0 | 0 | 0 | 0 | small | `15_04_Keep_Me_Turning_To_You_Folk_Hymn_Duet` | sung words match the sheet |
