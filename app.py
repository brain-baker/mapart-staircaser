import streamlit as st
import tempfile
import os
from staircase import convert

st.set_page_config(page_title="Map Art Staircaser", page_icon="🗺️")
st.title("🗺️ Map Art Staircase Converter")
st.write("Upload flat carpet map art → download staircased version")
st.write("Supported formats: `.nbt`, `.schem`, `.litematic`, `.schematic`")
st.info("⚠️ Already staircased files will be detected and skipped automatically.")

uploaded = st.file_uploader(
    "Upload your flat map art file",
    type=["nbt", "schem", "litematic", "schematic"]
)

if uploaded:
    base, ext = os.path.splitext(uploaded.name)
    out_name = f"{base}(fixed){ext}"

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp_in:
        tmp_in.write(uploaded.read())
        in_path = tmp_in.name

    out_path = in_path + ".out" + ext

    try:
        _, count = convert(in_path, out_path)
        with open(out_path, 'rb') as f:
            st.success(f"✅ Converted {count} carpets!")
            st.download_button(
                "⬇️ Download staircased file",
                f.read(),
                out_name
            )
    except ValueError as e:
        if "already staircased" in str(e).lower():
            st.warning(f"⚠️ {e}")
        else:
            st.error(f"❌ {e}")
    except Exception as e:
        st.error(f"❌ Error: {e}")
    finally:
        if os.path.exists(in_path):
            os.unlink(in_path)
        if os.path.exists(out_path):
            os.unlink(out_path)
