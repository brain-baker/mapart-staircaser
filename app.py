# app.py
import streamlit as st
import tempfile
import os
import zipfile
import io
from staircase import convert, carpets_to_json, extract_json_from_staircased

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

export_json = st.checkbox(
    "📄 Also export JSON",
    value=False,
    help="Generates a .json alongside the schematic. For already-staircased files, exports JSON directly without converting."
)

uploaded_files = st.file_uploader(
    "Upload your flat map art file(s)",
    type=["nbt", "schem", "litematic", "schematic"],
    accept_multiple_files=True
)

if uploaded_files:
    results  = []  # (out_name, out_bytes, count, json_bytes_or_none)
    skipped  = []  # (filename, reason, json_bytes_or_none)
    errors   = []  # (filename, error)

    progress = st.progress(0, text="Converting...")

    for i, uploaded in enumerate(uploaded_files):
        base, ext = os.path.splitext(uploaded.name)
        out_name = f"{base}(fixed){ext}"
        file_bytes = uploaded.read()

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp_in:
            tmp_in.write(file_bytes)
            in_path = tmp_in.name

        out_path = in_path + ".out" + ext

        try:
            _, count, carpets = convert(in_path, out_path)
            with open(out_path, 'rb') as f:
                json_bytes = carpets_to_json(carpets) if export_json else None
                results.append((out_name, f.read(), count, json_bytes))

        except ValueError as e:
            if "already staircased" in str(e).lower():
                # still extract JSON from the staircased file if checkbox is ticked
                json_bytes = None
                if export_json:
                    try:
                        json_bytes = extract_json_from_staircased(in_path)
                    except Exception as je:
                        json_bytes = None
                        st.warning(f"⚠️ Could not extract JSON from **{uploaded.name}**: {je}")
                skipped.append((uploaded.name, str(e), json_bytes))
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

    # skipped files — show warning + JSON download button if available
    for name, reason, json_bytes in skipped:
        st.warning(f"⚠️ **{name}** — {reason}")
        if json_bytes:
            json_name = os.path.splitext(name)[0] + ".json"
            st.download_button(
                f"📄 Download {json_name} (JSON — extracted from existing staircase)",
                json_bytes,
                json_name,
                key=f"skip_json_{name}"
            )

    if errors:
        for name, err in errors:
            st.error(f"❌ **{name}** — {err}")

    # single converted file
    if len(results) == 1:
        name, data, count, json_bytes = results[0]
        st.download_button(
            f"⬇️ Download {name} ({count} carpets)",
            data,
            name
        )
        if json_bytes:
            json_name = os.path.splitext(name)[0] + ".json"
            st.download_button(
                f"📄 Download {json_name} (JSON)",
                json_bytes,
                json_name
            )

    # multiple converted files
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
                if json_bytes:
                    json_name = os.path.splitext(name)[0] + ".json"
                    st.download_button(
                        f"📄 {json_name}",
                        json_bytes,
                        json_name,
                        key=f"json_{i}"
                    )

        st.markdown("---")

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for name, data, _, json_bytes in results:
                zf.writestr(name, data)
                if json_bytes:
                    zf.writestr(os.path.splitext(name)[0] + ".json", json_bytes)
        zip_buffer.seek(0)

        total_carpets = sum(c for _, _, c, _ in results)
        zip_label = f"📦 Download all {len(results)} files as ZIP ({total_carpets} total carpets)"
        if export_json:
            zip_label += " — includes JSON files"
        st.download_button(zip_label, zip_buffer.getvalue(), "staircased_maparts.zip")
