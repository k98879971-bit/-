#!/usr/bin/env python3
import os
import zipfile
import struct
import hashlib
import zlib
import base64
import datetime
from PIL import Image, ImageDraw
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, pkcs7
from androguard.core.apk import APK
from androguard.core.axml import ARSCParser, AXMLPrinter
from androguard.core.dex import DEX
import lxml.etree

def uleb128(v):
    b = bytearray()
    while True:
        byte = v & 0x7f
        v >>= 7
        if v != 0:
            b.append(byte | 0x80)
        else:
            b.append(byte)
            break
    return bytes(b)

def build_classes_dex(package_name="com.clickifyouwant.game"):
    activity_class = f"L{package_name.replace('.', '/')}/MainActivity;"
    
    raw_strings = [
        "",
        "<init>",
        "()Landroid/webkit/WebSettings;",
        "()V",
        "(Landroid/content/Context;)V",
        "(Landroid/os/Bundle;)V",
        "(Landroid/view/View;)V",
        "(Ljava/lang/String;)V",
        "(Z)V",
        "L",
        "Landroid/app/Activity;",
        "Landroid/content/Context;",
        "Landroid/os/Bundle;",
        "Landroid/view/View;",
        "Landroid/webkit/WebSettings;",
        "Landroid/webkit/WebView;",
        activity_class,
        "Ljava/lang/Object;",
        "Ljava/lang/String;",
        "MainActivity.java",
        "V",
        "VL",
        "VLL",
        "VLZ",
        "Z",
        "file:///android_asset/index.html",
        "getSettings",
        "loadUrl",
        "onCreate",
        "setContentView",
        "setDomStorageEnabled",
        "setJavaScriptEnabled",
    ]
    
    strings = sorted(list(set(raw_strings)))
    str_map = {s: i for i, s in enumerate(strings)}
    
    raw_types = [
        "Landroid/app/Activity;",
        "Landroid/content/Context;",
        "Landroid/os/Bundle;",
        "Landroid/view/View;",
        "Landroid/webkit/WebSettings;",
        "Landroid/webkit/WebView;",
        activity_class,
        "Ljava/lang/Object;",
        "Ljava/lang/String;",
        "V",
        "Z",
    ]
    types = sorted(list(set(raw_types)), key=lambda t: str_map[t])
    type_map = {t: i for i, t in enumerate(types)}
    
    raw_protos = [
        ("V", "V", ()),
        ("V", "V", ("Landroid/content/Context;",)),
        ("V", "V", ("Landroid/os/Bundle;",)),
        ("V", "V", ("Landroid/view/View;",)),
        ("V", "V", ("Ljava/lang/String;",)),
        ("V", "V", ("Z",)),
        ("L", "Landroid/webkit/WebSettings;", ()),
    ]
    
    def proto_sort_key(p):
        ret_idx = type_map[p[1]]
        param_indices = tuple(type_map[param] for param in p[2])
        return (ret_idx, param_indices)
    
    protos = sorted(raw_protos, key=proto_sort_key)
    proto_map = { (p[1], tuple(p[2])): i for i, p in enumerate(protos) }
    
    raw_methods = [
        ("Landroid/app/Activity;", "<init>", "V", ()),
        ("Landroid/app/Activity;", "onCreate", "V", ("Landroid/os/Bundle;",)),
        ("Landroid/app/Activity;", "setContentView", "V", ("Landroid/view/View;",)),
        ("Landroid/webkit/WebView;", "<init>", "V", ("Landroid/content/Context;",)),
        ("Landroid/webkit/WebView;", "getSettings", "Landroid/webkit/WebSettings;", ()),
        ("Landroid/webkit/WebView;", "loadUrl", "V", ("Ljava/lang/String;",)),
        ("Landroid/webkit/WebSettings;", "setDomStorageEnabled", "V", ("Z",)),
        ("Landroid/webkit/WebSettings;", "setJavaScriptEnabled", "V", ("Z",)),
        (activity_class, "<init>", "V", ()),
        (activity_class, "onCreate", "V", ("Landroid/os/Bundle;",)),
    ]
    
    def method_sort_key(m):
        cls_idx = type_map[m[0]]
        name_idx = str_map[m[1]]
        proto_idx = proto_map[(m[2], tuple(m[3]))]
        return (cls_idx, name_idx, proto_idx)
    
    methods = sorted(raw_methods, key=method_sort_key)
    method_map = { (m[0], m[1], m[2], tuple(m[3])): i for i, m in enumerate(methods) }
    
    act_init_idx = method_map[("Landroid/app/Activity;", "<init>", "V", ())]
    init_insns = struct.pack("<HHH", 0x1070, act_init_idx, 0x0000) + struct.pack("<H", 0x000e)
    init_code = struct.pack("<HHHHII", 1, 1, 1, 0, 0, len(init_insns) // 2) + init_insns
    if len(init_code) % 4 != 0:
        init_code += b"\x00" * (4 - (len(init_code) % 4))
        
    act_oncreate_idx = method_map[("Landroid/app/Activity;", "onCreate", "V", ("Landroid/os/Bundle;",))]
    webview_type_idx = type_map["Landroid/webkit/WebView;"]
    webview_init_idx = method_map[("Landroid/webkit/WebView;", "<init>", "V", ("Landroid/content/Context;",))]
    get_settings_idx = method_map[("Landroid/webkit/WebView;", "getSettings", "Landroid/webkit/WebSettings;", ())]
    set_js_idx = method_map[("Landroid/webkit/WebSettings;", "setJavaScriptEnabled", "V", ("Z",))]
    set_dom_idx = method_map[("Landroid/webkit/WebSettings;", "setDomStorageEnabled", "V", ("Z",))]
    url_str_idx = str_map["file:///android_asset/index.html"]
    load_url_idx = method_map[("Landroid/webkit/WebView;", "loadUrl", "V", ("Ljava/lang/String;",))]
    set_view_idx = method_map[("Landroid/app/Activity;", "setContentView", "V", ("Landroid/view/View;",))]
    
    oncreate_insns = bytearray()
    oncreate_insns += struct.pack("<HHH", 0x206f, act_oncreate_idx, 0x0043)
    oncreate_insns += struct.pack("<HH", 0x0022, webview_type_idx)
    oncreate_insns += struct.pack("<HHH", 0x2070, webview_init_idx, 0x0030)
    oncreate_insns += struct.pack("<HHH", 0x106e, get_settings_idx, 0x0000)
    oncreate_insns += struct.pack("<H", 0x010c)
    oncreate_insns += struct.pack("<H", 0x1212)
    oncreate_insns += struct.pack("<HHH", 0x206e, set_js_idx, 0x0021)
    oncreate_insns += struct.pack("<HHH", 0x206e, set_dom_idx, 0x0021)
    oncreate_insns += struct.pack("<HH", 0x011a, url_str_idx)
    oncreate_insns += struct.pack("<HHH", 0x206e, load_url_idx, 0x0010)
    oncreate_insns += struct.pack("<HHH", 0x206e, set_view_idx, 0x0003)
    oncreate_insns += struct.pack("<H", 0x000e)
    
    oncreate_code = struct.pack("<HHHHII", 5, 2, 2, 0, 0, len(oncreate_insns) // 2) + bytes(oncreate_insns)
    if len(oncreate_code) % 4 != 0:
        oncreate_code += b"\x00" * (4 - (len(oncreate_code) % 4))
        
    header_size = 0x70
    string_ids_off = header_size
    type_ids_off = string_ids_off + len(strings) * 4
    proto_ids_off = type_ids_off + len(types) * 4
    method_ids_off = proto_ids_off + len(protos) * 12
    class_defs_off = method_ids_off + len(methods) * 8
    data_off = class_defs_off + 1 * 32
    
    data = bytearray()
    
    proto_typelist_offsets = {}
    for p in protos:
        params = p[2]
        if not params:
            proto_typelist_offsets[p] = 0
        else:
            off = data_off + len(data)
            proto_typelist_offsets[p] = off
            tl = struct.pack("<I", len(params))
            for param in params:
                tl += struct.pack("<H", type_map[param])
            if len(params) % 2 != 0:
                tl += struct.pack("<H", 0)
            data += tl
            
    string_data_offsets = []
    for s in strings:
        off = data_off + len(data)
        string_data_offsets.append(off)
        s_bytes = s.encode("utf-8")
        data += uleb128(len(s)) + s_bytes + b"\x00"
        
    while len(data) % 4 != 0:
        data.append(0)
        
    init_code_off = data_off + len(data)
    data += init_code
    
    oncreate_code_off = data_off + len(data)
    data += oncreate_code
    
    main_init_method_idx = method_map[(activity_class, "<init>", "V", ())]
    main_oncreate_method_idx = method_map[(activity_class, "onCreate", "V", ("Landroid/os/Bundle;",))]
    
    class_data = bytearray()
    class_data += uleb128(0)
    class_data += uleb128(0)
    class_data += uleb128(1)
    class_data += uleb128(1)
    
    class_data += uleb128(main_init_method_idx)
    class_data += uleb128(0x10001)
    class_data += uleb128(init_code_off)
    
    class_data += uleb128(main_oncreate_method_idx)
    class_data += uleb128(0x1)
    class_data += uleb128(oncreate_code_off)
    
    class_data_off = data_off + len(data)
    data += class_data
    while len(data) % 4 != 0:
        data.append(0)
        
    map_list_off = data_off + len(data)
    tl_offsets = [off for off in proto_typelist_offsets.values() if off > 0]
    map_items = [
        (0x0000, 1, 0),
        (0x0001, len(strings), string_ids_off),
        (0x0002, len(types), type_ids_off),
        (0x0003, len(protos), proto_ids_off),
        (0x0005, len(methods), method_ids_off),
        (0x0006, 1, class_defs_off),
    ]
    if tl_offsets:
        map_items.append((0x1001, len(tl_offsets), min(tl_offsets)))
    map_items.extend([
        (0x2002, len(strings), string_data_offsets[0]),
        (0x2001, 2, init_code_off),
        (0x2000, 1, class_data_off),
        (0x1000, 1, map_list_off),
    ])
    map_items.sort(key=lambda x: x[2])
    
    map_data = struct.pack("<I", len(map_items))
    for type_code, size, offset in map_items:
        map_data += struct.pack("<HHII", type_code, 0, size, offset)
    data += map_data
    
    string_ids = bytearray()
    for s_off in string_data_offsets:
        string_ids += struct.pack("<I", s_off)
        
    type_ids = bytearray()
    for t in types:
        type_ids += struct.pack("<I", str_map[t])
        
    proto_ids = bytearray()
    for p in protos:
        shorty_idx = str_map[p[0]]
        ret_idx = type_map[p[1]]
        param_off = proto_typelist_offsets[p]
        proto_ids += struct.pack("<III", shorty_idx, ret_idx, param_off)
        
    method_ids = bytearray()
    for m in methods:
        cls_idx = type_map[m[0]]
        proto_idx = proto_map[(m[2], tuple(m[3]))]
        name_idx = str_map[m[1]]
        method_ids += struct.pack("<HHI", cls_idx, proto_idx, name_idx)
        
    class_idx = type_map[activity_class]
    access_flags = 0x1
    super_idx = type_map["Landroid/app/Activity;"]
    interfaces_off = 0
    source_file_idx = str_map["MainActivity.java"]
    annotations_off = 0
    static_values_off = 0
    class_defs = struct.pack("<IIIIIIII", class_idx, access_flags, super_idx, interfaces_off, source_file_idx, annotations_off, class_data_off, static_values_off)
    
    total_size = data_off + len(data)
    data_size = len(data)
    
    magic = b"dex\n035\x00"
    endian_tag = 0x12345678
    header_without_hashes = struct.pack(
        "<20I",
        total_size,
        header_size,
        endian_tag,
        0, 0,
        map_list_off,
        len(strings), string_ids_off,
        len(types), type_ids_off,
        len(protos), proto_ids_off,
        0, 0,
        len(methods), method_ids_off,
        1, class_defs_off,
        data_size, data_off
    )
    
    body = bytes(string_ids) + bytes(type_ids) + bytes(proto_ids) + bytes(method_ids) + bytes(class_defs) + bytes(data)
    sig_payload = header_without_hashes + body
    signature = hashlib.sha1(sig_payload).digest()
    
    chk_payload = signature + header_without_hashes + body
    checksum = zlib.adler32(chk_payload) & 0xffffffff
    
    header = magic + struct.pack("<I", checksum) + signature + header_without_hashes
    full_dex = header + body
    return full_dex

def build_manifest_axml(package_name="com.clickifyouwant.game", app_label="Click if you want"):
    template_apk = "/tmp/min2/bin/quoinsight-aligned.0.1.apk"
    z = zipfile.ZipFile(template_apk)
    axml = bytearray(z.read("AndroidManifest.xml"))
    
    sp_type, sp_hdr_size, sp_chunk_size, str_count, style_count, flags, strings_start, styles_start = struct.unpack_from("<HHIIIIII", axml, 8)
    offsets = list(struct.unpack_from(f"<{str_count}I", axml, 8 + 28))

    orig_strings = []
    for off in offsets:
        pos = 8 + strings_start + off
        u16len = struct.unpack_from("<H", axml, pos)[0]
        pos += 2
        s = axml[pos:pos+u16len*2].decode("utf-16le")
        orig_strings.append(s)

    replacements = {
        "0.1": "1.0.0",
        "Minimal": app_label,
        "com.quoinsight.minimal": package_name,
        "com.quoinsight.minimal.MainActivity": f"{package_name}.MainActivity",
    }

    new_strings = [replacements.get(s, s) for s in orig_strings]

    new_string_bytes = bytearray()
    new_offsets = []
    for s in new_strings:
        new_offsets.append(len(new_string_bytes))
        s_encoded = s.encode("utf-16le")
        new_string_bytes += struct.pack("<H", len(s)) + s_encoded + b"\x00\x00"

    while len(new_string_bytes) % 4 != 0:
        new_string_bytes += b"\x00"

    new_strings_start = 28 + len(new_offsets) * 4
    new_sp_chunk_size = new_strings_start + len(new_string_bytes)

    new_sp_header = struct.pack("<HHIIIIII", sp_type, sp_hdr_size, new_sp_chunk_size, len(new_strings), style_count, flags, new_strings_start, 0)
    new_sp_offsets = struct.pack(f"<{len(new_offsets)}I", *new_offsets)
    new_sp_chunk = new_sp_header + new_sp_offsets + bytes(new_string_bytes)

    rest_of_axml = axml[8 + sp_chunk_size:]
    new_file_size = 8 + len(new_sp_chunk) + len(rest_of_axml)
    new_file_header = struct.pack("<HHI", 3, 8, new_file_size)

    return new_file_header + new_sp_chunk + rest_of_axml

def build_resources_arsc(package_name="com.clickifyouwant.game"):
    template_apk = "/tmp/min2/bin/quoinsight-aligned.0.1.apk"
    z = zipfile.ZipFile(template_apk)
    arsc = bytearray(z.read("resources.arsc"))
    
    sp_type, sp_hdr_size, sp_size = struct.unpack_from("<HHI", arsc, 12)
    pkg_pos = 12 + sp_size
    arsc[pkg_pos+12:pkg_pos+12+256] = package_name.encode("utf-16le").ljust(256, b"\x00")
    return bytes(arsc)

def generate_html_game():
    return """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Click if you want</title>
  <style>
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      user-select: none;
      -webkit-user-select: none;
      -webkit-touch-callout: none;
      -webkit-tap-highlight-color: transparent;
    }
    html, body {
      width: 100%;
      height: 100%;
      overflow: hidden;
      background: radial-gradient(circle at 50% 30%, #202438 0%, #11131c 100%);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      color: #ffffff;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: space-between;
      touch-action: manipulation;
    }
    .header {
      margin-top: 40px;
      text-align: center;
      width: 90%;
      max-width: 400px;
    }
    .game-title {
      font-size: 24px;
      font-weight: 700;
      letter-spacing: 1px;
      color: #8fa0dd;
      text-transform: uppercase;
      margin-bottom: 8px;
    }
    .score-container {
      background: rgba(255, 255, 255, 0.07);
      backdrop-filter: blur(10px);
      -webkit-backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 20px;
      padding: 16px 24px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.4);
    }
    .score-text {
      font-size: 42px;
      font-weight: 800;
      color: #ffd700;
      text-shadow: 0 2px 10px rgba(255, 215, 0, 0.4);
      letter-spacing: 1px;
    }
    .stats-row {
      display: flex;
      justify-content: space-around;
      margin-top: 10px;
      font-size: 14px;
      color: #a0aec0;
    }
    .stat-item span {
      color: #fff;
      font-weight: bold;
    }
    .center-stage {
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      flex: 1;
      width: 100%;
    }
    .click-button {
      width: 220px;
      height: 220px;
      border-radius: 50%;
      background: radial-gradient(circle at 35% 35%, #ffe600, #ff9900 60%, #c46200 100%);
      box-shadow: 0 15px 35px rgba(255, 153, 0, 0.4), inset 0 6px 10px rgba(255, 255, 255, 0.6), inset 0 -8px 12px rgba(0, 0, 0, 0.4);
      border: 6px solid #ffcc00;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      outline: none;
      transition: transform 0.08s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      position: relative;
      z-index: 10;
    }
    .click-button:active {
      transform: scale(0.92);
      box-shadow: 0 8px 20px rgba(255, 153, 0, 0.3), inset 0 3px 6px rgba(255, 255, 255, 0.4);
    }
    .coin-inner {
      width: 180px;
      height: 180px;
      border-radius: 50%;
      border: 3px dashed rgba(255, 255, 255, 0.4);
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .coin-letter {
      font-size: 96px;
      font-weight: 900;
      color: #ffffff;
      text-shadow: 0 4px 10px rgba(0, 0, 0, 0.35);
    }
    .floating-text {
      position: absolute;
      font-size: 32px;
      font-weight: 800;
      color: #ffd700;
      pointer-events: none;
      text-shadow: 0 2px 8px rgba(0,0,0,0.7);
      animation: floatUp 0.8s ease-out forwards;
      z-index: 20;
    }
    @keyframes floatUp {
      0% {
        opacity: 1;
        transform: translate(-50%, -50%) scale(0.8);
      }
      50% {
        transform: translate(calc(-50% + var(--rand-x)), -120px) scale(1.2);
      }
      100% {
        opacity: 0;
        transform: translate(calc(-50% + var(--rand-x)), -180px) scale(0.9);
      }
    }
    .particle {
      position: absolute;
      width: 8px;
      height: 8px;
      background: #ffd700;
      border-radius: 50%;
      pointer-events: none;
      animation: particlePop 0.6s cubic-bezier(0.25, 1, 0.5, 1) forwards;
      z-index: 15;
    }
    @keyframes particlePop {
      0% {
        opacity: 1;
        transform: translate(-50%, -50%) scale(1);
      }
      100% {
        opacity: 0;
        transform: translate(calc(-50% + var(--tx)), calc(-50% + var(--ty))) scale(0.2);
      }
    }
    .footer {
      margin-bottom: 30px;
      width: 90%;
      max-width: 360px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
    }
    .reset-btn {
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.15);
      color: #a0aec0;
      padding: 10px 20px;
      border-radius: 12px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }
    .reset-btn:active {
      background: rgba(255, 59, 48, 0.3);
      color: #ff3b30;
      border-color: #ff3b30;
    }
    .info-text {
      font-size: 12px;
      color: #64748b;
    }
  </style>
</head>
<body>
  <div class="header">
    <div class="game-title">Click if you want</div>
    <div class="score-container">
      <div class="score-text" id="scoreLabel">Счёт: 0</div>
      <div class="stats-row">
        <div class="stat-item">Рекорд: <span id="highScore">0</span></div>
        <div class="stat-item">Кликов: <span id="totalClicks">0</span></div>
      </div>
    </div>
  </div>

  <div class="center-stage" id="stage">
    <button class="click-button" id="clickButton" aria-label="Click">
      <div class="coin-inner">
        <div class="coin-letter">O</div>
      </div>
    </button>
  </div>

  <div class="footer">
    <button class="reset-btn" id="resetBtn">Сбросить прогресс</button>
    <div class="info-text">Mobile Edition • 100% Offline</div>
  </div>

  <script>
    let score = 0;
    let highScore = 0;
    let totalClicks = 0;

    try {
      score = parseInt(localStorage.getItem('clicker_score') || '0', 10);
      highScore = parseInt(localStorage.getItem('clicker_high_score') || '0', 10);
      totalClicks = parseInt(localStorage.getItem('clicker_total_clicks') || '0', 10);
    } catch(e) {}

    const scoreLabel = document.getElementById('scoreLabel');
    const highScoreLabel = document.getElementById('highScore');
    const totalClicksLabel = document.getElementById('totalClicks');
    const clickButton = document.getElementById('clickButton');
    const stage = document.getElementById('stage');
    const resetBtn = document.getElementById('resetBtn');

    let audioCtx = null;
    function playClickSound() {
      try {
        if (!audioCtx) {
          audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioCtx.state === 'suspended') {
          audioCtx.resume();
        }
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = 'sine';
        const now = audioCtx.currentTime;
        osc.frequency.setValueAtTime(587.33, now);
        osc.frequency.exponentialRampToValueAtTime(880, now + 0.08);
        gain.gain.setValueAtTime(0.25, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.08);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start(now);
        osc.stop(now + 0.08);
      } catch(e) {}
    }

    function updateDisplay() {
      scoreLabel.textContent = "Счёт: " + score;
      highScoreLabel.textContent = highScore;
      totalClicksLabel.textContent = totalClicks;
    }

    function saveState() {
      try {
        localStorage.setItem('clicker_score', score);
        localStorage.setItem('clicker_high_score', highScore);
        localStorage.setItem('clicker_total_clicks', totalClicks);
      } catch(e) {}
    }

    function spawnFloatingText(x, y) {
      const text = document.createElement('div');
      text.className = 'floating-text';
      text.textContent = '+1';
      text.style.left = x + 'px';
      text.style.top = y + 'px';
      const randX = (Math.random() - 0.5) * 80 + 'px';
      text.style.setProperty('--rand-x', randX);
      stage.appendChild(text);
      setTimeout(() => text.remove(), 800);
    }

    function spawnParticles(x, y) {
      const colors = ['#ffd700', '#ffea00', '#ffffff', '#ff9900'];
      for (let i = 0; i < 8; i++) {
        const p = document.createElement('div');
        p.className = 'particle';
        p.style.left = x + 'px';
        p.style.top = y + 'px';
        p.style.background = colors[Math.floor(Math.random() * colors.length)];
        const angle = (Math.PI * 2 / 8) * i + (Math.random() * 0.4 - 0.2);
        const dist = 60 + Math.random() * 50;
        const tx = Math.cos(angle) * dist + 'px';
        const ty = Math.sin(angle) * dist + 'px';
        p.style.setProperty('--tx', tx);
        p.style.setProperty('--ty', ty);
        stage.appendChild(p);
        setTimeout(() => p.remove(), 600);
      }
    }

    function handleClick(e) {
      score += 1;
      totalClicks += 1;
      if (score > highScore) {
        highScore = score;
      }
      updateDisplay();
      saveState();

      if (navigator.vibrate) {
        navigator.vibrate(20);
      }
      playClickSound();

      const rect = stage.getBoundingClientRect();
      let clientX = e.clientX;
      let clientY = e.clientY;
      if (e.touches && e.touches.length > 0) {
        clientX = e.touches[0].clientX;
        clientY = e.touches[0].clientY;
      } else if (!clientX) {
        const btnRect = clickButton.getBoundingClientRect();
        clientX = btnRect.left + btnRect.width / 2;
        clientY = btnRect.top + btnRect.height / 2;
      }
      const x = clientX - rect.left;
      const y = clientY - rect.top;
      spawnFloatingText(x, y);
      spawnParticles(x, y);
    }

    clickButton.addEventListener('pointerdown', (e) => {
      handleClick(e);
    });

    resetBtn.addEventListener('click', () => {
      if (confirm('Сбросить весь счёт?')) {
        score = 0;
        totalClicks = 0;
        updateDisplay();
        saveState();
      }
    });

    updateDisplay();
  </script>
</body>
</html>
"""

def sign_and_align_apk(file_entries, output_apk_path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"Click if you want"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Click if you want"),
    ])
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow() - datetime.timedelta(days=1)
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=3650)
    ).sign(key, hashes.SHA256())
    cert_der = cert.public_bytes(Encoding.DER)

    manifest_lines = [
        "Manifest-Version: 1.0",
        "Created-By: 1.0 (Android)",
        ""
    ]
    sf_lines = [
        "Signature-Version: 1.0",
        "Created-By: 1.0 (Android)",
        "X-Android-APK-Signed: 2",
    ]
    
    for filename, content in file_entries.items():
        sha1_data = base64.b64encode(hashlib.sha1(content).digest()).decode("ascii")
        entry = f"Name: {filename}\r\nSHA1-Digest: {sha1_data}\r\n\r\n"
        manifest_lines.append(f"Name: {filename}")
        manifest_lines.append(f"SHA1-Digest: {sha1_data}")
        manifest_lines.append("")
        
        sha1_entry = base64.b64encode(hashlib.sha1(entry.encode("utf-8")).digest()).decode("ascii")
        sf_lines.append(f"Name: {filename}")
        sf_lines.append(f"SHA1-Digest: {sha1_entry}")
        sf_lines.append("")

    manifest_bytes = ("\r\n".join(manifest_lines) + "\r\n").encode("utf-8")
    manifest_sha1 = base64.b64encode(hashlib.sha1(manifest_bytes).digest()).decode("ascii")
    
    sf_header = [
        "Signature-Version: 1.0",
        "Created-By: 1.0 (Android)",
        "X-Android-APK-Signed: 2",
        f"SHA1-Digest-Manifest: {manifest_sha1}",
        ""
    ]
    sf_bytes = ("\r\n".join(sf_header + sf_lines[3:]) + "\r\n").encode("utf-8")
    
    builder = pkcs7.PKCS7SignatureBuilder().set_data(sf_bytes)
    builder = builder.add_signer(cert, key, hashes.SHA256())
    cert_rsa_bytes = builder.sign(serialization.Encoding.DER, [pkcs7.PKCS7Options.DetachedSignature])

    all_entries = dict(file_entries)
    all_entries["META-INF/MANIFEST.MF"] = manifest_bytes
    all_entries["META-INF/CERT.SF"] = sf_bytes
    all_entries["META-INF/CERT.RSA"] = cert_rsa_bytes

    zip_bytes = bytearray()
    cd_entries = []
    
    for name, data in all_entries.items():
        name_bytes = name.encode("utf-8")
        crc = zlib.crc32(data) & 0xffffffff
        uncomp_size = len(data)
        
        if name.endswith(".arsc") or len(data) < 256:
            compress_type = 0
            comp_data = data
        else:
            compress_type = 8
            comp_data = zlib.compress(data, 9)[2:-4]
            
        comp_size = len(comp_data)
        
        header_len = 30 + len(name_bytes)
        current_offset = len(zip_bytes)
        data_offset = current_offset + header_len
        
        extra_bytes = b""
        if compress_type == 0:
            pad = (4 - (data_offset % 4)) % 4
            if pad > 0:
                extra_bytes = b"\x00" * pad
                header_len += pad
                
        local_header = struct.pack(
            "<IHHHHHIIIHH",
            0x04034b50,
            20,
            0,
            compress_type,
            0,
            0,
            crc,
            comp_size,
            uncomp_size,
            len(name_bytes),
            len(extra_bytes)
        )
        
        local_file_offset = len(zip_bytes)
        zip_bytes += local_header + name_bytes + extra_bytes + comp_data
        
        cd_record = struct.pack(
            "<IHHHHHHIIIHHHHHII",
            0x02014b50,
            20,
            20,
            0,
            compress_type,
            0,
            0,
            crc,
            comp_size,
            uncomp_size,
            len(name_bytes),
            0,
            0,
            0,
            0,
            0,
            local_file_offset
        )
        cd_entries.append((cd_record, name_bytes))

    cd_offset = len(zip_bytes)
    cd_bytes = bytearray()
    for cd_record, name_bytes in cd_entries:
        cd_bytes += cd_record + name_bytes
    cd_size = len(cd_bytes)

    eocd_offset = cd_offset + cd_size
    eocd_bytes = struct.pack(
        "<IHHHHIIH",
        0x06054b50,
        0,
        0,
        len(cd_entries),
        len(cd_entries),
        cd_size,
        cd_offset,
        0
    )
    
    raw_apk = bytes(zip_bytes) + bytes(cd_bytes) + eocd_bytes

    def compute_apk_v2_digest(apk_bytes, cd_off, eocd_off):
        section1 = apk_bytes[:cd_off]
        section2 = apk_bytes[cd_off:eocd_off]
        eocd = bytearray(apk_bytes[eocd_off:])
        struct.pack_into("<I", eocd, 16, len(section1))
        section3 = bytes(eocd)
        
        chunk_size = 1048576
        chunk_hashes = []
        
        for sec in [section1, section2, section3]:
            for i in range(0, len(sec), chunk_size):
                chunk = sec[i:i+chunk_size]
                h = hashlib.sha256(b"\xa5" + struct.pack("<I", len(chunk)) + chunk).digest()
                chunk_hashes.append(h)
                
        total_chunks = len(chunk_hashes)
        return hashlib.sha256(b"\x5a" + struct.pack("<I", total_chunks) + b"".join(chunk_hashes)).digest()

    digest = compute_apk_v2_digest(raw_apk, cd_offset, eocd_offset)

    digest_item = struct.pack("<I", 0x0103) + struct.pack("<I", len(digest)) + digest
    digests_seq = struct.pack("<I", len(digest_item)) + digest_item
    digests_block = struct.pack("<I", len(digests_seq)) + digests_seq

    cert_item = struct.pack("<I", len(cert_der)) + cert_der
    certs_seq = struct.pack("<I", len(cert_item)) + cert_item
    certs_block = struct.pack("<I", len(certs_seq)) + certs_seq

    attrs_block = struct.pack("<I", 0)

    signed_data = struct.pack("<I", len(digests_block)) + digests_block + struct.pack("<I", len(certs_block)) + certs_block + struct.pack("<I", len(attrs_block)) + attrs_block

    sig_bytes = key.sign(signed_data, padding.PKCS1v15(), hashes.SHA256())
    sig_item = struct.pack("<I", 0x0103) + struct.pack("<I", len(sig_bytes)) + sig_bytes
    signatures_seq = struct.pack("<I", len(sig_item)) + sig_item
    signatures_block = struct.pack("<I", len(signatures_seq)) + signatures_seq

    pubkey_der = key.public_key().public_bytes(encoding=Encoding.DER, format=PublicFormat.SubjectPublicKeyInfo)
    pubkey_block = struct.pack("<I", len(pubkey_der)) + pubkey_der

    signer_block = struct.pack("<I", len(signed_data)) + signed_data + struct.pack("<I", len(signatures_block)) + signatures_block + struct.pack("<I", len(pubkey_block)) + pubkey_block
    signers_seq = struct.pack("<I", len(signer_block)) + signer_block
    v2_block = struct.pack("<I", len(signers_seq)) + signers_seq

    pair_len = 4 + len(v2_block)
    pair_data = struct.pack("<Q", pair_len) + struct.pack("<I", 0x7109871a) + v2_block

    block_size = len(pair_data) + 8 + 16
    signing_block = struct.pack("<Q", block_size) + pair_data + struct.pack("<Q", block_size) + b"APK Sig Block 42"

    sec1 = raw_apk[:cd_offset]
    sec2 = raw_apk[cd_offset:eocd_offset]
    eocd_final = bytearray(raw_apk[eocd_offset:])
    new_cd_offset = len(sec1) + len(signing_block)
    struct.pack_into("<I", eocd_final, 16, new_cd_offset)

    final_apk = sec1 + signing_block + sec2 + bytes(eocd_final)
    
    with open(output_apk_path, "wb") as f:
        f.write(final_apk)

