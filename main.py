# from fastapi import FastAPI, UploadFile, File
# from fastapi.responses import JSONResponse
# import pdfplumber
# import ocrmypdf
# import tempfile
# import os
# from typing import List
# from docx import Document
# from PIL import Image

# app = FastAPI()

# def get_file_text(files: List[UploadFile], languages='pan+eng'):
#     text = ""
    
#     for file in files:
#         file_name = file.filename
#         file_ext = os.path.splitext(file_name)[1].lower()
        
#         try:
#             if file_ext == '.pdf':
#                 try:
#                     with pdfplumber.open(file.file) as pdf_reader:
#                         for page in pdf_reader.pages:
#                             page_text = page.extract_text()
#                             if page_text:
#                                 text += page_text + "\n"
#                             else:
#                                 raise Exception("No text found - need OCR")
                
#                 except Exception:
#                     file.file.seek(0)
#                     temp_dir = tempfile.gettempdir()
#                     temp_input_path = os.path.join(temp_dir, f"input_{file_name}")
#                     temp_output_path = os.path.join(temp_dir, f"output_{file_name}")
                    
#                     try:
#                         with open(temp_input_path, 'wb') as f:
#                             f.write(file.file.read())
                        
#                         ocrmypdf.ocr(
#                             input_file=temp_input_path,
#                             output_file=temp_output_path,
#                             language=languages,
#                             force_ocr=True,
#                             progress_bar=False,
#                             optimize=False
#                         )
                        
#                         with pdfplumber.open(temp_output_path) as pdf_reader:
#                             for page in pdf_reader.pages:
#                                 page_text = page.extract_text()
#                                 if page_text:
#                                     text += page_text + "\n"
                    
#                     finally:
#                         for path in [temp_input_path, temp_output_path]:
#                             try:
#                                 if os.path.exists(path):
#                                     os.remove(path)
#                             except Exception as e:
#                                 print(f"Error cleaning up {path}: {e}")

#             elif file_ext == '.docx':
#                 doc = Document(file.file)
#                 for paragraph in doc.paragraphs:
#                     if paragraph.text.strip():
#                         text += paragraph.text + "\n"
            
#             elif file_ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
#                 temp_dir = tempfile.gettempdir()
#                 temp_image_path = os.path.join(temp_dir, f"image_{file_name}")
#                 temp_pdf_path = os.path.join(temp_dir, f"pdf_{file_name}.pdf")
#                 temp_output_path = os.path.join(temp_dir, f"output_{file_name}.pdf")
                
#                 try:
                     
#                     with open(temp_image_path, 'wb') as f:
#                         f.write(file.file.read())
     
#                     image = Image.open(temp_image_path)
#                     if image.mode != 'RGB':
#                         image = image.convert('RGB')
#                     image.save(temp_pdf_path, 'PDF')

#                     ocrmypdf.ocr(
#                         input_file=temp_pdf_path,
#                         output_file=temp_output_path,
#                         language=languages,
#                         force_ocr=True,
#                         progress_bar=False,
#                         optimize=False
#                     )
                    
#                     with pdfplumber.open(temp_output_path) as pdf_reader:
#                         for page in pdf_reader.pages:
#                             page_text = page.extract_text()
#                             if page_text:
#                                 text += page_text + "\n"
                
#                 finally:
#                     for path in [temp_image_path, temp_pdf_path, temp_output_path]:
#                         try:
#                             if os.path.exists(path):
#                                 os.remove(path)
#                         except Exception as e:
#                             print(f"Error cleaning up {path}: {e}")
            
#             else:
#                 raise Exception(f"Unsupported file type: {file_ext}")
                
#         except Exception as e:
#             print(f"Error processing {file_name}: {e}")
    
#     return text

# @app.post("/ocr/")
# async def ocr_endpoint(files: List[UploadFile] = File(...)):
#     try:
#         text = get_file_text(files)
#         return JSONResponse(content={"text": text})
#     except Exception as e:
#         return JSONResponse(status_code=500, content={"error": str(e)})









# 🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸
# from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# import pdfplumber
# import ocrmypdf
# import tempfile
# import os
# from typing import List
# from docx import Document
# from PIL import Image
# import jwt
# from datetime import datetime, timedelta
# from dotenv import load_dotenv

# app = FastAPI()

# load_dotenv()  

# JWT_KEY = os.getenv("JWT_SECRET_KEY")
# ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256") 

