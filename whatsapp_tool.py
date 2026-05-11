# ╔══════════════════════════════════════════════════════════╗
# ║         PhoneToMemo  PRO  v3.0                           ║
# ║  © 2026 PhoneToMemo. All Rights Reserved.                ║
# ║  For personal use only. Not affiliated with Meta.        ║
# ╚══════════════════════════════════════════════════════════╝

import subprocess, os, threading, time, math
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog

try:
    import psutil
    PSUTIL_OK = True
except ImportError:
    PSUTIL_OK = False

WHATSAPP_SOURCE  = "/sdcard/Android/media/com.whatsapp/WhatsApp/"
WHATSAPP_ACCOUNTS= "/sdcard/Android/media/com.whatsapp/WhatsApp/accounts/"
MEMU_DEST        = "/storage/emulated/0/WhatsApp"
MEMU_ACCOUNTS    = "/storage/emulated/0/WhatsApp/accounts"

C = {
    # Deep space background layers
    "bg":      "#050810",
    "hdr":     "#03050d",
    "panel":   "#080c18",
    "card":    "#0c1020",
    "dim":     "#101628",
    "border":  "#1a2240",
    "border2": "#1e2d55",
    # Accent palette — electric cyan-green
    "accent":  "#00f5c4",
    "accent2": "#00c4f0",
    "blue":    "#3d8bfe",
    "amber":   "#ffb020",
    "green":   "#1ddd7a",
    "red":     "#ff3b5c",
    "purple":  "#b57bff",
    "orange":  "#ff7c3b",
    # Text
    "text":    "#e8eeff",
    "muted":   "#3d4f72",
    "sub":     "#7a90bb",
    # Glow colors
    "glow":    "#00f5c420",
    "glow2":   "#3d8bfe18",
}
MONO = "Consolas"
SANS = "Segoe UI"
TITLE = "Segoe UI"
def fmono(s, b=False): return (MONO, s, "bold") if b else (MONO, s)
def fsans(s, b=False): return (SANS, s, "bold") if b else (SANS, s)
def ftitle(s, b=False): return (TITLE, s, "bold") if b else (TITLE, s)

