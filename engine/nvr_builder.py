import os
import json
import re
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://hanifsalman11.github.io/poe-nvr-index").rstrip("/")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "f1e2d3c4b5a6f7e8d9c0b1a2f3e4d5c6").strip()
CUSTOM_CAMERA = os.environ.get("CUSTOM_CAMERA", "").strip()
PAGES_PER_RUN = int(os.environ.get("PAGES_PER_RUN", "3"))

DOCS_DIR = "docs"
DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_cameras.json")
MONETIZATION_FILE = os.path.join(DATA_DIR, "monetization.json")

# Format: (Camera Model Name, Megapixels, Default H.265 Bitrate Mbps, Default FPS, Max PoE Watts, PoE Standard)
SEED_CAMERAS = [
    ("Reolink RLC-810A 4K 8MP Bullet PoE", 8, 6.1, 25, 10.5, "IEEE 802.3af PoE"),
    ("Reolink TrackMix PoE Dual-Lens PTZ", 8, 8.2, 25, 15.0, "IEEE 802.3af/at PoE+"),
    ("Reolink Duo 3 PoE 16MP UHD Panoramic", 16, 10.5, 20, 14.5, "IEEE 802.3at PoE+"),
    ("Ubiquiti UniFi Protect G5 Pro 4K", 8, 10.0, 30, 13.0, "IEEE 802.3af PoE"),
    ("Ubiquiti UniFi Protect AI Pro 4K", 8, 12.0, 30, 11.0, "IEEE 802.3af PoE"),
    ("Amcrest UltraHD 4K 8MP IP8M-T2599EW", 8, 6.5, 20, 9.5, "IEEE 802.3af PoE"),
    ("Hikvision DS-2CD2387G2-LU 4K ColorVu", 8, 8.0, 25, 12.5, "IEEE 802.3af PoE"),
    ("Dahua IPC-HFW5849T1-ASE-LED Full-Color 8MP", 8, 8.0, 25, 11.5, "IEEE 802.3af PoE"),
    ("EmpireTech IPC-Color4K-T 8MP 1/1.2 CMOS", 8, 8.5, 30, 12.0, "IEEE 802.3af PoE"),
    ("Annke NC800 4K 8MP NightChroma PoE", 8, 6.5, 20, 10.0, "IEEE 802.3af PoE"),
    ("Reolink RLC-823S2 4K 16X Optical Zoom PTZ", 8, 8.5, 25, 24.0, "IEEE 802.3at PoE+"),
    ("Ubiquiti UniFi G5 Turret Ultra 2K", 4, 5.0, 30, 4.5, "IEEE 802.3af PoE"),
    ("Reolink RLC-1212A 12MP Ultra-HD PoE", 12, 9.0, 20, 12.0, "IEEE 802.3af PoE"),
    ("Lorex 4K+ 12MP Smart Deterrence PoE", 12, 9.5, 20, 12.5, "IEEE 802.3af PoE"),
    ("Axis P3268-LVE 8MP 4K Outdoor Dome", 8, 8.5, 30, 12.9, "IEEE 802.3af/at PoE+"),
    ("Hanwha Vision Wisenet XNO-8080R 5MP", 5, 5.5, 30, 12.9, "IEEE 802.3af PoE"),
    ("Amcrest 5MP Turret IP5M-T1179EW PoE", 5, 4.5, 25, 7.5, "IEEE 802.3af PoE"),
    ("Reolink CX410 ColorX 2K True Full-Color", 4, 4.2, 30, 9.0, "IEEE 802.3af PoE"),
    ("Reolink CX810 ColorX 4K 8MP F1.0 Aperture", 8, 6.8, 25, 10.5, "IEEE 802.3af PoE"),
    ("Hikvision AcuSense PCI-T18F2S 8MP Turret", 8, 7.5, 25, 11.0, "IEEE 802.3af PoE"),
    ("UniFi Protect AI Theta 4K 360 Fisheye", 8, 10.0, 30, 12.5, "IEEE 802.3af PoE"),
    ("Synology BC500 5MP AI Bullet PoE Camera", 5, 5.0, 30, 8.5, "IEEE 802.3af PoE"),
    ("TP-Link VIGI C385 4K 8MP Full-Color PoE", 8, 6.5, 25, 10.0, "IEEE 802.3af PoE"),
    ("Uniview IPC3618SB-ADF28KMC-I0 8MP Tri-Guard", 8, 7.0, 25, 11.5, "IEEE 802.3af PoE"),
    ("Reolink RLC-843A 4K Vandal-Proof IK10 Dome", 8, 6.5, 25, 11.0, "IEEE 802.3af PoE"),
    ("Amcrest 4K AI Booby-Trap PTZ IP8M-2796EW", 8, 8.5, 30, 22.0, "IEEE 802.3at PoE+"),
    ("Hikvision DS-2DE4425IW-DE 4MP 25X DarkFighter PTZ", 4, 6.0, 30, 24.0, "IEEE 802.3at PoE+"),
    ("ReolinkFE-P 6MP 360-Degree Fisheye PoE", 6, 6.0, 25, 9.5, "IEEE 802.3af PoE"),
    ("Ubiquiti UniFi G4 Doorbell Pro PoE Kit", 5, 6.0, 30, 10.0, "IEEE 802.3af PoE"),
    ("Vivotek IB9387-HT-A 5MP Outdoor Bullet PoE", 5, 5.5, 30, 12.9, "IEEE 802.3af PoE")
]


