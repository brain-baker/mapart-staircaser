import streamlit as st
import tempfile
import os
import zipfile
import io
from staircase import convert

st.set_page_config(page_title="Map Art Staircaser", page_icon="🗺️", layout="wide")
st.title("🗺️ Map Art Staircase Converter")
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
""", unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "Upload your flat map art file(s)",
    type=["nbt", "schem", "litematic", "schematic"],
    accept_multiple_files=True
)

if uploaded_files:
    results = []       # (out_name, out_bytes)
    skipped = []       # (filename, reason)
    errors = []        # (filename, error)

    progress = st.progress(0, text="Converting...")

    for i, uploaded in enumerate(uploaded_files):
        base, ext = os.path.splitext(uploaded.name)
        out_name = f"{base}(fixed){ext}"

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp_in:
            tmp_in.write(uploaded.read())
            in_path = tmp_in.name

        out_path = in_path + ".out" + ext

        try:
            _, count = convert(in_path, out_path)
            with open(out_path, 'rb') as f:
                results.append((out_name, f.read(), count))
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

    # Summary
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

    # Single file → direct download
    if len(results) == 1:
        name, data, count = results[0]
        st.download_button(
            f"⬇️ Download {name} ({count} carpets)",
            data,
            name
        )

    # Multiple files → individual downloads + zip
    elif len(results) > 1:
        # Individual downloads
        cols = st.columns(min(len(results), 4))
        for i, (name, data, count) in enumerate(results):
            with cols[i % len(results)]:
                st.download_button(
                    f"⬇️ {name}",
                    data,
                    name,
                    key=f"dl_{i}"
                )

        # Zip all
        st.markdown("---")
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for name, data, _ in results:
                zf.writestr(name, data)
        zip_buffer.seek(0)

        total_carpets = sum(c for _, _, c in results)
        st.download_button(
            f"📦 Download all {len(results)} files as ZIP ({total_carpets} total carpets)",
            zip_buffer.getvalue(),
            "staircased_maparts.zip"
        )
