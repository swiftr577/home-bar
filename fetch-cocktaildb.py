"""Build library.json for the Home Bar app from several open cocktail sources.

Run once (and again whenever you want fresh data):
    python fetch-cocktaildb.py
Then commit library.json next to index.html and bump CACHE in sw.js.

Sources (each is optional — a failure just skips that source):
  1. IBA official cocktails      github.com/teijo/iba-cocktails
  2. Cocktail Recipes dataset    huggingface.co/datasets/brianarbuckle/cocktail_recipes  (Death & Co etc.)
  3. TheCocktailDB               thecocktaildb.com (free API key "1")

Output is one uniform shape the app understands:
  {"name","source","glass","ingredients":[{"measure":"1 1/2 oz","name":"Gin"}],"instructions","image","iba"}
"""
import json, re, string, time, urllib.request, urllib.parse

def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "home-bar-app/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)

UNIT = r"(?:oz\.?|ounces?|ml|cl|dash(?:es)?|tsp\.?|tbsp\.?|teaspoons?|tablespoons?|bar ?spoons?|drops?|splash(?:es)?|cups?|parts?|shots?|pinch|top|float|rinse)"
NUM = r"(?:\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?|[½¼¾⅓⅔])"
SPLIT = re.compile(rf"^\s*((?:{NUM}\s*(?:-|to)?\s*{NUM}?\s*{UNIT}?|top(?:ped)?(?:\s+(?:up|off))?(?:\s+with)?|fill(?:\s+with)?|splash(?:\s+of)?|dash(?:es)?(?:\s+of)?)\.?)\s*(?:of\s+)?(.+)$", re.I)

def split_measure(s):
    """'0.75 oz. Rye Whiskey' -> ('0.75 oz', 'Rye Whiskey'); 'Mint sprig' -> ('', 'Mint sprig')"""
    s = s.strip()
    m = SPLIT.match(s)
    if m and m.group(2).strip():
        return m.group(1).strip(" ."), m.group(2).strip(" ,.")
    return "", s

out, seen = [], set()
def add(rec):
    key = rec["name"].strip().lower()
    if not key or key in seen or not rec["ingredients"]:
        return
    seen.add(key); out.append(rec)

# ---------- 1. IBA ----------
try:
    data = get("https://raw.githubusercontent.com/teijo/iba-cocktails/master/recipes.json")
    n = 0
    for d in data:
        ings = []
        for i in d.get("ingredients", []):
            if "special" in i:
                meas, name = split_measure(i["special"])
            else:
                amt = i.get("amount", ""); unit = i.get("unit", "")
                meas = f"{amt} {unit}".strip(); name = i.get("label") or i.get("ingredient", "")
            if name: ings.append({"measure": meas, "name": name})
        method = d.get("preparation", "")
        if d.get("garnish"): method += f" Garnish: {d['garnish']}."
        add({"name": d["name"], "source": "IBA", "glass": d.get("glass", ""), "ingredients": ings,
             "instructions": method.strip(), "image": "", "iba": 1}); n += 1
    print(f"IBA: {n} recipes")
except Exception as e:
    print(f"IBA: skipped ({e})")

# ---------- 2. Hugging Face cocktail_recipes ----------
try:
    n, offset = 0, 0
    while True:
        url = ("https://datasets-server.huggingface.co/rows?dataset=brianarbuckle%2Fcocktail_recipes"
               f"&config=default&split=train&offset={offset}&length=100")
        rows = get(url).get("rows", [])
        if not rows: break
        for r in rows:
            d = r["row"]
            ings = [dict(zip(("measure", "name"), split_measure(s))) for s in d.get("ingredients", []) if s.strip()]
            add({"name": d["title"], "source": d.get("source") or "Cocktail Recipes dataset", "glass": "",
                 "ingredients": ings, "instructions": " ".join(d.get("directions", [])), "image": "", "iba": 0}); n += 1
        offset += 100
        if len(rows) < 100: break
        time.sleep(0.2)
    print(f"Hugging Face dataset: {n} recipes")
except Exception as e:
    print(f"Hugging Face dataset: skipped ({e})")

# ---------- 3. TheCocktailDB ----------
try:
    n = 0
    for ch in string.ascii_lowercase + string.digits:
        try:
            drinks = get(f"https://www.thecocktaildb.com/api/json/v1/1/search.php?f={ch}").get("drinks") or []
        except Exception as e:
            print(f"  {ch}: failed ({e})"); continue
        for d in drinks:
            ings = []
            for k in range(1, 16):
                name = (d.get(f"strIngredient{k}") or "").strip()
                if name: ings.append({"measure": (d.get(f"strMeasure{k}") or "").strip(), "name": name})
            add({"name": d["strDrink"], "source": "TheCocktailDB", "glass": d.get("strGlass") or "", "ingredients": ings,
                 "instructions": d.get("strInstructions") or "", "image": d.get("strDrinkThumb") or "",
                 "id": d["idDrink"], "iba": 0}); n += 1
        time.sleep(0.3)
    print(f"TheCocktailDB: {n} recipes")
except Exception as e:
    print(f"TheCocktailDB: skipped ({e})")

out.sort(key=lambda d: d["name"].lower())
with open("library.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
print(f"Wrote library.json with {len(out)} unique recipes")
