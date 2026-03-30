# app.py
import streamlit as st
import tempfile
import os
import zipfile
import io
from staircase import convert, carpets_to_json

st.set_page_config(page_title="Map Art Staircaser", page_icon="🗺️", layout="wide")
st.title("🗺️ Carpet Maparts Fixer")
st.write("Upload flat carpet map art → download staircased version")
st.write("Supported formats: `.nbt`, `.schem`, `.litematic`, `.schematic`")
st.info("⚠️ Already staircased files will be detected and skipped automatically.")

st.markdown("""
<style>
    [data-testid="stUploadDropzoneInput"] {
        min-height: 400px !important;
    }
    [data-testid="stFileUploadDropzone"] {
        min-height: 400px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    [data-testid="stFileUploadDropzone"] div {
        font-size: 1.3rem !important;
    }
    [data-testid="stFileUploadDropzone"] small {
        font-size: 1rem !important;
    }
</style>

<div class="easter-egg">KT loves Proe. Proe loves Roblox.</div>
<style>
    .easter-egg {
        position: fixed;
        left: 0;
        top: 50%;
        transform: translateY(-50%);
        width: 40px;
        height: 100px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: transparent;
        font-size: 0.9rem;
        user-select: none;
        z-index: 9999;
        transition: color 0.3s ease;
    }
    .easter-egg:hover {
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- optional JSON export checkbox ---
export_json = st.checkbox(
    "📄 Also export JSON for JsMacros mapart script",
    value=False,
    help="Generates a .json file alongside the converted schematic. Drop it in schematics/Maparts/WIP/ with the schematic file."
)

uploaded_files = st.file_uploader(
    "Upload your flat map art file(s)",
    type=["nbt", "schem", "litematic", "schematic"],
    accept_multiple_files=True
)

if uploaded_files:
    results = []   # (out_name, out_bytes, count, json_bytes_or_none)
    skipped = []   # (filename, reason)
    errors = []    # (filename, error)

    progress = st.progress(0, text="Converting...")

    for i, uploaded in enumerate(uploaded_files):
        base, ext = os.path.splitext(uploaded.name)
        out_name = f"{base}(fixed){ext}"

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp_in:
            tmp_in.write(uploaded.read())
            in_path = tmp_in.name

        out_path = in_path + ".out" + ext

        try:
            # convert() now returns 3 values — carpets used for JSON if needed
            _, count, carpets = convert(in_path, out_path)
            with open(out_path, 'rb') as f:
                json_bytes = carpets_to_json(carpets) if export_json else None
                results.append((out_name, f.read(), count, json_bytes))
        except ValueError as e:
            if "already staircased" in str(e).lower():
                skipped.append((uploaded.name, str(e)))
            else:
                errors.append((uploaded.name, str(e)))
        except Exception as e:
            errors.append((uploaded.name, str(e)))
        finally:
            if os.path.exists(in_path):
                os.unlink(in_path)
            if os.path.exists(out_path):
                os.unlink(out_path)

        progress.progress((i + 1) / len(uploaded_files), text=f"Converting... {i + 1}/{len(uploaded_files)}")

    progress.empty()

    st.markdown("---")
    st.subheader("Results")

    if results:
        st.success(f"✅ {len(results)} file(s) converted successfully!")
    if skipped:
        for name, reason in skipped:
            st.warning(f"⚠️ **{name}** — {reason}")
    if errors:
        for name, err in errors:
            st.error(f"❌ **{name}** — {err}")

    # single file
    if len(results) == 1:
        name, data, count, json_bytes = results[0]
        st.download_button(
            f"⬇️ Download {name} ({count} carpets)",
            data,
            name
        )
        # show JSON download only if checkbox was ticked
        if json_bytes:
            json_name = name.rsplit(".", 1)[0] + ".json"
            st.download_button(
                f"📄 Download {json_name} (JsMacros JSON)",
                json_bytes,
                json_name
            )

    # multiple files
    elif len(results) > 1:
        cols = st.columns(min(len(results), 4))
        for i, (name, data, count, json_bytes) in enumerate(results):
            with cols[i % len(results)]:
                st.download_button(
                    f"⬇️ {name}",
                    data,
                    name,
                    key=f"dl_{i}"
                )
                # JSON button per file if checkbox ticked
                if json_bytes:
                    json_name = name.rsplit(".", 1)[0] + ".json"
                    st.download_button(
                        f"📄 {json_name}",
                        json_bytes,
                        json_name,
                        key=f"json_{i}"
                    )

        st.markdown("---")

        # zip all schematics
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for name, data, _, json_bytes in results:
                zf.writestr(name, data)
                # include JSON files in zip too if checkbox ticked
                if json_bytes:
                    json_name = name.rsplit(".", 1)[0] + ".json"
                    zf.writestr(json_name, json_bytes)
        zip_buffer.seek(0)

        total_carpets = sum(c for _, _, c, _ in results)
        zip_label = f"📦 Download all {len(results)} files as ZIP ({total_carpets} total carpets)"
        if export_json:
            zip_label += " — includes JSON files"
        st.download_button(zip_label, zip_buffer.getvalue(), "staircased_maparts.zip")
