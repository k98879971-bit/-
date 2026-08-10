#!/usr/bin/env python3
import os
import subprocess
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
from androguard.core.axml import ARSCParser
from androguard.core.dex import DEX

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

def compile_with_aapt2(package_name="com.clickifyouwant.game", app_label="Click if you want"):
    aapt2_bin = "./node_modules/aaptjs3/bin/x64/linux/aapt2"
    android_jar = "/tmp/j2s/lib/android/android.jar"
    
    work_dir = "/tmp/aapt2_build"
    os.makedirs(f"{work_dir}/res/drawable", exist_ok=True)
    
    # Copy icon
    if os.path.exists("icon-192.png"):
        import shutil
        shutil.copy("icon-192.png", f"{work_dir}/res/drawable/icon.png")
        
    manifest_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{package_name}"
    android:versionCode="1"
    android:versionName="1.0.0">

    <uses-sdk
        android:minSdkVersion="21"
        android:targetSdkVersion="34" />

    <application
        android:label="{app_label}"
        android:icon="@drawable/icon"
        android:theme="@android:style/Theme.NoTitleBar.Fullscreen">
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:configChanges="orientation|screenSize|keyboardHidden"
            android:screenOrientation="portrait">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
"""
    with open(f"{work_dir}/AndroidManifest.xml", "w") as f:
        f.write(manifest_xml)
        
    subprocess.run([aapt2_bin, "compile", "--dir", f"{work_dir}/res", "-o", f"{work_dir}/compiled.zip"], check=True)
    subprocess.run([aapt2_bin, "link", "-I", android_jar, "--manifest", f"{work_dir}/AndroidManifest.xml", "-o", f"{work_dir}/linked.apk", f"{work_dir}/compiled.zip", "--auto-add-overlay"], check=True)
    
    z = zipfile.ZipFile(f"{work_dir}/linked.apk")
    axml_bytes = z.read("AndroidManifest.xml")
    arsc_bytes = z.read("resources.arsc")
    icon_bytes = z.read("res/drawable/icon.png")
    return axml_bytes, arsc_bytes, icon_bytes

def generate_html_game():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

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
    
    print("1. Compiling Android Resources and Manifest with official AAPT2...")
    axml_bytes, arsc_bytes, icon_bytes = compile_with_aapt2(package_name, app_label)
    
    print("2. Generating Dalvik DEX bytecode...")
    dex_bytes = build_classes_dex(package_name)
    
    print("3. Generating HTML5 game engine asset...")
    html_content = generate_html_game().encode("utf-8")
    
    file_entries = {
        "AndroidManifest.xml": axml_bytes,
        "classes.dex": dex_bytes,
        "resources.arsc": arsc_bytes,
        "res/drawable/icon.png": icon_bytes,
        "assets/index.html": html_content
    }
    
    output_apk = "Click_if_you_want.apk"
    print(f"4. Packaging, 4-byte zipaligning, and dual-signing (v1 + v2) into {output_apk}...")
    sign_and_align_apk(file_entries, output_apk)
    
    print(f"✅ Successfully built official AAPT2 APK: {output_apk} (Size: {os.path.getsize(output_apk)} bytes)!")
    
    print("\n🔍 Validating output APK...")
    a = APK(output_apk)
    print("Package:", a.get_package())
    print("App Name:", a.get_app_name())
    print("Min SDK:", a.get_min_sdk_version())
    print("Target SDK:", a.get_target_sdk_version())
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
