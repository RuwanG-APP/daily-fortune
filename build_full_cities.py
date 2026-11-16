"""
Script to build comprehensive Sri Lanka 25-District and 331-Divisional Secretariat (DS) Cities database.
Preserves existing IDs 1..168 for full backward compatibility, while ensuring EVERY official DS division
(including Attanagalla/Wathupitiwala, Biyagama, Katana, Mahara, etc.) is represented with accurate coordinates.
"""

from pathlib import Path
import json

# Official 331 Divisional Secretariat Divisions across 25 Districts of Sri Lanka
# (name_en, name_si, district_id, lat_deg, lat_min, lon_deg, lon_min)
ALL_331_DS_DIVISIONS = [
    # Colombo (13)
    ("Colombo", "කොළඹ", "Colombo", 6, 56, 79, 51),
    ("Dehiwala", "දෙහිවල", "Colombo", 6, 51, 79, 52),
    ("Homagama", "හෝමාගම", "Colombo", 6, 50, 80, 0),
    ("Kaduwela", "කඩුවෙල", "Colombo", 6, 56, 79, 59),
    ("Kesbewa / Piliyandala", "කැස්බෑව / පිළියන්දල", "Colombo", 6, 48, 79, 55),
    ("Kolonnawa", "කොළොන්නාව", "Colombo", 6, 56, 79, 54),
    ("Maharagama", "මහරගම", "Colombo", 6, 50, 79, 56),
    ("Moratuwa", "මොරටුව", "Colombo", 6, 46, 79, 53),
    ("Padukka", "පාදුක්ක", "Colombo", 6, 50, 80, 5),
    ("Ratmalana", "රත්මලාන", "Colombo", 6, 49, 79, 53),
    ("Seethawaka / Hanwella", "සීතාවක / හංවැල්ල", "Colombo", 6, 54, 80, 5),
    ("Sri Jayawardenepura Kotte", "ශ්‍රී ජයවර්ධනපුර කෝට්ටේ", "Colombo", 6, 54, 79, 55),
    ("Thimbirigasyaya", "තිඹිරිගස්යාය", "Colombo", 6, 53, 79, 52),

    # Gampaha (13)
    ("Attanagalla / Wathupitiwala", "අත්තනගල්ල / වතුපිටිවල", "Gampaha", 7, 7, 80, 8),
    ("Biyagama", "බියගම", "Gampaha", 6, 56, 79, 59),
    ("Divulapitiya", "දිවුලපිටිය", "Gampaha", 7, 13, 80, 1),
    ("Dompe", "දොම්පේ", "Gampaha", 6, 57, 80, 4),
    ("Gampaha", "ගම්පහ", "Gampaha", 7, 5, 79, 59),
    ("Ja-Ela", "ජා-ඇල", "Gampaha", 7, 4, 79, 53),
    ("Katana", "කටාන", "Gampaha", 7, 12, 79, 52),
    ("Kelaniya", "කැලණිය", "Gampaha", 6, 57, 79, 55),
    ("Mahara / Kadawatha", "මහර / කඩවත", "Gampaha", 7, 1, 79, 57),
    ("Minuwangoda", "මිනුවන්ගොඩ", "Gampaha", 7, 10, 79, 57),
    ("Mirigama", "මීරිගම", "Gampaha", 7, 15, 80, 8),
    ("Negombo", "මීගමුව", "Gampaha", 7, 12, 79, 50),
    ("Wattala", "වත්තල", "Gampaha", 6, 59, 79, 53),

    # Kalutara (14)
    ("Agalawatta", "අගලවත්ත", "Kalutara", 6, 32, 80, 9),
    ("Bandaragama", "බණ්ඩාරගම", "Kalutara", 6, 43, 79, 59),
    ("Beruwala", "බේරුවල", "Kalutara", 6, 28, 79, 59),
    ("Bulathsinhala", "බුලත්සිංහල", "Kalutara", 6, 39, 80, 10),
    ("Dodangoda", "දොඩංගොඩ", "Kalutara", 6, 35, 80, 2),
    ("Horana", "හොරණ", "Kalutara", 6, 43, 80, 4),
    ("Ingiriya", "ඉංගිරිය", "Kalutara", 6, 44, 80, 10),
    ("Kalutara", "කළුතර", "Kalutara", 6, 31, 79, 58),
    ("Madurawala", "මදුරාවල", "Kalutara", 6, 40, 80, 4),
    ("Mathugama", "මතුගම", "Kalutara", 6, 31, 80, 7),
    ("Millaniya", "මිල්ලනිය", "Kalutara", 6, 40, 80, 0),
    ("Palindanuwara", "පාලින්දනුවර", "Kalutara", 6, 28, 80, 12),
    ("Panadura", "පානදුර", "Kalutara", 6, 43, 79, 54),
    ("Walallavita", "වළල්ලාවිට", "Kalutara", 6, 26, 80, 11),

    # Kandy (20)
    ("Akurana", "අකුරණ", "Kandy", 7, 22, 80, 37),
    ("Delthota", "දෙල්තොට", "Kandy", 7, 11, 80, 42),
    ("Doluwa", "දොළුව", "Kandy", 7, 10, 80, 36),
    ("Ganga Ihala Korale", "ගඟ ඉහළ කෝරළේ", "Kandy", 7, 4, 80, 34),
    ("Harispattuwa / Katugastota", "හාරිස්පත්තුව / කටුගස්තොට", "Kandy", 7, 20, 80, 37),
    ("Hatharaliyadda", "හතරලියැද්ද", "Kandy", 7, 20, 80, 29),
    ("Kandy Four Gravets", "මහනුවර කඩවත් සතර", "Kandy", 7, 17, 80, 38),
    ("Kundasale", "කුණ්ඩසාලේ", "Kandy", 7, 17, 80, 41),
    ("Medadumbara / Teldeniya", "මැදදුම්බර / තෙල්දෙණිය", "Kandy", 7, 18, 80, 46),
    ("Minipe", "මිණිපේ", "Kandy", 7, 12, 80, 59),
    ("Panvila", "පන්විල", "Kandy", 7, 23, 80, 44),
    ("Pasbage Korale / Nawalapitiya", "පස්බාගේ කෝරළේ / නාවලපිටිය", "Kandy", 7, 3, 80, 32),
    ("Pathadumbara / Wattegama", "පාතදුම්බර / වත්තේගම", "Kandy", 7, 21, 80, 41),
    ("Pathahewaheta", "පාතහේවාහැට", "Kandy", 7, 14, 80, 42),
    ("Poojapitiya", "පූජාපිටිය", "Kandy", 7, 22, 80, 34),
    ("Thumpane", "තුම්පනේ", "Kandy", 7, 22, 80, 31),
    ("Udadumbara", "උඩදුම්බර", "Kandy", 7, 19, 80, 52),
    ("Udapalatha / Gampola", "උඩපළාත / ගම්පොළ", "Kandy", 7, 10, 80, 34),
    ("Udunuwara", "උඩුනුවර", "Kandy", 7, 13, 80, 34),
    ("Yatinuwara / Kadugannawa", "යටිනුවර / කඩුගන්නාව", "Kandy", 7, 15, 80, 31),

    # Matale (11)
    ("Ambanganga Korale", "අඹන්ගඟ කෝරළේ", "Matale", 7, 30, 80, 45),
    ("Dambulla", "දඹුල්ල", "Matale", 7, 52, 80, 39),
    ("Galewela", "ගලේවෙල", "Matale", 7, 46, 80, 34),
    ("Laggala-Pallegama", "ලග්ගල පල්ලේගම", "Matale", 7, 33, 80, 47),
    ("Matale", "මාතලේ", "Matale", 7, 28, 80, 37),
    ("Naula", "නාඋල", "Matale", 7, 42, 80, 39),
    ("Pallepola", "පල්ලේපොල", "Matale", 7, 35, 80, 34),
    ("Rattota", "රත්තොට", "Matale", 7, 31, 80, 40),
    ("Ukuwela", "උකුවෙල", "Matale", 7, 25, 80, 38),
    ("Vilgamuwa", "විල්ගමුව", "Matale", 7, 36, 80, 56),
    ("Yatawatta", "යටවත්ත", "Matale", 7, 32, 80, 34),

    # Nuwara Eliya (5)
    ("Ambagamuwa / Ginigathena", "අඹගමුව / ගිනිගත්හේන", "Nuwara Eliya", 6, 59, 80, 29),
    ("Hanguranketha", "හඟුරන්කෙත", "Nuwara Eliya", 7, 10, 80, 46),
    ("Kotmale", "කොත්මලේ", "Nuwara Eliya", 7, 4, 80, 37),
    ("Nuwara Eliya", "නුවරඑළිය", "Nuwara Eliya", 6, 58, 80, 46),
    ("Walapane", "වලපනේ", "Nuwara Eliya", 7, 5, 80, 52),

    # Galle (19)
    ("Akmeemana", "අක්මීමන", "Galle", 6, 4, 80, 16),
    ("Ambalangoda", "අම්බලන්ගොඩ", "Galle", 6, 14, 80, 3),
    ("Baddegama", "බද්දේගම", "Galle", 6, 11, 80, 14),
    ("Balapitiya", "බලපිටිය", "Galle", 6, 16, 80, 2),
    ("Bentota", "බෙන්තොට", "Galle", 6, 25, 80, 0),
    ("Bope-Poddala", "බෝපෙ පෝද්දල", "Galle", 6, 5, 80, 12),
    ("Elpitiya", "ඇල්පිටිය", "Galle", 6, 17, 80, 10),
    ("Galle Four Gravets", "ගාල්ල කඩවත් සතර", "Galle", 6, 2, 80, 13),
    ("Gonapinuwala", "ගෝනපීනුවල", "Galle", 6, 10, 80, 9),
    ("Habaraduwa / Koggala", "හබරාදුව / කොග්ගල", "Galle", 5, 59, 80, 20),
    ("Hikkaduwa", "හික්කඩුව", "Galle", 6, 8, 80, 6),
    ("Imaduwa", "ඉමදුව", "Galle", 6, 4, 80, 22),
    ("Karandeniya", "කරන්දෙනිය", "Galle", 6, 16, 80, 7),
    ("Nagoda", "නාගොඩ", "Galle", 6, 12, 80, 18),
    ("Neluwa", "නෙළුව", "Galle", 6, 21, 80, 24),
    ("Niyagama", "නියගම", "Galle", 6, 18, 80, 14),
    ("Thawalama", "තවලම", "Galle", 6, 20, 80, 20),
    ("Welivitiya-Divithura", "වැලිවිටිය දිවිතුර", "Galle", 6, 13, 80, 11),
    ("Yakkalamulla", "යක්කලමුල්ල", "Galle", 6, 7, 80, 21),

    # Matara (16)
    ("Akuressa", "අකුරැස්ස", "Matara", 6, 6, 80, 29),
    ("Athuraliya", "අතුරලිය", "Matara", 6, 8, 80, 29),
    ("Devinuwara", "දෙවිනුවර", "Matara", 5, 55, 80, 35),
    ("Dickwella", "දික්වැල්ල", "Matara", 5, 58, 80, 42),
    ("Hakmana", "හක්මන", "Matara", 6, 5, 80, 39),
    ("Kamburupitiya", "කඹුරුපිටිය", "Matara", 6, 5, 80, 34),
    ("Kirinda Puhulwella", "කිරින්ද පුහුල්වැල්ල", "Matara", 6, 3, 80, 35),
    ("Kotapola", "කොටපොල", "Matara", 6, 16, 80, 34),
    ("Malimbada", "මාලිම්බඩ", "Matara", 6, 2, 80, 32),
    ("Matara Four Gravets", "මාතර කඩවත් සතර", "Matara", 5, 57, 80, 33),
    ("Mulatiyana", "මුලටියන", "Matara", 6, 10, 80, 35),
    ("Pasgoda", "පස්ගොඩ", "Matara", 6, 14, 80, 37),
    ("Pitabeddara", "පිටබැද්දර", "Matara", 6, 12, 80, 28),
    ("Thihagoda", "තිහගොඩ", "Matara", 6, 0, 80, 34),
    ("Weligama", "වැලිගම", "Matara", 5, 58, 80, 26),
    ("Welipitiya", "වැලිපිටිය", "Matara", 6, 1, 80, 28),

    # Hambantota (12)
    ("Ambalantota", "අම්බලන්තොට", "Hambantota", 6, 7, 81, 2),
    ("Angunakolapelessa", "අඟුණකොළපැලැස්ස", "Hambantota", 6, 10, 80, 54),
    ("Beliatta", "බෙලිඅත්ත", "Hambantota", 6, 2, 80, 44),
    ("Hambantota", "හම්බන්තොට", "Hambantota", 6, 7, 81, 7),
    ("Katuwana", "කටුවන", "Hambantota", 6, 14, 80, 41),
    ("Lunugamvehera", "ලුණුගම්වෙහෙර", "Hambantota", 6, 21, 81, 12),
    ("Okewela", "ඔකේවෙල", "Hambantota", 6, 5, 80, 47),
    ("Sooriyawewa", "සූරියවැව", "Hambantota", 6, 19, 81, 0),
    ("Tangalle", "තංගල්ල", "Hambantota", 6, 1, 80, 47),
    ("Tissamaharama", "තිස්සමහාරාමය", "Hambantota", 6, 17, 81, 17),
    ("Walasmulla", "වලස්මුල්ල", "Hambantota", 6, 9, 80, 42),
    ("Weeraketiya", "වීරකැටිය", "Hambantota", 6, 8, 80, 47),

    # Jaffna (15)
    ("Delft", "ඩෙල්ෆ්ට්", "Jaffna", 9, 31, 79, 41),
    ("Island North / Kayts", "කයිට්ස්", "Jaffna", 9, 41, 79, 54),
    ("Island South / Velanai", "වෙලනයි", "Jaffna", 9, 39, 79, 54),
    ("Jaffna", "යාපනය", "Jaffna", 9, 40, 80, 1),
    ("Karainagar", "කරෙයිනගර්", "Jaffna", 9, 44, 79, 52),
    ("Nallur", "නල්ලූර්", "Jaffna", 9, 40, 80, 2),
    ("Thenmaradchi / Chavakachcheri", "චාවකච්චේරි", "Jaffna", 9, 39, 80, 9),
    ("Vadamaradchi East", "මරුදන්කර්ණි", "Jaffna", 9, 38, 80, 22),
    ("Vadamaradchi North / Point Pedro", "පේදුරු තුඩුව", "Jaffna", 9, 49, 80, 14),
    ("Vadamaradchi South-West / Karaveddy", "කරවෙඩ්ඩි", "Jaffna", 9, 46, 80, 11),
    ("Valikamam East / Kopay", "කෝපායි", "Jaffna", 9, 42, 80, 4),
    ("Valikamam North / Tellippalai", "තෙල්ලිප්පලෙයි", "Jaffna", 9, 46, 80, 2),
    ("Valikamam South / Uduvil", "උඩුවිල්", "Jaffna", 9, 44, 80, 1),
    ("Valikamam South-West / Sandilipay", "සන්දිලිපායි", "Jaffna", 9, 44, 79, 58),
    ("Valikamam West / Chankanai", "චන්කානයි", "Jaffna", 9, 45, 79, 58),

    # Kilinochchi (4)
    ("Kandavalai", "කණ්ඩාවලෙයි", "Kilinochchi", 9, 25, 80, 31),
    ("Karachchi / Kilinochchi", "කිලිනොච්චිය", "Kilinochchi", 9, 23, 80, 24),
    ("Pachchilaipalli / Pallai", "පල්ලෙයි", "Kilinochchi", 9, 35, 80, 20),
    ("Poonakary", "පූනරීන්", "Kilinochchi", 9, 30, 80, 12),

    # Mannar (5)
    ("Madhu", "මඩු", "Mannar", 8, 51, 80, 12),
    ("Mannar Town", "මන්නාරම", "Mannar", 8, 59, 79, 54),
    ("Manthai West", "බටහිර මාන්තෙයි", "Mannar", 8, 58, 80, 1),
    ("Musali", "මුසලි", "Mannar", 8, 42, 79, 56),
    ("Nanaddan", "නානාට්ටාන්", "Mannar", 8, 51, 79, 59),

    # Vavuniya (4)
    ("Vavuniya", "වව්නියාව", "Vavuniya", 8, 45, 80, 30),
    ("Vavuniya North", "උතුරු වව්නියාව", "Vavuniya", 8, 56, 80, 35),
    ("Vavuniya South", "දකුණු වව්නියාව", "Vavuniya", 8, 40, 80, 28),
    ("Vengalacheddikulam", "වෙංගලචෙඩ්ඩිකුලම", "Vavuniya", 8, 40, 80, 18),

    # Mullaitivu (6)
    ("Manthai East", "නැගෙනහිර මාන්තෙයි", "Mullaitivu", 9, 5, 80, 23),
    ("Maritimepattu / Mullaitivu", "මුලතිව්", "Mullaitivu", 9, 16, 80, 49),
    ("Oddusuddan", "ඔඩ්ඩුසුඩාන්", "Mullaitivu", 9, 9, 80, 39),
    ("Puthukkudiyiruppu", "පුදුකුඩුඉරිප්පු", "Mullaitivu", 9, 18, 80, 42),
    ("Thunukkai", "තුනුක්කායි", "Mullaitivu", 9, 9, 80, 17),
    ("Welioya", "වැලිඔය", "Mullaitivu", 8, 53, 80, 52),

    # Batticaloa (14)
    ("Eravur Pattu", "එරාවුර් පත්තුව", "Batticaloa", 7, 46, 81, 34),
    ("Eravur Town", "එරාවුර් නගරය", "Batticaloa", 7, 46, 81, 36),
    ("Kattankudy", "කාත්තන්කුඩි", "Batticaloa", 7, 41, 81, 44),
    ("Koralai Pattu / Valachchenai", "වාලච්චේන", "Batticaloa", 7, 55, 81, 32),
    ("Koralai Pattu Central", "කෝරළේ පත්තු මධ්‍යම", "Batticaloa", 7, 54, 81, 32),
    ("Koralai Pattu North / Vakarai", "වාකරේ", "Batticaloa", 8, 8, 81, 26),
    ("Koralai Pattu South / Kiran", "කිරාන්", "Batticaloa", 7, 51, 81, 33),
    ("Koralai Pattu West / Oddamavadi", "ඔට්ටමාවඩි", "Batticaloa", 7, 55, 81, 31),
    ("Manmunai North / Batticaloa", "මඩකලපුව", "Batticaloa", 7, 43, 81, 42),
    ("Manmunai Pattu / Arayampathy", "ආරයම්පති", "Batticaloa", 7, 39, 81, 44),
    ("Manmunai South & Eruvilpattu", "කළුfilterචිකුඩි", "Batticaloa", 7, 31, 81, 47),
    ("Manmunai South West", "කොක්කඩිචෝලෙයි", "Batticaloa", 7, 38, 81, 41),
    ("Manmunai West", "වවුනතිව්", "Batticaloa", 7, 42, 81, 38),
    ("Porativu Pattu / Vellavely", "වෙල්ලාවෙලි", "Batticaloa", 7, 27, 81, 45),

    # Ampara (20)
    ("Addalaichenai", "අද්දාලච්චේන", "Ampara", 7, 14, 81, 51),
    ("Akkaraipattu", "අක්කරපත්තුව", "Ampara", 7, 13, 81, 51),
    ("Alayadivembu", "ආලයඩිවෙම්බු", "Ampara", 7, 12, 81, 50),
    ("Ampara", "අම්පාර", "Ampara", 7, 17, 81, 40),
    ("Damana", "දමන", "Ampara", 7, 11, 81, 39),
    ("Dehiattakandiya", "දෙහිඅත්තකණ්ඩිය", "Ampara", 7, 41, 81, 3),
    ("Eragama", "ඉරක්කාමම්", "Ampara", 7, 10, 81, 46),
    ("Kalmunai", "කල්මුණේ", "Ampara", 7, 25, 81, 49),
    ("Kalmunai South", "දකුණු කල්මුණේ", "Ampara", 7, 24, 81, 49),
    ("Karaitivu", "කාරෙයිතිව්", "Ampara", 7, 21, 81, 50),
    ("Lahugala", "ලාහුගල", "Ampara", 6, 52, 81, 43),
    ("Mahaoya", "මහාඔය", "Ampara", 7, 32, 81, 21),
    ("Navithanveli", "නවිතන්වේලි", "Ampara", 7, 21, 81, 45),
    ("Ninnavur", "නින්දවුර්", "Ampara", 7, 18, 81, 50),
    ("Padiyathalawa", "පදියතලාව", "Ampara", 7, 23, 81, 12),
    ("Pothuvil", "පොතුවිල්", "Ampara", 6, 52, 81, 50),
    ("Sainthamaruthu", "සයින්දමරුදු", "Ampara", 7, 23, 81, 50),
    ("Samanthurai", "සමන්තුරේ", "Ampara", 7, 22, 81, 48),
    ("Thirukkovil", "තිරුක්කෝවිල්", "Ampara", 7, 7, 81, 51),
    ("Uhana", "උහන", "Ampara", 7, 22, 81, 38),

    # Trincomalee (11)
    ("Gomarankadawala", "ගෝමරන්කඩවල", "Trincomalee", 8, 39, 81, 1),
    ("Kantale", "කන්තලේ", "Trincomalee", 8, 22, 80, 59),
    ("Kinniya", "කින්නියා", "Trincomalee", 8, 29, 81, 11),
    ("Kuchchaveli", "කුච්චවේලි", "Trincomalee", 8, 49, 81, 5),
    ("Morawewa", "මොරවැව", "Trincomalee", 8, 42, 81, 2),
    ("Muttur", "මුතූර්", "Trincomalee", 8, 27, 81, 16),
    ("Padavi Siripura", "පදවි ශ්‍රීපුර", "Trincomalee", 8, 52, 80, 52),
    ("Seruvila", "සේරුවිල", "Trincomalee", 8, 21, 81, 18),
    ("Thambalagamuwa", "තඹලගමුව", "Trincomalee", 8, 31, 81, 5),
    ("Trincomalee Town", "ත්‍රිකුණාමලය", "Trincomalee", 8, 34, 81, 14),
    ("Verugal", "වෙරුගල්", "Trincomalee", 8, 15, 81, 22),

    # Kurunegala (30)
    ("Alawwa", "අලව්ව", "Kurunegala", 7, 18, 80, 14),
    ("Ambanpola", "අඹන්පොළ", "Kurunegala", 7, 59, 80, 14),
    ("Bamunakotuwa", "බමුණුකොටුව", "Kurunegala", 7, 38, 80, 19),
    ("Bingiriya", "බිංගිරිය", "Kurunegala", 7, 34, 79, 57),
    ("Ehetuwewa", "ඇහැටුවැව", "Kurunegala", 7, 58, 80, 11),
    ("Galgamuwa", "ගල්ගමුව", "Kurunegala", 7, 59, 80, 16),
    ("Ganewatta", "ගනේවත්ත", "Kurunegala", 7, 39, 80, 25),
    ("Giribawa", "ගිරිබාව", "Kurunegala", 8, 6, 80, 12),
    ("Ibbagamuwa", "ඉබ්බාගමුව", "Kurunegala", 7, 33, 80, 27),
    ("Katupotha", "කටුපොත", "Kurunegala", 7, 33, 80, 13),
    ("Kobeigane", "කොබෙයිගනේ", "Kurunegala", 7, 42, 80, 10),
    ("Kotavehera", "කොටවෙහෙර", "Kurunegala", 7, 47, 80, 8),
    ("Kuliyapitiya East", "නැගෙනහිර කුලියාපිටිය", "Kurunegala", 7, 28, 80, 6),
    ("Kuliyapitiya West", "බටහිර කුලියාපිටිය", "Kurunegala", 7, 28, 80, 2),
    ("Kurunegala", "කුරුණෑගල", "Kurunegala", 7, 29, 80, 22),
    ("Maho", "මහෝ", "Kurunegala", 7, 49, 80, 16),
    ("Mallawapitiya", "මල්ලවපිටිය", "Kurunegala", 7, 30, 80, 24),
    ("Maspotha", "මස්පොත", "Kurunegala", 7, 32, 80, 18),
    ("Mawathagama", "මාවතගම", "Kurunegala", 7, 26, 80, 26),
    ("Narammala", "නාරම්මල", "Kurunegala", 7, 26, 80, 13),
    ("Nikaweratiya", "නිකවැරටිය", "Kurunegala", 7, 45, 80, 7),
    ("Panduwasnuwara East", "නැගෙනහිර පණ්ඩුවස්නුවර", "Kurunegala", 7, 36, 80, 8),
    ("Panduwasnuwara West", "බටහිර පණ්ඩුවස්නුවර", "Kurunegala", 7, 36, 80, 4),
    ("Pannala", "පන්නල", "Kurunegala", 7, 20, 80, 2),
    ("Polgahawela", "පොල්ගහවෙල", "Kurunegala", 7, 20, 80, 18),
    ("Polpithigama", "පොල්පිතිගම", "Kurunegala", 7, 46, 80, 27),
    ("Rasnayakapura", "රස්නායකපුර", "Kurunegala", 7, 46, 80, 2),
    ("Rideegama", "රිදීගම", "Kurunegala", 7, 32, 80, 31),
    ("Udubaddawa", "උඩුබද්දාව", "Kurunegala", 7, 26, 79, 59),
    ("Wariyapola", "වාරියපොළ", "Kurunegala", 7, 38, 80, 14),
    ("Weerambugedara", "වීරඹුගෙදර", "Kurunegala", 7, 31, 80, 17),

    # Puttalam (16)
    ("Anamaduwa", "ආණමඩුව", "Puttalam", 7, 53, 80, 0),
    ("Arachchikattuwa", "ආරච්චිකට්ටුව", "Puttalam", 7, 38, 79, 50),
    ("Chilaw", "හලාවත", "Puttalam", 7, 34, 79, 48),
    ("Dankotuwa", "දංකොටුව", "Puttalam", 7, 18, 79, 53),
    ("Kalpitiya", "කල්පිටිය", "Puttalam", 8, 14, 79, 46),
    ("Karuwalagaswewa", "කරුවලගස්වැව", "Puttalam", 8, 3, 80, 4),
    ("Madampe", "මාදම්පෙ", "Puttalam", 7, 30, 79, 50),
    ("Mahakumbukkadawala", "මහකුඹුක්කඩවල", "Puttalam", 7, 56, 79, 55),
    ("Mahawewa", "මහවැව", "Puttalam", 7, 26, 79, 51),
    ("Mundalama", "මුන්දලම", "Puttalam", 7, 47, 79, 49),
    ("Nattandiya", "නාත්තන්ඩිය", "Puttalam", 7, 25, 79, 52),
    ("Nawagattegama", "නවගත්තේගම", "Puttalam", 7, 59, 80, 7),
    ("Pallama", "පල්ලම", "Puttalam", 7, 41, 79, 55),
    ("Puttalam", "පුත්තලම", "Puttalam", 7, 59, 79, 49),
    ("Vanathavilluwa", "වනතාවිල්ලුව", "Puttalam", 8, 10, 79, 51),
    ("Wennappuwa", "වෙන්නප්පුව", "Puttalam", 7, 20, 79, 51),

    # Anuradhapura (22)
    ("Galnewa", "ගල්නෑව", "Anuradhapura", 8, 1, 80, 25),
    ("Galenbindunuwewa", "ගලෙන්බිඳුනුවැව", "Anuradhapura", 8, 18, 80, 43),
    ("Horowpothana", "හොරොව්පොතාන", "Anuradhapura", 8, 34, 80, 51),
    ("Ipalogama", "ඉපලෝගම", "Anuradhapura", 8, 7, 80, 31),
    ("Kahatagasdigiliya", "කහටගස්දිගිලිය", "Anuradhapura", 8, 25, 80, 42),
    ("Kebithigollewa", "කැබිතිගොල්ලෑව", "Anuradhapura", 8, 39, 80, 40),
    ("Kekirawa", "කැකිරාව", "Anuradhapura", 8, 2, 80, 35),
    ("Mahavilachchiya", "මහවිලච්චිය", "Anuradhapura", 8, 22, 80, 10),
    ("Medawachchiya", "මැදවච්චිය", "Anuradhapura", 8, 32, 80, 29),
    ("Mihintale", "මිහින්තලේ", "Anuradhapura", 8, 21, 80, 30),
    ("Nachchaduwa", "නාච්චදූව", "Anuradhapura", 8, 15, 80, 29),
    ("Nochchiyagama", "නොච්චියාගම", "Anuradhapura", 8, 17, 80, 12),
    ("Nuwaragam Palatha Central", "නුවරගම් පළාත මධ්‍යම", "Anuradhapura", 8, 21, 80, 25),
    ("Nuwaragam Palatha East / Anuradhapura", "අනුරාධපුර", "Anuradhapura", 8, 20, 80, 24),
    ("Padaviya", "පදවිය", "Anuradhapura", 8, 52, 80, 45),
    ("Palagala", "පලාගල", "Anuradhapura", 8, 0, 80, 36),
    ("Palugaswewa", "පලුගස්වැව", "Anuradhapura", 8, 5, 80, 42),
    ("Rajanganaya", "රාජංගනය", "Anuradhapura", 8, 10, 80, 12),
    ("Rambewa", "රඹෑව", "Anuradhapura", 8, 27, 80, 31),
    ("Thalawa", "තලාව", "Anuradhapura", 8, 11, 80, 22),
    ("Thambuttegama", "තඹුත්තේගම", "Anuradhapura", 8, 8, 80, 18),
    ("Thirappane", "තිරප්පනේ", "Anuradhapura", 8, 12, 80, 33),

    # Polonnaruwa (7)
    ("Dimbulagala", "දිඹුලාගල", "Polonnaruwa", 7, 52, 81, 9),
    ("Elahera", "ඇලහැර", "Polonnaruwa", 7, 44, 80, 49),
    ("Hingurakgoda", "හිඟුරක්ගොඩ", "Polonnaruwa", 8, 2, 80, 57),
    ("Lankapura", "ලංකාපුර", "Polonnaruwa", 8, 0, 81, 8),
    ("Medirigiriya", "මැදිරිගිරිය", "Polonnaruwa", 8, 8, 80, 58),
    ("Thamankaduwa / Polonnaruwa", "පොළොන්නරුව", "Polonnaruwa", 7, 56, 81, 0),
    ("Welikanda", "වැලිoutputකන්ද", "Polonnaruwa", 7, 59, 81, 14),

    # Badulla (15)
    ("Badulla", "බදුල්ල", "Badulla", 6, 59, 81, 3),
    ("Bandarawela", "බණ්ඩාරවෙල", "Badulla", 6, 50, 80, 59),
    ("Ella", "ඇල්ල", "Badulla", 6, 52, 81, 3),
    ("Haldummulla", "හල්දුම්මුල්ල", "Badulla", 6, 46, 80, 53),
    ("Hali-Ela", "හාලිඇල", "Badulla", 6, 57, 81, 2),
    ("Haputale", "හපුතලේ", "Badulla", 6, 46, 80, 57),
    ("Kandaketiya", "කන්දෙකැටිය", "Badulla", 7, 6, 81, 2),
    ("Lunugala", "ලුණුගල", "Badulla", 7, 2, 81, 12),
    ("Mahiyanganaya", "මහියංගණය", "Badulla", 7, 19, 81, 0),
    ("Meegahakivula", "මීගහකිවුල", "Badulla", 7, 8, 81, 7),
    ("Passara", "පස්සර", "Badulla", 6, 56, 81, 9),
    ("Rideemaliyadda", "රිදීමාලියැද්ද", "Badulla", 7, 14, 81, 10),
    ("Soranathota", "සොරණාතොට", "Badulla", 7, 3, 81, 4),
    ("Uva-Paranagama", "ඌව පරණගම", "Badulla", 6, 58, 80, 54),
    ("Welimada", "වැලිමඩ", "Badulla", 6, 54, 80, 55),

    # Monaragala (11)
    ("Badalkumbura", "බඩල්කුඹුර", "Monaragala", 6, 51, 81, 13),
    ("Bibile", "බිබිල", "Monaragala", 7, 10, 81, 13),
    ("Buttala", "බුත්තල", "Monaragala", 6, 45, 81, 14),
    ("Katharagama", "කතරගම", "Monaragala", 6, 25, 81, 20),
    ("Madulla", "මඩුල්ල", "Monaragala", 7, 5, 81, 20),
    ("Medagama", "මැදගම", "Monaragala", 7, 3, 81, 18),
    ("Monaragala", "මොණරාගල", "Monaragala", 6, 52, 81, 21),
    ("Sevanagala", "සෙවණගල", "Monaragala", 6, 23, 80, 55),
    ("Siyambalanduwa", "සියඹලාණ්ඩුව", "Monaragala", 6, 54, 81, 33),
    ("Thanamalwila", "තණමල්විල", "Monaragala", 6, 28, 81, 8),
    ("Wellawaya", "වැල්ලවාය", "Monaragala", 6, 44, 81, 6),

    # Ratnapura (17)
    ("Ayagama", "අයගම", "Ratnapura", 6, 37, 80, 19),
    ("Balangoda", "බලංගොඩ", "Ratnapura", 6, 39, 80, 42),
    ("Eheliyagoda", "ඇහැලියගොඩ", "Ratnapura", 6, 51, 80, 16),
    ("Elapattha", "ඇලපාත", "Ratnapura", 6, 38, 80, 23),
    ("Embilipitiya", "ඇඹිලිපිටිය", "Ratnapura", 6, 20, 80, 51),
    ("Godakawela", "ගොඩකවෙල", "Ratnapura", 6, 31, 80, 37),
    ("Imbulpe", "ඉඹුල්පේ", "Ratnapura", 6, 42, 80, 44),
    ("Kahawatta", "කහවත්ත", "Ratnapura", 6, 34, 80, 34),
    ("Kalawana", "කලවාන", "Ratnapura", 6, 31, 80, 24),
    ("Kiriella", "කිරිඇල්ල", "Ratnapura", 6, 46, 80, 18),
    ("Kolonna", "කොලොන්න", "Ratnapura", 6, 24, 80, 39),
    ("Kuruwita", "කුරුවිට", "Ratnapura", 6, 46, 80, 22),
    ("Nivithigala", "නිවිතිගල", "Ratnapura", 6, 36, 80, 27),
    ("Opanayaka", "ඔපනායක", "Ratnapura", 6, 38, 80, 38),
    ("Pelmadulla", "පැල්මඩුල්ල", "Ratnapura", 6, 37, 80, 32),
    ("Ratnapura", "රත්නපුර", "Ratnapura", 6, 41, 80, 24),
    ("Weligepola", "වැලිගෙපොල", "Ratnapura", 6, 30, 80, 42),

    # Kegalle (11)
    ("Aranayaka", "අරණායක", "Kegalle", 7, 9, 80, 28),
    ("Bulathkohupitiya", "බුලත්කොහුපිටිය", "Kegalle", 7, 4, 80, 20),
    ("Dehiovita", "දෙහිඕවිට", "Kegalle", 6, 58, 80, 17),
    ("Deraniyagala", "දැරණියගල", "Kegalle", 6, 56, 80, 20),
    ("Galigamuwa", "ගලිගමුව", "Kegalle", 7, 12, 80, 17),
    ("Kegalle", "කෑගල්ල", "Kegalle", 7, 15, 80, 21),
    ("Mawanella", "මාවනැල්ල", "Kegalle", 7, 15, 80, 27),
    ("Rambukkana", "රඹුක්කන", "Kegalle", 7, 19, 80, 24),
    ("Ruwanwella", "රුවන්වැල්ල", "Kegalle", 7, 3, 80, 15),
    ("Warakapola", "වරකාපොළ", "Kegalle", 7, 14, 80, 12),
    ("Yatiyantota", "යටියන්තොට", "Kegalle", 7, 2, 80, 18),
]


