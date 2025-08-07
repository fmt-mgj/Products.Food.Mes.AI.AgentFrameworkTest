# 🎯 **BMAD → PocketFlow: Komplet Brugervejledning**

*Fra dine BMAD agenter til et kørende API på under 5 minutter*

## 📋 **Hvad Er Dette System?**

Dette system tager dine **BMAD agenter** (som du plejer at lave som Markdown-filer) og konverterer dem automatisk til **rigtige, kørende agenter** bag et REST API. 

**Simpelt forklaret:**
- **BMAD** = Din måde at designe agenter på (Markdown filer)
- **PocketFlow** = Det tekniske framework der får agenterne til at køre
- **Dette system** = Broen mellem de to - konverterer BMAD til PocketFlow automatisk

---

## 🏗 **Trin 1: Forbered Dit System (Én Gang Setup)**

### 1.1 Tjek At Python Er Installeret

**Windows:**
```cmd
python --version
```

**Mac/Linux:**
```bash
python3 --version
```

Du skal have **Python 3.10 eller nyere**. Hvis ikke, installer det fra [python.org](https://python.org).

### 1.2 Download/Klon Projektet

```bash
# Hvis du har git installeret:
git clone [repository-url]
cd Products.Food.Mes.AI.AgentFrameworkTest

# ELLER download som ZIP og udpak
```

### 1.3 Installer Python Dependencies

**Windows:**
```cmd
pip install -r requirements.txt
```

**Mac/Linux:**
```bash
pip3 install -r requirements.txt
```

**Hvad installerer dette?**
- `pocketflow` - Rammeværket der kører agenterne
- `fastapi` - Web framework til API'et
- `uvicorn` - Web server
- Andre nødvendige pakker

---

## 🎨 **Trin 2: Lav Dine BMAD Agenter**

### 2.1 Forstå BMAD Strukturen

Dine agenter skal ligge i mappen: `bmad/agents/`

**Hver agent er en `.md` fil** med denne struktur:

```markdown
---
id: min-agent
description: Hvad agenten laver
tools: []
memory_scope: isolated
wait_for:
  docs: []
  agents: []
parallel: false
---

Din agent prompt her...
```

### 2.2 Eksempel: Lav En Simpel Agent

Lav filen: `bmad/agents/translator.md`

```markdown
---
id: translator
description: Oversætter tekst mellem sprog
tools: []
memory_scope: isolated
wait_for:
  docs: []
  agents: []
parallel: false
---

Du er en oversætter. Din opgave er at:

1. Læse den givne tekst
2. Identificere sproget 
3. Oversætte til dansk hvis teksten ikke er dansk
4. Oversætte til engelsk hvis teksten er dansk

Giv altid et klart, præcist resultat.
```

### 2.3 Forklaring Af YAML Front-Matter

**Hver indstilling forklaret:**

- **`id`**: Agentens unique navn (bruges i API calls)
- **`description`**: Kort beskrivelse af hvad agenten laver
- **`tools`**: Liste af værktøjer (kan være tom: `[]`)
- **`memory_scope`**: 
  - `isolated` = Agenten har sin egen hukommelse
  - `shared` = Deler hukommelse med andre agenter
- **`wait_for.docs`**: Dokumenter agenten skal vente på
- **`wait_for.agents`**: Andre agenter der skal køre først
- **`parallel`**: 
  - `false` = Kører sekventielt (standard)
  - `true` = Kan køre samtidig med andre

---

## 🔄 **Trin 3: Konverter BMAD Til PocketFlow**

### 3.1 Kør Konverteringskommandoen

**Det magiske kommando:**

```bash
python scripts/bmad2pf.py --src ./bmad --out ./generated
```

**Windows alternativ:**
```cmd
python scripts\bmad2pf.py --src .\bmad --out .\generated
```

### 3.2 Forståelse Af Kommandoen

**Hvad betyder parametrene?**

- `--src ./bmad` = "Læs mine BMAD filer fra bmad mappen"
- `--out ./generated` = "Gem den genererede kode i generated mappen"

**Ekstra muligheder:**

```bash
# Med verbose output (detaljeret information)
python scripts/bmad2pf.py --src ./bmad --out ./generated --verbose

# Hjælp og alle muligheder
python scripts/bmad2pf.py --help
```

### 3.3 Hvad Sker Der Under Konverteringen?

Systemet gør automatisk:

1. **Parser** dine BMAD filer og læser YAML front-matter
2. **Loader** konfiguration (hvis du har workflow.yaml)
3. **Genererer** Python kode ved hjælp af templates
4. **Formaterer** koden med Black og Ruff
5. **Gem** alt i `/generated` mappen

**Forventet output:**
```
-> Parsing BMAD files from ./bmad...
  [OK] Found 2 agents
-> Loading configuration...
  [OK] Loaded workflow.yaml
-> Generating PocketFlow code...
  [OK] Generated 8 files
  [OK] Black formatting applied
  [OK] Ruff validation passed
[SUCCESS] Generation complete in 0.234s
```

---

## 🚀 **Trin 4: Start Dit API**

### 4.1 Start Serveren

**Kommando til at starte serveren:**

```bash
uvicorn generated.app:app --reload --port 8000
```

**Windows:**
```cmd
uvicorn generated.app:app --reload --port 8000
```

### 4.2 Forståelse Af Start Kommandoen

**Hvad betyder parametrene?**

- `generated.app:app` = "Kør app'en fra generated/app.py"
- `--reload` = "Genstart automatisk hvis filer ændres"
- `--port 8000` = "Kør på port 8000"

### 4.3 Verificer At Serveren Kører

**Du skal se output som dette:**
```
INFO:     Will watch for changes in these directories: ['/path/to/project']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using WatchFiles
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Test at det virker:**

Åbn din browser og gå til: `http://localhost:8000/docs`

Du skulle nu se FastAPI's automatiske dokumentation!

---

## 📡 **Trin 5: Test Dine Agenter**

### 5.1 Via Browser (Nemt At Starte Med)

1. Gå til: `http://localhost:8000/docs`
2. Find `/run` endpointet
3. Klik "Try it out"
4. Udfyld JSON:

```json
{
  "flow": "default",
  "input": "Hej, hvordan har du det?",
  "story_id": "test-123"
}
```

5. Klik "Execute"

### 5.2 Via Terminal (cURL)

```bash
curl -X POST "http://localhost:8000/run" \
  -H "Content-Type: application/json" \
  -d '{
    "flow": "default",
    "input": "Hej, hvordan har du det?",
    "story_id": "test-123"
  }'
```

**Windows PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/run" -Method POST -ContentType "application/json" -Body '{"flow": "default", "input": "Hej, hvordan har du det?", "story_id": "test-123"}'
```

### 5.3 Forståelse Af API Parametrene

**Input forklaring:**

- **`flow`**: Hvilket workflow der skal køres (næsten altid "default")
- **`input`**: Den tekst du vil have agenten til at behandle  
- **`story_id`**: Unique ID for denne samtale/session

**Respons eksempel:**
```json
{
  "status": "completed",
  "results": {
    "translator": "Hello, how are you?"
  },
  "execution_time": 1.23
}
```

---

## 🔧 **Trin 6: Avancerede Funktioner**

### 6.1 Agent Dependencies (Wait_for)

**Hvis en agent skal vente på en anden:**

```markdown
---
id: reviewer
wait_for:
  agents: [translator]
---

Review og forbedre oversættelsen fra translator agenten.
```

### 6.2 Parallel Agenter

**Agenter der kan køre samtidigt:**

```markdown
---
id: fast-agent
parallel: true
---

Denne agent kan køre samtidig med andre parallel agenter.
```

### 6.3 Memory Scopes

**Isolated (standard):**
- Hver agent har sin egen hukommelse per story_id

**Shared:**
- Agenter deler hukommelse på tværs af sessions

### 6.4 Debugging Endpoints

**Tjek agent status:**
```bash
curl http://localhost:8000/agent/translator/ready
```

**Se hukommelse:**
```bash
curl http://localhost:8000/memory/isolated/test-123__translator
```

---

## 📝 **Trin 7: Dokument Management**

### 7.1 Upload Dokumenter

```bash
# Upload et dokument
curl -X PUT "http://localhost:8000/doc/my-document" \
  -H "Content-Type: text/plain" \
  -d "Dette er mit dokument indhold"
```

### 7.2 Hent Dokumenter

```bash
# Hent et dokument
curl http://localhost:8000/doc/my-document
```

### 7.3 Tjek Om Dokument Findes

```bash
curl http://localhost:8000/doc/my-document/status
```

**Response:**
```json
{"exists": true}
```

---

## 🐛 **Fejlfinding: Hyppige Problemer**

### Problem 1: "Command not found" 

**Fejl:** `python: command not found`

**Løsning:**
- Windows: Prøv `py` i stedet for `python`
- Mac: Prøv `python3` i stedet for `python`
- Sørg for Python er installeret og i PATH

### Problem 2: "No module named 'xyz'"

**Fejl:** `ModuleNotFoundError: No module named 'fastapi'`

**Løsning:**
```bash
# Reinstaller dependencies
pip install -r requirements.txt

# Eller individuelt
pip install fastapi uvicorn pocketflow
```

### Problem 3: Port Already In Use

**Fejl:** `Error: [Errno 48] Address already in use`

**Løsning:**
```bash
# Brug en anden port
uvicorn generated.app:app --reload --port 8001

# Eller stop den kørende proces
lsof -i :8000  # Find process ID
kill [process_id]
```

### Problem 4: Generation Fejler

**Fejl:** Parsing eller generation fejler

**Løsning:**
1. Tjek YAML syntax i dine agent filer
2. Kør med `--verbose` for flere detaljer:
```bash
python scripts/bmad2pf.py --src ./bmad --out ./generated --verbose
```

### Problem 5: Agenter Responderer Ikke

**Mulige årsager:**
- Manglende API nøgler (hvis agenter bruger LLM)
- Fejl i agent prompts
- Dependencies ikke opfyldt

**Debug steps:**
1. Tjek logs i terminalen
2. Test `/health` endpointet
3. Tjek agent status via `/agent/{name}/ready`

---

## 🌟 **Trin 8: Deployment (Avanceret)**

### 8.1 Docker Build

```bash
# Build container
docker build -t min-bmad-app .

# Kør container
docker run -p 8000:8000 min-bmad-app
```

### 8.2 Environment Variables

Lav en `.env` fil:

```env
OPENAI_API_KEY=your-key-here
ANTHROPIC_API_KEY=your-key-here
```

### 8.3 Railway Deployment

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login og deploy  
railway login
railway up
```

---

## 📚 **Trin 9: Best Practices**

### 9.1 Agent Design

**✅ Gør dette:**
- Lav klare, specifikke prompts
- Brug deskriptive agent IDs
- Test med simple inputs først

**❌ Undgå dette:**
- Alt for lange prompts (under 500 ord er bedst)
- Cirkulære dependencies mellem agenter
- For mange parallel agenter (max 3-4 ad gangen)

### 9.2 Performance

**Hurtigere generation:**
- Hold BMAD filer simple
- Brug færre agenter per flow
- Test lokalt før deployment

### 9.3 Debugging Workflow

1. **Start simpelt** - Lav én agent først
2. **Test grundigt** - Verificer den virker
3. **Byg gradvist** - Tilføj flere agenter en ad gangen
4. **Brug verbose mode** - Når ting går galt

---

## 🎯 **Trin 10: Komplet Eksempel (Start Til Slut)**

Lad os lave et komplet eksempel sammen:

### 10.1 Lav Agent Fil

`bmad/agents/writer.md`:
```markdown
---
id: writer
description: Skriver kreative historier
tools: []
memory_scope: isolated
wait_for:
  docs: []
  agents: []
parallel: false
---

Du er en kreativ forfatter. Din opgave:

1. Læs input teksten
2. Identificer genre og tone
3. Skriv en kort, engaging historie (max 200 ord)
4. Inkluder et twist i slutningen

Skriv altid på dansk og gør historien interessant!
```

### 10.2 Generer Kode

```bash
python scripts/bmad2pf.py --src ./bmad --out ./generated
```

### 10.3 Start Server

```bash
uvicorn generated.app:app --reload --port 8000
```

### 10.4 Test Agent

```bash
curl -X POST "http://localhost:8000/run" \
  -H "Content-Type: application/json" \
  -d '{
    "flow": "default",
    "input": "Skriv en historie om en robot der opdager følelser",
    "story_id": "creative-test-1"
  }'
```

### 10.5 Se Resultatet

Du skulle få noget som:
```json
{
  "status": "completed", 
  "results": {
    "writer": "R0B-7 havde altid været den mest effektive robot i fabrikken..."
  },
  "execution_time": 2.1
}
```

---

## 🏆 **Færdig!**

**Tillykke! Du har nu:**

✅ Forstået BMAD → PocketFlow systemet  
✅ Konverteret dine BMAD agenter til kørende API  
✅ Testet det hele og fået det til at virke  
✅ Lært at fejlfinde og optimere  

**Næste skridt:** Byg dine egne agenter og del dem med verden! 🎉

---

**📞 Har du brug for hjælp?**
- Læs denne guide igen (de fleste problemer er dækket)
- Brug `--verbose` mode for detaljeret debugging
- Tjek `/docs` endpointet for API dokumentation
- Start simpelt og byg gradvist