# security = HTTPBearer()

# def create_token():
#     expire = datetime.utcnow() + timedelta(hours=1)
#     payload = {
#         "property": "Punjab Government",
#         "exp": expire
#     }
#     return jwt.encode(payload, JWT_KEY, algorithm=ALGORITHM)

# def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
#     try:
#         payload = jwt.decode(credentials.credentials, JWT_KEY, algorithms=[ALGORITHM])
#         if payload.get("property") != "Punjab Government":
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Invalid token - wrong property",
#                 headers={"WWW-Authenticate": "Bearer"},
#             )
#         return payload
#     except jwt.PyJWTError as e:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail=f"Could not validate credentials: {str(e)}",
#             headers={"WWW-Authenticate": "Bearer"},
#         )


# def process_pdf(file, languages='pan+eng'):
#     text = ""
#     try:
#         with pdfplumber.open(file.file) as pdf:
#             text = " ".join(page.extract_text() or "" for page in pdf.pages)
#         if not text.strip():
#             raise Exception("No text found - need OCR")
#     except Exception:
#         file.file.seek(0)
#         with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_input:
#             temp_input.write(file.file.read())
#             temp_input_path = temp_input.name
        
#         temp_output_path = temp_input_path + "_ocr.pdf"
#         try:
#             ocrmypdf.ocr(
#                 input_file=temp_input_path,
#                 output_file=temp_output_path,
#                 language=languages,
#                 force_ocr=True,
#                 progress_bar=False
#             )
#             with pdfplumber.open(temp_output_path) as pdf:
#                 text = " ".join(page.extract_text() or "" for page in pdf.pages)
#         finally:
#             for path in [temp_input_path, temp_output_path]:
#                 try:
#                     if os.path.exists(path):
#                         os.remove(path)
#                 except Exception:
#                     pass
#     return text

# def process_docx(file):
#     doc = Document(file.file)
#     return " ".join(para.text for para in doc.paragraphs if para.text.strip())

# def process_image(file, languages='pan+eng'):
#     with tempfile.NamedTemporaryFile(suffix=os.path.splitext(file.filename)[1], delete=False) as temp_img:
#         temp_img.write(file.file.read())
#         temp_img_path = temp_img.name
    
#     temp_pdf_path = temp_img_path + ".pdf"
#     temp_output_path = temp_img_path + "_ocr.pdf"
    
#     try:
#         image = Image.open(temp_img_path)
#         if image.mode != 'RGB':
#             image = image.convert('RGB')
#         image.save(temp_pdf_path, 'PDF')

#         ocrmypdf.ocr(
#             input_file=temp_pdf_path,
#             output_file=temp_output_path,
#             language=languages,
#             force_ocr=True,
#             progress_bar=False
#         )
        
#         with pdfplumber.open(temp_output_path) as pdf:
#             return " ".join(page.extract_text() or "" for page in pdf.pages)
#     finally:
#         for path in [temp_img_path, temp_pdf_path, temp_output_path]:
#             try:
#                 if os.path.exists(path):
#                     os.remove(path)
#             except Exception:
#                 pass

# def get_file_text(files: List[UploadFile], languages='pan+eng'):
#     text = []
#     for file in files:
#         ext = os.path.splitext(file.filename)[1].lower()
#         try:
#             if ext == '.pdf':
#                 text.append(process_pdf(file, languages))
#             elif ext == '.docx':
#                 text.append(process_docx(file))
#             elif ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
#                 text.append(process_image(file, languages))
#             else:
#                 raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
#         except Exception as e:
#             raise HTTPException(status_code=400, detail=f"Error processing {file.filename}: {str(e)}")
#     return " ".join(text)

# @app.get("/token")
# async def get_token():
#     token = create_token()
#     return {"token": token}

# @app.post("/ocr")
# async def ocr_endpoint(
#     files: List[UploadFile] = File(...),
#     token_payload: dict = Depends(verify_token)
# ):
#     extracted_text = get_file_text(files)
#     cleaned_text = ' '.join(extracted_text.replace('\n', ' ').split())
#     return cleaned_text
# 🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸🌸








from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import pdfplumber
import ocrmypdf
import tempfile
import os
from typing import List
from docx import Document
from PIL import Image
import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
import fitz  # PyMuPDF
import pytesseract
import io


app = FastAPI()

load_dotenv()  

JWT_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256") 

