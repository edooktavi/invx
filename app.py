import streamlit as st
import os
import tempfile
import pandas as pd
import logging
from invoice2data import extract_data
from invoice2data.extract.loader import read_templates
from PyPDF2 import PdfReader

# Aktifkan logging untuk debug invoice2data
#logging.basicConfig(level=logging.DEBUG)
#logger = logging.getLogger("invoice2data")
#logger.setLevel(logging.DEBUG)

def save_uploaded_file(uploaded_file):
    """Simpan file yang diunggah ke direktori sementara."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        return tmp_file.name

def extract_invoice_data(pdf_path, templates):
    """Ekstrak data dari PDF menggunakan invoice2data."""
    #logger.debug(f"Memproses file: {pdf_path}")
    extracted_data = extract_data(pdf_path, templates=templates)
    #logger.debug(f"Hasil ekstraksi: {extracted_data}")
    if extracted_data is None:
        logger.warning(f"Tidak ada data yang diekstrak dari {pdf_path}")
    return extracted_data

def normalize_data(results, expand_columns):
    """Pastikan semua kolom dalam expand_columns memiliki jumlah elemen yang sama."""
    for result in results:
        max_len = max([len(result[col]) if col in result and isinstance(result[col], list) else 1 for col in expand_columns])

        for col in expand_columns:
            if col in result:
                if isinstance(result[col], list):
                    result[col] = result[col] + [None] * (max_len - len(result[col]))
                else:
                    result[col] = [result[col]] * max_len
            else:
                result[col] = [None] * max_len  # Jika kolom tidak ada, isi dengan None
    return results

def expand_rows(data, expand_columns):
    """Memperluas baris berdasarkan kolom yang berisi array."""
    df = pd.DataFrame(data)
    df = df.explode(expand_columns, ignore_index=True)
    return df

def main():
    st.set_page_config(page_title="Invoice Extraction Tools")
    st.title("PDF Extractor")
    st.write("Unggah beberapa file PDF untuk diekstrak datanya.")
    
    uploaded_files = st.file_uploader("Upload file PDF", accept_multiple_files=True, type=["pdf"])
    
    if uploaded_files:
        #templates = read_templates("templates/")  # Pastikan folder 'templates/' berisi template yang sesuai
        templates = read_templates("/home/edo/programs/invx/app/templates")  # Pastikan folder 'templates/' berisi template yang sesuai
        results = []
        progress_bar = st.progress(0)
        total_files = len(uploaded_files)
        
        for i, uploaded_file in enumerate(uploaded_files):
            with st.spinner(f"Memproses file {i+1}/{total_files}..."):
                pdf_path = save_uploaded_file(uploaded_file)
                data = extract_invoice_data(pdf_path, templates)
                if data:
                    data["file"] = uploaded_file.name  # Tambahkan nama file ke data
                    #logger.debug(f"Data yang diekstrak dari {uploaded_file.name}: {data}")
                    results.append(data)
                os.remove(pdf_path)
            progress_bar.progress((i + 1) / total_files)
        
        if results:
            st.write("### Hasil Ekstraksi:")
            
            # Normalisasi data sebelum membuat DataFrame
            expand_columns = ["material", "amount", "sn"]
            results = normalize_data(results, expand_columns)
            
            df = pd.DataFrame(results)
            df_expanded = expand_rows(df, expand_columns)
            
            # Pastikan payment_method tetap dalam format string yang bersih
            if "payment_method" in df_expanded.columns:
                df_expanded["payment_method"] = df_expanded["payment_method"].apply(lambda x: ", ".join(x) if isinstance(x, list) else (x if x else "Unknown"))
            else:
                logger.warning("Kolom 'payment_method' tidak ditemukan dalam hasil ekstraksi.")
            
            st.dataframe(df_expanded)
            
            # Tombol unduh sebagai file Excel
            output_excel = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            with pd.ExcelWriter(output_excel.name, engine='xlsxwriter') as writer:
                df_expanded.to_excel(writer, index=False)
            
            with open(output_excel.name, "rb") as file:
                st.download_button(
                    label="Unduh Excel",
                    data=file,
                    file_name="hasil_ekstraksi.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("Tidak ada data yang berhasil diekstrak.")

if __name__ == "__main__":
    main()