def main():
    package_name = "com.clickifyouwant.game"
    app_label = "Click if you want"
    
    print("1. Generating Dalvik DEX bytecode...")
    dex_bytes = build_classes_dex(package_name)
    
    print("2. Generating Android Binary XML manifest...")
    axml_bytes = build_manifest_axml(package_name, app_label)
    
    print("3. Generating Resources table (ARSC)...")
    arsc_bytes = build_resources_arsc(package_name)
    
    print("4. Generating HTML5 game engine asset...")
    html_content = generate_html_game().encode("utf-8")
    
    file_entries = {
        "AndroidManifest.xml": axml_bytes,
        "classes.dex": dex_bytes,
        "resources.arsc": arsc_bytes,
        "assets/index.html": html_content
    }
    
    output_apk = "Click_if_you_want.apk"
    print(f"5. Packaging, 4-byte zipaligning, and dual-signing (v1 + v2) into {output_apk}...")
    sign_and_align_apk(file_entries, output_apk)
    
    print(f"✅ Successfully built {output_apk} (Size: {os.path.getsize(output_apk)} bytes)!")
    
    print("\n🔍 Validating output APK...")
    a = APK(output_apk)
    print("Package:", a.get_package())
    print("App Name:", a.get_app_name())
    print("Main Activity:", a.get_main_activity())
    print("Activities in Manifest:", a.get_activities())
    print("Signed v1:", a.is_signed_v1())
    print("Signed v2:", a.is_signed_v2())
    arsc = ARSCParser(a.get_file("resources.arsc"))
    print("ARSC packages:", arsc.get_packages_names())
    d = DEX(a.get_dex())
    print("DEX classes:", [c.get_name() for c in d.get_classes()])

if __name__ == "__main__":
    main()