security = HTTPBearer()

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


def process_pdf_ocrmypdf(file, languages='pan+eng'):
    text = ""
    try:
        file.file.seek(0)
        with pdfplumber.open(file.file) as pdf:
            text = " ".join(page.extract_text() or "" for page in pdf.pages)
        if not text.strip():
            raise Exception("No text found - need OCR")
    except Exception:
        file.file.seek(0)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_input:
            temp_input.write(file.file.read())
            temp_input_path = temp_input.name
        
        temp_output_path = temp_input_path + "_ocr.pdf"
        try:
            ocrmypdf.ocr(
                input_file=temp_input_path,
                output_file=temp_output_path,
                language=languages,
                force_ocr=True,
                progress_bar=False
            )
            with pdfplumber.open(temp_output_path) as pdf:
                text = " ".join(page.extract_text() or "" for page in pdf.pages)
        finally:
            for path in [temp_input_path, temp_output_path]:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except Exception:
                    pass
    return text

def process_pdf_tesseract(file, languages='pan+eng'):
    text = ""
    file.file.seek(0)
    pdf_bytes = file.file.read()
    pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
      
        pix = page.get_pixmap()
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        
        page_text = pytesseract.image_to_string(
            img,
            lang=languages,
            config='--psm 3'
        )
        text += page_text + " "
    
    pdf_document.close()
    return text

def process_docx(file):
    file.file.seek(0)
    doc = Document(file.file)
    return " ".join(para.text for para in doc.paragraphs if para.text.strip())

def process_image_ocrmypdf(file, languages='pan+eng'):
    file.file.seek(0)
    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(file.filename)[1], delete=False) as temp_img:
        temp_img.write(file.file.read())
        temp_img_path = temp_img.name
    
    temp_pdf_path = temp_img_path + ".pdf"
    temp_output_path = temp_img_path + "_ocr.pdf"
    
    try:
        image = Image.open(temp_img_path)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        image.save(temp_pdf_path, 'PDF')

        ocrmypdf.ocr(
            input_file=temp_pdf_path,
            output_file=temp_output_path,
            language=languages,
            force_ocr=True,
            progress_bar=False
        )
        
        with pdfplumber.open(temp_output_path) as pdf:
            return " ".join(page.extract_text() or "" for page in pdf.pages)
    finally:
        for path in [temp_img_path, temp_pdf_path, temp_output_path]:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass

def process_image_tesseract(file, languages='pan+eng'):
    file.file.seek(0)
    img = Image.open(io.BytesIO(file.file.read()))
    ocr_text = pytesseract.image_to_string(
        img,
        lang=languages,
        config='--psm 3'
    )
    return ocr_text

def get_file_text_ocrmypdf(files: List[UploadFile], languages='pan+eng'):
    text = []
    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        try:
            if ext == '.pdf':
                text.append(process_pdf_ocrmypdf(file, languages))
            elif ext == '.docx':
                text.append(process_docx(file))
            elif ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                text.append(process_image_ocrmypdf(file, languages))
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error processing {file.filename}: {str(e)}")
    return " ".join(text)

def get_file_text_tesseract(files: List[UploadFile], languages='pan+eng'):
    text = []
    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        try:
            if ext == '.pdf':
                text.append(process_pdf_tesseract(file, languages))
            elif ext == '.docx':
                text.append(process_docx(file))  # DOCX doesn't need OCR
            elif ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                text.append(process_image_tesseract(file, languages))
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error processing {file.filename}: {str(e)}")
    return " ".join(text)

@app.get("/token")
async def get_token():
    token = create_token()
    return {"token": token}

@app.post("/ocrmypdf")
async def ocr_endpoint(
    files: List[UploadFile] = File(...),
    languages: str = 'pan+eng',
    token_payload: dict = Depends(verify_token)
):
    extracted_text = get_file_text_ocrmypdf(files, languages)
    cleaned_text = ' '.join(extracted_text.replace('\n', ' ').split())
    return {"extracted_text": cleaned_text}

@app.post("/ocr-tesseract")
async def ocr_tesseract_only(
    files: List[UploadFile] = File(...),
    languages: str = 'pan+eng',
    token_payload: dict = Depends(verify_token)
):
    extracted_text = get_file_text_tesseract(files, languages)
    cleaned_text = ' '.join(extracted_text.replace('\n', ' ').split())
    return {"extracted_text": cleaned_text}