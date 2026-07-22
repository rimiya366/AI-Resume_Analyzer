import fitz  # PyMuPDF for PDF parsing
import requests
import streamlit as st

st.set_page_config(page_title="📄 Resume & Job Matcher", layout="centered")

st.title("📄 Resume & Job Matcher")

st.sidebar.info("""
This app uses a local LLM via **Ollama**.
1. Install Ollama: https://ollama.ai
2. Start the server: `ollama serve`
3. Pull a model: `ollama pull qwen2.5:1.5b` (or your preferred model)
4. Select your model in the dropdown below!
""")

# Model selector in sidebar
model_name = st.sidebar.text_input("Ollama Model", value="qwen2.5:1.5b")


# Helper: Extract text from PDF using PyMuPDF
def extract_pdf_text(uploaded_file) -> str:
    text = ""
    # Read bytes using getvalue() to avoid stream exhaustion
    pdf_bytes = uploaded_file.getvalue()
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text


def get_text_from_file(uploaded_file) -> str:
    if uploaded_file.type == "application/pdf":
        return extract_pdf_text(uploaded_file)
    else:
        # Decode text files safely
        return uploaded_file.getvalue().decode("utf-8", errors="ignore")


# File uploaders
resume_file = st.file_uploader("Upload Resume (PDF/TXT)", type=["pdf", "txt"])
job_file = st.file_uploader(
    "Upload Job Description (PDF/TXT)", type=["pdf", "txt"]
)

if st.button("🔍 Match Resume with Job Description", type="primary"):
    if resume_file and job_file:
        try:
            with st.spinner("⏳ Reading documents..."):
                resume_text = get_text_from_file(resume_file)
                job_text = get_text_from_file(job_file)

            if not resume_text.strip() or not job_text.strip():
                st.error(
                    "⚠️ Could not extract text from one or both files. Check if the files are empty or scanned image PDFs."
                )
                st.stop()

            # Structured Prompting
            prompt = f"""
You are an expert ATS (Applicant Tracking System) recruiter and career assistant.
Analyze the following resume against the job description.

--- RESUME START ---
{resume_text}
--- RESUME END ---

--- JOB DESCRIPTION START ---
{job_text}
--- JOB DESCRIPTION END ---

Provide your analysis in clean Markdown with the following structured format:
## Fit Score
Provide an estimated score from 0% to 100% with a short 1-sentence justification.

## Key Strengths
- Highlight 3-5 specific matching skills, experiences, or qualifications.

## Missing Skills & Gaps
- Identify key requirements from the job description that are missing or weak in the resume.

## Actionable Recommendations
- Provide clear steps to reword, restructure, or add relevant keywords to improve ATS alignment.
"""

            with st.spinner(f"🤖 Analyzing with local model `{model_name}`..."):
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": model_name,
                        "prompt": prompt,
                        "stream": False,
                    },
                    timeout=120,  # 2 minute safety timeout
                )
                response.raise_for_status()

                data = response.json()
                output = data.get("response", "⚠️ No response from model.")

            # Display Results
            st.subheader("📌 Match Analysis")
            st.markdown(output)

            # Store in session state for downloading
            st.session_state["resume_match"] = output

        except requests.exceptions.ConnectionError:
            st.error(
                "❌ Could not connect to Ollama. Make sure `ollama serve` is running on your machine."
            )
        except requests.exceptions.HTTPError as http_err:
            st.error(
                f"❌ Ollama API Error: {http_err}. Check if the model `{model_name}` is pulled (`ollama pull {model_name}`)."
            )
        except Exception as e:
            st.error(f" An error occurred: {str(e)}")

    else:
        st.warning("⚠️ Please upload both a Resume and a Job Description.")

# Download button outside the submit block so it persists
if "resume_match" in st.session_state:
    st.divider()
    st.download_button(
        label="💾 Download Match Report",
        data=st.session_state["resume_match"],
        file_name="resume_match_report.md",
        mime="text/markdown",
    )
