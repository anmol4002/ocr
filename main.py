from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import pdfplumber
import ocrmypdf
import tempfile
import os
import re 
from typing import List, Optional, Dict, Tuple
from docx import Document
from PIL import Image
import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
import fitz  
import pytesseract
import io
from langdetect import detect, DetectorFactory, LangDetectException
import unicodedata
import time
import gc

app = FastAPI()

load_dotenv()

JWT_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

DetectorFactory.seed = 0

security = HTTPBearer()

SUPPORTED_LANG_MAP = {
    "en": "eng",
    "hi": "hin", 
    "pa": "pan"
}

UNICODE_RANGES = {
    'devanagari': (0x0900, 0x097F),
    'gurmukhi': (0x0A00, 0x0A7F),
    'latin': (0x0041, 0x007A),
}

class PageProcessingInfo(BaseModel):
    page_number: int
    detected_languages: List[str]
    language_scores: Dict[str, float]
    ocr_method: str
    text_length: int

class OCRResponse(BaseModel):
    extracted_text: str
    detected_languages: List[str]
    language_used_for_ocr: str
    confidence_score: float
    page_processing_info: Optional[List[PageProcessingInfo]] = None
    total_pages: Optional[int] = None

def create_token():
    expire = datetime.utcnow() + timedelta(hours=1)
    payload = {
        "property": "Punjab Government",
        "exp": expire
    }
    return jwt.encode(payload, JWT_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_KEY, algorithms=[ALGORITHM])
        if payload.get("property") != "Punjab Government":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token - wrong property",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

def preprocess_text(text: str) -> str:
    if not text:
        return ""
    
    text = re.sub(r'\s+', ' ', text.strip())
    text = unicodedata.normalize('NFC', text)
    return text

def analyze_script_distribution(text: str) -> Dict[str, float]:
    if not text:
        return {'latin': 0, 'devanagari': 0, 'gurmukhi': 0}
    
    text = preprocess_text(text)
    total_chars = len(re.sub(r'\s+', '', text))
    
    if total_chars == 0:
        return {'latin': 0, 'devanagari': 0, 'gurmukhi': 0}
    
    script_counts = {'latin': 0, 'devanagari': 0, 'gurmukhi': 0}
    
    for char in text:
        char_code = ord(char)
        
        if UNICODE_RANGES['devanagari'][0] <= char_code <= UNICODE_RANGES['devanagari'][1]:
            script_counts['devanagari'] += 1
        elif UNICODE_RANGES['gurmukhi'][0] <= char_code <= UNICODE_RANGES['gurmukhi'][1]:
            script_counts['gurmukhi'] += 1
        elif UNICODE_RANGES['latin'][0] <= char_code <= UNICODE_RANGES['latin'][1]:
            script_counts['latin'] += 1
    
    return {
        script: (count / total_chars) * 100 
        for script, count in script_counts.items()
    }

