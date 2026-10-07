# Lyric validation - 2026-10-07

Standard: WoP Musical Testimony Lyric-Sync Standard, section 4 G4. Arrangements: 58 - ok 17, warn 31, fail 5, no-vtt 5.

`fail` (cue count or text) = the VTT is not attached; the arrangement shows static lyrics. `warn` = highlighted, but a timing check needs attention.

| status | cues | sheet lines | arrangement | problems |
|---|---:|---:|---|---|
| warn | 38 | 38 | `AN_01_The_Marks_of_Your_Worth_Sacred_Americana.mp3` | 1 gap(s) > 20s |
| warn | 74 | 74 | `AN_01_One_Voice_One_Mind_Cinematic_Inspirational.mp3` | 2 cue(s) < 1.0s (e.g. #50); 2 overlap(s) (e.g. cue #50 -> #51) |
| warn | 74 | 74 | `AN_02_One_Voice_One_Mind_Sacred_Americana.mp3` | 27 cue(s) < 1.0s (e.g. #5); 17 overlap(s) (e.g. cue #7 -> #8); 1 gap(s) > 20s |
| no-vtt | 0 | 0 | `SY_01_Words_of_Plainness_Mini_Symphony_Instrumental.mp3` |  |
| ok | 32 | 32 | `01_01_Introduction_to_Plainness_Sacred_Americana.mp3` |  |
| fail | 29 | 32 | `01_02_Introduction_to_Plainness_Cinematic_Inspirational.mp3` | cue count 29 != sheet lines 32; 3 cue(s) differ from the sheet text; 7 cue(s) < 1.0s (e.g. #2); 3 overlap(s) (e.g. cue #21 -> #22) |
| ok | 32 | 32 | `01_03_Introduction_to_Plainness_Americana_Folk.mp3` |  |
| fail | 39 | 43 | `02_01_Our_Search_Sacred_Americana.mp3` | cue count 39 != sheet lines 43; 4 cue(s) differ from the sheet text; 5 cue(s) < 1.0s (e.g. #35); 4 overlap(s) (e.g. cue #35 -> #36); 1 gap(s) > 20s |
| fail | 39 | 43 | `02_02_Our_Search_Cinematic_Inspirational.mp3` | cue count 39 != sheet lines 43; 4 cue(s) differ from the sheet text |
| fail | 39 | 43 | `02_03_Our_Search_Celtic_Worship.mp3` | cue count 39 != sheet lines 43; 4 cue(s) differ from the sheet text; 1 gap(s) > 20s |
| warn | 48 | 48 | `03_02_Two_Halves_of_a_Whole_Americana_Folk.mp3` | 1 gap(s) > 20s |
| fail | 44 | 48 | `03_01_Two_Halves_of_a_Whole_Celtic_Ballad.mp3` | cue count 44 != sheet lines 48; 4 cue(s) differ from the sheet text; 2 gap(s) > 20s |
| warn | 48 | 48 | `03_03_Two_Halves_of_a_Whole_Classical_Crossover.mp3` | 1 gap(s) > 20s |
| warn | 66 | 66 | `04_01_When_God_Becomes_Real_Sacred_Americana.mp3` | 1 cue(s) < 1.0s (e.g. #66) |
| warn | 66 | 66 | `04_02_When_God_Becomes_Real_Americana_Folk_Academics_Remix.mp3` | 4 cue(s) < 1.0s (e.g. #16) |
| warn | 66 | 66 | `04_03_When_God_Becomes_Real_Soul_Worship.mp3` | 23 cue(s) < 1.0s (e.g. #8); 12 overlap(s) (e.g. cue #26 -> #27); 1 gap(s) > 20s |
| warn | 66 | 66 | `04_04_When_God_Becomes_Real_Contemplative_Worship.mp3` | 11 cue(s) < 1.0s (e.g. #1); 6 overlap(s) (e.g. cue #60 -> #61); 1 gap(s) > 20s |
| warn | 61 | 61 | `05_01_The_Souls_Sincere_Desire_Soul_Worship.mp3` | 10 cue(s) < 1.0s (e.g. #31); 5 overlap(s) (e.g. cue #36 -> #37) |
| warn | 61 | 61 | `05_02_The_Souls_Sincere_Desire_Contemporary_Christian.mp3` | 30 cue(s) < 1.0s (e.g. #2); 25 overlap(s) (e.g. cue #5 -> #6); 1 gap(s) > 20s |
| warn | 61 | 61 | `05_03_The_Souls_Sincere_Desire_Cinematic_Inspirational.mp3` | 23 cue(s) < 1.0s (e.g. #2); 7 overlap(s) (e.g. cue #44 -> #45); 2 gap(s) > 20s |
| warn | 61 | 61 | `05_04_The_Souls_Sincere_Desire_Celtic_Worship.mp3` | 33 cue(s) < 1.0s (e.g. #2); 17 overlap(s) (e.g. cue #28 -> #29); 1 gap(s) > 20s |
| warn | 61 | 61 | `05_05_The_Souls_Sincere_Desire_Americana_Folk.mp3` | 12 cue(s) < 1.0s (e.g. #2); 6 overlap(s) (e.g. cue #19 -> #20); 1 gap(s) > 20s |
| warn | 61 | 61 | `05_06_The_Souls_Sincere_Desire_Broadway_Ballad.mp3` | 26 cue(s) < 1.0s (e.g. #9); 7 overlap(s) (e.g. cue #19 -> #20); 2 gap(s) > 20s |
| warn | 27 | 27 | `06_01_I_Have_Tasted_the_Light_Sacred_Americana.mp3` | 1 cue(s) < 1.0s (e.g. #20) |
| ok | 27 | 27 | `06_02_I_Have_Tasted_the_Light_Contemporary_Christian.mp3` |  |
| warn | 27 | 27 | `06_03_I_Have_Tasted_the_Light_Classical_Duet.mp3` | 6 cue(s) < 1.0s (e.g. #10); 4 overlap(s) (e.g. cue #10 -> #11); 1 gap(s) > 20s |
| ok | 27 | 27 | `06_04_I_Have_Tasted_the_Light_Soul_Worship.mp3` |  |
| warn | 27 | 27 | `06_05_I_Have_Tasted_the_Light_Broadway_Ballad.mp3` | 1 cue(s) < 1.0s (e.g. #26) |
| warn | 27 | 27 | `06_06_I_Have_Tasted_the_Light_Americana_Folk.mp3` | 2 cue(s) < 1.0s (e.g. #20); 1 overlap(s) (e.g. cue #20 -> #21) |
| warn | 27 | 27 | `06_07_I_Have_Tasted_the_Light_Contemplative_Worship_Female_Vocal.mp3` | 1 cue(s) < 1.0s (e.g. #25); 1 overlap(s) (e.g. cue #25 -> #26) |
| warn | 27 | 27 | `06_08_I_Have_Tasted_the_Light_Classical_Duet_Female_Vocal.mp3` | 1 cue(s) < 1.0s (e.g. #25); 1 overlap(s) (e.g. cue #25 -> #26) |
| ok | 27 | 27 | `06_09_I_Have_Tasted_the_Light_Indie_Folk.mp3` |  |
| ok | 69 | 69 | `07_01_Promises_Kept_Folk_Hymn.mp3` |  |
| warn | 69 | 69 | `07_02_Promises_Kept_Contemporary_Christian.mp3` | 41 cue(s) < 1.0s (e.g. #4); 37 overlap(s) (e.g. cue #5 -> #6); 2 gap(s) > 20s |
| ok | 38 | 38 | `08_01_Prepared_in_All_Things_Desert_Troubadour.mp3` |  |
| ok | 56 | 56 | `09_01_Established_in_Him_Sacred_Americana.mp3` |  |
| warn | 56 | 56 | `09_02_Established_in_Him_Contemporary_Christian.mp3` | 33 cue(s) < 1.0s (e.g. #2); 32 overlap(s) (e.g. cue #2 -> #3); 1 gap(s) > 20s |
| warn | 56 | 56 | `10_01_He_Always_Knew_Me_Cinematic_Worship.mp3` | 3 overlap(s) (e.g. cue #2 -> #3) |
| ok | 56 | 56 | `10_02_He_Always_Knew_Me_Contemporary_Christian.mp3` |  |
| ok | 56 | 56 | `10_03_He_Always_Knew_Me_Gospel_Soul.mp3` |  |
| warn | 37 | 37 | `11_01_Panteles_Sacred_Ballad.mp3` | 1 cue(s) < 1.0s (e.g. #37) |
| ok | 44 | 44 | `12_01_What_You_Were_Made_to_Be.mp3` |  |
| warn | 58 | 58 | `13_01_Understood_the_Assignment_Contemporary_Christian.mp3` | 1 cue(s) < 1.0s (e.g. #34) |
| warn | 58 | 58 | `13_02_Understood_the_Assignment_Cinematic_Orchestral.mp3` | 26 cue(s) < 1.0s (e.g. #33); 25 overlap(s) (e.g. cue #33 -> #34); 1 gap(s) > 20s |
| warn | 58 | 58 | `13_03_Understood_the_Assignment_Bluegrass_Fireside.mp3` | 2 cue(s) < 1.0s (e.g. #34) |
| warn | 58 | 58 | `13_04_Understood_the_Assignment_Blues.mp3` | 3 cue(s) < 1.0s (e.g. #34) |
| warn | 58 | 58 | `13_05_Understood_the_Assignment_Country.mp3` | 1 cue(s) < 1.0s (e.g. #34) |
| ok | 58 | 58 | `13_06_Understood_the_Assignment_A_Cappella.mp3` |  |
| ok | 31 | 31 | `14_01_The_First_One_I_Turn_To_Contemporary_Christian.mp3` |  |
| ok | 31 | 31 | `14_02_The_First_One_I_Turn_To_A_Cappella.mp3` |  |
| ok | 31 | 31 | `14_03_The_First_One_I_Turn_To_Piano_Ballad.mp3` |  |
| ok | 31 | 31 | `14_04_The_First_One_I_Turn_To_Roots_Gospel.mp3` |  |
| ok | 31 | 31 | `14_05_The_First_One_I_Turn_To_Theatrical_Ballad.mp3` |  |
| no-vtt | 0 | 64 | `15_01_Keep_Me_Turning_To_You_Piano_Ballad.mp3` |  |
| no-vtt | 0 | 64 | `15_02_Keep_Me_Turning_To_You_A_Capella.mp3` |  |
| no-vtt | 0 | 64 | `15_03_Keep_Me_Turning_To_You_Cinematic_Orchestra.mp3` |  |
| no-vtt | 0 | 64 | `15_04_Keep_Me_Turning_To_You_Folk_Hymn_Duet.mp3` |  |
| warn | 46 | 46 | `16_01_One_Day_in_Seven_Acoustic_Worship.mp3` | 5 cue(s) < 1.0s (e.g. #27); 5 overlap(s) (e.g. cue #27 -> #28) |

## Detail

### `AN_01_The_Marks_of_Your_Worth_Sacred_Americana.mp3`
- gap 26.36s after cue 24 (3:00.360 - 3:26.720)

### `AN_02_One_Voice_One_Mind_Sacred_Americana.mp3`
- gap 21.18s after cue 24 (3:27.860 - 3:49.040)

### `01_02_Introduction_to_Plainness_Cinematic_Inspirational.mp3`
- cue 18: VTT "(no cue)" / sheet "These are letters for the unborn, a heritage of grace,"
- cue 19: VTT "(no cue)" / sheet "For the ones who'll walk this wide and weary place."
- cue 20: VTT "(no cue)" / sheet "Because He first came looking, we will never walk alone—"

### `02_01_Our_Search_Sacred_Americana.mp3`
- cue 28: VTT "(no cue)" / sheet "Between the pride and the despair"
- cue 29: VTT "(no cue)" / sheet "Between the running and standing still"
- cue 30: VTT "(no cue)" / sheet "There's a narrow way for honest seekers"
- cue 31: VTT "(no cue)" / sheet "Where the deepest thirst is finally filled"
- gap 44.3s after cue 34 (3:14.320 - 3:58.620)

### `02_02_Our_Search_Cinematic_Inspirational.mp3`
- cue 28: VTT "(no cue)" / sheet "Between the pride and the despair"
- cue 29: VTT "(no cue)" / sheet "Between the running and standing still"
- cue 30: VTT "(no cue)" / sheet "There's a narrow way for honest seekers"
- cue 31: VTT "(no cue)" / sheet "Where the deepest thirst is finally filled"

### `02_03_Our_Search_Celtic_Worship.mp3`
- cue 28: VTT "(no cue)" / sheet "Between the pride and the despair"
- cue 29: VTT "(no cue)" / sheet "Between the running and standing still"
- cue 30: VTT "(no cue)" / sheet "There's a narrow way for honest seekers"
- cue 31: VTT "(no cue)" / sheet "Where the deepest thirst is finally filled"
- gap 29.9s after cue 20 (2:38.220 - 3:08.120)

### `03_02_Two_Halves_of_a_Whole_Americana_Folk.mp3`
- gap 36.04s after cue 36 (3:13.080 - 3:49.120)

### `03_01_Two_Halves_of_a_Whole_Celtic_Ballad.mp3`
- cue 25: VTT "(no cue)" / sheet "Now I'm standing at the ceiling of the framework,"
- cue 26: VTT "(no cue)" / sheet "Looking through the window at the rain."
- cue 27: VTT "(no cue)" / sheet "Reason is a shadow in the moonlight"
- cue 28: VTT "(no cue)" / sheet "If it cannot take away the pain."
- gap 28.96s after cue 24 (2:38.840 - 3:07.800)
- gap 30.06s after cue 32 (3:58.320 - 4:28.380)

### `03_03_Two_Halves_of_a_Whole_Classical_Crossover.mp3`
- gap 26.62s after cue 36 (3:54.960 - 4:21.580)

### `04_03_When_God_Becomes_Real_Soul_Worship.mp3`
- gap 27.98s after cue 12 (0:56.940 - 1:24.920)

### `04_04_When_God_Becomes_Real_Contemplative_Worship.mp3`
- gap 27.34s after cue 46 (6:00.140 - 6:27.480)

### `05_02_The_Souls_Sincere_Desire_Contemporary_Christian.mp3`
- gap 56.0s after cue 56 (3:26.840 - 4:22.840)

### `05_03_The_Souls_Sincere_Desire_Cinematic_Inspirational.mp3`
- gap 32.64s after cue 40 (3:48.120 - 4:20.760)
- gap 29.72s after cue 49 (4:36.960 - 5:06.680)

### `05_04_The_Souls_Sincere_Desire_Celtic_Worship.mp3`
- gap 28.02s after cue 59 (5:45.940 - 6:13.960)

### `05_05_The_Souls_Sincere_Desire_Americana_Folk.mp3`
- gap 21.84s after cue 40 (4:01.700 - 4:23.540)

### `05_06_The_Souls_Sincere_Desire_Broadway_Ballad.mp3`
- gap 32.5s after cue 40 (4:03.880 - 4:36.380)
- gap 46.34s after cue 50 (4:53.200 - 5:39.540)

### `06_03_I_Have_Tasted_the_Light_Classical_Duet.mp3`
- gap 24.72s after cue 6 (1:43.240 - 2:07.960)

### `07_02_Promises_Kept_Contemporary_Christian.mp3`
- gap 49.3s after cue 1 (0:15.300 - 1:04.600)
- gap 37.96s after cue 24 (3:06.360 - 3:44.320)

### `09_02_Established_in_Him_Contemporary_Christian.mp3`
- gap 73.5s after cue 55 (3:28.660 - 4:42.160)

### `13_02_Understood_the_Assignment_Cinematic_Orchestral.mp3`
- gap 63.7s after cue 14 (1:23.960 - 2:27.660)