def build_merged_cities():
    from fortune_engine.constants import CITIES as OLD_CITIES, _DISTRICT_SI

    # Step 1: Start with existing 1..168 cities to keep exact IDs intact
    merged = []
    seen_keys = set()
    next_id = 1

    for c in OLD_CITIES:
        key = (c["district"], c["name"].lower().split("/")[0].strip())
        seen_keys.add(key)
        merged.append(c)
        next_id = max(next_id, c["id"] + 1)

    print(f"Existing preserved: {len(merged)} cities (IDs 1..{next_id - 1})")

    # Step 2: Add any DS divisions not already in OLD_CITIES
    added = 0
    for name_en, name_si, dist, lat_d, lat_m, lon_d, lon_m in ALL_331_DS_DIVISIONS:
        key = (dist, name_en.lower().split("/")[0].strip())
        # Check if already present or matches existing
        already = False
        for ex in merged:
            if ex["district"] == dist:
                ex_n = ex["name"].lower()
                req_n = name_en.lower().split("/")[0].strip()
                if req_n in ex_n or ex_n in req_n:
                    already = True
                    # If this is Attanagalla or has extra alias, update label nicely
                    if "attanagalla" in req_n and "wathupitiwala" not in ex["name"].lower():
                        ex["name"] = name_en
                        ex["sinhala"] = name_si
                    break

        if not already:
            city_obj = {
                "id": next_id,
                "name": name_en,
                "sinhala": name_si,
                "district": dist,
                "district_si": _DISTRICT_SI[dist],
                "lat": round(lat_d + lat_m / 60.0, 6),
                "lon": round(lon_d + lon_m / 60.0, 6),
            }
            merged.append(city_obj)
            next_id += 1
            added += 1

    print(f"Added new DS divisions: {added}")
    print(f"Total comprehensive cities in database: {len(merged)}")
    return merged


if __name__ == "__main__":
    cities = build_merged_cities()
    # Check Attanagalla / Wathupitiwala
    att = [c for c in cities if "attanagalla" in c["name"].lower() or "wathupitiwala" in c["name"].lower()]
    print("Attanagalla matches:", att)
    # Check Narammala
    nar = [c for c in cities if "narammala" in c["name"].lower()]
    print("Narammala matches:", nar)
