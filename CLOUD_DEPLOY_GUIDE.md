# Daily Fortune — Cloud Hosting & Mobile App Install Guide

මෙම `DailyFortune` ෆෝල්ඩරය දැන් සම්පූර්ණ **PWA (Progressive Web App)** සහ **Cloud-Ready Docker Server** එකක් ලෙස සූදානම් කර ඇත.

---

## 1. Windows PC එකේ Native Desktop App එකක් ලෙස පාවිච්චි කිරීම

1. ෆෝල්ඩරයේ ඇති **`Create_Windows_App_Shortcut.bat`** මත Double-Click කරන්න — එවිට ඔබේ Desktop මත **Daily Fortune** App Icon එක සෑදේ.
2. එය Double-Click කළ විට කිසිදු කළු Console කවුළුවක් නොපෙනී Chrome / Edge App Mode තුළ කෙලින්ම Software එකක් මෙන් විවෘත වේ.
3. නැතිනම් **`Launch_Daily_Fortune_App.bat`** මගින්ද එලෙසම විවෘත කළ හැක.

---

## 2. එකම Wi-Fi මත Phone එකෙන් පාවිච්චි කිරීම (Local Network)

1. PC එකේ Server එක ක්‍රියාත්මක වන විට ඇප් එකේ ඉහළ ඇති **`📲 ඇප්`** බොත්තම ඔබන්න.
2. එහි පෙන්වන `http://192.168.x.x:8795` (හෝ `10.x.x.x:8795`) ලිපිනය ඔබේ Phone Browser එකේ විවෘත කරන්න.
3. **Android Chrome**: Menu (`⋮`) → **"Add to home screen"** ඔබන්න.
4. **iPhone Safari**: Share (`⎋`) → **"Add to Home Screen"** ඔබන්න.

*(සටහන: Android Chrome හි ස්වයංක්‍රීය "Install App" පණිවිඩය ලැබීමට Online `https://` ලිපිනයක් අවශ්‍ය වේ — පහත 3 වන පියවර බලන්න.)*

---

## 3. පාරිභෝගිකයන් සඳහා Online Cloud Hosting (Render / Railway / VPS)

මෙම `DailyFortune` ෆෝල්ඩරය ඇතුළත Cloud Deploy සඳහා අවශ්‍ය සියලු ගොනු (`Dockerfile`, `render.yaml`, `Procfile`, `requirements.txt`, `/healthz`) සූදානම් කර ඇත.

### Option A: Render.com (පහසුම ක්‍රමය — Singapore Region / Free Starter)
1. `K:\STAR\DailyFortune` ෆෝල්ඩරයේ අන්තර්ගතය ඔබේ **GitHub Repository** එකකට Upload/Push කරන්න.
2. [Render.com](https://render.com) වෙත ගොස් **New + → Blueprint** (හෝ **Web Service**) තෝරා එම GitHub Repo එක සම්බන්ධ කරන්න.
3. `render.yaml` හා `Dockerfile` ස්වයංක්‍රීයව හඳුනාගනී — **Deploy** ඔබන්න. *(මෙම Docker Image එක තුළ Chromium + Noto Sinhala Fonts ඇති බැවින් Cloud තුළදී පවා PDF Export වැඩ කරයි!)*
4. Deploy අවසන් වූ පසු ලැබෙන `https://your-app.onrender.com` ලිපිනය පාරිභෝගිකයන්ට යවන්න.

### Option B: Railway / Fly.io / VPS Docker
```bash
docker build -t daily-fortune .
docker run -d -p 8795:8795 --name daily-fortune daily-fortune
```
`PORT` සහ `HOST` Environment Variables ස්වයංක්‍රීයව සහාය දක්වයි.

### පාරිභෝගිකයා Online Link එක විවෘත කළ පසු:
- **Android**: කෙලින්ම **"📲 Install"** බොත්තම පෙන්වයි — එක් ක්ලික් එකකින් Play Store App එකක් මෙන් Phone එකේ ස්ථාපනය වේ!
- **iPhone**: Safari → Share (`⎋`) → **"Add to Home Screen"** ඔබා Home Screen එකට ගනී.
- අවසන් වරට බැලූ කාලසටහන Phone එකේ Cache වන බැවින් Signal නැති විටදී පවා App එක විවෘත කර බලාගත හැක.