def run_adb(cmd, device=None):
    full = (["adb", "-s", device] if device else ["adb"]) + cmd
    r = subprocess.run(full, capture_output=True, text=True)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def run_adb_priority(cmd, device=None):
    full = (["adb", "-s", device] if device else ["adb"]) + cmd
    proc = subprocess.Popen(full, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if PSUTIL_OK:
        try:
            p = psutil.Process(proc.pid)
            cls = getattr(psutil, "BELOW_NORMAL_PRIORITY_CLASS", None)
            p.nice(cls if cls else 10)
        except: pass
    out, err = proc.communicate()
    return out.strip(), err.strip(), proc.returncode

def adb_prop(device, prop):
    o, _, _ = run_adb(["shell", "getprop", prop], device=device)
    return o.strip() or "N/A"

def folder_size(path):
    total = 0
    if os.path.exists(path):
        for dp, _, fn in os.walk(path):
            for f in fn:
                try: total += os.path.getsize(os.path.join(dp, f))
                except: pass
    return total

def fmt_size(b):
    if b < 1024: return f"{b} B"
    elif b < 1048576: return f"{b/1024:.1f} KB"
    elif b < 1073741824: return f"{b/1048576:.1f} MB"
    else: return f"{b/1073741824:.2f} GB"

def get_phone_info(device):
    """Extract device info universally for any Android device."""

    def p(prop):
        return adb_prop(device, prop)

    def best(*props):
        for prop in props:
            v = p(prop).strip()
            if v and v not in ("N/A", "", "unknown", "0"):
                return v
        return "N/A"

    def is_codename(name):
        """Detect internal codenames like bluejay, cheetah, fogos_g, etc."""
        if not name or name == "N/A":
            return True
        # Codenames: all lowercase, no spaces, may have underscores or digits
        # Marketing names always have spaces (e.g. "Pixel 6a", "Galaxy S23")
        # Exception: single-word brands like "iPhone" — but Android won't have that
        if " " in name:
            return False  # Has space = marketing name
        if name.lower() == name and "_" in name:
            return True   # all_lower_with_underscore = codename
        if name.lower() == name and name.isalpha():
            return True   # alllowercase = codename (bluejay, cheetah, etc)
        if name.lower() == name and any(c.isdigit() for c in name) and len(name) < 8:
            return True   # short lowercase+digits = codename (e.g. "sm8450")
        return False

    # ── BRAND ─────────────────────────────────────────────────
    # Try all brand props — pick one with correct casing
    BRAND_NORMALIZE = {
        "oplus":    "Realme/OnePlus",
        "google":   "Google",
        "htc":      "HTC",
        "lge":      "LG",
        "zte":      "ZTE",
        "tcl":      "TCL",
        "bbk":      "Vivo",
        "qcom":     "",
        "msm":      "",
        "sprd":     "",
        "mtk":      "",
    }
    raw_brand = best(
        "ro.product.system.brand",
        "ro.product.vendor.brand",
        "ro.product.brand",
        "ro.product.odm.brand",
    )
    brand = BRAND_NORMALIZE.get(raw_brand.lower(), raw_brand)

    # ── MODEL CODE ────────────────────────────────────────────
    # ro.product.model usually has model code OR marketing name depending on brand
    model_code = best(
        "ro.product.model",
        "ro.product.odm.model",
        "ro.product.vendor.model",
        "ro.product.system.model",
    )

    # ── FULL MARKETING NAME ───────────────────────────────────
    # Strategy: try props in order, reject codenames, fall back to brand+model

    # Priority 1: Known model lookup table (most reliable for devices with no prop)
    MODEL_LOOKUP = {
        # iQOO
        "I2301": "iQOO Z7 Pro 5G",    "I2202": "iQOO 9 Pro",
        "I2012": "iQOO 7",             "I2105": "iQOO Z3",
        "I2010": "iQOO 3",             "I2209": "iQOO Z6 Pro 5G",
        "I2127": "iQOO Z5",            "I2206": "iQOO Z6 5G",
        "I2014": "iQOO 7 Legend",      "I2011": "iQOO Neo 5",
        "I2126": "iQOO Neo 6",         "I2227": "iQOO Z7",
        "I2229": "iQOO Neo 7",         "I2214": "iQOO 11",
    }

    full_name = MODEL_LOOKUP.get(model_code)

    # Priority 2: Scan all known marketing name props
    if not full_name:
        MARKETING_PROPS = [
            # Universal
            "ro.product.marketname",
            "ro.config.marketing_name",
            # Xiaomi / Redmi / POCO
            "ro.product.vendor.marketname",
            "ro.vendor.product.marketname",
            "ro.mi.product.marketname",
            "ro.product.mod_device",
            # Samsung
            "ro.product.odm.marketname",
            "ro.product.system.marketname",
            # iQOO / Vivo
            "ro.vivo.product.name",
            "persist.sys.device_marketname",
            "ro.vivo.market.name",
            # Realme / OnePlus / OPPO
            "ro.oppo.market.name",
            "ro.product.oppo.marketname",
            "persist.vendor.oplus.market.name",
            "ro.vendor.oplus.market.name",
            "ro.oppo.product.name",
            # Motorola
            "ro.mot.product.marketname",
            "ro.product.device.market_name",
            # Sony
            "ro.semc.ms_name",
            "ro.semc.product.name",
            # Huawei / Honor
            "ro.huawei.product.name",
            "ro.config.hw_device_name",
            # Nokia
            "ro.product.device.marketname",
            # Nothing Phone
            "ro.product.odm.name",
            # ASUS
            "ro.product.name",
            # General fallbacks
            "vendor.usb.product.string",
            "persist.vendor.radio.device.name",
        ]
        for prop in MARKETING_PROPS:
            v = p(prop).strip()
            if v and v not in ("N/A", "", model_code) and not is_codename(v):
                full_name = v
                break

    # Priority 3: Try odm.model — Motorola stores marketing name there
    if not full_name:
        odm = best("ro.product.odm.model", "ro.product.product.model")
        if odm != "N/A" and not is_codename(odm) and odm != model_code:
            full_name = odm

    # Priority 4: model_code itself if it looks like marketing name
    if not full_name and model_code != "N/A" and not is_codename(model_code):
        full_name = model_code  # e.g. "moto g45 5G", "Pixel 6a"

    # Priority 5: brand + model_code fallback
    if not full_name:
        if brand and brand not in ("N/A", ""):
            full_name = f"{brand} {model_code}".strip()
        else:
            full_name = model_code

    # Clean up — remove brand prefix duplication (e.g. "samsung Samsung S23")
    if full_name and brand and full_name.lower().startswith(brand.lower() + " "):
        pass  # already has brand prefix, keep as is
    elif full_name and brand and brand.lower() in full_name.lower():
        pass  # brand already in name
    elif full_name and brand and brand not in ("", "N/A", "Realme/OnePlus"):
        # Add brand if not present and name doesn't start with it
        if not full_name.lower().startswith(brand.lower()):
            # Only add for brands that always prefix names (Google, Samsung, etc.)
            PREFIX_BRANDS = {"Google", "Samsung", "Nokia", "HTC", "LG", "Sony"}
            if brand in PREFIX_BRANDS:
                full_name = f"{brand} {full_name}"

    # ── SERIAL ────────────────────────────────────────────────
    serial = device

    # ── IMEI ──────────────────────────────────────────────────
    def try_extract(raw):
        imei = ""
        for part in raw.split("'"):
            c = part.replace(".", "").strip()
            if c.isdigit() and len(c) > 3:
                imei += c
        return imei[:15] if len(imei) >= 15 else None

    def get_imei(call_id):
        raw, _, _ = run_adb(
            ["shell", "service", "call", "iphonesubinfo", call_id],
            device=device)
        val = try_extract(raw)
        if val:
            return val
        import re
        dots = len(re.findall(r"\.", raw))
        if dots >= 8:
            return "🔒 Protected (15-digit, needs root)"
        for prop in ["gsm.imei", "ril.imei", "persist.radio.imei"]:
            v, _, _ = run_adb(["shell", "getprop", prop], device=device)
            v = v.strip().strip("[]").split(",")[0].strip()
            if v.isdigit() and len(v) == 15:
                return v
        return "🔒 Protected (needs root)"

    imei1 = get_imei("1")
    imei2 = get_imei("3")

    return {
        "Full Name":  full_name,
        "Model No":   model_code,
        "Serial No":  serial,
        "IMEI 1":     imei1,
        "IMEI 2":     imei2,
    }


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PhoneToMemo  PRO  v3.0")
        self.geometry("1020x900")
        self.minsize(960,800)
        self.resizable(True, True)
        self.configure(bg=C["bg"])
        self.phone_id=None; self.memu_id=None
        self._cancel_flag=False; self.selected_folder=None
        self.external_path=None; self._timer_running=False; self._speed_running=False
        self._build()

    def _load_icon(self):
        """Load embedded PTM icon for window and taskbar."""
        try:
            import base64, tempfile, os
            ICO_B64 = "AAABAAEAEBAAAAAAIADGAwAAFgAAAIlQTkcNChoKAAAADUlIRFIAAAAQAAAAEAgGAAAAH/P/YQAAA41JREFUeJxNk+tP1XUAhz/fy+93zoFzP0WnMU5GVGAEyxa32iQwTGxTW/Um1haruVyzZnNZL6p36ptua0mRXVil0dYwnTnIRSqQDBwSWYrKgWOg4Ll4br/r9/ftRa36D57teR4CbbQKoAKS2pCmQN5y4PHZ8NkmoJmIx4FVTQpyBRe0qxxelYIEGYihAIxSSGHCyZtwChayBRtl5UX4zAJ2DyjI0xb4Y214v88NXySPshoNWWnDKVhwDANSWgT5n6JwmICv3AQqdWzv9rP6qlqx6YE22LSVOA6TfnWYHTo9JBLxKez6UAPibuQSCqhgBJnRMJIFgXe/VgNEqdPX1rZb1RVNfGbpNvXto2FoJjVe7kyJjppZXPrzhHfs4mAW4jxe3SKRzSkEciKA8d84/fmP553y0CNIGxVsYCokfpzwA0wFIaASlvPQ6izftj5pe+VFXMseQeOqg7j3bocjkyNouMOUDdX+9Ufn670Dp1zjs8uuxq4timlYsKVjr6QzxFjORC481+Nu738jPNrd/GsuvSwCmRylAQSB5ByJocTaU9fse+LpTvL5dx9oqypj2if7dxe8btV6/bVthb5D+7Kbuh4TxzY+GagsEhNIIoggKAAAEdiwQT0qcRxJ+r/63tO7/xvP5YUrJf1fHvQszF0JZHJ5/sqObnvwzJRT5o1QrCxKAOAAgFQSPFJOrheL5q6de92JhcWl2o61Iylw8FtuV0QoVNzX++2dFybOrtn+5ouSoUxirkgQBfgNZIAUsABVPtXTm9IvJSpKN7QlZo58/EXntAhhfkzf4YKGA4MP018mG3eODCfSj5Y7CFdhHpl/CMIRSOhKqoSxUkXV5OTZhtK72j+lqovbjqTU45Jk6Zqbqn4tqYJL6ArCEQDAvxr58LmtMnZrJ0nrUd43EuaTsyG4OEAJUNAh6iuz1rOt12W0dFFeXvrBaa3+CA332H+HZGdsvNRbygLhemfDfe2IRZvY8fMVSs9QiGgWsV5Yl7E31iUQX5ygJ6aPiUzuDPY+o4EH+f9SXm0AERNdj9/EHqxbIza3rCM39BZYDpdR7xg7PH5cOTl9Wv9szwrgU5GLqyAWIyiejEEaAnkm4GECvhodmLHwzlAIWzuaYdgleO/wKby1+SpQq2DpdzdYlsEbpCCSk/92NmxIQyBHBUqYgO9mHYlzAstpgvsbCbKGG1qOw6tQUHAQcEBhfwHSq63AmUDOsAAAAABJRU5ErkJggg=="
            ico_data = base64.b64decode(ICO_B64)
            # Write to temp file
            tmp = os.path.join(tempfile.gettempdir(), "phonetomemo.ico")
            with open(tmp, "wb") as f:
                f.write(ico_data)
            self.iconbitmap(tmp)
            # Also try PhotoImage for better quality on some systems
            try:
                from PIL import Image, ImageTk
                import io
                img = Image.open(io.BytesIO(ico_data))
                img = img.resize((32,32), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.iconphoto(True, photo)
                self._icon_photo = photo  # keep reference
            except:
                pass
        except Exception as e:
            pass  # Icon loading failure is non-critical

    def _build(self):
        self._hdr()

        # ── Scrollable middle area ──────────────────────────────
        self._scroll_container = tk.Frame(self, bg=C["bg"])
        self._scroll_container.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(self._scroll_container,
                                 bg=C["bg"], highlightthickness=0)
        self._scrollbar = ttk.Scrollbar(self._scroll_container,
                                        orient="vertical",
                                        command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._scrollbar.set)

        self._scrollbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        # Inner frame inside canvas — all sections go here
        self._inner = tk.Frame(self._canvas, bg=C["bg"])
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._inner, anchor="nw")

        # Make inner frame expand to canvas width
        def _on_canvas_resize(e):
            self._canvas.itemconfig(self._canvas_window, width=e.width)
        def _on_inner_resize(e):
            self._canvas.configure(scrollregion=self._canvas.bbox("all"))
            # Always keep scrolled to top on initial load
            if not hasattr(self, "_initial_scroll_done"):
                self._canvas.yview_moveto(0)
                self._initial_scroll_done = True

        self._canvas.bind("<Configure>", _on_canvas_resize)
        self._inner.bind("<Configure>", _on_inner_resize)

        # Mouse wheel scrolling
        self._canvas.bind_all("<MouseWheel>",
            lambda e: self._canvas.yview_scroll(
                int(-1*(e.delta/120)), "units"))

        # Override pack target to inner frame
        self._pack_target = self._inner

        self._devices_section()
        self._device_info_section()
        self._source_section()
        self._folder_section()
        self._action_row()
        self._progress_section()
        self._console_section()
        self._footer()
        # Force canvas to recalculate scroll region
        self._inner.update_idletasks()
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        self._log("PhoneToMemo PRO v3.0 ready.  Click  SCAN DEVICES  to begin.\n","head")
        self.after(100, lambda: self._canvas.yview_moveto(0))
        # Scroll canvas to top after building
        self.after(100, lambda: self._canvas.yview_moveto(0))
        # Scroll canvas to top after build
        self.after(100, lambda: self._canvas.yview_moveto(0))

    def _hdr(self):
        # Top gradient accent bar — 3 color segments
        bar = tk.Frame(self, bg=C["hdr"], height=3)
        bar.pack(fill="x")
        for col, w in [(C["accent"],200),(C["accent2"],200),(C["blue"],200),("#1a2240",1000)]:
            tk.Frame(bar, bg=col, height=3, width=w).pack(side="left")

        h = tk.Frame(self, bg=C["hdr"])
        h.pack(fill="x")

        # Hexagon logo with glow ring
        cv = tk.Canvas(h, width=56, height=56, bg=C["hdr"], highlightthickness=0)
        cv.pack(side="left", padx=(20,12), pady=12)
        # Outer glow ring
        pts_outer = []
        for i in range(6):
            a = math.pi*(60*i-90)/180
            pts_outer += [28+24*math.cos(a), 28+24*math.sin(a)]
        cv.create_polygon(pts_outer, fill="#001f18", outline=C["accent"], width=1)
        # Inner hex
        pts = []
        for i in range(6):
            a = math.pi*(60*i-90)/180
            pts += [28+18*math.cos(a), 28+18*math.sin(a)]
        cv.create_polygon(pts, fill=C["accent"], outline="")
        cv.create_text(28, 28, text="PTM", font=fmono(8,True), fill=C["hdr"])

        # Title block
        tf = tk.Frame(h, bg=C["hdr"])
        tf.pack(side="left", pady=12)
        tk.Label(tf, text="PhoneToMemo",
                 font=(TITLE, 20, "bold"), bg=C["hdr"],
                 fg=C["text"]).pack(anchor="w")
        sub_row = tk.Frame(tf, bg=C["hdr"])
        sub_row.pack(anchor="w")
        tk.Label(sub_row, text="PRO", font=fmono(7,True),
                 bg=C["accent"], fg=C["hdr"],
                 padx=5, pady=1).pack(side="left", padx=(0,6))
        tk.Label(sub_row, text="EDITION  v3.0   ·   ADB TRANSFER TOOL",
                 font=fmono(7), bg=C["hdr"], fg=C["muted"]).pack(side="left")

        # Badges
        br = tk.Frame(h, bg=C["hdr"])
        br.pack(side="right", padx=18, pady=16)
        badges = [
            ("ADB",    C["accent"],  C["hdr"]),
            ("PSUTIL" if PSUTIL_OK else "NO PSUTIL",
             C["blue"] if PSUTIL_OK else C["muted"], "white"),
            ("PRO",    C["amber"],   C["hdr"]),
            ("v3.0",   C["purple"],  "white"),
        ]
        for txt, bg, fg in badges:
            f = tk.Frame(br, bg=bg, padx=1, pady=1)
            f.pack(side="left", padx=3)
            tk.Label(f, text=f" {txt} ", font=fmono(7,True),
                     bg=bg, fg=fg, padx=7, pady=3).pack()

        # Separator with accent gradient
        sep = tk.Frame(self, bg=C["hdr"], height=1)
        sep.pack(fill="x")
        tk.Frame(sep, bg=C["accent"], height=1, width=300).place(x=0, y=0)

    def _sec(self,text):
        p=getattr(self,"_pack_target",self)
        row=tk.Frame(p,bg=C["bg"]); row.pack(fill="x",padx=16,pady=(12,4))
        # Glowing left bar
        tk.Frame(row,bg=C["accent"],width=3,height=14).pack(side="left",padx=(0,8))
        tk.Label(row,text=text,font=fmono(7,True),bg=C["bg"],
                 fg=C["accent"]).pack(side="left")
        # Dotted separator line
        tk.Frame(row,bg=C["border2"],height=1).pack(
            side="left",fill="x",expand=True,padx=(12,0))

    def _card(self):
        p=getattr(self,"_pack_target",self)
        # Outer glow frame
        outer=tk.Frame(p,bg=C["border2"],padx=1,pady=1)
        outer.pack(fill="x",padx=16,pady=(0,4))
        f=tk.Frame(outer,bg=C["card"])
        f.pack(fill="x")
        return f

    def _devices_section(self):
        self._sec("CONNECTED DEVICES")
        card=self._card()
        row=tk.Frame(card,bg=C["card"]); row.pack(fill="x",padx=12,pady=10)

        self.ptile=tk.Frame(row,bg=C["dim"],highlightbackground=C["border2"],highlightthickness=1)
        self.ptile.pack(side="left",fill="x",expand=True,padx=(0,8))
        ph=tk.Frame(self.ptile,bg=C["dim"]); ph.pack(fill="x",padx=10,pady=8)
        tk.Label(ph,text="📱  PHONE",font=fmono(7,True),bg=C["dim"],fg=C["muted"]).pack(anchor="w")
        self.lbl_phone=tk.Label(ph,text="Not detected",font=fmono(10,True),bg=C["dim"],fg=C["red"])
        self.lbl_phone.pack(anchor="w",pady=(2,0))
        self.lbl_phone_sub=tk.Label(ph,text="—",font=fmono(8),bg=C["dim"],fg=C["muted"])
        self.lbl_phone_sub.pack(anchor="w")

        tk.Frame(row,bg=C["border2"],width=1).pack(side="left",fill="y")

        self.mtile=tk.Frame(row,bg=C["dim"],highlightbackground=C["border2"],highlightthickness=1)
        self.mtile.pack(side="left",fill="x",expand=True,padx=(8,0))
        mh=tk.Frame(self.mtile,bg=C["dim"]); mh.pack(fill="x",padx=10,pady=8)
        tk.Label(mh,text="🖥️  MEmu EMULATOR",font=fmono(7,True),bg=C["dim"],fg=C["muted"]).pack(anchor="w")
        self.lbl_memu=tk.Label(mh,text="Not detected",font=fmono(10,True),bg=C["dim"],fg=C["red"])
        self.lbl_memu.pack(anchor="w",pady=(2,0))
        self.lbl_memu_sub=tk.Label(mh,text="—",font=fmono(8),bg=C["dim"],fg=C["muted"])
        self.lbl_memu_sub.pack(anchor="w")

        sr=tk.Frame(card,bg=C["card"]); sr.pack(fill="x",padx=12,pady=(0,12))
        scan_frame=tk.Frame(sr,bg=C["green"],padx=1,pady=1)
        scan_frame.pack(side="left")
        self.btn_scan=tk.Button(scan_frame,text="⟳   SCAN DEVICES",
            font=fsans(10,True),bg=C["green"],fg=C["hdr"],
            activebackground="#25ee8a",relief="flat",
            padx=22,pady=8,cursor="hand2",command=self._scan)
        self.btn_scan.pack()
        self.lbl_scan_status=tk.Label(sr,text="   Click Scan to detect Phone & MEmu",
            font=fmono(8),bg=C["card"],fg=C["muted"])
        self.lbl_scan_status.pack(side="left",padx=12)

    def _device_info_section(self):
        p2=getattr(self,"_pack_target",self)
        sep=tk.Frame(p2,bg=C["border"],height=1); sep.pack(fill="x",padx=16)
        hrow=tk.Frame(p2,bg=C["bg"]); hrow.pack(fill="x",padx=16,pady=(6,3))
        tk.Frame(hrow,bg=C["blue"],width=3,height=12).pack(side="left",padx=(0,7))
        tk.Label(hrow,text="DEVICE INFORMATION",font=fmono(7,True),bg=C["bg"],fg=C["blue"]).pack(side="left")
        tk.Frame(hrow,bg=C["border"],height=1).pack(side="left",fill="x",expand=True,padx=(10,0))
        p=getattr(self,"_pack_target",self)
        self.info_outer=tk.Frame(p,bg=C["card"],highlightbackground=C["border"],highlightthickness=1)
        self.info_outer.pack(fill="x",padx=16,pady=(0,4))
        # content_frame is what we rebuild each time — never touch info_outer itself
        self.info_content=tk.Frame(self.info_outer,bg=C["card"])
        self.info_content.pack(fill="x",padx=8,pady=8)
        tk.Label(self.info_content,
            text="  Scan devices to load phone details here  ",
            font=fmono(8),bg=C["card"],fg=C["muted"],pady=12).pack(anchor="w")

    def _show_phone_info(self,info):
        # Rebuild info_content completely
        for w in self.info_outer.winfo_children():
            w.destroy()

        wrapper=tk.Frame(self.info_outer,bg=C["card"])
        wrapper.pack(fill="x",padx=8,pady=8)

        ICONS={"Full Name":"📱","Model No":"🔖","Serial No":"🔢",
               "IMEI 1":"📡","IMEI 2":"📡"}

        items=list(info.items())
        for c,(key,val) in enumerate(items):
            wrapper.columnconfigure(c,weight=1)
            hl  = key in {"IMEI 1","IMEI 2"}
            acc = C["accent"] if hl else C["blue"]
            bdr = C["accent"] if hl else C["border2"]

            cell=tk.Frame(wrapper,bg=C["dim"],
                          highlightbackground=bdr,highlightthickness=1)
            cell.grid(row=0,column=c,padx=4,pady=4,sticky="nsew")

            icon=ICONS.get(key,"•")
            # Label key
            tk.Label(cell,text=f"{icon}  {key.upper()}",
                     font=fmono(6,True),bg=C["dim"],fg=acc,
                     padx=12,pady=6).pack(anchor="w",pady=(6,0))
            # Label value — no tuple pady in constructor
            val_color=C["accent"] if hl else C["text"]
            val_font =fmono(11,True) if hl else fmono(10,True)
            tk.Label(cell,text=val or "N/A",
                     font=val_font,bg=C["dim"],fg=val_color,
                     wraplength=200,justify="left",
                     padx=12,pady=6).pack(anchor="w",pady=(0,8))

        self.info_outer.update_idletasks()

    def _source_section(self):
        self._sec("SOURCE PATH  (Phone)")
        card = self._card()
        row  = tk.Frame(card, bg=C["card"])
        row.pack(fill="x", padx=12, pady=10)

        # Source path — only set via Browse, no manual typing
        self.source_var = tk.StringVar(value="")

        self.lbl_source_path = tk.Label(row,
            text="  No source selected — Click Browse ADB",
            font=fmono(9), bg=C["dim"], fg=C["muted"],
            anchor="w", padx=10, pady=7)
        self.lbl_source_path.pack(side="left", fill="x", expand=True, padx=(0,10))

        tk.Button(row, text="✕  Clear",
            font=fmono(8), bg=C["dim"], fg=C["muted"],
            activebackground=C["border"], relief="flat",
            padx=10, pady=7, cursor="hand2",
            command=self._clear_source).pack(side="right", padx=(4,0))

        tk.Button(row, text="📂  Browse ADB",
            font=fsans(10,True), bg=C["blue"], fg="white",
            activebackground="#3b72d9", relief="flat",
            padx=16, pady=7, cursor="hand2",
            command=self._browse_source).pack(side="right")

    def _browse_source(self):
        """List directories on phone via ADB and let user pick."""
        if not self.phone_id:
            messagebox.showwarning("No Phone", "Please scan devices first.")
            return
        # Ask user to type the path they want to browse
        current = self.source_var.get().strip().rstrip("/")
        # Show a simple dialog to navigate
        win = tk.Toplevel(self)
        win.title("Browse Phone — ADB")
        win.geometry("620x460")
        win.configure(bg=C["bg"])
        win.grab_set()

        tk.Label(win, text="BROWSE PHONE STORAGE",
                 font=fmono(8,True), bg=C["bg"], fg=C["accent"]).pack(pady=(12,4))

        path_var = tk.StringVar(value=current or "/sdcard")
        path_row = tk.Frame(win, bg=C["bg"]); path_row.pack(fill="x",padx=12,pady=4)
        path_entry = tk.Entry(path_row, textvariable=path_var,
                              font=fmono(9), bg=C["dim"], fg=C["text"],
                              insertbackground=C["accent"], relief="flat")
        path_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0,6))
        tk.Button(path_row, text="Go", font=fmono(9,True),
                  bg=C["blue"], fg="white", relief="flat", padx=12, pady=4,
                  command=lambda: _load(path_var.get().strip())).pack(side="left")

        listbox = tk.Listbox(win, font=fmono(10), bg=C["dim"], fg=C["text"],
                             selectbackground=C["accent"], selectforeground=C["hdr"],
                             relief="flat", bd=0, activestyle="none")
        listbox.pack(fill="both", expand=True, padx=12, pady=6)

        status = tk.Label(win, text="Loading...", font=fmono(7),
                          bg=C["bg"], fg=C["muted"])
        status.pack(pady=(0,4))

        btn_row = tk.Frame(win, bg=C["bg"]); btn_row.pack(pady=8)
        tk.Button(btn_row, text="⬆  Up", font=fmono(9,True),
                  bg=C["dim"], fg=C["sub"], relief="flat", padx=14, pady=6,
                  command=lambda: _go_up()).pack(side="left", padx=4)
        tk.Button(btn_row, text="✓  Select This Folder", font=fsans(10,True),
                  bg=C["green"], fg=C["hdr"], relief="flat", padx=18, pady=6,
                  command=lambda: _select()).pack(side="left", padx=4)
        tk.Button(btn_row, text="✕  Cancel", font=fmono(9),
                  bg=C["red"], fg="white", relief="flat", padx=14, pady=6,
                  command=win.destroy).pack(side="left", padx=4)

        def _load(path):
            path = path.rstrip("/") or "/sdcard"
            path_var.set(path)
            listbox.delete(0,"end")
            listbox.insert("end","  ⏳  Loading…")
            status.config(text="Loading…", fg=C["muted"])
            win.update_idletasks()
            def _do():
                # Use ls -la and filter directories (lines starting with d)
                out, _, _ = run_adb(
                    ["shell", "ls", "-la", path + "/"],
                    device=self.phone_id)
                dirs = []
                if out:
                    for line in out.splitlines():
                        parts = line.split()
                        # drwx... format — first char is 'd'
                        if parts and parts[0].startswith("d"):
                            name = parts[-1]
                            if name not in (".", ".."):
                                dirs.append(name)
                # Fallback: plain ls if -la gave nothing
                if not dirs:
                    out2, _, _ = run_adb(
                        ["shell", "ls", path + "/"],
                        device=self.phone_id)
                    if out2:
                        # Try each entry — check if it's a directory
                        for name in out2.splitlines():
                            name = name.strip()
                            if name and not name.startswith("ls:"):
                                _, _, rc = run_adb(
                                    ["shell", "test", "-d",
                                     f"{path}/{name}"],
                                    device=self.phone_id)
                                if rc == 0:
                                    dirs.append(name)
                win.after(0, lambda d=dirs, p=path: _populate(d, p))
            threading.Thread(target=_do, daemon=True).start()

        def _populate(dirs, path):
            listbox.delete(0,"end")
            if not dirs:
                listbox.insert("end","  (no subfolders found)")
                status.config(text=f"Path: {path}  |  No subfolders", fg=C["muted"])
            else:
                for d in sorted(dirs):
                    listbox.insert("end", f"  📁  {d}")
                status.config(text=f"Path: {path}  |  {len(dirs)} folder(s)", fg=C["sub"])

        def _go_up():
            p = path_var.get().rstrip("/")
            parent = "/".join(p.split("/")[:-1]) or "/"
            _load(parent)

        def _on_double(e):
            sel = listbox.curselection()
            if sel:
                name = listbox.get(sel[0]).strip().lstrip("📁").strip()
                _load(f"{path_var.get().rstrip('/')}/{name}")
        listbox.bind("<Double-Button-1>", _on_double)

        def _select():
            path = path_var.get().rstrip("/") + "/"
            self.source_var.set(path)
            self.lbl_source_path.config(text=f"  {path}", fg=C["green"])
            self._log(f"Source path → {path}", "ok")
            win.destroy()

        _load(path_var.get())

    def _clear_source(self):
        self.source_var.set("")
        self.lbl_source_path.config(
            text="  No source selected — Click Browse ADB",
            fg=C["muted"])
        self._log("Source path cleared", "warn")

    def _folder_section(self):
        self._sec("BACKUP DESTINATION")
        card=self._card()
        row=tk.Frame(card,bg=C["card"]); row.pack(fill="x",padx=12,pady=10)
        self.lbl_path=tk.Label(row,text="  No folder selected — Click BROWSE",
            font=fmono(9),bg=C["dim"],fg=C["muted"],anchor="w",padx=10,pady=7)
        self.lbl_path.pack(side="left",fill="x",expand=True,padx=(0,10))
        tk.Button(row,text="✕  Clear",font=fmono(8),bg=C["dim"],fg=C["muted"],
            activebackground=C["border"],relief="flat",padx=10,pady=7,cursor="hand2",
            command=self._clear_folder).pack(side="right",padx=(6,0))
        tk.Button(row,text="📂   BROWSE",font=fsans(10,True),bg=C["blue"],fg="white",
            activebackground="#3b72d9",relief="flat",padx=16,pady=7,cursor="hand2",
            command=self._browse_folder).pack(side="right")

    def _action_row(self):
        p=getattr(self,"_pack_target",self)
        row=tk.Frame(p,bg=C["bg"]); row.pack(fill="x",padx=16,pady=12)

        # START BACKUP — glowing blue button
        start_frame=tk.Frame(row,bg=C["blue"],padx=2,pady=2)
        start_frame.pack(side="left",padx=(0,10))
        self.btn_backup=tk.Button(start_frame,text="▶   START BACKUP",
            font=fsans(11,True),bg=C["blue"],fg="white",
            activebackground="#5a9eff",relief="flat",
            padx=26,pady=10,cursor="hand2",state="disabled",
            command=self._start_backup)
        self.btn_backup.pack()

        # CLEAR LOG
        tk.Button(row,text="⌫  CLEAR LOG",font=fmono(9,True),
            bg=C["dim"],fg=C["sub"],activebackground=C["border2"],
            relief="flat",padx=16,pady=10,cursor="hand2",
            command=self._clear_log).pack(side="left",padx=(0,10))

        # CANCEL — red
        cancel_frame=tk.Frame(row,bg=C["red"],padx=1,pady=1)
        cancel_frame.pack(side="left")
        self.btn_cancel=tk.Button(cancel_frame,text="✕  CANCEL",
            font=fmono(9,True),bg=C["red"],fg="white",
            activebackground="#ff5577",relief="flat",
            padx=16,pady=10,cursor="hand2",state="disabled",
            command=self._cancel_backup)
        self.btn_cancel.pack()

    def _progress_section(self):
        card=self._card()
        pw=tk.Frame(card,bg=C["card"]); pw.pack(fill="x",padx=12,pady=(10,6))
        style=ttk.Style(); style.theme_use("default")
        style.configure("Pro.Horizontal.TProgressbar",
            troughcolor=C["dim"], background=C["accent"],
            thickness=14, bordercolor=C["border2"],
            lightcolor=C["accent"], darkcolor=C["accent2"])
        self.pb=ttk.Progressbar(pw,mode="determinate",maximum=100,value=0,
            style="Pro.Horizontal.TProgressbar")
        self.pb.pack(fill="x", pady=(4,0))
        sr=tk.Frame(card,bg=C["card"]); sr.pack(fill="x",padx=12,pady=(0,10))

        def _stat_box(parent, label, init, color, side="left"):
            f=tk.Frame(parent,bg=C["dim"],
                       highlightbackground=C["border2"],highlightthickness=1)
            f.pack(side=side,padx=(0,6),pady=4)
            tk.Label(f,text=label,font=fmono(6,True),
                     bg=C["dim"],fg=C["muted"],padx=14,pady=4).pack(anchor="w",pady=(6,0))
            lbl=tk.Label(f,text=init,font=fmono(13,True),
                         bg=C["dim"],fg=color,padx=14,pady=6)
            lbl.pack(anchor="w",pady=(2,8))
            return lbl

        self.lbl_speed   = _stat_box(sr,"⚡ SPEED",  "— MB/s", C["accent"])
        self.lbl_elapsed = _stat_box(sr,"⏱ ELAPSED", "00:00",  C["blue"])
        self.lbl_pct     = _stat_box(sr,"📊 PROGRESS","0%",     C["amber"])

    def _console_section(self):
        self._sec("CONSOLE OUTPUT")
        p=getattr(self,"_pack_target",self)
        # Console border frame with accent top line
        con_outer=tk.Frame(p,bg=C["accent"],padx=1,pady=0)
        con_outer.pack(fill="both",expand=True,padx=16,pady=(2,8))
        tk.Frame(con_outer,bg=C["accent"],height=2).pack(fill="x")
        self.log=scrolledtext.ScrolledText(con_outer,font=fmono(9),
            bg="#060a16",fg=C["text"],
            insertbackground=C["accent"],relief="flat",bd=0,
            state="disabled", selectbackground=C["border2"],
            height=12, padx=10, pady=8)
        self.log.pack(fill="both",expand=True)
        self.log.tag_config("ok",   foreground=C["green"])
        self.log.tag_config("err",  foreground=C["red"])
        self.log.tag_config("warn", foreground=C["amber"])
        self.log.tag_config("info", foreground=C["accent2"])
        self.log.tag_config("head", foreground=C["accent"],
                            font=fmono(9,True))
        self.log.tag_config("dim",  foreground=C["muted"])
        self.log.tag_config("ts",   foreground="#2a3a5a")

    def _footer(self):
        p=getattr(self,"_pack_target",self)
        # Gradient-style footer bar
        foot=tk.Frame(p,bg=C["hdr"])
        foot.pack(fill="x",pady=(8,0))
        # Top accent line
        bar=tk.Frame(foot,bg=C["hdr"],height=2)
        bar.pack(fill="x")
        for col,w in [(C["accent"],150),(C["accent2"],100),(C["blue"],100),
                      (C["border"],2000)]:
            tk.Frame(bar,bg=col,height=2,width=w).pack(side="left")
        # Footer text row
        txt_row=tk.Frame(foot,bg=C["hdr"])
        txt_row.pack(fill="x",padx=16,pady=6)
        tk.Label(txt_row,text="🔌  USB Debugging ON",
                 font=fmono(7),bg=C["hdr"],fg=C["muted"]).pack(side="left",padx=(0,16))
        tk.Label(txt_row,text="🖥️  MEmu fully loaded",
                 font=fmono(7),bg=C["hdr"],fg=C["muted"]).pack(side="left",padx=(0,16))
        tk.Label(txt_row,text="PhoneToMemo PRO v3.0  ©2026",
                 font=fmono(7,True),bg=C["hdr"],fg=C["border2"]).pack(side="right")

    def _log(self,msg,tag="info"):
        self.log.config(state="normal")
        ts=datetime.now().strftime("%H:%M:%S")
        self.log.insert("end",f"[{ts}] ","ts")
        self.log.insert("end",msg+"\n",tag)
        self.log.see("end")
        self.log.config(state="disabled")

    def _clear_log(self):
        self.log.config(state="normal"); self.log.delete("1.0","end"); self.log.config(state="disabled")

    def _browse_folder(self):
        folder=filedialog.askdirectory(title="Select Backup Destination",initialdir=os.path.expanduser("~"))
        if folder:
            self.selected_folder=folder
            self.lbl_path.config(text=f"  {folder}",fg=C["green"])
            self._log(f"Backup folder → {folder}","ok")
            if self.phone_id and self.memu_id: self.btn_backup.config(state="normal")

    def _clear_folder(self):
        self.selected_folder=None
        self.lbl_path.config(text="  No folder selected — Click BROWSE",fg=C["muted"])
        self.btn_backup.config(state="disabled"); self._log("Folder cleared","warn")

    def _scan(self):
        self.lbl_scan_status.config(text="   Scanning…",fg=C["amber"])
        self.btn_scan.config(state="disabled")
        self._log("━"*54,"head"); self._log("Scanning ADB devices…","info")
        threading.Thread(target=self._do_scan,daemon=True).start()

    def _do_scan(self):
        stdout,_,_=run_adb(["devices"])
        devs=[l.split()[0] for l in stdout.splitlines()[1:] if "device" in l and "offline" not in l]
        self.phone_id=next((d for d in devs if "." not in d and not d.startswith("emulator")),None)
        self.memu_id =next((d for d in devs if "127.0.0.1" in d or d.startswith("emulator")),None)
        def ui():
            self.lbl_phone.config(text=self.phone_id or "Not detected",
                fg=C["green"] if self.phone_id else C["red"])
            self.lbl_memu.config(text=self.memu_id or "Not detected",
                fg=C["green"] if self.memu_id else C["red"])
            if self.phone_id: self.lbl_phone_sub.config(text="USB connected  •  ADB authorized",fg=C["sub"])
            if self.memu_id:  self.lbl_memu_sub.config(text="Emulator running  •  ADB connected",fg=C["sub"])
            self._log(f"Phone  →  {self.phone_id or 'Not found'}","ok" if self.phone_id else "err")
            self._log(f"MEmu   →  {self.memu_id  or 'Not found'}","ok" if self.memu_id  else "err")
            if self.phone_id and self.memu_id:
                if self.selected_folder: self.btn_backup.config(state="normal")
                self.lbl_scan_status.config(text="   ✓  Both devices ready!",fg=C["green"])
                self._log("Both detected — fetching device info…","ok")
                threading.Thread(target=self._fetch_info,daemon=True).start()
            else:
                self.btn_backup.config(state="disabled")
                self.lbl_scan_status.config(text="   ⚠  Connect phone + open MEmu, then scan again",fg=C["amber"])
            self.btn_scan.config(state="normal")
        self.after(0,ui)

    def _fetch_info(self):
        try:
            info=get_phone_info(self.phone_id)
        except Exception as e:
            self.after(0,lambda: self._log(f"Device info error: {e}","err"))
            return
        name   = info.get("Full Name","")
        model  = info.get("Model No","")
        serial = info.get("Serial No","")
        imei1  = info.get("IMEI 1","")
        # Update UI
        self.after(0,lambda i=info: self._show_phone_info(i))
        self.after(100,lambda: self.lbl_phone_sub.config(
            text=f"{name}  •  S/N: {serial}",fg=C["sub"]))
        self.after(200,lambda: self._log(
            f"Device: {name}  |  Model: {model}  |  S/N: {serial}  |  IMEI: {imei1}","ok"))

    def _start_backup(self):
        if not self.selected_folder:
            messagebox.showwarning("No Folder","Please select a backup destination folder first.")
            return
        self._cancel_flag=False; self._backup_folder=self.selected_folder
        src = self.source_var.get().strip()
        self._source_path = src if src.endswith("/") else src + "/"
        self.btn_backup.config(state="disabled"); self.btn_cancel.config(state="normal")
        self.pb["value"]=0; self.lbl_pct.config(text="0%")
        self.lbl_speed.config(text="— MB/s",fg=C["accent"])
        self.lbl_elapsed.config(text="00:00",fg=C["blue"])
        self._start_time=time.time(); self._timer_running=True
        threading.Thread(target=self._update_timer,daemon=True).start()
        threading.Thread(target=self._run_backup,   daemon=True).start()

    def _cancel_backup(self):
        if messagebox.askyesno("Cancel Backup","Cancel the ongoing backup?"):
            self._cancel_flag=True; self._timer_running=False; self._speed_running=False
            self._log("BACKUP CANCELLED BY USER","err"); self._set_progress(0)
            self.lbl_elapsed.config(text="cancelled",fg=C["red"])
            self.btn_cancel.config(state="disabled"); self.btn_backup.config(state="normal")

    def _update_timer(self):
        while self._timer_running:
            e=int(time.time()-self._start_time); m,s=divmod(e,60)
            self.after(0,lambda m=m,s=s: self.lbl_elapsed.config(text=f"{m:02d}:{s:02d}",fg=C["blue"]))
            time.sleep(1)

    def _start_speed_monitor(self,path):
        self._speed_running=True
        def _mon():
            prev,pt=0,time.time()
            smooth_spd=0.0
            while self._speed_running:
                time.sleep(1)
                try:
                    cur=folder_size(path); ct=time.time()
                    db=cur-prev; dt=ct-pt
                    if dt>0 and db>0:
                        raw_spd=(db/1048576)/dt
                        # Cap at realistic USB 3.0 max ~600 MB/s
                        raw_spd=min(raw_spd, 600.0)
                        # Smooth with exponential moving average
                        smooth_spd=0.7*raw_spd + 0.3*smooth_spd if smooth_spd>0 else raw_spd
                        self.after(0,lambda s=smooth_spd: self.lbl_speed.config(
                            text=f"{s:.1f} MB/s", fg=C["accent"]))
                    prev,pt=cur,ct
                except: pass
        threading.Thread(target=_mon,daemon=True).start()

    def _stop_speed_monitor(self): self._speed_running=False

    def _start_device_monitor(self):
        """Monitor phone connection every 3 seconds during backup."""
        self._device_monitor_running = True
        def _monitor():
            consecutive_fails = 0
            while self._device_monitor_running:
                time.sleep(3)
                if not self._device_monitor_running:
                    break
                # Check if phone is still in adb devices list
                out, _, _ = run_adb(["devices"])
                connected = any(
                    self.phone_id in line and "device" in line
                    for line in out.splitlines()
                )
                if not connected:
                    consecutive_fails += 1
                    if consecutive_fails == 1:
                        self.after(0, lambda: self._log(
                            "⚠  WARNING: Phone not detected — checking again…", "warn"))
                    elif consecutive_fails >= 2:
                        self._device_monitor_running = False
                        self._cancel_flag = True
                        self.after(0, self._on_device_disconnected)
                        break
                else:
                    consecutive_fails = 0  # reset on successful check
        threading.Thread(target=_monitor, daemon=True).start()

    def _stop_device_monitor(self):
        self._device_monitor_running = False

    def _on_device_disconnected(self):
        """Called when phone disconnects during backup."""
        self._timer_running  = False
        self._speed_running  = False
        self._log("━"*54, "err")
        self._log("🔌  PHONE DISCONNECTED DURING BACKUP!", "err")
        self._log("   The backup process was interrupted.", "err")
        self._log("   Please reconnect the phone and try again.", "warn")
        self._log("━"*54, "err")
        self.lbl_speed.config(text="Disconnected!", fg=C["red"])
        self.btn_backup.config(state="normal")
        self.btn_cancel.config(state="disabled")
        # Flash the phone tile red
        self.lbl_phone.config(text="📵  DISCONNECTED", fg=C["red"])
        self.lbl_phone_sub.config(text="Phone lost during backup — reconnect USB", fg=C["red"])
        messagebox.showerror("📵  Phone Disconnected!",
            "The phone was disconnected during backup!\n\n"
            "The backup is INCOMPLETE.\n"
            "Please reconnect the USB cable and start again.")

    def _set_progress(self,v):
        self.after(0,lambda: self.pb.config(value=v))
        self.after(0,lambda: self.lbl_pct.config(text=f"{int(v)}%"))

    def _push_subfolders(self, wa_local, memu_dest, label=""):
        """Push Backups, Databases, Media from wa_local into memu_dest."""
        SUBS = ["Backups", "Databases", "Media"]
        for sub in SUBS:
            if self._cancel_flag: return False
            local_sub = os.path.join(wa_local, sub)
            if not os.path.exists(local_sub):
                self._log(f"  ⚠  {label}{sub} not found — skipping", "warn")
                continue
            self._log(f"  → Pushing  {label}{sub}…", "info")
            run_adb(["shell","rm","-rf",f"{memu_dest}/{sub}"], device=self.memu_id)
            run_adb(["shell","mkdir","-p", memu_dest],          device=self.memu_id)
            self._start_speed_monitor(local_sub)
            ts = time.time()
            _, err, code = run_adb_priority(
                ["push", local_sub, f"{memu_dest}/{sub}"],
                device=self.memu_id)
            elapsed = time.time() - ts
            self._stop_speed_monitor()
            if code == 0:
                self._log(f"  ✓  {label}{sub} — Done!  ({elapsed:.1f}s)", "ok")
            else:
                self._log(f"  ✗  {label}{sub} failed: {err}", "err")
        return True

    def _run_backup(self):
        try:
            self._log("━"*54,"head"); self._log("▶  BACKUP STARTED","head"); self._log("━"*54,"head")
            os.makedirs(self._backup_folder, exist_ok=True)

            # ── STEP 1 — Pull entire WhatsApp folder ──────────
            self._log("\n[ STEP 1 / 3 ]  Pulling entire WhatsApp folder from phone…","info")
            self._log(f"  Save to : {self._backup_folder}","dim")
            self._set_progress(5)
            self._start_speed_monitor(self._backup_folder)
            t1 = time.time()
            src = self._source_path
            self._log(f"  Source  : {src}", "dim")
            _, err, code = run_adb_priority(
                ["pull", src, self._backup_folder],
                device=self.phone_id)
            pull_time = time.time() - t1
            self._stop_speed_monitor()
            if self._cancel_flag: return
            if code == 0:
                self._log(f"  ✓  Done!  ({pull_time:.1f}s)", "ok")
                self._set_progress(40)
            else:
                self._log(f"  ✗  Pull failed: {err}", "err"); return

            wa_local = os.path.join(self._backup_folder, "WhatsApp")
            if not os.path.exists(wa_local):
                self._log("  ✗  WhatsApp folder not found in backup", "err"); return

            # ── STEP 2 — Push to MEmu ──────────────────────────
            self._log(f"\n[ STEP 2 / 3 ]  Pushing to MEmu…","info")
            self._set_progress(45)

            # Check for accounts subfolder (dual WhatsApp accounts)
            accounts_local = os.path.join(wa_local, "accounts")
            has_accounts   = os.path.exists(accounts_local) and os.path.isdir(accounts_local)
            account_ids    = sorted(os.listdir(accounts_local)) if has_accounts else []

            if has_accounts and account_ids:
                # ── DUAL / MULTIPLE ACCOUNTS ──
                self._log(f"  📱  Found {len(account_ids)} WhatsApp account(s): {', '.join(account_ids)}", "ok")

                # First push main account (Backups/Databases/Media at root level)
                self._log(f"\n  ── Main Account ──", "info")
                self._log(f"  Destination : {MEMU_DEST}", "dim")
                self._push_subfolders(wa_local, MEMU_DEST, label="")
                self._set_progress(65)

                # Then push each sub-account into accounts/<id>/
                total_acc  = len(account_ids)
                for idx, acc_id in enumerate(account_ids):
                    if self._cancel_flag: return
                    acc_local = os.path.join(accounts_local, acc_id)
                    acc_memu  = f"{MEMU_ACCOUNTS}/{acc_id}"
                    self._log(f"\n  ── Account {acc_id} ──", "info")
                    self._log(f"  Destination : {acc_memu}", "dim")
                    run_adb(["shell","mkdir","-p", acc_memu], device=self.memu_id)
                    self._push_subfolders(acc_local, acc_memu, label=f"[{acc_id}] ")
                    prog = 65 + int((idx+1) / total_acc * 23)
                    self._set_progress(prog)
            else:
                # ── SINGLE ACCOUNT ──
                self._log(f"  Destination : {MEMU_DEST}", "dim")
                self._push_subfolders(wa_local, MEMU_DEST)
                self._set_progress(88)

            if self._cancel_flag: return
            self._set_progress(90)

            # ── STEP 3 — Verify ────────────────────────────────
            self._log(f"\n[ STEP 3 / 3 ]  Verifying in MEmu…","info")
            stdout,_,_ = run_adb(["shell","ls",MEMU_DEST], device=self.memu_id)
            if stdout:
                self._log("  ✓  MEmu WhatsApp contents:","ok")
                for line in stdout.splitlines()[:8]:
                    self._log(f"     📁  {line}","dim")
            self._set_progress(100)
            self._timer_running = False
            self.after(0, lambda: self.lbl_speed.config(text="Done!", fg=C["green"]))

            total = int(time.time()-self._start_time)
            m, s  = divmod(total, 60)
            ts_str = f"{m}m {s}s" if m else f"{s}s"
            acc_info = f"{len(account_ids)} sub-account(s)" if has_accounts and account_ids else "Single account"
            self._log("\n"+"━"*54,"head")
            self._log("🎉  BACKUP COMPLETE!","head")
            self._log(f"  ⏱  Time     : {ts_str}","ok")
            self._log(f"  📱  Accounts : {acc_info}","ok")
            self._log(f"  💾  Saved    : {self._backup_folder}","ok")
            self._log(f"  📁  MEmu     : {MEMU_DEST}","ok")
            self._log("━"*54,"head")
            msg = (f"Backup finished!\n\n"
                   f"\u23f1  Time     : {ts_str}\n"
                   f"\U0001f4f1  Accounts : {acc_info}\n"
                   f"\U0001f4be  Saved    : {self._backup_folder}\n"
                   f"\U0001f4c1  MEmu     : {MEMU_DEST}")
            self.after(0,lambda m=msg: messagebox.showinfo("Backup Complete!", m))
        except Exception as e:
            self._log(f"  ✗  Unexpected error: {e}","err")
        finally:
            self._timer_running=False; self._speed_running=False
            self._stop_device_monitor()
            self.after(0,lambda: self.btn_backup.config(state="normal"))
            self.after(0,lambda: self.btn_cancel.config(state="disabled"))

if __name__=="__main__":
    App().mainloop()