def load_json(filepath, default):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Could not parse {filepath}: {e}")
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def safe_float(val, default=6.5):
    try:
        cleaned = re.sub(r"[^0-9.]", "", str(val))
        return float(cleaned) if cleaned else float(default)
    except Exception:
        return float(default)


def build_amazon_url(search_keywords, mon_cfg):
    domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")
    encoded_q = urllib.parse.quote_plus(search_keywords)
    return f"https://{domain}/s?k={encoded_q}&tag={tag}"


def discover_google_camera_queries():
    """Mengambil model kamera PoE & NVR yang sedang dicari di Google Autocomplete US."""
    discovered = []
    seeds = [
        "reolink ",
        "unifi protect ",
        "hikvision 4k ",
        "amcrest poe ",
        "nvr storage calculator for "
    ]
    for seed in seeds:
        try:
            q = f"{seed}storage calculator" if "calculator" not in seed else seed
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q={urllib.parse.quote(q)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for suggestion in data[1]:
                    cleaned = re.sub(
                        r"\b(nvr|storage|calculator|hard drive|size|bitrate|bandwidth|for|how much)\b",
                        "",
                        suggestion,
                        flags=re.IGNORECASE
                    ).strip()
                    if 5 <= len(cleaned) <= 42:
                        discovered.append((cleaned.title(), 8, 6.5, 25, 11.5, "IEEE 802.3af PoE"))
        except Exception as e:
            print(f"[WARN] Google Suggest notice: {e}")
    return discovered


def build_deterministic_nvr_data(cam_tuple):
    """Mesin Fisika Bitrate Video & Kapasitas Hardisk NVR (100% bebas gagal)."""
    cam_name, mp, bitrate_mbps, fps, poe_watts, poe_std = cam_tuple

    # Rumus konversi: 1 Mbps kontinu selama 24 jam = (1 / 8) MB/s * 86400 detik = 10,800 MB = 10.55 GB/hari
    gb_per_day_single = round(bitrate_mbps * 10.55, 1)
    # Default 8 kamera, rekam 24/7 selama 30 hari (dengan 10% overhead formatting filesystem)
    tb_8cam_30d = round((gb_per_day_single * 8 * 30 * 1.10) / 1000.0, 1)
    poe_8cam_watts = int(round(poe_watts * 8 * 1.25))

    if tb_8cam_30d <= 6.0:
        hdd_rec = "WD Purple Pro / Seagate SkyHawk 8TB 24/7 Surveillance Hard Drive"
        hdd_query = "WD Purple 8TB Surveillance Internal Hard Drive SATA"
        hdd_price = "$169 - $219"
    elif tb_8cam_30d <= 12.0:
        hdd_rec = "WD Purple Pro / Seagate SkyHawk AI 12TB 7200RPM Surveillance HDD"
        hdd_query = "WD Purple Pro 12TB Surveillance Hard Drive"
        hdd_price = "$239 - $299"
    else:
        hdd_rec = "WD Purple Pro / Seagate SkyHawk AI 16TB–20TB Enterprise NVR Hard Drive"
        hdd_query = "Seagate SkyHawk AI 16TB Surveillance Hard Drive"
        hdd_price = "$299 - $399"

    return {
        "camera_name": cam_name,
        "seo_title": f"{cam_name} NVR Storage (TB), Bitrate & PoE Switch Calculator (2026)",
        "meta_description": f"Calculate exact NVR hard drive capacity ({tb_8cam_30d} TB for 8 cameras / 30 days), H.265 bitrate ({bitrate_mbps} Mbps), and PoE switch wattage for the {cam_name}.",
        "specs": {
            "resolution_mp": mp,
            "default_bitrate_mbps": bitrate_mbps,
            "default_fps": fps,
            "max_poe_watts": poe_watts,
            "poe_standard": poe_std,
            "gb_per_day_per_cam": gb_per_day_single,
            "recommended_8cam_30d_tb": tb_8cam_30d
        },
        "engineering_verdict": f"Operating at {mp}MP resolution ({fps} FPS) with H.265 compression, a single {cam_name} generates an average stream of {bitrate_mbps} Mbps ({gb_per_day_single} GB per 24 hours). An 8-camera system recording 24/7 for 30 days requires {tb_8cam_30d} TB of formatted NVR storage and a {poe_std} switch with at least {poe_8cam_watts}W of total power budget.",
        "hardware_bundle": [
            {
                "badge": "24/7 Surveillance HDD",
                "title": hdd_rec,
                "price_range": hdd_price,
                "amazon_query": hdd_query,
                "tech_note": f"Engineered with AllFrame/ImagePerfect firmware for 24/7 continuous write workloads without dropped video frames."
            },
            {
                "badge": "Matched PoE+ Switch",
                "title": f"8/16-Port Gigabit {poe_std} Network Switch ({max(120, poe_8cam_watts)}W+ Budget)",
                "price_range": "$79 - $219",
                "amazon_query": "16 Port Gigabit PoE+ Switch 250W Fanless Metal",
                "tech_note": f"Provides {poe_watts}W per port with 25% night-vision IR surge headroom and VLAN isolation support."
            },
            {
                "badge": "Camera & NVR System",
                "title": f"{cam_name} Add-On Camera & Multi-Channel NVR Bundle",
                "price_range": "$109 - $699",
                "amazon_query": f"{cam_name} PoE Camera",
                "tech_note": f"Delivers {mp}MP Ultra-HD video with onboard person/vehicle AI detection and H.265 hardware encoding."
            },
            {
                "badge": "Pure Copper Cat6 Spool",
                "title": "1000ft / 500ft 23AWG Solid Bare Copper Cat6 Riser/Outdoor Ethernet Cable",
                "price_range": "$119 - $199",
                "amazon_query": "1000ft Cat6 Solid Bare Copper Ethernet Cable CMR Outdoor",
                "tech_note": "Never use Copper-Clad Aluminum (CCA) wire for PoE cameras; 23AWG 100% solid bare copper prevents voltage drop up to 328ft."
            }
        ],
        "deployment_checklist": [
            f"Enable H.265 / H.265+ smart encoding on your {cam_name} main stream to cut NVR hard drive consumption by up to 45% compared to legacy H.264.",
            "Never use desktop PC hard drives (like WD Blue or Seagate Barracuda) inside an NVR; their read/write heads overheat and fail under 24/7 multi-stream recording.",
            f"Size your PoE switch power supply with at least 25% headroom above the {poe_watts}W maximum rating to prevent cameras from rebooting when IR night-vision LEDs turn on simultaneously.",
            "Set a 30-frames-per-second (1-second atau 2-second) I-Frame / Keyframe interval so motion triggers and NVR timeline scrubbing remain responsive."
        ],
        "faqs": [
            {
                "q": f"How much NVR hard drive space does one {cam_name} use per day?",
                "a": f"At {mp}MP ({fps} FPS) using H.265 compression at {bitrate_mbps} Mbps, a single {cam_name} recording 24/7 consumes {gb_per_day_single} GB per day, or approximately {round(gb_per_day_single * 30 / 1000, 2)} TB per 30-day month."
            },
            {
                "q": f"What size hard drive do I need for 8 {cam_name} cameras for 30 days?",
                "a": f"For 24/7 continuous recording across 8 {cam_name} cameras over 30 days, you need {tb_8cam_30d} TB of storage ({hdd_rec}). If you enable Smart Motion/AI Event-Only recording (30% activity), storage drops to approximately {round(tb_8cam_30d * 0.30, 1)} TB."
            },
            {
                "q": f"How many watts does the {cam_name} draw on a PoE switch?",
                "a": f"The {cam_name} draws ~4.5W during daytime operation and peaks at {poe_watts}W at night when infrared (IR) or warm spotlight LEDs are at 100% brightness ({poe_std})."
            }
        ]
    }


def generate_nvr_data(cam_tuple):
    """Memanggil Gemini 2.5 Flash API; jika gagal otomatis memakai Deterministic Bitrate Engine."""
    if not GEMINI_API_KEY:
        return build_deterministic_nvr_data(cam_tuple)

    cam_name, mp, bitrate_mbps, fps, poe_watts, poe_std = cam_tuple
    gb_per_day_single = round(bitrate_mbps * 10.55, 1)
    tb_8cam_30d = round((gb_per_day_single * 8 * 30 * 1.10) / 1000.0, 1)

    prompt = f"""
You are a Senior IP Video Surveillance & Network Storage Architect. Create an accurate 2026 NVR hard drive storage (TB), bitrate, and PoE switch sizing guide for: "{cam_name}".
Baseline reference specs: Resolution={mp}MP, H.265 Bitrate={bitrate_mbps} Mbps, Frame Rate={fps} FPS, Max PoE Power={poe_watts}W ({poe_std}), Single Camera 24h Usage={gb_per_day_single} GB/day, 8-Camera 30-Day Total={tb_8cam_30d} TB.
Return ONLY a valid JSON object matching this exact schema:
{{
  "camera_name": "{cam_name}",
  "seo_title": "{cam_name} NVR Storage (TB), Bitrate & PoE Switch Calculator (2026)",
  "meta_description": "Calculate exact NVR hard drive capacity (TB), H.265/H.264 bitrate (Mbps), and PoE switch wattage for the {cam_name}.",
  "specs": {{
    "resolution_mp": {mp},
    "default_bitrate_mbps": {bitrate_mbps},
    "default_fps": {fps},
    "max_poe_watts": {poe_watts},
    "poe_standard": "{poe_std}",
    "gb_per_day_per_cam": {gb_per_day_single},
    "recommended_8cam_30d_tb": {tb_8cam_30d}
  }},
  "engineering_verdict": "3-sentence technical summary stating resolution, Mbps bitrate, GB per day, and exact TB needed for 8 cameras over 30 days.",
  "hardware_bundle": [
    {{
      "badge": "24/7 Surveillance HDD",
      "title": "Exact WD Purple Pro or Seagate SkyHawk AI TB Hard Drive recommendation",
      "price_range": "$189 - $349",
      "amazon_query": "WD Purple Pro 12TB Surveillance Hard Drive",
      "tech_note": "1-sentence continuous write reliability note"
    }},
    {{
      "badge": "Matched PoE+ Switch",
      "title": "Exact Gigabit PoE+ Switch recommendation",
      "price_range": "$79 - $219",
      "amazon_query": "16 Port Gigabit PoE+ Switch 250W",
      "tech_note": "1-sentence PoE wattage budget note"
    }},
    {{
      "badge": "Camera & NVR Hardware",
      "title": "{cam_name}",
      "price_range": "$109 - $599",
      "amazon_query": "{cam_name}",
      "tech_note": "1-sentence optical and AI detection note"
    }},
    {{
      "badge": "Solid Bare Copper Cat6",
      "title": "1000ft 23AWG Solid Bare Copper Cat6 Ethernet Spool",
      "price_range": "$129 - $199",
      "amazon_query": "1000ft Cat6 Solid Bare Copper Ethernet Cable",
      "tech_note": "1-sentence PoE voltage drop prevention note"
    }}
  ],
  "deployment_checklist": [
    "Step 1 regarding H.265 vs H.264 encoding",
    "Step 2 regarding surveillance-grade HDD vs desktop HDD",
    "Step 3 regarding PoE night-vision IR wattage headroom",
    "Step 4 regarding Cat6 pure copper cabling"
  ],
  "faqs": [
    {{"q": "How much NVR hard drive space does one {cam_name} use per day?", "a": "Exact GB per day and TB per month."}},
    {{"q": "What size hard drive do I need for 8 {cam_name} cameras for 30 days?", "a": "Exact TB required for 24/7 vs motion recording."}},
    {{"q": "How many watts does the {cam_name} use on a PoE switch?", "a": "Exact daytime vs night-vision IR wattage."}}
  ]
}}
"""

    for model_id in ["gemini-2.5-flash", "gemini-2.0-flash"]:
        try:
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json"
                }
            }
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=35) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                raw_text = re.sub(r"\s*```$", "", raw_text)
                parsed = json.loads(raw_text)
                if "specs" in parsed and "hardware_bundle" in parsed:
                    return parsed
        except Exception as e:
            print(f"[WARN] Gemini ({model_id}) notice for '{cam_name}': {e}")

    return build_deterministic_nvr_data(cam_tuple)