def detect_languages(text: str) -> tuple[List[str], Dict[str, float]]:
    if not text or len(text.strip()) < 10:
        return ["eng"], {"eng": 60.0}
    
    text = preprocess_text(text)
    script_dist = analyze_script_distribution(text)
    
    language_scores = {
        'hin': script_dist['devanagari'],
        'pan': script_dist['gurmukhi'],
        'eng': script_dist['latin']
    }
    
    try:
        if max(language_scores.values()) < 30:
            clean_text = re.sub(r'[^\u0900-\u097F\u0A00-\u0A7Fa-zA-Z\s]', ' ', text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
            if len(clean_text) > 20:
                detected_lang = detect(clean_text)
                if detected_lang in SUPPORTED_LANG_MAP:
                    lang_code = SUPPORTED_LANG_MAP[detected_lang]
                    language_scores[lang_code] = max(language_scores[lang_code], 70.0)
                    
    except Exception:
        pass
    
    detected_languages = []
    primary_lang = max(language_scores.items(), key=lambda x: x[1])
    
    if primary_lang[1] >= 25:
        detected_languages.append(primary_lang[0])
    
    for lang, score in language_scores.items():
        if lang != primary_lang[0] and score >= 10:
            detected_languages.append(lang)
    
    if not detected_languages:
        detected_languages = ["eng"]
        language_scores["eng"] = 50.0
    
    return detected_languages, language_scores

def get_ocr_language_string(detected_languages: List[str]) -> str:
    if not detected_languages:
        return 'pan+eng+hin'
    
    if 'eng' not in detected_languages:
        detected_languages.append('eng')
    
    return '+'.join(detected_languages)

def should_use_ocrmypdf(detected_languages: List[str], language_scores: Dict[str, float]) -> bool:
    if not detected_languages:
        return False
    
    if len(detected_languages) == 1 and detected_languages[0] == 'eng':
        return True
   
    eng_score = language_scores.get('eng', 0)
    other_scores = [score for lang, score in language_scores.items() if lang != 'eng']
    
    if eng_score > 60 and all(score < 10 for score in other_scores):
        return True
    
    return False

def detect_language_from_image(img: Image.Image) -> Tuple[List[str], Dict[str, float]]:
    try:
        width, height = img.size
        center_crop = img.crop((width//4, height//4, 3*width//4, 3*height//4))
        
        sample_text = pytesseract.image_to_string(
            center_crop, 
            lang='eng+hin+pan',
            config='--psm 8 --oem 3'
        )
        
        if sample_text and len(sample_text.strip()) > 5:
            return detect_languages(sample_text)
        else:
            return ["eng", "hin", "pan"], {"eng": 40.0, "hin": 30.0, "pan": 30.0}
            
    except Exception:
        return ["eng"], {"eng": 60.0, "hin": 20.0, "pan": 20.0}

def safe_file_cleanup(file_paths: List[str], max_retries: int = 3, delay: float = 0.1):
    for file_path in file_paths:
        if not file_path or not os.path.exists(file_path):
            continue
            
        for attempt in range(max_retries):
            try:
                gc.collect()
                
                if attempt > 0:
                    time.sleep(delay * (attempt + 1))
                
                os.remove(file_path)
                break
                
            except PermissionError:
                if attempt == max_retries - 1:
                    break
            except Exception:
                break

def process_with_ocrmypdf_single_page(pdf_document, page_num):
    temp_input_path = None
    temp_output_path = None
    single_page_doc = None
    
    try:
        single_page_doc = fitz.open()
        single_page_doc.insert_pdf(pdf_document, from_page=page_num, to_page=page_num)
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_input:
            single_page_doc.save(temp_input.name)
            temp_input_path = temp_input.name
        
        single_page_doc.close()
        single_page_doc = None
        
        temp_output_path = temp_input_path + "_ocr.pdf"
        
        ocrmypdf.ocr(
            input_file=temp_input_path,
            output_file=temp_output_path,
            language='eng',
            force_ocr=True,
            progress_bar=False,
            skip_text=True  
        )
       
        with pdfplumber.open(temp_output_path) as ocr_pdf:
            page_text = ocr_pdf.pages[0].extract_text() if ocr_pdf.pages else ""
        
        return page_text, "ocrmypdf"
        
    except Exception:
        try:
            page = pdf_document.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            page_text = pytesseract.image_to_string(img, lang='eng')
            return page_text, "tesseract"
        except Exception:
            return "", "tesseract"
        
    finally:
        if single_page_doc:
            single_page_doc.close()
        temp_files = [f for f in [temp_input_path, temp_output_path] if f is not None]
        if temp_files:
            safe_file_cleanup(temp_files)

def process_pdf_page_by_page(pdf_bytes: bytes) -> Tuple[List[str], List[PageProcessingInfo], int]:
    all_text_parts = []
    all_page_info = []
    
    pdf_document = None
    try:
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_pages = len(pdf_document)
        
        for page_num in range(total_pages):
            try:
                page = pdf_document.load_page(page_num)
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
     
                page_detected_languages, page_language_scores = detect_language_from_image(img)
                use_ocrmypdf = should_use_ocrmypdf(page_detected_languages, page_language_scores)
                
                if use_ocrmypdf:
                    page_text, ocr_method = process_with_ocrmypdf_single_page(pdf_document, page_num)
                else:
                    lang_string = get_ocr_language_string(page_detected_languages)
                    page_text = pytesseract.image_to_string(img, lang=lang_string)
                    ocr_method = "tesseract"
                    
                    if page_text.strip():
                        quick_lang_check, quick_scores = detect_languages(page_text)
                        should_switch_to_ocrmypdf = should_use_ocrmypdf(quick_lang_check, quick_scores)
                        
                        if should_switch_to_ocrmypdf and len(page_text.strip()) > 50:
                            try:
                                ocrmypdf_text, _ = process_with_ocrmypdf_single_page(pdf_document, page_num)
                                if len(ocrmypdf_text.strip()) > len(page_text.strip()) * 0.5:
                                    page_text = ocrmypdf_text
                                    ocr_method = "ocrmypdf"
                            except Exception:
                                pass
       
                if page_text.strip():
                    final_page_languages, final_page_scores = detect_languages(page_text)
                else:
                    final_page_languages, final_page_scores = page_detected_languages, page_language_scores
          
                page_info = PageProcessingInfo(
                    page_number=page_num + 1,
                    detected_languages=final_page_languages,
                    language_scores={k: round(v, 1) for k, v in final_page_scores.items()},
                    ocr_method=ocr_method,
                    text_length=len(page_text.strip())
                )
                all_page_info.append(page_info)
             
                if page_text.strip():
                    all_text_parts.append(page_text.strip())
                
            except Exception:
                page_info = PageProcessingInfo(
                    page_number=page_num + 1,
                    detected_languages=["eng"],
                    language_scores={"eng": 0.0},
                    ocr_method="tesseract",
                    text_length=0
                )
                all_page_info.append(page_info)
        
        return all_text_parts, all_page_info, total_pages
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")
    
    finally:
        if pdf_document:
            pdf_document.close()

def process_image_file(img: Image.Image) -> Tuple[str, str, List[str], Dict[str, float]]:
    img_languages, img_scores = detect_language_from_image(img)
    
    if should_use_ocrmypdf(img_languages, img_scores):
        ocr_text = pytesseract.image_to_string(img, lang='eng')
        ocr_method = "tesseract"
    else:
        lang_str = get_ocr_language_string(img_languages)
        ocr_text = pytesseract.image_to_string(img, lang=lang_str)
        ocr_method = "tesseract"
    
    return ocr_text, ocr_method, img_languages, img_scores

@app.get("/token")
async def get_token():
    token = create_token()
    return {"token": token}

@app.post("/ocr", response_model=OCRResponse)
async def ocr_endpoint(
    files: List[UploadFile] = File(...),
    languages: Optional[str] = None,
    token_payload: dict = Depends(verify_token)
):
    try:
        all_text_parts = []
        all_page_info = []
        total_pages = 0
        
        for file in files:
            ext = os.path.splitext(file.filename)[1].lower()
            
            if ext == '.pdf':
                file.file.seek(0)
                pdf_bytes = file.file.read()
                
                pdf_text_parts, pdf_page_info, pdf_total_pages = process_pdf_page_by_page(pdf_bytes)
                
                all_text_parts.extend(pdf_text_parts)
                all_page_info.extend(pdf_page_info)
                total_pages += pdf_total_pages
                
            elif ext == '.docx':
                file.file.seek(0)
                doc = Document(file.file)
                doc_text = " ".join(para.text for para in doc.paragraphs if para.text.strip())
                all_text_parts.append(doc_text)
                
                doc_languages, doc_scores = detect_languages(doc_text)
                page_info = PageProcessingInfo(
                    page_number=1,
                    detected_languages=doc_languages,
                    language_scores={k: round(v, 1) for k, v in doc_scores.items()},
                    ocr_method="text_extraction",
                    text_length=len(doc_text.strip())
                )
                all_page_info.append(page_info)
                total_pages += 1
                
            elif ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                file.file.seek(0)
                img = Image.open(io.BytesIO(file.file.read()))
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                ocr_text, ocr_method, img_languages, img_scores = process_image_file(img)
                all_text_parts.append(ocr_text)
                
                page_info = PageProcessingInfo(
                    page_number=1,
                    detected_languages=img_languages,
                    language_scores={k: round(v, 1) for k, v in img_scores.items()},
                    ocr_method=ocr_method,
                    text_length=len(ocr_text.strip())
                )
                all_page_info.append(page_info)
                total_pages += 1
                
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
        
        final_text = " ".join(all_text_parts)
        cleaned_text = preprocess_text(final_text)
        
        if cleaned_text:
            detected_languages, language_scores = detect_languages(cleaned_text)
        else:
            detected_languages = ["eng"]
            language_scores = {"eng": 50.0}
        
        if languages:
            language_used = languages
        else:
            language_used = get_ocr_language_string(detected_languages)
        
        confidence_score = max(language_scores.values()) if language_scores else 70.0
        
        return OCRResponse(
            extracted_text=cleaned_text,
            detected_languages=detected_languages,
            language_used_for_ocr=language_used,
            confidence_score=round(confidence_score, 1),
            page_processing_info=all_page_info,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")