def build_nvr_html_page(data, slug, mon_cfg):
    cam_name = data.get("camera_name", "4K PoE Camera")
    sp = data.get("specs", {})
    mp = int(safe_float(sp.get("resolution_mp", 8), 8))
    bitrate_mbps = round(safe_float(sp.get("default_bitrate_mbps", 6.5), 6.5), 1)
    fps = int(safe_float(sp.get("default_fps", 25), 25))
    poe_watts = round(safe_float(sp.get("max_poe_watts", 11.5), 11.5), 1)
    poe_std = sp.get("poe_standard", "IEEE 802.3af PoE")
    gb_day = round(bitrate_mbps * 10.55, 1)

    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "WD+Purple+Pro+Surveillance+Hard+Drive"), mon_cfg)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": f"{cam_name} NVR Storage & PoE Switch Calculator",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web Browser",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f.get("q", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}
                    } for f in data.get("faqs", [])
                ]
            }
        ]
    }

    bundle_html = ""
    for item in data.get("hardware_bundle", []):
        amz_url = build_amazon_url(item.get("amazon_query", item.get("title", "WD Purple Hard Drive")), mon_cfg)
        bundle_html += f"""
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between hover:border-sky-500/60 transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold uppercase tracking-wider bg-sky-500/10 text-sky-400 border border-sky-500/20 px-2.5 py-0.5 rounded">{item.get('badge', 'NVR Gear')}</span>
              <span class="text-sm font-bold text-emerald-400">{item.get('price_range', '$99+')}</span>
            </div>
            <h3 class="text-base font-bold text-white mt-2">{item.get('title', '')}</h3>
            <p class="text-xs text-slate-400 mt-2 leading-relaxed">🛡️ {item.get('tech_note', '')}</p>
          </div>
          <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="mt-5 block text-center bg-sky-500 hover:bg-sky-400 text-slate-950 font-extrabold py-2.5 px-4 rounded-lg text-sm transition shadow-lg">
            Check Price on Amazon →
          </a>
        </div>"""

    # Build Multi-Camera Retention Table (2, 4, 8, 12, 16, 32 Cameras)
    matrix_rows_html = ""
    for cam_cnt in [2, 4, 8, 12, 16, 32]:
        tot_mbps = round(bitrate_mbps * cam_cnt, 1)
        tb_14d = round((gb_day * cam_cnt * 14 * 1.10) / 1000.0, 1)
        tb_30d = round((gb_day * cam_cnt * 30 * 1.10) / 1000.0, 1)
        sw_watts = int(round(poe_watts * cam_cnt * 1.25))
        matrix_rows_html += f"""
        <tr class="border-b border-slate-800 hover:bg-slate-800/40">
          <td class="py-3 px-4 font-bold text-white">{cam_cnt} Cameras</td>
          <td class="py-3 px-4 text-slate-300">{tot_mbps} Mbps</td>
          <td class="py-3 px-4 text-sky-400 font-semibold">{tb_14d} TB</td>
          <td class="py-3 px-4 font-bold text-emerald-400">{tb_30d} TB</td>
          <td class="py-3 px-4 text-xs text-amber-400 font-semibold">Min {sw_watts}W PoE Budget</td>
        </tr>"""

    checklist_html = ""
    for idx, step_text in enumerate(data.get("deployment_checklist", []), start=1):
        checklist_html += f"""
        <label class="flex items-start gap-3.5 bg-slate-900 border border-slate-800 rounded-xl p-4 cursor-pointer hover:border-slate-700 transition">
          <input type="checkbox" class="mt-1 w-5 h-5 accent-sky-500 rounded cursor-pointer nvr-check">
          <span class="text-sm text-slate-200 leading-relaxed"><strong>Step {idx}:</strong> {step_text}</span>
        </label>"""

    faqs_html = "".join([
        f"<div class='bg-slate-900 border border-slate-800 rounded-xl p-5'><h3 class='font-bold text-white text-base mb-2'>{f.get('q', '')}</h3><p class='text-sm text-slate-300 leading-relaxed'>{f.get('a', '')}</p></div>"
        for f in data.get("faqs", [])
    ])

    canonical_url = f"{SITE_BASE_URL}/{slug}.html"
    amz_domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    amz_tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('seo_title', cam_name)}</title>
  <meta name="description" content="{data.get('meta_description', '')}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{data.get('seo_title', cam_name)}">
  <meta property="og:description" content="{data.get('meta_description', '')}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_url}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="application/ld+json">{json.dumps(schema_graph)}</script>
</head>
<body class="bg-slate-950 text-slate-100 antialiased min-h-screen flex flex-col">
  <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <a href="index.html" class="text-lg font-black tracking-tight text-white flex items-center gap-2">
        <span class="bg-sky-500 text-slate-950 px-2 py-0.5 rounded font-black">NVR</span>StorageIndex
      </a>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-sky-500 hover:bg-sky-400 text-slate-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Surveillance Hard Drives →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full">
    <div class="mb-8">
      <div class="flex flex-wrap items-center gap-2.5 mb-3">
        <span class="text-xs font-extrabold uppercase tracking-widest bg-sky-500 text-slate-950 px-3 py-1 rounded-full">{mp}MP Ultra-HD ({fps} FPS)</span>
        <span class="text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">H.265 Stream: {bitrate_mbps} Mbps ({gb_day} GB/day)</span>
        <span class="text-xs font-semibold bg-slate-800 text-slate-300 px-3 py-1 rounded-full">Max Power: {poe_watts}W ({poe_std})</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight">{data.get('seo_title', cam_name)}</h1>
      <div class="mt-4 bg-slate-900 border-l-4 border-sky-500 p-4 rounded-r-xl text-sm text-slate-200 leading-relaxed">
        <strong>Surveillance Storage Benchmark:</strong> {data.get('engineering_verdict', '')}
      </div>
    </div>

    <!-- INTERACTIVE NVR HARD DRIVE (TB) & POE SWITCH CALCULATOR -->
    <section class="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 mb-12 shadow-2xl">
      <h2 class="text-xl font-extrabold text-white mb-2">Interactive {cam_name} NVR Storage & PoE Budget Calculator</h2>
      <p class="text-xs text-slate-400 mb-6">Adjust your camera count, desired retention days, video compression codec, and daily motion activity to calculate exact Terabytes (TB) and PoE switch wattage.</p>

      <div class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-5">
          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="camSlider" class="text-slate-300">Number of {cam_name} Cameras</label>
              <span class="text-sky-400 font-bold"><span id="camVal">8</span> Cameras</span>
            </div>
            <input id="camSlider" type="range" min="1" max="32" step="1" value="8" class="w-full accent-sky-500 cursor-pointer">
          </div>

          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="daysSlider" class="text-slate-300"> Desired Footage Retention (Days)</label>
              <span class="text-sky-400 font-bold"><span id="daysVal">30</span> Days</span>
            </div>
            <input id="daysSlider" type="range" min="7" max="90" step="1" value="30" class="w-full accent-sky-500 cursor-pointer">
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="codecSelect" class="block text-xs font-medium text-slate-400 mb-1">Video Codec</label>
              <select id="codecSelect" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-sky-500">
                <option value="0.70">H.265+ (Smart AI Codec)</option>
                <option value="1.00" selected>H.265 (HEVC Standard)</option>
                <option value="1.65">H.264 (Legacy Codec)</option>
              </select>
            </div>
            <div>
              <label for="modeSelect" class="block text-xs font-medium text-slate-400 mb-1">Recording Schedule</label>
              <select id="modeSelect" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-sky-500">
                <option value="1.00" selected>24/7 Continuous (100%)</option>
                <option value="0.50">High Traffic Motion (50%)</option>
                <option value="0.25">Smart AI Events Only (25%)</option>
              </select>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-slate-950 border border-sky-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-sky-400 font-bold">Required NVR Storage</span>
            <div class="text-2xl sm:text-3xl font-black text-white mt-1"><span id="tbOut">0.0</span> <span class="text-sm font-normal text-slate-400">TB</span></div>
            <p id="bandwidthOut" class="text-xs text-slate-400 mt-1">Total Stream: 48.8 Mbps</p>
          </div>

          <div class="bg-slate-950 border border-emerald-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-emerald-400 font-bold">Min PoE Switch Budget</span>
            <div class="text-2xl sm:text-3xl font-black text-emerald-400 mt-1"><span id="poeWattsOut">120</span> <span class="text-sm font-normal text-slate-400">Watts</span></div>
            <p class="text-xs text-slate-500 mt-1">Includes 25% IR night surge</p>
          </div>
        </div>
      </div>

      <div class="mt-6 bg-sky-950/40 border border-sky-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div id="hddAdviceBanner" class="text-sm text-sky-100 font-medium"></div>
        <a id="dynamicHddBtn" href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="shrink-0 bg-sky-500 hover:bg-sky-400 text-slate-950 font-extrabold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider transition">
          Shop Recommended NVR Drive on Amazon →
        </a>
      </div>
    </section>

    <!-- 4-CARD HARDWARE BUNDLE -->
    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Recommended NVR Storage & PoE Hardware for {cam_name}</h2>
        <span class="text-xs text-slate-400">24/7 Continuous Duty Rated</span>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{bundle_html}</div>
    </section>

    <!-- RETENTION & POE MATRIX TABLE -->
    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-4">{cam_name} Multi-Camera Storage & PoE Sizing Chart (24/7 H.265)</h2>
      <div class="overflow-x-auto bg-slate-900 border border-slate-800 rounded-xl">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="border-b border-slate-800 bg-slate-950/60 text-slate-400 uppercase text-xs">
              <th class="py-3.5 px-4">Camera Count</th>
              <th class="py-3.5 px-4">Total NVR Bandwidth</th>
              <th class="py-3.5 px-4 text-sky-400">14-Day 24/7 Storage</th>
              <th class="py-3.5 px-4 text-emerald-400">30-Day 24/7 Storage</th>
              <th class="py-3.5 px-4 text-amber-400">Recommended PoE Budget</th>
            </tr>
          </thead>
          <tbody>{matrix_rows_html}</tbody>
        </table>
      </div>
    </section>

    <!-- DEPLOYMENT CHECKLIST -->
    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Pro Surveillance NVR & PoE Deployment Checklist</h2>
        <span id="nvrBadge" class="text-xs font-bold bg-slate-800 text-sky-400 px-3 py-1 rounded-full">0 / 4 Completed</span>
      </div>
      <div class="space-y-3">{checklist_html}</div>
    </section>

    <!-- FAQ -->
    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-5">Frequently Asked Questions ({cam_name})</h2>
      <div class="space-y-4">{faqs_html}</div>
    </section>
  </main>

  <footer class="border-t border-slate-800 py-8 text-center text-xs text-slate-500 px-4">
    <p>© {datetime.now(timezone.utc).year} NVRStorageIndex. Independent IP Surveillance Storage & PoE Engineering Database. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const baseBitrate = {bitrate_mbps};
    const camPoeWatts = {poe_watts};
    const amzDomain = "{amz_domain}";
    const amzTag = "{amz_tag}";

    const camSlider = document.getElementById('camSlider');
    const daysSlider = document.getElementById('daysSlider');
    const codecSelect = document.getElementById('codecSelect');
    const modeSelect = document.getElementById('modeSelect');
    const camVal = document.getElementById('camVal');
    const daysVal = document.getElementById('daysVal');
    const tbOut = document.getElementById('tbOut');
    const bandwidthOut = document.getElementById('bandwidthOut');
    const poeWattsOut = document.getElementById('poeWattsOut');
    const hddAdviceBanner = document.getElementById('hddAdviceBanner');
    const dynamicHddBtn = document.getElementById('dynamicHddBtn');

    function recalculateNvr() {{
      const cams = parseInt(camSlider.value, 10);
      const days = parseInt(daysSlider.value, 10);
      const codecFactor = parseFloat(codecSelect.value);
      const modeFactor = parseFloat(modeSelect.value);

      camVal.textContent = cams;
      daysVal.textContent = days;

      const adjBitratePerCam = baseBitrate * codecFactor;
      const totalMbps = adjBitratePerCam * cams;
      const gbPerDayPerCam = adjBitratePerCam * 10.55 * modeFactor;
      const totalTb = (gbPerDayPerCam * cams * days * 1.10) / 1000.0;
      const recPoeWatts = Math.ceil((camPoeWatts * cams * 1.25) / 10) * 10;

      tbOut.textContent = totalTb.toFixed(1);
      bandwidthOut.textContent = `Total Stream: ${{totalMbps.toFixed(1)}} Mbps`;
      poeWattsOut.textContent = recPoeWatts;

      let driveSpec = "4TB";
      if (totalTb <= 3.6) driveSpec = "4TB";
      else if (totalTb <= 5.5) driveSpec = "6TB";
      else if (totalTb <= 7.5) driveSpec = "8TB";
      else if (totalTb <= 9.5) driveSpec = "10TB";
      else if (totalTb <= 11.5) driveSpec = "12TB";
      else if (totalTb <= 15.0) driveSpec = "16TB";
      else if (totalTb <= 19.0) driveSpec = "20TB";
      else driveSpec = "24TB";

      hddAdviceBanner.innerHTML = `💾 <strong>Recommended Drive Configuration:</strong> Requires <strong>${{totalTb.toFixed(1)}} TB</strong>. Install a <strong>${{driveSpec}} WD Purple Pro / Seagate SkyHawk AI Surveillance HDD</strong>.`;
      dynamicHddBtn.href = `https://${{amzDomain}}/s?k=WD+Purple+Pro+Seagate+SkyHawk+${{driveSpec}}+Surveillance+Hard+Drive&tag=${{amzTag}}`;
    }}

    camSlider.addEventListener('input', recalculateNvr);
    daysSlider.addEventListener('input', recalculateNvr);
    codecSelect.addEventListener('change', recalculateNvr);
    modeSelect.addEventListener('change', recalculateNvr);
    recalculateNvr();

    const checks = document.querySelectorAll('.nvr-check');
    const badge = document.getElementById('nvrBadge');
    checks.forEach(ch => {{
      ch.addEventListener('change', () => {{
        const done = Array.from(checks).filter(c => c.checked).length;
        badge.textContent = `${{done}} / ${{checks.length}} Completed`;
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)


def rebuild_portal_sitemap_and_rss(published, mon_cfg):
    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "WD+Purple+Pro+Surveillance+Hard+Drive"), mon_cfg)

    cards_html = ""
    for item in reversed(published):
        cards_html += f"""
        <a href="{item['slug']}.html" class="block bg-slate-900 border border-slate-800 hover:border-sky-500/60 rounded-xl p-5 transition group">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-black uppercase bg-sky-500 text-slate-950 px-2.5 py-0.5 rounded">{item.get('mp', 8)}MP | {item.get('bitrate_mbps', 6.5)} Mbps</span>
            <span class="text-xs text-slate-400">8-Cam 30d: {item.get('tb_8cam', 16.5)} TB</span>
          </div>
          <h2 class="text-base font-bold text-white group-hover:text-sky-400 transition">{item['camera_name']} NVR Storage Calculator</h2>
          <p class="text-xs text-slate-400 mt-2 line-clamp-2">{item['description']}</p>
          <span class="inline-block mt-4 text-xs font-extrabold text-sky-400">Calculate Hard Drive TB & PoE Watts →</span>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NVRStorageIndex — 4K PoE Security Camera NVR Hard Drive & Bitrate Calculator (2026)</title>
  <meta name="description" content="Calculate exact NVR surveillance hard drive capacity (TB), H.265 video bitrate (Mbps), and PoE switch wattage for Reolink, Ubiquiti UniFi, Hikvision, Amcrest, and Dahua cameras.">
  <link rel="canonical" href="{SITE_BASE_URL}/">
  <link rel="alternate" type="application/rss+xml" title="NVRStorageIndex RSS Feed" href="{SITE_BASE_URL}/rss.xml">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col">
  <header class="border-b border-slate-800 bg-slate-900/80 sticky top-0 z-30 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <div class="text-lg font-black text-white flex items-center gap-2">
        <span class="bg-sky-500 text-slate-950 px-2 py-0.5 rounded font-black">NVR</span>StorageIndex
      </div>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-sky-500 hover:bg-sky-400 text-slate-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Surveillance Hard Drives →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-12 flex-1 w-full">
    <div class="text-center max-w-2xl mx-auto mb-10">
      <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">PoE Security Camera NVR Storage & Bitrate Database</h1>
      <p class="text-slate-400 mt-3 text-base sm:text-lg">Select your IP security camera model below to calculate exact NVR hard drive Terabytes (TB) for 7–90 days, H.265 bandwidth, and PoE switch wattage.</p>
      <div class="mt-6">
        <input id="filterInput" type="text" placeholder="Search camera model (e.g. Reolink TrackMix, UniFi G5 Pro, Hikvision ColorVu, Amcrest 4K, 12MP...)" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-sky-500">
      </div>
    </div>

    <div id="camGrid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{cards_html}</div>
  </main>

  <footer class="border-t border-slate-800 py-8 text-center text-xs text-slate-500">
    <p>© {datetime.now(timezone.utc).year} NVRStorageIndex. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const filterInput = document.getElementById('filterInput');
    const cards = Array.from(document.getElementById('camGrid').children);
    filterInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      cards.forEach(c => {{
        c.style.display = c.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for item in published:
        urls_xml += f"""  <url>
    <loc>{SITE_BASE_URL}/{item['slug']}.html</loc>
    <lastmod>{item.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}</urlset>""")

    rss_items = ""
    for item in list(reversed(published))[:30]:
        rss_items += f"""    <item>
      <title>{item['title']}</title>
      <link>{SITE_BASE_URL}/{item['slug']}.html</link>
      <guid>{SITE_BASE_URL}/{item['slug']}.html</guid>
      <description>{item['description']}</description>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>NVRStorageIndex PoE Surveillance Storage Database</title>
    <link>{SITE_BASE_URL}/</link>
    <description>Interactive 4K PoE Camera NVR Hard Drive Capacity & Bitrate Calculators</description>
    <atom:link href="{SITE_BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
{rss_items}  </channel>
</rss>"""

    with open(os.path.join(DOCS_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def notify_search_engines(new_urls):
    if not SITE_BASE_URL or not new_urls:
        return
    parsed_host = urllib.parse.urlparse(SITE_BASE_URL).netloc
    payload = {
        "host": parsed_host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": new_urls
    }
    try:
        req = urllib.request.Request(
            "https://api.indexnow.org/indexnow",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"[INDEXNOW] Pushed {len(new_urls)} URLs (HTTP {resp.status})")
    except Exception as e:
        print(f"[WARN] IndexNow ping notice: {e}")

    try:
        hub_data = urllib.parse.urlencode({
            "hub.mode": "publish",
            "hub.url": f"{SITE_BASE_URL}/rss.xml"
        }).encode("utf-8")
        req_hub = urllib.request.Request(
            "https://pubsubhubbub.appspot.com/",
            data=hub_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req_hub, timeout=15) as resp_hub:
            print(f"[WEBSUB] Google PubSubHubbub ping status: {resp_hub.status}")
    except Exception as e:
        print(f"[WARN] WebSub ping notice: {e}")


def main():
    published = load_json(PUBLISHED_FILE, [])
    mon_cfg = load_json(MONETIZATION_FILE, {})
    published_slugs = {item["slug"] for item in published}

    candidates = []
    if CUSTOM_CAMERA:
        candidates.append((CUSTOM_CAMERA.strip(), 8, 6.5, 25, 11.5, "IEEE 802.3af PoE"))
    candidates.extend(SEED_CAMERAS)
    candidates.extend(discover_google_camera_queries())

    new_urls = []
    count = 0

    for cam_tuple in candidates:
        if count >= PAGES_PER_RUN:
            break
        cam_name = cam_tuple[0]
        slug = slugify(f"{cam_name}-nvr-storage-calculator")
        if slug in published_slugs:
            continue

        print(f"[ENGINE] Generating NVR storage & PoE calculator for: {cam_name}...")
        try:
            data = generate_nvr_data(cam_tuple)
            build_nvr_html_page(data, slug, mon_cfg)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sp = data.get("specs", {})
            b_mbps = round(safe_float(sp.get("default_bitrate_mbps", cam_tuple[2]), cam_tuple[2]), 1)
            tb_8 = round(safe_float(sp.get("recommended_8cam_30d_tb", 16.5), 16.5), 1)

            published.append({
                "camera_name": data.get("camera_name", cam_name),
                "slug": slug,
                "title": data.get("seo_title", f"{cam_name} NVR Storage Calculator"),
                "description": data.get("meta_description", ""),
                "mp": int(safe_float(sp.get("resolution_mp", cam_tuple[1]), cam_tuple[1])),
                "bitrate_mbps": b_mbps,
                "tb_8cam": tb_8,
                "date": today
            })
            published_slugs.add(slug)
            if SITE_BASE_URL:
                new_urls.append(f"{SITE_BASE_URL}/{slug}.html")
            count += 1
            time.sleep(2)
        except Exception as e:
            print(f"[ERROR] Failed building {cam_name}: {e}")

    save_json(PUBLISHED_FILE, published)
    rebuild_portal_sitemap_and_rss(published, mon_cfg)
    if new_urls and SITE_BASE_URL:
        new_urls.append(f"{SITE_BASE_URL}/")
        notify_search_engines(new_urls)
    print(f"[DONE] Published {count} new PoE camera NVR storage calculator pages.")


if __name__ == "__main__":
    main()
